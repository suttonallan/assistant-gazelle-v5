# 🚀 Orchestration & Notifications - Assistant Gazelle V5

## ✅ Implémentation Complète

Système d'orchestration des tâches et de notifications intelligent mis en place avec succès.

---

## 📋 Vue d'Ensemble

### 1. **Chaînage Automatique (Orchestration)** ✅

Le système orchestre maintenant les tâches de manière intelligente :

```
01:00 → Sync Gazelle Totale
  ↓ (si succès)
  └→ Génération Rapport Timeline (automatique)
```

**Avant :**
- 01:00 - Sync Gazelle
- 02:00 - Rapport Timeline (séparé, même si sync échouait)

**Maintenant :**
- 01:00 - Sync Gazelle → déclenche automatiquement Timeline si succès
- ⚠️ Si Gazelle échoue → Timeline n'est PAS généré (évite les rapports avec données obsolètes)

---

### 2. **Système de Notifications Unifié** ✅

#### Architecture

```
core/notification_service.py (Service Centralisé)
  ├── core/slack_notifier.py (Slack)
  └── core/email_notifier.py (SendGrid Email)
```

#### Routage Intelligent

| Événement | Destination | Canal |
|-----------|-------------|-------|
| **Erreur Sync Gazelle** | Administrateurs | 📱 Slack |
| **Erreur Timeline** | Administrateurs | 📱 Slack |
| **Alerte Humidité** | Nicolas | 📧 Email + 📱 Slack |
| **Alerte Humidité** | Louise | 📱 Slack |

#### Configuration Email

Fichier `.env` - Variables à configurer :

```bash
# SendGrid (pour emails)
SENDGRID_API_KEY=your_sendgrid_api_key_here

# Destinataires des emails
EMAIL_NICOLAS=nicolas@example.com
EMAIL_ALLAN=allan@example.com
EMAIL_LOUISE=louise@example.com

# Email expéditeur
EMAIL_FROM=noreply@assistant-gazelle.com
EMAIL_FROM_NAME=Assistant Gazelle
```

#### Configuration Slack

Déjà en place, variables existantes :

```bash
# Webhooks Slack (déjà configurés)
SLACK_WEBHOOK_ADMIN_1=https://hooks.slack.com/...  # Louise
SLACK_WEBHOOK_ADMIN_2=https://hooks.slack.com/...  # Nicolas
SLACK_WEBHOOK_ALLAN=https://hooks.slack.com/...
```

---

### 3. **Logs de Santé (Traçabilité)** ✅

#### Tables Supabase

**`scheduler_logs`** - Logs des tâches planifiées
- Trace chaque exécution du scheduler (01:00 Gazelle, 16:00 Alertes, etc.)
- Enregistre : durée, statut, statistiques, déclencheur

**`sync_logs`** - Logs des synchronisations
- Trace les syncs manuelles et automatiques
- Format flexible pour tous types de scripts

#### Dashboard "Logs de Santé"

**Accès :** Admin → 🏥 Logs de Santé

**Affiche :**
- ⏰ **Tâches Planifiées** : Historique du scheduler (Gazelle, Timeline, Alertes RV)
- 🔄 **Synchronisations** : Historique des syncs manuelles
- 📊 **Statistiques** : Taux de succès, durées moyennes, dernières exécutions
- 🔍 **Détails** : Stats JSON dépliables pour chaque log

**Permet de voir d'un coup d'œil :**
- ✅ Tout s'est bien passé la nuit dernière ?
- ❌ Y a-t-il eu des erreurs récentes ?
- ⏱️ Combien de temps prennent les syncs ?
- 📈 Combien de données ont été synchronisées ?

---

### 4. **Cohérence des Alertes Humidité** ✅

**Problème résolu :** Dashboard, Slack et emails lisent tous la **même source de vérité**.

**Source unique :** Table Supabase `humidity_alerts`

**Workflow unifié :**
1. Scanner nocturne détecte alerte → enregistre dans `humidity_alerts`
2. Notification automatique :
   - Email → Nicolas (avec détails piano, client, lieu)
   - Slack → Nicolas + Louise (notification instantanée)
3. Dashboard affiche les alertes depuis `humidity_alerts`

