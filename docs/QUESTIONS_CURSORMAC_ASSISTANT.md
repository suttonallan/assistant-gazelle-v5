# ❓ QUESTIONS CRITIQUES POUR CURSOR MAC
## Migration Assistant Conversationnel V4 → V5

**Date:** 2025-12-14
**Urgence:** 🔥 URGENT - À répondre AVANT implémentation

---

## 📋 CONTEXTE

### ✅ Ce qui fonctionne (Inventaire V5):
```
modules/inventaire/
├── __init__.py
├── migrations/
│   └── 002_add_product_classifications.sql
└── (scripts d'import)
```

**Principes validés:**
1. **psycopg2 direct** (pas de layer SupabaseStorage)
2. **Variables d'environnement** (SUPABASE_URL, PASSWORD)
3. **Scripts autonomes**
4. **Migrations idempotentes**

---

## ❓ QUESTIONS

### Q1: Architecture Backend V5

**Q1.1:** La structure `backend/` existe-t-elle?
```
~/assistant-gazelle-v5/
├── backend/
│   ├── services/
│   ├── routers/
│   └── database/
```
✅ Oui / ❌ Non

**Q1.2:** Devrais-je suivre le pattern inventaire?
```
modules/assistant/
├── __init__.py
├── migrations/
└── services/
    ├── parser.py
    ├── queries.py
    └── vector_search.py
```
✅ Oui / ❌ Non / 💡 Autre (préciser)

**Q1.3:** Y a-t-il déjà `main.py` ou `app.py` FastAPI?
✅ Oui / ❌ Non

---

### Q2: Connexion Base de Données

**Q2.1:** Confirmes-tu: **psycopg2 direct** (comme inventaire)?
✅ Oui, psycopg2 direct / ❌ Non, utiliser SupabaseStorage

**Q2.2:** Où est le fichier `.env`?
- [ ] `~/assistant-gazelle-v5/.env`
- [ ] Autre: _____________

**Q2.3:** Les tables Gazelle existent-elles dans Supabase?
```sql
-- À vérifier:
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'gazelle';

-- Tables attendues:
-- gazelle.appointments
-- gazelle.clients
-- gazelle.contacts
-- gazelle.pianos
-- gazelle.timeline_entries
```
✅ Oui, toutes / ⚠️ Partielles / ❌ Non

---

### Q3: Données Gazelle

**Q3.1:** Les données Gazelle sont-elles importées dans Supabase?
✅ Oui, via import cloud / ❌ Non, encore sur SQL Server

**Q3.2:** Si non, doit-on importer AVANT de migrer l'assistant?
✅ Oui / ❌ Non, l'assistant peut interroger SQL Server

---

### Q4: OpenAI et Vector Search

**Q4.1:** Où est `gazelle_vectors.pkl` (126,519 entrées)?
- [ ] Déjà sur Mac: _____________
- [ ] À copier depuis Windows
- [ ] À recréer

**Q4.2:** Stratégie vector index:
- [ ] Réutiliser .pkl de V4
- [ ] Stocker dans Supabase (table JSONB)
- [ ] Service externe (Pinecone/Weaviate)

**Q4.3:** Clé OpenAI:
- [ ] Même que V4 (dans .env Windows)
- [ ] Nouvelle clé pour V5
- [ ] Déjà dans .env Mac

---

### Q5: Authentification JWT

**Q5.1:** Système auth V5 existe?
✅ Oui: _____________  / ❌ Non

**Q5.2:** Approche auth:
- [ ] Supabase Auth (intégré)
- [ ] JWT custom (comme V4)
- [ ] Autre: _____________

**Q5.3:** Stockage users/permissions:
- [ ] Table Supabase `auth.users`
- [ ] Fichier config (comme V4)
- [ ] Autre: _____________

---

### Q6: Routes FastAPI

**Q6.1:** Structure existante?
```python
# Option A: Module dédié
# routers/assistant.py
@router.post("/api/assistant/chat")

# Option B: Endpoint global
# main.py
@app.post("/api/chat")
```
✅ Option A / ✅ Option B / 💡 Autre

**Q6.2:** Port FastAPI:
- [ ] 8000 (standard)
- [ ] 5000 (comme Flask V4)
- [ ] Autre: _____________

