# 🏗️ Diagramme d'Architecture - Assistant Gazelle V5

**Vue d'ensemble visuelle du système**

---

## 🌐 Architecture Globale

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         UTILISATEUR (Navigateur)                         │
│                          http://localhost:5174                           │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 │ HTTP/REST
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      FRONTEND (React + Vite)                             │
│  ┌─────────────┬─────────────┬─────────────┬─────────────┬────────────┐│
│  │  Vincent    │    UQAM     │   Place     │   Orford    │    SMCQ    ││
│  │  d'Indy     │             │  des Arts   │             │            ││
│  └─────────────┴─────────────┴─────────────┴─────────────┴────────────┘│
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 │ GET /{institution}/pianos
                                 │ GET /institutions/list
                                 │ GET /humidity-alerts/institutional
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    API BACKEND (FastAPI) :8000                           │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  /api/main.py - Point d'entrée                                   │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                           │
│  ┌──────────────────────┬──────────────────────┬───────────────────┐   │
│  │  institutions.py     │  humidity_alerts_    │  vincent_dindy.py │   │
│  │  Routes dynamiques   │  routes.py           │  (Legacy)         │   │
│  │  /{slug}/pianos      │  Alertes humidité    │                   │   │
│  └──────────────────────┴──────────────────────┴───────────────────┘   │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  /core/gazelle_api_client.py                                     │   │
│  │  Client GraphQL pour API Gazelle                                 │   │
│  │  • Gestion tokens (x-gazelle-api-key / Bearer)                   │   │
│  │  • Auto-refresh                                                   │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  /core/supabase_storage.py                                       │   │
│  │  Client Supabase PostgreSQL                                      │   │
│  │  • get_system_setting('gazelle_oauth_token')                     │   │
│  │  • CRUD tables                                                    │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└───────────────┬─────────────────────────────┬───────────────────────────┘
                │                             │
                │ GraphQL                     │ SQL
                ▼                             ▼
┌───────────────────────────┐   ┌─────────────────────────────────────────┐
│   API GAZELLE (Externe)   │   │     SUPABASE PostgreSQL (Hébergé)      │
│  gazelleapp.io/graphql    │   │  beblgzvmjqkcillmcavk.supabase.co      │
│                           │   │                                         │
│  • Clients                │   │  ┌────────────────────────────────────┐ │
│  • Pianos                 │   │  │ gazelle_clients                    │ │
│  • Appointments           │   │  │  - external_id (cli_xxx)           │ │
│  • Timeline               │   │  │  - tags (TEXT[])  ← Manuel!        │ │
│                           │   │  └────────────────────────────────────┘ │
│  Auth:                    │   │                                         │
│  x-gazelle-api-key        │   │  ┌────────────────────────────────────┐ │
│  ou Bearer token          │   │  │ gazelle_pianos                     │ │
└───────────────────────────┘   │  │  - id (auto-increment)             │ │
                                │  │  - external_id (ins_xxx)           │ │
                                │  │  - client_external_id              │ │
                                │  │  - dampp_chaser_installed ← Auto! │ │
                                │  └────────────────────────────────────┘ │
                                │                                         │
                                │  ┌────────────────────────────────────┐ │
                                │  │ gazelle_timeline_entries           │ │
                                │  │  - external_id (tme_/tle_)         │ │
                                │  │  - description                     │ │
                                │  │  - service_notes                   │ │
                                │  └────────────────────────────────────┘ │
                                │                                         │
                                │  ┌────────────────────────────────────┐ │
                                │  │ institutions                       │ │
                                │  │  - slug (vincent-dindy, uqam...)   │ │
                                │  │  - gazelle_client_id               │ │
                                │  └────────────────────────────────────┘ │
                                │                                         │
                                │  ┌────────────────────────────────────┐ │
                                │  │ humidity_alerts                    │ │
                                │  │  - client_id ← Filter par ID!      │ │
                                │  │  - alert_type (housse, alim...)    │ │
                                │  └────────────────────────────────────┘ │
                                │                                         │
                                │  ┌────────────────────────────────────┐ │
                                │  │ system_settings                    │ │
                                │  │  - key: 'gazelle_oauth_token'      │ │
                                │  │  - value: {access_token, ...}      │ │
                                │  └────────────────────────────────────┘ │
                                └─────────────────────────────────────────┘
