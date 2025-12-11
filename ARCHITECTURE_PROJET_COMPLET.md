# Architecture Complète - Assistant Gazelle V5

Date: 2025-12-09

## Vue d'ensemble

Assistant Gazelle V5 est une application web complète de gestion pour Piano Technique Montréal, comprenant:
- Gestion des pianos (École Vincent-d'Indy)
- Système d'alertes de rendez-vous
- Module d'inventaire (cordes, feutres, outils)

## Structure actuelle du projet

```
/Users/allansutton/Documents/assistant-gazelle-v5/
│
├── 📁 PROJET PRINCIPAL (FastAPI + React) - ✅ EN PRODUCTION
│   ├── api/                              # Backend FastAPI
│   │   ├── main.py                       # Point d'entrée API
│   │   ├── vincent_dindy.py             # Routes Vincent-d'Indy
│   │   ├── alertes_rv.py                # Routes alertes RV
│   │   └── inventaire.py                # Routes inventaire ✅
│   │
│   ├── core/                            # Logique métier partagée
│   │   ├── supabase_storage.py         # Client Supabase centralisé ✅
│   │   ├── db_utils.py                  # Utils DB (legacy)
│   │   ├── github_gist.py              # Sauvegarde Gist
│   │   └── auth.py                      # Authentification
│   │
│   ├── modules/                         # Modules métier
│   │   ├── vincent-dindy/              # Module pianos école
│   │   ├── alertes-rv/                 # Module alertes
│   │   ├── humidity-alerts/            # Module humidité
│   │   └── inventaire/                 # Module inventaire ✅
│   │       ├── README.md
│   │       └── migrations/
│   │           └── 001_create_inventory_tables.sql
│   │
│   ├── scripts/                        # Scripts automation
│   │   ├── inventory_checker_v5.py    # Vérification stock V5 ✅
│   │   ├── inventory_checker.py       # Version legacy
│   │   ├── export_inventory_data.py   # Export données
│   │   ├── backup_db.py               # Backup
│   │   └── check_sync.py              # Vérification sync
│   │
│   ├── frontend/                       # Interface React
│   │   ├── src/
│   │   │   ├── App.jsx
│   │   │   ├── components/
│   │   │   │   ├── VincentDIndyDashboard.jsx  # Dashboard pianos
│   │   │   │   ├── AlertesRV.jsx              # Alertes RV
│   │   │   │   ├── DashboardHome.jsx           # Accueil
│   │   │   │   └── LoginScreen.jsx             # Connexion
│   │   │   └── lib/
│   │   │       └── supabaseClient.js          # Client Supabase frontend
│   │   ├── .env.local                  # Config dev
│   │   ├── .env.production            # Config prod
│   │   └── package.json
│   │
│   ├── data/                           # Données statiques
│   │   └── pianos_vincent_dindy.csv   # Référence pianos
│   │
│   ├── requirements.txt                # Dépendances Python ✅
│   ├── .env                           # Variables environnement
│   └── README.md                      # Doc principale
│
├── 📁 PROTOTYPE FLASK (assistant-gazelle-web) - ⚠️ ARCHIVAGE RECOMMANDÉ
│   ├── app/
│   │   ├── __init__.py
│   │   └── inventory_routes.py        # Routes Flask inventaire (obsolète)
│   ├── scripts/
│   │   ├── inventory_checker.py       # Doublon (copié vers scripts/)
│   │   └── export_inventory_data.py   # Doublon (copié vers scripts/)
│   ├── data/
│   │   └── gazelle_web.db            # SQLite local (obsolète)
│   ├── docs/
│   │   ├── GAZELLE_API_REFERENCE.md
│   │   └── IMPORT_STRATEGY.md
│   ├── run_web.py                     # Serveur Flask (obsolète)
│   └── requirements.txt               # Dépendances Flask
│
├── 📁 EXPORTS (GazelleV5_Inventaire_Export) - ⚠️ ARCHIVAGE RECOMMANDÉ
│   ├── inventory_checker.py          # Script Gazelle legacy
│   ├── export_inventory_data.py      # Script export legacy
│   ├── INSTRUCTIONS_IMPORT.md
│   └── requirements.txt
│
└── 📁 DIVERS
    ├── appointment_alerts_v5/        # Code alertes RV
    ├── push-to-gazelle/             # Scripts sync Gazelle
    ├── gazelle_api_client.py        # Client API Gazelle
    └── sync_gazelle_to_sqlite.py    # Sync local
```

## État actuel des composants

### ✅ PRODUCTION (assistant-gazelle-v5/)

| Composant | État | URL/Commande | Notes |
|-----------|------|--------------|-------|
| Backend FastAPI | ✅ Actif | https://assistant-gazelle-v5-api.onrender.com | Render.com |
| Frontend React | ✅ Actif | https://allansutton.github.io/assistant-gazelle-v5/ | GitHub Pages |
| Base Supabase | ✅ Actif | https://beblgzvmjqkcillmcavk.supabase.co | PostgreSQL cloud |
| Module Vincent-d'Indy | ✅ Déployé | `/vincent-dindy/pianos` | 91 pianos gérés |
| Module Alertes RV | ✅ Déployé | `/alertes-rv/...` | Alertes rendez-vous |
| Module Inventaire | ✅ Prêt | `/inventaire/...` | 9 endpoints + vérification auto |

### ⚠️ PROTOTYPES À ARCHIVER

| Composant | Raison | Action recommandée |
|-----------|--------|-------------------|
| `assistant-gazelle-web/` | Prototype Flask obsolète, remplacé par FastAPI | **ARCHIVER** dans `_archives/` |
| `GazelleV5_Inventaire_Export/` | Scripts copiés dans `scripts/`, code legacy | **ARCHIVER** dans `_archives/` |
| `gazelle_web.db` | SQLite local, remplacé par Supabase | **SUPPRIMER** après backup |

### 📋 DONNÉES STATIQUES

| Fichier | Usage | Source | Fréquence MAJ |
|---------|-------|--------|---------------|
| `pianos_vincent_dindy.csv` | Référence 91 pianos | Export Gazelle | Annuel |
| `data/gazelle_web.db` (obsolète) | Cache local | Sync Gazelle | N/A - remplacé |

## Flux de données

```
┌─────────────────────────────────────────────────────────────┐
│                    SOURCES DE DONNÉES                        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
        ┌──────────────────────────────────────┐
        │   Gazelle API (SQL Server Cloud)     │
        │   - Clients / Contacts                │
        │   - Pianos / Instruments              │
        │   - Rendez-vous                       │
        │   - Inventaire (legacy schema)        │
        └──────────────────────────────────────┘
                            │
                            │ Sync 1x/jour (scripts/)
                            ▼
        ┌──────────────────────────────────────┐
        │        Supabase (PostgreSQL)         │
        │  ┌──────────────────────────────────┐│
        │  │ vincent_dindy_piano_updates      ││
        │  │ - Modifications manuelles pianos ││
        │  ├──────────────────────────────────┤│
        │  │ produits_catalogue               ││
        │  │ inventaire_techniciens           ││
        │  │ transactions_inventaire          ││
        │  │ - Nouveau schéma V5              ││
        │  └──────────────────────────────────┘│
        └──────────────────────────────────────┘
                            │
                ┌───────────┴───────────┐
                │                       │
                ▼                       ▼
    ┌────────────────────┐   ┌────────────────────┐
    │  Backend FastAPI   │   │  Frontend React    │
    │  Render.com        │   │  GitHub Pages      │
    │                    │   │                    │
    │  /vincent-dindy    │◄──┤  VincentDIndy      │
    │  /alertes-rv       │◄──┤  AlertesRV         │
    │  /inventaire       │◄──┤  (À créer)         │
    └────────────────────┘   └────────────────────┘
                │
                │ Cron Jobs (Render)
                ▼
    ┌────────────────────────┐
    │  Tâches automatiques   │
    │  - check_stock         │
    │  - alert_appointments  │
    └────────────────────────┘
```

## Recommandations d'organisation

### 1. Archiver les prototypes (MAINTENANT)

```bash
cd /Users/allansutton/Documents/assistant-gazelle-v5

# Créer dossier archives
mkdir -p _archives/2025-12-09

# Archiver assistant-gazelle-web
mv assistant-gazelle-web/ _archives/2025-12-09/

# Archiver GazelleV5_Inventaire_Export
mv GazelleV5_Inventaire_Export/ _archives/2025-12-09/

# Créer README d'archivage
cat > _archives/2025-12-09/README.md << 'EOF'
# Archives - 2025-12-09

## Contenu

- **assistant-gazelle-web/**: Prototype Flask créé par Cursor PC
  - Remplacé par: FastAPI dans `api/`
  - Code utile extrait: Scripts inventaire copiés dans `scripts/`

- **GazelleV5_Inventaire_Export/**: Scripts d'export Gazelle legacy
  - Remplacé par: `scripts/inventory_checker_v5.py`
  - Schéma BDD différent: legacy vs V5

## Raison de l'archivage

Ces prototypes ont été intégrés dans le projet principal FastAPI + React.
Les scripts utiles ont été adaptés et copiés dans `scripts/`.

## Conservation

Ces archives sont conservées pour référence historique.
Ne pas utiliser ce code directement - utiliser le projet principal.
EOF
```

### 2. Nettoyer les doublons (APRÈS ARCHIVAGE)

```bash
# Supprimer les fichiers temporaires
rm -f *.log
rm -f backend.log
rm -f gazelle_api_audit.log

# Supprimer les bases SQLite locales (APRÈS BACKUP!)
# rm -f data/gazelle_web.db  # ⚠️ Vérifier d'abord qu'il n'y a pas de données importantes
```

### 3. Organiser la documentation

```bash
# Créer dossier docs/ centralisé
mkdir -p docs/

# Déplacer les docs
mv INTEGRATION_INVENTAIRE_COMPLETE.md docs/
mv ARCHITECTURE_PROJET_COMPLET.md docs/
mv GAZELLE_DATA_DICTIONARY.md docs/
mv GUIDE_PUSH_GAZELLE_V5.md docs/
mv CONFIGURER_SUPABASE_RENDER.md docs/
mv DEV_LOCAL_GUIDE.md docs/
mv INSTALL_MAC.sh docs/

# Garder à la racine seulement
# - README.md (principal)
# - requirements.txt
# - .env / .env.example
# - .gitignore
```

## Prochaines étapes de développement

### Court terme (1-2 semaines)

1. ✅ **Module inventaire backend** - TERMINÉ
2. ⏳ **Tests de l'endpoint check-stock**
   - Créer données de test dans Supabase
   - Tester appel API local
   - Configurer Cron Job Render
3. ⏳ **Frontend inventaire React**
   - Page catalogue produits
   - Page stock par technicien
   - Page alertes stock bas

### Moyen terme (1 mois)

4. ⏳ **Notifications automatiques**
   - Email via Gmail API
   - Slack/Discord webhooks
5. ⏳ **Dashboard analytics**
   - Graphiques consommation
   - Prévisions de commande
6. ⏳ **Mobile responsive**
   - Adapter UI mobile
   - PWA (Progressive Web App)

### Long terme (3+ mois)

7. ⏳ **Synchronisation bidirectionnelle Gazelle**
   - Push modifications vers Gazelle
   - Conflict resolution
8. ⏳ **Module facturation**
   - Génération factures PDF
   - Suivi paiements
9. ⏳ **Application mobile native**
   - React Native
   - Scan code-barres

## Commandes utiles

### Développement local

```bash
# Backend
cd /Users/allansutton/Documents/assistant-gazelle-v5
source .env
python3 -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Frontend
cd frontend
npm run dev

# Tests inventaire
python3 scripts/inventory_checker_v5.py
curl -X POST http://localhost:8000/inventaire/check-stock | jq
```

### Déploiement

```bash
# Frontend (GitHub Pages)
cd frontend
npm run build
npm run deploy

# Backend (Render)
# Auto-déployé via git push
git add .
git commit -m "Update: ..."
git push origin main
```

### Maintenance

```bash
# Backup Supabase
# Via Dashboard Supabase > Settings > Database > Backups

# Backup CSV
python3 scripts/backup_db.py

# Vérification sync
python3 scripts/check_sync.py
```

## Support et contacts

- **Développeur**: Allan Sutton (allan@pianoteknik.com)
- **Hébergement Backend**: Render.com
- **Hébergement Frontend**: GitHub Pages
- **Base de données**: Supabase (PostgreSQL)
- **Repo Git**: https://github.com/allansutton/assistant-gazelle-v5

## Changelog

### 2025-12-09
- ✅ Module inventaire backend complet (9 endpoints)
- ✅ Script vérification automatique stocks
- ✅ Endpoint `/inventaire/check-stock` pour Cron Jobs
- ✅ Documentation complète
- ✅ Architecture projet documentée
- ⚠️ Identification prototypes à archiver

### 2025-12-04
- ✅ Feature "Top" status pour pianos (statut brun/amber)
- ✅ CSV + Supabase fusion architecture restaurée
- ✅ Déploiement Render configuration fixée
- ✅ Frontend .env.production créé

### 2025-11-30
- ✅ Migration Supabase tables initiale
- ✅ Module Vincent-d'Indy déployé
- ✅ Module Alertes RV déployé

---

**Version actuelle**: 1.0.0
**Dernière mise à jour**: 2025-12-09
