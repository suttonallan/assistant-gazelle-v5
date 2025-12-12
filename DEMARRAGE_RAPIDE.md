# 🚀 Démarrage Rapide - Assistant Gazelle V5

**Guide pour lancer et tester l'application**

---

## ⚡ Lancement en 3 Commandes

### 1. Backend (FastAPI)
```bash
# Terminal 1
cd /Users/allansutton/Documents/assistant-gazelle-v5
source .env
python3 -m uvicorn api.main:app --reload --port 8000
```

**Vérification:**
```bash
curl http://localhost:8000/health
# Devrait afficher: {"status":"healthy"}
```

### 2. Frontend (React + Vite)
```bash
# Terminal 2
cd /Users/allansutton/Documents/assistant-gazelle-v5/frontend
npm run dev
```

**Accès:** http://localhost:5173

### 3. Ouvrir dans le Navigateur
```bash
open http://localhost:5173
```

---

## 🧪 Tests Rapides API

### Test 1: Lire l'inventaire d'Allan
```bash
curl -s http://localhost:8000/inventaire/stock/Allan | python3 -m json.tool
```

### Test 2: Mettre à jour une quantité
```bash
curl -X POST http://localhost:8000/inventaire/stock \
  -H "Content-Type: application/json" \
  -d '{
    "code_produit": "PROD-4",
    "technicien": "Allan",
    "quantite_stock": 20,
    "motif": "Test rapide"
  }'
```

### Test 3: Envoyer un commentaire → Slack
```bash
curl -X POST http://localhost:8000/inventaire/comment \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Besoin de coupelles brunes",
    "username": "Allan"
  }'
```

### Test 4: Voir les transactions
```bash
curl -s "http://localhost:8000/inventaire/transactions?limit=5" | python3 -m json.tool
```

---

## 📋 Checklist Avant Production

### ✅ Migrations BDD à Exécuter

**Étape 1: Ouvrir Supabase Dashboard**
- URL: https://beblgzvmjqkcillmcavk.supabase.com
- Aller dans **SQL Editor**

**Étape 2: Exécuter Migration 002**
```sql
-- Copier-coller le contenu de:
-- scripts/migrations/002_add_v4_columns_to_produits.sql
```

**Étape 3: Exécuter Migration 003**
```sql
-- Copier-coller le contenu de:
-- scripts/migrations/003_create_central_schemas.sql
```

**Étape 4: Vérifier**
```bash
python3 scripts/data/initial_schema_creator.py --check
# Devrait afficher 8/8 tables existantes
```

---

## 🎯 Scénarios de Test Interface

### Scénario 1: Vue Technicien Mobile
1. Ouvrir http://localhost:5173 sur mobile (ou réduire fenêtre <768px)
2. Devrait afficher **1 seule colonne** (utilisateur connecté)
3. Cliquer sur une quantité → modifier → blur
4. Vérifier feedback vert 1 seconde
5. Rafraîchir → quantité mise à jour

### Scénario 2: Vue Admin Desktop
1. Ouvrir http://localhost:5173 sur desktop
2. Onglet **Admin**
3. Voir **toutes les colonnes** (Allan, Nicolas, Jean-Philippe)
4. Drag & drop une ligne vers le haut/bas
5. Cliquer **"💾 Sauvegarder l'ordre"**
6. Rafraîchir → ordre conservé

### Scénario 3: Commentaire Slack
1. En bas de l'inventaire, zone commentaire
2. Taper: "Besoin urgent de cordes #1"
3. Cliquer **"Envoyer"**
4. Vérifier notification reçue dans Slack (canaux admin)

---

## 🔧 Dépannage

### Backend ne démarre pas
```bash
# Vérifier port 8000 libre
lsof -ti:8000 | xargs kill

# Vérifier variables d'environnement
cat .env | grep SUPABASE
```

### Frontend erreur CORS
Vérifier dans `frontend/vite.config.js`:
```javascript
server: {
  proxy: {
    '/api': 'http://localhost:8000'
  }
}
```

### Supabase erreur 401
```bash
# Vérifier clés valides
echo $SUPABASE_URL
echo $SUPABASE_KEY
```

---

## 📊 Données de Test

### Créer un Produit Test
```bash
curl -X POST http://localhost:8000/inventaire/catalogue \
  -H "Content-Type: application/json" \
  -d '{
    "code_produit": "TEST-001",
    "nom": "Produit Test",
    "categorie": "Test",
    "prix_unitaire": 10.0,
    "unite_mesure": "unité",
    "is_active": true,
    "display_order": 1
  }'
```

### Ajouter Stock Initial
```bash
for TECH in Allan Nicolas Jean-Philippe; do
  curl -X POST http://localhost:8000/inventaire/stock \
    -H "Content-Type: application/json" \
    -d "{
      \"code_produit\": \"TEST-001\",
      \"technicien\": \"$TECH\",
      \"quantite_stock\": 5,
      \"motif\": \"Stock initial test\"
    }"
done
```

---

## 📚 Documentation Complète

- [MODIFICATIONS_INVENTAIRE_V4.md](MODIFICATIONS_INVENTAIRE_V4.md) - Détails techniques inventaire
- [MIGRATION_BDD_CENTRALES.md](MIGRATION_BDD_CENTRALES.md) - Guide schémas BDD
- [TEST_INVENTAIRE.md](TEST_INVENTAIRE.md) - Checklist tests exhaustifs
- [RESUME_SESSION_2025-12-11.md](RESUME_SESSION_2025-12-11.md) - Résumé session

---

## 🎉 Statut Actuel

✅ **Backend:** Opérationnel (port 8000)
✅ **Frontend:** Opérationnel (port 5173)
✅ **Inventaire V4:** Restauré et testé
✅ **Notifications Slack:** Fonctionnelles
⚠️ **Migrations BDD:** À exécuter manuellement (002 + 003)
⚠️ **Import Gazelle:** Scripts prêts, exports à fournir

**Prêt pour production après exécution des migrations SQL !**
