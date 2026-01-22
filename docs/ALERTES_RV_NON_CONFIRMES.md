# 📧 Alertes RV Non Confirmés - Guide Complet

## ❓ Pourquoi ça n'a pas fonctionné hier ?

### Problème Identifié

**Le scheduler n'était PAS actif** → La tâche programmée à 16:00 n'a pas tourné.

**Causes possibles :**
1. L'API a été redémarrée et le scheduler n'a pas été relancé automatiquement
2. Le processus uvicorn s'est arrêté
3. Le scheduler a été arrêté manuellement

**Solution :**
- Le scheduler démarre maintenant automatiquement avec l'API (dans `api/main.py` startup event)
- Vérification : Dashboard → 🏥 Logs de Santé → Vérifier que le scheduler est actif

---

## 📬 À Qui les Alertes Vont ?

### Destinataires

Les alertes sont envoyées **aux techniciens concernés** qui ont des RV non confirmés pour le lendemain.

**Emails actuels configurés :**
- **Nick** (`usr_HcCiFk7o0vZ9xAI0`) → `nlessard@piano-tek.com`
- **JP** (`usr_ReUSmIJmBF86ilY1`) → `jpreny@gmail.com`
- **Allan** (`usr_ofYggsCDt2JAVeNP`) → `asutton@piano-tek.com`

**Chaque technicien reçoit :**
- Un email avec **ses propres RV non confirmés**
- Liste complète avec heures, clients, détails
- Format HTML lisible

---

## 📧 Comment les Alertes Sont Envoyées ?

### Méthode d'Envoi

**1. SendGrid (Recommandé - Production)**
- Si `SENDGRID_API_KEY` est configuré dans `.env`
- Envoi via API SendGrid
- Fiable et rapide

**2. SMTP Gmail (Fallback)**
- Si SendGrid n'est pas configuré
- Utilise `SMTP_USER` et `SMTP_PASSWORD` depuis `.env`
- Connexion via `smtp.gmail.com:587`

**3. Mode Simulation (Développement)**
- Si aucune méthode n'est configurée
- Affiche l'email dans les logs (pas d'envoi réel)
- Utile pour tester sans envoyer de vrais emails

### Configuration Requise

**Fichier `.env` :**

```bash
# Option 1: SendGrid (recommandé)
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxx

# Option 2: SMTP Gmail (fallback)
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Expéditeur
ALERT_FROM_EMAIL=alerts@piano-tek.com
ALERT_FROM_NAME=Assistant Gazelle Alertes
```

---

## ⏰ Quand les Alertes Sont Envoyées ?

### Horaire Automatique

**Tous les jours à 16:00 (heure Montréal)**

**Workflow :**
1. **16:00** → Scheduler déclenche `task_sync_rv_and_alerts`
2. **Sync appointments** → Récupère les derniers RV depuis Gazelle
3. **Détection** → Identifie les RV non confirmés pour **demain**
4. **Envoi** → Envoie un email à chaque technicien concerné
5. **Logging** → Enregistre tout dans `alert_logs` (Supabase)

### Critères de Détection

Un RV est considéré "non confirmé" si :
- `status = 'ACTIVE'` (pas annulé)
- `appointment_date = demain`
- `technicien` assigné (pas "À attribuer")
- Pas de confirmation explicite dans les notes

---

## 📊 Dashboard des Alertes

### Accès

**Menu Admin → 📧 Alertes RV**

### Fonctionnalités

**Onglet 1 : RV Non Confirmés Actuels**
- Liste des techniciens avec RV non confirmés
- Détails de chaque RV (heure, client, titre)
- Compteur par technicien

**Onglet 2 : Historique des Alertes**
- Toutes les alertes envoyées (depuis `alert_logs`)
- Statut (✅ Envoyé, ❌ Échec, ✓ Lu)
- Date d'envoi
- Détails complets

**Statistiques :**
- Total alertes envoyées
- Nombre de RV alertés
- Nombre de techniciens concernés
- Taux de succès d'envoi

---

## 🔍 Vérification et Dépannage

### Vérifier que le Système Fonctionne

**1. Scheduler actif ?**
```bash
# Dashboard → 🏥 Logs de Santé
# Vérifier que "Sync RV & Alertes (16:00)" est programmé
```

