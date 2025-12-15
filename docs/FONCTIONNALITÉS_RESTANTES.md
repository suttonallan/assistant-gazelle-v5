# 📋 FONCTIONNALITÉS RESTANTES À TRANSITIONNER
**Date:** 2025-12-14
**Mis à jour par:** Claude Code (Windows)

---

## ✅ DÉJÀ MIGRÉ VERS V5

### 1. Module Inventaire ✅ COMPLÉTÉ
- ✅ Import produits SQL Server → Supabase
- ✅ Table `inv.produits_catalogue`
- ✅ Scripts test connexion

### 2. Assistant Conversationnel 🚧 EN COURS (Cursor Mac)
- ✅ Questions/réponses complétées
- ✅ Architecture validée
- ✅ Prérequis fournis (SUPABASE_PASSWORD, OPENAI_API_KEY, gazelle_vectors.pkl)
- ⏳ **EN COURS:** Implémentation par Cursor Mac
- **Statut:** Phase 2 - Actions urgentes (psycopg2, tables Gazelle)

---

## 🔄 FONCTIONNALITÉS V4 RESTANTES À MIGRER

D'après le diagnostic global, voici ce qui reste:

### 3. Import Quotidien Gazelle (API → Supabase) 🔥 HAUTE PRIORITÉ

**Actuellement (V4 - Windows):**
- **Emplacement:** `C:\Genosa\Working\update.bat`
- **Exécution:** Tâche planifiée Windows (quotidienne)
- **Scripts:**
  - `Import_daily_update.py` (orchestrateur)
  - `clients.py` (clients/contacts/emails/téléphones/adresses)
  - `pianos.py` (pianos/mesures humidité)
  - `timeline.py` (timeline/événements)
- **Destination:** SQL Server `PianoTek`
- **Période:** 60 jours passé, 90 jours futur

**À migrer vers V5:**
- ✅ Guide déjà créé: [GUIDE_MIGRATION_IMPORT_GAZELLE_CLOUD.md](../GUIDE_MIGRATION_IMPORT_GAZELLE_CLOUD.md)
- **Destination:** Supabase PostgreSQL (schéma `gazelle`)
- **Déploiement cloud:** Render / Railway / GitHub Actions
- **Tâche cron:** Quotidienne à 2h du matin
- **Tables:**
  - `gazelle.clients`
  - `gazelle.contacts`
  - `gazelle.contact_emails`
  - `gazelle.contact_phones`
  - `gazelle.contact_locations`
  - `gazelle.pianos`
  - `gazelle.piano_measurements`
  - `gazelle.timeline_entries`

**Impact:**
- 🔥 **CRITIQUE** - L'assistant V5 a besoin de ces données!
- Cursor Mac a mentionné que tables Gazelle doivent être vérifiées
- Sans import quotidien, données V5 deviennent obsolètes

**Prochaines étapes:**
1. ⏳ Vérifier si tables Gazelle existent dans Supabase (Cursor Mac - en cours)
2. ⏳ Si non, exécuter migrations SQL pour créer schéma `gazelle`
3. ⏳ Adapter scripts d'import (API Gazelle → PostgreSQL)
4. ⏳ Déployer sur cloud (Render/Railway/GitHub Actions)
5. ⏳ Configurer tâche cron quotidienne

---

### 4. Alertes Humidité ⚠️ MOYENNE PRIORITÉ

**Actuellement (V4 - Windows):**
- **Emplacement:** `C:\Allan Python projets\humidity_alerts\humidity_alert_system.py`
- **Exécution:** Appelé par `update.bat` quotidiennement
- **Fonction:**
  - Détecte problèmes humidité (housse, alimentation)
  - Utilise OpenAI pour analyse intelligente
  - Envoie notifications Slack via webhooks
- **Configuration:** `humidity_alerts/config.json`
  - Webhooks Slack: Louise, Nicolas
  - Placeholders: Allan, Jean-Philippe
- **Base de données:** SQL Server `PianoTek`

