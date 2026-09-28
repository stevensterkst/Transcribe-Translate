from __future__ import annotations
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

if getattr(sys, "frozen", False):
    # In a PyInstaller onedir build, config.local.json, models and runtime are
    # deliberately shipped beside the EXE, not inside PyInstaller internals.
    ROOT = Path(sys.executable).resolve().parent
else:
    ROOT = Path(__file__).resolve().parents[1]

@dataclass
class AppConfig:
    local_model: str = "base"
    language: str = "auto"
    compute_type: str = "int8"
    word_timestamps: bool = False
    hotwords: str = ""
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = ""
    analysis_language: str = "source"
    target_language: str = "English"
    translate_transcript: bool = False
    analysis: bool = False
    search_query: str = ""
    top_terms: int = 30
    qa_question: str = ""
    qa_language: str = "English"
    diarization: bool = False
    diarization_segmentation_model: str = ""
    diarization_embedding_model: str = ""
    diarization_num_speakers: int = 0
    diarization_threshold: float = 0.5
    output_dir: str = "output"
    ytdlp_path: str = ""
    keep_media: bool = False
    range_mode: str = "full"  # full | minutes | percent
    range_value: float = 0.0

def save_local_config(config: AppConfig, path: Path | None = None) -> Path:
    path = path or (ROOT / "config.local.json")
    payload = {
        "asr": {
            "local_model": config.local_model,
            "language": config.language,
            "compute_type": config.compute_type,
            "word_timestamps": config.word_timestamps,
            "hotwords": config.hotwords,
        },
        "text": {
            "ollama_model": config.ollama_model,
            "analysis_language": config.analysis_language,
            "target_language": config.target_language,
            "translate_transcript": config.translate_transcript,
            "analysis": config.analysis,
        },
        "analysis": {"search_query": config.search_query, "top_terms": config.top_terms},
        "qa": {"question": config.qa_question, "language": config.qa_language},
        "diarization": {
            "enabled": config.diarization,
            "segmentation_model": config.diarization_segmentation_model,
            "embedding_model": config.diarization_embedding_model,
            "num_speakers": config.diarization_num_speakers,
            "cluster_threshold": config.diarization_threshold,
        },
        "paths": {"output_dir": config.output_dir, "ytdlp_path": config.ytdlp_path, "keep_media": config.keep_media},
        "range": {"mode": config.range_mode, "value": config.range_value},
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path

def load_config(path: Path | None = None) -> AppConfig:
    path = path or (ROOT / "config.json")
    data: dict[str, Any] = {}
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    local_path = path.with_name("config.local.json")
    if local_path.exists():
        local_data = json.loads(local_path.read_text(encoding="utf-8-sig"))
        for section in ("asr", "text", "analysis", "qa", "diarization", "paths", "range"):
            if isinstance(local_data.get(section), dict):
                data.setdefault(section, {}).update(local_data[section])
    asr, text, analysis, qa, diar, paths = (
        data.get("asr", {}), data.get("text", {}), data.get("analysis", {}),
        data.get("qa", {}), data.get("diarization", {}), data.get("paths", {})
    )
    return AppConfig(
        local_model=asr.get("local_model", "base"), language=asr.get("language", "auto"),
        compute_type=asr.get("compute_type", "int8"), word_timestamps=bool(asr.get("word_timestamps", False)),
        hotwords=str(asr.get("hotwords", "")), ollama_url=text.get("ollama_url", "http://127.0.0.1:11434"),
        ollama_model=text.get("ollama_model", ""), analysis_language=str(text.get("analysis_language", "source")),
        target_language=text.get("target_language", "English"), translate_transcript=bool(text.get("translate_transcript", False)),
        analysis=bool(text.get("analysis", False)), search_query=str(analysis.get("search_query", "")),
        top_terms=int(analysis.get("top_terms", 30)), qa_question=str(qa.get("question", "")),
        qa_language=str(qa.get("language", "English")), diarization=bool(diar.get("enabled", False)),
        diarization_segmentation_model=str(diar.get("segmentation_model", "")),
        diarization_embedding_model=str(diar.get("embedding_model", "")),
        diarization_num_speakers=int(diar.get("num_speakers", 0)),
        diarization_threshold=float(diar.get("cluster_threshold", 0.5)),
        output_dir=paths.get("output_dir", "output"), ytdlp_path=paths.get("ytdlp_path", ""),
        keep_media=bool(paths.get("keep_media", False)),
        range_mode=str(data.get("range", {}).get("mode", "full")).lower(),
        range_value=float(data.get("range", {}).get("value", 0.0)),
    )