**2. Test manuel (sans envoyer d'emails) :**
```bash
python3 << 'EOF'
from modules.alertes_rv.checker import AppointmentChecker
from core.supabase_storage import SupabaseStorage
from datetime import datetime, timedelta

storage = SupabaseStorage()
checker = AppointmentChecker(storage)

target_date = (datetime.now() + timedelta(days=1)).date()
appointments = checker.get_unconfirmed_appointments(target_date)

print(f"Techniciens avec RV non confirmés: {len(appointments)}")
for tech_id, apts in appointments.items():
    print(f"  {tech_id}: {len(apts)} RV")
EOF
```

**3. Vérifier les logs :**
```bash
# Dashboard → 📧 Alertes RV → Historique
# Vérifier que les alertes d'hier apparaissent
```

### Problèmes Courants

**Problème : Aucune alerte envoyée**

**Solutions :**
1. Vérifier que le scheduler est actif
2. Vérifier que SendGrid/SMTP est configuré
3. Vérifier les logs dans Dashboard → 🏥 Logs de Santé
4. Vérifier qu'il y a bien des RV non confirmés pour demain

**Problème : Emails non reçus**

**Solutions :**
1. Vérifier les spams
2. Vérifier que l'email du technicien est correct dans `users` table
3. Vérifier les logs d'envoi (Dashboard → 📧 Alertes RV → Historique)
4. Tester manuellement l'envoi d'email

**Problème : Scheduler ne démarre pas**

**Solutions :**
1. Vérifier que l'API tourne : `ps aux | grep uvicorn`
2. Redémarrer l'API : `python3 -m uvicorn api.main:app --reload`
3. Vérifier les erreurs dans les logs de l'API

---

## 📝 Structure des Données

### Table `alert_logs` (Supabase)

Chaque alerte envoyée est enregistrée avec :

```sql
{
  id: UUID,
  appointment_id: TEXT,        -- ID du RV
  technician_id: TEXT,         -- ID Gazelle du technicien
  technician_name: TEXT,        -- Nom du technicien
  technician_email: TEXT,       -- Email du technicien
  appointment_date: DATE,       -- Date du RV
  appointment_time: TIME,      -- Heure du RV
  client_name: TEXT,           -- Nom du client
  service_type: TEXT,           -- Type de service
  title: TEXT,                  -- Titre du RV
  status: TEXT,                 -- 'sent' ou 'failed'
  acknowledged: BOOLEAN,        -- Lu par le technicien ?
  sent_at: TIMESTAMP,           -- Date d'envoi
  triggered_by: TEXT            -- 'scheduler' ou 'manual'
}
```

---

## 🎯 Utilisation

### Consulter les Alertes

1. **Dashboard → 📧 Alertes RV**
2. **Onglet "RV Non Confirmés Actuels"** → Voir qui a des RV non confirmés maintenant
3. **Onglet "Historique"** → Voir toutes les alertes envoyées

### Forcer un Envoi Manuel

**Via API :**
```bash
curl -X POST http://localhost:8000/api/alertes-rv/send \
  -H "Content-Type: application/json" \
  -d '{"target_date": "2026-01-22"}'
```

**Via Python :**
```python
from modules.alertes_rv.service import UnconfirmedAlertsService
from datetime import date

service = UnconfirmedAlertsService()
result = service.send_alerts(
    target_date=date(2026, 1, 22),
    triggered_by='manual'
)
```

---

## ✅ Checklist de Validation

- [ ] Scheduler actif (Dashboard → 🏥 Logs de Santé)
- [ ] Tâche "Sync RV & Alertes" programmée à 16:00
- [ ] SendGrid ou SMTP configuré dans `.env`
- [ ] Emails des techniciens corrects dans table `users`
- [ ] Dashboard 📧 Alertes RV accessible
- [ ] Test manuel de détection fonctionne
- [ ] Historique des alertes s'affiche

---

## 📞 Support

**En cas de problème :**
1. Vérifier Dashboard → 🏥 Logs de Santé
2. Vérifier Dashboard → 📧 Alertes RV → Historique
3. Vérifier les logs de l'API
4. Tester manuellement la détection

---

**Document créé le :** 2026-01-21  
**Version :** 1.0  
**Statut :** ✅ Système Opérationnel