```

---

## 🔄 Flux de Synchronisation

```
┌────────────────────────────────────────────────────────────────────────┐
│                   SYNC GAZELLE → SUPABASE                              │
└────────────────────────────────────────────────────────────────────────┘

1. SYNC INITIALE
   ┌──────────────────┐
   │ scripts/         │
   │ sync_to_        │
   │ supabase.py     │
   └────────┬─────────┘
            │
            │ GraphQL: allClients, allPianos, allAppointments, allTimeline
            ▼
   ┌─────────────────┐       ┌──────────────────────────────────────────┐
   │  API Gazelle    │────▶  │  Supabase Tables                         │
   └─────────────────┘       │  ✓ gazelle_clients (préserve tags)       │
                             │  ✓ gazelle_pianos (préserve PLS flag)    │
                             │  ✓ gazelle_appointments                   │
                             │  ✓ gazelle_timeline_entries (23,869)     │
                             └──────────────────────────────────────────┘

2. DÉTECTION PLS (Après sync)
   ┌──────────────────────────────┐
   │ scripts/                     │
   │ detect_dampp_chaser_        │
   │ installations.py --write     │
   └──────────┬───────────────────┘
              │
              │ Scan keywords: "dampp", "chaser", "PLS", "humidistat"
              ▼
   ┌──────────────────────────────┐
   │ gazelle_timeline_entries     │───▶  UPDATE gazelle_pianos
   │ (service_notes, description) │      SET dampp_chaser_installed = true
   └──────────────────────────────┘      WHERE keywords matched
                                         
                                         Résultat: 340 pianos marqués

3. DÉTECTION ALERTES HUMIDITÉ (Quotidien)
   ┌──────────────────────────────┐
   │ core/                        │
   │ humidity_alert_detector.py   │
   │ (via scheduler)              │
   └──────────┬───────────────────┘
              │
              │ Scan keywords: "housse retirée", "débranché", "réservoir vide"
              ▼
   ┌──────────────────────────────┐
   │ gazelle_timeline_entries     │───▶  INSERT INTO humidity_alerts
   │ (Clients institutionnels)    │      (timeline_entry_id, client_id, 
   └──────────────────────────────┘       piano_id, alert_type, ...)
```

---

## 📊 Flux d'Affichage Frontend

```
┌────────────────────────────────────────────────────────────────────────┐
│              FRONTEND → API → DONNÉES                                  │
└────────────────────────────────────────────────────────────────────────┘

USER clique sur "Vincent d'Indy"
       │
       │ GET /institutions/list
       ▼
┌─────────────────┐       ┌──────────────────────────────────────┐
│  API Backend    │────▶  │  SELECT * FROM institutions          │
└─────────────────┘       │  WHERE active = true                 │
       │                  └──────────────────────────────────────┘
       │
       │ Retour: [{slug: "vincent-dindy", name: "...", 
       │           gazelle_client_id: "cli_9UMLkteep8EsISbG"}, ...]
       ▼
┌─────────────────┐
│  Frontend       │  Affiche liste institutions
└─────────────────┘

USER clique sur "Vincent d'Indy"
       │
       │ GET /vincent-dindy/pianos
       ▼
┌─────────────────┐
│  API Backend    │
│  institutions.  │  1. SELECT gazelle_client_id 
│  py             │     FROM institutions 
└────────┬────────┘     WHERE slug = 'vincent-dindy'
         │              → cli_9UMLkteep8EsISbG
         │
         │ 2. GraphQL: allPianos(clientId: "cli_9UMLkteep8EsISbG")
         ▼
┌─────────────────┐       ┌──────────────────────────────────────┐
│  API Gazelle    │────▶  │  Retour: 121 pianos                  │
└─────────────────┘       │  [{id, make, model, location, ...}]  │
         │                └──────────────────────────────────────┘
         │
         │ 3. JOIN avec Supabase overlays (statuts, notes...)
         ▼