**Module mis à jour :** `modules/alerts/humidity_scanner.py`
- Utilise maintenant `NotificationService` centralisé
- Envoie email ET Slack simultanément
- Configuration flexible des destinataires

---

## 🏗️ Architecture Technique

### Fichiers Créés/Modifiés

#### Nouveaux Fichiers

```
core/
  ├── email_notifier.py          # Module SendGrid pour emails
  └── notification_service.py    # Service centralisé notifications

frontend/src/components/
  └── SystemHealthDashboard.jsx  # Dashboard Logs de Santé

api/
  └── scheduler_logs_routes.py   # API endpoints pour scheduler_logs

sql/
  └── create_sync_logs_table.sql # Schéma table sync_logs

docs/
  └── ORCHESTRATION_ET_NOTIFICATIONS.md  # Ce fichier
```

#### Fichiers Modifiés

```
core/
  └── scheduler.py               # Orchestration Gazelle → Timeline + notifications

modules/alerts/
  └── humidity_scanner.py        # Utilise nouveau système notifications

scripts/
  └── sync_logger.py             # Support nouveau schéma sync_logs

api/
  └── main.py                    # Enregistrement routes scheduler_logs

frontend/src/
  └── App.jsx                    # Route "Logs de Santé" + bouton menu
```

---

## 📊 Schéma de la Table `sync_logs`

```sql
CREATE TABLE sync_logs (
    id UUID PRIMARY KEY,
    script_name TEXT NOT NULL,        -- "Sync Gazelle Totale", "Rapport Timeline"
    task_type TEXT NOT NULL,          -- "sync", "report", "chain", "backup"
    status TEXT NOT NULL,             -- "success", "error", "warning", "running"
    message TEXT,                     -- Message de succès/erreur
    stats JSONB,                      -- {"clients": 50, "pianos": 100, ...}
    error_details TEXT,               -- Stack trace si erreur
    triggered_by TEXT,                -- "scheduler", "manual", "api"
    triggered_by_user TEXT,           -- Email utilisateur si manuel
    created_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    execution_time_seconds INTEGER
);
```

**À exécuter dans Supabase :**
```bash
# Copier le contenu du fichier SQL
cat sql/create_sync_logs_table.sql

# Exécuter dans le SQL Editor de Supabase
```

---

## 🎯 Utilisation

### 1. Développeur : Ajouter des Notifications

```python
from core.notification_service import get_notification_service

notifier = get_notification_service()

# En cas d'erreur de sync
try:
    # ... code de sync ...
except Exception as e:
    notifier.notify_sync_error(
        task_name='Ma Sync Importante',
        error_message=str(e),
        send_slack=True,  # Notification Slack
        send_email=False   # Pas d'email (optionnel)
    )
```

### 2. Administrateur : Changer les Destinataires Email

**Fichier `.env` :**

```bash
# Pour changer le destinataire des alertes humidité
EMAIL_NICOLAS=nouveau-email@example.com

# Pour ajouter un destinataire (nécessite code)
# Modifier core/email_notifier.py → RECIPIENTS dict
```

### 3. Utilisateur : Consulter les Logs

1. Se connecter comme **Admin**
2. Cliquer sur **🏥 Logs de Santé** dans le menu
3. Consulter les 2 onglets :
   - ⏰ **Tâches Planifiées** (scheduler)
   - 🔄 **Synchronisations** (syncs manuelles)

---

## 🔧 Dépannage

### SendGrid n'envoie pas d'emails

**Problème :** `SENDGRID_API_KEY` manquante ou invalide

