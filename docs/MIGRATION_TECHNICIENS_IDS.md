# Migration des IDs de Techniciens - Place des Arts

## Date: 2025-12-26

## Problème Résolu

Le système utilisait des IDs de techniciens **différents** dans Place des Arts vs Gazelle pour les mêmes personnes:

| Technicien | ID Place des Arts (ancien) | ID Gazelle (correct) |
|------------|----------------------------|----------------------|
| Allan      | `usr_allan`                | `usr_ofYggsCDt2JAVeNP` |
| Nicolas    | `usr_U9E5bLxrFiXqTbE8`     | `usr_HcCiFk7o0vZ9xAI0` |

### Impact du Problème

1. **Validation échouée**: La validation de cohérence ne trouvait pas les RV Gazelle car elle cherchait avec les mauvais IDs
2. **Interface incohérente**: L'interface Place des Arts assignait avec des IDs qui n'existaient pas dans Gazelle
3. **Erreurs "Failed to fetch"**: Tentatives de mise à jour avec des IDs invalides

## Solution Implémentée

### 1. Script de Migration

Créé: `/assistant-v6/modules/assistant/services/migrate_pda_technician_ids.py`

Ce script:
- ✅ Identifie toutes les demandes PDA avec anciens IDs
- ✅ Crée un mapping clair ancien → nouveau
- ✅ Supporte dry-run pour tester avant d'appliquer
- ✅ Affiche un rapport détaillé de la migration

### 2. Exécution de la Migration

```bash
# Test (dry-run)
python3 migrate_pda_technician_ids.py

# Application réelle
python3 migrate_pda_technician_ids.py --live
```

**Résultat:**
- ✅ 12 demandes migrées avec succès
- ❌ 0 échecs

### 3. Mise à Jour de l'Interface

Fichier: `/frontend/src/components/place_des_arts/PlaceDesArtsDashboard.jsx`

**Avant (ligne 176-180):**
```javascript
const techMap = {
  '1': 'usr_allan',              // ❌ ID PDA invalide
  '2': 'usr_tndhXmnT0iakT4HF',   // ✅ OK
  '3': 'usr_U9E5bLxrFiXqTbE8',   // ❌ ID PDA invalide
}
```

**Après:**
```javascript
const techMap = {
  '1': 'usr_ofYggsCDt2JAVeNP',  // ✅ Allan (ID Gazelle)
  '2': 'usr_tndhXmnT0iakT4HF',  // ✅ Timo (ID Gazelle)
  '3': 'usr_HcCiFk7o0vZ9xAI0',  // ✅ Patrick/Nicolas (ID Gazelle)
}
```

## Vérification Post-Migration

### Base de Données

**Avant:**
```
usr_U9E5bLxrFiXqTbE8: 10 requêtes  ❌ (ID PDA invalide)
usr_allan: 2 requêtes               ❌ (ID PDA invalide)
```

**Après:**
```
usr_HcCiFk7o0vZ9xAI0: 10 requêtes  ✅ (ID Gazelle valide)
usr_ofYggsCDt2JAVeNP: 2 requêtes   ✅ (ID Gazelle valide)
```

### Validation de Cohérence

**Avant migration:**
```
⚠️  Assignés SANS RV: 12  (faux positifs dus aux mauvais IDs)
```

**Après migration:**
```
✅ Assignés avec RV: 12
⚠️  Assignés SANS RV: 0
✅ 100% de cohérence!
```

## Référence des IDs Techniciens

Pour référence future, voici tous les IDs de techniciens Gazelle valides:

| Nom | ID Gazelle | Nb RV dans Gazelle |
|-----|------------|--------------------|
| Nicolas/Patrick | `usr_HcCiFk7o0vZ9xAI0` | 227 RV |
| Allan | `usr_ofYggsCDt2JAVeNP` | 157 RV |
| Timo | `usr_tndhXmnT0iakT4HF` | 79 RV |
| (Autre) | `usr_ReUSmIJmBF86ilY1` | 146 RV |
| (Autre) | `usr_QmEpdeM2xMgZVkDS` | 22 RV |

## Prochaines Étapes

1. ✅ Migration complétée
2. ✅ Interface mise à jour
3. ✅ Validation confirmée
4. 🔄 Tester l'assignation d'un technicien dans l'interface
5. 🔄 Vérifier que "Failed to fetch" est résolu

## Notes Importantes

- **NE JAMAIS** utiliser les anciens IDs (`usr_allan`, `usr_U9E5bLxrFiXqTbE8`)
- **TOUJOURS** utiliser les IDs Gazelle (format `usr_` + 16 caractères)
- Le script de migration peut être relancé en mode dry-run à tout moment pour vérifier qu'il n'y a plus d'anciens IDs
