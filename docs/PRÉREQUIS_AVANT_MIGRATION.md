# 🔧 PRÉREQUIS AVANT MIGRATION
## Informations nécessaires pour Cursor Mac

**Date:** 2025-12-14
**Urgence:** 🔥 CRITIQUE - À fournir avant de commencer

---

## 📋 INFORMATIONS REQUISES D'ALLAN

### 1. 🔐 SUPABASE_PASSWORD

**Besoin:** Mot de passe PostgreSQL de votre projet Supabase

**Comment l'obtenir:**
1. Aller sur [Supabase Dashboard](https://supabase.com/dashboard)
2. Sélectionner votre projet
3. Aller dans **Settings** → **Database**
4. Section **Connection string**
5. Cliquer sur **Reveal** (ou **Show**)
6. Copier le mot de passe (entre `:` et `@` dans la connection string)

**Format attendu:**
```
Connection string:
postgresql://postgres.xxxxx:YOUR_PASSWORD_HERE@aws-0-us-east-1.pooler.supabase.com:6543/postgres

Le mot de passe est: YOUR_PASSWORD_HERE
```

**Où le mettre:**
```bash
# Dans ~/assistant-gazelle-v5/.env
SUPABASE_PASSWORD=votre_mot_de_passe_ici
```

---

### 2. 🤖 OPENAI_API_KEY

**Besoin:** Clé API OpenAI (commence par `sk-`)

**Comment l'obtenir:**
- **Option A:** Utiliser la même clé que V4
  - Ouvrir `C:\Allan Python projets\assistant-gazelle\.env` sur PC Windows
  - Copier la valeur de `OPENAI_API_KEY`

- **Option B:** Créer une nouvelle clé
  1. Aller sur [OpenAI Platform](https://platform.openai.com/api-keys)
  2. Cliquer **Create new secret key**
  3. Nommer la clé (ex: "Assistant Gazelle V5")
  4. Copier la clé (commence par `sk-`)

**Format attendu:**
```
sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**Où la mettre:**
```bash
# Dans ~/assistant-gazelle-v5/.env
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**⚠️ IMPORTANT:**
- La clé ne sera visible qu'une seule fois
- La sauvegarder dans un endroit sûr

---

### 3. 📦 gazelle_vectors.pkl

**Besoin:** Fichier d'index vectoriel (126,519 entrées)

**Localisation actuelle (V4):**
```
C:\Allan Python projets\assistant-gazelle\data\gazelle_vectors.pkl
```

**Options:**

#### Option A: Copier le fichier existant (RECOMMANDÉ) ✅
**Avantages:**
- Fonctionne immédiatement
- Testé et validé
- Pas besoin de recréer (économise temps + coûts OpenAI)

**Actions:**
1. Localiser le fichier sur PC Windows:
   ```
   C:\Allan Python projets\assistant-gazelle\data\gazelle_vectors.pkl
   ```

2. Copier vers Mac:
   ```bash
   # Option 1: Via réseau partagé
   cp "C:\Allan Python projets\assistant-gazelle\data\gazelle_vectors.pkl" \
      "\\tsclient\assistant-gazelle-v5\data\gazelle_vectors.pkl"

   # Option 2: Via USB/iCloud/email (si fichier < 100MB)
   ```

3. Vérifier la copie:
   ```bash
   ls -lh ~/assistant-gazelle-v5/data/gazelle_vectors.pkl
   # Devrait afficher la taille du fichier
   ```

#### Option B: Recréer le fichier (si copie impossible) ⚠️
**Inconvénients:**
- Coûte en crédits OpenAI (embeddings pour 126,519 entrées)
- Prend du temps (plusieurs heures)
- Nécessite accès aux données sources

**Si cette option est nécessaire:**
- Confirmer d'abord avec Allan
- Estimer les coûts OpenAI
- Préparer script de génération

**🎯 RECOMMANDATION:** Option A (copier fichier existant)

---

### 4. 📊 Variables d'environnement Supabase

**Besoin:** Configuration complète Supabase

**À ajouter dans `~/assistant-gazelle-v5/.env`:**

```bash
# Supabase PostgreSQL Connection
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_HOST=db.xxxxx.supabase.co
SUPABASE_PASSWORD=votre_mot_de_passe_ici
SUPABASE_DATABASE=postgres
SUPABASE_USER=postgres
SUPABASE_PORT=5432

# Supabase API (si nécessaire)
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# OpenAI
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Application
APP_PORT=8000
APP_ENV=development
```

**Comment obtenir ces valeurs:**
1. **SUPABASE_URL** et **SUPABASE_HOST**:
   - Dashboard Supabase → Settings → API
   - URL: Section "Project URL"
   - Host: Extraire de la connection string

2. **SUPABASE_KEY** (clé API):
   - Dashboard Supabase → Settings → API
   - Copier "anon public" key

---

## ✅ CHECKLIST PRÉREQUIS

Avant de commencer l'implémentation, vérifier:

### Configuration Supabase
- [ ] **SUPABASE_PASSWORD** obtenu et testé
- [ ] **SUPABASE_URL** configuré
- [ ] **SUPABASE_HOST** configuré
- [ ] Connexion testée: `python scripts/test_supabase_connection.py`

### OpenAI
- [ ] **OPENAI_API_KEY** obtenu (sk-...)
- [ ] Clé testée (simple appel API)
- [ ] Crédits disponibles sur compte OpenAI

### Vector Index
- [ ] **gazelle_vectors.pkl** localisé sur Windows
- [ ] Fichier copié vers Mac: `~/assistant-gazelle-v5/data/`
- [ ] Taille fichier vérifiée (devrait être > 1MB)

### Fichier .env
- [ ] Fichier `~/assistant-gazelle-v5/.env` créé
- [ ] Toutes les variables ajoutées
- [ ] Permissions correctes: `chmod 600 .env`

### Tables Gazelle
- [ ] Tables vérifiées dans Supabase:
  ```sql
  SELECT table_name
  FROM information_schema.tables
  WHERE table_schema = 'gazelle';
  ```
- [ ] Tables attendues:
  - [ ] gazelle.appointments
  - [ ] gazelle.clients
  - [ ] gazelle.contacts
  - [ ] gazelle.pianos
  - [ ] gazelle.timeline_entries

---

## 🧪 TESTS DE VALIDATION

Après avoir configuré les prérequis:

### Test 1: Connexion Supabase
```bash
cd ~/assistant-gazelle-v5
python scripts/test_supabase_connection.py
```

**Résultat attendu:**
```
✅ Connexion réussie!
PostgreSQL version: PostgreSQL 15.x...
✅ Table inv.produits_catalogue existe (X enregistrements)
```

### Test 2: OpenAI API
```bash
python -c "
import os
from openai import OpenAI
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
response = client.embeddings.create(
    model='text-embedding-3-small',
    input='test'
)
print('✅ OpenAI API fonctionne!')
print(f'Embedding dimension: {len(response.data[0].embedding)}')
"
```

**Résultat attendu:**
```
✅ OpenAI API fonctionne!
Embedding dimension: 1536
```

### Test 3: Vector Index
```bash
python -c "
import pickle
import os
with open('data/gazelle_vectors.pkl', 'rb') as f:
    index = pickle.load(f)
print(f'✅ Vector index chargé!')
print(f'Nombre d\'entrées: {len(index.get(\"entries\", []))}')
"
```

**Résultat attendu:**
```
✅ Vector index chargé!
Nombre d'entrées: 126519
```

---

## 📝 TEMPLATE .env COMPLET

Copier ce template dans `~/assistant-gazelle-v5/.env` et remplir les valeurs:

```bash
# =============================================================================
# SUPABASE POSTGRESQL CONNECTION
# =============================================================================
# Obtenir depuis: Dashboard Supabase → Settings → Database
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_HOST=db.xxxxx.supabase.co
SUPABASE_PASSWORD=                    # ⚠️ À REMPLIR
SUPABASE_DATABASE=postgres
SUPABASE_USER=postgres
SUPABASE_PORT=5432

# =============================================================================
# SUPABASE API (Optionnel, pour l'API REST)
# =============================================================================
# Obtenir depuis: Dashboard Supabase → Settings → API
SUPABASE_KEY=                         # ⚠️ À REMPLIR (clé "anon public")

# =============================================================================
# OPENAI
# =============================================================================
# Obtenir depuis: https://platform.openai.com/api-keys
OPENAI_API_KEY=                       # ⚠️ À REMPLIR (sk-...)

# =============================================================================
# APPLICATION
# =============================================================================
APP_PORT=8000
APP_ENV=development
APP_DEBUG=true

# =============================================================================
# AUTHENTIFICATION (V4 - à adapter pour V5)
# =============================================================================
JWT_SECRET_KEY=your-secret-key-here-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# =============================================================================
# VECTOR SEARCH
# =============================================================================
VECTOR_INDEX_PATH=data/gazelle_vectors.pkl
EMBEDDING_MODEL=text-embedding-3-small
```

---

## 🚨 SÉCURITÉ

### ⚠️ IMPORTANT

1. **Fichier .env**:
   ```bash
   chmod 600 ~/assistant-gazelle-v5/.env
   ```
   - Permissions: Lecture/écriture propriétaire uniquement
   - **NE JAMAIS** committer `.env` dans Git

2. **Vérifier .gitignore**:
   ```bash
   echo ".env" >> ~/assistant-gazelle-v5/.gitignore
   ```

3. **Mots de passe**:
   - Utiliser un gestionnaire de mots de passe
   - Ne jamais partager par email/Slack non chiffré
   - Considérer variables d'environnement système:
     ```bash
     export SUPABASE_PASSWORD="..."
     export OPENAI_API_KEY="..."
     ```

---

## 📞 QUESTIONS / PROBLÈMES

### Si SUPABASE_PASSWORD ne fonctionne pas:
1. Vérifier qu'il n'y a pas d'espaces avant/après
2. Essayer de regénérer le mot de passe dans Dashboard
3. Tester avec psql:
   ```bash
   psql "postgresql://postgres:PASSWORD@db.xxxxx.supabase.co:5432/postgres"
   ```

### Si OPENAI_API_KEY invalide:
1. Vérifier qu'elle commence par `sk-`
2. Vérifier qu'il n'y a pas de caractères invisibles
3. Regénérer une nouvelle clé si nécessaire

### Si gazelle_vectors.pkl inaccessible:
1. Vérifier que le dossier `data/` existe:
   ```bash
   mkdir -p ~/assistant-gazelle-v5/data
   ```
2. Vérifier les permissions du fichier
3. Contacter Allan pour obtenir le fichier

---

## 🎯 PROCHAINE ÉTAPE

Une fois TOUS les prérequis validés:

1. ✅ Exécuter les 3 tests de validation
2. ✅ Confirmer que tous passent
3. 📝 Répondre aux questions dans [QUESTIONS_CURSORMAC_ASSISTANT.md](QUESTIONS_CURSORMAC_ASSISTANT.md)
4. ⏸️ Attendre validation Allan
5. 🚀 Commencer l'implémentation

---

**Créé:** 2025-12-14
**Par:** Claude Code (Windows)
**Pour:** Cursor Mac + Allan
**Statut:** 🔥 CRITIQUE - À compléter AVANT migration
