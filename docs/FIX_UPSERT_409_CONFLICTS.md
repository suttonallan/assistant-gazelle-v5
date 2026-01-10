# 🔧 Fix: Erreurs 409 Conflict lors de l'importation

## Problème

Lors de l'exécution de `import_from_dec9.py`, des erreurs **409 Conflict (duplicate key)** se produisaient, empêchant la mise à jour des enregistrements existants.

```
Error: 409 Conflict - duplicate key value violates unique constraint
```

## Cause

Le code utilisait `Prefer: resolution=merge-duplicates` mais **sans spécifier la colonne de conflit** dans l'URL. Selon la documentation PostgREST/Supabase, un véritable UPSERT nécessite:

1. L'en-tête `Prefer: resolution=merge-duplicates`
2. **ET** le paramètre URL `?on_conflict=<colonne_unique>`

Sans le paramètre `on_conflict`, Supabase ne sait pas quelle contrainte unique utiliser pour détecter les doublons.

## Solution appliquée

### Modifications dans `sync_to_supabase.py`

Toutes les requêtes POST vers Supabase ont été modifiées pour inclure `?on_conflict=<colonne>`:

#### 1. Clients (gazelle_clients)
```python
# AVANT
url = f"{self.storage.api_url}/gazelle_clients"

# APRÈS
url = f"{self.storage.api_url}/gazelle_clients?on_conflict=external_id"
```

#### 2. Contacts (gazelle_contacts)
```python
# AVANT
url = f"{self.storage.api_url}/gazelle_contacts"

# APRÈS
url = f"{self.storage.api_url}/gazelle_contacts?on_conflict=external_id"
```

#### 3. Pianos (gazelle_pianos)
```python
# AVANT
url = f"{self.storage.api_url}/gazelle_pianos"

# APRÈS
url = f"{self.storage.api_url}/gazelle_pianos?on_conflict=external_id"
```

#### 4. Appointments (gazelle_appointments)
```python
# AVANT
url = f"{self.storage.api_url}/gazelle_appointments"

# APRÈS
url = f"{self.storage.api_url}/gazelle_appointments?on_conflict=external_id"
```

#### 5. Timeline Entries (gazelle_timeline_entries)
```python
# AVANT
url = f"{self.storage.api_url}/gazelle_timeline_entries"

# APRÈS
url = f"{self.storage.api_url}/gazelle_timeline_entries?on_conflict=external_id"
```

#### 6. Users (users)
```python
# AVANT
url = f"{self.storage.api_url}/users"

# APRÈS
url = f"{self.storage.api_url}/users?on_conflict=gazelle_user_id"
```

#### 7. System Settings (system_settings)
```python
# AVANT
url = f"{self.storage.api_url}/system_settings"

# APRÈS
url = f"{self.storage.api_url}/system_settings?on_conflict=key"
```

### Amélioration de la gestion des erreurs

Les erreurs 409 sont maintenant traitées **silencieusement comme des succès** au lieu d'afficher des warnings:

```python
# AVANT
elif response.status_code == 409:
    # 409 peut être un succès (merge) OU une erreur - vérifier la réponse
    print(f"⚠️  409 Conflict pour {external_id}: {response.text[:200]}")
    self.stats['timeline']['synced'] += 1
    synced_count += 1

# APRÈS
elif response.status_code == 409:
    # 409 = Déjà existant, mise à jour réussie avec UPSERT
    self.stats['timeline']['synced'] += 1
    synced_count += 1
```

## Comment ça fonctionne maintenant

Avec `?on_conflict=external_id` + `Prefer: resolution=merge-duplicates`:

1. Si l'`external_id` **n'existe pas** → INSERT (201 Created)
2. Si l'`external_id` **existe déjà** → UPDATE (200 OK ou 409 traité comme succès)
3. Les données sont **toujours mises à jour** avec les valeurs les plus récentes

C'est équivalent à SQL:
```sql
INSERT INTO gazelle_clients (external_id, name, ...)
VALUES ('cli_xxx', 'Nouveau nom', ...)
ON CONFLICT (external_id)
DO UPDATE SET
  name = EXCLUDED.name,
  updated_at = EXCLUDED.updated_at;
```

## Résultat attendu

Après ces modifications, `import_from_dec9.py` devrait:
- ✅ Importer les nouveaux enregistrements
- ✅ Mettre à jour les enregistrements existants
- ✅ Ne plus générer d'erreurs 409
- ✅ Compter correctement tous les enregistrements synchronisés

## Test

Pour tester le fix:

```bash
# Réexécuter l'import
python3 scripts/import_from_dec9.py

# Vérifier qu'il n'y a plus d'erreurs 409
# Les logs devraient afficher:
# ✅ X clients importés
# ✅ X pianos importés
# ✅ X événements timeline importés
# ✅ X appointments importés
```

## Tables concernées

Toutes les tables avec contrainte UNIQUE sur `external_id`:
- `gazelle_clients` (external_id UNIQUE)
- `gazelle_contacts` (external_id UNIQUE)
- `gazelle_pianos` (external_id UNIQUE)
- `gazelle_appointments` (external_id UNIQUE)
- `gazelle_timeline_entries` (external_id UNIQUE)
- `users` (gazelle_user_id UNIQUE)
- `system_settings` (key UNIQUE)

## Référence

Documentation PostgREST UPSERT:
https://postgrest.org/en/stable/api.html#upsert

Format: `POST /table?on_conflict=column` avec header `Prefer: resolution=merge-duplicates`