┌─────────────────┐       ┌──────────────────────────────────────┐
│  Supabase       │────▶  │  SELECT * FROM                       │
│                 │       │  vincent_dindy_piano_updates         │
└─────────────────┘       │  WHERE institution_slug =            │
         │                │  'vincent-dindy'                     │
         │                └──────────────────────────────────────┘
         │
         │ 4. Fusion données Gazelle + Supabase
         ▼
┌─────────────────┐
│  Frontend       │  Affiche 121 pianos avec statuts à jour
└─────────────────┘
```

---

## 🔐 Flux d'Authentification

```
┌────────────────────────────────────────────────────────────────────────┐
│                    GESTION TOKEN GAZELLE                               │
└────────────────────────────────────────────────────────────────────────┘

DÉMARRAGE API
       │
       │ Instanciation GazelleAPIClient()
       ▼
┌────────────────────────────────────────────┐
│  _load_token()                             │
│  1. Priorité: Supabase system_settings     │────▶ SELECT value
│  2. Fallback: config/token.json (legacy)   │      FROM system_settings
└────────────────┬───────────────────────────┘      WHERE key = 
                 │                                   'gazelle_oauth_token'
                 ▼
┌────────────────────────────────────────────┐
│  Token récupéré:                           │
│  {                                         │
│    "access_token": "<jeton>",         │
│    "refresh_token": "manual_override",     │
│    "expires_at": 1999999999                │
│  }                                         │
└────────────────┬───────────────────────────┘
                 │
                 │ len(access_token) < 50 chars ?
                 ▼
           ┌─────┴─────┐
           │           │
      OUI  │           │  NON
           ▼           ▼
   ┌─────────────┐   ┌──────────────────┐
   │ API Key     │   │ JWT Token        │
   │ Header:     │   │ Header:          │
   │ x-gazelle-  │   │ Authorization:   │
   │ api-key     │   │ Bearer <token>   │
   └─────────────┘   └──────────────────┘


REQUÊTE API GAZELLE
       │
       │ GraphQL query
       ▼
┌────────────────────────────────────────────┐
│  POST https://gazelleapp.io/graphql/       │
│  Headers:                                  │
│    x-gazelle-api-key: EkS12hs61...         │
│    Content-Type: application/json          │
└────────────────┬───────────────────────────┘
                 │
                 ▼
           ┌─────┴─────┐
           │           │
      200  │           │  401
           ▼           ▼
   ┌─────────────┐   ┌──────────────────────────┐
   │ Succès      │   │ Token invalide           │
   │ Retour      │   │ _refresh_token()         │
   │ données     │   │ → Retry avec nouveau     │
   └─────────────┘   │   token                  │
                     └──────────────────────────┘
```

---

## 📄 Flux de Rapport Google Sheet

```
┌────────────────────────────────────────────────────────────────────────┐
│            GÉNÉRATION RAPPORT TIMELINE → GOOGLE SHEET                  │
└────────────────────────────────────────────────────────────────────────┘

Déclenchement Manuel ou Scheduler
       │
       │ generate_reports()
       ▼
┌────────────────────────────────────────────┐
│  modules/reports/service_reports.py        │
└────────────────┬───────────────────────────┘
                 │
                 │ 1. RÉCUPÉRATION (avec pagination)
                 ▼
┌────────────────────────────────────────────┐       ┌──────────────────┐
│  _fetch_timeline_entries()                 │────▶  │  Supabase        │
│  Batch de 1000 entrées à la fois           │       │  23,869 entrées  │
└────────────────┬───────────────────────────┘       └──────────────────┘
                 │
                 │ 2. DÉDUPLICATION
                 │    Signature: (date, description)
                 │    Priorité: tme_ > tle_
                 │    Résultat: -4,527 doublons
                 ▼
