# DeepSeek Review — transcribe-translate @ b81766f

Reviewer: DeepSeek (external reasoning agent)
Date: 2026-09-23
Scope: Read-only inspection of GitHub main at commit b81766f.
Purpose: Hand-off to OpenAI/Codex agent for action. Not a chat transcript.
Rules honored: did not modify repo; findings are file/line references, not claims.
Known limits: could not fetch full contents of diarization.py, text.py
  (tail), captions.py (lines 38–104), query.py, library.py, search.py,
  watch.py, player.py, build-exe.ps1, verify-local.ps1, START-APP.vbs,
  or the complete windows-build.yml. Items marked [UNVERIFIED] require the
  OpenAI agent to confirm on disk before acting.

---

## A. CRITICAL — fix before next release

### A1. `app.py` StringVars ignore persisted config  [VERIFIED]
`App.__init__` loads `initial = load_config(ROOT / "config.json")` but then
constructs these with hardcoded defaults instead of `initial.*`:

- self.ollama_model      = tk.StringVar()                    # should use initial.ollama_model
- self.target            = tk.StringVar(value="English")     # initial.target_language
- self.analysis_language = tk.StringVar(value="source")      # initial.analysis_language
- self.hotwords          = tk.StringVar()                    # initial.hotwords
- self.top_terms         = tk.IntVar(value=30)               # initial.top_terms
- self.translate_transcript = tk.BooleanVar(value=False)     # initial.translate_transcript
- self.qa_language       = tk.StringVar(value="English")     # initial.qa_language

Effect: config.local.json is written but never reflected in the UI on relaunch.
Fix: pass initial.* into every constructor above.

### A2. `config.py` — save/load key mismatch  [UNVERIFIED, HIGH RISK]
`app.py` reads `ROOT / "config.json"`.
`save_local_config` writes `ROOT / "config.local.json"`.
If `load_config` does not merge `config.local.json` on top of `config.json`,
every saved setting is silently dropped. Confirm and fix in `core/config.py`.

### A3. `pipeline.py` aborts the job on optional English-summary failure  [VERIFIED]
Lines ~69–76 raise RuntimeError when `translate_summary_to_english` fails.
Packet §D is explicit: source summary is primary; English summary is optional.
Fix: catch, write a warning row to job.json (`status="partial"`), continue to
analysis/Q&A/outputs. Do not raise.

### A4. `media.py` hardcodes Python 3.13 in the yt-dlp search path  [VERIFIED]
Lines ~24–28 embed:
  .../Python/Python313/Scripts/yt-dlp.exe
Users on 3.11/3.12 fail to locate yt-dlp.
Fix: build the path from `sys.version_info` OR glob
  %APPDATA%/Python/Python3*/Scripts/yt-dlp.exe
and
  %LOCALAPPDATA%/Programs/Python/Python3*/Scripts/yt-dlp.exe
Take the newest match.

### A5. `verify-final.ps1` checks the wrong symbol  [VERIFIED]
Audit greps `core/query.py` for `ask_ollama`.
Runtime uses `provider.ask_transcript(...)` where provider is
`OllamaTextProvider` from `core/text.py`.
Two possibilities — OpenAI agent must pick one:
  (a) delete dead `core/query.py` and update the audit to grep
      `core/text.py` for `ask_transcript`, or
  (b) if `query.py` is live, route `pipeline.py` through it and adjust
      the audit.
Right now the audit passes while the runtime uses a different code path.

---

## B. HIGH — audit and correctness

