# Deployment Guide

MarketFlow has two deployable parts:

- **`server/`** — FastAPI app, deployed to **Render** (Docker web service) with a Postgres database and Redis cache.
- **`client/`** — React + Vite app, deployed to **Render** (static site).

The client reads the API host from `VITE_SERVER_HOST` (set as a Render static site env var), and the server reads allowed CORS origins from `CLIENT_ORIGINS` (set as a Render web service env var) — neither URL is hardcoded, so redeploying either side to a new URL just means updating the corresponding env var.

---

## 1. Prerequisites

- A [Render](https://render.com) account (for the API, Postgres, Redis, and the client static site).
- Repo pushed to GitHub (Render deploys from a connected Git repo).

---

## 2. Deploy the database and cache (Render)

1. In the Render dashboard, click **New → PostgreSQL**.
   - Name it (e.g. `marketflow-db`), pick a region close to where the API will run.
   - Once created, copy the **Internal Database URL** — you'll use it as `DB_URL`.
2. Click **New → Key Value** (Render's managed Redis).
   - Name it (e.g. `marketflow-cache`).
   - Note the **Host** and **Port** from its connection info — used as `CACHE_HOST` / `CACHE_PORT`.

---

## 3. Deploy the API (Render Web Service)

1. Click **New → Web Service** and connect the GitHub repo.
2. Set **Root Directory** to `server`.
3. Render will detect `server/Dockerfile` automatically — choose **Docker** as the environment.
4. Set the instance type/region, then configure **Environment Variables** (do not use `.env.dev.sample` values in production):

   | Key | Value |
   |---|---|
   | `ADMIN_USERNAME` | your chosen admin username |
   | `ADMIN_PASSWORD` | a strong admin password |
   | `SECRET` | a long random string (used to sign JWTs) |
   | `DB_URL` | Internal Database URL from step 2 |
   | `CACHE_HOST` | Redis host from step 2 |
   | `CACHE_PORT` | Redis port from step 2 |
   | `CLIENT_ORIGINS` | comma-separated list of allowed client origins, e.g. `https://<your-client>.vercel.app` |

5. Deploy. Render will build the Docker image and start it with:
   ```
   fastapi run ./main.py --host 0.0.0.0 --port $PORT
   ```
   Render injects its own `PORT` env var at runtime (it does **not** use the Dockerfile's `EXPOSE` to pick the port) — `server/Dockerfile`'s `CMD` reads `$PORT` for this reason. If the service ever 404s/times out on every route, the most likely cause is the app listening on the wrong port, not a routing bug.
6. Once live, note the public URL Render assigns, e.g. `https://<your-service>.onrender.com`.

> **Note:** the app calls `SQLModel.metadata.create_all(engine)` on startup (`server/main.py`), so tables are created automatically on first boot — no separate migration step is needed.

---

## 4. Point the client at the API

No code change is needed — the client reads the API host from the `VITE_SERVER_HOST` env var (see `client/src/lib/utils.ts`). Set it as a Render static site env var in the next step, e.g.:

```
VITE_SERVER_HOST=<your-service>.onrender.com
```

(Note: no `https://` prefix — the client adds that itself.)

---

## 5. Deploy the client (Render Static Site)

1. Click **New → Static Site** and connect the same GitHub repo.
2. Set **Root Directory** to `client`.
3. Configure the build settings:
   - **Build Command:** `npm install && npm run build`
   - **Publish Directory:** `dist`
4. Add an **Environment Variable**:

   | Key | Value |
   |---|---|
   | `VITE_SERVER_HOST` | `<your-service>.onrender.com` (no `https://` prefix) |

5. Client-side routing (`react-router`) needs every path to fall back to `index.html`, or deep links like `/admin` or `/stocks` 404 on a hard refresh. `client/public/_redirects` handles this:
   ```
   /*    /index.html   200
   ```
   Vite copies anything in `public/` into `dist/` on build, so Render picks this up automatically — no dashboard config needed. (This replaces `client/vercel.json`, which only applies if deploying to Vercel instead.)
6. Deploy. Render gives you a `*.onrender.com` URL (add a custom domain under Settings if desired).
7. Go back to the API service and set `CLIENT_ORIGINS` to this URL (e.g. `https://<your-client>.onrender.com`), then redeploy the server so CORS allows requests from it.

---

## 6. Verify

1. Open the deployed client URL.
2. Confirm it can reach the API (check the Network tab for successful calls to the `VITE_SERVER_HOST` value).
3. Test login/signup and a stock action to confirm the DB and Redis cache are wired correctly.
4. On Render, check the web service logs for errors (`DB_URL`/`CACHE_HOST` typos are the most common issue).

---

## 7. Redeploying after changes

- **Server:** push to the connected branch — Render auto-deploys (or trigger manually from the dashboard).
- **Client:** push to the connected branch — Render auto-deploys. Remember to update the `VITE_SERVER_HOST` env var first if the API URL changed, then trigger a redeploy (env var changes require a rebuild to take effect since Vite bakes them in at build time).

---

## Local development (for reference)

`compose.yaml` at the repo root spins up all four services together for local dev:

```
docker compose up
```

This runs the client (`:3000`), server (`:8000`), Redis (`:6379`), and Postgres (`:5432`) using `server/.env.dev.sample` for the server's env vars and an inline `VITE_SERVER_HOST=localhost:8000` for the client — it is **not** used in production deployment, but is useful to sanity-check the app before deploying.