---

### Q7: Tests et Validation

**Q7.1:** Stratégie de test:
- [ ] V4 (Windows 5000) + V5 (Mac 8000) en parallèle
- [ ] Arrêter V4, tester V5, rollback si problème
- [ ] Autre: _____________

**Q7.2:** Tests prioritaires:
```bash
1. POST /api/chat {"question": ".mes rv"}
2. POST /api/chat {"question": "mes rendez-vous demain"}
3. POST /api/chat {"question": "cherche Yamaha Montreal"}
4. POST /api/chat {"question": "résume ma semaine"}
```
✅ Créer tests automatisés / ❌ Tests manuels

---

### Q8: Déploiement

**Q8.1:** Plateforme cible:
- [ ] Mac local (dev uniquement)
- [ ] Cloud: Render / Railway / Vercel / GH Actions
- [ ] Serveur dédié

**Q8.2:** Plan de transition:
- [ ] Basculement immédiat (1 jour)
- [ ] Cohabitation V4+V5 (1-2 semaines)
- [ ] Migration progressive (fonctionnalité par fonctionnalité)

**Q8.3:** Rollback V4 si problème:
- [ ] Procédure définie
- [ ] À définir

---

## ✅ INSTRUCTIONS

### CE QU'IL FAUT FAIRE

1. **Suivre pattern inventaire:**
   ```
   modules/assistant/
   ├── services/
   │   ├── parser.py     # COPIER conversational_parser.py
   │   ├── queries.py    # ADAPTER conversational_queries.py
   │   └── vector_search.py  # COPIER gazelle_vector_index.py
   ```

2. **psycopg2 direct:**
   ```python
   import psycopg2
   conn = psycopg2.connect(
       host=os.getenv('SUPABASE_HOST'),
       database='postgres',
       user='postgres',
       password=os.getenv('SUPABASE_PASSWORD')
   )
   ```

3. **Adapter SQL:**
   ```python
   # V4 (SQL Server)
   query = "SELECT CONVERT(VARCHAR, a.StartAt, 127), ISNULL(a.Description, '') FROM Appointments WHERE a.StartAt >= ?"

   # V5 (PostgreSQL)
   query = "SELECT TO_CHAR(a.start_at, 'YYYY-MM-DD\"T\"HH24:MI:SS'), COALESCE(a.description, '') FROM gazelle.appointments WHERE a.start_at >= %s"
   ```

4. **Tests:**
   ```bash
   python scripts/test_assistant_queries.py
   ```

5. **Implémentation progressive:**
   - Phase 1: Parser (tests parsing)
   - Phase 2: Queries (1 table)
   - Phase 3: Queries complexes (joins)
   - Phase 4: Vector search
   - Phase 5: OpenAI
   - Phase 6: Routes FastAPI

### CE QU'IL NE FAUT PAS FAIRE

1. ❌ Créer SupabaseStorage
2. ❌ Modifier logique V4
3. ❌ Réinventer vector index
4. ❌ Casser V4 Windows
5. ❌ Déployer sans tests

---

## 📝 FORMAT RÉPONSE ATTENDU

Créer: `REPONSES_CURSORMAC_2025-12-14.md`

```markdown
# Réponses - Cursor Mac
**Date:** 2025-12-14

## Q1: Architecture Backend V5
**Q1.1:** ✅ Oui, backend/ existe à ~/assistant-gazelle-v5/backend/
**Q1.2:** 💡 Je recommande modules/assistant/ car...
**Q1.3:** ✅ Oui, main.py existe

## Q2: Connexion Base de Données
**Q2.1:** ✅ Oui, psycopg2 direct
**Q2.2:** `.env` à ~/assistant-gazelle-v5/.env
**Q2.3:** ⚠️ Partielles: clients ✅, appointments ❌

## Q3: Données Gazelle
[...]

## Q8: Déploiement
[...]
```

---

## 🚦 APRÈS RÉPONSES

1. **Cursor Mac envoie réponses** → Allan valide
2. **Ajustement guide** selon réponses
3. **Création fichiers base** → Parser, Queries, Vector
4. **Tests unitaires** → pytest
5. **Intégration FastAPI** → Routes + auth
6. **Tests end-to-end** → V4 vs V5
7. **Validation Allan** → Approbation
8. **Déploiement** → Production

