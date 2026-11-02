# Backend production deployment

The chat backend (`/backend`) runs locally via `docker-compose.yml`. This document
covers running it in production: a Hetzner VPS, a Cloudflare-managed domain, and Caddy
for automatic HTTPS, so the Vercel-hosted frontend (a static export, `output: "export"`)
can call it directly over HTTPS from the browser.

## 1. Provision a VPS

- Any VPS with Docker support works the same way; this deployment uses a Hetzner CPX
  instance running Ubuntu.
- Create a non-root sudo user (e.g. `deploy`) and disable SSH password auth — don't SSH
  in as root day to day.
- Note the VPS's public IPv4 address.

## 2. Point a domain at it (Cloudflare)

- Create an A record for a subdomain, e.g. `api.yourdomain.com`, pointing at the VPS's
  public IP. **Proxied (orange cloud)** is fine — Cloudflare passes port 80/443 through,
  so Caddy's Let's Encrypt HTTP-01 challenge still works.
- Cloudflare SSL/TLS mode: start at **Full**, then switch to **Full (strict)** once
  Caddy has issued its own certificate for the subdomain (step 5) — otherwise Cloudflare
  will reject the origin's self-signed/absent cert during the gap.

## 3. Bootstrap the server

```bash
ssh deploy@<vps-ip>
sudo apt update && sudo apt upgrade -y
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker deploy
sudo apt install -y ufw
sudo ufw allow OpenSSH
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

Port 8000 (Django) is intentionally never opened on the firewall — `docker-compose.prod.yml`
only `expose`s it to other containers, not the host, so Caddy is the only way in.

## 4. Get the code and configure secrets

```bash
git clone https://github.com/mohalansari2005-sys/profile-webpage.git
cd profile-webpage
```

Create `backend/.env` (gitignored, never committed) with production values:

```
DJANGO_SECRET_KEY=<new random string, e.g. `openssl rand -hex 32`>
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=<your domain, e.g. api.yourdomain.com>

OPENAI_API_KEY=<your OpenAI key>
# No OPENAI_*MODEL lines: the defaults in backend/config/settings.py apply and
# move with the code. A pinned name kept the retired gpt-4.1-nano in use.

POSTGRES_DB=chat
POSTGRES_USER=chat
POSTGRES_PASSWORD=<new random string>
POSTGRES_HOST=db
REDIS_URL=redis://redis:6379/0

IP_HASH_SALT=<new random string>
CHAT_RATE=10/min
CHAT_DAILY_CAP=200
CORS_ORIGINS=<your production frontend origin, e.g. https://yourdomain.com>

DOMAIN=<your domain, e.g. api.yourdomain.com>
```

`CORS_ALLOWED_ORIGIN_REGEXES` in `backend/config/settings.py` already whitelists any
`*.vercel.app` subdomain, so Vercel preview deploys work without extra config; the
`CORS_ORIGINS` value above is for the production domain specifically.

`CORS_ORIGINS` is also what analytics treats as the live site: list every origin
the site is served from, exactly (comma-separated, e.g. both the `www.` and the
bare domain if both serve pages rather than redirect). Questions from any other
origin, or none (the canary, curl), are answered but logged as synthetic and left
off the dashboard; page views from any other origin are not recorded.

`DOMAIN` is read by both the `web` and `caddy` services (via `env_file: backend/.env`)
and substituted into `Caddyfile`'s `{$DOMAIN}`.

## 5. Deploy

```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec web python manage.py migrate
docker compose -f docker-compose.prod.yml exec web python manage.py ingest_content
```

Caddy will automatically request and renew a Let's Encrypt certificate for `$DOMAIN`
once DNS resolves to this server.

## 6. Verify

```bash
docker compose -f docker-compose.prod.yml logs web    # confirm clean startup, no migration errors
curl -X POST https://<domain>/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{"question":"test","history":[]}'
```

A JSON response (`{"answer": ..., "sources": ..., "refused": ...}`) confirms TLS, CORS,
and the full request chain work.

## 7. Point the frontend at it

In the Vercel project dashboard, set for the **Production** environment:

```
NEXT_PUBLIC_CHAT_API_URL=https://<domain>/api/chat/
```

This is inlined into the static export at build time, so an env-var-only change needs
a rebuild — push a commit, or use Vercel's "Redeploy" button. Then confirm on the live
site that the Ask section renders, a real question returns an answer, and the browser
devtools Network tab shows no CORS errors on the `api/chat/` request.

## 8. Analytics dashboard (optional)

Page views are recorded as soon as this backend and a frontend built with
`NEXT_PUBLIC_CHAT_API_URL` are deployed; the deploy's `migrate` creates the
table. The dashboard that shows them stays off (a 404) until it has a password.
To turn it on, add a line to `backend/.env` on the server:

```
DASHBOARD_PASSWORD=<new random string, e.g. `openssl rand -hex 24`>
```

and recreate `web` so it reads the file again (`restart` would keep the old
environment):

```bash
docker compose -f docker-compose.prod.yml up -d --force-recreate web
```

Then open `https://<domain>/dashboard/`. The browser asks for a username and a
password: the username can be anything, the password is the one above.
`?days=7`, `30`, `90` or `365` picks the range. Days are counted in
`Asia/Riyadh` unless `DASHBOARD_TZ` says otherwise.

Service errors are chat turns logged with `ChatLog.unavailable` (the AI provider
failed). Chat numbers leave out synthetic questions (`ChatLog.synthetic`): the
daily canary, curl checks and Vercel previews; see `CORS_ORIGINS` above. Until
`migrate` has run on a deploy, page views are dropped with one WARNING line each
in `docker compose logs web`, not a 500.

To keep your own visits out of the numbers, open the site once in each browser
you use with `?analytics=off` (e.g. `https://yourdomain.com/?analytics=off`);
`?analytics=on` undoes it. The page takes the parameter back out of the address
bar once it has read it, so a link you copy afterwards does not opt out whoever
opens it.

Automated QA against the live site counts as a real visitor too: Playwright's
desktop Chrome does not identify itself as headless, so the bot filter lets it
through. Opt that browser out first, by opening a page with `?analytics=off`
or by setting the flag before any page script runs:
`page.addInitScript(() => localStorage.setItem("analytics", "off"))`.

## Updating the deployment

Pushing to `main` with changes under `backend/**`, `docker-compose.prod.yml`, or
`Caddyfile` triggers `.github/workflows/deploy-backend.yml`, which SSHes into the VPS
and runs the same commands below. To update manually instead:

```bash
cd profile-webpage
git pull
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec web python manage.py migrate
docker compose -f docker-compose.prod.yml exec web python manage.py ingest_content
```
