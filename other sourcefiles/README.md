# SS Transcribe-Translate

Windows-native, local-first transcription, summarisation, translation and source-grounded analysis.

## Product order — this is intentional

The **source-language transcript is the primary product**.

The **source-language summary is also a primary/basic feature** and is generated directly from that original-language transcript.

The **English summary is NOT an independent summary**. It is only a translation of the source-language summary.

A **full transcript translation is optional**, independent of the summaries, and can target any language supported by the selected Ollama model.

The source-grounded meeting/evidence analysis is an additional layer downstream of the original transcript. It must never replace or rewrite the primary source transcript.

## Pipeline

1. Local media file or YouTube URL
2. Existing FFmpeg extracts 16 kHz mono audio
3. faster-whisper + CTranslate2 performs local speech-to-text
4. Original-language transcript is saved with segment timestamps
5. Source-language summary is generated directly from the source transcript
6. English summary is translated from the source-language summary
7. Source-grounded analysis optionally extracts topics/timeline, people mentioned, proposals, decisions, votes, questions/objections, action items, evidence, procedural/governance flags, contradictions and knowledge-management tags
8. Full transcript translation is optionally performed into the user's target language

## Local/free boundary

The application runtime makes **no OpenAI API calls and requires no paid API token**.

OpenAI remains part of the wider SS development/knowledge-management ecosystem and may be used outside this application for coding, SDK work, orchestration or SS-brain functions. That is deliberately separate from this application's runtime.

The app's transcription is local via faster-whisper/CTranslate2. Text summarisation, analysis and optional translation are local via Ollama.

## Ollama model selection

The GUI calls Ollama's local `/api/tags` endpoint and exposes **every model currently installed**, rather than hard-coding Qwen or another model.

The currently known PC models are:

- `llama3.2:1b` — fast/lightweight
- `gemma3:1b` — fast/lightweight
- `qwen3:1.7b` — balanced multilingual/speed option
- `phi4-mini:3.8b` — stronger starting choice for careful translation/analysis, with slower CPU generation

The GUI gives a recommendation but never silently changes the user's selection. The recommendation is a heuristic, not a benchmark claim.

## Outputs

Primary outputs:

- `original.txt` — complete source-language transcript
- `original.json` — transcript + segment timestamps
- `original.srt` — timestamped source transcript
- `original.vtt` — timestamped source transcript
- `source_summary.md` — source-language summary
- `english_summary.md` — English translation of the source summary

Additional output when analysis is enabled:

- `analysis.md` — source-grounded analysis including timeline, topics, decisions, proposals, votes, action items, evidence matrix, procedural/governance review points, contradictions and knowledge-management tags

Additional output when full translation is enabled:

- `translation.txt` — complete source transcript translated to the selected target language

Metadata:

- `job.json` — model, language, provenance and zero-paid-API assertion
- `output_manifest.json` — produced outputs

## Evidence rules

The analysis layer is deliberately conservative:

- It uses only the original-language transcript.
- It does not claim speaker diarization unless the transcript itself supports speaker identification.
- It does not invent votes, motives, legal conclusions, dates, amounts or decisions.
- It distinguishes explicit transcript facts from analytical flags and reports insufficient evidence when necessary.

## Existing FFmpeg / standalone yt-dlp

The application does not install, replace or modify the user's existing FFmpeg or standalone yt-dlp.

For YouTube input, the application first looks for an existing standalone Windows `yt-dlp.exe` in PATH, the project's `tools` directory, the Python Scripts locations, and other common user locations. It does not move or install it. If no standalone executable exists but the already-installed Python `yt-dlp` package is available, the application uses that package directly as a fallback. A GUI Browse button remains available for an executable at an arbitrary location. For current YouTube extraction, full support may also require yt-dlp's EJS component and a supported JavaScript runtime; the application reports that prerequisite state instead of pretending that yt-dlp alone guarantees full YouTube support.

## Obsolete Whisper/Torch cleanup

The application itself requires neither WhisperX nor Torch.

Do **not** run the cleanup blindly: first run the read-only audit supplied in the working instructions and verify package ownership and disk usage. The cleanup script is intentionally restricted to obsolete `openai-whisper` and `torch`; it does not touch Python, FFmpeg, standalone yt-dlp, Hugging Face cache, or SS project files.

## Verification

Repository inspection verifies the architecture and source-first data flow.

