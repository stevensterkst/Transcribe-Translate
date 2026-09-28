from __future__ import annotations

import html
import json
import re
import xml.etree.ElementTree as ET
from typing import Any

import requests


def _clean_caption_text(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", "", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _timestamp(value: str) -> float:
    value = value.strip().replace(",", ".")
    parts = value.split(":")
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    return float(parts[0])


def _parse_vtt(text: str) -> list[dict[str, Any]]:
    cues: list[dict[str, Any]] = []
    blocks = re.split(r"\n\s*\n", text.replace("\r", ""))
    for block in blocks:
        lines = [x.strip("\ufeff") for x in block.split("\n") if x.strip()]
        timing_index = next((i for i, x in enumerate(lines) if "-->" in x), None)
        if timing_index is None:
            continue
        timing = lines[timing_index]
        try:
            left, right = [x.strip().split()[0] for x in timing.split("-->", 1)]
            start, end = _timestamp(left), _timestamp(right)
        except (ValueError, IndexError):
            continue
        body = " ".join(_clean_caption_text(x) for x in lines[timing_index + 1:])
        if body and end >= start:
            cues.append({"start": start, "end": end, "text": body})
    return cues


def _parse_srv3(text: str) -> list[dict[str, Any]]:
    root = ET.fromstring(text)
    cues: list[dict[str, Any]] = []
    for p in root.iter():
        if p.tag.rsplit("}", 1)[-1].lower() != "p":
            continue
        try:
            start_ms = float(p.attrib.get("t", "0"))
            duration_ms = float(p.attrib.get("d", "0"))
        except ValueError:
            continue
        pieces: list[str] = []
        for node in p.iter():
            if node.text:
                pieces.append(node.text)
        body = _clean_caption_text("".join(pieces))
        if not body:
            continue
        start = start_ms / 1000.0
        end = start + max(0.0, duration_ms / 1000.0)
        if end <= start:
            end = start + 2.0
        cues.append({"start": start, "end": end, "text": body})
    return cues


def _parse_json3(text: str) -> list[dict[str, Any]]:
    data = json.loads(text)
    cues: list[dict[str, Any]] = []
    for event in data.get("events", []):
        if not isinstance(event, dict) or "tStartMs" not in event:
            continue
        try:
            start = float(event.get("tStartMs", 0)) / 1000.0
            duration = float(event.get("dDurationMs", 0)) / 1000.0
        except (TypeError, ValueError):
            continue
        parts: list[str] = []
        for seg in event.get("segs") or []:
            if isinstance(seg, dict):
                parts.append(str(seg.get("utf8", "")))
        body = _clean_caption_text("".join(parts))
        if not body:
            continue
        end = start + max(duration, 2.0)
        cues.append({"start": start, "end": end, "text": body})
    return cues


def _ttml_time(value: str, frame_rate: float = 30.0) -> float:
    value = value.strip()
    if re.fullmatch(r"\d+(?:\.\d+)?s", value):
        return float(value[:-1])
    if re.fullmatch(r"\d+(?:\.\d+)?ms", value):
        return float(value[:-2]) / 1000.0
    if re.fullmatch(r"\d+(?:\.\d+)?f", value):
        return float(value[:-1]) / frame_rate
    if re.fullmatch(r"\d+(?:\.\d+)?t", value):
        return float(value[:-1]) / 1.0
    return _timestamp(value)


def _parse_ttml(text: str) -> list[dict[str, Any]]:
    root = ET.fromstring(text)
    cues: list[dict[str, Any]] = []
    frame_rate = 30.0
    for key in ("frameRate", "{http://www.w3.org/ns/ttml#parameter}frameRate"):
        raw = root.attrib.get(key)
        if raw:
            try:
                frame_rate = float(raw)
            except ValueError:
                pass
    for node in root.iter():
        if node.tag.rsplit("}", 1)[-1].lower() != "p":
            continue
        begin = node.attrib.get("begin")
        if not begin:
            continue
        try:
            start = _ttml_time(begin, frame_rate)
            if node.attrib.get("end"):
                end = _ttml_time(node.attrib["end"], frame_rate)
            elif node.attrib.get("dur"):
                end = start + _ttml_time(node.attrib["dur"], frame_rate)
            else:
                end = start + 2.0
        except ValueError:
            continue
        pieces: list[str] = []
        for child in node.iter():
            if child.text:
                pieces.append(child.text)
        body = _clean_caption_text(" ".join(pieces))
        if body and end >= start:
            cues.append({"start": start, "end": end, "text": body})
    return cues


def _parse_caption(text: str, ext: str) -> list[dict[str, Any]]:
    ext = ext.lower().lstrip(".")
    if ext == "vtt":
        return _parse_vtt(text)
    if ext == "srv3":
        return _parse_srv3(text)
    if ext == "ttml":
        return _parse_ttml(text)
    if ext == "json3":
        return _parse_json3(text)
    raise ValueError(f"Unsupported caption format: {ext}")


def _choose_track(info: dict, requested_language: str) -> tuple[str, dict] | None:
    requested = (requested_language or "auto").lower().strip()
    tracks: list[tuple[str, dict, int]] = []
    for source_name, mapping in (
        ("manual", info.get("subtitles") or {}),
        ("automatic", info.get("automatic_captions") or {}),
    ):
        for lang, entries in mapping.items():
            if not entries:
                continue
            score = 0
            ll = lang.lower()
            if requested != "auto":
                if ll == requested:
                    score += 100
                elif ll.startswith(requested + "-") or ll.startswith(requested):
                    score += 80
            if source_name == "manual":
                score += 20
            if ll.startswith("en"):
                score += 5
            for entry in entries:
                ext = str(entry.get("ext", "")).lower()
                if entry.get("url") and ext in {"vtt", "srv3", "ttml", "json3"}:
                    tracks.append((lang, entry, score))
    if not tracks:
        return None
    tracks.sort(key=lambda x: x[2], reverse=True)
    return tracks[0][0], tracks[0][1]


def _deduplicate_cues(cues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    last_text = None
    for cue in sorted(cues, key=lambda x: (float(x["start"]), float(x["end"]))):
        text = cue["text"]
        if text == last_text:
            continue
        result.append(cue)
        last_text = text
    return result


def scrape_transcript(source: str, requested_language: str = "auto", progress=print, range_mode: str = "full", range_value: float = 0.0):
    """Return a Transcript-like object from remote captions without downloading media."""
    if not source.lower().startswith(("http://", "https://")):
        return None
    try:
        import yt_dlp
        from .asr import Segment, Transcript

        progress("Caption-first probe: checking remote transcript/caption tracks before downloading media...")
        opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
            "extract_flat": False,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(source, download=False)
        chosen = _choose_track(info, requested_language)
        mode = (range_mode or "full").lower().strip()
        value = float(range_value or 0)
        if mode not in {"full", "minutes", "percent"}:
            raise ValueError("range_mode must be full, minutes, or percent")
        limit = None
        if value > 0 and mode == "minutes":
            limit = value * 60.0
        elif value > 0 and mode == "percent":
            duration = float(info.get("duration") or 0)
            if duration > 0:
                limit = duration * min(value, 100.0) / 100.0
        if not chosen:
            progress("No usable remote caption track found; falling back to local audio transcription.")
            return None

        lang, track = chosen
        ext = str(track.get("ext", "")).lower()
        response = requests.get(track["url"], timeout=60)
        response.raise_for_status()
        cues = _parse_caption(response.text, ext)
        if not cues:
            progress(f"Remote {ext} caption track was found but contained no usable cues; falling back to audio transcription.")
            return None

        dedup = _deduplicate_cues(cues)
        if limit is not None:
            dedup = [c for c in dedup if float(c["start"]) < limit]
            dedup = [dict(c, end=min(float(c["end"]), limit)) for c in dedup]
            progress(f"Remote transcript limited to first {limit/60:.2f} minutes.")
        segments = [Segment(float(c["start"]), float(c["end"]), c["text"]) for c in dedup]
        text = "\n".join(s.text for s in segments)
        progress(f"REMOTE TRANSCRIPT USED: {lang} {ext} captions; media download and Whisper were skipped.")
        return Transcript(
            text=text,
            segments=segments,
            language=lang,
            backend="remote-captions",
            model=ext,
        )
    except Exception as exc:
        progress(f"Caption-first probe unavailable ({exc}); falling back to local audio transcription.")
        return None
