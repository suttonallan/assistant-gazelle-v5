# 🔧 Configuration SendGrid - Guide de Dépannage

## ✅ Actions Effectuées

1. **Clé API ajoutée dans `.env`**
   ```bash
   SENDGRID_API_KEY=YOUR_SENDGRID_API_KEY
   ```

2. **SendGrid ajouté dans `requirements.txt`**
   ```bash
   sendgrid>=6.12.5
   ```

3. **Variables email configurées**
   ```bash
   EMAIL_ALLAN=asutton@piano-tek.com
   ALERT_FROM_EMAIL=alerts@piano-tek.com
   ALERT_FROM_NAME=Assistant Gazelle Alertes
   ```

4. **Routage erreurs → Email Allan**
   - Erreurs de sync Gazelle → Email Allan
   - Erreurs Timeline → Email Allan
   - Alertes humidité → Email Nicolas (comme avant)

---

## ⚠️ Problème Actuel : Erreur 403 Forbidden

### Symptôme

Lors de l'envoi d'email via SendGrid, erreur :
```
HTTP Error 403: Forbidden
```

### Causes Possibles

1. **Email expéditeur non vérifié**
   - SendGrid nécessite que l'adresse email expéditrice soit vérifiée
   - Solution : Vérifier `alerts@piano-tek.com` ou `asutton@piano-tek.com` dans SendGrid Dashboard

2. **Permissions API insuffisantes**
   - La clé API doit avoir "Full Access" ou au minimum "Mail Send" permissions
   - Solution : Vérifier les permissions dans SendGrid → Settings → API Keys

3. **Domaine non authentifié**
   - Si utilisation d'un domaine personnalisé, il doit être authentifié
   - Solution : Authentifier le domaine `piano-tek.com` dans SendGrid

4. **Clé API révoquée ou expirée**
   - La clé peut avoir été révoquée
   - Solution : Générer une nouvelle clé API dans SendGrid

---

## 🔍 Vérification dans SendGrid Dashboard

### 1. Vérifier l'Email Expéditeur

1. Aller sur https://app.sendgrid.com
2. Settings → Sender Authentication
3. Single Sender Verification
4. Vérifier que `alerts@piano-tek.com` ou `asutton@piano-tek.com` est vérifié

### 2. Vérifier les Permissions de la Clé API

1. Settings → API Keys
2. Trouver la clé API correspondante
3. Vérifier qu'elle a "Full Access" ou "Mail Send" permissions

### 3. Vérifier l'Authentification du Domaine

1. Settings → Sender Authentication
2. Domain Authentication
3. Vérifier que `piano-tek.com` est authentifié (si utilisé)

---

## 🧪 Test Après Correction

Une fois les problèmes ci-dessus résolus, tester :

```bash
python3 << 'EOF'
import os
from dotenv import load_dotenv
load_dotenv()

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

sendgrid_key = os.getenv('SENDGRID_API_KEY')
allan_email = 'asutton@piano-tek.com'

message = Mail(
    from_email=Email(allan_email, 'Assistant Gazelle'),
    to_emails=To(allan_email, 'Allan'),
    subject='Test SendGrid',
    html_content=Content("text/html", "<p>Test réussi !</p>")
)

sg = SendGridAPIClient(sendgrid_key)
response = sg.send(message)

if response.status_code in [200, 202]:
    print("✅ Email envoyé avec succès !")
else:
    print(f"❌ Erreur {response.status_code}")
EOF
```

---

## 📊 État Actuel du Système

### ✅ Fonctionnel

- **SendGrid installé** : Version 6.12.5
- **Clé API configurée** : Dans `.env`
- **Code prêt** : Tous les modules utilisent SendGrid
- **Routage erreurs** : → Email Allan configuré
- **Orchestration** : Gazelle → Timeline automatique

### ⚠️ En Attente

- **Envoi d'emails** : Bloqué par erreur 403 (à corriger dans SendGrid Dashboard)

### 🔄 Fallback Actif

En attendant la résolution du 403, le système utilise :
- **SMTP Gmail** (si `SMTP_USER` et `SMTP_PASSWORD` configurés)
- **Mode simulation** (si rien n'est configuré - affiche dans logs)

---

## 🎯 Prochaines Étapes

1. **Vérifier SendGrid Dashboard** :
   - Email expéditeur vérifié
   - Permissions clé API
   - Domaine authentifié

2. **Tester l'envoi** :
   - Utiliser le script de test ci-dessus
   - Vérifier que l'email arrive

3. **Une fois fonctionnel** :
   - Les alertes RV non confirmés utiliseront SendGrid automatiquement
   - Les erreurs de sync enverront des emails à Allan
   - Les alertes humidité enverront des emails à Nicolas

---

**Document créé le :** 2026-01-21  
**Statut :** ⚠️ Configuration complète, en attente résolution 403 SendGrid
