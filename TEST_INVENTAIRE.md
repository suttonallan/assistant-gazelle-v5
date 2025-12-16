# 🧪 Tests Inventaire V4 restauré

## Tests à effectuer pour valider la migration

### ✅ **1. Frontend - Vue Technicien**

#### Chargement initial
- [ ] Page charge en <2 secondes
- [ ] Tableau affiche tous les produits
- [ ] Groupement par catégorie fonctionne
- [ ] Produits triés par display_order

#### Sticky scroll
- [ ] Scroll vertical : header reste fixe en haut
- [ ] Scroll horizontal : colonne "Produit" reste fixe à gauche
- [ ] Headers de catégorie sticky (sous le header principal)

#### Édition inline
```
Test:
1. Cliquer sur un input de quantité
2. Vérifier que le texte est sélectionné automatiquement
3. Taper une nouvelle valeur (ex: 10)
4. Cliquer ailleurs (blur)
5. Vérifier feedback vert 1 seconde
6. Vérifier que la valeur est sauvegardée
```

#### Filtre mobile/desktop
```
Test mobile:
1. Réduire fenêtre à <768px
2. Vérifier qu'une seule colonne est affichée (utilisateur connecté)
3. Si admin: toutes les colonnes visibles

Test desktop:
1. Agrandir fenêtre >768px
2. Vérifier que toutes les colonnes sont affichées
```

#### Commentaire rapide
```
Test:
1. Taper dans la zone commentaire: "Test notification Slack"
2. Cliquer "Envoyer"
3. Vérifier le message de confirmation
4. Vérifier notification Slack reçue sur #general ou canal admin
```

---

### ✅ **2. Frontend - Vue Admin**

#### Drag & Drop
```
Test:
1. Aller dans onglet "Admin"
2. Cliquer-maintenir sur une ligne
3. Glisser vers haut ou bas
4. Vérifier que l'ordre change visuellement
5. Cliquer "💾 Sauvegarder l'ordre"
6. Recharger la page
7. Vérifier que l'ordre est conservé
```

#### Recherche
```
Test:
1. Taper "cord" dans la recherche
2. Vérifier que seuls les produits avec "cord" sont affichés
3. Effacer la recherche
4. Vérifier que tous les produits réapparaissent
```

#### Boutons ↑↓
```
Test:
1. Cliquer sur ▲ d'un produit
2. Vérifier qu'il monte d'une position
3. Cliquer sur ▼
4. Vérifier qu'il descend d'une position
```

#### Modal édition
```
Test:
1. Cliquer sur ✏️ d'un produit
2. Modal s'ouvre avec les données
3. Modifier:
   - Nom
   - Catégorie
   - Prix
   - Commission (activer/désactiver)
   - Groupe de variantes
   - Label de variante
4. Cliquer "Enregistrer"
5. Vérifier que les modifications sont visibles dans le tableau
```

#### Toggle actif/inactif
```
Test:
1. Cliquer sur 🚫 d'un produit actif
2. Vérifier que la ligne devient grisée avec strikethrough
3. Aller dans vue technicien
4. Vérifier que le produit n'apparaît plus
5. Retour admin, cliquer sur ✅
6. Vérifier que le produit redevient actif
```

---

### ✅ **3. Backend - Endpoints**

#### Test API avec curl/Postman

**A. Mise à jour de stock :**
```bash
curl -X POST http://localhost:8000/inventaire/stock \
  -H "Content-Type: application/json" \
  -d '{
    "code_produit": "CORD-001",
    "technicien": "Allan",
    "quantite_stock": 15,
    "motif": "Test API"
  }'

# Vérifier réponse:
# {
#   "success": true,
#   "old_quantity": 10,
#   "new_quantity": 15,
#   "message": "Stock mis à jour pour Allan"
# }
```

**B. Commentaire inventaire :**
```bash
curl -X POST http://localhost:8000/inventaire/comment \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Test notification Slack depuis API",
    "username": "Allan"
  }'

# Vérifier:
# 1. Réponse {"success": true, ...}
# 2. Notification Slack reçue
```

