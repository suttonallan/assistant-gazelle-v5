# Variables d'Environnement - Configuration Déploiement

## 📋 Checklist Complète pour Render & GitHub Pages

### 🔧 **Backend (Render)**

#### Variables OBLIGATOIRES:

```bash
# Supabase
SUPABASE_URL=https://beblgzvmjqkcillmcavk.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<VOTRE_CLE_SERVICE_ROLE>
SUPABASE_KEY=<VOTRE_CLE_ANON>  # Fallback si SERVICE_ROLE_KEY absent

# Gazelle API
GAZELLE_CLIENT_ID=<VOTRE_CLIENT_ID>
GAZELLE_CLIENT_SECRET=<VOTRE_CLIENT_SECRET>
```

#### Variables OPTIONNELLES:

```bash
# Place des Arts (si vous utilisez cet établissement)
GAZELLE_CLIENT_ID_PDA=<CLIENT_ID_PLACE_DES_ARTS>

# Vincent d'Indy (optionnel - utilise GAZELLE_CLIENT_ID par défaut)
GAZELLE_CLIENT_ID_VDI=<CLIENT_ID_VINCENT_DINDY>

# Orford (optionnel)
GAZELLE_CLIENT_ID_ORFORD=<CLIENT_ID_ORFORD>
```

---

### 🌐 **Frontend (GitHub Pages / Vite)**

#### Variables OBLIGATOIRES:

```bash
# URL de votre API déployée sur Render
VITE_API_URL=https://assistant-gazelle-v5-api.onrender.com
```

#### Variables OPTIONNELLES (pour accès direct Supabase depuis frontend):

```bash
# Supabase (si vous voulez que le frontend accède directement à Supabase)
VITE_SUPABASE_URL=https://beblgzvmjqkcillmcavk.supabase.co
VITE_SUPABASE_ANON_KEY=<VOTRE_CLE_ANON_SUPABASE>

# Gazelle Client IDs (pour config frontend)
VITE_GAZELLE_CLIENT_ID_VDI=<CLIENT_ID_VINCENT_DINDY>
VITE_GAZELLE_CLIENT_ID_ORFORD=<CLIENT_ID_ORFORD>
VITE_GAZELLE_CLIENT_ID_PDA=<CLIENT_ID_PLACE_DES_ARTS>
```

---

## 🔐 **Où Trouver les Valeurs?**

### Supabase:
1. Aller sur https://supabase.com/dashboard
2. Sélectionner votre projet
3. Settings → API
   - `SUPABASE_URL`: Project URL
   - `SUPABASE_SERVICE_ROLE_KEY`: service_role (secret)
   - `SUPABASE_ANON_KEY`: anon (public)

### Gazelle API:
1. Ces valeurs sont dans votre fichier `.env` local
2. Si vous ne les avez pas:
   - Contacter l'admin Gazelle
   - Ou vérifier la documentation interne

---

## 🚀 **Configuration dans Render**

1. Aller sur https://dashboard.render.com
2. Sélectionner votre service `assistant-gazelle-v5-api`
3. Environment → Environment Variables
4. Ajouter chaque variable avec `Add Environment Variable`
5. **IMPORTANT:** Redéployer après avoir ajouté les variables

---

## 🏗️ **Configuration dans GitHub Pages (Vite)**

### Option A: Fichier .env.production (Recommandé)

Créer `frontend/.env.production`:
```bash
VITE_API_URL=https://assistant-gazelle-v5-api.onrender.com
```

### Option B: Variables dans GitHub Secrets

1. Aller sur votre repo GitHub
2. Settings → Secrets and variables → Actions
3. Ajouter `VITE_API_URL`
4. Modifier `.github/workflows/deploy.yml` pour passer la variable au build

---

## ✅ **Validation Post-Déploiement**

### Backend (Render):
```bash
# Test de santé
curl https://assistant-gazelle-v5-api.onrender.com/

# Vérifier les variables
curl https://assistant-gazelle-v5-api.onrender.com/health
```

### Frontend (GitHub Pages):
1. Ouvrir https://suttonallan.github.io/assistant-gazelle-v5
2. Ouvrir la console développeur (F12)
3. Vérifier qu'il n'y a pas d'erreur CORS
4. Tester le changement d'établissement (Vincent d'Indy → Orford)

---

## 🔒 **Sécurité**

### ✅ **Ce qui est OK d'exposer:**
- `SUPABASE_URL` (public)
- `SUPABASE_ANON_KEY` (public, limité par RLS)
- `VITE_API_URL` (public)
- Client IDs Gazelle (semi-publics)

### ❌ **NE JAMAIS EXPOSER:**
- `SUPABASE_SERVICE_ROLE_KEY` (bypass RLS)
- `GAZELLE_CLIENT_SECRET` (permet accès complet API)
- Fichier `.env` (ajouté au .gitignore)

---

## 🐛 **Troubleshooting**

### Erreur: "GAZELLE_CLIENT_ID/SECRET manquants"
→ Ajouter les variables dans Render et redéployer

### Erreur CORS depuis GitHub Pages
→ Vérifier que `https://suttonallan.github.io` est dans allow_origins (api/main.py)

### Frontend ne charge pas les données
→ Vérifier que `VITE_API_URL` pointe vers Render
→ Vérifier que l'API Render est active (pas en sleep mode)

### Pianos ne s'affichent pas
→ Vérifier les logs Render: `View Logs` dans le dashboard
→ Vérifier que les Client IDs correspondent aux bonnes institutions

---

## 📝 **Résumé: Variables Minimales pour Déployer**

### Backend (Render) - 4 variables OBLIGATOIRES:
1. `SUPABASE_URL`
2. `SUPABASE_SERVICE_ROLE_KEY`
3. `GAZELLE_CLIENT_ID`
4. `GAZELLE_CLIENT_SECRET`

### Frontend (GitHub Pages) - 1 variable OBLIGATOIRE:
1. `VITE_API_URL`

Avec ces 5 variables, votre application sera fonctionnelle en production! 🎉
