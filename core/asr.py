from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Callable

@dataclass
class Word:
    start: float
    end: float
    word: str
    probability: float | None = None

@dataclass
class Segment:
    start: float
    end: float
    text: str
    words: list[Word] | None = None
    speaker: str | None = None

@dataclass
class Transcript:
    text: str
    segments: list[Segment]
    language: str | None
    backend: str
    model: str

Progress = Callable[[str], None]

class FasterWhisperASR:
    # Process long recordings in bounded windows. Never ask Whisper to load the
    # whole recording into one inference call.
    CHUNK_SECONDS = 180

    def __init__(self, model: str, language: str, compute_type: str,
                 hotwords: str = "", word_timestamps: bool = False,
                 progress: Progress = print):
        self.model_name = model
        self.language = language
        self.compute_type = compute_type
        self.hotwords = hotwords.strip()
        self.word_timestamps = word_timestamps
        self.progress = progress

    @staticmethod
    def _ram_gb() -> float:
        try:
            import ctypes
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            m = MEMORYSTATUSEX()
            m.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            return m.ullTotalPhys / (1024 ** 3)
        except Exception:
            return 8.0

    @classmethod
    def _batch_size(cls) -> int:
        ram = cls._ram_gb()
        if ram >= 16:
            return 4
        if ram >= 12:
            return 3
        if ram >= 8:
            return 2
        return 1

    @staticmethod
    def _cpu_threads() -> int:
        import os
        n = os.cpu_count() or 4
        return max(2, min(8, n - 2))

    def _run(self, runner, audio, language, vad_filter, batch_size):
        kwargs = {
            "language": language,
            "beam_size": 1,
            "vad_filter": vad_filter,
            "condition_on_previous_text": False,
            "word_timestamps": self.word_timestamps,
            "batch_size": batch_size,
        }
        if self.hotwords:
            kwargs["hotwords"] = self.hotwords
        return runner.transcribe(audio, **kwargs)

    @staticmethod
    def _collect_segments(items, word_timestamps: bool) -> list[Segment]:
        collected = []
        for segment in items:
            text = segment.text.strip()
            if not text:
                continue
            words = None
            if word_timestamps and getattr(segment, "words", None):
                words = [
                    Word(float(w.start), float(w.end), str(w.word),
                         float(w.probability) if getattr(w, "probability", None) is not None else None)
                    for w in segment.words
                ]
            collected.append(Segment(
                float(segment.start), float(segment.end), text, words=words
            ))
        return collected

    def _collect(self, runner, audio, language, batch_size, window_seconds: float):
        # First use VAD so silence does not become hallucinated speech.
        segments, info = self._run(runner, audio, language, True, batch_size)
        collected = self._collect_segments(segments, self.word_timestamps)

        # VAD is allowed to reject a whole window, but it is NOT allowed to make
        # that window disappear silently. Retry without VAD.
        # Also retry when VAD produced an implausibly tiny result for a normal
        # speech recording; this catches aggressive VAD misses without making
        # every silent window expensive.
        text_chars = sum(len(s.text) for s in collected)
        suspicious = (
            not collected
            or (window_seconds >= 15 and text_chars < max(8, window_seconds * 0.35))
        )
        if suspicious:
            reason = "no speech survived VAD" if not collected else (
                f"VAD returned only {text_chars} text characters for a {window_seconds:.1f}s window"
            )
            self.progress(f"VAD coverage check: {reason}; retrying window without VAD.")
            segments, info = self._run(runner, audio, language, False, batch_size)
            fallback = self._collect_segments(segments, self.word_timestamps)
            if fallback:
                collected = fallback
        return collected, info

    def transcribe(self, audio: Path) -> Transcript:
        try:
            from faster_whisper import WhisperModel, BatchedInferencePipeline
        except ImportError as exc:
            raise RuntimeError(
                "faster-whisper is not installed. Torch/WhisperX are not required."
            ) from exc

        import wave
        import numpy as np

        language = None if self.language == "auto" else self.language
        batch_size = self._batch_size()
        threads = self._cpu_threads()
        self.progress(
            f"Local ASR: faster-whisper {self.model_name} / CPU INT8; "
            f"threads={threads}, batch={batch_size}, window={self.CHUNK_SECONDS}s, "
            f"word-timestamps={'ON' if self.word_timestamps else 'OFF'}"
        )

        with wave.open(str(audio), "rb") as wf:
            channels, width, rate, frames = (
                wf.getnchannels(), wf.getsampwidth(), wf.getframerate(), wf.getnframes()
            )
            duration = frames / float(rate or 1)
            if (channels, width, rate) != (1, 2, 16000):
                raise RuntimeError(
                    f"Internal audio format is {rate} Hz, {channels} channel(s), "
                    f"{width*8}-bit; expected 16000 Hz mono 16-bit PCM WAV."
                )

            self.progress(f"Audio duration: {duration/60:.1f} minutes")
            model = WhisperModel(
                self.model_name,
                device="cpu",
                compute_type=self.compute_type,
                cpu_threads=threads,
                num_workers=1,
            )
            runner = BatchedInferencePipeline(model=model)

            chunk_frames = self.CHUNK_SECONDS * rate
            ranges = [
                (start, min(frames, start + chunk_frames))
                for start in range(0, frames, chunk_frames)
            ]

            self.progress(
                f"ASR coverage plan: {len(ranges)} window(s) covering "
                f"0.0–{duration/60:.2f} minutes."
            )

            all_segments = []
            detected_language = None

            for i, (start, end) in enumerate(ranges, 1):
                offset = start / float(rate)
                window_seconds = (end - start) / float(rate)
                wf.setpos(start)
                raw = wf.readframes(end - start)
                samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0

                self.progress(
                    f"ASR window {i}/{len(ranges)} — "
                    f"{offset/60:.2f}–{end/rate/60:.2f} min "
                    f"({window_seconds:.1f}s)"
                )
                collected, info = self._collect(
                    runner, samples, language or detected_language,
                    batch_size, window_seconds
                )
                if detected_language is None:
                    detected_language = getattr(info, "language", None) or language

                for s in collected:
                    s.start += offset
                    s.end += offset
                    if s.words:
                        for w in s.words:
                            w.start += offset
                            w.end += offset
                    all_segments.append(s)

                self.progress(
                    f"ASR window {i}/{len(ranges)} complete: "
                    f"{len(collected)} segment(s)."
                )

        if not all_segments:
            raise RuntimeError(
                "Local transcription produced zero speech segments. No downstream AI stage was run."
            )

        # The final segment timeline must never extend beyond the actual audio.
        # This catches offset/unit regressions before downstream summaries run.
        for s in all_segments:
            if s.start < 0 or s.end < s.start or s.end > duration + 0.5:
                raise RuntimeError(
                    f"ASR timestamp audit failed: segment {s.start:.3f}–{s.end:.3f}s "
                    f"is outside the {duration:.3f}s source audio."
                )

        return Transcript(
            text="\n".join(s.text for s in all_segments),
            segments=all_segments,
            language=detected_language,
            backend="faster-whisper-batched",
            model=self.model_name,
        )

def transcript_dict(transcript: Transcript) -> dict:
    return {
        "text": transcript.text,
        "language": transcript.language,
        "backend": transcript.backend,
        "model": transcript.model,
        "segments": [asdict(s) for s in transcript.segments],
    }
