# 🎯 Activation : Orchestration & Notifications

## ⚡ Actions Immédiates Requises

### 1️⃣ Créer la Table `sync_logs` dans Supabase

**Durée :** 2 minutes

```bash
# 1. Copier le SQL
cat sql/create_sync_logs_table.sql

# 2. Dans Supabase Dashboard :
#    - Aller dans "SQL Editor"
#    - Coller le contenu du fichier
#    - Cliquer "Run"
```

**Résultat attendu :**
- ✅ Table `sync_logs` créée
- ✅ Index ajoutés pour performance
- ✅ Vue `v_recent_sync_logs` créée

---

### 2️⃣ Ajouter la Colonne `task_label` à `scheduler_logs`

**Durée :** 1 minute

Si ce n'est pas déjà fait :

```sql
-- Dans Supabase SQL Editor
ALTER TABLE scheduler_logs ADD COLUMN IF NOT EXISTS task_label TEXT;
```

---

### 3️⃣ Configurer SendGrid pour les Emails

**Durée :** 10 minutes

#### A. Créer un Compte SendGrid

1. Aller sur https://sendgrid.com
2. S'inscrire (gratuit jusqu'à 100 emails/jour)
3. Vérifier email

#### B. Générer une Clé API

1. Dashboard SendGrid → Settings → API Keys
2. Create API Key → Full Access
3. **Copier la clé** (ne sera plus visible après)

#### C. Ajouter dans `.env`

```bash
# Dans /Users/allansutton/Documents/assistant-gazelle-v5/.env

# SendGrid
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxxxxxxx

# Destinataires emails
EMAIL_NICOLAS=nicolas@vrai-email.com
EMAIL_ALLAN=allan@vrai-email.com
EMAIL_LOUISE=louise@vrai-email.com

# Expéditeur
EMAIL_FROM=noreply@gazelle-assistant.com
EMAIL_FROM_NAME=Assistant Gazelle
```

**⚠️ IMPORTANT :** Remplacer par les vrais emails !

---

### 4️⃣ Redémarrer l'API

**Durée :** 1 minute

Pour que les nouveaux modules soient chargés :

```bash
# Arrêter l'API actuelle
pkill -f "uvicorn api.main:app"

# Redémarrer
cd /Users/allansutton/Documents/assistant-gazelle-v5
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

**Vérifier :**
```bash
# Doit afficher "✅ Scheduler démarré avec succès"
# Doit afficher "✅ 01:00 - Sync Gazelle → Timeline (chaînées)"
```

---

### 5️⃣ Redémarrer le Frontend

**Durée :** 1 minute

```bash
# Terminal frontend
cd /Users/allansutton/Documents/assistant-gazelle-v5/frontend
npm run dev
```

---

## ✅ Validation

### Test 1 : Dashboard Logs de Santé

1. Ouvrir http://localhost:5174
2. Se connecter comme **admin**
3. Cliquer sur **🏥 Logs de Santé** dans le menu
4. Vérifier que les 2 onglets s'affichent :
   - ⏰ Tâches Planifiées
   - 🔄 Synchronisations

**Si vide :** Normal, les logs s'accumuleront au fil du temps.

---

### Test 2 : API Endpoints

```bash
# Tester endpoint scheduler logs
curl http://localhost:8000/api/scheduler-logs/recent

# Tester endpoint sync logs
curl http://localhost:8000/api/sync-logs/recent
```

**Résultat attendu :** JSON avec `{"logs": [], "count": 0, ...}`

---

### Test 3 : Notification Slack (Erreur de Sync)

```bash
# Forcer une erreur de sync pour tester
python3 << 'EOF'
from core.notification_service import get_notification_service

notifier = get_notification_service()
notifier.notify_sync_error(
    task_name='Test Notification',
    error_message='Test erreur de sync',
    send_slack=True
)
print("✅ Notification test envoyée !")
EOF
```

**Résultat attendu :** Message sur Slack des admins

---

### Test 4 : Email SendGrid

```bash
# Tester l'envoi d'email
python3 << 'EOF'
from core.email_notifier import get_email_notifier

