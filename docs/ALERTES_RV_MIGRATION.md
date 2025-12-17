# Migration Alertes RV - De Windows vers Cloud (Render + Supabase)

**Date:** 2025-12-17
**Objectif:** Migrer complètement le système d'alertes RV depuis le PC Windows vers l'architecture cloud.

---

## 🎯 Vue d'Ensemble

### Ancien Système (Windows)
- **Localisation:** PC Windows (`C:\Allan Python projets`)
- **Déclenchement:** Windows Task Scheduler (daily à 16h)
- **Base de données:** SQL Server (connexion ODBC)
- **Emails:** Gmail API avec credentials locaux
- **Scripts:** `check_unconfirmed_appointments.py`, `gmail_sender.py`

### Nouveau Système (Cloud)
- **Backend:** FastAPI sur Render
- **Base de données:** Supabase (PostgreSQL)
- **Emails:** SendGrid API (ou SMTP Gmail en fallback)
- **Déclenchement:** Cron job Render (daily à 16h UTC)
- **Frontend:** Dashboard React sur GitHub Pages

---

## 📦 Fichiers Créés/Modifiés

### Backend
- `modules/alertes_rv/checker.py` - Logique de vérification des RV non confirmés
- `modules/alertes_rv/email_sender.py` - Envoi d'emails (SendGrid/SMTP)
- `api/alertes_rv.py` - Endpoints REST (complètement refait avec vraies données)

### Frontend (À FAIRE)
- `frontend/src/components/AlertesRVDashboard.jsx` - Dashboard alertes
- Ajouter dans `App.jsx` et routing

---

## 🗄️ Table Supabase

### Créer la table `alerts_history`

Connecte-toi à Supabase et exécute ce SQL:

```sql
-- Table pour historiser les alertes envoyées
CREATE TABLE IF NOT EXISTS alerts_history (
    id BIGSERIAL PRIMARY KEY,
    technician_external_id TEXT NOT NULL,
    technician_name TEXT NOT NULL,
    technician_email TEXT NOT NULL,
    target_date DATE NOT NULL,
    appointment_count INTEGER NOT NULL,
    sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    triggered_by TEXT NOT NULL,  -- Email de qui a déclenché l'alerte
    status TEXT NOT NULL CHECK (status IN ('sent', 'failed')),
    subject TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index pour recherches rapides
CREATE INDEX IF NOT EXISTS idx_alerts_history_sent_at ON alerts_history(sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_history_target_date ON alerts_history(target_date);
CREATE INDEX IF NOT EXISTS idx_alerts_history_technician ON alerts_history(technician_external_id);
CREATE INDEX IF NOT EXISTS idx_alerts_history_triggered_by ON alerts_history(triggered_by);

-- RLS (Row Level Security) - À activer selon tes besoins
ALTER TABLE alerts_history ENABLE ROW LEVEL SECURITY;

-- Policy: Admins peuvent tout voir
CREATE POLICY "Admins can view all alerts"
    ON alerts_history FOR SELECT
    TO authenticated
    USING (true);  -- Ajuste selon ton système d'auth

-- Policy: Service peut insérer
CREATE POLICY "Service can insert alerts"
    ON alerts_history FOR INSERT
    TO anon, authenticated
    WITH CHECK (true);
```

---

## ⚙️ Configuration Environnement

### Variables d'environnement à ajouter sur Render

```bash
# Supabase (déjà configuré normalement)
SUPABASE_URL=https://beblgzvmjqkcillmcavk.supabase.co
SUPABASE_KEY=eyJhbG...

# SendGrid (recommandé pour production)
SENDGRID_API_KEY=SG.xxx...
ALERT_FROM_EMAIL=alerts@piano-tek.com
ALERT_FROM_NAME=Assistant Gazelle Alertes

# OU SMTP Gmail (fallback dev)
SMTP_USER=ton-email@gmail.com
SMTP_PASSWORD=ton-app-password
```

### Obtenir SendGrid API Key (gratuit jusqu'à 100 emails/jour)

