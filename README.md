# Assistant Gazelle V5
**Piano Technique Montréal - Système complet de gestion**

---

## 📚 **DOCUMENTATION PRINCIPALE**

**Nouveau dans le projet ?** Commencez ici :

### 🗺️ [**Guide d'Architecture Complet**](docs/ARCHITECTURE_GUIDE.md)
**Où se trouve QUOI dans le système** - Tokens, configuration, base de données, API, frontend, scripts, logs, flux de données

### ⚡ [**Quick Reference**](docs/QUICK_REFERENCE.md)
**Aide-mémoire pour opérations quotidiennes** - Démarrage, tests, requêtes SQL, scripts, debugging, fixes rapides

### 📖 Autres Guides
- [**Rapport Timeline**](docs/historique/RAPPORT_TIMELINE_V5_RECETTE.md) - Génération du rapport Google Sheet
- [**Post-mortem Tags perdus**](docs/historique/INCIDENT_2026-01-19_TAGS_PERDUS.md) - Incident tags institutionnels
- [**Setup Google Sheets**](docs/SETUP_GOOGLE_CREDENTIALS.md) - Configuration credentials Google
- [**Alertes Humidité**](docs/INTEGRATION_ALERTES_HUMIDITE_COMPLETE.md) - Système de détection automatique

---

## 🚀 Démarrage Rapide

