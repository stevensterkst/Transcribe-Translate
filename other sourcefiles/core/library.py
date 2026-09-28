from __future__ import annotations
import json
import sqlite3
from pathlib import Path

def _db(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    return root / "library.sqlite3"

def init_library(root: Path) -> None:
    with sqlite3.connect(_db(root)) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS jobs(
            id INTEGER PRIMARY KEY, job_dir TEXT UNIQUE NOT NULL, created TEXT,
            source TEXT, language TEXT, duration REAL, speakers INTEGER,
            transcript TEXT, summary TEXT)""")
        db.commit()

def index_job(job_dir: Path, root: Path) -> None:
    init_library(root)
    job=json.loads((job_dir/"job.json").read_text(encoding="utf-8"))
    transcript=(job_dir/"original.txt").read_text(encoding="utf-8") if (job_dir/"original.txt").exists() else ""
    summary=(job_dir/"source_summary.md").read_text(encoding="utf-8") if (job_dir/"source_summary.md").exists() else ""
    segments=json.loads((job_dir/"original.json").read_text(encoding="utf-8")).get("segments",[])
    duration=max((float(s.get("end",0)) for s in segments),default=0.0)
    speakers=len({s.get("speaker") for s in segments if s.get("speaker")})
    with sqlite3.connect(_db(root)) as db:
        db.execute("""INSERT INTO jobs(job_dir,created,source,language,duration,speakers,transcript,summary)
        VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(job_dir) DO UPDATE SET
        created=excluded.created,source=excluded.source,language=excluded.language,
        duration=excluded.duration,speakers=excluded.speakers,transcript=excluded.transcript,summary=excluded.summary""",
        (str(job_dir),job_dir.name[:19],job.get("source",""),job.get("language",""),duration,speakers,transcript,summary))
        db.commit()

def reindex(root: Path) -> int:
    init_library(root); count=0
    for job in root.iterdir():
        if job.is_dir() and (job/"job.json").exists() and (job/"original.json").exists():
            index_job(job,root); count+=1
    return count

def search_jobs(root: Path, query: str="") -> list[dict]:
    init_library(root); q=f"%{query.strip()}%"
    with sqlite3.connect(_db(root)) as db:
        db.row_factory=sqlite3.Row
        rows=db.execute("""SELECT job_dir,created,source,language,duration,speakers FROM jobs
        WHERE ?='' OR source LIKE ? OR language LIKE ? OR transcript LIKE ? OR summary LIKE ?
        ORDER BY created DESC""",(query.strip(),q,q,q,q)).fetchall()
    return [dict(r) for r in rows]