### B1. `verify-final.ps1` never asserts EXE size or SHA256  [VERIFIED]
Packet §3 Step 11 explicitly demands EXE size + SHA256 in the final report.
The audit stops at source-string checks. Either:
  - extend verify-final.ps1 to hash dist/*.exe, or
  - make windows-build.yml the authoritative gate that produces
    exe-info.txt (path, size, sha256) and uploads it as an artifact.
Confirm windows-build.yml actually does this; current size (870 bytes on
disk per earlier observation) is too small for that whole chain.

### B2. `asr.py` beam_size hardcoded to 1  [VERIFIED]
`_run` sets beam_size=1 (greedy). For a "high-quality" tool this is a
quality regression on accents, numbers, proper nouns.
Fix: default beam_size=5, expose via AppConfig (`asr_beam_size`), plumb to
FasterWhisperASR. Document the speed/quality trade-off in README.

### B3. `asr.py` chunking + VAD-retry claims not visible in code  [UNVERIFIED]
Docstring claims bounded windows + VAD-first retry without VAD on silent
window. `CHUNK_SECONDS = 180` is declared but no chunk loop is visible in
the section I could read; `_collect` always passes vad_filter=True.
Confirm whether transcribe() actually chunks and retries. If not, implement
both, or remove the claim from the docstring.

### B4. TTML frame rate hardcoded to 30  [VERIFIED]
`captions.py` `_ttml_time(value, frame_rate=30.0)`.
Read `ttp:frameRate` from the root `<tt>` element and pass it. PAL (25) and
film (24) tracks are currently mis-timed.

### B5. Unknown languages produce nonsense prompts  [VERIFIED]
`pipeline.py` `LANGUAGE_NAMES` covers 11 languages. For Japanese etc.,
`source_name` falls back to the ISO code ("ja") and the prompt reads
"Summarize this portion of a ja transcript in ja."
Fix: fall back to a phrase like "the source language" and instruct the model
to answer in the transcript's own language.

### B6. `detected_code` may be the literal "auto"  [VERIFIED]
`detected_code = transcript.language or cfg.language`. If Whisper returns
None and cfg.language == "auto", source_name becomes "auto".
Guard with:
  if detected_code in (None, "", "auto"): detected_code = "und"

---

## C. MEDIUM — performance / robustness

### C1. `pipeline.py` runs `build_search_report` unconditionally  [VERIFIED]
Line ~82 runs the report even when cfg.search_query is empty. On long
transcripts this burns CPU before outputs are written.
Gate: if cfg.search_query.strip(): search_report = build_search_report(...)

### C2. `app.py` window geometry breaks on 768p laptops  [VERIFIED]
geometry("1200x1020") + minsize(1040, 900) exceeds 1366x768 screens.
Wrap the form in a ttk.Canvas + vertical Scrollbar, or drop default to
1024x720 and let users resize up.

### C3. `media.py` — full file SHA256 reads the media twice  [VERIFIED]
pipeline computes sha256_file(media) then FFmpeg re-reads the file. On large
downloads this doubles I/O. Consider computing the hash inside the yt-dlp
postprocessor hook, or during FFmpeg input read via pipe.

### C4. `watch_folder` has no concurrency lock  [UNVERIFIED]
If both the watch thread and a manual Start run the same new file, two
run_job calls can race: duplicate output dirs, two ASR models in RAM.
Add a threading.Lock + in-flight set keyed by absolute path.

---

## D. MEDIUM — verification quality

### D1. `verify-final.ps1` is string-match based, not behavioral  [VERIFIED]
Checks like:
  if($asr -notmatch 'BatchedInferencePipeline'){throw ...}
  if($pipeline -notmatch 'finally:'){throw ...}
pass on comments and fail on renames. Recommended replacements:
  - importlib-import core.asr and assert hasattr(FasterWhisperASR,"transcribe")
  - assert faster_whisper.BatchedInferencePipeline importable
  - run a 5-second silent WAV through run_job with a stubbed Ollama and
    assert work/ is deleted afterward

### D2. Audit does not scan requirements.txt for forbidden packages  [VERIFIED]
Source scan covers imports, not requirements. Add:
  $reqBad = Get-Content requirements.txt |
            Select-String '^\s*(torch|openai-whisper|whisperx|torchaudio|pyannote)'
  if($reqBad){ throw "Forbidden runtime dep in requirements.txt: $reqBad" }

### D3. Audit does not assert config.local.json is gitignored  [VERIFIED]
If .gitignore is 45 bytes it likely lacks config.local.json / *.local.json /
output/ / _work/ / *.wav / *.mp3. If the optional OpenAI Q&A key is stored
there, an accidental commit leaks it. Confirm and extend .gitignore.

### D4. requirements.txt uses range pins  [VERIFIED]
faster-whisper>=1.2,<2 etc. For a verified Windows artifact, pin exact
versions or add requirements.lock via pip freeze. The [default] extra on
yt-dlp also drags curl_cffi + brotli into the PyInstaller bundle.
Recommend explicit extras: yt-dlp[default] -> drop, add only what's needed.

### D5. No CI job runs unit tests on push  [VERIFIED]
Repo has ci.yml (431 bytes) and ss-ci.yml (1066 bytes) at root, plus the
windows workflow inside transcribe-translate. A fast Linux job running
  python -m unittest discover -s tests
on push to core/ would catch regressions without waiting for a Windows run.
Confirm which of the three CI files actually runs tests.

### D6. Test coverage gaps  [VERIFIED]
tests/ has only test_captions.py and test_ranges.py. AGENTS.md §4 says
"All business logic must have unit tests." Missing:
  - tests/test_config_roundtrip.py (save_local_config -> load_config)
  - tests/test_pipeline_stub.py (mocked ASR + stubbed Ollama; assert outputs)
  - tests/test_text_provider.py (stub HTTP server for Ollama endpoint)
  - tests/test_media_paths.py (find_ytdlp, find_ffmpeg on temp dirs)

---

## E. LOW — docs / housekeeping

### E1. `transcribe-translate/AGENTS.md` is still the template  [VERIFIED]
§1–§4 still contain placeholders like "[Project Name]", "[e.g., Next.js 15,
TypeScript, Python FastAPI, PostgreSQL]", "/src/components".
The file's own rule states GitHub is the source of truth; a fresh agent
reading it cannot determine stack, dirs, or active task.
Populate with:
  Stack: Python 3.13 + Tkinter + faster-whisper + CTranslate2 + FFmpeg +
         yt-dlp + Ollama + PyInstaller.
  Dirs: core/, tests/, web/, browser-extension/ (planned).
  Active task: browser transcript bridge NOT yet implemented.
  Next action: EXE audit + SHA256 + browser bridge.

### E2. VTT parser may miss cues without blank-line separation  [VERIFIED]
`_parse_vtt` splits on r"\n\s*\n". Some non-YouTube VTTs pack cues
back-to-back. Add a fallback split on the "-->" timing line when the
blank-line split yields zero or one block.

---

## F. Preserve as-is (correct and should not be refactored away)

- requirements.txt correctly excludes torch / openai-whisper / whisperx /
  torchaudio / pyannote. Keep it that way.
- captions.py has distinct parsers per format (vtt, srv3, ttml, json3).
  Do not collapse them back into one path.
- pipeline.py writes the source transcript BEFORE any Ollama call.
  Preserve that ordering — a failed AI stage must never destroy the
  transcription.
- pipeline.py has try/finally with shutil.rmtree(work, ignore_errors=True).
- asr.py RAM detection uses GlobalMemoryStatusEx on Windows with a sane
  fallback. Keep.
- config.py ROOT switches on sys.executable vs __file__ — correct pattern
  for PyInstaller onedir with config.local.json beside the EXE. Keep.
- verify-final.ps1 runs compileall + unittest discover + real import check
  for faster_whisper, ctranslate2, requests, yt_dlp, sherpa_onnx. Keep.
- AGENTS.md (bottom section) correctly records that the browser transcript
  bridge and tab-audio capture are NOT finished. Do not over-claim.

---

## G. Suggested fix order (OpenAI agent)

1.  A2 confirm + fix load_config merge       (core/config.py)
2.  A1 wire initial.* into StringVars        (app.py)
3.  A3 stop aborting on optional EN summary  (core/pipeline.py)
4.  A4 dynamic yt-dlp path glob              (core/media.py)
5.  A5 ask_ollama vs ask_transcript mismatch (verify-final.ps1 or query.py)
6.  B1 audit EXE + SHA256                    (verify-final.ps1 / windows-build.yml)
7.  B2 beam_size configurable                (core/asr.py, core/config.py)
8.  B3 confirm chunking + VAD retry          (core/asr.py lines 43–83)
9.  E1 populate AGENTS.md §1–§4              (transcribe-translate/AGENTS.md)
10. D6 add config + pipeline tests           (tests/)
11. D4 pin versions or add lock file         (requirements.txt)
12. B4 TTML ttp:frameRate                    (core/captions.py)

After each fix: run `pwsh -File ./verify-final.ps1 -SkipExe` locally, then
trigger windows-build.yml and paste the run URL + artifact into the next
hand-off file. Do not mark a fix "done" in chat — mark it done only when
the artifact exists.

---

## H. Reply protocol

OpenAI agent: reply by committing
  transcribe-translate/AGENT-NOTES/openai-response-<new-sha>.md
with a table of the form:

  Item | Status | Commit | Evidence
  A1   | FIXED  | <sha>  | app.py:NN uses initial.ollama_model

and one line per item. Do not reply in chat — chat is not the source of truth.