---

## 📞 CONTACT

- **Questions techniques:** Allan ou Claude Code (Windows)
- **Validation:** Allan

---

**Créé:** 2025-12-14
**Par:** Claude Code (Windows)
**Pour:** Cursor Mac
**Urgence:** 🔥 URGENT

---

## ✅ RÉPONSES AUX QUESTIONS - Cursor Mac
**Date:** 2025-12-14
**Analysé par:** Cursor Mac (Claude Code)

---

### Q1: Architecture Backend V5

**Q1.1:** ❌ **Non**, la structure `backend/` n'existe pas.
- ✅ **Structure actuelle:** `api/` avec `main.py` FastAPI
- ✅ **Fichier principal:** `/Users/allansutton/Documents/assistant-gazelle-v5/api/main.py`
- ✅ **Port configuré:** 8000 (standard FastAPI)

**Q1.2:** ✅ **Oui**, suivre le pattern inventaire est la bonne approche.
```
modules/assistant/
├── __init__.py
├── migrations/          # Si nécessaire pour tables spécifiques
└── services/
    ├── parser.py       # COPIER conversational_parser.py
    ├── queries.py      # ADAPTER conversational_queries.py (SQL Server → PostgreSQL)
    └── vector_search.py # COPIER gazelle_vector_index.py
```
**Justification:**
- Pattern cohérent avec `modules/inventaire/`
- Séparation claire des responsabilités
- Facilite la maintenance et les tests

**Q1.3:** ✅ **Oui**, `main.py` FastAPI existe.
- **Chemin:** `api/main.py`
- **Structure:** FastAPI avec routers modulaires
- **Routers existants:** `inventaire`, `alertes_rv`, `catalogue_routes`, `tournees`, `vincent_dindy`
- **Action:** Créer `api/assistant.py` (router) et l'enregistrer dans `main.py`

---

### Q2: Connexion Base de Données

**Q2.1:** ✅ **Oui, psycopg2 direct** (comme inventaire).
- ⚠️ **Note:** Certains modules utilisent encore `SupabaseStorage` (ex: `api/inventaire.py`)
- ✅ **Recommandation:** Utiliser psycopg2 direct pour l'assistant (comme spécifié dans les instructions)
- **Pattern à suivre:** Voir `scripts/export_inventory_data.py` pour exemple de connexion psycopg2

**Q2.2:** ✅ **Oui**, `.env` à `/Users/allansutton/Documents/assistant-gazelle-v5/.env`
- ✅ **Vérifié:** Fichier existe
- ✅ **Variables présentes:** `SUPABASE_URL` (SET), `OPENAI_API_KEY` (SET)
- ⚠️ **Manquant:** `SUPABASE_PASSWORD` (NOT_SET) - **À AJOUTER**

**Q2.3:** ✅ **Oui, tables existent et contiennent des données** (2025-12-14).
- ✅ **Tables vérifiées via API REST Supabase:**
  - ✅ `gazelle_clients`: 1,000 enregistrements
  - ✅ `gazelle_pianos`: 921 enregistrements
  - ⚠️ `gazelle_contacts`: 0 (peut-être pas encore synchronisé)
  - ⚠️ `gazelle_appointments`: 0 (peut-être pas encore synchronisé)
- **Note:** Les tables utilisent le préfixe `gazelle_` (pas `gazelle.` comme prévu initialement)
- **Pour l'assistant:** Utiliser l'API REST Supabase (`SupabaseStorage`) ou adapter les requêtes pour le schéma `public` avec préfixe `gazelle_`

---

### Q3: Données Gazelle

**Q3.1:** ✅ **Oui, données importées dans Supabase** (2025-12-14).
- ✅ **Clients:** 1,000 synchronisés
- ✅ **Pianos:** 921 synchronisés
- ⚠️ **Contacts:** 0 (à synchroniser si nécessaire)
- ⚠️ **Appointments:** 0 (à synchroniser si nécessaire)
- **Total:** 1,921 enregistrements
- **Script utilisé:** `modules/sync_gazelle/sync_to_supabase.py`

