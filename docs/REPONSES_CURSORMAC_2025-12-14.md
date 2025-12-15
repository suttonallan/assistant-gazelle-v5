# Réponses - Cursor Mac
**Date:** 2025-12-14
**Par:** Cursor Mac Assistant
**Pour:** Migration Assistant Conversationnel V4 → V5

---

## Q1: Architecture Backend V5

**Q1.1:** La structure `backend/` existe-t-elle?
❌ **Non**, il n'y a pas de dossier `backend/` à la racine. La structure actuelle utilise:
- `api/` pour les routes FastAPI (main.py, inventaire.py, vincent_dindy.py, etc.)
- `modules/` pour les modules fonctionnels (inventaire, vincent-dindy, humidity-alerts, etc.)
- `core/` pour les utilitaires partagés (auth.py, db_utils.py, supabase_storage.py, etc.)

**Q1.2:** Devrais-je suivre le pattern inventaire?
✅ **Oui**, suivre le pattern `modules/inventaire/`:
```
modules/assistant/
├── __init__.py
├── migrations/
│   └── 001_create_assistant_tables.sql (si nécessaire)
└── services/
    ├── parser.py     # COPIER conversational_parser.py
    ├── queries.py    # ADAPTER conversational_queries.py
    └── vector_search.py  # COPIER gazelle_vector_index.py
```

**Q1.3:** Y a-t-il déjà `main.py` ou `app.py` FastAPI?
✅ **Oui**, `api/main.py` existe et est déjà configuré:
- FastAPI app initialisé
- Port 8000 (ligne 96: `uvicorn.run(app, host="0.0.0.0", port=8000)`)
- Routes modulaires via `APIRouter`
- CORS configuré
- Routes existantes: vincent-dindy, alertes-rv, inventaire, catalogue, tournees

---

## Q2: Connexion Base de Données

**Q2.1:** Confirmes-tu: **psycopg2 direct** (comme inventaire)?
✅ **Oui, psycopg2 direct**. Confirmé par:
- `scripts/check_gazelle_tables.py` utilise psycopg2 direct
- `requirements.txt` inclut `psycopg2-binary>=2.9.9`
- Pattern validé dans le module inventaire (selon README)
- Exemple de connexion dans `scripts/check_gazelle_tables.py` (lignes 24-53)

**Q2.2:** Où est le fichier `.env`?
✅ `.env` à `~/assistant-gazelle-v5/.env` (racine du projet)
- Chargé dans `api/main.py` (lignes 12-14)
- Variables attendues: `SUPABASE_URL`, `SUPABASE_PASSWORD`, `SUPABASE_DATABASE`, `SUPABASE_USER`, `SUPABASE_PORT`
- Note: `.env` est dans `.gitignore` (ne pas commiter)

**Q2.3:** Les tables Gazelle existent-elles dans Supabase?
⚠️ **À vérifier avec le script**. Le script `scripts/check_gazelle_tables.py` existe pour vérifier:
- Tables attendues: `gazelle.appointments`, `gazelle.clients`, `gazelle.contacts`, `gazelle.pianos`, `gazelle.timeline_entries`
- Le script vérifie l'existence du schéma `gazelle` et de chaque table
- **Action requise:** Exécuter `python scripts/check_gazelle_tables.py` pour confirmer l'état

---

## Q3: Données Gazelle

**Q3.1:** Les données Gazelle sont-elles importées dans Supabase?
❓ **À vérifier**. Le script `scripts/check_gazelle_tables.py` compte les lignes dans chaque table, mais:
- Il n'y a pas de script d'import visible dans le repo actuel
- Des guides existent: `GUIDE_MIGRATION_IMPORT_GAZELLE_CLOUD.md`
- **Action requise:** Vérifier avec `scripts/check_gazelle_tables.py` si les tables contiennent des données

**Q3.2:** Si non, doit-on importer AVANT de migrer l'assistant?
✅ **Oui**, l'assistant a besoin des données pour fonctionner. Si les tables sont vides:
- Suivre `GUIDE_MIGRATION_IMPORT_GAZELLE_CLOUD.md`
- Importer les données depuis SQL Server V4 vers Supabase
- L'assistant ne peut pas interroger SQL Server directement (architecture V5 = Supabase uniquement)

---

## Q4: OpenAI et Vector Search

**Q4.1:** Où est `gazelle_vectors.pkl` (126,519 entrées)?
❓ **À localiser**. Le fichier n'est pas dans le repo (probablement dans `.gitignore`):
- [ ] Déjà sur Mac: **À vérifier** (chercher dans le projet ou demander à Allan)
- [ ] À copier depuis Windows: **Probable** (fichier V4)
- [ ] À recréer: **Option de secours** si le fichier est perdu

**Q4.2:** Stratégie vector index:
💡 **Recommandation:** Réutiliser .pkl de V4 initialement, puis migrer vers Supabase (table JSONB) pour:
- Performance (pas de chargement de 126K entrées en mémoire)
- Scalabilité (Supabase peut gérer des millions de vecteurs)
- Cohérence avec l'architecture V5 (tout dans Supabase)
- Option future: Service externe (Pinecone/Weaviate) si besoin de recherche sémantique avancée

**Q4.3:** Clé OpenAI:
❓ **À vérifier dans .env**. Variables attendues:
- `OPENAI_API_KEY` (standard)
- Vérifier si déjà présente: `grep OPENAI .env` ou `cat .env | grep OPENAI`
- Si absente, utiliser la même clé que V4 (dans .env Windows) ou créer une nouvelle clé

