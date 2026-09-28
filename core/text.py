from __future__ import annotations
import re
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
    def __init__(self, url: str, model: str, progress: Progress = print, num_predict: int = 1024):
        self.url = url.rstrip("/")
        self.model = model
        self.progress = progress
        self.num_predict = max(1024, int(num_predict))
        self.last_response_meta: dict[str, object] = {}

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
            "options": {"temperature": 0, "num_predict": self.num_predict},
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
        data = response.json()
        self.last_response_meta = {"prompt_sha256": __import__("hashlib").sha256(prompt.encode("utf-8")).hexdigest(), "response_token_count": data.get("eval_count"), "prompt_token_count": data.get("prompt_eval_count"), "truncated": bool(data.get("done") is False)}
        content = str(data.get("message", {}).get("content", "")).strip()
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

    @staticmethod
    def _summary_quality_ok(text: str, transcript: str) -> bool:
        value = (text or "").strip()
        if len(value) < 80:
            return False
        lines = [x.strip() for x in value.splitlines() if x.strip()]
        # Reject the characteristic small-model failure seen in testing:
        # one generic sentence repeated under many headings.
        if len(lines) >= 6:
            unique = {x.lower() for x in lines if len(x) > 35}
            if len(unique) <= max(2, len(lines) // 3):
                return False
        # Reject obvious meta/template output rather than a summary of the
        # supplied recording.
        bad = ("voting positions", "voting procedures", "questions and questions",
               "no statement on", "pas de déclaration sur")
        low = value.lower()
        bad_hits = sum(1 for marker in bad if marker in low)
        if bad_hits >= 2:
            return False
        # A summary must have some lexical connection to the transcript.
        source_words = {w for w in re.findall(r"[a-zà-ÿ]{4,}", transcript.lower())}
        summary_words = {w for w in re.findall(r"[a-zà-ÿ]{4,}", value.lower())}
        return len(source_words & summary_words) >= 5

    def _summary_call(self, transcript: str, source_language: str) -> str:
        return self._call(
            f"""You are summarizing an actual spoken {source_language} transcript.
Write a concise but information-dense factual summary in {source_language}.
Use ONLY information explicitly present in the transcript.
Do NOT use a generic meeting/legal template. Do NOT invent sections such as voting,
deadlines or decisions unless the transcript actually contains them.
Do NOT repeat the same fact. Preserve the sequence of the discussion and distinguish
what was said from uncertainty or misunderstanding. Mention important names/terms,
proposals, questions, practical next steps and unresolved points only when evidenced.
For a short recording, produce a short summary rather than padding it.

TRANSCRIPT:
{transcript}"""
        )

    def summarize_source(self, transcript: str, source_language: str) -> str:
        parts = chunk_text(transcript)
        self.progress(f"Source-language summary: {source_language} [{self.model}]")
        if len(parts) == 1:
            result = self._summary_call(transcript, source_language)
        else:
            summaries = [self._source_chunk_summary(part, source_language, i, len(parts)) for i, part in enumerate(parts, 1)]
            self.progress(f"Consolidating {len(summaries)} source-summary chunks [{self.model}]")
            result = self._call(
                f"Consolidate these intermediate summaries into one factual, non-repetitive summary in {source_language}. "
                "Use only their contents. Do not add generic headings or facts not evidenced. Remove duplication "
                "while retaining distinct facts and uncertainties.\n\n" + "\n\n---\n\n".join(summaries)
            )
        if self._summary_quality_ok(result, transcript):
            return result

        # If a small/fast model produces template/repetition garbage, retry with
        # a stronger installed local model. Never silently use a cloud provider.
        try:
            available = self.list_models()
        except Exception:
            available = []
        candidates = ["qwen3:1.7b", "phi4-mini:3.8b"]
        for candidate in candidates:
            if candidate == self.model or candidate not in available:
                continue
            self.progress(f"Summary quality check failed with {self.model}; retrying with local {candidate}.")
            backup = OllamaTextProvider(self.url, candidate, self.progress, self.num_predict)
            retry = backup._summary_call(transcript, source_language)
            if backup._summary_quality_ok(retry, transcript):
                self.progress(f"SUMMARY QUALITY PASS: {candidate}")
                return retry
        raise RuntimeError(
            f"Source summary from {self.model} failed the factual/repetition quality gate. "
            "No acceptable local fallback was available."
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

    def _looks_like_english(self, text: str) -> bool:
        value = " " + text.lower().replace("\n", " ") + " "
        english_markers = {
            " the ", " and ", " of ", " to ", " in ", " is ", " are ",
            " was ", " were ", " that ", " this ", " with ", " for ",
            " from ", " has ", " have ", " on ", " as ", " by ",
            " not ", " but ", " about ", " summary ", " court ",
        }
        french_markers = {
            " le ", " la ", " les ", " des ", " une ", " un ",
            " est ", " sont ", " dans ", " avec ", " pour ", " que ",
            " pas ", " mais ", " je ", " vous ", " ce ", " cette ",
            " du ", " au ", " aux ", " en français ",
        }
        en = sum(value.count(word) for word in english_markers)
        fr = sum(value.count(word) for word in french_markers)
        return en >= 2 and en > fr

    def translate_summary_to_english(self, source_summary: str, source_language: str) -> str:
        self.progress(f"Translating {source_language} summary -> English [{self.model}]")
        prompt = (
            "You are a professional translation engine.\n"
            "OUTPUT LANGUAGE: ENGLISH.\n"
            "The source text may be French, Spanish, Dutch, German, or another language.\n"
            "Translate it into natural, faithful English.\n"
            "OUTPUT ONLY THE ENGLISH TRANSLATION.\n"
            "Do NOT answer the text. Do NOT discuss whether you can translate it.\n"
            "Do NOT produce French or any other source-language text.\n"
            "Do NOT summarize again; translate the supplied summary faithfully.\n\n"
            f"SOURCE LANGUAGE: {source_language}\n\n"
            "SOURCE SUMMARY:\n" + source_summary
        )
        result = self._call(prompt)
        if self._looks_like_english(result):
            return result
        self.progress("English-summary language check failed; retrying with strict English-only instruction.")
        retry = self._call(
            "STRICT TRANSLATION TASK. Write ONLY English. Translate the following "
            f"{source_language} text into English. Never refuse, never explain, never "
            "repeat the source language, and never answer its subject matter.\n\n"
            + source_summary
        )
        if not self._looks_like_english(retry):
            raise RuntimeError(
                "Ollama did not produce an English translation of the source summary. "
                "The transcript and source-language summary have already been saved; "
                "English summary was not accepted because its language could not be verified."
            )
        return retry