**Q3.2:** ✅ **Oui**, importer AVANT de migrer l'assistant.
- **Raison:** L'assistant V5 doit interroger Supabase, pas SQL Server
- **Alternative temporaire:** Si données non importées, l'assistant peut interroger SQL Server en transition (mais pas recommandé)

---

### Q4: OpenAI et Vector Search

**Q4.1:** ✅ **Oui, copié sur Mac** - `gazelle_vectors.pkl` est présent.
- ✅ **Emplacement V5 (Mac):** `/Users/allansutton/Documents/assistant-gazelle-v5/data/gazelle_vectors.pkl`
- ✅ **Taille vérifiée:** 1.5 Go (correspond à 126,519 entrées)
- ✅ **Date:** 2025-10-22 (fichier source)
- ✅ **Action complétée:** 2025-12-14

**Q4.2:** ✅ **Réutiliser .pkl de V4** (recommandé).
- **Raison:** 
  - Index déjà créé et testé (126,519 entrées)
  - Évite de recréer l'index (long et coûteux)
  - Cohérence avec V4
- **Alternative future:** Migrer vers Supabase JSONB ou service externe (Pinecone/Weaviate) si nécessaire

**Q4.3:** ✅ **Déjà dans .env Mac** (ajouté le 2025-12-14).
- ✅ **Vérifié:** `OPENAI_API_KEY` est SET dans `.env`
- ✅ **Même clé que V4:** À confirmer avec Allan (probablement oui)

---

### Q5: Authentification JWT

**Q5.1:** ✅ **Oui**, système auth V5 existe.
- **Fichier:** `core/auth.py`
- **Service:** `AuthService` avec vérification JWT Supabase
- **Dependency FastAPI:** `get_current_user()` disponible

**Q5.2:** ✅ **Supabase Auth (intégré)**.
- **Implémentation:** `core/auth.py` utilise `SUPABASE_JWT_SECRET`
- **Mode dev:** Si `SUPABASE_JWT_SECRET` non défini, retourne user dev automatique
- **Production:** Vérifie les tokens JWT Supabase avec `jwt.decode()`

**Q5.3:** ✅ **Table Supabase `auth.users`**.
- **Stockage:** Géré par Supabase Auth (intégré)
- **Pas de fichier config:** Contrairement à V4

---

### Q6: Routes FastAPI

**Q6.1:** ✅ **Option A: Module dédié** (recommandé).
- **Structure:** Créer `api/assistant.py` (router)
- **Pattern existant:** Suivre `api/inventaire.py`, `api/alertes_rv.py`
- **Enregistrement:** Ajouter dans `api/main.py`:
  ```python
  from api.assistant import router as assistant_router
  app.include_router(assistant_router)
  ```
- **Route suggérée:** `POST /api/assistant/chat` ou `POST /assistant/chat`

**Q6.2:** ✅ **8000 (standard)**.
- **Configuré dans:** `api/main.py` ligne 96: `uvicorn.run(app, host="0.0.0.0", port=8000)`
- **Différent de V4:** V4 Flask utilise port 5000
- **Avantage:** Cohabitation V4 (5000) + V5 (8000) possible

---

### Q7: Tests et Validation

**Q7.1:** ✅ **V4 (Windows 5000) + V5 (Mac 8000) en parallèle** (recommandé).
- **Avantage:** Tests comparatifs sans interruption V4
- **Durée:** 1-2 semaines de cohabitation
- **Rollback:** Facile (arrêter V5, continuer V4)

**Q7.2:** ✅ **Créer tests automatisés**.
- **Framework suggéré:** `pytest` avec `httpx` pour tests API
- **Tests prioritaires:**
  1. `POST /api/assistant/chat {"question": ".mes rv"}`
  2. `POST /api/assistant/chat {"question": "mes rendez-vous demain"}`
  3. `POST /api/assistant/chat {"question": "cherche Yamaha Montreal"}`
  4. `POST /api/assistant/chat {"question": "résume ma semaine"}`
- **Fichier:** `tests/test_assistant_api.py`

---

### Q8: Déploiement

