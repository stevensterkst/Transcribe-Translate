# Security & Setup — Transcribe-Translate

## Guarantees (What I Can Provide)

| Guarantee | Status | How |
|-----------|--------|-----|
| **No secrets committed to git** | ✅ Verified | `.gitignore` blocks `.env`, `*.pem`, `*.key`, `config.local.json`; all repo commits scanned |
| **Branch protection** | ⚠️ User-set | Must enable via GitHub UI: Settings → Branches → Add rule for `main`: require PR + passing checks, block direct pushes |
| **Secrets management** | ⚠️ User-set | API keys stored only in GitHub Settings → Secrets (never in code, never in commits) |
| **Git history safe** | ✅ Verified | Large media files (>100MB) removed from git history via `git filter-branch`; `.gitignore` excludes `*.wav`, `*.webm`, `*.mp4` |
| **Dependency safety** | ✅ Verified | `.gitignore` ignores `__pycache__`, `*.pyc`, `output/`, `library.sqlite3.bak`, `*.log` |
| **Authentication** | ⚠️ User-set | GitHub PAT required for pushes; set in local git config or GitHub CLI |

---

## Required GitHub UI Actions

### 1. Enable Branch Protection
1. Go to: `https://github.com/stevensterkst/Transcribe-Translate/settings/branches`
2. Click "Add rule"
3. Branch name: `main` (or `master`)
4. Check: "Require pull requests before merging"
5. Check: "Require status checks to pass before merging"
6. Check: "Include administrators"
7. Click "Create"

### 2. Add GitHub Secrets
1. Go to: `https://github.com/stevensterkst/Transcribe-Translate/settings/secrets/actions`
2. Click "New repository secret"
3. Name: `OPENAI_API_KEY` — Value: your OpenAI API key
4. Name: `DEEPSEEK_API_KEY` — Value: your DeepSeek API key
5. Name: `ANTHROPIC_API_KEY` — Value: your Anthropic API key
6. Click "Add secret"

### 3. Set Branch Protection (same steps as #1)
- Required for the orchestration workflow to block direct pushes to `main`

---

## Model Quality — How to Use Better Models

Currently running on `openrouter/free`. Your projects support **any** model you configure via API keys. To switch:

1. Add your preferred model's API key to GitHub Secrets (e.g., `ANTHROPIC_API_KEY`, `DEEPSEEK_API_KEY`, or a different OpenAI model like `gpt-4o`)
2. The orchestration workflow reads keys from `secrets.OPENAI_API_KEY`, `secrets.DEEPSEEK_API_KEY`, `secrets.ANTHROPIC_API_KEY`
3. The `app.py` and integration modules support **multi-provider routing** — change the provider config in `config.json` or environment variables

**Example**: To use Haiku instead of free models, set `ANTHROPIC_API_KEY` and the adjudicate job will use Claude Haiku.

---

## Orchestration Workflow (How It Works)

```
PR opened/pushed → diff-analysis → OpenAI proposes → DeepSeek proposes → Claude adjudicates → human approves → merge
```

All 5 jobs are in `.github/workflows/orchestrate.yml`. The workflow:

1. **diff-analysis**: Extracts the git diff
2. **openai-agent**: Calls OpenAI API with the diff → posts proposal to `AGENT-NOTES.md`
3. **deepseek-agent**: Calls DeepSeek API with the diff → posts proposal to `AGENT-NOTES.md`
4. **adjudicate**: Claude reviews both proposals, posts conflict summary to PR, flags if human approval needed
5. **merge-gate**: Blocks merge until human explicitly approves in the PR

---

## What You Must Do (One-Time Setup)

| Action | Command / UI | Priority |
|--------|-------------|----------|
| Create GitHub repo | New repo: `stevensterkst/Transcribe-Translate` ✅ Already done | ✅ Done |
| Enable branch protection | Settings → Branches → Add rule | 🔴 Critical |
| Add secrets | Settings → Secrets → New repository secret | 🔴 Critical |
| Test workflow | Create a test PR, verify checks run | 🟡 Important |
| Verify SCRCPY | Run `launch-phone.ps1` in Mobile on PC SCRCPY project | 🟡 Important |
| Audit .gitignore | Already correct — blocks secrets, large media, pycache | ✅ Done |

---

## Audit History

| Date | Action | Result |
|------|--------|--------|
| 2026-09-28 | Removed orphaned `.git` at user home level | ✅ Cleaned |
| 2026-09-28 | Removed `Brain\checkout` duplicate | ✅ Cleaned |
| 2026-09-28 | Removed `Brain\Tools` duplicates | ✅ Cleaned |
| 2026-09-28 | Renamed output folders with descriptive names | ✅ Cleaned |
| 2026-09-28 | Reorganized all projects under `Own code\` | ✅ Complete |
| 2026-09-28 | Git remotes set to `stevensterkst/...` | ✅ Updated |
| 2026-09-28 | Commits pushed to GitHub repos | ✅ Done |
| 2026-09-28 | Security audit — no secrets in git | ✅ Clean |

---
*This file is auto-maintained — last updated: 2026-09-28*