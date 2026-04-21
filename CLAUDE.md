# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Assistant Gazelle V5 — Piano Technique Montréal management system. FastAPI (Python) backend + React/Vite frontend. Manages piano tuning/maintenance for 3 institutions (Vincent-d'Indy: 121 pianos, Place des Arts: 16 pianos, Orford: 61 pianos). Codebase is predominantly **French** (variable names, functions, UI text, docs).

## Commands

### Backend (Python)
```bash
pip install -r requirements.txt

# Run API (two equivalent options)
./start_api.sh                                                        # wraps python3 api/main.py with PYTHONPATH set
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload   # with auto-reload

# API docs: http://localhost:8000/docs   (FastAPI OpenAPI UI)
```

Port: defaults to `8000`; Render overrides via `PORT` env var. **Note:** `frontend/vite.config.js` proxies `/api/*` to `localhost:8001` — if you rely on the Vite proxy in dev, either run uvicorn on `8001` or update the proxy target. Otherwise set `VITE_API_URL=http://localhost:8000` and skip the proxy.

### Frontend (React/Vite)
```bash
cd frontend
npm install
npm run dev       # dev server on http://localhost:5174
npm run build     # production build to frontend/dist
npm run preview   # preview production build
```

### Testing
No formal test framework. No pytest config, no CI test jobs. "Tests" are integration scripts in `scripts/` and `test_*.py` at repo root that connect to real Supabase/Gazelle. Run individually with `python3 <script>.py`.

### Common Operations
```bash
python3 scripts/auto_refresh_token.py                            # refresh Gazelle OAuth token
python3 scripts/sync_to_supabase.py                              # full Gazelle → Supabase sync
python3 scripts/detect_dampp_chaser_installations.py --write     # PLS (Dampp-Chaser) badge detection
python3 -c "from modules.reports.service_reports import generate_reports; generate_reports()"  # Google Sheet report
```

## High-Level Architecture

### Backend (`api/`)
- **Entry point** `api/main.py`: creates the FastAPI app, validates env vars on startup, initializes singletons (`SupabaseStorage`, `GazelleAPIClient`), triggers institution auto-discovery, and starts APScheduler.
- **Dual route registration**: every router is `include_router`'d **twice** — once without a prefix (for dev with Vite proxy stripping `/api`) and once with `prefix="/api"` (for production direct-to-Render). When adding a new router, register both. Order matters: `humidity_alerts_router` must come before `institutions_router`, and `institutions_router` (dynamic `/{institution}/pianos`) must be last.
- **Per-feature routers**: `vincent_dindy.py`, `place_des_arts.py`, `institutions.py`, `inventaire.py`, `tableau_de_bord_routes.py` (3 sub-routers: alertes/pianos/système), `humidity_alerts_routes.py`, `assistant.py` / `assistant_routes.py` / `conversation_routes.py` (three AI conversation surfaces), `chat/` (Claude-powered chat service), `briefing_routes.py`, `service_records.py`, `admin.py`, etc.
- **Zoom SMS webhook** lives directly in `api/main.py` (`/api/zoom/webhook`) — handles Zoom's `endpoint.url_validation` HMAC challenge and forwards inbound SMS as email via `core/email_notifier.py`.

### Core Modules (`core/`)
- `gazelle_api_client.py` / `gazelle_api_client_incremental.py` — OAuth2 GraphQL client (singleton). Token source priority: Supabase `system_settings.gazelle_oauth_token` → fallback `config/token.json`.
- `supabase_storage.py` — REST/Postgrest wrapper for Supabase (singleton).
- `scheduler.py` + `scheduler_logger.py` — APScheduler background jobs; started/stopped from FastAPI lifecycle hooks.
- `humidity_alert_detector.py` — Humidity anomaly detection (housse retirée, débranché, réservoir vide, etc.).
- `email_notifier.py` — Resend-based email (migrated from SendGrid March 2026). Sender: `asutton@piano-tek.com`.
- `timezone_utils.py` — `MONTREAL_TZ` / `UTC_TZ` helpers. Gazelle API sends UTC ISO-8601; convert to `America/Montreal` before comparing or displaying.
- `gazelle_push_service.py`, `service_completion_bridge.py`, `notification_service.py`, `gmail_reader.py`, `gmail_sender.py`, `slack_notifier.py`, `zoom_sms.py`, `feature_flags.py`, `reference_manager.py`, `sync.py`.

