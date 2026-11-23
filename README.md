# Qyad v9.2

Private plans, a clear opportunity list and an application tracker. Modern white/black surfaces with a focused orange accent. Python 3.10+.

## Start on Windows

1. Save the delivered text file as `extract.py` in an empty folder. Run `py extract.py`.
2. Open PowerShell in the new `qyad-v9.2` folder:

```powershell
cd .\server
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open http://localhost:8000. Local development uses the password login. No Node needed to try the app. Production requires Clerk and HTTPS, see `docs/deploy-split.md`.

## Keep your data

Stop the old server. Make a backup with its SQLite backup API or stop it before copying `workspace.db`. With WAL enabled, copying just the main file while the server runs can lose recent writes. Keep the old folder and `.env` private.

Copy the backed-up `workspace.db` into **`qyad-v9.2/server/`**, not the monorepo root. Merge your old `.env` into **`server/.env`**. If you have an absolute `DATABASE_URL`, preserve it or deliberately change it. Never run the demo seed on a real database.

No schema changes from v7. Existing users, teams, private applications and tasks stay. Clerk links from v7 stay. Previously domain-only records cannot be turned into real jobs without checking their links; v9 marks them as needing details.

## Structure

- `client/public/`: HTML, compiled styles, plain JavaScript, Pages API gateway.
- `client/styles/`: Tailwind source/config. Compiled CSS is shipped.
- `server/app/`: FastAPI, server-verified Clerk, SQLite, API routers and dated opportunity catalog.
- `server/tests/`: regression tests.
- `server/scripts/backup.py`: consistent SQLite backup with seven-file local retention.
- `docs/deploy-split.md`: Cloudflare Pages frontend + VPS backend/database.
- `docs/security.md`: protections, boundaries and launch checks.
- `docs/opportunity-sources.md`: checked opportunity sources and caveats.

## v9.1 palette update

Dark mode only: #121212 page, #18181B surfaces, off-white text and soft muted orange. Light theme, tables, font and features are unchanged.

## What's new in v9

- Table only: one row per opportunity link, with Role, Company/location, Type, Deadline, Match, Status and Apply/Open link. No card/list toggle. On phones the table scrolls sideways inside its own region.
- Private applications are also a table, with an editable status dropdown instead of a drag board.
- Be Vietnam Pro, regular 400 and medium 500 for everyday text. Titles are 14px medium, not oversized bold. Font files are self-hosted, no Google Fonts runtime request.
- White/black theme and orange links, readable spacing and column headers. Extra notes, match explanation and private/team save actions remain under Details in the role cell.
- All v8 backend, Clerk-only production, API v1, resume preview/matching, inline real data, client/server layout and deployment safety remain. No Discover page.
- Footer/sidebar says v0.9.2, API v1. Database format unchanged.

## Tests

From `server/`: `python -m pytest -q`. From `client/`: `node --test tests/*.test.mjs`.

The shipped tests cover privacy, shared/private separation, Clerk JWT validation with generated keys, linking restrictions, the versioned API, source catalog, upload limits, and gateway behavior. Real Clerk keys, live VPS deployment and Cloudflare production have not been tested for your account. Check them before inviting friends.

## Honest limits

This is a personal/small-team MVP, not an audited SaaS. No automatic applications, phone notifications, live collaboration, universal job scraping or built-in WhatsApp integration. Existing voice-agent endpoints remain an unverified integration until an end-to-end acceptance test is run. Dependency patching, server access control, offsite backups and monitoring are still operational duties.

## Push the clean repo from Windows PowerShell

The extractor creates source files only. It does not initialize git, commit, create a GitHub repository or push anything. Install Git for Windows, create an empty private repository on your chosen Git host, then open PowerShell in the extracted `qyad-v9.2` root.

```powershell
git init
git branch -M main
git status --short
# Inspect files before staging. No .env, database, uploads or backups should be listed.
git add .
git diff --cached --stat
# Review staged files, then:
git commit -m "Initial Qyad source"
git remote add origin YOUR-REPOSITORY-REMOTE-URL
git push -u origin main
```

Use the actual remote URL your Git host provides. Do not paste access tokens into commands or commit messages; use Git's normal browser/credential-manager sign-in. You choose when to push and whether the repository is private. A private repo is not a safe place for secrets either.

`.gitignore` excludes env files, SQLite/DB and WAL files, virtual environments, node_modules, dist/build, backups, logs and uploads. Example env files contain non-secret placeholders only. Do not copy your live `.env` or `workspace.db` into the source repo to share it. Keep your runtime database in a separate private deployment location, or verify it remains ignored before every commit.

No application-source license was selected for you. Read `LICENSE-DECISION.md` and choose one before external reuse. Third-party font/CSS licenses are included under `licenses/`.

## Optional idle-host check

`docs/keepalive.md` and `ops/keepalive/` provide an opt-in Cloudflare Worker scheduled every 15 minutes. Verify host rules and sleep behavior first; no keep-alive or deployment has been activated.

## v9.2 Docker on InstaBox

Start with `DEPLOY-DOCKER.txt` in the repo root. The backend container runs non-root, with SQLite stored in the named `/data` volume. Keep secrets only in `server/.env`. Existing local databases are not imported automatically. No Docker image was built or run in the validation environment.