Verification status after the 2026-09-22 audit:
- Architecture/source-code checks: implemented.
- Ollama local endpoint and all four installed models: verified on this PC.
- faster-whisper + CTranslate2 imports: verified on this PC.
- Existing FFmpeg executable: verified on this PC.
- A real end-to-end run was attempted, but the automatically selected 4.54-second browser-extension cache MP4 produced zero transcript segments; the old verifier incorrectly continued into Ollama stages and only failed when it found an empty SRT.
- The verifier is now strict: it requires an explicit user-selected recording, treats zero ASR segments as a hard failure, and checks transcript text/segments before declaring success.
- The ASR now retries once with VAD disabled when the normal VAD pass produces zero segments.
- The application's FFmpeg discovery now also searches the existing C:\Program Files\FFmpeg* installation when FFmpeg is not on PATH.
- Obsolete Whisper/Torch cleanup is no longer automatic in finish-local.ps1.
- Speaker diarization remains optional and is NOT claimed as verified: sherpa-onnx and compatible local ONNX speaker models were not present in the audited PC state.

No code inspection can honestly substitute for the final real run on a genuine recording containing speech.


## Requirements audit — 2026-09-22

The application is intentionally source-first and local at runtime:

- **Primary:** original/source-language transcript with timestamps.
- **Primary:** source-language summary generated from the original transcript.
- **English summary:** translation of that source summary, not a second independent summary.
- **Optional:** full transcript translation to a selected target language.
- **Optional:** source-grounded analysis, transcript search/top terms, and transcript-grounded Q&A.
- **Languages:** source language can be auto-detected or entered as a Whisper language code; analysis/Q&A/translation outputs are independently selectable.
- **ASR:** faster-whisper + CTranslate2; no WhisperX/Torch runtime.
- **Ollama:** every installed local model is exposed in the GUI; the recommendation is only a heuristic and never overrides the user's selection.
- **YouTube:** existing yt-dlp executable is preferred; the already-installed Python yt-dlp package is a non-installing fallback. Existing FFmpeg is used for merging/extraction.
- **No paid OpenAI API calls:** the application runtime does not call OpenAI APIs.
- **No automatic destructive cleanup:** obsolete package cleanup requires an explicit switch.
- **Diarization:** local ONNX-only design; not claimed operational until sherpa-onnx and compatible model files are actually present.
- **Provenance:** input SHA-256 and job metadata are recorded.
- **Exports:** TXT, JSON, SRT, VTT, Markdown summaries/analysis and optional translation/Q&A.

Features identified during competitor review but deliberately not treated as silently completed include watch-folder automation, a persistent searchable job library, synchronized media playback, and multi-file batch orchestration. Those require separate product work; the repository must not claim them as implemented merely because related concepts exist.

## Final feature set

The current application includes:

- Windows GUI with local file and YouTube input.
- faster-whisper/CTranslate2 local transcription with automatic source-language detection, word timestamps and vocabulary/hotwords.
- Source-language transcript and source-language summary as the primary outputs.
- English summary as a translation of the source summary.
- Optional full transcript translation to a user-selected language.
- Ollama model discovery and selection for every locally installed model.
- Source-grounded analysis, exact transcript search, language-neutral top-term counts, and transcript-grounded Q&A.
- Offline Sherpa-ONNX speaker diarization with local Pyannote segmentation and 3D-Speaker embeddings; no Torch, WhisperX or cloud diarization.
- Batch-folder processing.
- Hash-based watch-folder processing.
- Persistent SQLite local library with transcript/summary search.
- Synchronized HTML media player with timestamp navigation and active transcript highlighting.
- TXT, Markdown, CSV, JSON, SRT and VTT transcript exports plus structured summaries, analysis, Q&A and manifests.
- SHA-256 input provenance and timestamped job directories, so repeated transcriptions are retained as separate versions rather than overwritten.
- Existing FFmpeg and existing yt-dlp are reused. YouTube also supports the already-installed Python yt-dlp package; yt-dlp[default] supplies the current EJS scripts and the setup installs local Deno for the required JavaScript runtime.
- No paid OpenAI API calls from this application.

### One-pass Windows setup

Run:

    powershell -ExecutionPolicy Bypass -File .\finish-local.ps1

It installs the local Python dependencies, installs a local Deno runtime, downloads the official Sherpa-ONNX diarization models, configures them, builds the Windows GUI executable, opens a file picker for a real verification recording, runs all Ollama smoke tests, runs the real pipeline, and verifies the generated outputs.

It never runs the obsolete Whisper/Torch cleanup unless -CleanupObsoleteWhisper is explicitly supplied.

The packaged executable is produced at:

    dist\SS-Transcribe-Translate\SS-Transcribe-Translate.exe