### Frontend (`frontend/`)
React 18 + Vite 5, Material-UI 7.3, TailwindCSS 3.4, Axios, Supabase JS 2.89, Lucide icons. State is **React hooks only** — no Redux/Zustand. In production, Vite `base` is `/assistant-gazelle-v5/` (GitHub Pages); in dev it's `/`.

### Multi-Institution Architecture
3 institutions auto-discovered from Gazelle at startup (`discover_and_sync_institutions` in `api/institutions.py`):
- Vincent-d'Indy — `cli_9UMLkteep8EsISbG`
- Place des Arts — `cli_HbEwl9rN11pSuDEU`
- Orford — `cli_PmqPUBTbPFeCMGmz`

Backend registers dynamic per-institution routes via `institutions.py`; frontend renders dashboards dynamically. Two institutions (Vincent-d'Indy, Place des Arts) also have legacy dedicated modules (`api/vincent_dindy.py`, `api/place_des_arts.py`).

### Database (Supabase PostgreSQL)
Key tables: `gazelle_clients`, `gazelle_pianos`, `gazelle_appointments`, `gazelle_timeline_entries`, `institutions`, `humidity_alerts`, `notification_logs`, `system_settings`. Migrations in `sql/` (28+ SQL files). Dashboard: https://supabase.com/dashboard/project/beblgzvmjqkcillmcavk.

### Modules (`modules/`)
17 feature subdirs — most relevant: `modules/reports/service_reports.py` (Timeline Google Sheet generator with dedup and humidity/temperature extraction), `modules/sync_gazelle/`, `modules/alertes-rv/`, `modules/admin/`, `modules/inventaire/`, `modules/travel_fees/`.

## Conventions and Gotchas

### Data Protection — NEVER Overwrite
These three fields are **not** sourced from Gazelle on sync and must be preserved:
1. `gazelle_clients.tags` — manually assigned (e.g. `'institutional'`). If the Gazelle API response omits tags, keep the existing row's tags.
2. `gazelle_pianos.dampp_chaser_installed` — populated by the PLS detection scan, not by sync.
3. `system_settings.gazelle_oauth_token` — OAuth token; only the OAuth callback writes it.

### Sync Rules
- Prefer **incremental** sync (future data, 2025+). Never run a full historical backfill without explicit instruction.
- PLS (Dampp-Chaser) detection re-runs after every major sync.
- For service history, include type `SERVICE` (not only `NOTE` and `APPOINTMENT`) — `SERVICE` entries carry humidity readings.

### Timezone
Working tz is always `America/Montreal` (EST/EDT). Gazelle returns UTC ISO; always convert via `core/timezone_utils.py` before any comparison, date arithmetic, or display.

### Code Patterns
- **Singleton**: `GazelleAPIClient`, `SupabaseStorage` — initialized once at FastAPI startup.
- **Router per module**: each `api/*_routes.py` / feature module exposes `router`. New routers must be registered twice in `api/main.py` (with and without `/api` prefix).
- **French naming**: follow existing French naming — don't rename to English.

### Import Rules
- Import `requests` at module top-level only (avoid local shadowing in functions).
- Never extract piano model from free-text notes; use `piano_id`, `instrument_id`, or `Client Token` for SQL joins.

### Environment
Required `.env` vars: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` (or `SUPABASE_KEY`), `SUPABASE_ANON_KEY`, `GAZELLE_CLIENT_ID`, `GAZELLE_CLIENT_SECRET`, `ANTHROPIC_API_KEY`, `GOOGLE_CREDENTIALS_PATH` (→ `config/google-credentials.json`), `VITE_API_URL`. Optional: `OPENAI_API_KEY` (embeddings only), `ZOOM_SECRET_TOKEN`, `RESEND_API_KEY`, `PLANE_API_KEY`, `EMAIL_SMS_FORWARD`. `config/` is gitignored.

## CI/CD and Deployments
| Workflow | Trigger | Purpose |
|---|---|---|
| `deploy-frontend.yml` | push to `frontend/` | Build + deploy to GitHub Pages |
| `full_gazelle_sync.yml` | daily 02:00 UTC | Full Gazelle → Supabase sync |
| `hourly_appointments_sync.yml` | hourly 11–02 UTC | Incremental appointments sync |
| `humidity_alerts_scanner.yml` | scheduled | Humidity anomaly detection |
| `backfill_timeline_weekly.yml` | weekly | Timeline backfill |

Backend deploys: `git push` triggers automatic Render redeploy of `https://assistant-gazelle-v5-api.onrender.com`. Frontend: `https://suttonallan.github.io/assistant-gazelle-v5/`.
