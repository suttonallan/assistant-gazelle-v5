# Guide développeur — Assistant Gazelle v5

> Ce document est destiné à un développeur professionnel qui arrive sur le projet. Il explique comment le système fonctionne, pourquoi il est construit comme ça, et comment ne rien casser.

## Ce que ce système fait (et pour qui)

Piano Technique Montréal (PTM) est une entreprise de 4 techniciens + 1 assistante qui accordent et entretiennent des pianos pour ~4000 clients (privés + institutions comme la Place des Arts, l'École Vincent-d'Indy, Orford Musique).

Ce système (assistant-gazelle-v5) est le centre nerveux :
- **Ma Journée** : chaque technicien voit ses RV du jour avec un briefing IA (profil client, historique, soumissions, drapeaux)
- **Sync Gazelle** : synchronise clients, pianos, RV, timeline depuis l'API GraphQL de Gazelle (le CRM de l'industrie piano) vers Supabase
- **Alertes** : alerte les techs quand un RV n'est pas confirmé (J-1), quand un RV change de tech/horaire
- **Rapports** : génère un rapport Google Sheets institutionnel (PDA, VDI, UQAM)
- **Dashboards** : inventaire, gestion PDA, Vincent-d'Indy, Orford

Ça tourne en production depuis 2025. Le backend est sur Render, le frontend sur GitHub Pages, la base sur Supabase PostgreSQL.

## Flux de données principaux

```
Gazelle (CRM)
    │
    ├─ Nightly sync (2h UTC) ─────→ Supabase
    │   sync clients, contacts,       (PostgreSQL)
    │   pianos, appointments,              │
    │   timeline entries                   │
    │                                      ├─→ Ma Journée (briefings IA)
    ├─ Hourly sync (7h-21h) ──→ Supabase  │     └─ Claude Haiku par RV
    │   appointments only          │       │
    │                              │       ├─→ Alertes RV non confirmé (16h)
    │                              │       │     └─ Email via Resend
    │                              │       │
    │                              │       ├─→ Alertes Late Assignment
    │                              │       │     └─ Détecte changement tech/horaire
    │                              │       │
    │                              │       ├─→ Rapport Google Sheets
    │                              │       │     └─ PDA / VDI / UQAM / Alertes
    │                              │       │
    └─ API live (soumissions) ────┘       └─→ Dashboard frontend (React)
```

## Le sync — c'est le cœur

**Nightly** (`.github/workflows/full_gazelle_sync.yml`) :
1. `sync_users()` → table `users`
2. `sync_clients()` → table `gazelle_clients`
3. `sync_contacts()` → table `gazelle_contacts`
4. `sync_pianos()` → table `gazelle_pianos`
5. `sync_appointments()` → table `gazelle_appointments`
6. `sync_timeline_entries()` → table `gazelle_timeline_entries`
7. Génération rapport Google Sheets
8. Pré-chauffe du cache briefings

**Hourly** (`.github/workflows/hourly_appointments_sync.yml`) :
- `sync_appointments()` seulement
- Détecte les changements de tech/horaire → file d'alerte

### Pièges connus du sync
- Supabase REST retourne max 1000 rows par défaut. Toute requête sans pagination est silencieusement tronquée.
- Les upserts utilisent `on_conflict=external_id`. Un 409 peut être un conflit normal OU une FK violation — vérifier `23503` dans le body.
- Le mode incrémental des clients sort par `CREATED_AT_DESC` → ne rattrape que les clients créés depuis la dernière sync, pas ceux modifiés.
- Le record `appointment_record` ne doit contenir QUE des colonnes qui existent dans la table. Sinon Supabase retourne 400 pour TOUT le batch.

## Règles métier non évidentes

| Règle | Pourquoi |
|-------|----------|
| "stat 20" dans les notes PDA = stationnement 20$ | Abréviation terrain d'Allan |
| CL = SCL = Salle Claude-Léveillée | Code PDA |
| Ne jamais dire "dépose" → dire "retrait" | Jargon incompréhensible pour le client |
| PLS = Piano Life Saver (Dampp-Chaser) | Ne jamais écrire "Dampp-Chaser" dans les soumissions |
| Pas de signature "— Piano Tek Musique" | Allan ne veut pas |
| Accord de suivi 3 sem post-PLS = facturé séparément | Ne pas inclure dans les bundles d'installation |
| Les soumissions refaites gardent le technicien original | Assignation doit rester au tech qui a fait l'inspection |
| Ne jamais inventer la logistique | Ne pas deviner la séquence des visites/déplacements |
| Institutions (PDA, VDI) : pas de suggestions de réparation dans les briefings | Le RV est un accord standard, point |

## Checklist de non-régression

Après un changement au sync ou aux briefings, vérifier :

- [ ] **Ma Journée** : se connecter comme JP (`pin 6345`), voir ses RV de demain avec briefings complets
- [ ] **Rapport Google Sheets** : onglet "Place des Arts" a des données récentes (pas juste 2019)
- [ ] **Alertes non confirmé** : à 16h, les RV de demain non confirmés génèrent un email
- [ ] **Sync clients** : `curl Supabase/gazelle_clients?select=count` retourne 3900+ (pas 1000)
- [ ] **PDA parking** : un RV PDA complété avec "stat 20" dans les notes → colonne parking = 20.00
- [ ] **Briefing soumissions** : les soumissions réalisées (détectées par keyword matching) ne sont PAS présentées comme "en attente"

## Comment lancer en local

```bash
# Backend
cd assistant-gazelle-v5
cp .env.example .env  # remplir les clés Supabase + Gazelle
pip install -r requirements.txt
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend
cd frontend
npm install
npm run dev  # port 5174, proxy vers localhost:8000
```

## Fichiers importants

| Fichier | Rôle |
|---------|------|
| `CLAUDE.md` | Contexte projet pour Claude Code |
| `decisions.md` | Décisions techniques avec le pourquoi |
| `tech-debt-observations.md` | Liste honnête des fragilités connues |
| `config/techniciens_config.py` | Source de vérité des IDs techniciens |
| `core/supabase_storage.py` | Wrapper REST Supabase (singleton) |
| `core/gazelle_api_client.py` | Client GraphQL Gazelle (OAuth2) |
| `core/gazelle_api_client_incremental.py` | Mode incrémental rapide |
| `modules/sync_gazelle/sync_to_supabase.py` | Le sync principal |
| `modules/briefing/client_intelligence_service.py` | Génération des briefings IA |
| `modules/alertes_rv/checker.py` | Détection RV non confirmés |
| `modules/place_des_arts/` | Tout le workflow PDA |
| `modules/reports/service_reports.py` | Rapport Google Sheets |

## Ce qui a été construit par Allan + Claude Code

Ce projet n'a pas été écrit par un développeur professionnel. Il a été construit par Allan (propriétaire de PTM, technicien de piano) avec l'aide de Claude Code, en résolvant des problèmes réels un par un. Le code reflète ça :

- Pas de tests automatisés
- Typage minimal
- `print()` au lieu de `logging`
- Singleton qui n'en est pas vraiment un
- Des raccourcis pragmatiques qui marchent

Mais aussi :
- Un système qui tourne en production depuis plus d'un an
- 4 techniciens qui l'utilisent au quotidien
- Des briefings IA qui épatent les clients
- Un sync fiable qui traite 24 000+ timeline entries
- Des alertes qui ont prévenu des RV oubliés

Le respect qu'on demande, c'est de ne pas tout réécrire "parce que c'est pas propre". C'est d'améliorer ce qui existe en comprenant pourquoi c'est là.
