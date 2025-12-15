# 🔄 Service de Synchronisation Gazelle → Supabase

## 🎯 Objectif

Synchronise quotidiennement les données de l'API Gazelle vers Supabase pour alimenter :
- L'assistant conversationnel
- Les dashboards
- Les rapports

## 📁 Structure

```
modules/sync_gazelle/
├── __init__.py
├── sync_to_supabase.py    # Script principal de synchronisation
└── README.md              # Ce fichier
```

## 🚀 Installation

### Dépendances

Les dépendances sont déjà installées si le projet fonctionne :
- `requests` (pour API Gazelle)
- `python-dotenv` (pour variables d'environnement)

### Configuration

Le script utilise les variables `.env` existantes :

```bash
# API Gazelle
GAZELLE_CLIENT_ID=xxx
GAZELLE_CLIENT_SECRET=xxx

# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=xxx
```

Le fichier `config/token.json` (OAuth Gazelle) est également requis.

## 📊 Tables Synchronisées

| Table Supabase | Source API Gazelle | Statut |
|----------------|-------------------|--------|
| `gazelle.clients` | `allClients` | ✅ Implémenté |
| `gazelle.pianos` | `allPianos` | ✅ Implémenté |
| `gazelle.contacts` | Contacts dans clients | 🔜 TODO |
| `gazelle.appointments` | Events/Appointments | 🔜 TODO |
| `gazelle.timeline_entries` | Timeline | 🔜 TODO |

## 🧪 Test Manuel

### 1. Test en local

```bash
cd /Users/allansutton/Documents/assistant-gazelle-v5
python3 modules/sync_gazelle/sync_to_supabase.py
```

**Sortie attendue :**
```
======================================================================
🔄 SYNCHRONISATION GAZELLE → SUPABASE
======================================================================
📅 Date: 2025-12-15 10:30:00
======================================================================
🔧 Initialisation du service de synchronisation...
✅ Client API Gazelle initialisé
✅ Client Supabase initialisé

📋 Synchronisation des clients...
📥 150 clients récupérés depuis l'API
✅ 150 clients synchronisés

🎹 Synchronisation des pianos...
📥 85 pianos récupérés depuis l'API
✅ 85 pianos synchronisés

======================================================================
✅ SYNCHRONISATION TERMINÉE
======================================================================
⏱️  Durée: 12.45s

📊 Résumé:
   • Clients:       150 synchronisés,  0 erreurs
   • Pianos:         85 synchronisés,  0 erreurs
   • Contacts:        0 synchronisés (TODO)
   • RV:              0 synchronisés (TODO)
   • Timeline:        0 synchronisés (TODO)
======================================================================
```

### 2. Vérifier les données dans Supabase

Connecte-toi au dashboard Supabase et vérifie :

```sql
-- Compter les clients
SELECT COUNT(*) FROM gazelle.clients;

-- Compter les pianos
SELECT COUNT(*) FROM gazelle.pianos;

-- Exemples de clients
SELECT company_name, email, city FROM gazelle.clients LIMIT 10;
```

## ⏰ Automatisation (CRON)

### Option A : CRON Mac Local (Dev/Test)

Ajouter au crontab (`crontab -e`) :

```bash
# Sync Gazelle tous les jours à 2h du matin
0 2 * * * cd /Users/allansutton/Documents/assistant-gazelle-v5 && /usr/bin/python3 modules/sync_gazelle/sync_to_supabase.py >> logs/sync_gazelle.log 2>&1
```

Créer le dossier logs :
```bash
mkdir -p logs
```

### Option B : Render Cron Job (Production) ⭐ **Recommandé**

Créer un fichier `render.yaml` à la racine :

```yaml
services:
  # API FastAPI (service principal)
  - type: web
    name: gazelle-api-v5
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python3 api/main.py
    envVars:
      - key: SUPABASE_URL
        sync: false
      - key: SUPABASE_KEY
        sync: false
      - key: GAZELLE_CLIENT_ID
        sync: false
      - key: GAZELLE_CLIENT_SECRET
        sync: false

  # Sync job quotidien
  - type: cron
    name: gazelle-sync-daily
    env: python
    schedule: "0 2 * * *"  # 2h du matin tous les jours
    buildCommand: pip install -r requirements.txt
    startCommand: python3 modules/sync_gazelle/sync_to_supabase.py
    envVars:
      - key: SUPABASE_URL
        sync: false
      - key: SUPABASE_KEY
        sync: false
      - key: GAZELLE_CLIENT_ID
        sync: false
      - key: GAZELLE_CLIENT_SECRET
        sync: false
```

## 📈 Monitoring

### Logs

Les logs sont affichés dans stdout. Pour les consulter :

**Mac Local :**
```bash
tail -f logs/sync_gazelle.log
```

**Render :**
Dashboard Render → Logs du cron job

### Alertes en Cas d'Échec

Le script retourne :
- **Exit code 0** : Succès
- **Exit code 1** : Erreur

Render peut envoyer des alertes email si le cron job échoue.

## 🔧 Développement

### Ajouter une Nouvelle Table

1. **Créer une méthode dans `GazelleToSupabaseSync` :**

```python
def sync_appointments(self) -> int:
    """Synchronise les rendez-vous."""
    print("\n📅 Synchronisation des rendez-vous...")

    # 1. Récupérer depuis API
    appointments = self.api_client.get_appointments()

    # 2. Pour chaque appointment
    for appt in appointments:
        # 3. Préparer données
        record = {
            'external_id': appt['id'],
            'client_external_id': appt['clientId'],
            'date': appt['date'],
            'time': appt['time'],
            ...
        }

        # 4. UPSERT vers Supabase
        url = f"{self.storage.api_url}/gazelle.appointments"
        headers = self.storage._get_headers()
        headers["Prefer"] = "resolution=merge-duplicates"

        response = requests.post(url, headers=headers, json=record)

        if response.status_code in [200, 201]:
            self.stats['appointments']['synced'] += 1
```

2. **Appeler dans `sync_all()` :**

```python
def sync_all(self):
    self.sync_clients()
    self.sync_pianos()
    self.sync_appointments()  # ← Ajouter ici
```

### Schéma des Tables

Les tables doivent exister dans Supabase avant le sync. Créer via :

```sql
-- Exemple: gazelle.clients
CREATE TABLE IF NOT EXISTS gazelle.clients (
    id SERIAL PRIMARY KEY,
    external_id TEXT UNIQUE NOT NULL,
    company_name TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    tags TEXT[],
    email TEXT,
    phone TEXT,
    city TEXT,
    postal_code TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_clients_external_id ON gazelle.clients(external_id);
```

## 🐛 Troubleshooting

### Erreur : "GAZELLE_CLIENT_ID non défini"

Vérifier `.env` et `config/.env` :
```bash
grep GAZELLE .env config/.env
```

### Erreur : "Token expiré"

Le token OAuth se rafraîchit automatiquement. Si problème :
```bash
# Vérifier le fichier token
cat config/token.json
```

### Erreur : "SUPABASE_KEY non défini"

Vérifier `.env` :
```bash
grep SUPABASE .env
```

### Erreur : "Table gazelle.clients does not exist"

Créer les tables dans Supabase d'abord (voir section Schéma).

## 📝 TODO

- [ ] Implémenter `sync_contacts()`
- [ ] Implémenter `sync_appointments()`
- [ ] Implémenter `sync_timeline_entries()`
- [ ] Ajouter retry logic en cas d'erreur réseau
- [ ] Ajouter rate limiting pour API Gazelle
- [ ] Logging vers fichier en plus de stdout
- [ ] Slack notifications en cas d'erreur
- [ ] Dashboard de monitoring (nombre de records, durée, erreurs)

---

**Créé :** 2025-12-15
**Version :** 1.0.0
**Statut :** ✅ Fonctionnel (clients + pianos)
