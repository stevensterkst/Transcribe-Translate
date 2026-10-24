# AGENTS.md — SS Transcribe-Translate

## Source of truth and workflow
- Repository: `stevensterkst/Transcribe-Translate`.
- Default/active integration branch: `master`. Do not assume `main` exists or is authoritative.
- GitHub is the shared source of truth. Inspect the current branch and working tree before changing code.
- Preserve user changes. Never use destructive reset/clean operations or overwrite local edits without explicit approval.
- The application is Windows-native Python/Tkinter with faster-whisper, FFmpeg, yt-dlp and Ollama; packaging uses PyInstaller.
- Do not silently install, update, remove or replace unrelated software on the user's Windows PC.
- Keep changes narrow and add deterministic tests/audit assertions where practical.

## Verification gates
- Run `verify-final.ps1` and the Windows EXE build audit.
- CI source/build success is not an end-to-end real-media result.
- Do not claim the application is fully verified until `verify-local.ps1` passes with an explicit real media file on the target Windows machine.
- Important unresolved end-to-end case: a user-reported local `.m4a` previously produced only about 12 seconds of transcript. Compare FFmpeg-reported duration, ASR segment coverage and generated transcript for that exact file before claiming it is resolved.
- Browser transcript bridge and browser tab-audio capture are unfinished unless subsequent code and tests prove otherwise.

## Current implementation notes
- Caption parsing supports VTT, SRV3, TTML and JSON3.
- Acquisition is caption-first, then yt-dlp/local media and faster-whisper fallback.
- Primary transcript output is persisted before Ollama summary/translation stages so later AI failures do not erase the transcript.
- Local ASR uses bounded windows and coverage/timestamp checks; verify the current implementation and tests before changing it.
- Range selection is full / first N minutes / first N percent. Local-media extraction must fail explicitly if a requested non-full range cannot be safely calculated; it must not silently process the full recording.
- AUTO caption selection and manual-track preferences are covered by regression tests; inspect the current tests before changing selection behavior.
- English summary generation follows the source-language summary and has an English-language acceptance check/retry; verify current code/tests before modifying it.

## Change discipline
- Distinguish source/build verification from real-media end-to-end verification in reports.
- Record newly verified changes and remaining blockers here; do not turn unverified assumptions into project facts.
