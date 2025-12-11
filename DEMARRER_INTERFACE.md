# 🚀 Démarrer l'Interface pour Voir l'Inventaire

## Étape 1: Démarrer le Backend (Terminal 1)

```bash
cd /Users/allansutton/Documents/assistant-gazelle-v5
python3 -m uvicorn api.main:app --reload --port 8000
```

Vous devriez voir:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

## Étape 2: Démarrer le Frontend (Terminal 2)

```bash
cd /Users/allansutton/Documents/assistant-gazelle-v5/frontend
npm run dev
```

Vous devriez voir:
```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
```

## Étape 3: Ouvrir dans le Navigateur

1. Allez sur: **http://localhost:5173**
2. Connectez-vous (si nécessaire)
3. Cliquez sur **"Inventaire"** dans le menu
4. Cliquez sur l'onglet **"Catalogue"**

## ✅ Vous devriez voir vos 63 produits!

---

## URLs Utiles

- **Frontend React:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **API Docs (Swagger):** http://localhost:8000/docs
- **Supabase Dashboard:** https://supabase.com/dashboard
