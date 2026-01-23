# Configuration Zoom SMS

Ce guide explique comment configurer l'envoi de SMS via l'API Zoom Phone.

## Prérequis

1. **Scope activé**: Le scope `phone:write:sms` doit être activé sur votre application Zoom
2. **Credentials Zoom**: Vous devez avoir un Client ID, Client Secret, et Account ID Zoom

## Configuration des variables d'environnement

Ajoutez les variables suivantes dans votre fichier `.env`:

```env
# Zoom OAuth pour SMS
ZOOM_CLIENT_ID=votre_client_id
ZOOM_CLIENT_SECRET=votre_client_secret
ZOOM_ACCOUNT_ID=votre_account_id
```

### Comment obtenir ces credentials:

1. **ZOOM_CLIENT_ID et ZOOM_CLIENT_SECRET**:
   - Allez sur https://marketplace.zoom.us/
   - Créez une nouvelle application Server-to-Server OAuth
   - Activez le scope `phone:write:sms`
   - Copiez le Client ID et Client Secret

2. **ZOOM_ACCOUNT_ID**:
   - Dans votre application Zoom, allez dans "App Credentials"
   - L'Account ID est affiché dans la section "Server-to-Server OAuth"

## Utilisation

### Via le script de test

```bash
python3 test_send_sms.py +15551234567 "Votre message ici"
```

Le numéro peut être formaté de différentes façons:
- `+15551234567` (format E.164)
- `5551234567` (10 chiffres, format US/Canada)
- `5145551234` (10 chiffres avec indicatif régional)

### Via le code Python

```python
from core.zoom_sms import send_zoom_sms

result = send_zoom_sms(
    to_number="+15551234567",
    message="Votre message SMS"
)

if result['success']:
    print(f"SMS envoyé! Message ID: {result['message_id']}")
else:
    print(f"Erreur: {result['error']}")
```

## Format des numéros de téléphone

Les numéros sont automatiquement formatés en E.164:
- Format E.164: `+[code pays][numéro]` (ex: `+15551234567`)
- Maximum 15 chiffres après le `+`
- Le code pays `+1` est ajouté automatiquement pour les numéros US/Canada à 10 chiffres

## Limites

- Longueur maximale du message: 1600 caractères
- Les SMS sont envoyés via l'utilisateur Zoom associé au token OAuth

## Dépannage

### Erreur: "ZOOM_CLIENT_ID et ZOOM_CLIENT_SECRET doivent être configurés"
→ Vérifiez que les variables sont bien définies dans `.env`

### Erreur: "ZOOM_ACCOUNT_ID requis"
→ Ajoutez `ZOOM_ACCOUNT_ID` dans votre `.env`

### Erreur: "Erreur OAuth Zoom 401"
→ Vérifiez que vos credentials sont corrects et que le scope `phone:write:sms` est activé

### Erreur: "Erreur API Zoom 403"
→ Vérifiez que le scope `phone:write:sms` est bien activé sur votre application Zoom
