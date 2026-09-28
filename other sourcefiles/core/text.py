from __future__ import annotations
from typing import Callable
import requests

Progress = Callable[[str], None]

def chunk_text(text: str, size: int = 18000) -> list[str]:
    text = text.strip()
    if not text:
        return [""]
    if len(text) <= size:
        return [text]
    parts: list[str] = []
    current: list[str] = []
    length = 0
    for paragraph in text.split("\n"):
        extra = len(paragraph) + 1
        if current and length + extra > size:
            parts.append("\n".join(current))
            current, length = [], 0
        current.append(paragraph)
        length += extra
    if current:
        parts.append("\n".join(current))
    return parts

MODEL_HINTS = {
    "phi4-mini": ("precision", "Best starting choice among the four currently reported PC models for careful translation/analysis; expect slower CPU generation."),
    "qwen3": ("balanced", "Good speed/multilingual compromise; use when Phi is too slow."),
    "llama3.2": ("fast", "Small and fast; useful when turnaround matters more than maximum text precision."),
    "gemma3": ("fast", "Small and fast; useful for quick summaries and lightweight translation."),
}

def model_advice(model: str) -> tuple[str, str]:
    name = model.lower()
    for key, value in MODEL_HINTS.items():
        if key in name:
            return value
    return ("unknown", "No preset recommendation; benchmark this installed model on your material before relying on it.")

class OllamaTextProvider:
    def __init__(self, url: str, model: str, progress: Progress = print):
        self.url = url.rstrip("/")
        self.model = model
        self.progress = progress

    def list_models(self) -> list[str]:
        try:
            response = requests.get(f"{self.url}/api/tags", timeout=10)
            response.raise_for_status()
            return [str(m.get("name")) for m in response.json().get("models", []) if m.get("name")]
        except requests.RequestException as exc:
            raise RuntimeError(f"Cannot reach Ollama at {self.url}: {exc}") from exc

    def _call(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0},
        }
        if "qwen3" in self.model.lower():
            payload["think"] = False
        response = requests.post(
            f"{self.url}/api/chat",
            json=payload,
            timeout=3600,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"Ollama request failed ({response.status_code}): {response.text[:3000]}")
        content = str(response.json().get("message", {}).get("content", "")).strip()
        if not content:
            raise RuntimeError("Ollama returned an empty response.")
        return content

    def _source_chunk_summary(self, chunk: str, source_language: str, index: int, total: int) -> str:
        self.progress(f"Source-summary chunk {index}/{total} [{self.model}]")
        return self._call(
            f"Summarize this portion of a {source_language} transcript in {source_language}. "
            "Keep every material fact, argument, proposal, decision, objection, question, name, date, "
            "amount, condition, vote, action item, deadline, uncertainty and unresolved issue that occurs "
            "in this portion. Do not invent or infer. This is an intermediate source-language summary and "
            "will be consolidated later.\n\n" + chunk
        )

    def summarize_source(self, transcript: str, source_language: str) -> str:
        parts = chunk_text(transcript)
        if len(parts) == 1:
            self.progress(f"Source-language summary: {source_language} [{self.model}]")
            return self._call(
                f"Produce a comprehensive summary in {source_language} of the transcript below. "
                "This is the PRIMARY summary. Base it only on the transcript. Preserve all material facts, "
                "important arguments, decisions, proposals, objections, questions, named people or organisations, "
                "dates, amounts, conditions, votes or voting positions when stated, action items, deadlines, "
                "uncertainties and unresolved issues. Do not invent, infer, or silently omit material information. "
                "Keep the structure useful for later knowledge-management and legal/meeting review.\n\n" + transcript
            )
        summaries = [self._source_chunk_summary(part, source_language, i, len(parts)) for i, part in enumerate(parts, 1)]
        self.progress(f"Consolidating {len(summaries)} source-summary chunks [{self.model}]")
        return self._call(
            f"Consolidate these intermediate summaries into one comprehensive summary in {source_language}. "
            "Use only their contents. Preserve material facts, arguments, decisions, proposals, objections, "
            "questions, names, dates, amounts, conditions, votes, action items, deadlines, uncertainties and "
            "unresolved issues. Do not invent, infer or silently omit. Remove duplication while retaining distinct "
            "facts.\n\n" + "\n\n---\n\n".join(summaries)
        )

    def analyze_source(self, timestamped_transcript: str, source_language: str) -> str:
        parts = chunk_text(timestamped_transcript, size=14000)
        analyses = []
        for i, part in enumerate(parts, 1):
            self.progress(f"Source-grounded analysis chunk {i}/{len(parts)} [{self.model}]")
            analyses.append(self._call(
                f"""Analyse this portion of a timestamped {source_language} transcript in {source_language}.
Extract only evidence explicitly present here: topics/timeline, people mentioned, proposals, decisions,
votes, questions/objections, unresolved issues, action items/deadlines, evidence, procedural/governance
review points, contradictions and knowledge-management entities. Preserve timestamps. Never invent.
Mark insufficient evidence. This is an intermediate analysis, not a legal conclusion.

TRANSCRIPT:
{part}"""
            ))
        self.progress(f"Consolidating source-grounded analysis [{self.model}]")
        return self._call(
            f"""Consolidate the following source-grounded analyses in {source_language}.
Produce Markdown sections: Executive overview; Topic timeline; People/speakers evidenced by transcript;
Motions/proposals; Decisions; Votes/stated positions; Questions/objections/unresolved issues; Action
items/deadlines; Evidence matrix with timestamps; Procedural/governance review points; Legal/governance
issues for human review (not conclusions); Contradictions; Knowledge-management tags/entities.
Use only the supplied analyses. Do not invent or turn uncertainty into certainty.

{chr(10).join(analyses)}"""
        )

    def ask_transcript(self, transcript_context: str, question: str, answer_language: str) -> str:
        parts = chunk_text(transcript_context, size=9000)
        evidence = []
        for i, part in enumerate(parts, 1):
            self.progress(f"Q&A evidence pass {i}/{len(parts)} [{self.model}]")
            evidence.append(self._call(
                f"""Answer the question using ONLY the supplied transcript excerpt.
Return the relevant facts and timestamps/speaker labels present in the excerpt. If the excerpt does not
contain enough evidence, say so. Do not infer missing facts.

QUESTION:
{question}

TRANSCRIPT EXCERPT:
{part}"""
            ))
        return self._call(
            f"""Answer this transcript-grounded question in {answer_language}.
Use ONLY the evidence passages below. Give a concise answer followed by supporting timestamps where available.
Do not invent facts. If evidence conflicts or is insufficient, explicitly state that.
Do not provide legal conclusions merely because the transcript mentions a legal issue.

QUESTION:
{question}

EVIDENCE:
{chr(10).join(evidence)}"""
        )

    def translate(self, text: str, target_language: str, purpose: str = "transcript") -> str:
        outputs = []
        for index, part in enumerate(chunk_text(text), 1):
            self.progress(f"Local {purpose} translation: part {index} -> {target_language} [{self.model}]")
            outputs.append(self._call(
                f"Translate this {purpose} faithfully into {target_language}. Do not summarize. Preserve names, "
                "numbers, dates, legal/voting terminology, uncertainty, negation, speaker meaning and all "
                "substantive details. Do not add commentary.\n\n" + part
            ))
        return "\n\n".join(outputs)

    def translate_summary_to_english(self, source_summary: str, source_language: str) -> str:
        return self.translate(source_summary, "English", purpose=f"{source_language} summary")
