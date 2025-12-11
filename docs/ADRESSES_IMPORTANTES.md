# 📍 Adresses Importantes - Assistant Gazelle V5

**Date:** 2025-01-15

---

## 🖥️ Développement Local (Mac)

### Frontend React
**URL:** http://localhost:5173

**Pour démarrer:**
```bash
cd frontend
npm run dev
```

**Pages disponibles:**
- http://localhost:5173 → Page d'accueil
- http://localhost:5173 → Inventaire (après connexion admin)

### Backend FastAPI
**URL:** http://localhost:8000

**Pour démarrer:**
```bash
python3 -m uvicorn api.main:app --reload --port 8000
```

**Endpoints:**
- http://localhost:8000 → API root (liste des endpoints)
- http://localhost:8000/docs → **Swagger UI** (documentation interactive)
- http://localhost:8000/redoc → ReDoc (documentation alternative)
- http://localhost:8000/health → Health check
- http://localhost:8000/inventaire/catalogue → Liste des produits
- http://localhost:8000/api/catalogue/add → Ajouter un produit

---

## ☁️ Supabase (Cloud)

### Dashboard Supabase
**URL:** https://app.supabase.com

**Votre projet:**
- **URL du projet:** https://beblgzvmjqkcillmcavk.supabase.co
- **Dashboard:** https://app.supabase.com/project/beblgzvmjqkcillmcavk

**Sections importantes:**
- **Table Editor:** https://app.supabase.com/project/beblgzvmjqkcillmcavk/editor
  - Table `produits_catalogue` → Vos produits
  - Table `inventaire_techniciens` → Stock par technicien
  - Table `transactions_inventaire` → Historique
  
- **SQL Editor:** https://app.supabase.com/project/beblgzvmjqkcillmcavk/sql
  - Pour exécuter les migrations SQL
  - Pour vérifier les données

- **API Settings:** https://app.supabase.com/project/beblgzvmjqkcillmcavk/settings/api
  - Project URL: `https://beblgzvmjqkcillmcavk.supabase.co`
  - anon public key: (dans `.env`)

---

## 🔗 URLs API Supabase

### API REST
**Base URL:** https://beblgzvmjqkcillmcavk.supabase.co/rest/v1

**Tables:**
- Produits catalogue: https://beblgzvmjqkcillmcavk.supabase.co/rest/v1/produits_catalogue
- Inventaire techniciens: https://beblgzvmjqkcillmcavk.supabase.co/rest/v1/inventaire_techniciens
- Transactions: https://beblgzvmjqkcillmcavk.supabase.co/rest/v1/transactions_inventaire

**Note:** Nécessite l'en-tête `Authorization: Bearer <SUPABASE_KEY>`

---

## 📋 Résumé Rapide

### Pour voir vos données en local:

1. **Démarrer le backend:**
   ```bash
   python3 -m uvicorn api.main:app --reload --port 8000
   ```
   → http://localhost:8000

2. **Démarrer le frontend:**
   ```bash
   cd frontend
   npm run dev
   ```
   → http://localhost:5173

3. **Ouvrir dans le navigateur:**
   - http://localhost:5173
   - Se connecter (admin)
   - Aller dans "Inventaire"

### Pour voir vos données dans Supabase:

1. **Dashboard:** https://app.supabase.com/project/beblgzvmjqkcillmcavk
2. **Table Editor:** https://app.supabase.com/project/beblgzvmjqkcillmcavk/editor
3. **Sélectionner:** Table `produits_catalogue`

---

## 🎯 URLs Clés

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend React** | http://localhost:5173 | Interface utilisateur |
| **Backend API** | http://localhost:8000 | API FastAPI |
| **Swagger UI** | http://localhost:8000/docs | Documentation API interactive |
| **Supabase Dashboard** | https://app.supabase.com/project/beblgzvmjqkcillmcavk | Gestion base de données |
| **Table Editor** | https://app.supabase.com/project/beblgzvmjqkcillmcavk/editor | Voir/modifier les données |
| **SQL Editor** | https://app.supabase.com/project/beblgzvmjqkcillmcavk/sql | Exécuter SQL |

---

## 📝 Notes

- **Frontend:** Port 5173 (Vite par défaut)
- **Backend:** Port 8000 (Uvicorn)
- **Supabase:** Cloud (pas de port local)
- **Credentials:** Dans `.env` à la racine du projet

---

## 🚀 Démarrage Rapide

```bash
# Terminal 1: Backend
cd /Users/allansutton/Documents/assistant-gazelle-v5
python3 -m uvicorn api.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev

# Navigateur
open http://localhost:5173
```

**C'est tout!** 🎉
