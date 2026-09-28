from __future__ import annotations

from pathlib import Path
import webbrowser


SUMMARY_INSTRUCTIONS = """You are producing the PRIMARY SOURCE-LANGUAGE SUMMARY of a spoken transcript.

Rules:
- Write in the transcript's source language.
- Use ONLY information explicitly present in the transcript.
- Do not translate the transcript.
- Do not invent names, dates, decisions, votes, deadlines or legal conclusions.
- Do not use a generic meeting/legal template.
- Do not repeat the same fact under multiple headings.
- Preserve important names, organisations, dates, amounts, requests, arguments, objections,
  questions, practical next steps and unresolved points when they are actually stated.
- For a short recording, keep the summary short but information-dense.
- Distinguish uncertainty or misunderstanding where the transcript is uncertain.
- Return ONLY the summary.

SOURCE LANGUAGE: {language}

TRANSCRIPT:
{transcript}
"""


def build_summary_prompt(transcript: str, language: str) -> str:
    return SUMMARY_INSTRUCTIONS.format(language=language, transcript=transcript.strip())


def write_browser_prompt(job_dir: Path, transcript: str, language: str) -> Path:
    path = job_dir / "CLOUD_SUMMARY_PROMPT.md"
    prompt = build_summary_prompt(transcript, language)
    path.write_text(
        "# Browser cloud-summary prompt\n\n"
        "This prompt is intentionally user-controlled: the desktop app does not log in to "
        "or automate a consumer AI website.\n\n"
        "## Prompt\n\n" + prompt + "\n",
        encoding="utf-8",
    )
    return path


def open_chatgpt() -> None:
    webbrowser.open("https://chatgpt.com/")


def open_claude() -> None:
    webbrowser.open("https://claude.ai/")


def save_cloud_summary(job_dir: Path, summary: str, filename: str = "source_summary_cloud.md") -> Path:
    value = summary.strip()
    if len(value) < 80:
        raise ValueError("Cloud summary is too short to accept as a primary summary.")
    path = job_dir / filename
    path.write_text("# Source-language cloud summary\n\n" + value + "\n", encoding="utf-8")
    return path
