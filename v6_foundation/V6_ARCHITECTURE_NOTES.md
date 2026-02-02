# Notes pour l'Architecture V6

## Gestion des Roles Utilisateurs

### Probleme actuel (V5)
- Les alertes sont envoyees a tous les utilisateurs assignes dans Gazelle
- Pas de distinction entre technicien, assistant, admin
- Louise (assistante) recoit des alertes destinees aux techniciens

### Solution V6
- Utiliser un systeme de roles coherent pour filtrer les alertes
- Champs suggeres dans la table `users`:
  - `role`: enum ('admin', 'technicien', 'assistant')
  - `is_technicien`: boolean (recoit alertes RV)
  - `is_assistant`: boolean (recoit relances Louise)
  - `receives_rv_alerts`: boolean (opt-in/opt-out explicite)

### Cas d'usage des alertes par role
| Type d'alerte | Admin | Technicien | Assistant |
|---------------|-------|------------|-----------|
| RV non confirme | Non | Oui | Non |
| Late Assignment | Non | Oui | Non |
| Relance vieux RV | Non | Non | Oui |
| Humidite critique | Oui | Oui | Non |

### Implementation suggeree
```python
# V6: Filtrer par role au lieu de GAZELLE_IDS hardcode
def get_technicians_for_alerts():
    """Retourne uniquement les utilisateurs avec role technicien."""
    return users.filter(
        is_technicien=True,
        receives_rv_alerts=True
    )
```

---

## Autres notes V6

### Inventaire
- Simplifier la cle unique: `(code_produit, technicien)` seulement
- Enlever `emplacement` completement
- Normalisation automatique des noms (Nick -> Nicolas)

### Institutions
- Table `institutions` avec discovery automatique depuis Gazelle
- Detection par mots-cles dans titre/location/description
- Support pour Vincent-d'Indy, Place des Arts, Orford, etc.

---
*Derniere mise a jour: 2026-02-02*
