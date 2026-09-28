from __future__ import annotations
from pathlib import Path
import os
import shutil
import subprocess
import sys
from urllib.parse import urlparse

WINDOWS_NO_CONSOLE = {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}

VIDEO_EXTS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".mp3", ".m4a", ".wav", ".flac", ".ogg"}

def is_url(source: str) -> bool:
    try:
        return urlparse(source).scheme in {"http", "https"}
    except Exception:
        return False

def find_ffmpeg() -> str:
    found = shutil.which("ffmpeg")
    if found:
        return found
    for root in [os.environ.get("ProgramFiles", r"C:\Program Files")]:
        for candidate in Path(root).glob("FFmpeg*/bin/ffmpeg.exe"):
            if candidate.is_file():
                return str(candidate)
    raise RuntimeError(
        "FFmpeg was not found on PATH or under C:\\Program Files\\FFmpeg*\\bin. "
        "The application does not install or replace FFmpeg."
    )

def find_ytdlp(configured: str = "", progress=print) -> str:
    candidates: list[Path] = []

    def add(value: str | Path):
        if not value:
            return
        p = Path(os.path.expandvars(os.path.expanduser(str(value))))
        if p not in candidates:
            candidates.append(p)

    add(configured)
    add(os.environ.get("YTDLP_PATH", ""))
    add(Path(__file__).resolve().parents[1] / "tools" / "yt-dlp.exe")

    for command in ("yt-dlp.exe", "yt-dlp"):
        found = shutil.which(command)
        if found:
            add(found)

    home = Path.home()
    local = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
    roaming = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
    common = [
        home / "Downloads" / "yt-dlp.exe",
        home / "Desktop" / "yt-dlp.exe",
        home / "Documents" / "yt-dlp.exe",
        home / "AppData" / "Roaming" / "Python" / "Python313" / "Scripts" / "yt-dlp.exe",
        home / "AppData" / "Roaming" / "Python" / "yt-transcript-tool" / "yt-dlp.exe",
        Path(sys.executable).resolve().parent / "yt-dlp.exe",
        local / "Programs" / "Python" / "Python313" / "Scripts" / "yt-dlp.exe",
        local / "yt-dlp.exe",
        local / "Programs" / "yt-dlp" / "yt-dlp.exe",
        local / "Programs" / "yt-dlp.exe",
        roaming / "yt-dlp" / "yt-dlp.exe",
        Path(r"C:\yt-dlp\yt-dlp.exe"),
    ]
    for p in common:
        add(p)

    for candidate in candidates:
        if candidate.is_file():
            return str(candidate.resolve())

    # Do not recursively scan the whole profile: an arbitrary profile scan can hit synced/cloud trees and become slow.\n
    raise FileNotFoundError(
        "No existing yt-dlp.exe was found. The application did not install or move one. "
        "Use Browse yt-dlp… once to select your existing standalone executable."
    )

def find_ytdlp_command(configured: str = "", progress=print) -> list[str]:
    try:
        return [find_ytdlp(configured, progress)]
    except FileNotFoundError:
        # The audited PC already has the yt-dlp Python package installed.
        # Use it without installing/updating/removing anything.
        try:
            probe = subprocess.run(
                [sys.executable, "-c", "import yt_dlp; print(yt_dlp.version.__version__)"],
                capture_output=True, text=True, timeout=15, **WINDOWS_NO_CONSOLE,
            )
            if probe.returncode == 0 and probe.stdout.strip():
                progress("Using existing Python yt-dlp package: " + probe.stdout.strip())
                return [sys.executable, "-m", "yt_dlp"]
        except Exception:
            pass
        raise

def find_js_runtime() -> str | None:
    candidates=[
        shutil.which("deno"),
        str(Path(__file__).resolve().parents[1]/"runtime"/"deno.exe"),
        shutil.which("node"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file() or candidate and shutil.which(candidate):
            return candidate
    return None

def prepare_media(source: str, work: Path, ytdlp_path: str = "") -> Path:
    work.mkdir(parents=True, exist_ok=True)
    if is_url(source):
        ytdlp_command = find_ytdlp_command(ytdlp_path)
        output = work / "%(id)s.%(ext)s"
        ffmpeg = find_ffmpeg()
        js_runtime = find_js_runtime()
        command = [
            *ytdlp_command, "--no-playlist", "--no-warnings",
            # Transcription does not need the video stream. Download audio only to
            # keep a 2–3 hour job small and avoid a needless video merge/copy.
            "-f", "bestaudio/best",
            "--ffmpeg-location", str(Path(ffmpeg).parent),
            *(["--js-runtimes", f"deno:{js_runtime}"] if js_runtime and Path(js_runtime).name.lower() == "deno.exe" else ["--js-runtimes", f"node:{js_runtime}"] if js_runtime else []),
            "--print", "after_move:filepath",
            "-o", str(output), source,
        ]
        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True, encoding="utf-8", errors="replace", **WINDOWS_NO_CONSOLE)
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or "").strip()
            progress("Primary YouTube format download failed; retrying with a single progressive format.")
            fallback = [
                *ytdlp_command, "--no-playlist", "--no-warnings",
                "-f", "ba/b",
                "--ffmpeg-location", str(Path(ffmpeg).parent),
                "--print", "after_move:filepath",
                "-o", str(output), source,
            ]
            try:
                result = subprocess.run(fallback, check=True, capture_output=True, text=True, encoding="utf-8", errors="replace", **WINDOWS_NO_CONSOLE)
            except subprocess.CalledProcessError as fallback_exc:
                fallback_detail = (fallback_exc.stderr or fallback_exc.stdout or "").strip()
                raise RuntimeError(
                    "yt-dlp failed for both normal and progressive YouTube formats. "
                    + (fallback_detail or detail)[-5000:]
                ) from fallback_exc
        printed = [Path(line.strip().strip('"')) for line in result.stdout.splitlines() if line.strip()]
        media = next((p for p in reversed(printed) if p.is_file() and p.suffix.lower() in VIDEO_EXTS), None)
        if media is None:
            media = next((p for p in sorted(work.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
                          if p.is_file() and p.suffix.lower() in VIDEO_EXTS), None)
        if not media:
            raise RuntimeError("yt-dlp reported success but no supported media file was produced.")
        return media

    media = Path(source).expanduser().resolve()
    if not media.is_file():
        raise FileNotFoundError(media)
    destination = work / media.name
    shutil.copy2(media, destination)
    return destination

def extract_audio(media: Path, destination: Path, max_seconds: float | None = None) -> Path:
    ffmpeg = find_ffmpeg()
    command = [ffmpeg, "-y", "-i", str(media)]
    if max_seconds is not None:
        command += ["-t", f"{max_seconds:.3f}"]
    command += ["-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(destination)]
    subprocess.run(command, check=True, **WINDOWS_NO_CONSOLE)
    if not destination.is_file() or destination.stat().st_size <= 44:
        raise RuntimeError("FFmpeg produced no usable audio track.")
    return destination
