# Module Alertes de Rendez-vous Non Confirmés

## Description

Ce module gère les alertes pour les rendez-vous non confirmés par les clients. Il permet de :

- Détecter les RV non confirmés (créés il y a plus de X jours sans confirmation)
- Envoyer des notifications par email
- Suivre qui a reçu les alertes et quand
- Visualiser l'historique des alertes dans le dashboard admin

## Architecture

### Backend
- **Endpoint API** : `/alertes-rv/`
- **Stockage** : Supabase (table `appointment_alerts`)
- **Notifications** : Email via API (à définir)

### Frontend
- **Vue admin** : Liste des RV non confirmés avec historique d'alertes
- **Permissions** : Accessible uniquement aux admins (Allan, Louise)

## Flux de travail

1. **Détection automatique** (cron quotidien ou manuel)
   - Récupérer les RV depuis Gazelle API
   - Identifier ceux non confirmés depuis > 3 jours
   - Créer des alertes dans Supabase

2. **Notification**
   - Envoyer email au client
   - Logger l'envoi (qui, quand, statut)

3. **Suivi dans Dashboard**
   - Voir qui a reçu des alertes
   - Quand les alertes ont été envoyées
   - Statut de confirmation

## Tables Supabase

### `appointment_alerts`
```sql
CREATE TABLE appointment_alerts (
    id SERIAL PRIMARY KEY,
    appointment_id TEXT NOT NULL,
    client_name TEXT,
    client_email TEXT,
    appointment_date TIMESTAMP,
    alert_sent_at TIMESTAMP DEFAULT NOW(),
    alert_sent_by TEXT,  -- Email de l'utilisateur qui a déclenché l'alerte
    status TEXT DEFAULT 'sent',  -- 'sent', 'confirmed', 'cancelled'
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Utilisation

### Déclencher les alertes manuellement
```python
python modules/alertes-rv/check_unconfirmed.py
```

### API Endpoints
- `GET /alertes-rv/check` - Vérifier les RV non confirmés
- `GET /alertes-rv/alerts` - Lister toutes les alertes
- `POST /alertes-rv/send/{appointment_id}` - Envoyer une alerte pour un RV spécifique
