# Security and limits

Qyad v0.9.2. Security-conscious MVP, not a security audit or promise of complete protection.

## Implemented

- Clerk required in production. RS256 signature/JWKS, exact issuer, exp/nbf/iat, authorized-party, session/user ID and pending-status checks on the server. Local session cookies cannot bypass Clerk-only mode.
- Separate production `/api/v1` routes. Legacy aliases and interactive API docs are development-only.
- Server-side ownership/team membership checks, private applications and resume profiles, explicit shared statuses and audit events.
- Account linking requires an existing password session plus matching verified Clerk email. No email-only merge. Link in private staging before production cutover.
- Same-origin Pages API gateway, fixed HTTPS upstream, no arbitrary target, no redirects, no API caching, no forwarded cookies. Bearer token is never saved to browser localStorage by Qyad. Clerk manages its session.
- Trusted Host allowlist, exact browser write-origin checks, no wildcard CORS. Security headers in server and static deployment.
- Production basic rate limit: 15 auth/upload requests per minute per upstream client IP, 180 other API requests. One process, bounded 10,000-entry store. A shared edge IP can share limits. Caddy and the deployment provider should enforce broader abuse protection.
- Caddy caps request body at 3MB. Resume upload cap 2MB, at most 20 PDF pages. PDF parser runs separately with an 8-second wall timeout and Linux CPU/address-space limits. Original upload is not kept by the app; multipart handling may use a temporary file before cleanup. Extracted text is stored only after Save profile. No external AI or job-provider resume disclosure.
- No arbitrary webpage URL scraping. Known catalog URLs fill checked metadata. Unknown URLs must be reviewed, avoiding an SSRF route into the VPS network.
- SQLite WAL and busy timeout; backup script uses online backup and integrity check. Secrets and database artifacts are excluded from git.
- Non-root, localhost-only backend example, warning/error logging retained, no reload/access/debug logging in service command.

## Still your responsibility

- Run the real deployment acceptance checks, set Clerk production DNS and authorized parties, use MFA for owner accounts and SSH keys for the VPS.
- Apply security updates, scan dependencies, restrict SSH/firewall, protect backups and .env, use provider monitoring.
- JWT validation is offline; a revoked Clerk session's token can remain valid until short expiry. No live online session lookup per API call.
- Basic rate limits are not distributed; proxy IP sharing can over-limit users. Review with actual deployment traffic before wider rollout. No per-account quotas, billing, email abuse control or enterprise audit setup.
- The CSP shipped here restricts base/object/framing/form targets but is not a strict script allowlist. Inline-style-heavy UI and Clerk integration need a tested, domain-specific policy before enforcing a strict CSP.
- SQLite is one-writer storage. No high-availability replica, formal migrations, query pagination, restore automation or account-deletion lifecycle is included. Keep this small-team scale. Existing list endpoints can return many rows; do not claim high-scale readiness.
- Retention of saved resume text is until you clear it; backups can retain older data until rotation. Server owner can access the database. “Private” means access-controlled in the app, not end-to-end encrypted.
- Existing agent-token endpoints are separate opt-in credentials with write permissions and audit logs. Revoke unused tokens. Their end-to-end chat integration is unverified.

## API

Base: `/api/v1`. Existing resource names and JSON shapes remain stable. In development, `/openapi.json` documents v1; production hides it. Public health: `/api/v1/health`. Public auth config exposes only publishable settings. Authentication routes provision verified Clerk identities; all workspace routes enforce access checks. Unknown API versions return 404. New major behavior should use a new major path rather than silently breaking v1.
