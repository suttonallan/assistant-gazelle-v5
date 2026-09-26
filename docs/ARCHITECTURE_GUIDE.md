# 🗺️ Guide d'Architecture - Assistant Gazelle V5

**Dernière mise à jour :** 2026-01-20  
**Objectif :** Savoir exactement OÙ se trouve QUOI dans le système

---

## 📑 Table des Matières

1. [Authentification & Tokens](#authentification--tokens)
2. [Configuration](#configuration)
3. [Base de Données](#base-de-données)
4. [API Backend](#api-backend)
5. [Frontend](#frontend)
6. [Scripts Utiles](#scripts-utiles)
7. [Logs & Debugging](#logs--debugging)
8. [Flux de Données](#flux-de-données)
9. [Déploiement](#déploiement)

---

## 🔐 Authentification & Tokens

### Token OAuth Gazelle

**Emplacement principal :** Supabase `system_settings` table

```sql
-- Requête pour voir le token
SELECT key, value 
FROM system_settings 
WHERE key = 'gazelle_oauth_token';
```

**Fichier de fallback :** `/config/token.json` (legacy, non utilisé si Supabase disponible)

**Structure du token :**
```json
{
  "access_token": "EkS12hs61KsedjtN7t2TuCcCV9hpc6vo",  // Token court = API Key
  "refresh_token": "manual_override",                 // Pour auto-refresh
  "expires_at": 1999999999,                           // Timestamp Unix
  "created_at": 0                                     // Timestamp création
}
```

**Comment le token est chargé :**
1. `GazelleAPIClient.__init__()` → appelle `_load_token()`
2. `_load_token()` cherche dans Supabase (`gazelle_oauth_token`)
3. Fallback sur `config/token.json` si Supabase échoue
4. Si token court (< 50 chars) → utilise header `x-gazelle-api-key`
5. Si token long → utilise header `Authorization: Bearer`

**Fichier source :** `/core/gazelle_api_client.py` lignes 55-90

### Injecter un nouveau token

```python
from core.supabase_storage import SupabaseStorage
storage = SupabaseStorage()

token_data = {
    "access_token": "NOUVEAU_TOKEN",
    "refresh_token": "manual_override",
    "expires_at": 1999999999,
    "created_at": 0
}

storage.save_system_setting('gazelle_oauth_token', token_data)
```

**IMPORTANT :** Après injection, redémarrer l'API :
```bash
pkill -f "uvicorn.*main:app"
cd /Users/allansutton/Documents/assistant-gazelle-v5
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload &
```

---

## ⚙️ Configuration

### Variables d'Environnement

**Fichier :** `/.env` (racine du projet)

**Variables critiques :**
```bash
# Supabase
SUPABASE_URL=https://beblgzvmjqkcillmcavk.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Gazelle API (OAuth - legacy, non utilisé si token dans Supabase)
GAZELLE_CLIENT_ID=yCLgIwBusPMX9bZHtbzePvcNUisBQ9PeA4R93OwKwNE
GAZELLE_CLIENT_SECRET=CHiMzcYZ2cVgBCjQ7vDCxr3jIE5xkLZ_9v4VkU-O9Qc

# Google Sheets (pour rapports)
GOOGLE_CREDENTIALS_PATH=config/google-credentials.json
```

**Chargement :**
- Backend : `python-dotenv` charge automatiquement au démarrage
- Scripts : Chaque script charge avec `load_dotenv()` dans `core/gazelle_api_client.py`

### Credentials Google Sheets

**Fichier :** `/config/google-credentials.json`

**Format :**
```json
{
  "type": "service_account",
  "project_id": "assistant-gazelle-v5",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...",
  "client_email": "gazelle-service@assistant-gazelle-v5.iam.gserviceaccount.com",
  ...
}
```

**Guide de setup :** `/docs/SETUP_GOOGLE_CREDENTIALS.md`

---

## 🗄️ Base de Données

### Supabase PostgreSQL

**URL :** https://beblgzvmjqkcillmcavk.supabase.co  
**Interface Web :** https://supabase.com/dashboard/project/beblgzvmjqkcillmcavk

### Tables Principales

#### `gazelle_clients` - Clients Gazelle
```sql
Colonnes critiques :
- external_id (TEXT) : ID Gazelle (ex: cli_9UMLkteep8EsISbG)
- company_name (TEXT) : Nom de la compagnie
- first_name, last_name (TEXT) : Pour contacts individuels
- tags (TEXT[]) : Tags manuels (ex: ['institutional'])
- email, phone, city, postal_code
- status (TEXT) : 'active' | 'inactive'
```

**⚠️ IMPORTANT :** Le champ `tags` est assigné **manuellement** et ne vient PAS de l'API Gazelle. Ne jamais l'écraser lors des syncs !

#### `gazelle_pianos` - Pianos
```sql
Colonnes critiques :
- id (INTEGER, auto-increment)
- external_id (TEXT) : ID Gazelle (ex: ins_abc123)
- client_external_id (TEXT) : Lien vers gazelle_clients.external_id
- make, model, serial_number, type, year
- location (TEXT) : Emplacement du piano
- dampp_chaser_installed (BOOLEAN) : Badge PLS
- dampp_chaser_humidistat_model, dampp_chaser_mfg_date
```

**⚠️ IMPORTANT :** Le champ `dampp_chaser_installed` est détecté automatiquement par scan de timeline. Ne pas écraser lors des syncs !

#### `gazelle_timeline_entries` - Timeline
```sql
Colonnes critiques :
- id (INTEGER)
- external_id (TEXT) : 'tme_xxx' (Timeline Manual Entry) ou 'tle_xxx' (Timeline Legacy Entry)
- piano_id (TEXT) : Lien vers piano
- client_id (TEXT) : Lien vers client
- entry_type (TEXT) : 'service' | 'measurement' | 'note'
- occurred_at (TIMESTAMPTZ) : Date de l'événement
- description (TEXT) : Contenu de l'entrée
- service_notes (TEXT) : Notes de service
```

**Déduplication :** Les entrées avec même `(occurred_at, description)` mais `external_id` différents (`tme_` vs `tle_`) sont des doublons.

#### `institutions` - Configuration Institutions
```sql
Colonnes :
- slug (TEXT, PRIMARY KEY) : 'vincent-dindy', 'uqam', 'place-des-arts'
- name (TEXT) : Nom affiché
- gazelle_client_id (TEXT) : Lien vers gazelle_clients.external_id
- active (BOOLEAN) : Institution active ou non
- options (JSONB) : Config spécifique
```

**Usage :** Routes dynamiques `/api/{slug}/pianos` lisent cette table pour obtenir le `gazelle_client_id`.

#### `system_settings` - Paramètres Système
```sql
Colonnes :
- key (TEXT, PRIMARY KEY) : 'gazelle_oauth_token', 'gazelle_access_token'
- value (JSONB) : Données du token
- updated_at (TIMESTAMPTZ)
```

**Tokens disponibles :**
- `gazelle_oauth_token` : Token principal utilisé par `GazelleAPIClient`
- `gazelle_access_token` : Ancien emplacement (legacy)

#### `humidity_alerts` - Alertes Humidité
```sql
Colonnes :
- id (UUID)
- timeline_entry_id (TEXT) : Lien vers timeline
- client_id (TEXT) : ID externe du client
- piano_id (TEXT) : ID du piano (peut être external_id ou serial)
- alert_type (TEXT) : 'housse' | 'alimentation' | 'reservoir' | 'autre'
- description (TEXT)
- is_resolved (BOOLEAN)
- observed_at (TIMESTAMPTZ)
```

**Vue associée :** `humidity_alerts_active` (JOIN avec clients et pianos)

#### `vincent_dindy_piano_updates` - Mises à jour Pianos
```sql
Colonnes :
- piano_id (TEXT) : ID Gazelle du piano
- institution_slug (TEXT) : 'vincent-dindy', 'orford', etc.
- status (TEXT) : 'normal' | 'proposed' | 'work_in_progress' | 'completed'
- a_faire (TEXT) : Travail à faire
- travail (TEXT) : Travail effectué
- observations (TEXT) : Observations du technicien
- is_work_completed (BOOLEAN)
- sync_status (TEXT) : 'pending' | 'synced' | 'error'
- updated_by (TEXT) : Email du technicien
- updated_at (TIMESTAMPTZ)
```

---

## 🔌 API Backend

### Structure

**Racine :** `/api/`  
**Point d'entrée :** `/api/main.py`  
**Port :** 8000 (défaut)

### Routes Principales

#### `/api/main.py` - Application FastAPI
```python
from fastapi import FastAPI
from api import institutions, vincent_dindy, humidity_alerts_routes, ...

app = FastAPI()
app.include_router(institutions.router)
app.include_router(vincent_dindy.router)
app.include_router(humidity_alerts_routes.router)
...
```

#### `/api/institutions.py` - Routes Dynamiques Institutions
**Endpoints :**
```
GET /institutions/list
    → Liste toutes les institutions actives

GET /{institution}/pianos
    → Pianos pour une institution (vincent-dindy, uqam, etc.)
    → Lit la table 'institutions' pour obtenir gazelle_client_id
    → Appelle l'API Gazelle avec ce client_id

PUT /{institution}/pianos/{piano_id}
    → Met à jour un piano (sauvegarde dans vincent_dindy_piano_updates)

GET /{institution}/activity
    → Historique d'activité pour une institution

GET /{institution}/stats
    → Statistiques pour une institution

GET /{institution}/tournees
    → Tournées pour une institution
```

**Comment ajouter une institution :**
```sql
INSERT INTO institutions (slug, name, gazelle_client_id, active)
VALUES ('nouvelle-ecole', 'Nouvelle École de Musique', 'cli_xxxxx', true);
```

#### `/api/humidity_alerts_routes.py` - Alertes Humidité
**Endpoints :**
```
GET /humidity-alerts/institutional
    → Alertes pour clients institutionnels
    → ⚠️ Filtre par client_id (external_id), PAS par client_name

GET /humidity-alerts/all
    → Toutes les alertes

POST /humidity-alerts/{alert_id}/resolve
    → Marquer une alerte comme résolue

GET /humidity-alerts/scheduler/status
    → Statut du scan automatique

POST /humidity-alerts/scheduler/start
    → Démarrer le scan automatique
```

**IDs institutionnels filtrés :**
```python
INSTITUTIONAL_CLIENT_IDS = [
    'cli_9UMLkteep8EsISbG',  # Vincent-d'Indy
    'cli_HbEwl9rN11pSuDEU',  # Place des Arts
    'cli_PmqPUBTbPFeCMGmz',  # Orford
    'cli_sos6RK8t4htOApiM',  # UQAM
    'cli_UVMjT9g1b1wDkRHr',  # SMCQ
]
```

#### `/api/vincent_dindy.py` - Routes Vincent-d'Indy (Legacy)
**Endpoints :**
```
GET /vincent-dindy/pianos
    → Pianos Vincent-d'Indy (legacy, utilise institutions.py maintenant)

POST /vincent-dindy/report
    → Soumettre un rapport de technicien
```

### Démarrer l'API

```bash
cd /Users/allansutton/Documents/assistant-gazelle-v5
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

**Avec logs :**
```bash
nohup python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload \
  > logs/api_$(date +%Y%m%d_%H%M%S).log 2>&1 &
```

**Tester :**
```bash
curl http://localhost:8000/health
curl http://localhost:8000/institutions/list
curl http://localhost:8000/vincent-dindy/pianos
```

---

## 🎨 Frontend

### Structure

**Racine :** `/frontend/`  
**Port :** 5174 (Vite dev server)  
**Framework :** React + Vite

### Fichiers Clés

```
frontend/
├── src/
│   ├── main.jsx                 # Point d'entrée
│   ├── App.jsx                  # Composant principal
│   ├── components/              # Composants réutilisables
│   ├── pages/                   # Pages de l'application
│   └── utils/                   # Utilitaires
├── package.json                 # Dépendances npm
└── vite.config.js              # Configuration Vite
```

### Démarrer le Frontend

```bash
cd /Users/allansutton/Documents/assistant-gazelle-v5/frontend
npm run dev
```

**Résultat :**
```
VITE v5.4.21  ready in 538 ms
➜  Local:   http://localhost:5174/
```

**⚠️ Si port occupé :**
```bash
pkill -f "vite"
npm run dev
```

### Appels API depuis le Frontend

**Pattern typique :**
```javascript
// Récupérer pianos pour une institution
const response = await fetch(`http://localhost:8000/${institution}/pianos`);
const data = await response.json();
// data = { pianos: [...], count: 119, institution: "..." }

// Récupérer liste des institutions
const response = await fetch('http://localhost:8000/institutions/list');
const data = await response.json();
// data = { institutions: [{slug, name, options}, ...], count: 5 }
```

---

## 🛠️ Scripts Utiles

### Synchronisation

#### `/scripts/sync_to_supabase.py` - Sync Gazelle → Supabase
**Usage :**
```bash
python3 scripts/sync_to_supabase.py
```

**Ce qu'il fait :**
- Récupère clients, pianos, appointments, timeline depuis API Gazelle
- Les insère/met à jour dans Supabase
- ⚠️ **ATTENTION :** Peut écraser les tags et dampp_chaser_installed !

**Protections en place :**
```python
# Ne pas inclure 'tags' si vide (préserve les tags existants)
if tags:
    client_record['tags'] = tags
```

#### `/scripts/detect_dampp_chaser_installations.py` - Détection PLS
**Usage :**
```bash
python3 scripts/detect_dampp_chaser_installations.py --write
```

**Ce qu'il fait :**
- Scanne les timeline entries pour mots-clés PLS/Dampp-Chaser
- Marque `gazelle_pianos.dampp_chaser_installed = true`
- Extraie modèle et date de fabrication

**Mots-clés détectés :**
- "dampp", "chaser", "damp chaser", "humidistat", "humidity control system", "P.L.S", "Piano Life Saver"

### Rapports

#### `/modules/reports/service_reports.py` - Rapport Timeline Google Sheet
**Usage :**
```python
from modules.reports.service_reports import generate_reports
generate_reports()
```

**Ce qu'il fait :**
- Récupère toutes les timeline entries (pagination)
- Catégorise par client : Vincent, Place des Arts, Services Complets, Alertes Maintenance
- Déduplique les entrées (`tme_` vs `tle_`)
- Insère dans Google Sheet "Rapport Timeline de l'assistant v5"

**Feuille Google :** [Lien vers la feuille](https://docs.google.com/spreadsheets/)

**Documentation complète :** `/docs/historique/RAPPORT_TIMELINE_V5_RECETTE.md`

### Tokens

#### `/scripts/auto_refresh_token.py` - Rafraîchir Token OAuth
**Usage :**
```bash
python3 scripts/auto_refresh_token.py --force
```

**Ce qu'il fait :**
- Tente de rafraîchir le token avec `refresh_token`
- Si échec, affiche les instructions pour obtenir un nouveau token manuellement

### Debugging

#### `/scripts/test_timeline_query.py` - Test Requêtes Timeline
**Usage :**
```bash
python3 scripts/test_timeline_query.py
```

#### `/scripts/diagnostic_doublons_alertes.py` - Diagnostiquer Doublons
**Usage :**
```bash
python3 scripts/diagnostic_doublons_alertes.py
```

---

## 📋 Logs & Debugging

### Logs API

**Emplacement :** `/logs/api_*.log`

**Dernier log :**
```bash
ls -t logs/api_*.log | head -1 | xargs tail -100
```

**Filtrer erreurs :**
```bash
grep -i "error\|exception\|401\|500" logs/api_*.log | tail -50
```

### Logs Scripts

**Pour scripts avec nohup :**
```bash
nohup python3 script.py > logs/script_$(date +%Y%m%d_%H%M%S).log 2>&1 &
```

**Suivre en temps réel :**
```bash
tail -f logs/script_YYYYMMDD_HHMMSS.log
```

### Debugging Supabase

**Interface Web :** https://supabase.com/dashboard/project/beblgzvmjqkcillmcavk/editor

**SQL Editor :**
```sql
-- Vérifier token
SELECT key, value->>'access_token' as token_preview
FROM system_settings 
WHERE key LIKE '%token%';

-- Vérifier tags institutionnels
SELECT external_id, company_name, tags
FROM gazelle_clients
WHERE tags && ARRAY['institutional'];

-- Vérifier pianos avec PLS
SELECT COUNT(*), make
FROM gazelle_pianos
WHERE dampp_chaser_installed = true
GROUP BY make;

-- Vérifier alertes actives
SELECT client_name, piano_make, alert_type, observed_at
FROM humidity_alerts_active
ORDER BY observed_at DESC
LIMIT 10;
```

### Debugging API Gazelle

**GraphQL Playground :** https://gazelleapp.io/graphql/private/

**Test avec curl :**
```bash
curl -s 'https://gazelleapp.io/graphql/private/' \
  -H 'x-gazelle-api-key: VOTRE_CLE' \
  -H 'Content-Type: application/json' \
  --data-raw '{"query":"query { allClients { nodes { id companyName } } }"}' \
  | python3 -m json.tool
```

---

## 🔄 Flux de Données

### 1. Synchronisation Gazelle → Supabase

```
API Gazelle (GraphQL)
    ↓ scripts/sync_to_supabase.py
Supabase PostgreSQL
    ├─ gazelle_clients
    ├─ gazelle_pianos
    ├─ gazelle_appointments
    └─ gazelle_timeline_entries
```

**Fréquence :** Manuel ou cron (à configurer)

### 2. Détection PLS (Badge Dampp-Chaser)

```
gazelle_timeline_entries
    ↓ scripts/detect_dampp_chaser_installations.py
    │   (scan keywords: "dampp", "chaser", "PLS", etc.)
    ↓
gazelle_pianos.dampp_chaser_installed = true
```

**Fréquence :** Après chaque sync majeure, ou manuellement

### 3. Détection Alertes Humidité

```
gazelle_timeline_entries
    ↓ core/humidity_alert_detector.py
    │   (scan keywords: "housse retirée", "débranché", etc.)
    ↓
humidity_alerts (table)
    ↓
humidity_alerts_active (vue avec JOIN)
```

**Fréquence :** Automatique via scheduler (quotidien) ou manuel

### 4. Affichage Frontend

```
Frontend (React)
    ↓ HTTP GET /institutions/list
API Backend (FastAPI)
    ↓ SELECT * FROM institutions
Supabase
    ↓ Retour JSON
Frontend affiche liste

Frontend clique sur institution
    ↓ HTTP GET /{institution}/pianos
API Backend
    ↓ SELECT gazelle_client_id FROM institutions WHERE slug=...
    ↓ GraphQL query allPianos(clientId: ...)
API Gazelle
    ↓ Retour JSON pianos
Frontend affiche pianos
```

### 5. Rapport Timeline Google Sheet

```
Supabase gazelle_timeline_entries (23,869 entries)
    ↓ modules/reports/service_reports.py
    │   - Pagination (1000 par batch)
    │   - Déduplication (tme_ vs tle_)
    │   - Catégorisation par client
    │   - Détection alertes maintenance
    │   - Extraction mesures (humidité, temp)
    ↓
Google Sheets API
    ↓
Rapport Timeline de l'assistant v5
    ├─ Services Complets
    ├─ Vincent
    ├─ UQAM
    ├─ Place des Arts
    ├─ SMCQ
    └─ Alertes Maintenance
```

**Fréquence :** Manuel via `generate_reports()` ou automatisé via scheduler

---

## 🚀 Déploiement

### Prérequis

1. **Python 3.9+**
2. **Node.js 18+** (pour frontend)
3. **PostgreSQL** (Supabase hébergé)
4. **Credentials Google** (pour rapports)
5. **Token API Gazelle**

### Installation

```bash
# 1. Clone du repo
git clone <repo-url>
cd assistant-gazelle-v5

# 2. Installation Python
pip install -r requirements.txt

# 3. Installation Frontend
cd frontend
npm install
cd ..

# 4. Configuration
cp .env.example .env
# Éditer .env avec vos credentials

# 5. Google Credentials
# Placer google-credentials.json dans /config/
```

### Démarrage Complet

**Terminal 1 - API Backend :**
```bash
cd /Users/allansutton/Documents/assistant-gazelle-v5
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 - Frontend :**
```bash
cd /Users/allansutton/Documents/assistant-gazelle-v5/frontend
npm run dev
```

**Terminal 3 - Sync Périodique (optionnel) :**
```bash
# Sync toutes les heures
while true; do
  python3 scripts/sync_to_supabase.py
  sleep 3600
done
```

### Vérification

```bash
# API
curl http://localhost:8000/health
# → {"status":"healthy"}

# Frontend
open http://localhost:5174

# Base de données
python3 -c "from core.supabase_storage import SupabaseStorage; s=SupabaseStorage(); print('✅ Supabase OK')"
```

---

## 📚 Documents Complémentaires

- **Setup Google :** `/docs/SETUP_GOOGLE_CREDENTIALS.md`
- **Rapport Timeline :** `/docs/historique/RAPPORT_TIMELINE_V5_RECETTE.md`
- **Post-mortem Tags perdus :** `/docs/historique/INCIDENT_2026-01-19_TAGS_PERDUS.md`
- **Alertes Humidité :** `/docs/INTEGRATION_ALERTES_HUMIDITE_COMPLETE.md`

---

## 🆘 Problèmes Courants

### "Token expiré (401)"

**Solution :**
```bash
# Vérifier le token
python3 -c "from core.supabase_storage import SupabaseStorage; s=SupabaseStorage(); print(s.get_system_setting('gazelle_oauth_token'))"

# Injecter un nouveau token (voir section Authentification)
```

### "Page blanche sur le frontend"

**Causes possibles :**
1. Port 5174 déjà utilisé → `pkill -f vite && npm run dev`
2. Erreur JavaScript → F12 Console dans le navigateur
3. API non démarrée → `curl http://localhost:8000/health`

### "Pianos institutionnels invisibles"

**Vérifier :**
1. Tags présents : `SELECT tags FROM gazelle_clients WHERE external_id='cli_9UMLkteep8EsISbG'`
2. Institution configurée : `SELECT * FROM institutions WHERE slug='vincent-dindy'`
3. API retourne pianos : `curl http://localhost:8000/vincent-dindy/pianos`

### "Badge PLS disparu"

**Solution :**
```bash
nohup python3 scripts/detect_dampp_chaser_installations.py --write \
  > logs/detect_pls_$(date +%Y%m%d_%H%M%S).log 2>&1 &
```

---

## ✅ Checklist Maintenance

**Quotidien :**
- [ ] Vérifier logs API : `tail -100 logs/api_*.log | grep ERROR`
- [ ] Vérifier token expire : `python3 scripts/auto_refresh_token.py`

**Hebdomadaire :**
- [ ] Sync Gazelle → Supabase : `python3 scripts/sync_to_supabase.py`
- [ ] Régénérer rapport Timeline : `python3 -c "from modules.reports.service_reports import generate_reports; generate_reports()"`
- [ ] Vérifier alertes humidité : `curl http://localhost:8000/humidity-alerts/institutional`

**Mensuel :**
- [ ] Backup Supabase (automatique via Supabase)
- [ ] Audit tags institutionnels
- [ ] Vérification pianos PLS : `SELECT COUNT(*) FROM gazelle_pianos WHERE dampp_chaser_installed=true`

---

**Créé par :** Assistant Claude + Allan Sutton  
**Version :** 1.0  
**Licence :** Propriétaire