**À migrer vers V5:**
- **Destination DB:** Supabase PostgreSQL
- **Déploiement:** Cloud (même instance que import Gazelle)
- **Configuration:** Variables d'environnement + Supabase table
- **Webhooks:** À migrer dans .env ou table Supabase

**Impact:**
- ⚠️ Notifications techniciens (Louise, Nicolas)
- Dépend des données `gazelle.piano_measurements`

**Prochaines étapes:**
1. Après import Gazelle fonctionnel
2. Adapter requêtes SQL Server → PostgreSQL
3. Migrer webhooks Slack dans configuration V5
4. Intégrer dans tâche cron quotidienne

---

### 5. Briefings Techniciens 📋 MOYENNE PRIORITÉ

**Actuellement (V4 - Windows):**
- **Emplacement:** `C:\Allan Python projets\Gazelle import v2\`
- **Scripts:**
  - `generate_briefing.py` (génère briefings)
  - `send_briefing_allan.py` (envoie à Allan)
  - `send_briefing_nicolas.py` (envoie à Nicolas)
  - `send_briefing_louise.py` (envoie à Louise)
- **Fonction:**
  - Résumés quotidiens/hebdomadaires pour techniciens
  - Vue `vw_TechnicianBrief` (50+ colonnes)
  - Envoi email via SMTP Gmail
- **Webhooks:** Hardcodés dans chaque script (à migrer)

**À migrer vers V5:**
- ✅ **DÉJÀ INTÉGRÉ** dans assistant conversationnel!
  - Voir [GUIDE_MIGRATION_ASSISTANT_V5.md](GUIDE_MIGRATION_ASSISTANT_V5.md) section "Briefings"
  - 3 niveaux adaptatifs: synthèse, détaillé, complet
  - Mode conversationnel: "Résume ma journée", "Briefing semaine"
- **Alternative:** Service autonome pour envoi email quotidien
  - Tâche cron séparée (ex: 7h du matin)
  - Interroge `vw_TechnicianBrief` dans Supabase
  - Envoie email via SMTP ou service email (SendGrid, Mailgun)

**Impact:**
- 📋 Confort techniciens (résumés automatiques)
- Dépend de l'assistant conversationnel V5

**Prochaines étapes:**
1. Après assistant V5 fonctionnel
2. Décider: conversationnel uniquement OU envoi auto email
3. Si envoi auto: créer service séparé + tâche cron

---

### 6. Rapports Excel 📊 BASSE PRIORITÉ

**Actuellement (V4 - Windows):**
- **Emplacement:** `C:\Genosa\Working\`
- **Scripts:**
  - `generate_report.py` (rapport historique)
  - `generate_report_All.py` (rapport complet)
- **Exécution:** Appelés par `update.bat` quotidiennement
- **Fonction:** Génère rapports Excel pour analyse
- **Base de données:** SQL Server `PianoTek`

**À migrer vers V5:**
- **Option A:** Scripts Python cloud (comme import Gazelle)
- **Option B:** Fonction serverless (AWS Lambda / Vercel)
- **Option C:** Module FastAPI dédié (génération à la demande)

**Impact:**
- 📊 Analyse/reporting (probablement peu utilisé)
- Peut attendre après fonctionnalités critiques

**Prochaines étapes:**
1. Clarifier avec Allan: utilisation actuelle?
2. Si important: migrer après assistant V5
3. Si peu utilisé: déprioritiser

---

### 7. Serveur OAuth Gazelle 🔐 BASSE PRIORITÉ

**Actuellement (V4 - Windows):**
- **Emplacement:** `C:\Genosa\Working\serverapi.py`
- **Fonction:**
  - Serveur Flask OAuth2 pour Gazelle API
  - Dashboard web
  - Gestion tokens
- **Statut:** Production active

**À migrer vers V5:**
- **Question:** Toujours nécessaire?
- Gazelle API utilise déjà OAuth2 directement
- Scripts V5 peuvent utiliser tokens sans serveur intermédiaire

**Impact:**
- 🔐 Gestion tokens (probablement optionnel)

**Prochaines étapes:**
1. Clarifier avec Allan: usage actuel?
2. Si nécessaire: migrer après fonctionnalités critiques
3. Si optionnel: supprimer

---

## 📊 RÉCAPITULATIF PAR PRIORITÉ

### 🔥 HAUTE PRIORITÉ (Bloquants pour V5)

| Fonctionnalité | Statut | Bloqueur pour | ETA |
|----------------|--------|---------------|-----|
| **Assistant Conversationnel** | 🚧 EN COURS | Tous | Cette semaine |
| **Import Gazelle Cloud** | 📋 DOCUMENTÉ | Assistant, Alertes | 1-2 semaines |

### ⚠️ MOYENNE PRIORITÉ (Important mais non bloquant)

| Fonctionnalité | Statut | Dépend de | ETA |
|----------------|--------|-----------|-----|
| **Alertes Humidité** | ⏳ À FAIRE | Import Gazelle | 2-3 semaines |
| **Briefings Techniciens** | ✅ INTÉGRÉ* | Assistant V5 | Avec assistant |

*Intégré dans assistant conversationnel, ou service séparé à décider

### 📋 BASSE PRIORITÉ (Peut attendre)

| Fonctionnalité | Statut | Dépend de | ETA |
|----------------|--------|-----------|-----|
| **Rapports Excel** | ⏳ À FAIRE | Import Gazelle | TBD |
| **Serveur OAuth** | ⏳ À CLARIFIER | - | TBD |

---

## 🎯 ROADMAP RECOMMANDÉE

### Phase 1 (Cette semaine - 2025-12-14 à 2025-12-20) 🚧
1. ✅ Assistant Conversationnel V5 - Cursor Mac
2. ⏳ Vérification tables Gazelle dans Supabase
3. ⏳ Tests parallèles V4/V5

### Phase 2 (Semaines 3-4 - 2025-12-21 à 2026-01-03) 📋
1. Import Gazelle Cloud (Render/Railway/GH Actions)
2. Création schéma `gazelle` si nécessaire
3. Tâche cron quotidienne
4. Validation données synchronisées

### Phase 3 (Janvier 2026) ⚠️
1. Alertes Humidité V5
2. Briefings Techniciens (décision: conversationnel vs auto email)
3. Tests intégration complète

### Phase 4 (Février 2026) 📊
1. Rapports Excel (si nécessaire)
2. Nettoyage code V4
3. Documentation finale
4. **Arrêt PC Windows définitif** 🎉

---

## 💡 OBSERVATIONS IMPORTANTES

### 1. Dépendances critiques:
```
Import Gazelle Cloud
    ↓
