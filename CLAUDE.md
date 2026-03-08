# CLAUDE.md - Assistant Gazelle V5

## Project Overview

Piano Technique Montreal management system. Backend FastAPI (Python) + Frontend React/Vite. Manages piano tuning/maintenance for 3 institutions (Vincent-d'Indy: 121 pianos, Place des Arts: 16 pianos, Orford: 61 pianos).

## Quick Start

```bash
# Backend (Terminal 1)
pip install -r requirements.txt
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend (Terminal 2)
cd frontend && npm install && npm run dev
# Frontend runs on http://localhost:5174, API on http://localhost:8000
```

## Architecture

```
assistant-gazelle-v5/
├── api/                    # FastAPI backend
│   ├── main.py             # Entry point, CORS, router registration
│   ├── chat/               # AI chat service (Claude-powered)
│   │   ├── service.py      # Main chat logic
│   │   ├── schemas.py      # Pydantic models
│   │   └── router.py       # Chat routes
│   ├── institutions.py     # Dynamic multi-institution routes
│   ├── vincent_dindy.py    # VDI-specific endpoints
│   ├── place_des_arts.py   # PDA-specific endpoints
│   ├── inventaire.py       # Inventory management
│   ├── assistant.py        # Conversational AI routes
│   ├── admin.py            # Admin panel endpoints
│   └── *_routes.py         # Feature-specific routers
├── core/                   # Core Python modules
│   ├── gazelle_api_client.py      # OAuth2 GraphQL client for Gazelle API
│   ├── supabase_storage.py        # Supabase REST wrapper (singleton)
│   ├── scheduler.py               # APScheduler background jobs
│   ├── email_notifier.py          # Email via Resend
│   └── humidity_alert_detector.py # Humidity anomaly detection
├── frontend/               # React 18 + Vite 5
│   ├── src/
│   │   ├── App.jsx         # Main app component
│   │   ├── components/     # 40+ React components
│   │   ├── api/            # API client utilities
│   │   ├── utils/          # Helpers
│   │   └── config/         # Frontend configuration
│   └── package.json
├── modules/                # Feature-specific modules (17 subdirs)
├── scripts/                # Utility and maintenance scripts
├── sql/                    # Database migrations (28+ files)
├── docs/                   # Documentation (23 guides, mostly French)
├── config/                 # Credentials (gitignored)
├── .github/workflows/      # CI/CD (4 workflows)
└── requirements.txt        # Python dependencies
```

## Tech Stack

**Backend:** FastAPI 0.104+, Pydantic 2.0+, Supabase 2.0+, APScheduler 3.10+, Anthropic SDK 0.39+ (Claude AI), OpenAI 1.3+ (embeddings only), Resend 2.0+ (email), gspread (Google Sheets)

**Frontend:** React 18, Vite 5, Material-UI 7.3, TailwindCSS 3.4, Axios, Supabase JS 2.89, Lucide React icons

**Infrastructure:** Render (backend), GitHub Pages (frontend), Supabase PostgreSQL (database)

## Key Conventions

### Language
- **French naming** throughout codebase: variables, functions, comments, UI text are in French
- Documentation is mostly in French

### Code Patterns
- **Singleton pattern** for GazelleAPIClient and SupabaseStorage
- **Dual route registration** in `api/main.py`: routes registered both with and without `/api` prefix (dev vs prod compatibility)
- **Router architecture**: each module exposes a `router` for FastAPI inclusion
- **React hooks** (useState, useEffect) for state management — no Redux/Zustand

### Timezone Rules
- Working timezone is always `America/Montreal` (EST/EDT)
- Gazelle API sends dates in ISO UTC format
- Always convert UTC to Montreal time before comparisons or display
- Use `core/timezone_utils.py` for conversions

### Data Protection — NEVER Overwrite
1. `gazelle_clients.tags` — manually assigned (e.g., 'institutional')
2. `gazelle_pianos.dampp_chaser_installed` — detected by automatic scan
3. `system_settings.gazelle_oauth_token` — API token

### API Communication
- **Gazelle API**: GraphQL private endpoint with OAuth2 bearer tokens
- **Token storage**: Supabase `system_settings` table (priority), fallback `config/token.json`
- **Supabase**: PostgreSQL via REST API wrapper (`core/supabase_storage.py`)
- **Email**: Resend (migrated from SendGrid, March 2026). Sender: `asutton@piano-tek.com`

### Sync Rules
- Prioritize incremental sync (future data, 2025+). Never run full historical backfill without explicit instruction
- Sync preserves manual tags — if API doesn't return tags, keep existing ones
- PLS (Dampp-Chaser) detection runs after each major sync

## Production URLs

| Service | URL |
|---------|-----|
| Backend API (Render) | `https://assistant-gazelle-v5-api.onrender.com` |
| Frontend (GitHub Pages) | `https://suttonallan.github.io/assistant-gazelle-v5/` |
| Supabase | `https://beblgzvmjqkcillmcavk.supabase.co` |

## CI/CD Workflows

1. **`deploy-frontend.yml`** — Triggers on push to `frontend/`, deploys to GitHub Pages
2. **`hourly_appointments_sync.yml`** — Hourly (11h-2h UTC), syncs appointments
3. **`full_gazelle_sync.yml`** — Daily at 2h UTC, full Gazelle→Supabase sync
4. **`humidity_alerts_scanner.yml`** — Regular humidity alert detection

After backend commits, `git push` triggers automatic Render redeploy.

## Environment Variables

Required in `.env` (see `.env.example`):
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_ANON_KEY`
- `GAZELLE_CLIENT_ID`, `GAZELLE_CLIENT_SECRET`
- `GOOGLE_CREDENTIALS_PATH` (path to `config/google-credentials.json`)
- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY` (optional, embeddings only)
- `VITE_API_URL` (frontend API base URL)

## Database (Supabase PostgreSQL)

### Key Tables
- `gazelle_clients` — Clients with manual tags
- `gazelle_pianos` — Pianos with PLS badge detection
- `gazelle_appointments` — Appointment sync with notification memory columns
- `gazelle_timeline_entries` — Service history
- `institutions` — Auto-discovered institution configs
- `humidity_alerts` — Detected humidity anomalies
- `notification_logs` — Email notification audit trail
- `system_settings` — Tokens and system configuration

## Multi-Institution Architecture

3 primary institutions auto-discovered from Gazelle API at startup:
- **Vincent-d'Indy** (École de musique) — `cli_9UMLkteep8EsISbG`
- **Place des Arts** (Concert venue) — `cli_HbEwl9rN11pSuDEU`
- **Orford** (Orford Musique) — `cli_PmqPUBTbPFeCMGmz`

Frontend renders institution-specific dashboards dynamically. Backend creates routes per institution.

## Testing

No formal test framework (no pytest config). Tests are manual integration scripts in `scripts/` and root directory that connect to real Supabase/Gazelle. No automated tests in CI.

## Common Operations

```bash
# Refresh OAuth token
python3 scripts/auto_refresh_token.py

# Sync Gazelle → Supabase
python3 scripts/sync_to_supabase.py

# Detect PLS installations
python3 scripts/detect_dampp_chaser_installations.py --write

# Generate Google Sheet report
python3 -c "from modules.reports.service_reports import generate_reports; generate_reports()"
```

## Frontend Dev Proxy

In development, Vite proxies `/api/*` requests to `localhost:8001`. In production, the frontend uses the full Render URL. Config in `frontend/vite.config.js`.

## Import Rules

- `requests` module must be imported only at the global level to avoid shadowing
- For service history, always include type `SERVICE` (not just `NOTE` and `APPOINTMENT`) — it contains humidity readings
- Never extract piano model from note text. Use `piano_id`, `instrument_id`, or `Client Token` for SQL joins
