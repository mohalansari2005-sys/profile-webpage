# Backend production deployment

The chat backend (`/backend`) runs locally via `docker-compose.yml`. This document
covers taking it to production: a Hostinger VPS, a domain, and Caddy for automatic
HTTPS, so the Vercel-hosted frontend (a static export, `output: "export"`) can call it
directly over HTTPS from the browser.

## 1. Provision a VPS

- Hostinger, KVM plan, Ubuntu 24.04 image (any VPS with Docker support works the same
  way — Hostinger isn't required by anything in this repo).
- During creation, add your local machine's SSH public key
  (`~/.ssh/id_ed25519.pub` or similar) as an authorized key for the root/deploy user.
- Note the VPS's public IPv4 address.

## 2. Point a domain at it

- Any registrar. Create an A record for a subdomain, e.g. `api.yourdomain.com`,
  pointing at the VPS's public IP.
- Caddy (step 5) needs this to resolve before it can issue a Let's Encrypt cert.

## 3. Bootstrap the server

```bash
ssh root@<vps-ip>
apt update && apt upgrade -y
curl -fsSL https://get.docker.com | sh
apt install -y ufw
ufw allow 22
ufw allow 80
ufw allow 443
ufw enable
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

GEMINI_API_KEY=<your Gemini API key>
GEMINI_MODEL=gemini-3.5-flash
GEMINI_FAST_MODEL=gemini-3.5-flash-lite
GEMINI_EMBED_MODEL=gemini-embedding-001

POSTGRES_DB=chat
POSTGRES_USER=chat
POSTGRES_PASSWORD=<new random string>
POSTGRES_HOST=db
REDIS_URL=redis://redis:6379/0

IP_HASH_SALT=<new random string>
CHAT_RATE=10/min
CHAT_DAILY_CAP=200
CORS_ORIGINS=https://profile-webpage-liart.vercel.app

DOMAIN=<your domain, e.g. api.yourdomain.com>
```

`CORS_ALLOWED_ORIGIN_REGEXES` in `backend/config/settings.py` already whitelists any
`*.vercel.app` subdomain, so Vercel preview deploys work without extra config; the
`CORS_ORIGINS` value above is for the production domain specifically.

`DOMAIN` is read by both the `web` and `caddy` services (via `env_file: backend/.env`)
and substituted into `Caddyfile`'s `{$DOMAIN}`.

## 5. Deploy

```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec web python manage.py migrate
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

## Updating the deployment later

```bash
cd profile-webpage
git pull
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec web python manage.py migrate
```
