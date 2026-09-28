from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import threading
import uuid


class _Handler(BaseHTTPRequestHandler):
    server_version = "SS-Transcribe-Translate-Bridge/0.1"

    def _reply(self, code: int, payload: dict):
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-SS-Bridge-Token")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self):
        self._reply(204, {})

    def do_POST(self):
        bridge = self.server.bridge
        token = self.headers.get("X-SS-Bridge-Token", "")
        if bridge.token and token != bridge.token:
            self._reply(401, {"ok": False, "error": "Invalid bridge token"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        if self.path == "/transcript":
            try:
                payload = json.loads(body.decode("utf-8"))
            except Exception as exc:
                self._reply(400, {"ok": False, "error": f"Invalid JSON: {exc}"})
                return
            target = bridge.inbox / f"transcript-{uuid.uuid4().hex}.json"
            target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            bridge.progress(f"BROWSER TRANSCRIPT RECEIVED: {target}")
            self._reply(200, {"ok": True, "path": str(target)})
            return
        if self.path == "/audio":
            target = bridge.inbox / f"browser-audio-{uuid.uuid4().hex}.webm"
            target.write_bytes(body)
            bridge.progress(f"BROWSER AUDIO RECEIVED: {target}")
            self._reply(200, {"ok": True, "path": str(target)})
            return
        self._reply(404, {"ok": False, "error": "Unknown bridge endpoint"})

    def log_message(self, fmt, *args):
        return


class BrowserBridge:
    def __init__(self, inbox: Path, token: str = "", progress=print, host: str = "127.0.0.1", port: int = 8766):
        self.inbox = Path(inbox)
        self.token = token.strip()
        self.progress = progress
        self.host = host
        self.port = port
        self.server = None
        self.thread = None

    def start(self):
        if self.server is not None:
            return self
        self.inbox.mkdir(parents=True, exist_ok=True)
        self.server = ThreadingHTTPServer((self.host, self.port), _Handler)
        self.server.bridge = self
        self.thread = threading.Thread(target=self.server.serve_forever, name="ss-browser-bridge", daemon=True)
        self.thread.start()
        self.progress(f"Browser bridge listening on http://{self.host}:{self.port}")
        return self

    def stop(self):
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
