# Comment Utiliser le Système de Référence Automatique

## 🎯 Objectif

Le système de référence automatique garantit que:
1. **La référence est consultée** avant chaque action
2. **La référence est mise à jour** après chaque succès
3. **Plus besoin de deviner** - tout est documenté et vérifié

## 📚 Utilisation dans les Scripts

### Exemple 1: Mapping des Techniciens

```python
from core.reference_manager import get_reference_manager

ref = get_reference_manager()

# S'assurer que la référence est consultée
ref.ensure_reference_consulted("mapping_techniciens")

# Récupérer le nom d'un technicien
technicien_nom = ref.get_technicien_name("usr_xxx")
if not technicien_nom:
    print("⚠️  Technicien non trouvé dans la référence")
    # Demander à l'utilisateur ou utiliser une valeur par défaut

# Après un succès, mettre à jour
ref.update_after_success("technicien_mapping", {
    "usr_new_id": "Nouveau Technicien"
})
```

### Exemple 2: Validation des Colonnes

```python
from core.reference_manager import get_reference_manager

ref = get_reference_manager()

# Vérifier qu'une colonne existe
if not ref.validate_column("produits_catalogue", "code_produit"):
    raise ValueError("Colonne code_produit n'existe pas!")

# Récupérer toutes les colonnes valides
colonnes = ref.get_valid_columns("produits_catalogue")
print(f"Colonnes valides: {colonnes}")
```

## 🔄 Workflow Automatique

### Avant une Action

1. **Consulter la référence:**
   ```python
   ref.ensure_reference_consulted("action_name")
   ```

2. **Récupérer les informations nécessaires:**
   ```python
   mapping = ref.get_technicien_name(id)
   colonnes = ref.get_valid_columns(table)
   ```

3. **Valider avant d'agir:**
   ```python
   if not ref.validate_column(table, column):
       raise ValueError(f"Colonne {column} invalide!")
   ```

### Après un Succès

1. **Mettre à jour la référence:**
   ```python
   ref.update_after_success("update_type", {
       "new_info": "value"
   })
   ```

2. **La référence est automatiquement sauvegardée**

## 📝 Types de Mises à Jour

### `technicien_mapping`
Met à jour le mapping des techniciens:
```python
ref.update_after_success("technicien_mapping", {
    "usr_xxx": "Nom Technicien"
})
```

### `column_info`
Met à jour les informations sur les colonnes:
```python
ref.update_after_success("column_info", {
    "table_name": "produits_catalogue",
    "columns": ["code_produit", "nom", ...]
})
```

## 🎨 Intégration dans les Scripts Existants

### Script de Mapping

```python
# AVANT
MAPPING_TECHNICIENS = {
    "usr_xxx": "Allan",  # Deviné?
}

# APRÈS
from core.reference_manager import get_reference_manager
ref = get_reference_manager()
ref.ensure_reference_consulted("mapping_techniciens")

MAPPING_TECHNICIENS = {
    "usr_xxx": ref.get_technicien_name("usr_xxx") or "Allan",
}
```

### Script d'Import

```python
# AVANT
query = "SELECT product_id, name FROM Products"  # product_id existe?

# APRÈS
from core.reference_manager import get_reference_manager
ref = get_reference_manager()

# Vérifier les colonnes
if not ref.validate_column("produits_catalogue", "gazelle_product_id"):
    # Utiliser une colonne alternative
    pass
```

## 🔍 Cache

Le système utilise un cache (`.reference_cache.json`) pour:
- Accélérer les consultations répétées
- Mémoriser les informations apprises
- Éviter de re-lire le fichier à chaque fois

**Le cache est automatiquement mis à jour** après chaque succès.

## ⚠️ Règles Importantes

1. **TOUJOURS** appeler `ensure_reference_consulted()` avant une action
2. **TOUJOURS** utiliser `get_technicien_name()` au lieu de deviner
3. **TOUJOURS** valider les colonnes avec `validate_column()`
4. **TOUJOURS** mettre à jour après un succès avec `update_after_success()`

## 📊 Exemple Complet

```python
from core.reference_manager import get_reference_manager

def import_inventaire():
    ref = get_reference_manager()
    
    # 1. Consulter la référence
    ref.ensure_reference_consulted("import_inventaire")
    
    # 2. Récupérer les informations
    technicien_id = "usr_xxx"
    technicien_nom = ref.get_technicien_name(technicien_id)
    
    if not technicien_nom:
        raise ValueError(f"Technicien {technicien_id} non trouvé dans la référence!")
    
    # 3. Valider les colonnes
    if not ref.validate_column("inventaire_techniciens", "technicien"):
        raise ValueError("Colonne technicien invalide!")
    
    # 4. Effectuer l'action
    # ... import ...
    
    # 5. Mettre à jour après succès
    if success:
        ref.update_after_success("technicien_mapping", {
            technicien_id: technicien_nom
        })
```


