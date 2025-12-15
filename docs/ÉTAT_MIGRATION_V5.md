# 📊 ÉTAT MIGRATION V5 - Piano Technique Montréal
**Date:** 2025-12-14
**Windows (Claude Code) → Mac (Cursor Mac)**

---

## ✅ COMPLÉTÉ

### Module Inventaire ✅ FONCTIONNEL
- ✅ Connexion Supabase (psycopg2 direct)
- ✅ Import SQL Server → Supabase (`inv.produits_catalogue`)
- ✅ Migrations SQL idempotentes
- ✅ Scripts test validés

**Principes validés:**
1. Pas de layer SupabaseStorage → psycopg2 direct
2. Migrations SQL idempotentes
3. Scripts autonomes
4. Même format données V4

---

## 🚧 EN COURS

### Assistant Conversationnel ⏳ PLANIFIÉ

**Fichiers V4 à migrer:**

| Fichier | Lignes | Statut | Destination V5 |
|---------|--------|--------|----------------|
| `conversational_parser.py` | 360 | ✅ Prêt | `modules/assistant/services/parser.py` |
| `conversational_queries.py` | 663 | ⚠️ SQL adapt | `modules/assistant/services/queries.py` |
| `gazelle_vector_index.py` | ~ | ✅ Prêt | `modules/assistant/services/vector_search.py` |
| `unified_assistant.py` | 1265 | ⚠️ Structure | `modules/assistant/services/assistant_service.py` |
| `assistant_gazelle_v4_secure.py` | 5628 | ⚠️ Flask→FastAPI | `routers/assistant.py` |

**Total V4:** 7916 lignes de code mature

**Bloqueurs:**
1. ❓ Architecture V5 (backend/ vs modules/assistant/?)
2. ❓ Données Gazelle dans Supabase?
3. ❓ Vector index .pkl copié sur Mac?
4. ❓ Auth JWT (Supabase Auth vs custom)?

**Prochaines étapes:**
1. ✅ Cursor Mac répond aux questions → [QUESTIONS_CURSORMAC_ASSISTANT.md](QUESTIONS_CURSORMAC_ASSISTANT.md) **COMPLÉTÉ**
2. ⏳ Actions urgentes (psycopg2, SUPABASE_PASSWORD, tables, .pkl)
3. ⏳ Validation architecture
4. ⏳ Implémentation phase par phase
5. ⏳ Tests V4 vs V5
6. ⏳ Déploiement

---

## 📅 TIMELINE

### Semaine 1 ✅ COMPLÉTÉE
- ✅ Module Inventaire migré
- ✅ Documentation complète

### Semaine 2 🚧 EN COURS
- ✅ Guide migration assistant
- ✅ Questions critiques pour Cursor Mac
- ✅ **COMPLÉTÉ:** Réponses Cursor Mac (2025-12-14)
- ⏳ **PROCHAIN:** Actions urgentes (psycopg2, SUPABASE_PASSWORD, tables, .pkl)
- ⏳ **ENSUITE:** Implémentation V5

### Semaines 3-4 📅 PLANIFIÉ
- Import Gazelle Cloud
- Tests parallèles V4/V5
- Validation et déploiement

---

## 🔧 INFRASTRUCTURE

### V4 (Windows) - PRODUCTION
```
C:\Allan Python projets\assistant-gazelle\
├── app/
│   ├── assistant_gazelle_v4_secure.py  (Flask 5000)
│   ├── unified_assistant.py
│   ├── conversational_parser.py
│   ├── conversational_queries.py
│   └── gazelle_vector_index.py
├── data/
│   └── gazelle_vectors.pkl  (126,519 entrées)
└── .env
```

**DB:** SQL Server PIANOTEK\SQLEXPRESS

### V5 (Mac) - DÉVELOPPEMENT
```
~/assistant-gazelle-v5/
├── backend/ (?)  ← À confirmer
│   ├── services/
│   ├── routers/
│   └── database/
├── modules/
│   └── inventaire/  ✅
└── .env
```

**DB:** Supabase PostgreSQL
- ✅ **Données Gazelle synchronisées** (2025-12-14):
  - 1,000 clients (`gazelle_clients`)
  - 921 pianos (`gazelle_pianos`)
  - **Total:** 1,921 enregistrements
  - **Script:** `modules/sync_gazelle/sync_to_supabase.py`

---

## 🎯 PRIORITÉS

### 1. Assistant V5 🔥 URGENT
**Pourquoi:**
- 80% utilisation quotidienne
- Cas critique: ".mes rv" (rendez-vous)
- V4 bloqué sur PC Windows

**Actions:**
1. ⏳ Cursor Mac répond questions
2. ⏳ Validation architecture
3. ⏳ Implémentation

### 2. Import Gazelle Cloud ⚠️ IMPORTANT
- Automatisation quotidienne
- Élimination PC Windows
- Données synchronisées

### 3. Autres modules 📋 MOYEN
- Facturation, Rapports, Analytics

---

## 🚨 RISQUES & MITIGATION

### Risque 1: V5 ≠ V4
**Impact:** Élevé (perturbation)
**Mitigation:**
- ✅ Tests V4 vs V5 en parallèle
- ✅ Cohabitation 1-2 semaines
- ✅ Rollback rapide si problème
- ✅ Copie exacte logique V4

### Risque 2: Données non synchro
**Impact:** Élevé
**Mitigation:**
- ❓ Vérifier état avec Cursor Mac
- ✅ Scripts import documentés
- ✅ Validation quotidienne

### Risque 3: Performance vector search
**Impact:** Moyen
**Mitigation:**
- ✅ Réutiliser .pkl V4
- ✅ Code identique
- ✅ Benchmarks V4 vs V5

---

## 📊 MÉTRIQUES

**Code V4:** 7916 lignes
- assistant_gazelle_v4_secure.py: 5628
- unified_assistant.py: 1265
- conversational_queries.py: 663
- conversational_parser.py: 360

**Données:**
- Vector index: 126,519 entrées
- Produits: ~100 (Supabase ✅)
- Rendez-vous: ~500/mois (à importer)

---

## 📝 PRINCIPES

1. **Conserver ce qui fonctionne** ✅
2. **Migration progressive** ✅
3. **Simplicité technique** ✅
4. **Documentation complète** ✅

---

## 🔗 DOCUMENTS

- [README Navigation](README_MIGRATION_V5.md)
- [Questions Cursor Mac](QUESTIONS_CURSORMAC_ASSISTANT.md)
- [Guide Technique](GUIDE_MIGRATION_ASSISTANT_V5.md)
- [API Gazelle](GAZELLE_API_REFERENCE.md)
- [Import Cloud](../GUIDE_MIGRATION_IMPORT_GAZELLE_CLOUD.md)

---

**Créé:** 2025-12-14
**Par:** Claude Code (Windows)
**Statut:** ✅ PRÊT