---

## Q5: Authentification JWT

**Q5.1:** Système auth V5 existe?
✅ **Oui**, `core/auth.py` existe et implémente:
- `AuthService` avec vérification JWT Supabase
- `get_current_user()` dependency pour FastAPI
- Support mode dev (sans auth si `SUPABASE_JWT_SECRET` non configuré)
- Utilise `SUPABASE_JWT_SECRET` depuis .env

**Q5.2:** Approche auth:
✅ **Supabase Auth (intégré)**. Le système utilise:
- JWT Supabase (pas de JWT custom)
- Vérification avec `SUPABASE_JWT_SECRET`
- Header `Authorization: Bearer <token>`

**Q5.3:** Stockage users/permissions:
✅ **Table Supabase `auth.users`**. Le système:
- Utilise les tokens JWT émis par Supabase Auth
- Extrait `user_id`, `email`, `role` depuis le payload JWT
- Pas de fichier config (contrairement à V4)
- Les permissions peuvent être gérées via RLS (Row Level Security) dans Supabase

---

## Q6: Routes FastAPI

**Q6.1:** Structure existante?
✅ **Option A: Module dédié** (recommandé). Pattern actuel:
```python
# api/assistant.py (à créer)
router = APIRouter(prefix="/assistant", tags=["assistant"])

@router.post("/chat")
async def chat(request: ChatRequest):
    ...
```

Puis dans `api/main.py`:
```python
from api.assistant import router as assistant_router
app.include_router(assistant_router)
```

**Q6.2:** Port FastAPI:
✅ **8000** (standard). Confirmé dans `api/main.py` ligne 96:
```python
uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## Q7: Tests et Validation

**Q7.1:** Stratégie de test:
💡 **Recommandation:** V4 (Windows 5000) + V5 (Mac 8000) en parallèle pour:
- Comparaison directe des réponses
- Validation progressive fonctionnalité par fonctionnalité
- Rollback facile si problème
- Pas d'interruption de service

**Q7.2:** Tests prioritaires:
✅ **Créer tests automatisés**. Créer `tests/test_assistant.py` avec:
```python
import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_chat_rv():
    response = client.post("/assistant/chat", json={"question": ".mes rv"})
    assert response.status_code == 200

def test_chat_rv_demain():
    response = client.post("/assistant/chat", json={"question": "mes rendez-vous demain"})
    assert response.status_code == 200

# etc.
```

---

## Q8: Déploiement

**Q8.1:** Plateforme cible:
💡 **Recommandation:** Cloud (Render / Railway) pour:
- Disponibilité 24/7
- Pas de dépendance à la machine locale
- Scalabilité
- Backup automatique
- **Note:** Le projet a déjà des fichiers de déploiement (`DEPLOYMENT.md`, `CONFIGURER_SUPABASE_RENDER.md`)

**Q8.2:** Plan de transition:
💡 **Recommandation:** Cohabitation V4+V5 (1-2 semaines) pour:
- Tests en production avec utilisateurs réels
- Validation complète avant basculement
- Migration progressive fonctionnalité par fonctionnalité
- Rollback facile si problème

**Q8.3:** Rollback V4 si problème:
⚠️ **À définir**. Procédure recommandée:
1. Garder V4 Windows actif pendant la période de cohabitation
2. Documenter les endpoints V4 vs V5
3. Configurer un proxy/load balancer pour basculer rapidement
4. Script de rollback automatique si erreurs critiques détectées

---

## 📝 RÉSUMÉ DES ACTIONS REQUISES

### Actions Immédiates (Avant Implémentation)

1. ✅ **Vérifier tables Gazelle:**
   ```bash
   python scripts/check_gazelle_tables.py
   ```

2. ✅ **Vérifier données importées:**
   - Si tables vides → suivre `GUIDE_MIGRATION_IMPORT_GAZELLE_CLOUD.md`

3. ✅ **Localiser `gazelle_vectors.pkl`:**
   - Chercher sur Mac
   - Si absent, copier depuis Windows V4
   - Si perdu, prévoir recréation

4. ✅ **Vérifier clé OpenAI:**
   ```bash
   grep OPENAI .env
   ```

5. ✅ **Vérifier variables Supabase:**
   ```bash
   grep SUPABASE .env
   ```

### Structure à Créer

```
modules/assistant/
├── __init__.py
├── migrations/
│   └── (si nécessaire pour tables spécifiques)
└── services/
    ├── parser.py          # COPIER depuis V4
    ├── queries.py         # ADAPTER depuis V4 (SQL Server → PostgreSQL)
    └── vector_search.py   # COPIER depuis V4

api/
└── assistant.py          # NOUVEAU: Routes FastAPI pour l'assistant
```

### Variables d'Environnement Requises

```bash
# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_PASSWORD=xxx
SUPABASE_DATABASE=postgres
SUPABASE_USER=postgres
SUPABASE_PORT=5432
SUPABASE_JWT_SECRET=xxx

# OpenAI
OPENAI_API_KEY=sk-xxx
```

---

## ✅ VALIDATION

**Prochaines étapes après validation de ces réponses:**

1. Allan valide les réponses
2. Ajustement du guide selon réponses
3. Création fichiers base → Parser, Queries, Vector
4. Tests unitaires → pytest
5. Intégration FastAPI → Routes + auth
6. Tests end-to-end → V4 vs V5
7. Validation Allan → Approbation
8. Déploiement → Production

---

**Créé:** 2025-12-14  
**Par:** Cursor Mac Assistant  
**Statut:** ✅ Prêt pour validation
