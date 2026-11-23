# AGENTS.md — 🕋 Nusuk Master HQ

Instructions for every coding agent working here (Claude Code, Antigravity, OpenCode, Codex).
The shared rules are in `~/.claude-master/Standards/agents.md`; anything below overrides them for this project.

## What it is
Nusuk Master HQ: autonomous quiz solver, referral-keys manager and real-time orchestrator for the Nusuk Umrah Challenge, using an offline verified Islamic Q&A knowledge base.

## Stack
Python

## Layout
Top-level folders: `docs/`.

## Commands
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
./start.sh
```
Run the test, lint and type-check commands that exist before every push.

## Branches
- Production: `main`
- Staging: none
- Pull requests go to: `main`
- Agent branches: `claude/<type>/<task>`, `agy/<type>/<task>`, `oc/<type>/<task>`; owner: `wajed/<type>/<task>`
- Never push to the production branch; open a pull request. **The owner merges.**

## Environment
No environment files. Never commit `.env*` files, keys or tokens (they are gitignored).

## Rules for this project
- Public repository: never commit keys, accounts, or personal data.
