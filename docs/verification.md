# v9 verification, 23 Nov 2026

- 36 Python tests pass. The original 27 tests and their five files are unchanged. Nine new tests cover versioning, fail-closed production, catalog/no-network behavior, Clerk-required rejection of local login, SQLite WAL, private TXT/PDF extraction and upload limits, matching explanations and safe metadata preview.
- Four Node gateway tests pass: static bypass, origin/version restrictions, bearer forwarding/cookie stripping/no-store, HTTPS fixed upstream and error/redirect handling.
- Browser checks: actual light/dark desktop and 390px/320px phone layouts, no horizontal document overflow, resume upload preview and save, list filters and shared status, unknown link opens review without a fake title, inline catalog save, no Discover navigation. No JavaScript page errors in these runs.
- SQLite backup utility ran and integrity check passed on a local test database.
- Real Clerk provider sign-in, production DNS/HTTPS, Cloudflare account deploy and the owner's VPS remain untested. JWT tests use generated keys and mocked profile responses. Gateway tests use a local mock upstream.
- No load benchmark or full security audit. No claim of unlimited users or measured production latency. A small-team starting architecture is not a capacity guarantee.

## v9 UI checks

Table-only shared opportunities, private applications and solo starter opportunities. Be Vietnam Pro font files are self-hosted; computed font and loaded-font checks passed. Browser tests covered filters, shared-status write, private status write, no card/list toggle, and phone table swipe to Apply with page horizontal scrolling contained. Inspected actual light/dark desktop table screenshots and both phone scroll positions. Backend remains 36 tests passing and gateway remains four tests passing. No live deployment or real Clerk sign-in was added.

## v9.1

Dark-only palette update. Tested text pairs against #18181B: title 16.12:1, body 13.42:1, metadata 8.70:1, muted text 6.05:1, link 9.61:1 and button text 8.11:1. These pairs exceed 4.5:1, not a full accessibility audit. Clean source package excludes databases, secrets, runtime artifacts and git history. No git commands, commits or pushes are performed by the extractor. Owner chooses the source license.

## v9.1 final checks

37 backend tests, 4 Pages gateway tests and 3 keep-alive Worker unit tests pass locally. Final dark UI inspected in Chromium with self-hosted Be Vietnam Pro loaded; body computed #121212. Light-theme rules were not changed. No real Clerk login, deployment, live cron or provider sleep behavior was tested.

## v9.2 Docker packaging

Compose YAML parsed and persistent /data mount settings checked. Absolute-directory SQLite backup tested. Production health/auth guard smoke passed with synthetic settings, not a real Clerk login. 37 backend, 4 gateway and 3 keep-alive tests passed. Docker is not installed in the validation environment: no image build, container run, machine SSH, public URL, real Clerk login or custom domain was tested. UI unchanged except version label.
