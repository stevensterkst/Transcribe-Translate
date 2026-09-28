from __future__ import annotations
import argparse
import json
from pathlib import Path

MEDIA_EXTS = {".mp4",".mkv",".mov",".avi",".webm",".m4v",".mp3",".m4a",".wav",".flac",".ogg"}

def build_index(output_root: Path) -> list[dict]:
    rows = []
    for job in sorted(output_root.iterdir()) if output_root.exists() else []:
        if not job.is_dir() or job.name.startswith("_"):
            continue
        manifest = job / "job.json"
        transcript = job / "original.txt"
        if not manifest.is_file() or not transcript.is_file():
            continue
        meta = json.loads(manifest.read_text(encoding="utf-8"))
        rows.append({
            "job": job.name,
            "path": str(job.resolve()),
            "source": meta.get("source"),
            "language": meta.get("language"),
            "asr_model": meta.get("asr_model"),
            "text_model": meta.get("text_model"),
            "analysis_language": meta.get("analysis_language"),
            "searchable_text": transcript.read_text(encoding="utf-8")[:20000],
        })
    (output_root / "library-index.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return rows

def search_index(output_root: Path, query: str) -> list[dict]:
    index = output_root / "library-index.json"
    rows = build_index(output_root) if not index.exists() else json.loads(index.read_text(encoding="utf-8"))
    q = query.casefold()
    return [r for r in rows if q in (r.get("searchable_text") or "").casefold()
            or q in str(r.get("source") or "").casefold()
            or q in str(r.get("language") or "").casefold()]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Local searchable SS transcript library")
    parser.add_argument("output", type=Path)
    parser.add_argument("--search", default="")
    args = parser.parse_args()
    results = search_index(args.output, args.search) if args.search else build_index(args.output)
    print(json.dumps(results, ensure_ascii=False, indent=2))