**C. Mise à jour produit catalogue :**
```bash
curl -X PUT http://localhost:8000/inventaire/catalogue/CORD-001 \
  -H "Content-Type: application/json" \
  -d '{
    "nom": "Corde #1 Modifiée",
    "has_commission": true,
    "commission_rate": 20,
    "variant_group": "Cordes Piano",
    "variant_label": "Do#3"
  }'

# Vérifier:
# {"success": true, "message": "Produit mis à jour", ...}
```

**D. Sauvegarde bulk order :**
```bash
curl -X PATCH http://localhost:8000/inventaire/catalogue/batch-order \
  -H "Content-Type: application/json" \
  -d '{
    "products": [
      {"code_produit": "CORD-001", "display_order": 1},
      {"code_produit": "CORD-002", "display_order": 2},
      {"code_produit": "FELT-001", "display_order": 3}
    ]
  }'

# Vérifier:
# {"success": true, "updated_count": 3, ...}
```

---

### ✅ **4. Intégration complète**

#### Workflow complet technicien
```
Scénario: Nicolas a besoin de coupelles brunes
1. Nicolas ouvre l'inventaire sur mobile
2. Voit uniquement sa colonne
3. Trouve "Coupelles brunes" : quantité = 0
4. Tape dans commentaire: "Besoin urgent de 10 coupelles brunes"
5. Envoie → Slack notifie Allan (admin)
6. Allan reçoit notification Slack
7. Allan ouvre admin desktop
8. Trouve "Coupelles brunes"
9. Modifie quantité Nicolas: 0 → 10
10. Nicolas rafraîchit → voit 10 coupelles
```

#### Workflow réorganisation admin
```
Scénario: Allan veut regrouper les cordes ensemble
1. Allan ouvre admin
2. Filtre recherche: "cord"
3. Voit toutes les cordes
4. Drag & drop pour les mettre dans l'ordre:
   - Corde #1, #2, #3, etc.
5. Modifie display_order de chaque corde (1, 2, 3...)
6. Clique "Sauvegarder l'ordre"
7. Retourne dans vue technicien
8. Voit les cordes groupées et triées
```

---

### ✅ **5. Tests de performance**

#### Chargement
- [ ] Catalogue de 100 produits charge en <2s
- [ ] Scroll fluide (pas de lag)
- [ ] Drag & drop responsive (<100ms)

#### Recherche admin
- [ ] Filtre instantané (<100ms)
- [ ] Pas de freeze avec 100+ produits

---

### ✅ **6. Tests edge cases**

#### Quantités négatives
```
Test:
1. Tenter de mettre quantité = -5
2. Vérifier que l'input n'accepte pas (min="0")
```

#### Produit inactif
```
Test:
1. Désactiver un produit (admin)
2. Vérifier qu'il disparaît de la vue technicien
3. Vérifier qu'il reste visible en admin (grisé)
```

#### Slack en échec
```
Test:
1. Couper internet ou modifier webhook invalide
2. Envoyer commentaire
3. Vérifier que l'UI ne bloque pas
4. Message: "Commentaire enregistré (notification Slack échouée)."
```

---

## 📊 Checklist de validation

### Frontend
- [ ] Sticky header/column
- [ ] Groupement catégories
- [ ] Édition inline + feedback
- [ ] Filtre mobile/desktop
- [ ] Commentaire Slack
- [ ] Drag & drop admin
- [ ] Recherche admin
- [ ] Modal édition
- [ ] Toggle actif/inactif

### Backend
- [ ] POST /stock fonctionne
- [ ] POST /comment envoie Slack
- [ ] PUT /catalogue accepte nouveaux champs
- [ ] PATCH /batch-order sauvegarde
- [ ] Transactions enregistrées

### Intégration
- [ ] Workflow technicien complet
- [ ] Workflow admin complet
- [ ] Performance OK (100 produits)

---

**🎯 Si tous les tests passent → Migration réussie !**
