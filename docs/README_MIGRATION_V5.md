# 📚 NAVIGATION - MIGRATION V5 ASSISTANT GAZELLE

**Date:** 2025-12-14
**Objectif:** Centraliser tous les documents de migration V4 → V5
**Dossier partagé:** `//tsclient/assistant-gazelle-v5/docs/`

---

## 🗂️ INDEX DES DOCUMENTS (Sur Mac)

### 1️⃣ COMMENCER ICI
📊 **[ÉTAT_MIGRATION_V5.md](ÉTAT_MIGRATION_V5.md)**
- ✅ Ce qui est complété (Module Inventaire)
- 🚧 En cours (Assistant Conversationnel)
- 📅 Timeline globale
- 🔧 Infrastructure (PC Windows vs Mac)
- 🎯 Priorités et prochaines actions

### 2️⃣ QUESTIONS URGENTES
❓ **[QUESTIONS_CURSORMAC_ASSISTANT.md](QUESTIONS_CURSORMAC_ASSISTANT.md)**
- **8 sections de questions critiques**
- Architecture V5 (backend/ vs modules/?)
- Connexion DB (psycopg2 direct)
- État données Gazelle dans Supabase
- OpenAI et Vector Search
- Authentification JWT
- Routes FastAPI
- Déploiement

**🚨 ACTION REQUISE:** Répondre AVANT de commencer l'implémentation

### 3️⃣ GUIDE TECHNIQUE
📘 **[GUIDE_MIGRATION_ASSISTANT_V5.md](GUIDE_MIGRATION_ASSISTANT_V5.md)**
- Architecture V4 complète (7916 lignes)
- Roadmap migration (15 heures)
- 🆕 Nouveautés V5:
  - Briefings adaptatifs (3 niveaux)
  - Raccourcis ".mes rv" → aujourd'hui
- Adaptations SQL Server → PostgreSQL
- Tests définis

### 4️⃣ RÉFÉRENCE API
📙 **[GAZELLE_API_REFERENCE.md](GAZELLE_API_REFERENCE.md)**
- Queries GraphQL Gazelle
- Schéma complet (client, contact, piano, event, timeline)

### 5️⃣ IMPORT CLOUD
📗 **[GUIDE_MIGRATION_IMPORT_GAZELLE_CLOUD.md](../GUIDE_MIGRATION_IMPORT_GAZELLE_CLOUD.md)**
- Migration import (PC Windows → Cloud)
- Scripts GraphQL → PostgreSQL
- Déploiement (Render / Railway / GitHub Actions)

---

## 🚀 DÉMARRAGE RAPIDE POUR CURSOR MAC

### Étape 1: Lire dans cet ordre
1. 📊 [ÉTAT_MIGRATION_V5.md](ÉTAT_MIGRATION_V5.md) - Vue d'ensemble
2. ❓ [QUESTIONS_CURSORMAC_ASSISTANT.md](QUESTIONS_CURSORMAC_ASSISTANT.md) - Questions critiques
3. 📘 [GUIDE_MIGRATION_ASSISTANT_V5.md](GUIDE_MIGRATION_ASSISTANT_V5.md) - Guide technique

### Étape 2: Répondre aux questions
Créer: `REPONSES_CURSORMAC_2025-12-14.md`

Format:
```markdown
# Réponses - Cursor Mac

## Question 1: Architecture Backend V5
**Q1.1 - Structure backend/:**
✅/❌ [Réponse]

**Q1.2 - Pattern:**
[Recommandation + justification]

[etc.]
```

### Étape 3: Vérifier prérequis
```bash
# Test connexion Supabase
cd ~/assistant-gazelle-v5
python scripts/test_supabase_connection.py

# Vérifier tables Gazelle
psql -h db.xxx.supabase.co -U postgres
\dt gazelle.*

# Variables d'environnement
cat .env | grep -E 'SUPABASE|OPENAI'
```

### Étape 4: Commencer implémentation
Suivre [GUIDE_MIGRATION_ASSISTANT_V5.md](GUIDE_MIGRATION_ASSISTANT_V5.md) phase par phase

---

## 📊 STATUT PAR MODULE

| Module | V4 (Windows) | V5 (Mac) | Statut | Priorité |
|--------|--------------|----------|--------|----------|
| **Inventaire** | SQL Server | ✅ Supabase | ✅ COMPLÉTÉ | ✅ |
| **Assistant** | Flask | 🚧 FastAPI | 🚧 PLANIFIÉ | 🔥 URGENT |
| **Import Gazelle** | Windows | 📋 Cloud | 📋 DOCUMENTÉ | ⚠️ IMPORTANT |

---

## 🎯 PROCHAINES ACTIONS

1. **Cursor Mac répond aux questions** ⏰ URGENT
2. **Validation architecture V5** ⏰ URGENT
3. **Implémentation Assistant** 🚧
4. **Tests V4 vs V5** ✅
5. **Déploiement** 🚀

---

## 📞 CONTACT

- **PC Windows:** Claude Code
- **Mac:** Cursor Mac (Claude Code)
- **Validation:** Allan

---

**Créé le:** 2025-12-14
**Par:** Claude Code (Windows)
**Pour:** Cursor Mac + Allan
**Statut:** ✅ PRÊT
