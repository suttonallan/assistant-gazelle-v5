# Prompt: Correction de la persistance des quantités dans l'inventaire des accessoires et fournitures

## Contexte du problème

Le système Assistant Gazelle V5 gère un inventaire des accessoires et fournitures pour chaque technicien. Les utilisateurs peuvent modifier les quantités directement dans l'interface, mais **les changements ne persistent pas correctement** - les quantités reviennent à leur valeur précédente après modification.

**Problème observé** : Quand un utilisateur change une quantité dans l'interface, la modification semble s'appliquer visuellement (mise à jour optimiste), mais après rechargement ou rafraîchissement, la quantité revient à l'ancienne valeur. Les changements ne sont pas sauvegardés en base de données.

## Structure de la base de données

### Table `inventaire_techniciens`
- `id` : ID unique de l'enregistrement
- `code_produit` : Code du produit (ex: "CORD-001")
- `technicien` : Nom du technicien (ex: "Nicolas", "Allan", "Jean-Philippe")
- `quantite_stock` : Quantité en stock (nombre entier)
- `emplacement` : Localisation du stock (ex: "Atelier", "Camion")
- `derniere_verification` : Date de dernière vérification
- **Contrainte unique** : `(code_produit, technicien, emplacement)` - un seul enregistrement par combinaison

### Table `transactions_inventaire`
- Enregistre toutes les transactions (ajouts, retraits, ajustements)
- Liée à `inventaire_techniciens` via `inventaire_id`

## Flux actuel de mise à jour

### Frontend (`TechniciensInventaireTable.jsx` et `InventaireDashboard.jsx`)

1. **Mise à jour optimiste** : L'UI est mise à jour immédiatement
2. **Debounce** : Attente de 500ms après la dernière modification
3. **Appel API** : `POST /api/inventaire/stock` avec :
   ```json
   {
     "code_produit": "CORD-001",
     "technicien": "Nicolas",  // Nom complet, pas username
     "quantite_stock": 15,     // Nouvelle quantité absolue
     "type_transaction": "ajustement",
     "motif": "Ajustement manuel depuis interface"
   }
   ```
4. **Rechargement** : Après succès, `loadInventory()` est appelé pour recharger depuis la DB

### Backend (`api/inventaire.py` - endpoint `POST /stock`)

1. **Récupération quantité actuelle** :
   - Cherche avec filtres : `code_produit`, `technicien`, `emplacement="Atelier"`
   - Si pas trouvé, cherche sans `emplacement` (compatibilité)
2. **Calcul ajustement** : `quantite_ajustement = nouvelle_quantite - quantite_actuelle`
3. **Appel `update_stock()`** : Passe l'ajustement (delta) à `SupabaseStorage.update_stock()`

### Backend (`core/supabase_storage.py` - méthode `update_stock()`)

1. **Récupération inventaire actuel** : Cherche avec `code_produit`, `technicien`, `emplacement`
2. **Calcul nouveau stock** : `nouveau_stock = stock_actuel + quantite_ajustement`
3. **UPDATE ou INSERT** :
   - Si `inventaire_id` existe → `UPDATE` via PATCH avec `upsert=False`
   - Sinon → `INSERT` via POST avec `upsert=True`
4. **Enregistrement transaction** : Crée une entrée dans `transactions_inventaire`

### Backend (`core/supabase_storage.py` - méthode `update_data()`)

1. **Mode UPDATE** (`upsert=False`) :
   - Utilise PATCH : `/{table}?id=eq.{id_value}`
   - Requiert que `id` soit présent dans `data`
2. **Mode INSERT/UPSERT** (`upsert=True`) :
   - Pour `inventaire_techniciens` sans `id` : Utilise `on_conflict=code_produit,technicien,emplacement`
   - Sinon : Utilise POST avec `Prefer: resolution=merge-duplicates`

## Problèmes identifiés potentiels

### 1. Mapping username → nom complet
Le frontend envoie le **nom complet** ("Nicolas", "Allan", "Jean-Philippe") mais utilise des **usernames** ("nicolas", "allan", "jeanphilippe") en interne. Il faut vérifier que le mapping est cohérent partout.

### 2. Contrainte unique et emplacement
La contrainte unique est `(code_produit, technicien, emplacement)`. Si l'API cherche avec `emplacement="Atelier"` mais que l'enregistrement existe avec un autre emplacement (ou NULL), la mise à jour échouera silencieusement.

### 3. Logique UPDATE vs INSERT
Si `inventaire_id` n'est pas trouvé lors de la recherche initiale dans `update_stock()`, mais qu'un enregistrement existe réellement (avec un autre emplacement ou une recherche qui a échoué), l'INSERT avec `upsert=True` pourrait créer un doublon ou ne pas mettre à jour le bon enregistrement.

### 4. Race conditions
Si plusieurs modifications rapides sont faites, les requêtes peuvent se chevaucher et écraser les modifications précédentes.

### 5. Erreurs silencieuses
Si `update_data()` retourne `False` ou échoue, l'erreur pourrait ne pas être correctement propagée au frontend, donnant l'impression que la sauvegarde a réussi.

## Tâches à accomplir

### Tâche 1 : Vérifier et corriger le mapping technicien
- S'assurer que le mapping `username → nom complet` est cohérent partout
- Vérifier que l'API reçoit bien le nom complet et que la recherche dans la DB utilise le même format
- Ajouter des logs pour tracer les valeurs envoyées et reçues

