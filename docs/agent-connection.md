> Historical design notes. For v8 setup and current limits, use deploy-split.md, security.md and opportunity-sources.md.

## Instinct connection: app side only, UNVERIFIED

The existing Route B interface remains: personal access tokens and `POST /api/v1/agent/apply`. It accepts structured, confirmed changes with owner checks, idempotent batch references, a confidence floor and an audit trail. It does not transcribe voice, run WhatsApp reminders or embed an assistant in this site.

To test later:

1. Deploy a private reachable app with HTTPS and persistent storage.
2. Sign in, create a token in Settings, and store it through a secure credential flow, never paste it into chat.
3. With the deployed URL and securely stored token configured, have the assistant create one test item and then change its status. Confirm both changes on the website and in Settings > Recent agent-made changes.
4. Only after that test passes call the write-back connection working. No such end-to-end test was performed for this delivery.

## Mac / Linux

```bash
cd qyad-v7
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
.venv/bin/python -m scripts.seed
.venv/bin/python -m uvicorn app.main:app --reload
```

API docs are at http://localhost:8000/docs while the server is running.
