# 🌐 Gestion du Temps et Fuseaux Horaires
- **Référence Locale :** L'heure de travail est toujours `America/Montreal` (EST/EDT) [1].
- **Conformité API Gazelle :** Gazelle envoie les dates en format ISO UTC (ex: 2027-01-25T10:00:00Z) [3].
- **Règle de Comparaison :** Toujours convertir les dates UTC de l'API en `America/Montreal` avant de calculer les alertes.
- **Calcul des 24h :** Une alerte est déclenchée si `Date_RDV - Heure_Actuelle < 24h` (heure locale).

## 🧩 Conformité et Robustesse de l'API
- **Import Unique :** Le module `requests` doit être importé uniquement au niveau global pour éviter le "shadowing".
- **Mode Incrémental :** Prioriser la synchronisation des données futures (2025+) et récentes. Ne jamais lancer de full backfill historique sans instruction explicite [4].
- **Single Sender :** L'envoi d'email doit strictement utiliser `asutton@piano-tek.com` (SendGrid).

## 🏗️ Structure des Données (Spécifique V5)
- **Types Critiques :** Pour l'historique d'entretien, inclure impérativement le type `SERVICE` (en plus de `NOTE` et `APPOINTMENT`) car il contient les relevés d'humidité [8][9].
- **Zéro Devinage :** Ne jamais tenter d'extraire le modèle du piano depuis le texte des notes. Utiliser exclusivement `piano_id`, `instrument_id` ou le `Client Token` pour faire les jointures SQL [7].
- **Stockage Hybride :** Les données fixes (Marque, Série) viennent de la table `gazelle_pianos`. Les données variables (Humidité, Température) viennent de la `Timeline` (CSV/API) [10].

---

# 🚀 ARCHITECTURE V6 - PROMPT ALPHA

> **Important:** La v6 est une refonte structurelle, pas une mise à jour de la v5. Ignorer les "mauvaises habitudes" de la v5 (notifications sans traçabilité, patches accumulés).

## 1. Carte d'Identité du Projet

**Instruction:** "Tu travailles exclusivement dans le dossier v6. Ta mission est d'implémenter l'architecture 'Proactive' décrite dans ce Prompt Alpha."

### Entités Fondamentales

| Entité | Description | Comportement |
|--------|-------------|--------------|
| **Clients Individuels** | RV ponctuels | Standard |
| **Institutions** (ex: Vincent-D'Indy) | Entités structurelles avec sous-ressources (Pianos/Salles) | Constante, pas un simple champ texte |
| **Admin** (Allan) | Seul maître du Dashboard | Gère techniciens, emails, logs |
| **Techniciens** (ex: JP) | Utilisateurs passifs-actifs | Consultent assistant, reçoivent emails |

## 2. État de la Base de Données (Supabase)

**Instruction:** "Analyse le schéma actuel de Supabase. Ajoute les colonnes de mémoire et crée la table notification_logs pour l'historique."

### Colonnes de Mémoire (sur `gazelle_appointments`)

```sql
last_notified_tech_id   VARCHAR  -- Dernier technicien notifié
last_notified_time      TIME     -- Dernière heure notifiée
last_notified_at        TIMESTAMP -- Quand la notification a été envoyée
```

### Table de Traçabilité

```sql
CREATE TABLE notification_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    appointment_external_id VARCHAR NOT NULL,
    technician_id VARCHAR NOT NULL,
    technician_email VARCHAR,
    notification_type VARCHAR, -- 'new_assignment', 'time_change', 'reminder'
    email_subject VARCHAR,
    email_body TEXT,
    sent_at TIMESTAMP DEFAULT NOW(),
    status VARCHAR DEFAULT 'sent', -- 'sent', 'failed', 'pending'
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## 3. Hiérarchie des Priorités (Le "Allan Way")

**Instruction:** "Priorise la lisibilité du Dashboard Admin. Chaque email doit être loggé. Pour Vincent-D'Indy, extrais et affiche systématiquement le numéro de salle et de piano."

### Règles Métier

1. **Dashboard Admin:** Contrôle total sur les logs, visibilité des erreurs (alerte rouge si échec)
2. **Technicien:** Info épurée, email ultra-simple
3. **Vincent-D'Indy:** Prioriser affichage Salle + Numéro Piano dans l'assistant

## 4. Règle d'Or - Sync & Notify (Atomique)

**Instruction:** "Implémenter ce flux de manière atomique (tout ou rien)."

```
Entrée: Sync horaire Gazelle → gazelle_appointments

Condition Critique:
  IF (current_tech != last_notified_tech)
  OR (current_time != last_notified_time)
  AND appointment_date <= tomorrow

Actions Obligatoires (dans l'ordre):
  1. send_simple_email(tech)
     → Sujet: "Nouveau RV"
     → Corps: "Tu as un nouveau RV à [Heure]. Consulte ton assistant."

  2. log_notification()
     → INSERT INTO notification_logs

  3. update_notified_state()
     → UPDATE gazelle_appointments SET last_notified_*
```

## 5. Gestion Vincent-D'Indy

**Instruction:** "Pour l'institution Vincent-D'Indy, l'assistant du technicien doit prioriser l'affichage de la Salle et du Numéro de Piano. Ces données sont des constantes liées à l'institution et doivent être extraites de la source Gazelle lors de la sync."

---

# 🔧 V5 - MODE MAINTENANCE

> La v5 reste en maintenance pour bugs critiques uniquement. Exception: implémenter `notification_logs` pour que la v6 hérite des données de test.