### Tâche 2 : Améliorer la recherche d'inventaire existant
- Dans `POST /stock`, améliorer la recherche pour gérer tous les cas :
  - Chercher avec `emplacement="Atelier"` d'abord
  - Si pas trouvé, chercher sans filtre `emplacement` (pour compatibilité)
  - Si toujours pas trouvé, chercher avec `emplacement IS NULL`
- S'assurer que l'`inventaire_id` récupéré correspond bien à l'enregistrement à mettre à jour

### Tâche 3 : Corriger la logique UPDATE/INSERT
- Dans `update_stock()`, s'assurer que :
  - Si un enregistrement existe (même avec un autre emplacement), on fait un UPDATE, pas un INSERT
  - Utiliser la contrainte unique correctement pour l'UPSERT
  - Gérer le cas où plusieurs enregistrements existent (devrait être impossible avec la contrainte, mais à vérifier)

### Tâche 4 : Améliorer la gestion d'erreurs
- S'assurer que toutes les erreurs sont correctement propagées au frontend
- Ajouter des logs détaillés à chaque étape pour le debugging
- Retourner des messages d'erreur clairs si la mise à jour échoue

### Tâche 5 : Gérer les race conditions
- Implémenter un verrou ou une sérialisation des requêtes pour éviter les conflits
- Ou utiliser des transactions pour garantir la cohérence

### Tâche 6 : Vérifier la contrainte unique en base
- Vérifier que la contrainte unique `(code_produit, technicien, emplacement)` existe bien en base
- Si elle n'existe pas, la créer
- S'assurer qu'il n'y a pas de doublons existants qui empêchent les mises à jour

## Fichiers à modifier

1. **`api/inventaire.py`** (lignes ~290-355)
   - Endpoint `POST /stock`
   - Améliorer la recherche d'inventaire existant
   - Ajouter des logs détaillés
   - Améliorer la gestion d'erreurs

2. **`core/supabase_storage.py`** (lignes ~475-566)
   - Méthode `update_stock()`
   - Améliorer la logique UPDATE/INSERT
   - Gérer tous les cas d'emplacement

3. **`core/supabase_storage.py`** (lignes ~237-320)
   - Méthode `update_data()`
   - Améliorer la gestion de la contrainte unique pour `inventaire_techniciens`
   - Améliorer les messages d'erreur

4. **`frontend/src/components/TechniciensInventaireTable.jsx`** (lignes ~132-210)
   - Fonction `updateQuantity()`
   - Vérifier le mapping username → nom complet
   - Améliorer la gestion d'erreurs côté frontend

5. **`frontend/src/components/InventaireDashboard.jsx`** (lignes ~248-297)
   - Fonction `updateQuantity()`
   - Vérifier le mapping username → nom complet
   - Améliorer la gestion d'erreurs côté frontend

## Script de diagnostic

Créer un script `scripts/diagnostic_inventaire_quantites.py` qui :
1. Liste tous les enregistrements `inventaire_techniciens` avec leurs valeurs
2. Vérifie s'il y a des doublons (violation de contrainte unique)
3. Teste une mise à jour de quantité et vérifie qu'elle persiste
4. Compare les valeurs dans la DB avec ce qui est affiché dans l'UI

## Critères de succès

✅ **Les quantités modifiées dans l'interface persistent en base de données**

✅ **Après rechargement de la page, les quantités modifiées sont toujours visibles**

✅ **Aucune erreur silencieuse** - toutes les erreurs sont loggées et propagées

✅ **Pas de doublons** - la contrainte unique est respectée

✅ **Gestion correcte des emplacements** - les mises à jour fonctionnent même si l'emplacement diffère

✅ **Logs détaillés** pour faciliter le debugging futur

## Exemple de requête SQL pour vérifier

```sql
-- Vérifier les doublons (devrait retourner 0)
SELECT code_produit, technicien, emplacement, COUNT(*) as count
FROM inventaire_techniciens
GROUP BY code_produit, technicien, emplacement
HAVING COUNT(*) > 1;

-- Vérifier la contrainte unique existe
SELECT constraint_name, constraint_type
FROM information_schema.table_constraints
WHERE table_name = 'inventaire_techniciens'
  AND constraint_type = 'UNIQUE';

-- Vérifier les dernières transactions
SELECT * 
FROM transactions_inventaire
ORDER BY created_at DESC
LIMIT 20;
```

## Notes importantes

- **Les noms de techniciens doivent être exacts** : "Nicolas", "Allan", "Jean-Philippe" (avec majuscules)
- **L'emplacement par défaut est "Atelier"** mais peut varier
- **La contrainte unique est critique** - elle doit exister et être respectée
- **Les transactions doivent être enregistrées** pour la traçabilité
- **Les erreurs doivent être visibles** - ne pas retourner "success" si la mise à jour a échoué

## Code de référence

Le code utilise :
- `SupabaseStorage` pour accéder à la base de données
- `storage.get_data()` pour récupérer les données
- `storage.update_data()` pour sauvegarder
- `storage.update_stock()` pour ajuster les stocks
- Format de technicien : nom complet ("Nicolas", "Allan", "Jean-Philippe")
- Format de quantité : nombre entier (`int`)

---

**Objectif final** : Les modifications de quantités dans l'interface doivent persister correctement en base de données, et rester visibles après rechargement de la page.