**Solution :**
1. Obtenir une clé API SendGrid (https://sendgrid.com)
2. Ajouter dans `.env` :
   ```bash
   SENDGRID_API_KEY=SG.xxx...
   ```
3. Redémarrer l'API :
   ```bash
   pkill -f "uvicorn api.main:app"
   python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
   ```

### Slack ne reçoit pas les notifications

**Problème :** Webhooks Slack incorrects

**Vérification :**
```bash
# Tester un webhook
curl -X POST https://hooks.slack.com/services/YOUR/WEBHOOK/URL \
  -H 'Content-Type: application/json' \
  -d '{"text": "🧪 Test notification"}'
```

### Timeline ne se génère pas après Gazelle

**Problème :** Sync Gazelle a échoué (normal, chaînage ne se déclenche que si succès)

**Vérification :**
1. Dashboard → **🏥 Logs de Santé**
2. Onglet **⏰ Tâches Planifiées**
3. Chercher la dernière "Sync Gazelle → Timeline"
4. Si ❌ rouge → voir le message d'erreur

**Solution manuelle :**
```bash
# Relancer Gazelle manuellement
python3 -c "from core.scheduler import task_sync_gazelle_totale; task_sync_gazelle_totale()"
```

### Dashboard Logs de Santé vide

**Problème :** Tables `scheduler_logs` ou `sync_logs` n'existent pas

**Solution :**
```sql
-- Exécuter dans Supabase SQL Editor
-- Fichier : sql/create_sync_logs_table.sql

-- Vérifier que task_label existe
ALTER TABLE scheduler_logs ADD COLUMN IF NOT EXISTS task_label TEXT;
```

---

## 📈 Métriques & KPIs

Le système enregistre automatiquement :

- ⏱️ **Durée d'exécution** de chaque tâche
- 📊 **Statistiques détaillées** (nb clients, pianos, RV synchronisés)
- ✅ **Taux de succès** (% de tâches réussies vs échouées)
- 🔔 **Notifications envoyées** (compteur par type)

**Visible dans :**
- Dashboard "Logs de Santé"
- API endpoints `/api/scheduler-logs/stats` et `/api/sync-logs/stats`

---

## 🎓 Exemples d'Utilisation

### Notification d'Erreur de Sync

```python
# Dans une tâche de sync personnalisée
from core.notification_service import get_notification_service

notifier = get_notification_service()

try:
    # Sync de données
    result = ma_fonction_sync()
except Exception as e:
    # Notifier sur Slack
    notifier.notify_sync_error(
        task_name='Sync Custom Data',
        error_message=f"Erreur: {str(e)}",
        send_slack=True
    )
    raise
```

### Notification d'Alerte Humidité

```python
# Déjà intégré dans humidity_scanner.py
notifier.notify_humidity_alert(
    piano_info={
        'nom': 'Steinway Model D',
        'client': 'Place des Arts',
        'lieu': 'Salle Wilfrid-Pelletier'
    },
    humidity_value=28.5,
    alert_type='TROP_SEC',
    send_email=True,  # Email à Nicolas
    send_slack=True   # Slack à Louise + Nicolas
)
```

### Logger une Sync dans sync_logs

```python
from scripts.sync_logger import SyncLogger

logger = SyncLogger()

logger.log_sync(
    script_name='Ma Sync Personnalisée',
    task_type='sync',
    status='success',
    message='Sync réussie',
    stats={'items': 150, 'duration': 12.5},
    execution_time_seconds=12,
    triggered_by='manual',
    triggered_by_user='allan@example.com'
)
```

---

## 🚀 Prochaines Étapes (Optionnelles)

### Améliorations Possibles

1. **Notifications par SMS** (Twilio)
   - Pour les alertes critiques
   - Backup si Slack/Email échouent

2. **Dashboard Temps Réel**
   - WebSocket pour mise à jour live
   - Graphiques de performance (Chart.js)

3. **Alertes Prédictives**
   - ML pour prédire les échecs de sync
   - Notifications proactives

4. **Intégration PagerDuty**
   - Escalade automatique pour erreurs critiques
   - Rotation des astreintes

---

## ✅ Checklist de Validation

- [x] **Orchestration** : Gazelle déclenche Timeline automatiquement
- [x] **Notifications** : Erreurs de sync → Slack admins
- [x] **Notifications** : Alertes humidité → Email Nicolas + Slack
- [x] **Logs** : Toutes les tâches enregistrées dans scheduler_logs
- [x] **Logs** : Syncs enregistrées dans sync_logs
- [x] **Dashboard** : Vue "Logs de Santé" accessible admin
- [x] **Cohérence** : Dashboard/Slack/Email lisent même table humidity_alerts

---

## 📞 Support

**Questions ou problèmes ?**

1. Consulter ce document
2. Vérifier Dashboard "Logs de Santé"
3. Vérifier fichier `.env` (clés API)
4. Consulter logs API : `tail -f /path/to/api/logs`

---

**Document créé le :** 2026-01-21  
**Version :** 1.0  
**Auteur :** Assistant Gazelle AI  
**Statut :** ✅ Implémentation Complète
