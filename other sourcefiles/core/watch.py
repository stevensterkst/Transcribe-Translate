from __future__ import annotations
import hashlib
import json
import time
from pathlib import Path
from .batch import MEDIA_EXTS
from .config import AppConfig
from .pipeline import run_job

def file_hash(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def watch_folder(folder: Path, cfg: AppConfig, output_root: Path, stop_event, progress=print, interval: int=5):
    state_path=output_root/"watch-state.json"
    state=json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    progress(f"WATCHING: {folder}")
    while not stop_event.is_set():
        for path in sorted(folder.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in MEDIA_EXTS: continue
            try: key=str(path.resolve()); digest=file_hash(path)
            except OSError: continue
            if state.get(key)==digest: continue
            try:
                run_job(key,cfg,output_root,progress)
                state[key]=digest
                state_path.write_text(json.dumps(state,indent=2),encoding="utf-8")
            except Exception as exc:
                progress(f"WATCH FAILED: {path}: {exc}")
        stop_event.wait(interval)
