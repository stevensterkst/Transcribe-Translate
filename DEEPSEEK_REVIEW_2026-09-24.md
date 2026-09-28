# DeepSeek/OpenAI joint review — 2026-09-24

## Real Windows test evidence

The user tested a short local WAV/media job. The generated job metadata shows:
- ASR: faster-whisper-batched, base
- Ollama: llama3.2:1b
- range: full
- source language detected: fr
- primary outputs were created

The attached real output demonstrates a serious source-summary failure: the French summary repeats the same sentence under generic sections such as Introduction, Decision, Propositions, Questions, Voting positions, and Action items. The English file merely translates this defective summary.

The actual transcript is about 4m12s and contains a coherent discussion about a French point d'accès juridique, tribunal, avocat/procureur, legal-aid possibilities and identifying the competent tribunal. The transcript is imperfect ASR French, but it is materially longer and more informative than the generated summary.

## Confirmed software defects addressed in this pass

1. Legacy project-local output paths are now migrated generically to the Downloads\Transcribe-Translate content root, including nested project-local transcribe-translate/output paths.
2. GUI now restores the persisted Ollama model selection and prefers qwen3:1.7b, then phi4-mini:3.8b, before smaller models when no explicit configured model exists.
3. Source-summary generation now has a factual/repetition quality gate.
4. If the selected local model produces template/repetition garbage, the app retries with an installed local qwen3:1.7b or phi4-mini:3.8b. No cloud fallback is introduced.
5. Added regression tests for rejection of the observed repeated-template failure and acceptance of an evidence-grounded summary.
6. Existing ASR hardening remains: bounded 180-second windows, VAD/no-VAD retry, explicit coverage reporting, timestamp validation.
7. Primary transcript is saved before any Ollama stage.
8. AUTO caption selection no longer silently prefers English.

## Still required before calling this final

- Rebuild the Windows EXE from current GitHub.
- Run the supplied real media test again.
- Confirm the GUI Output field and actual job directory are under Downloads\Transcribe-Translate.
- Confirm the summary is materially non-repetitive and grounded in the transcript.
- Confirm English summary is a translation of the improved source summary.
- Run the complete final audit and real-media verification.
- Continue reviewing all requirements in the existing migration packet/extra improvements file, especially browser transcript bridge/tab-audio capture, CI/build gating, behavioral tests, requirements hardening, config-local safety, concurrency/Start locking, and progress reporting.

## Cooperation protocol

GitHub is the shared source of truth. OpenAI handles architecture/prompt/output semantics; DeepSeek is asked to independently inspect logic, performance, edge cases and tests. Neither side should declare a feature final merely because its source text exists: final status requires a verified Windows build and real-media smoke test.