### Prérequis
- Python 3.9+
- Node.js 18+
- Accès Supabase (https://beblgzvmjqkcillmcavk.supabase.co)
- Token API Gazelle

### Installation
```bash
# 1. Dépendances Python
pip install -r requirements.txt

# 2. Dépendances Frontend
cd frontend && npm install && cd ..

# 3. Configuration
cp .env.example .env
# Éditer .env avec vos credentials
```

### Lancer l'application

**Terminal 1 - API Backend (port 8000):**
```bash
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 - Frontend (port 5174):**
```bash
cd frontend && npm run dev
```

**Accès :**
- Frontend : http://localhost:5174
- API : http://localhost:8000
- API Docs : http://localhost:8000/docs

---

## 🏗️ Architecture

```
assistant-gazelle-v5/
├── api/                      # Backend FastAPI
│   ├── main.py              # Point d'entrée
│   ├── institutions.py      # Routes dynamiques institutions
│   ├── humidity_alerts_routes.py  # Alertes humidité
│   └── vincent_dindy.py     # Routes Vincent-d'Indy (legacy)
├── core/                    # Modules Python centraux
│   ├── gazelle_api_client.py      # Client API Gazelle
│   ├── supabase_storage.py        # Accès Supabase
│   └── humidity_alert_detector.py # Détection alertes
├── frontend/                # React + Vite
│   ├── src/
│   └── package.json
├── scripts/                 # Scripts utilitaires
│   ├── sync_to_supabase.py        # Sync Gazelle → Supabase
│   └── detect_dampp_chaser_installations.py  # Détection PLS
├── modules/                 # Modules métier
│   └── reports/
│       └── service_reports.py     # Rapport Timeline Google Sheet
├── sql/                     # Migrations SQL
├── docs/                    # Documentation
│   ├── ARCHITECTURE_GUIDE.md     # 📖 Guide complet
│   └── QUICK_REFERENCE.md        # ⚡ Aide-mémoire
└── docs/historique/          # Leçons apprises, incidents, recettes
```

---

## 🎯 Fonctionnalités Principales

### 1. **Gestion Multi-Institutions (3 institutions)**
- Vincent-d'Indy (121 pianos)
- Place des Arts (16 pianos)
- Orford (61 pianos)

### 2. **Synchronisation Gazelle**
- Import automatique clients, pianos, rendez-vous, timeline
- Préservation données manuelles (tags, PLS)
- Détection doublons

### 3. **Détection Automatique**
- **Badge PLS** (Piano Life Saver / Dampp-Chaser)
- **Alertes humidité** (housse retirée, débranché, réservoir vide, etc.)

### 4. **Rapports Google Sheets**
- Timeline complète avec catégorisation
- Déduplication automatique
- Export mesures (humidité, température)

### 5. **API RESTful**
- Endpoints dynamiques par institution
- GraphQL Gazelle
- Gestion statuts pianos

---

## 🔧 Maintenance

### Quotidien
```bash
# Vérifier token
python3 scripts/auto_refresh_token.py

# Vérifier logs
tail -100 logs/api_*.log | grep ERROR
```

### Hebdomadaire
```bash
# Sync Gazelle → Supabase
python3 scripts/sync_to_supabase.py

# Détecter PLS
python3 scripts/detect_dampp_chaser_installations.py --write

# Générer rapport
python3 -c "from modules.reports.service_reports import generate_reports; generate_reports()"
```

---

## 📊 Base de Données (Supabase)

### Tables Principales
- `gazelle_clients` - Clients (avec tags manuels)
- `gazelle_pianos` - Pianos (avec badge PLS)
- `gazelle_timeline_entries` - Historique services
- `institutions` - Configuration institutions
- `humidity_alerts` - Alertes détectées
- `system_settings` - Tokens et config

**Interface :** https://supabase.com/dashboard/project/beblgzvmjqkcillmcavk

---

## ⚠️ Important

### Ne JAMAIS Écraser
1. **`gazelle_clients.tags`** - Assignés manuellement (ex: 'institutional')
2. **`gazelle_pianos.dampp_chaser_installed`** - Détecté par scan automatique
3. **`system_settings.gazelle_oauth_token`** - Token API Gazelle

### Protections en Place
- Sync préserve tags si API ne les retourne pas
- Détection PLS s'exécute après chaque sync majeure
- Backup automatique Supabase

---

## 🐛 Problèmes Courants

Voir [**Quick Reference**](docs/QUICK_REFERENCE.md) section "Fixes Rapides"

**Token expiré :** [Guide Tokens](docs/ARCHITECTURE_GUIDE.md#authentification--tokens)  
**Badge PLS disparu :** `python3 scripts/detect_dampp_chaser_installations.py --write`  
**Tags perdus :** [Post-mortem incident](docs/historique/INCIDENT_2026-01-19_TAGS_PERDUS.md)

---

## 📞 Support

**Documentation complète :** [docs/ARCHITECTURE_GUIDE.md](docs/ARCHITECTURE_GUIDE.md)  
**Aide-mémoire :** [docs/QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md)

---

## 📜 Historique / Legacy

### Description Originale
Script automatisé qui vérifie chaque jour à 16h les rendez-vous non confirmés pour le lendemain et envoie un email individuel à chaque technicien avec uniquement ses propres rendez-vous.

## Fichiers inclus
1. **check_unconfirmed_appointments.py** - Script principal
2. **gmail_sender.py** - Module d'envoi d'emails via Gmail API
3. **README.md** - Ce fichier

## Dépendances Python
```bash
pip install pyodbc
pip install google-auth google-auth-oauthlib google-auth-httplib2
pip install google-api-python-client
pip install pytz
```

## Configuration requise

### 1. Base de données SQL Server
- Serveur: `PIANOTEK\SQLEXPRESS` (à adapter pour Mac)
- Database: `PianoTek`
- Driver ODBC: `ODBC Driver 17 for SQL Server`

**Pour Mac**, installer le driver SQL Server:
```bash
# Homebrew
brew tap microsoft/mssql-release https://github.com/Microsoft/homebrew-mssql-release
brew update
brew install msodbcsql17

# Puis installer unixodbc
brew install unixodbc
```

### 2. Gmail API Credentials
Il faut copier ces fichiers depuis Windows vers Mac:
- `credentials.json` - Credentials OAuth2 Gmail API
- `token.json` - Token d'authentification généré

Placer ces fichiers dans: `./data/credentials.json` et `./data/token.json`

### 3. Mapping des techniciens
Configurer dans le script (lignes 37-51):
```python
TECHNICIANS = {
    'usr_ofYggsCDt2JAVeNP': {
        'name': 'Allan',
        'email': 'asutton@piano-tek.com'
    },
    'usr_HcCiFk7o0vZ9xAI0': {
        'name': 'Nicolas',
        'email': 'nlessard@piano-tek.com'
    },
    'usr_ReUSmIJmBF86ilY1': {
        'name': 'Jean-Philippe',
        'email': 'jpreny@gmail.com'
    }
}
```

## Modifications nécessaires pour Mac

### 1. Chemin vers gmail_sender
Ligne 24 du script `check_unconfirmed_appointments.py`:
```python
# Windows (actuel)
sys.path.insert(0, r"c:\Allan Python projets\assistant-gazelle\scripts")

# Mac (à modifier)
sys.path.insert(0, "/chemin/vers/assistant-gazelle-v5/scripts")
```

### 2. Chemins vers credentials/token
Lignes 34-35:
```python
# Windows (actuel)
CREDENTIALS_FILE = r"c:\Allan Python projets\assistant-gazelle\data\credentials.json"
TOKEN_FILE = r"c:\Allan Python projets\assistant-gazelle\data\token.json"

# Mac (à modifier)
CREDENTIALS_FILE = "/chemin/vers/assistant-gazelle-v5/data/credentials.json"
TOKEN_FILE = "/chemin/vers/assistant-gazelle-v5/data/token.json"
```

### 3. Connexion SQL Server
Lignes 28-30 - Adapter le serveur pour accès distant depuis Mac:
```python
# Windows local (actuel)
DB_SERVER = "PIANOTEK\\SQLEXPRESS"

# Mac - accès distant (à configurer)
DB_SERVER = "192.168.x.x\\SQLEXPRESS"  # IP du serveur Windows
# OU utiliser SQL Server sur Mac si disponible
```

## Automatisation sur Mac

### Avec cron
Éditer crontab:
```bash
crontab -e
```

Ajouter cette ligne pour exécution quotidienne à 16h:
```
0 16 * * * /usr/bin/python3 /chemin/vers/check_unconfirmed_appointments.py
```

### Avec launchd (recommandé sur Mac)
Créer un fichier `.plist` dans `~/Library/LaunchAgents/`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.pianoteknik.unconfirmed.alerts</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/chemin/vers/check_unconfirmed_appointments.py</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>16</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/tmp/unconfirmed_alerts.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/unconfirmed_alerts.error.log</string>
</dict>
</plist>
```

Charger le service:
```bash
launchctl load ~/Library/LaunchAgents/com.pianoteknik.unconfirmed.alerts.plist
```

## Fonctionnement

### Ce que le script fait:
1. Se connecte à la base de données PianoTek
2. Récupère les rendez-vous pour demain qui sont:
   - Type `APPOINTMENT` (pas PERSONAL)
   - Non confirmés (`ConfirmedByClient = 0 or NULL`)
   - Actifs (`AppointmentStatus = 'ACTIVE'`)
   - Assignés à un technicien
   - **Excluant** les MEMO (Description contenant "MEMO")
3. Groupe les rendez-vous par technicien
4. Envoie un email individuel à chaque technicien avec:
   - Sujet: "⚠️ X rendez-vous nécessitent peut-être une confirmation pour demain"
   - Tableau HTML avec heure, client, description, piano, durée
   - Version texte alternative

### Format de l'email:
- **Heure:** Convertie en timezone de Montréal (America/Toronto)
- **Client:** Nom de la compagnie
- **Description:** Description du rendez-vous
- **Piano:** Location, Make, Model
- **Durée:** En minutes

### Logs:
Les logs sont sauvegardés dans: `unconfirmed_appointments_log.txt`

## Test manuel
```bash
cd /chemin/vers/dossier
python3 check_unconfirmed_appointments.py
```

Vérifier le fichier log pour les résultats.

## Support
Pour toute question, contacter Allan Sutton (asutton@piano-tek.com)

---
**Version:** 2025-12-03
**Plateforme source:** Windows (PIANOTEK)
**Migration cible:** Mac (V5)
