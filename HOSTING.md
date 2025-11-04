# Blackline Forensics — Hosting & Deployment Guide

This guide consolidates installation requirements and actionable steps to run Blackline locally with Docker, and to deploy the backend and frontend for clients in production.

Use cases covered:
- Local development with Docker Compose (Postgres + API, optional MinIO/S3)
- Production backend on Cloud Run or Render (containerized FastAPI)
- Production frontend on Netlify or GitHub Pages (static site)

If you prefer a VM + Nginx + Gunicorn setup, see also `documentation/deploy.md`.

## Requirements

- Docker Engine 24+ and Docker Compose v2
- For building the frontend locally: Node 18+
- For building the backend without Docker: Python 3.11+
- For Cloud Run: Google Cloud SDK (`gcloud`) and a GCP project
- For Render: Render account and GitHub access to the repo
- For Netlify: Netlify account and GitHub access to the repo

Tip for zsh: this repo path contains `!` — quote or escape paths in shell commands (e.g., `"/Users/you/\!PROJECTS/..."`).

## Environment and Secrets

Backend reads environment variables (see `backend/.env.example`):
- `BL_JWT_SECRET` — required in production (unique per client)
- `DATABASE_URL` — Postgres recommended (SQLite supported for simple cases)
- `STORAGE_BACKEND` — `local` or `s3`
- When `s3`: `STORAGE_BUCKET`, `AWS_REGION`, optional `STORAGE_PREFIX`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, etc.
- Optional: `DATA_ROOT` (defaults to `backend/data` locally and `/tmp/data` on Cloud Run)

Frontend consumes at build time:
- `VITE_API_BASE` — e.g., `https://api.client.tld`

In production, keep secrets in your platform’s secret manager (Cloud Run secrets/vars, Render environment, Netlify build env). Do not commit `.env` files.

## Admin Account (debug admin)

For local development, the backend can seed and maintain a persistent Admin user so you always have an admin account available. This is controlled entirely by environment variables and should be disabled in production.

- Defaults (from `backend/.env.example`):
  - `BL_ENABLE_DEBUG_ADMIN=1`
  - `BL_DEBUG_ADMIN_USER=admin`
  - `BL_DEBUG_ADMIN_EMAIL=admin@local`
  - `BL_DEBUG_ADMIN_PASSWORD=admin`

- Change the seeded admin username/email/password:
  - Edit `backend/.env` and set the variables above to your desired values.
  - Restart the backend (container or process). On startup, the service runs a seeding step that:
    - Creates the user if it doesn’t exist with plan `Admin`.
    - Ensures the user remains `Admin` and syncs email; updates password if provided.
  - Implementation reference: `backend/src/auth.py` (`ensure_debug_admin`). The special debug admin cannot be demoted via the admin API.

- Disable in production:
  - Set `BL_ENABLE_DEBUG_ADMIN=0` in your production environment (Cloud Run/Render). Do not ship a default admin.
  - Promote real users to Admin using the in‑app DB Viewer (Admins only) or the admin API (see below).

- Promote/demote users (non‑debug accounts):
  - UI: open the DB Viewer (visible to Admins) and click “Make Admin” / “Make Guest”.
  - API: `POST /api/admin/users/{username}/plan` with JSON body `{ "plan": "Admin" | "Guest" }`.

Notes:
- Changing `BL_DEBUG_ADMIN_USER` to a new value will create a new admin account for that username; the old account remains untouched. Clean up old accounts manually if needed.
- Always set a unique, strong `BL_JWT_SECRET` per environment. This is independent from user passwords.

## Quick Start: Local with Docker Compose

1) Copy and adjust env for backend:
```
cp backend/.env.example backend/.env
# Set BL_JWT_SECRET and, if using S3 locally with MinIO, set AWS_*/STORAGE_* accordingly.
```

2) Start database and API (CPU-friendly image):
```
docker compose up -d postgres api
```
This exposes API on `http://localhost:8000` and persists data at `backend/data`.

3) Optional: MinIO (S3-compatible) + pgAdmin
```
# Start S3-compatible storage and provision bucket
docker compose --profile object-storage up -d minio minio-init

# Start pgAdmin UI (http://localhost:5050, admin@local / admin)
docker compose --profile devtools up -d pgadmin
```

4) Frontend (dev):
```
cd front-end
npm ci || npm install
npm run dev
```
Set `VITE_API_BASE` in `.env` or run with `VITE_API_BASE=http://localhost:8000`.

Health checks:
- Backend: `curl http://localhost:8000/api/health`
- Build info: `curl http://localhost:8000/api/buildinfo`

## Docker: Build and Run Backend (standalone)

CPU-friendly build (recommended for most clients):
```
docker build -f backend/Dockerfile.lite -t blackline-api:lite ./backend
docker run --rm -p 8000:8000 \
  --env-file backend/.env \
  -v "$(pwd)/backend/data:/app/backend/data" \
  blackline-api:lite
```

GPU build (CUDA runtime) when required:
```
docker build -f backend/Dockerfile -t blackline-api:cuda ./backend
docker run --rm -p 8080:8080 \
  --gpus all \
  --env-file backend/.env \
  blackline-api:cuda
```
Note: ensure `$PORT` alignment. Our images default to `${PORT:-8080}`; Compose maps to `8000`. Standardize on one port per environment.

