from __future__ import annotations
from pathlib import Path
from .config import AppConfig
from .pipeline import run_job

MEDIA_EXTS={".mp4",".mkv",".mov",".avi",".webm",".m4v",".mp3",".m4a",".wav",".flac",".ogg"}

def discover_media(folder: Path) -> list[str]:
    return [str(p) for p in sorted(folder.rglob("*")) if p.is_file() and p.suffix.lower() in MEDIA_EXTS]

def run_batch(sources: list[str], cfg: AppConfig, output_root: Path, progress=print) -> list[Path]:
    results=[]
    for i,source in enumerate(sources,1):
        progress(f"BATCH {i}/{len(sources)}: {source}")
        try:
            results.append(run_job(source,cfg,output_root,progress))
        except Exception as exc:
            progress(f"BATCH {i}/{len(sources)} FAILED: {exc}")
    return results
