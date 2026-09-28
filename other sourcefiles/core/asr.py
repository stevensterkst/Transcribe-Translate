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
    # Long recordings are processed in bounded windows. Within each window,
    # faster-whisper's BatchedInferencePipeline batches VAD speech segments.
    # This is materially faster than one Whisper call for every 20-45 seconds,
    # while keeping the decoded PCM bounded on a 16 GB Windows machine.
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
        # Conservative because Ollama/GUI may also be using RAM.
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

    def _collect(self, runner, audio, language, batch_size):
        segments, info = self._run(runner, audio, language, True, batch_size)
        collected = []

        def collect_from(items):
            for segment in items:
                text = segment.text.strip()
                if not text:
                    continue
                words = None
                if self.word_timestamps and getattr(segment, "words", None):
                    words = [
                        Word(float(w.start), float(w.end), str(w.word),
                             float(w.probability) if getattr(w, "probability", None) is not None else None)
                        for w in segment.words
                    ]
                collected.append(Segment(float(segment.start), float(segment.end), text, words=words))

        collect_from(segments)
        if not collected:
            self.progress("No speech survived VAD in this window; retrying without VAD.")
            segments, info = self._run(runner, audio, language, False, batch_size)
            collect_from(segments)
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
            if len(ranges) > 1:
                self.progress(
                    f"Long-recording mode: {len(ranges)} bounded windows; "
                    f"batched speech inference={batch_size}. RAM remains bounded."
                )

            all_segments = []
            detected_language = None

            for i, (start, end) in enumerate(ranges, 1):
                offset = start / float(rate)
                wf.setpos(start)
                raw = wf.readframes(end - start)
                samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
                self.progress(
                    f"ASR window {i}/{len(ranges)} — {offset/60:.1f}–{end/rate/60:.1f} min"
                )
                collected, info = self._collect(
                    runner, samples, language or detected_language, batch_size
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

        if not all_segments:
            raise RuntimeError(
                "Local transcription produced zero speech segments. No downstream AI stage was run."
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