┌────────────────────────────────────────────┐
│  19,342 entrées uniques                    │
└────────────────┬───────────────────────────┘
                 │
                 │ 3. CATÉGORISATION
                 ▼
   ┌─────────────┬──────────────┬──────────────┬─────────────┐
   │ Vincent     │ UQAM         │ Place Arts   │ SMCQ        │
   ├─────────────┼──────────────┼──────────────┼─────────────┤
   │ Services    │ Alertes      │              │             │
   │ Complets    │ Maintenance  │              │             │
   └─────────────┴──────────────┴──────────────┴─────────────┘
                 │
                 │ 4. FORMATTING
                 │    - Piano: "Steinway Model D #123456 (Grand, 1995)"
                 │    - Timezone: UTC → America/Montreal
                 │    - Extraction: Humidité %, Température, Fréquence Hz
                 ▼
┌────────────────────────────────────────────┐
│  Rows prêtes pour insertion                │
│  Format: [Date, NomTechnicien, Description,│
│           Humidite, Temp, Piano]           │
└────────────────┬───────────────────────────┘
                 │
                 │ 5. INSERTION GOOGLE SHEETS
                 ▼
┌────────────────────────────────────────────┐
│  Google Sheets API (gspread)               │
│  • Clear worksheet                         │
│  • Append headers                          │
│  • Append rows (batch)                     │
└────────────────┬───────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────┐
│  "Rapport Timeline de l'assistant v5"      │
│  https://docs.google.com/spreadsheets/...  │
│                                            │
│  Onglets:                                  │
│  • Services Complets                       │
│  • Vincent                                 │
│  • UQAM                                    │
│  • Place des Arts                          │
│  • SMCQ                                    │
│  • Alertes Maintenance                     │
│  • Mesures Orphelines                      │
└────────────────────────────────────────────┘
```

---

## 🚨 Points Critiques (Ne JAMAIS Écraser)

```
┌────────────────────────────────────────────────────────────────────────┐
│                     DONNÉES CRITIQUES À PRÉSERVER                      │
└────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│  gazelle_clients.tags                                                │
│  ─────────────────────                                               │
│  Source: MANUEL (assigné par admin)                                 │
│  Utilisé pour: Filtrage institutions dans API/Frontend              │
│  Valeurs: ['institutional']                                          │
│                                                                       │
│  ⚠️ L'API Gazelle NE retourne PAS les tags                          │
│  ⚠️ Ne JAMAIS écraser si vide lors des syncs                        │
│                                                                       │
│  Protection: Dans sync_to_supabase.py                                │
│    if tags:                                                          │
│        client_record['tags'] = tags  # Mise à jour seulement si non-vide│
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│  gazelle_pianos.dampp_chaser_installed                               │
│  ──────────────────────────────────────                              │
│  Source: AUTOMATIQUE (détecté par scan timeline)                     │
│  Utilisé pour: Badge PLS dans frontend                               │
│  Valeurs: true | false                                               │
│                                                                       │
│  ⚠️ L'API Gazelle NE gère PAS ce flag                               │
│  ⚠️ Doit être régénéré après chaque sync majeure                     │
│                                                                       │
│  Régénération: scripts/detect_dampp_chaser_installations.py --write  │
│  Résultat: 340 pianos marqués                                        │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│  system_settings.gazelle_oauth_token                                 │
│  ────────────────────────────────────────                            │
│  Source: MANUEL (injecté par admin via script)                       │
│  Utilisé pour: Authentification API Gazelle                          │
│  Format: {access_token, refresh_token, expires_at, created_at}      │
│                                                                       │
│  ⚠️ Token court (< 50 chars) = API Key → header x-gazelle-api-key   │
│  ⚠️ Token long = JWT → header Authorization: Bearer                 │
│  ⚠️ Redémarrer API après changement de token                         │
│                                                                       │
│  Injection: (voir docs/ARCHITECTURE_GUIDE.md#authentification)       │
└──────────────────────────────────────────────────────────────────────┘
```

---

**Document créé :** 2026-01-20  
**Version :** 1.0  
**Complément de :** [ARCHITECTURE_GUIDE.md](ARCHITECTURE_GUIDE.md)
