# Vues SQL Gazelle - Installation réussie ✅

## Vues créées

### 1. `gazelle_client_timeline` (MATERIALIZED VIEW)
Combine les timeline entries de 2 sources:
- **CLIENT**: Entrées liées directement au client (`entity_type = 'CLIENT'`)
- **PIANO**: Entrées liées via piano (`entity_type = 'PIANO'`)

**Colonnes clés:**
- `client_external_id`: ID du client
- `piano_id`, `piano_external_id`, `piano_make`, etc.: Info piano (NULL pour CLIENT)
- `source_type`: 'CLIENT' ou 'PIANO'
- `occurred_at`: Date de l'événement

**Index créés:**
- `idx_client_timeline_client_ext`: Recherche par client
- `idx_client_timeline_piano_ext`: Recherche par piano
- `idx_client_timeline_occurred`: Tri par date
- `idx_client_timeline_search`: Recherche full-text
- `idx_client_timeline_source`: Filtre par type

### 2. `gazelle_client_search` (VIEW)
Vue de recherche combinant clients ET contacts (pour éviter confusion)

**Sources (UNION):**
- **contact**: Personnes avec leur client parent
- **client**: Entreprises

**Colonnes clés:**
- `source_type`: 'contact' ou 'client' (pour distinguer)
- `display_name`: Nom affiché
- `client_external_id`: ID du client
- `piano_count`: Nombre de pianos
- `timeline_count`: Nombre d'entrées timeline

### 3. `gazelle_piano_list` (VIEW)
Liste des pianos avec leur client

**Colonnes clés:**
- `piano_id`, `piano_external_id`
- `make`, `model`, `serial_number`, etc.
- `client_external_id`, `company_name`
- `timeline_count`: Nombre d'entrées timeline pour ce piano
- `primary_contact`: Nom du contact principal

## Fonction utilitaire

### `refresh_gazelle_views()`
Rafraîchit la vue matérialisée (à appeler après import de données)

```sql
SELECT refresh_gazelle_views();
```

## Tests de validation

Voir: `TEST_ALL_VIEWS.sql`

## Fichiers SQL

- **Installation complète**: `DROP_AND_CREATE.sql`
- **Vues supplémentaires**: `CREATE_OTHER_VIEWS.sql`
- **Tests**: `TEST_ALL_VIEWS.sql`

## Exemple d'utilisation

```sql
-- Timeline pour un client
SELECT * FROM gazelle_client_timeline
WHERE client_external_id = 'cli_Pc3O0Ybqvve64xcF'
ORDER BY occurred_at DESC NULLS LAST;

-- Rechercher "Monique"
SELECT * FROM gazelle_client_search
WHERE search_name ILIKE '%Monique%';

-- Pianos d'un client
SELECT * FROM gazelle_piano_list
WHERE client_external_id = 'cli_Pc3O0Ybqvve64xcF';
```

## Notes importantes

1. **Déduplication client/contact**: La vue `client_search` retourne à la fois le client ET le contact. Utiliser `source_type` pour filtrer.

2. **occurred_at NULL**: Beaucoup d'entrées ont `occurred_at = NULL`. Utiliser `ORDER BY occurred_at DESC NULLS LAST` pour les mettre à la fin.

3. **Refresh nécessaire**: Après import de données, appeler `refresh_gazelle_views()` pour mettre à jour la vue matérialisée.

## Colonnes vérifiées

Toutes les colonnes utilisées ont été vérifiées dans `information_schema.columns`:
- ✅ `gazelle_clients`: city, postal_code (pas d'adresse complète)
- ✅ `gazelle_contacts`: first_name, last_name, client_external_id
- ✅ `gazelle_pianos`: make (pas brand), serial_number
- ✅ `gazelle_timeline_entries`: occurred_at, entity_type, entity_id