notifier = get_email_notifier()
success = notifier.send_email(
    to_emails=['nicolas@example.com'],  # Remplacer par vrai email
    subject='Test Assistant Gazelle',
    html_content='<h1>✅ Email fonctionne !</h1><p>SendGrid configuré correctement.</p>'
)
print(f"Email envoyé : {success}")
EOF
```

**Résultat attendu :** Email reçu dans la boîte (vérifier spam)

---

### Test 5 : Orchestration Gazelle → Timeline

**⚠️ Ne pas exécuter maintenant** (attendre la nuit pour la sync automatique)

Pour tester manuellement :

```bash
# ATTENTION : Lance une sync complète (peut prendre 10-20 min)
python3 -c "from core.scheduler import task_sync_gazelle_totale; task_sync_gazelle_totale(triggered_by='manual', user_email='allan@example.com')"
```

**Vérifier dans Dashboard Logs de Santé :**
- ✅ Sync Gazelle : success
- ✅ Rapport Timeline : success (généré automatiquement)

---

## 🔍 Vérification Finale

### Checklist Activation

- [ ] Table `sync_logs` créée dans Supabase
- [ ] Colonne `task_label` ajoutée à `scheduler_logs`
- [ ] SendGrid configuré (clé API dans `.env`)
- [ ] Emails destinataires configurés dans `.env`
- [ ] API redémarrée avec succès
- [ ] Frontend redémarré avec succès
- [ ] Dashboard "Logs de Santé" accessible
- [ ] Test notification Slack réussi
- [ ] Test email SendGrid réussi

---

## 🌙 Première Sync Nocturne

**Cette nuit à 01:00 :**

1. ⏰ Scheduler déclenche `Sync Gazelle Totale`
2. 🔄 Sync Gazelle s'exécute (clients, pianos, timeline, appointments)
3. ✅ Si succès → Génération automatique du Rapport Timeline
4. 📊 Tout est loggé dans `scheduler_logs`
5. 📧 Si erreur → Notification Slack automatique aux admins

**Demain matin :**

1. Dashboard → 🏥 Logs de Santé
2. Vérifier que tout est ✅ vert
3. Si ❌ rouge → Lire le message d'erreur

---

## 📚 Documentation Complète

Lire pour plus de détails :

```
docs/ORCHESTRATION_ET_NOTIFICATIONS.md
```

Contient :
- Architecture complète
- Schémas des tables
- Exemples de code
- Dépannage
- Utilisation avancée

---

## 🆘 En Cas de Problème

### Problème : API ne démarre pas

```bash
# Vérifier erreurs
tail -f /Users/allansutton/Documents/assistant-gazelle-v5/api.log

# Ou lancer en mode debug
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### Problème : Dashboard Logs vide

```sql
-- Vérifier que les tables existent
SELECT * FROM scheduler_logs LIMIT 1;
SELECT * FROM sync_logs LIMIT 1;
```

### Problème : Emails ne partent pas

```bash
# Vérifier configuration
python3 -c "import os; from dotenv import load_dotenv; load_dotenv(); print(f'SendGrid: {os.getenv(\"SENDGRID_API_KEY\")[:10]}...')"
```

Doit afficher : `SendGrid: SG.xxxxxx...`

### Problème : Slack ne reçoit rien

```bash
# Tester webhook directement
curl -X POST $SLACK_WEBHOOK_ADMIN_1 \
  -H 'Content-Type: application/json' \
  -d '{"text": "Test depuis terminal"}'
```

---

## 🎉 C'est Tout !

Système prêt à fonctionner automatiquement.

**Cette nuit à 01:00 :**
- Sync Gazelle → Timeline (chaînées)
- Logs enregistrés
- Notifications si erreur

**Demain matin :**
- Dashboard "Logs de Santé" pour tout vérifier

---

**Besoin d'aide ?** Consulter `docs/ORCHESTRATION_ET_NOTIFICATIONS.md`
