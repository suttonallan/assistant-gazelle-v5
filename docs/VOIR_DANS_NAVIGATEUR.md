# 🌐 Comment Voir Vos Données dans le Navigateur

**Guide rapide pour voir l'interface React dans votre navigateur**

---

## 🚀 Démarrage Rapide (2 Terminaux)

### Terminal 1: Backend FastAPI

```bash
cd /Users/allansutton/Documents/assistant-gazelle-v5
python3 -m uvicorn api.main:app --reload --port 8000
```

**Vous devriez voir:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

✅ **Backend démarré!** Laissez ce terminal ouvert.

---

### Terminal 2: Frontend React

```bash
cd /Users/allansutton/Documents/assistant-gazelle-v5/frontend
npm run dev
```

**Vous devriez voir:**
```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

✅ **Frontend démarré!** Laissez ce terminal ouvert.

---

## 🌐 Ouvrir dans le Navigateur

### Option 1: Ouvrir Automatiquement

Le terminal Vite devrait afficher l'URL. Cliquez dessus ou copiez-la.

### Option 2: Ouvrir Manuellement

**Ouvrez votre navigateur et allez à:**

```
http://localhost:5173
```

---

## 🔐 Connexion

### Écran de Connexion

Vous verrez un écran de connexion. Utilisez:

**Pour Admin (voir tout):**
- **Nom:** `Allan` (ou votre nom)
- **Rôle:** `admin`

**Pour Technicien (vue limitée):**
- **Nom:** Votre nom
- **Rôle:** `technicien`

---

## 📦 Voir l'Inventaire

### Après Connexion

1. **Si vous êtes admin:**
   - Cliquez sur **"📦 Inventaire"** dans le menu en haut
   - Vous verrez tous les onglets: Catalogue, Stock, Transactions, Admin

2. **Si vous êtes technicien:**
   - Vous verrez directement l'inventaire (vue limitée)

---

## 📊 Onglets Disponibles

### 1. Catalogue
- Liste de tous les produits
- Filtres par catégorie et commission
- Bouton "📥 Exporter CSV"

### 2. Stock Technicien
- Inventaire par technicien
- Sélection du technicien dans le menu déroulant

### 3. Transactions
- Historique des mouvements
- Filtres par technicien et produit

### 4. Admin (admin uniquement)
- Modification des produits
- Configuration des commissions
- Réorganisation de l'ordre d'affichage
- Export CSV

---

## 🔍 Vérifier que les Données Sont Là

### Si vous voyez "Aucun produit dans le catalogue"

**Cela signifie que les données n'ont pas encore été importées.**

**Solution:**
1. Vérifier dans Supabase Dashboard que les données sont là
2. Si non, exécuter le script d'import sur PC
3. Rafraîchir la page (F5)

### Si vous voyez vos produits

✅ **Tout fonctionne!** Vous pouvez:
- Modifier les produits
- Configurer les commissions
- Réorganiser l'ordre
- Exporter en CSV

---

## 🐛 Dépannage

### Erreur: "Failed to fetch"

**Cause:** Le backend n'est pas démarré

**Solution:**
```bash
# Vérifier que le backend tourne
curl http://localhost:8000/health
```

Si ça ne fonctionne pas, redémarrer le backend (Terminal 1).

---

### Erreur: "Connection refused"

**Cause:** Le frontend essaie de se connecter au mauvais port

**Vérifier:**
- Backend sur port 8000
- Frontend sur port 5173
- Variable `VITE_API_URL` dans `.env` (optionnel)

---

### Page blanche

**Cause:** Erreur JavaScript

**Solution:**
1. Ouvrir la console du navigateur (F12)
2. Voir les erreurs
3. Vérifier que les deux serveurs tournent

---

## 📋 Checklist Rapide

- [ ] Backend démarré (Terminal 1) → http://localhost:8000
- [ ] Frontend démarré (Terminal 2) → http://localhost:5173
- [ ] Navigateur ouvert → http://localhost:5173
- [ ] Connecté (admin)
- [ ] Onglet "Inventaire" ouvert
- [ ] Données visibles

---

## 🎯 URLs Importantes

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend React** | http://localhost:5173 | Interface utilisateur |
| **Backend API** | http://localhost:8000 | API FastAPI |
| **Swagger UI** | http://localhost:8000/docs | Documentation API |
| **Health Check** | http://localhost:8000/health | Vérification backend |

---

## ✅ Résumé

1. **Démarrer backend:** `python3 -m uvicorn api.main:app --reload --port 8000`
2. **Démarrer frontend:** `cd frontend && npm run dev`
3. **Ouvrir navigateur:** http://localhost:5173
4. **Se connecter:** Admin
5. **Cliquer:** "📦 Inventaire"

**C'est tout!** 🎉
