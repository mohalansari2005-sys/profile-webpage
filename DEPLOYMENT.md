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

Then create a second, smaller `.env` in the repo root, next to `docker-compose.prod.yml`
(also gitignored):

```bash
printf 'POSTGRES_PASSWORD=%s\n' '<the same value as in backend/.env>' > .env
chmod 600 .env backend/.env
```

Compose needs this one for itself. The `db` service's `${POSTGRES_PASSWORD}` (and
`${POSTGRES_DB}`/`${POSTGRES_USER}`, which default to `chat`) are substituted by compose
when it reads the file, from the shell or this root `.env` — **never from
`backend/.env`**, which only becomes the `web` and `caddy` containers' environment.
Without it every compose command stops with `required variable POSTGRES_PASSWORD is
missing a value`. Keep the two files in step: if `backend/.env` sets a `POSTGRES_DB`
or `POSTGRES_USER` other than `chat`, put the same line here, or Postgres creates one
user and `web` logs in as another.

`CORS_ALLOWED_ORIGIN_REGEXES` in `backend/config/settings.py` already whitelists any
`*.vercel.app` subdomain, so Vercel preview deploys work without extra config; the
`CORS_ORIGINS` value above is for the production domain specifically.

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

## Updating the deployment

Pushing to `main` with changes under `backend/**`, `docker-compose.prod.yml`, or
`Caddyfile` triggers `.github/workflows/deploy-backend.yml`, which SSHes into the VPS
and runs the same commands below under `set -e`: the first command that fails fails
the job, and the chat canary (which runs after a successful deploy) is skipped. A red
deploy means the server may be part-way through — check `git log -1` and
`docker compose -f docker-compose.prod.yml ps` there. To update manually instead:

```bash
cd profile-webpage
git pull
docker compose -f docker-compose.prod.yml exec -T caddy caddy reload --config - --adapter caddyfile < Caddyfile
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec web python manage.py migrate
docker compose -f docker-compose.prod.yml exec web python manage.py ingest_content
```

The `caddy reload` line is how a `Caddyfile` change reaches Caddy. `up` does not
recreate the `caddy` container for it, and because `git pull` replaces the file rather
than rewriting it, the container's single-file bind mount keeps showing the old one —
so the file goes in on stdin. `caddy reload` validates it first and keeps the running
config if it is invalid; stop there if it fails.

It runs before `up` because the `Caddyfile` decides which headers Django reads the
visitor's address from. The other way round, a freshly built `web` sat behind the old
proxy config, which let a visitor choose their own per-IP bucket — until the end of the
deploy, or for good if `migrate` or `ingest_content` failed first. The current file
sets both `X-Real-IP` and `X-Forwarded-For`, so whichever Django is running reads the
visitor correctly.

The `Caddyfile` trusts Cloudflare's `CF-Connecting-IP` header from Cloudflare's
published IP ranges only, so the chat's per-IP limit sees the visitor rather than a
Cloudflare edge. The ranges are listed by hand with the date they were fetched;
refresh them from <https://www.cloudflare.com/ips/> now and then. CI's `caddy` job
runs `caddy validate` on every pull request, so a bad edit is caught before it reaches
the server — where a Caddy restart would load it from disk and keep failing.
