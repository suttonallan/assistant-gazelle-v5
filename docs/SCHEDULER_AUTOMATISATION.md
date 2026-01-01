# 📅 Automatisation des Tâches Planifiées - Assistant Gazelle V5

## Vue d'ensemble

Le système de scheduler automatise 4 tâches critiques qui s'exécutent quotidiennement pour maintenir les données à jour et envoyer les alertes nécessaires.

## ✅ Tâches Automatisées

### 1. 🔄 01:00 - Sync Gazelle Totale

**Objectif:** Rafraîchit toutes les données depuis l'API Gazelle vers Supabase

**Données synchronisées:**
- Clients (gazelle_clients)
- Contacts (gazelle_contacts)
- Pianos (gazelle_pianos)
- Timeline entries (gazelle_timeline_entries)
- Appointments (gazelle_appointments)

**Fréquence:** Tous les jours à 01:00 (heure Montréal)

**Fichier:** `core/scheduler.py` → `task_sync_gazelle_totale()`

---

### 2. 📊 02:00 - Rapport Timeline Google Sheets

**Objectif:** Génère le rapport Timeline dans Google Sheets

**Onglets générés:**
- UQAM
- Vincent d'Indy
- Place des Arts
- Alertes Maintenance

**Fréquence:** Tous les jours à 02:00 (heure Montréal)

**Fichier:** `core/scheduler.py` → `task_generate_rapport_timeline()`

