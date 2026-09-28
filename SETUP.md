# One-Time Setup Guide — Transcribe-Translate

## 🔴 Critical: GitHub UI Actions Required

You **must** perform these steps in the GitHub UI for the repository to work securely and enable the orchestration workflow.

### Step 1: Enable Branch Protection
1. Go to: `https://github.com/stevensterkst/Transcribe-Translate/settings/branches`
2. Click "**Add rule**"
3. Branch name pattern: `main`
4. ✅ **Require pull requests before merging**
5. ✅ **Require status checks to pass before merging**
6. ✅ **Include administrators**
7. Click "**Create**"

> This ensures no direct pushes to `main` — all changes require PR approval.

### Step 2: Add GitHub Secrets
1. Go to: `https://github.com/stevensterkst/Transcribe-Translate/settings/secrets/actions`
2. Click "**New repository secret**" for each:
   - **Name**: `OPENAI_API_KEY` → **Value**: [your OpenAI API key]
   - **Name**: `DEEPSEEK_API_KEY` → **Value**: [your DeepSeek API key]
   - **Name**: `ANTHROPIC_API_KEY` → **Value**: [your Anthropic API key]
3. Click "**Add secret**" after each

> These keys are encrypted and only accessible to GitHub Actions workflows.

### Step 3: Verify .gitignore (Already Correct)
- `.gitignore` blocks: `.env`, `*.local.json`, `output/`, `_work/`, `__pycache__`, `*.pyc`, `*.wav`, `*.webm`, `*.mp4`, `*.mkv`, `library.sqlite3.bak`

## Optional: Test the Orchestration Workflow

1. Create a test branch: `git checkout -b test-security`
2. Make a trivial change (e.g., update README.md with a comment)
3. Commit: `git commit -am "Test: verify orchestration workflow"`
4. Push: `git push origin test-security`
5. Open a Pull Request on GitHub
6. Watch the Actions tab — you should see:
   - `diff-analysis` job
   - `openai-agent` job (fails if OPENAI_API_KEY not set)
   - `deepseek-agent` job (fails if DEEPSEEK_API_KEY not set)
   - `adjudicate` job (fails if ANTHROPIC_API_KEY not set)
   - `merge-gate` job (waits for human approval)

> If secrets are missing, the corresponding agent jobs will fail — this is expected and safe.

## What Happens Next

1. When you open a PR, the workflow runs all 5 stages
2. OpenAI and DeepSeek agents propose changes
3. Claude adjudicates conflicts and posts a summary to the PR
4. You review the proposals and Claude's notes
5. You approve the PR (merge) only when satisfied

## Need Help?
- See `SECURITY.md` for audit details
- See `.github/workflows/orchestrate.yml` for workflow definition
- All API keys stay in GitHub Secrets — never in code or logs

---
*Last updated: 2026-09-28*