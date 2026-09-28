# AGENTS.md - Project Specification & AI Coordination Hand-off
<!-- SOURCE OF TRUTH: GitHub Repository -->
<!-- Last Updated: 2026-09-23 -->

## 1. Project Identity & Architecture
*   **Project Name:** [Project Name]
*   **Core Objective:** [1-2 sentences on what this codebase does]
*   **Tech Stack:** [e.g., Next.js 15, TypeScript, Python FastAPI, PostgreSQL]
*   **Key Directories:**
    *   `/src/components`: UI Layer
    *   `/src/api`: Backend logic

## 2. Shared Development Workflow (The Multi-AI Rule)
This project utilizes a dual-engine AI strategy (OpenAI & DeepSeek). To maintain sync:
1. **GitHub is the absolute Source of Truth.** Never trust a previous chat window's assumption over the actual state of the code on GitHub.
2. Before writing code, you must read the latest commit changes or request a file export.
3. **OpenAI Focus:** Architectural design, system prompt engineering, feature planning, and structured layouts.
4. **DeepSeek Focus:** Math, performance optimization, heavy logical debugging, and deep algorithmic thinking.

## 3. Current Sprint & State of Play
*   **Active Branch:** `main` (or `dev-feature-x`)
*   **Last Successfully Merged Feature:** [e.g., Implemented Auth0 integration]
*   **Current Bottleneck / Active Task:** [e.g., DB queries are throwing connection pool timeouts]
*   **Immediate Next Action Item:** [e.g., Optimize the prisma-client connection pooling config]

## 4. Code Style & Technical Constraints
*   **Formatting:** [e.g., Prettier defaults, strict TypeScript, no `any`]
*   **Testing Protocol:** Run `npm run test` before declaring code "complete". All business logic must have unit tests.
*   **Explicit Boundaries:** Do not alter configuration files (`package.json`, `.env.example`) without explicit permission.

## SS TRANSCRIBE-TRANSLATE PROJECT OVERRIDES
- This repository is the source of truth for the Windows-native SS Transcribe-Translate application.
- The application is Python/Tkinter + faster-whisper + FFmpeg + yt-dlp + Ollama, packaged with PyInstaller.
- Before any code change, inspect the current `main` branch and preserve existing working features.
- OpenAI and DeepSeek are cooperating engineering agents; neither may treat the other agent's claims as verified until the relevant GitHub code/tests prove them.
- Every substantive feature must have a deterministic test or audit assertion where practical.
- Never silently install, update, remove, or replace unrelated software on the user's Windows PC.
- Do not claim the application is final until the source audit, Windows build audit, and an end-to-end real-media test pass.
- Record important architecture/feature changes in this file so the next agent can resume from GitHub without relying on chat history.

## CURRENT SS TRANSCRIBE-TRANSLATE STATE
- Caption parsing supports VTT, SRV3, TTML and JSON3 with regression tests.
- Acquisition is caption-first, then yt-dlp/local-media + faster-whisper fallback.
- The GUI now supports transcription of the full source, the first N minutes, or the first N percent (including 50% for the first half).
- The selected range is applied to remote caption cues and local FFmpeg audio extraction, and is persisted in config.local.json.
- `CONSOLE.cmd` provides Start, final audit, local verification, EXE build and Explorer actions.
- `START-APP.vbs` creates the Start Menu application and console shortcuts and prefers the packaged EXE.
- Browser transcript bridge and browser tab-audio capture remain explicitly unfinished; do not claim them as implemented until committed and verified.
- The current definition of final verification is: `verify-final.ps1` + Windows EXE build + `verify-local.ps1` with an explicit real media file. CI uses the same final source/build gate.