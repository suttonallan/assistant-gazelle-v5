# Alertes RV Non Confirmés - Routage Ciblé J-1

## 📋 Vue d'ensemble

Modification de la règle d'urgence J-1 pour les rendez-vous non confirmés avec routage ciblé par technicien.

## ✅ Modifications Implémentées

### 1. Identification du Technicien

Le script identifie automatiquement le technicien assigné au rendez-vous dans Gazelle par son nom :
- **Nicolas** (ou "Nick") → Email Nicolas
- **Allan** → Email Allan  
- **JP** (ou "Jean-Philippe", "Jean Philippe") → Email JP
- **Fallback** : Si technicien non reconnu → Email Nicolas par défaut

### 2. Routage Ciblé

Les emails sont envoyés directement au technicien concerné :
- **Nicolas** → `EMAIL_NICOLAS` (variable d'environnement)
- **Allan** → `EMAIL_ALLAN` (variable d'environnement)
- **JP** → `EMAIL_JP` (variable d'environnement)

### 3. Contenu Personnalisé

Chaque alerte contient un message personnalisé :
```
Salut [Nom],
Ton rendez-vous de demain chez [Client] n'est toujours pas confirmé.
```

**Format** : Un email par RV non confirmé (au lieu d'un email groupé).

### 4. Dashboard Alerts

Chaque alerte crée une entrée dans la table `dashboard_alerts` avec :
- **Type** : `URGENCE_CONFIRMATION`
- **Severity** : `warning` (affichage en rouge sur le Dashboard)
- **Technician Name** : Nom du technicien concerné
- **Client Name** : Nom du client
- **Appointment Date/Time** : Date et heure du RV

## 📁 Fichiers Modifiés

### 1. `modules/alertes_rv/service.py`
- Ajout de `_identify_technician_and_route()` : Identification et routage
- Ajout de `_format_urgence_message()` : Message personnalisé
- Modification de `send_alerts()` : Routage ciblé + un email par RV
- Ajout de `_create_dashboard_alerts()` : Création des entrées dashboard
- Ajout de `_dashboard_alert_exists()` : Vérification doublons

### 2. `core/scheduler.py`
- Correction de l'affichage des résultats (nouveau format)

### 3. `sql/create_dashboard_alerts_table.sql` (Nouveau)
- Création de la table `dashboard_alerts`
- Vue `v_dashboard_alerts_pending` pour les alertes non reconnues

## 🔧 Configuration Requise

### Variables d'Environnement (.env)

```bash
# Emails des techniciens
EMAIL_NICOLAS=nicolas@pianotekinc.com
EMAIL_ALLAN=asutton@piano-tek.com
EMAIL_JP=jp@pianotekinc.com

# SendGrid (déjà configuré)
SENDGRID_API_KEY=...
EMAIL_FROM=info@piano-tek.com
```

### Base de Données

Exécuter le script SQL pour créer la table `dashboard_alerts` :

```sql
-- Exécuter dans Supabase SQL Editor
\i sql/create_dashboard_alerts_table.sql
```

Ou copier-coller le contenu du fichier dans l'éditeur SQL de Supabase.

## 📊 Structure Table dashboard_alerts

```sql
CREATE TABLE dashboard_alerts (
    id UUID PRIMARY KEY,
    type VARCHAR(50) NOT NULL,  -- 'URGENCE_CONFIRMATION'
    severity VARCHAR(20) NOT NULL DEFAULT 'warning',  -- 'warning' = rouge
    title VARCHAR(255) NOT NULL,
    message TEXT,
    technician_id VARCHAR(255),
    technician_name VARCHAR(255),
    appointment_id VARCHAR(255),
    client_name VARCHAR(255),
    appointment_date DATE,
    appointment_time TIME,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMPTZ,
    acknowledged_by VARCHAR(255),
    metadata JSONB
);
```

## 🚀 Fonctionnement

### Déclenchement Automatique

**Heure** : 16:00 chaque jour (via `task_sync_rv_and_alerts`)

**Processus** :
1. Sync des appointments depuis Gazelle
2. Détection des RV non confirmés pour demain (J+1)
3. Pour chaque RV non confirmé :
   - Identification du technicien par nom
   - Routage vers l'email approprié
   - Envoi d'un email personnalisé
   - Création d'une entrée `dashboard_alerts` (type `URGENCE_CONFIRMATION`)

### Exemple d'Email Envoyé

```
Sujet: ⚠️ RV non confirmé demain chez [Client]

Salut Nicolas,
Ton rendez-vous de demain chez Centre Pierre-Péladeau n'est toujours pas confirmé.

Merci de contacter le client pour confirmer le rendez-vous.
```

### Exemple d'Entrée Dashboard

```json
{
  "type": "URGENCE_CONFIRMATION",
  "severity": "warning",
  "title": "RV non confirmé - Centre Pierre-Péladeau",
  "message": "Rendez-vous de demain chez Centre Pierre-Péladeau non confirmé",
  "technician_name": "Nicolas",
  "client_name": "Centre Pierre-Péladeau",
  "appointment_date": "2026-01-23",
  "appointment_time": "09:00:00"
}
```

## 🔍 Vérification

### Tester l'Identification

```python
from modules.alertes_rv.service import UnconfirmedAlertsService

service = UnconfirmedAlertsService()

# Test avec un technicien
tech_info = {"name": "Nicolas Paradis", "email": "nicolas@pianotekinc.com"}
name, email = service._identify_technician_and_route(tech_info)
print(f"{name} → {email}")  # Nicolas → nicolas@pianotekinc.com
```

### Vérifier les Alertes Dashboard

```sql
-- Voir les alertes non reconnues
SELECT * FROM v_dashboard_alerts_pending
WHERE type = 'URGENCE_CONFIRMATION'
ORDER BY created_at DESC;
```

## 📝 Notes

- **Un email par RV** : Chaque RV non confirmé génère un email séparé (au lieu d'un email groupé)
- **Fallback Nicolas** : Si le technicien n'est pas reconnu, l'alerte est envoyée à Nicolas
- **Dashboard en rouge** : Les alertes `URGENCE_CONFIRMATION` apparaissent en rouge (severity: `warning`)
- **Déduplication** : Les alertes dashboard ne sont pas créées en double (vérification par `appointment_id` + `technician_id`)

## 🔄 Prochaines Étapes

1. ✅ Exécuter le script SQL pour créer `dashboard_alerts`
2. ✅ Vérifier les variables d'environnement (`EMAIL_NICOLAS`, `EMAIL_ALLAN`, `EMAIL_JP`)
3. ⏳ Tester avec un RV non confirmé réel
4. ⏳ Intégrer l'affichage des alertes dans le Dashboard frontend
