# Prompt Système pour Consultation Automatique

## 🎯 Pour les Assistants IA (Claude, Cursor, etc.)

**AVANT TOUTE RÉPONSE OU MODIFICATION, TOUJOURS:**

### 1. Consulter la Référence

```markdown
Je dois d'abord consulter docs/REFERENCE_COMPLETE.md pour:
- Le mapping des techniciens (IDs → noms)
- Les noms de colonnes valides
- Le schéma des tables
- Les règles d'import
```

### 2. Utiliser ReferenceManager

Dans tout script Python, utiliser:
```python
from core.reference_manager import get_reference_manager
ref = get_reference_manager()
ref.ensure_reference_consulted("action_name")
```

### 3. Valider Avant d'Agir

- Vérifier les colonnes avec `ref.validate_column()`
- Récupérer les mappings avec `ref.get_technicien_name()`
- Ne jamais deviner

### 4. Mettre à Jour Après Succès

```python
ref.update_after_success("update_type", data)
```

## 📋 Checklist Automatique

Avant chaque modification:
- [ ] J'ai lu `docs/REFERENCE_COMPLETE.md`
- [ ] J'ai utilisé `ReferenceManager` pour valider
- [ ] Je n'ai pas deviné de mapping de technicien
- [ ] Je n'ai pas inventé de nom de colonne
- [ ] J'ai mis à jour la référence après succès

## 🔄 Workflow Imposé

1. **Lire** → `docs/REFERENCE_COMPLETE.md`
2. **Valider** → `ReferenceManager.validate_column()` / `get_technicien_name()`
3. **Agir** → Effectuer la modification
4. **Mettre à jour** → `ReferenceManager.update_after_success()`

## ⚠️ Interdictions

- ❌ Deviner le mapping des techniciens
- ❌ Inventer des noms de colonnes
- ❌ Utiliser des colonnes sans vérifier
- ❌ Ignorer la référence




