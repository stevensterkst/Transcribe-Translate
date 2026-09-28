from __future__ import annotations
import os
import requests
from .text import chunk_text

class TranscriptQuery:
    def __init__(self, ollama_url: str, ollama_model: str, progress=print):
        self.ollama_url=ollama_url.rstrip("/")
        self.ollama_model=ollama_model
        self.progress=progress

    def ask_ollama(self, context: str, question: str, language: str) -> str:
        parts=chunk_text(context, size=9000)
        evidence=[]
        for i,part in enumerate(parts,1):
            self.progress(f"Local query evidence {i}/{len(parts)} [{self.ollama_model}]")
            r=requests.post(f"{self.ollama_url}/api/chat",json={"model":self.ollama_model,
                "messages":[{"role":"user","content":f"Answer ONLY from this transcript excerpt. Preserve timestamps and speaker labels. If insufficient, say so.\n\nQUESTION:\n{question}\n\nEXCERPT:\n{part}"}],
                "stream":False,"options":{"temperature":0}},timeout=3600)
            r.raise_for_status()
            evidence.append(str(r.json().get("message",{}).get("content","")).strip())
        prompt=f"Answer the question in {language} using ONLY these evidence passages from one recording. State uncertainty or conflicting evidence. Include supporting timestamps where available. Do not invent.\n\nQUESTION:\n{question}\n\nEVIDENCE:\n\n---\n"+ "\n---\n".join(evidence)
        r=requests.post(f"{self.ollama_url}/api/chat",json={"model":self.ollama_model,"messages":[{"role":"user","content":prompt}],"stream":False,"options":{"temperature":0}},timeout=3600)
        r.raise_for_status()
        answer=str(r.json().get("message",{}).get("content","")).strip()
        if not answer: raise RuntimeError("Ollama returned an empty query answer.")
        return answer

    def ask_openai(self, context: str, question: str, language: str, model: str="gpt-5.6-luna") -> str:
        key=os.environ.get("OPENAI_API_KEY","").strip()
        if not key: raise RuntimeError("OPENAI_API_KEY is not set. OpenAI querying is optional and is never used automatically.")
        parts=chunk_text(context, size=18000); evidence=[]
        for i,part in enumerate(parts,1):
            self.progress(f"OpenAI query evidence {i}/{len(parts)} [{model}]")
            prompt=f"Answer ONLY from this transcript excerpt. Preserve timestamps and speaker labels. If insufficient, say so.\n\nQUESTION:\n{question}\n\nEXCERPT:\n{part}"
            r=requests.post("https://api.openai.com/v1/responses",headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},json={"model":model,"input":prompt,"store":False},timeout=3600)
            if r.status_code>=400: raise RuntimeError(f"OpenAI request failed ({r.status_code}): {r.text[:2000]}")
            d=r.json(); evidence.append(str(d.get("output_text","")).strip())
        prompt=f"Answer this transcript-grounded question in {language}. Use ONLY the evidence below. Give the answer, then supporting timestamps where available. State uncertainty/conflict. Do not invent.\n\nQUESTION:\n{question}\n\nEVIDENCE:\n\n---\n"+"\n---\n".join(evidence)
        r=requests.post("https://api.openai.com/v1/responses",headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},json={"model":model,"input":prompt,"store":False},timeout=3600)
        if r.status_code>=400: raise RuntimeError(f"OpenAI request failed ({r.status_code}): {r.text[:2000]}")
        answer=str(r.json().get("output_text","")).strip()
        if not answer: raise RuntimeError("OpenAI returned an empty query answer.")
        return answer
