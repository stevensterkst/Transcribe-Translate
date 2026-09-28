from __future__ import annotations
from collections import Counter
import re
from .asr import Transcript

STOPWORDS = set("""
a an the and or but if then than of to in on at by for from with without is are was were be been
de la el los las un una y o que en por para con sin es son fue fueron del al
le la les des et ou un une de du dans pour avec sans est sont
der die das ein eine und oder von zu im in mit ohne ist sind
""".split())

def search_transcript(transcript: Transcript, query: str) -> list[dict]:
    query = query.strip()
    if not query:
        return []
    q = query.casefold()
    hits = []
    for segment in transcript.segments:
        if q in segment.text.casefold():
            hits.append({"start": segment.start, "end": segment.end, "text": segment.text, "query": query})
    return hits

def top_terms(transcript: Transcript, limit: int = 30) -> list[dict]:
    text = transcript.text.casefold()
    # Unicode-letter tokenisation: do not restrict analysis to Latin/Cyrillic/CJK only.
    # This covers Arabic, Hebrew, Greek, Korean and other Unicode scripts without another dependency.
    words = re.findall(r"[^\W\d_]{3,}", text, flags=re.UNICODE)
    counts = Counter(w for w in words if w not in STOPWORDS and not w.isdigit())
    return [{"term": term, "count": count} for term, count in counts.most_common(max(1, limit))]

def build_search_report(transcript: Transcript, query: str, limit: int) -> dict:
    hits = search_transcript(transcript, query)
    return {
        "language": transcript.language,
        "query": query,
        "match_count": len(hits),
        "matches": hits,
        "top_terms": top_terms(transcript, limit),
    }