## Production: Backend on Cloud Run

Reference: `backend/DEPLOY_CLOUDRUN.md` and `deployment/cloudrun/service.yaml`.

High-level steps:
1) Build and push the image:
```
gcloud builds submit --tag gcr.io/PROJECT_ID/blackline-api:latest ./backend 
```
2) Deploy:
```
gcloud run deploy blackline-api \
  --image gcr.io/PROJECT_ID/blackline-api:latest \
  --region YOUR_REGION \
  --platform managed \
  --allow-unauthenticated \
  --cpu 2 --memory 4Gi --timeout 600 --concurrency 1
```
3) Set env vars (via Console or CLI): `BL_JWT_SECRET`, `DATABASE_URL`, `STORAGE_BACKEND`, and S3 variables as needed.

4) Custom domain: map `api.client.tld` to the service; issue TLS.

Operational notes:
- Models live under `/app/backend/models`; the Dockerfile copies the `backend/` folder into the image.
- Default data root on Cloud Run is `/tmp/data` (ephemeral). Use external storage for assets (S3) and a managed DB.
- See `/api/buildinfo` for ffmpeg/torch diagnostics.

## Production: Backend on Render

Reference: `documentation/deploy.md`.

- Root Directory: `backend`
- `backend/runtime.txt` pinning Python 3.11 is already present
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn backend.src.api_server:app --host 0.0.0.0 --port $PORT`
- Environment: set `BL_JWT_SECRET`, DB URL, and storage variables

## Production: Frontend Hosting

Netlify (recommended):
- Repo contains `netlify.toml` (base=`front-end`, publish=`dist`, SPA fallback)
- Set `VITE_API_BASE` (Site settings → Build & Deploy → Environment)
- Connect `app.client.tld` and enable TLS
- Optional: enable `/api/*` proxy in `netlify.toml` and set `VITE_API_BASE` to your site origin to avoid CORS

GitHub Pages:
- Workflow in `.github/workflows/deploy-pages.yml` builds `front-end` and deploys
- Configure `VITE_API_BASE` via Actions Secrets/Variables
- Custom domain supported via `front-end/public/CNAME`

Static server (Nginx):
- Build: `cd front-end && VITE_API_BASE=https://api.client.tld npm run build`
- Serve `front-end/dist` and reverse proxy `/api/` to backend (see `documentation/deploy.md` for an example server block)

## S3/MinIO Configuration

When using S3 for uploads and downloads:
- Set backend env: `STORAGE_BACKEND=s3`, `STORAGE_BUCKET`, `AWS_REGION`, and credentials/role
- Optional MinIO for local dev: `docker compose --profile object-storage up -d minio minio-init`
- Example bucket CORS (replace origin):
```
[
  {"AllowedHeaders":["*"],"AllowedMethods":["PUT","GET","HEAD"],"AllowedOrigins":["https://app.client.tld"],"ExposeHeaders":["ETag"],"MaxAgeSeconds":3000}
]
```

## CORS and Security

- In production, restrict CORS allow_origins in `backend/src/api_server.py` to your frontend origin(s)
- Rotate `BL_JWT_SECRET` per client; disable debug admin in prod (`backend/.env.example` shows dev-only flags)
- Keep secrets in your platform’s secret store; audit public buckets/ACLs if using `STORAGE_PUBLIC_BASE_URL`

## Health and Diagnostics

- `/api/health` — readiness
- `/api/buildinfo` — ffmpeg/torch/opencv presence, model files, runtime env
- `/status` — torch/cuda info (when using DL builds)

## Per-Client Checklist

- Domains: `app.client.tld` (frontend), `api.client.tld` (backend)
- Backend: Cloud Run or Render; set env vars and sizing (2 vCPU / 4GiB RAM is a good baseline)
- Frontend: build with `VITE_API_BASE` pointing at backend; deploy to Netlify/Pages
- Storage: S3 bucket + CORS; set `STORAGE_PREFIX` for isolation per client
- Database: managed Postgres per client (or at least per-environment)
- CORS/Security: tighten in backend; disable debug admin; verify TLS end-to-end

## Troubleshooting

- CORS errors: ensure `VITE_API_BASE` matches backend origin and backend CORS allows your frontend domain
- 403 on S3 PUT: check bucket CORS and that presigned method is `PUT`
- Large uploads/timeouts: front with Nginx; increase `client_max_body_size` and backend request timeouts (Cloud Run `--timeout`)
- Missing ffmpeg/torch: verify `/api/buildinfo`; for Cloud Run, use the provided requirements and environment in `backend/DEPLOY_CLOUDRUN.md`

---

Related files:
- `docker-compose.yml` — local services (Postgres, API, MinIO, pgAdmin)
- `backend/Dockerfile.lite` and `backend/Dockerfile` — backend images
- `backend/DEPLOY_CLOUDRUN.md` — Cloud Run specifics
- `deployment/cloudrun/service.yaml` — Knative service spec template
- `documentation/deploy.md` — VM/Nginx, Netlify, Render walkthroughs
- `netlify.toml` — Netlify build + SPA fallback
- `.github/workflows/deploy-pages.yml` — GitHub Pages workflow