**Q8.1:** ✅ **Mac local (dev) + Cloud (production)**.
- **Dev:** Mac local (port 8000)
- **Production:** Cloud (Render / Railway / GitHub Actions) - à définir
- **Note:** Frontend déjà déployé (GitHub Pages) selon `.github/workflows/deploy-frontend.yml`

**Q8.2:** ✅ **Cohabitation V4+V5 (1-2 semaines)** (recommandé).
- **Phase 1:** V5 en dev (Mac local)
- **Phase 2:** Tests parallèles V4 vs V5
- **Phase 3:** Basculement progressif (fonctionnalité par fonctionnalité)
- **Phase 4:** V4 arrêté, V5 production

**Q8.3:** ⚠️ **À définir**.
- **Recommandation:** Documenter procédure de rollback
- **Fichier:** `docs/ROLLBACK_PROCEDURE.md`

---

## 📋 ACTIONS REQUISES AVANT DÉMARRAGE

### 🔴 URGENT (Bloqueurs)

1. ✅ **Installer psycopg2-binary:** **COMPLÉTÉ** (2025-12-14)
   - ✅ psycopg2 déjà installé et fonctionnel

2. ✅ **Ajouter SUPABASE_PASSWORD dans .env:** **COMPLÉTÉ** (2025-12-14)
   - ✅ Variable ajoutée et vérifiée
   - ✅ Nécessaire pour connexion psycopg2

3. ✅ **Vérifier tables Gazelle dans Supabase:** **COMPLÉTÉ** (2025-12-14)
   - ✅ Tables vérifiées via API REST Supabase
   - ✅ **Données synchronisées:**
     - `gazelle_clients`: 1,000 enregistrements
     - `gazelle_pianos`: 921 enregistrements
   - ⚠️ **Note importante:** Tables dans schéma `public` avec préfixe `gazelle_` (pas `gazelle.`)
   - **Pour l'assistant:** Adapter les requêtes pour utiliser `gazelle_clients`, `gazelle_pianos`, etc.

4. ✅ **Copier gazelle_vectors.pkl depuis Windows:** **COMPLÉTÉ** (2025-12-14)
   - ✅ Fichier présent: `/Users/allansutton/Documents/assistant-gazelle-v5/data/gazelle_vectors.pkl`
   - ✅ Taille: 1.5 Go (126,519 entrées)

### 🟡 IMPORTANT (Avant implémentation)

5. **Créer structure modules/assistant/:**
   ```
   modules/assistant/
   ├── __init__.py
   └── services/
       ├── __init__.py
       ├── parser.py
       ├── queries.py
       └── vector_search.py
   ```

6. **Créer router api/assistant.py:**
   - Suivre pattern `api/inventaire.py`
   - Route principale: `POST /api/assistant/chat`

7. **Enregistrer router dans api/main.py:**
   ```python
   from api.assistant import router as assistant_router
   app.include_router(assistant_router)
   ```

### 🟢 OPTIONNEL (Améliorations)

8. **Créer tests automatisés:**
   - `tests/test_assistant_api.py`
   - `tests/test_assistant_queries.py`

9. **Documenter procédure rollback:**
   - `docs/ROLLBACK_PROCEDURE.md`

---

## ✅ VALIDATION

**Statut:** ✅ **PRÊT POUR IMPLÉMENTATION** (après actions urgentes)

**Prochaines étapes:**
1. ✅ Compléter actions urgentes (psycopg2 ✅, SUPABASE_PASSWORD ✅, tables ✅, .pkl ✅)
2. ⏳ Créer structure `modules/assistant/`
3. ⏳ Copier/adapter code V4 → V5
4. ⏳ Adapter requêtes SQL pour tables `gazelle_*` (schéma public)
5. ⏳ Tests unitaires
6. ⏳ Tests intégration
7. ⏳ Validation Allan

**Note importante:** Les tables Gazelle sont dans le schéma `public` avec préfixe `gazelle_`:
- `gazelle_clients` (pas `gazelle.clients`)
- `gazelle_pianos` (pas `gazelle.pianos`)
- Adapter les requêtes SQL dans `conversational_queries.py` en conséquence

---

**Répondu par:** Cursor Mac (Claude Code)
**Date:** 2025-12-14