Tables gazelle.* dans Supabase
    ↓
Assistant V5 (données)
    ↓
Alertes Humidité V5
    ↓
Briefings Techniciens V5
```

### 2. PC Windows peut être éteint APRÈS:
- ✅ Assistant V5 validé et en production
- ✅ Import Gazelle Cloud fonctionnel (quotidien automatique)
- ✅ Alertes Humidité V5 fonctionnelles
- ⚠️ Rapports Excel migrés OU confirmés non nécessaires

### 3. Cohabitation V4/V5:
- **1-2 semaines** minimum pour assistant
- **2-4 semaines** recommandé pour tout l'écosystème
- Rollback possible à tout moment

---

## 📞 QUESTIONS POUR ALLAN

### À clarifier:

1. **Rapports Excel** (`generate_report.py`, `generate_report_All.py`):
   - Utilisés actuellement? À quelle fréquence?
   - Priorité migration?

2. **Serveur OAuth** (`serverapi.py`):
   - Toujours nécessaire?
   - Peut-on utiliser tokens Gazelle directement?

3. **Briefings Techniciens**:
   - Préférence: conversationnel uniquement OU envoi email auto quotidien?
   - Horaire envoi si auto: 7h du matin?

4. **Webhooks Slack**:
   - Confirmer webhooks Louise + Nicolas actifs?
   - Configurer webhooks Allan + Jean-Philippe?

---

**Créé:** 2025-12-14
**Par:** Claude Code (Windows)
**Statut:** ✅ COMPLET - Attend clarifications Allan
