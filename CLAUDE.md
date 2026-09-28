# Transcribe-Translate Project Architecture

## Overview
This document defines the architecture, processes, and rules for the Transcribe-Translate project.
It is read automatically by Claude Code at the start of every session to ensure consistent
adherence to the established workflow.

## Core Principles
1. **Human-in-the-loop adjudication** - AI agents propose solutions; humans make final decisions.
2. **Branch protection** - `main` branch requires PR + passing checks; no direct pushes.
3. **Version synchronization** - All AI agents work from the same base via git and shared notes.
4. **Conflict resolution** - Disagreements between agents are surfaced for human adjudication.

## Repository Structure
```
/ (repo root)
├── CLAUDE.md              ← This file
├── AGENT-NOTES.md         ← Shared workspace for AI agent proposals
├── .github/
│   └── workflows/
│       └── orchestrate.yml← GitHub Action for multi-agent coordination
├── output/                ← Transcription/translation outputs (per-run folders)
├── library.sqlite3        ← Central metadata store
└── [project-specific files]
```

## Branching Model
- `main` → Protected branch. Only updated via PR with:
  - At least one approving review
  - All status checks passing (CI/tests)
  - No direct pushes allowed
- `feature/*` → Short-lived branches for ongoing work (created automatically via PRs)
- Agents work on PR branches; proposals land as commits to those branches

## AI Orchestration Flow (GitHub Action)
1. **Trigger**: On `pull_request` targeting `main` or `push` to feature branches
2. **Diff Analysis**: Action computes changes since base commit
3. **Agent Invocation**: 
   - Reads current `AGENT-NOTES.md`
   - Calls OpenAI GPT-4o and DeepSeek Chat APIs with:
     - The diff
     - Current agent notes
     - Project context (from CLAUDE.md)
   - Each agent writes its proposed solution/notes back to `AGENT-NOTES.md`
4. **Conflict Detection**: Action compares agent outputs; flags significant divergences
5. **Adjudication**: 
   - Claude Code (this instance) reviews conflicts and suggests a resolution
   - Posts suggestion as PR comment
6. **Human Gate**: 
   - User reviews agent proposals + Claude's adjudication
   - Explicit approval required (via PR comment `/approve` or merge button)
7. **Merge**: On approval, Action merges PR to `main` after final CI validation

## AGENT-NOTES.md Usage
- **Format**: Markdown file with sections per agent/run
- **Conventions**:
  - `## OpenAI Proposal` - OpenAI's analysis and suggested changes
  - `## DeepSeek Proposal` - DeepSeek's analysis and suggested changes
  - `## Adjudication Notes` - Human or Claude's conflict resolution notes
  - `## Verified Main` - Summary of what was merged to main (updated post-merge)
- **Rules**:
  - Agents append to file; never delete others' contributions
  - Humans may edit to consolidate or clarify
  - File is committed alongside code changes

## Required Status Checks
Before merging to `main`, the following must pass:
- `lint` - Code style checks
- `test` - Unit/integration tests (project-specific)
- `security` - Basic security scan (secrets, known vulns)
- `orchestrate` - Multi-agent orchestration validation (no conflicts, proper notes)

## Human Responsibilities
1. **Approval Authority**: Only you can merge to `main` (via PR approval)
2. **Conflict Arbitration**: When agents disagree, you decide the best path forward
3. **Note Maintenance**: Periodically refine `AGENT-NOTES.md` for clarity
4. **API Key Management**: Ensure OpenAI/DeepSeek secrets are set in GitHub repo Settings → Secrets

## Getting Started
1. Install GitHub App (already done: https://github.com/apps/claude)
2. Initialize git repo: `git init && git add . && git commit -m "initial commit"`
3. Push to GitHub: `git remote add origin <your-repo-url> && git push -u origin main`
4. Enable branch protection (GitHub UI):
   - Settings → Branches → Add rule
   - Branch name pattern: `main`
   - ✅ Require a pull request before merging
   - ✅ Require approvals
   - ✅ Require status checks to pass
   - ✅ Include administrators
5. Add repository secrets:
   - `OPENAI_API_KEY`
   - `DEEPSEEK_API_KEY`
   - `GITHUB_TOKEN` (auto-provided by Actions, but ensure repo has permissions)
6. Customize workflow (`.github/workflows/orchestrate.yml`) for your test/lint commands

---
*This CLAUDE.md is version-controlled. Evolve it as the project matures, but keep the 
human-adjudication gate as the core invariant.*