1. Aller sur [https://sendgrid.com](https://sendgrid.com)
2. Créer un compte gratuit
3. API Keys → Create API Key
4. Permissions: "Mail Send" (Full Access)
5. Copier la clé et l'ajouter sur Render

---

## 🔄 Endpoints API

### 1. `POST /alertes-rv/check`
Vérifie les RV non confirmés pour une date.

**Request:**
```json
{
    "target_date": "2025-12-18",  // Optionnel, demain par défaut
    "exclude_types": ["PERSONAL", "MEMO"]  // Optionnel
}
```

**Response:**
```json
{
    "target_date": "2025-12-18",
    "checked_at": "2025-12-17T16:00:00",
    "total_technicians": 2,
    "total_appointments": 5,
    "technicians": [
        {
            "id": "usr_ofYggsCDt2JAVeNP",
            "name": "Allan",
            "email": "asutton@piano-tek.com",
            "unconfirmed_count": 3,
            "appointments": [...]
        }
    ]
}
```

### 2. `POST /alertes-rv/send`
Envoie les alertes par email.

**Request:**
```json
{
    "target_date": "2025-12-18",  // Optionnel
    "technician_ids": null,  // null = tous, ou liste d'IDs
    "triggered_by": "asutton@piano-tek.com"
}
```

**Response:**
```json
{
    "success": true,
    "message": "2 alerte(s) en cours d'envoi",
    "sent_count": 2,
    "target_date": "2025-12-18",
    "technicians": [...]
}
```

### 3. `GET /alertes-rv/history?limit=50&offset=0`
Historique des alertes envoyées.

### 4. `GET /alertes-rv/stats`
Statistiques globales.

---

## ⏰ Cron Job sur Render

### Option A: Render Cron Job (Recommandé)

Render supporte les cron jobs natifs. Dans ton dashboard Render:

1. Aller dans ton service backend
2. Settings → Environment
3. Ajouter un nouveau service de type "Cron Job"
4. Commande:
```bash
curl -X POST https://assistant-gazelle-v5-api.onrender.com/alertes-rv/send \
  -H "Content-Type: application/json" \
  -d '{"triggered_by":"system@piano-tek.com"}'
```
5. Schedule: `0 16 * * *` (tous les jours à 16h UTC)

### Option B: Script Python schedulé

Créer un fichier `cron_check_alerts.py` à la racine:

```python
#!/usr/bin/env python3
"""
Script cron pour vérifier et envoyer alertes RV automatiquement.
À exécuter via Render Cron Job ou scheduler externe.
"""
import requests
import os

API_URL = os.getenv('API_URL', 'https://assistant-gazelle-v5-api.onrender.com')

def main():
    # Check
    check_response = requests.post(f"{API_URL}/alertes-rv/check", json={})
    print(f"Check: {check_response.json()}")

    # Send si RV trouvés
    check_data = check_response.json()
    if check_data.get('total_appointments', 0) > 0:
        send_response = requests.post(
            f"{API_URL}/alertes-rv/send",
            json={"triggered_by": "system@piano-tek.com"}
        )
        print(f"Send: {send_response.json()}")
    else:
        print("Aucun RV non confirmé, pas d'alerte envoyée")

if __name__ == '__main__':
    main()
```

Et dans Render, cron job avec: `python3 cron_check_alerts.py`

---

## 🧪 Tests Locaux

### 1. Installer dépendances
```bash
pip install sendgrid  # ou laisser en mode SMTP
```

### 2. Tester le checker
```python
from modules.alertes_rv.checker import AppointmentChecker

checker = AppointmentChecker()
results = checker.get_unconfirmed_appointments()
print(results)
```

### 3. Tester l'API
```bash
# Check
curl -X POST http://localhost:8000/alertes-rv/check \
  -H "Content-Type: application/json" \
  -d '{}'

# Send (mode simulation si pas de SENDGRID_API_KEY)
curl -X POST http://localhost:8000/alertes-rv/send \
  -H "Content-Type: application/json" \
  -d '{"triggered_by":"test@piano-tek.com"}'
```

---

## 📊 Dashboard Frontend (TODO)

### Créer le composant React

**Fichier:** `frontend/src/components/AlertesRVDashboard.jsx`

Fonctionnalités:
- Voir l'historique des alertes envoyées
- Déclencher manuellement une vérification
- Envoyer les alertes manuellement
- Voir les stats (7 jours, 30 jours, par technicien)
- Tableau avec date, technicien, # RV, status

### Ajouter au routing

Dans `App.jsx`, ajouter:
```jsx
import AlertesRVDashboard from './components/AlertesRVDashboard'

// Dans les dashboards disponibles
{dashboard === 'alertes-rv' && <AlertesRVDashboard currentUser={currentUser} />}
```

Et dans `config/roles.js`, ajouter `'alertes-rv'` dans les dashboards admin.

---

## ✅ Checklist de Migration

- [ ] Créer table `alerts_history` dans Supabase
- [ ] Configurer SendGrid API Key sur Render
- [ ] Tester endpoints localement
- [ ] Déployer backend sur Render
- [ ] Configurer cron job sur Render (16h UTC = 11h EST)
- [ ] Créer dashboard frontend
- [ ] Tester le système complet avec vraies données
- [ ] Monitorer les premiers envois
- [ ] Documenter pour l'équipe

---

## 🔒 Sécurité

- Les API keys (SendGrid, Supabase) sont dans les variables d'environnement Render
- Table `alerts_history` avec RLS activé
- Pas de credentials en dur dans le code
- Emails envoyés en arrière-plan (non-bloquant)

---

## 📝 Notes

- **Ancien système:** Ne RIEN effacer sur le PC Windows (backup)
- **Timezone:** Render utilise UTC, ajuster le cron selon ton fuseau horaire
- **Limite SendGrid gratuit:** 100 emails/jour (largement suffisant)
- **Fallback:** Si SendGrid fail, le système bascule en mode SMTP ou simulation

---

## 🚀 Prochaines Étapes

1. Créer la table Supabase
2. Configurer SendGrid
3. Tester localement
4. Déployer sur Render
5. Créer le dashboard frontend
6. Activer le cron job
