from __future__ import annotations
from datetime import datetime
from pathlib import Path
import hashlib
import shutil
import json

from .asr import FasterWhisperASR
from .config import AppConfig
from .diarization import assign_speakers, diarize_audio
from .media import extract_audio, prepare_media, is_url
from .outputs import write_outputs
from .search import build_search_report
from .library import index_job
from .player import write_player
from .text import OllamaTextProvider, model_advice
from .captions import scrape_transcript

LANGUAGE_NAMES = {
    "ca": "Catalan", "es": "Spanish", "en": "English", "fr": "French",
    "de": "German", "it": "Italian", "nl": "Dutch", "pt": "Portuguese",
    "pl": "Polish", "ru": "Russian", "uk": "Ukrainian",
}

def timestamped_transcript(transcript) -> str:
    lines = []
    for segment in transcript.segments:
        start = int(segment.start)
        h, rem = divmod(start, 3600)
        m, s = divmod(rem, 60)
        speaker = f"[{segment.speaker}] " if segment.speaker else ""
        lines.append(f"[{h:02d}:{m:02d}:{s:02d}] {speaker}{segment.text}")
    return "\n".join(lines)

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def _range_seconds(cfg: AppConfig, duration: float) -> float | None:
    mode = (cfg.range_mode or "full").lower().strip()
    value = float(cfg.range_value or 0)
    if mode == "full" or value <= 0:
        return None
    if mode == "minutes":
        return min(duration, value * 60.0)
    if mode == "percent":
        return min(duration, duration * min(value, 100.0) / 100.0)
    raise ValueError("range_mode must be full, minutes, or percent")

