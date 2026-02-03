# Pre-Share Checklist

Before sharing this project publicly, complete these quick tasks:

## 1. Update Personal Info (5 min)

### Files to edit:
- [ ] `README.md` - Add your LinkedIn/GitHub links at bottom
- [ ] `LESSONS_LEARNED.md` - Add contact info in "About the Author"
- [ ] `SUMMARY.md` - Fill in your LinkedIn/Email/GitHub links
- [ ] `LINKEDIN_POST.md` - Add your GitHub repo URL

### Search and replace:
```bash
# Find all placeholder text
grep -r "\[Your" *.md
grep -r "\[Link to" *.md
grep -r "\[GitHub" *.md
```

Replace:
- `[Your LinkedIn]` → Your actual LinkedIn URL
- `[Your email]` → Your email address
- `[GitHub repo]` → Your GitHub repository URL
- `[This repo]` → Your GitHub repository URL

---

## 2. Clean Up Sensitive Info (2 min) ⚠️ CRITICAL

**Run the security check script:**
```bash
./check_secrets.sh
```

This checks for:
- [ ] Anthropic API keys (sk-ant-*)
- [ ] OpenAI API keys (sk-proj-*, sk-*)
- [ ] .env files (should be in .gitignore)
- [ ] Hardcoded secrets in code
- [ ] .gitignore exists and includes .env

**Manual checks:**
- [ ] Remove any personal notes/comments
- [ ] Review `RUN_LOG.md` for anything sensitive
- [ ] Check terminal output in screenshots for keys
- [ ] Verify .env file is NOT in git: `git ls-files | grep env`

**If you find any secrets:**
1. ❌ DO NOT COMMIT
2. Remove them immediately
3. Add patterns to .gitignore
4. Run check_secrets.sh again

---

## 3. Test the Quick Start (5 min)

Make sure someone can actually run this:

```bash
# Clean install test
cd /tmp
git clone <your-repo>
cd adcock-challenge
pip install -r requirements.txt
python3 -m playwright install chromium

# Verify it runs (without API key, should fail gracefully)
python3 main.py --help

# Should show clear error message about API key
python3 main.py
```

---

## 4. GitHub Repository Setup (10 min)

### Create new repo:
- [ ] Create repo: `browser-automation-agent` (or similar)
- [ ] Add description: "Production-grade AI agent for browser automation - demonstrating when AI makes sense vs. deterministic scripts"
- [ ] Add topics: `browser-automation`, `ai-agent`, `playwright`, `llm`, `anthropic`, `openai`

### Add to repo:
- [ ] `.gitignore` file (see below)
- [ ] LICENSE file (MIT recommended)
- [ ] All code + documentation

### `.gitignore` to add:
```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/

# Playwright
.playwright/
screenshots/

# Secrets
.env
*.key
*_key.txt

# Outputs
run_stats.json
*.log

# IDE
.vscode/
.idea/
*.swp
*.swo

# macOS
.DS_Store

# Temporary
temp/
tmp/
```

---

## 5. Polish LinkedIn Post (10 min)

### Edit `LINKEDIN_POST.md`:

- [ ] Read it out loud - does it flow?
- [ ] Is it under 3,000 characters? (LinkedIn limit)
- [ ] Does it have a hook in the first 2 lines?
- [ ] Does it end with a clear call-to-action?
- [ ] Are code snippets formatted correctly?

### Optional enhancements:
- [ ] Add emojis (sparingly) for visual breaks
- [ ] Tag Brett Adcock if you want his attention
- [ ] Tag relevant companies (Anthropic, OpenAI, Playwright)
- [ ] Add hashtags: #AI #Engineering #Automation #TPM

---

## 6. Create Supporting Materials (Optional, 30 min)

### Screenshot your architecture:
```bash
# Run with visible browser
python3 main.py --visible
# Take screenshots of:
# - Browser window with challenge
# - Terminal with metrics output
# - Code editor showing agent/ directory
```

### Create architecture diagram:
- Draw.io, Excalidraw, or Miro
- Show: Browser ↔ Agent ↔ LLM flow
- Export as PNG, add to repo

### Record demo video (optional):
```bash
# macOS screen recording
Cmd+Shift+5
# Record 30-60 seconds of agent running
# Upload to YouTube as unlisted
# Add link to README
```

---

## 7. Final Quality Check (5 min)

### Run through this:
- [ ] All links work (no 404s)
- [ ] Code blocks render correctly in GitHub markdown
- [ ] No typos in README (spell check)
- [ ] File tree in README matches actual structure
- [ ] Quick start commands actually work
- [ ] Contact info is correct

### Test markdown rendering:
```bash
# Preview locally
pip install grip
grip README.md
# Open http://localhost:6419
```

---

## 8. Publish Strategy

### Timing:
- [ ] **Best time:** Tuesday-Thursday, 8-10am PT (peak LinkedIn engagement)
- [ ] **Avoid:** Friday afternoons, weekends, holidays

### Posting:
1. Push to GitHub first
2. Copy `LINKEDIN_POST.md` content
3. Paste to LinkedIn
4. Add repo link at bottom
5. Tag relevant people/companies (optional)
6. Hit "Post"

### Follow-up:
- [ ] Respond to comments within 24 hours
- [ ] Share to relevant Slack/Discord communities
- [ ] Email to friends who'd find it interesting
- [ ] Consider cross-posting to:
  - Medium (expand to full article)
  - Dev.to
  - Hacker News (Show HN: ...)

---

## 9. Backup Plan

If LinkedIn post doesn't get traction:
- [ ] Share in niche communities (r/programming, AI Slack groups)
- [ ] Email directly to hiring managers at target companies
- [ ] Use as conversation starter in interviews
- [ ] Reference in portfolio/website

**Remember:** The goal isn't viral reach. It's demonstrating strategic thinking to the right people.

---

## 10. Quick Wins (If Short on Time)

If you only have 30 minutes, do these:
1. Add your LinkedIn/GitHub links (5 min)
2. Create GitHub repo (10 min)
3. Push code + docs (5 min)
4. Post LinkedIn with repo link (10 min)

Done. The rest can wait.

---

## Status Checklist

- [ ] Personal info updated
- [ ] Sensitive info removed
- [ ] Quick start tested
- [ ] GitHub repo created
- [ ] LinkedIn post ready
- [ ] Published!

**When you're done, delete this file before pushing to GitHub.**

---

Good luck! You've built something that demonstrates real engineering judgment. 🚀
