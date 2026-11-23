# Split deployment: Pages + VPS + SQLite

Qyad v0.9.2. Prepared 23 Nov 2026. These are setup instructions, not confirmation that your server is deployed.

## Layout

Use your domain with two subdomains, for example **app.YOUR-DOMAIN** and **api.YOUR-DOMAIN**. These are placeholders, not existing addresses.

Browser -> Cloudflare Pages `app` -> `/api/v1/*` gateway -> Caddy HTTPS `api` -> FastAPI on 127.0.0.1:8000 -> SQLite on the VPS.

The browser only calls its own origin. The gateway forwards Clerk bearer tokens, strips cookies and refuses redirects. No wildcard CORS or cross-site cookie workaround is needed. The database is never uploaded to Pages and never listens on a public port. A Pages Function is used for the API proxy, so its plan limits apply. This is not a static-only API deployment.

## Before you begin

- Have the actual domain, DNS access, VPS SSH access and Clerk/Cloudflare accounts ready. Never send private keys, passwords or .env files in chat.
- Linux examples assume Ubuntu 24.04, systemd and a non-root SSH account named `deploy`. Adapt that username and every domain placeholder.
- Confirm free disk with `df -h`, provider firewall rules and SSH recovery access before enabling a firewall.
- Do not publish a demo database. No demo accounts are required.

## 1. Prepare the VPS

Upload the extractor from Windows, replacing the placeholder hostname/IP:

```powershell
scp .\extract.py deploy@YOUR-VPS-IP:~/extract.py
ssh deploy@YOUR-VPS-IP
```

On the server:

```bash
sudo apt update
sudo apt install -y python3-venv caddy
mkdir -p ~/qyad-release
cd ~/qyad-release
python3 ~/extract.py
cd qyad-v9.2/server
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
chmod 600 .env
```

If updating, copy the consistent old database backup into this `server/` directory before starting. Do not overwrite the old copy.

## 2. Link existing accounts to Clerk before cutover

New accounts can skip linking and use Clerk directly. For existing password accounts, email matching alone is deliberately not enough to transfer data.

In a private/local copy first, keep `APP_ENV=development`, `AUTH_MODE=local`, configure a Clerk development instance and authorize `http://localhost:8000`. Start the server locally, sign in with your existing Qyad password, go to Settings > Link Clerk account and use the same verified primary email. Verify spaces and applications remain. Stop and back up the linked database.

Important: Clerk development and production instances have different user IDs. A link to a development user does **not** automatically link a production user. For the actual production cutover, configure the production Clerk instance and perform linking through a private HTTPS staging route on your domain with strict access controls (VPN/SSH access tunnel and a trusted HTTPS setup) before changing to production mode. Do not temporarily expose password mode to everyone. If you cannot provide a private staging route, stop and plan the account migration before rollout. There is no automatic email merge or untested database rewrite script in this package.

## 3. Configure the server

Edit only `server/.env` using a server editor. Use real values, not these placeholders:

```dotenv
DATABASE_URL=sqlite:///./workspace.db
APP_ENV=production
AUTH_MODE=clerk
PUBLIC_URL=https://app.YOUR-DOMAIN
ALLOWED_HOSTS=api.YOUR-DOMAIN
CLERK_PUBLISHABLE_KEY=YOUR_PUBLISHABLE_KEY
CLERK_SECRET_KEY=YOUR_SECRET_KEY
CLERK_ISSUER_URL=https://YOUR-CLERK-FRONTEND-API-HOST
CLERK_AUTHORIZED_PARTIES=https://app.YOUR-DOMAIN
```

`CLERK_ISSUER_URL` is the actual Frontend API origin shown by Clerk, not an invented URL. Server verifies JWT RS256 signatures with that issuer's JWKS, issuer, exp, nbf, iat, user/session ID, allowed party and pending status. No key is hardcoded. Enable production sign-in methods and add required DNS records in Clerk. Do not add arbitrary preview hosts to authorized parties.

Only the publishable key and frontend URL are returned to the client. The Clerk secret stays on the VPS. Account session revocation follows Clerk's short-lived token expiry, it is not an online session lookup on every API request.

## 4. Run FastAPI as a service

Create `/etc/systemd/system/qyad.service` with a server editor. Replace `deploy` and paths if different:

```ini
[Unit]
Description=Qyad API v1
After=network.target

[Service]
User=deploy
Group=deploy
WorkingDirectory=/home/deploy/qyad-release/qyad-v9.2/server
EnvironmentFile=/home/deploy/qyad-release/qyad-v9.2/server/.env
ExecStart=/home/deploy/qyad-release/qyad-v9.2/server/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1 --proxy-headers --forwarded-allow-ips=127.0.0.1 --no-access-log --log-level warning
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
UMask=0077
MemoryMax=1G
TasksMax=128

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now qyad
sudo systemctl status qyad
```

