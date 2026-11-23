# Optional 15-minute keep-alive

First identify the hosting provider and check its current rules. An always-on VPS normally does not sleep for inactivity. Your host may be a sleeping app/container/free development service rather than an always-on VPS. If the whole VM powers off or cannot receive HTTP while paused, an ordinary ping cannot wake it. Ask the provider what resets its idle timer. Do not use pings to evade a host policy or paid-plan limit.

The app already has `GET /api/v1/health`: public, no auth, only `{"ok":true}`, no user data and no database query. Production middleware rate limits it. Use the **direct backend HTTPS URL**, not a cached homepage, so a request reaches the app. Cold starts can exceed a monitor timeout; a failed check is not proof that data is lost.

## Cloudflare Worker, optional

This is a separate scheduled Worker, not the Pages frontend function. It makes one HTTP check every 15 minutes, 96 checks/day. No private API key or resume data is involved. Cloudflare plan limits and provider terms still apply. It has not been deployed or tested on your account.

1. Open `ops/keepalive/wrangler.toml` and replace only `HEALTH_URL` with your direct backend URL, such as `https://api.YOUR-DOMAIN/api/v1/health`. Use your real hostname.
2. From PowerShell, after installing Node LTS:

```powershell
cd .\ops\keepalive
npx wrangler login
npx wrangler deploy
```

3. Check the Worker dashboard's trigger and invocation logs. Cron uses UTC. `*/15 * * * *` runs at minutes 0, 15, 30 and 45. Trigger updates may take up to 15 minutes to propagate; scheduled invocations can be missed before propagation completes.
4. Confirm with your host that these requests reset its inactivity counter. If not, use the provider's supported always-on setting/plan rather than increasing ping frequency.
5. To stop, change `crons = []` and redeploy, or delete the separate keep-alive Worker in Cloudflare. Merely commenting out the cron field is not the documented disable route.

This checks HTTP health, not private DB access or full application correctness. It does not send alerts by itself. Inspect failures in Cloudflare logs or use a monitor that alerts you.

## Free uptime monitor alternative

UptimeRobot offers a free monitoring option. Verify the current plan's interval/usage terms at https://uptimerobot.com/ before enabling it. Create an HTTP(S) monitor for your direct `/api/v1/health` URL, select a 15-minute check interval if offered by your plan, and configure your own alert channel. No auth token is needed. Do not use both the Worker and monitor for the same keep-alive unless you deliberately want two check sources.

## Restart is separate from keep-alive

The included systemd service uses `Restart=on-failure`, and `systemctl enable --now qyad` starts it on boot. This does not keep a host awake. If you later choose Docker, use an appropriate restart policy such as `unless-stopped` and persist the database outside the container. Docker deployment is now included in v9.2; see the root DEPLOY-DOCKER.txt. A restart policy cannot override provider suspension.

Sources: https://developers.cloudflare.com/workers/configuration/cron-triggers/ and https://uptimerobot.com/ . No live monitor was created for you.

## InstaBox-specific update in v9.2

Current InstaBox docs say a request to a published HTTPS port wakes a machine that auto-paused after 30 idle minutes. A manually paused/stopped machine stays offline. You may not need keep-alive at all; test the normal wake behavior first. See `DEPLOY-DOCKER.txt`. Source: https://instabox.sh/docs/access/ports . Docker health checks happen inside the VM and are not external keep-alive requests.
