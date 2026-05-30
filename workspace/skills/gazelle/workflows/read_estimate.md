# Workflow — Lire et analyser une soumission existante

## Recherche par numéro

```python
from app.modules.gazelle.estimates import get_estimate_by_number

estimate = get_estimate_by_number(11914)
# Utilise search: "11914" en interne, puis filtre node.number == 11914
```

Si le client v6 n'a pas accès à system_settings (anon key), utiliser le
client v5 avec la query directe :

```python
QUERY = """
query GetEstimateByNumber($search: String!) {
    allEstimates(first: 5, filters: {search: $search}) {
        nodes {
            id number notes estimatedOn expiresOn locale
            recommendedTierTotal
            client { id defaultContact { firstName lastName } }
            piano { id make model year }
            allEstimateTiers {
                id sequenceNumber isPrimary notes subtotal taxTotal total
                allEstimateTierGroups {
                    id name sequenceNumber
                    allEstimateTierItems {
                        id name sequenceNumber amount quantity duration
                        type description isTaxable isTuning
                        subtotal taxTotal total
                        masterServiceItem { id }
                        taxes { taxId rate total }
                    }
                }
                allUngroupedEstimateTierItems {
                    id name amount quantity isTaxable subtotal total
                    masterServiceItem { id }
                }
            }
        }
    }
}
"""
```

## Recherche par client

Utiliser `filters: {clientId: "cli_xxx"}` dans `allEstimates`.

## Analyse recommandée

Quand on lit une soumission existante pour la reconstruire ou l'évaluer :

1. **Identifier les frictions** :
   - Items à 0 $ qui devraient être dans la description → friction #2
   - Tier 2 qui retire des items de Tier 1 → friction #1
   - Avertissements en items au lieu des notes → friction #3
   - URLs tronquées dans les descriptions
   - Descriptions génériques héritées du MSL sans personnalisation

2. **Cartographier les MSL** : noter les `masterServiceItem.id` de chaque item
   pour retrouver le bundle correspondant s'il existe

3. **Vérifier l'inclusion des tiers** : si 2+ tiers, confirmer que
   chaque tier étendu ⊇ le tier de base

## Filtres disponibles sur allEstimates

```
clientId, pianoId, search, createdGet/Let, expiresGet/Let,
archived, expired, primaryTierTotalGet/Let, anyTierTotalGet/Let,
recommendedTierTotalGet/Let, createdById, assignedToId, pianoType,
anyTags, allTags, excludeTags, region, municipality, postCode
```

Note : PAS de `number` — utiliser `search` (String).