def run_job(source: str, cfg: AppConfig, output_root: Path, progress=print) -> Path:
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    stem = Path(source).stem[:80] if not is_url(source) else "web-media"
    job_dir = output_root / f"{stamp}_{stem}"
    work = job_dir / "_work"
    work.mkdir(parents=True, exist_ok=True)

    try:
        transcript = scrape_transcript(source, cfg.language, progress, cfg.range_mode, cfg.range_value) if is_url(source) else None
        media = None
        media_hash = None
        if transcript is None:
            progress("Preparing media...")
            media = prepare_media(source, work, cfg.ytdlp_path)
            media_hash = sha256_file(media)
            progress(f"Input SHA-256: {media_hash}")
            progress("Extracting 16 kHz mono audio...")
            limit = None
            if cfg.range_mode == "minutes" and cfg.range_value > 0:
                limit = cfg.range_value * 60.0
            elif cfg.range_mode == "percent" and cfg.range_value > 0:
                import subprocess, re
                from .media import find_ffmpeg, WINDOWS_NO_CONSOLE
                probe = subprocess.run([find_ffmpeg(), "-i", str(media)], capture_output=True, text=True, encoding="utf-8", errors="replace", **WINDOWS_NO_CONSOLE)
                match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", probe.stderr or "")
                if match:
                    total = int(match.group(1))*3600 + int(match.group(2))*60 + float(match.group(3))
                    limit = total * min(float(cfg.range_value), 100.0) / 100.0
            if limit is not None:
                progress(f"TRANSCRIPTION RANGE: first {limit/60:.2f} minutes only")
            audio = extract_audio(media, work / "audio.wav", limit)

            transcript = FasterWhisperASR(
                cfg.local_model, cfg.language, cfg.compute_type,
                hotwords=cfg.hotwords, word_timestamps=cfg.word_timestamps, progress=progress,
            ).transcribe(audio)
        else:
            progress("Caption/script path selected: no media download and no Whisper ASR required.")

        if not transcript.segments or not transcript.text.strip():
            raise RuntimeError("Pipeline safety check: source transcript is empty; downstream AI stages will not run.")

        diarization_used = False
        if cfg.diarization and media is not None:
            diarization_segments = diarize_audio(
                audio, cfg.diarization_segmentation_model, cfg.diarization_embedding_model,
                num_speakers=cfg.diarization_num_speakers,
                threshold=cfg.diarization_threshold, progress=progress,
            )
            assign_speakers(transcript.segments, diarization_segments)
            diarization_used = True

        detected_code = transcript.language or cfg.language
        source_name = LANGUAGE_NAMES.get(detected_code, detected_code or "source language")
        progress(f"PRIMARY TRANSCRIPT COMPLETE: {source_name}")

        provider = OllamaTextProvider(cfg.ollama_url, cfg.ollama_model, progress)
        source_summary = provider.summarize_source(transcript.text, source_name)
        if not source_summary.strip():
            raise RuntimeError("Source-language summary returned empty; job stopped.")
        english_summary = provider.translate_summary_to_english(source_summary, source_name)
        if not english_summary.strip():
            raise RuntimeError("English summary translation returned empty; job stopped.")

        timestamped = timestamped_transcript(transcript)
        analysis_source = ""
        analysis_translated = ""
        if cfg.analysis:
            analysis_source = provider.analyze_source(timestamped, source_name)
            if cfg.analysis_language.strip().lower() not in ("", "source", source_name.lower()):
                analysis_translated = provider.translate(analysis_source, cfg.analysis_language, purpose="analysis")

        search_report = build_search_report(transcript, cfg.search_query, cfg.top_terms)

        qa_answer = ""
        if cfg.qa_question.strip():
            qa_answer = provider.ask_transcript(timestamped, cfg.qa_question.strip(), cfg.qa_language.strip() or "English")

        translation = ""
        if cfg.translate_transcript:
            translation = provider.translate(transcript.text, cfg.target_language, purpose="transcript")

        write_outputs(
            transcript, translation, source_summary, english_summary, analysis_source, analysis_translated,
            search_report, qa_answer, cfg.qa_question, cfg.qa_language, job_dir, source,
            translated=cfg.translate_transcript, target_language=cfg.target_language,
            analysis_created=cfg.analysis, analysis_language=cfg.analysis_language,
        )

        tier, advice = model_advice(cfg.ollama_model)
        metadata = {
            "source": source, "input_media_sha256": media_hash, "language": transcript.language,
            "asr_backend": transcript.backend, "asr_model": transcript.model,
            "word_timestamps": cfg.word_timestamps, "hotwords": cfg.hotwords,
            "text_provider": "ollama", "text_model": cfg.ollama_model,
            "ollama_model_advice": {"tier": tier, "note": advice},
            "source_summary": "generated from original-language transcript",
            "english_summary": "translation of source-language summary",
            "analysis": "generated from timestamped original-language transcript" if cfg.analysis else None,
            "analysis_language": cfg.analysis_language if cfg.analysis else None,
            "search_query": cfg.search_query, "search_match_count": search_report["match_count"],
            "qa_question": cfg.qa_question, "qa_language": cfg.qa_language,
            "diarization": {"enabled": cfg.diarization, "used": diarization_used,
                            "segmentation_model": cfg.diarization_segmentation_model if cfg.diarization else None,
                            "embedding_model": cfg.diarization_embedding_model if cfg.diarization else None},
            "full_transcript_translation": cfg.translate_transcript,
            "target_language": cfg.target_language if cfg.translate_transcript else None,
            "range": {"mode": cfg.range_mode, "value": cfg.range_value},
            "api_cost": "Core processing is local/Ollama at no OpenAI API cost; optional transcript-workspace OpenAI queries are user-triggered and may incur API charges.",
        }
        (job_dir / "job.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        if cfg.keep_media and media is not None:
            write_player(job_dir, media, job_dir / "original.json")
            progress("Media retention enabled: downloaded/source media and extracted audio are retained in _work.")
        elif cfg.keep_media:
            progress("KEEP requested, but this job used a remote caption/script; no media was downloaded to retain.")
        else:
            progress("Text-only retention: deleting downloaded/source media and extracted audio.")

        index_job(job_dir, output_root)
        progress(f"COMPLETE: {job_dir}")
        return job_dir
    finally:
        if not cfg.keep_media:
            shutil.rmtree(work, ignore_errors=True)
            progress("Temporary source media/audio cleaned; text outputs retained.")