Do not use reload/debug or bind port 8000 to the internet. One worker is intentional: cache/rate limits are per process and SQLite has one writer at a time. Rate limits are bounded basic abuse protection, not a distributed WAF.

## 5. DNS and HTTPS

At your DNS provider, create an A record for `api` pointing to your VPS IPv4. Add AAAA only if IPv6 works. If using Cloudflare DNS, start DNS-only while issuing the Caddy certificate; if you later enable proxying, use Full (strict), never Flexible. Permit inbound 80/443. Keep SSH restricted where possible.

Edit `/etc/caddy/Caddyfile`:

```caddy
api.YOUR-DOMAIN {
    request_body {
        max_size 3MB
    }
    @api path /api/v1/*
    handle @api {
        reverse_proxy 127.0.0.1:8000
    }
    handle {
        respond "Not found" 404
    }
}
```

Validate, then reload:

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

Caddy will request/renew HTTPS when DNS and port access are right. Test `https://api.YOUR-DOMAIN/api/v1/health`. It must return `{"ok":true}`. A health response is not proof auth or private-data isolation works.

## 6. Deploy the client from Windows

Install current Node LTS to get npm. In PowerShell:

```powershell
cd .\qyad-v9.2\client
npm install
npx wrangler login
npx wrangler pages project create
npx wrangler pages deploy public --project-name YOUR-PAGES-PROJECT --branch main
```

Choose `main` as production branch when creating the project. Do not upload the whole monorepo or `server/`. Only `client/public` goes to Pages. `client/public/_worker.js` is the API gateway. Use Wrangler, not an uncertain drag-and-drop workflow. Review the deployment output.

In the Pages dashboard:

1. Add custom domain `app.YOUR-DOMAIN` and finish the DNS instructions shown there.
2. Under Settings > Variables and Secrets, set production variables:
   - `APP_ORIGIN`: `https://app.YOUR-DOMAIN`
   - `BACKEND_ORIGIN`: `https://api.YOUR-DOMAIN`
3. Redeploy after changing variables. Do not put the Clerk secret or database URL here.

The generic pages.dev and branch-preview URLs intentionally cannot use the API because `APP_ORIGIN` is pinned to the custom domain. This prevents unapproved preview sites from becoming API clients. Open the custom app domain for acceptance tests.

## 7. Launch checks, do not skip

- Health succeeds through `https://app.YOUR-DOMAIN/api/v1/health`.
- `/api/health`, password register/login and `/docs` are not usable in production.
- Sign in with your real Clerk account, reload, log out, sign in again. Test wrong/expired bearer and wrong origin are rejected.
- User A cannot read User B's personal space, resume profile or applications. An outsider cannot read a team. Linking does not move data by email alone.
- Upload a small text PDF/TXT. Review extracted skills, save, refresh. Upload is private. Clear profile works. An invalid/scanned PDF gives a clear error.
- Save one checked internship to a team and privately; it appears once. Apply opens the real source. Change a private application status using its dropdown, reload and verify the stage stayed.
- Check mobile light/dark readability. Check no console errors.
- Run a backup and test restore in a separate folder.

No live Clerk login, Cloudflare deployment, DNS, certificates or VPS commands were run on your account during this build. Node gateway tests and local browser/API tests do not replace these launch checks.

## 20GB disk: is it good?

For this text-only personal/small-team MVP, 4 vCPU and 8GB RAM are a reasonable starting size. The **20GB disk** is the tighter limit. It stores the OS, Python environment, database, SQLite WAL, logs, releases and backups, not only the data. It is not 20GB of safe application capacity.

Start without Docker images, local AI models, stored resumes or uploaded media. Keep at least 5GB or 25% free as an operating target. Measure your actual growth, not a guessed user count. SQLite suits this small-team workload; switch to PostgreSQL when write contention or product requirements justify a planned migration. Do not move the DB to Pages or a network filesystem.

Daily from the `server/` directory:

```bash
.venv/bin/python -m scripts.backup
```

It uses SQLite online backup, checks integrity and retains the newest seven local files. Keep an encrypted off-server copy too. Local backup alone does not survive VPS loss. Arrange a daily scheduler on the server after verifying paths. Bound system journal size and keep only the previous working release; do not let backups/releases fill the disk. Check `df -h`, service warnings/errors and uptime regularly.

## Sources

- https://developers.cloudflare.com/pages/functions/advanced-mode/
- https://developers.cloudflare.com/pages/get-started/direct-upload/
- https://developers.cloudflare.com/pages/configuration/serving-pages/
- https://clerk.com/docs/guides/sessions/manual-jwt-verification
- https://www.sqlite.org/wal.html
- https://caddyserver.com/docs/automatic-https

## Host sleeps after inactivity?

See [optional 15-minute keep-alive](keepalive.md). Check provider policy first. The included separate Worker can ping the public backend health endpoint every 15 minutes, but nothing has been deployed. This helps only if HTTP traffic resets an allowed app-idle timer, not if the whole VPS is powered off.