**Lien:** [Rapport Timeline](https://docs.google.com/spreadsheets/d/1ZZsMrIT0BEwHKQ6-BKGzFoXR3k99zCEzixp0tsRKUj8)

---

### 3. 💾 03:00 - Backup SQL

**Objectif:** Sauvegarde la base de données SQLite

**Détails:**
- Crée un backup horodaté dans `data/backups/`
- Garde les 10 derniers backups
- Supprime automatiquement les anciens backups

**Fréquence:** Tous les jours à 03:00 (heure Montréal)

**Fichier:** `core/scheduler.py` → `task_backup_database()`

---

### 4. 📧 16:00 - Sync RV & Alertes

**Objectif:** Importe les RV et envoie les alertes pour RV non confirmés

**Processus:**
1. Synchronise les appointments depuis Gazelle
2. Détecte les RV non confirmés pour le lendemain
3. Envoie des emails aux techniciens concernés

**Fréquence:** Tous les jours à 16:00 (heure Montréal)

**Fichier:** `core/scheduler.py` → `task_sync_rv_and_alerts()`

---

## 🎯 Journal des Tâches (Frontend)

### Accès

Dans l'application V5 (port 5176):
1. Se connecter en tant qu'Admin (Allan)
2. Aller dans l'onglet **Inventaire**
3. Cliquer sur **⏰ Tâches** (visible uniquement pour les admins)

### Fonctionnalités

**1. Exécution Manuelle**
- 4 boutons pour lancer chaque tâche manuellement
- Exécution en arrière-plan (ne bloque pas l'UI)
- Feedback visuel pendant l'exécution

**2. Historique des Exécutions**
- Tableau des 20 dernières exécutions
- Colonnes:
  - Heure de démarrage
  - Nom de la tâche
  - Statut (✅ Succès / ❌ Erreur / ⏳ En cours)
  - Durée d'exécution
  - Message détaillé
  - Déclencheur (⏰ Auto / 👤 Manuel)

**3. Auto-refresh**
- Les logs se rafraîchissent automatiquement toutes les 30 secondes

---

## 🗄️ Base de Données

### Table: `scheduler_logs`

**Colonnes principales:**
- `id` - UUID unique
- `task_name` - Nom technique ('sync_gazelle', 'rapport_timeline', 'backup', 'rv_alerts')
- `task_label` - Libellé affiché dans l'UI
- `started_at` - Heure de démarrage
- `completed_at` - Heure de fin
- `duration_seconds` - Durée en secondes
- `status` - Statut ('success', 'error', 'running')
- `message` - Message de détail ou erreur
- `stats` - Statistiques JSON (ex: `{"clients": 150, "pianos": 250}`)
- `triggered_by` - Mode ('scheduler', 'manual', 'api')
- `triggered_by_user` - Email de l'utilisateur si manuel

### Création de la Table

**⚠️ IMPORTANT:** La table doit être créée manuellement dans Supabase

**Étapes:**
1. Aller dans [Supabase Dashboard](https://supabase.com/dashboard)
2. Sélectionner votre projet
3. Aller dans **SQL Editor**
4. Copier le contenu de `scripts/create_scheduler_logs_table.sql`
5. Exécuter le script

**Ou via psql:**
```bash
psql $DATABASE_URL < scripts/create_scheduler_logs_table.sql
```

---

## 🔌 API Endpoints

### GET /scheduler/logs

Récupère les logs récents

**Paramètres:**
- `limit` (optionnel) - Nombre de logs (défaut: 20)

**Exemple:**
```bash
curl "http://localhost:8000/scheduler/logs?limit=20"
```

---

### POST /scheduler/run/sync

Exécute la synchronisation Gazelle manuellement

**Body:**
```json
{
  "user_email": "asutton@piano-tek.com"
}
```

**Réponse:**
```json
{
  "success": true,
  "message": "Synchronisation Gazelle démarrée en arrière-plan",
  "task_name": "sync_gazelle",
  "started_at": "2026-01-01T14:30:00"
}
```

---

### POST /scheduler/run/rapport

Exécute la génération du rapport Timeline manuellement

---

### POST /scheduler/run/backup

Exécute le backup de la base de données manuellement

---

### POST /scheduler/run/alerts

Exécute le sync RV & alertes manuellement

---

## 🧪 Tests

### Test Manuel des Tâches

Script de test disponible: `test_scheduled_tasks.py`

**Usage:**
```bash
# Tester toutes les tâches
python3 test_scheduled_tasks.py

# Tester une tâche spécifique
python3 test_scheduled_tasks.py --task sync
python3 test_scheduled_tasks.py --task rapport
python3 test_scheduled_tasks.py --task backup
python3 test_scheduled_tasks.py --task alerts
```

---

## 📝 Fichiers Créés/Modifiés

### Nouveaux Fichiers

**Backend:**
- `core/scheduler.py` - Module scheduler principal avec APScheduler
- `core/scheduler_logger.py` - Helper pour logger dans Supabase
- `api/scheduler_routes.py` - Endpoints API pour logs et exécution manuelle
- `scripts/create_scheduler_logs_table.sql` - Script SQL pour créer la table
- `test_scheduled_tasks.py` - Script de test des tâches

**Frontend:**
- `frontend/src/components/SchedulerJournal.jsx` - Composant Journal des Tâches

### Fichiers Modifiés

**Backend:**
- `api/main.py` - Intégration du scheduler au démarrage/arrêt de l'API

**Frontend:**
- `frontend/src/components/InventaireDashboard.jsx` - Ajout de l'onglet "⏰ Tâches"

---

## 🚀 Déploiement

### Sur Render (Production)

Le scheduler démarre automatiquement avec l'API:
1. L'API démarre (déclenchement automatique via GitHub push)
2. `startup_event()` dans `main.py` appelle `start_scheduler()`
3. Les 4 tâches sont configurées avec leurs horaires
4. Logs enregistrés dans `scheduler_logs` Supabase

**Variables d'environnement requises:**
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `GAZELLE_CLIENT_ID`
- `GAZELLE_CLIENT_SECRET`
- `SENDGRID_API_KEY` (pour les alertes RV)

### En Développement (Local)

```bash
# Démarrer l'API avec le scheduler
cd /Users/allansutton/Documents/assistant-gazelle-v5
source .env
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

Le scheduler démarre automatiquement et affiche:
```
🚀 Scheduler démarré avec succès

📅 Prochaines exécutions:
   - Sync Gazelle Totale (01:00): 2026-01-02 01:00:00
   - Rapport Timeline Google Sheets (02:00): 2026-01-02 02:00:00
   - Backup SQL (03:00): 2026-01-02 03:00:00
   - Sync RV & Alertes (16:00): 2026-01-01 16:00:00
```

---

## 🎨 Cohérence "Nick"

Le système utilise le fichier central `config/techniciens.config.js` pour s'assurer que:
- Tous les logs affichent "Nick" au lieu de "Nicolas"
- Les stats remplacent "Nicolas" par "Nick" dans les messages
- La fonction `formatMessage()` dans `SchedulerJournal.jsx` fait le remplacement

---

## ⚙️ Configuration APScheduler

**Timezone:** `America/Montreal`

**Triggers:** CronTrigger (format cron)
- `hour=1, minute=0` → 01:00
- `hour=2, minute=0` → 02:00
- `hour=3, minute=0` → 03:00
- `hour=16, minute=0` → 16:00

**Options:**
- `max_instances=1` - Une seule instance par tâche à la fois
- `replace_existing=True` - Remplace les jobs existants au redémarrage

---

## 🐛 Dépannage

### Le scheduler ne démarre pas

**Vérifier:**
1. Les logs de démarrage de l'API
2. Les variables d'environnement Supabase
3. La table `scheduler_logs` existe dans Supabase

### Les tâches ne s'exécutent pas

**Vérifier:**
1. L'heure du serveur (timezone)
2. Les logs du scheduler dans la console
3. La table `scheduler_logs` pour les erreurs

### Les logs ne s'affichent pas dans le frontend

**Vérifier:**
1. La table `scheduler_logs` existe
2. L'endpoint `/scheduler/logs` fonctionne
3. Les permissions RLS dans Supabase

---

## 📚 Ressources

**Documentation APScheduler:**
- https://apscheduler.readthedocs.io/

**Code Source:**
- Scheduler: `/core/scheduler.py`
- Logger: `/core/scheduler_logger.py`
- API Routes: `/api/scheduler_routes.py`
- Frontend: `/frontend/src/components/SchedulerJournal.jsx`

---

**Dernière mise à jour:** 2026-01-01

**Auteur:** Assistant Gazelle V5 - Claude Code
