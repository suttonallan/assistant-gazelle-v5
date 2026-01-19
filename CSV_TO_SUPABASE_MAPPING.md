# 📊 Mapping CSV → Supabase - Timeline Import v6

## Étape 1 : Analyse

### Colonnes CSV (13 colonnes)
1. **Client ID** - `cli_xxxxx` (ID Gazelle du client)
2. **Type** - Type d'événement (email, log, event, etc.)
3. **Timestamp** - Date/heure au format `2024-11-11 06:05:22 UTC`
4. **Comment** - Commentaire/description
5. **System Message** - Message système
6. **Piano Token** - Token du piano (peut être vide)
7. **Piano Type** - Type de piano
8. **Piano Make** - Marque du piano
9. **Piano Model** - Modèle du piano
10. **Piano Serial Number** - Numéro de série
11. **Piano Location** - Localisation du piano
12. **Piano Year** - Année du piano
13. **Created By** - Créateur (nom d'utilisateur)

### Colonnes Supabase (20 colonnes)
- `id` (auto-généré)
- `external_id` ⚠️ **CRITIQUE** - ID unique Gazelle (manquant dans CSV)
- `client_external_id` ✅
- `entry_type` ✅ (mappé depuis Type)
- `title` ✅ (mappé depuis System Message)
- `description` ✅ (mappé depuis Comment)
- `entry_date` ✅ (mappé depuis Timestamp)
- `occurred_at` ✅ (mappé depuis Timestamp)
- `entity_type` ✅ (déduit)
- `entity_id` ✅ (mappé depuis Client ID)
- `event_type` ✅ (mappé depuis Type)
- `piano_id` ⚠️ **MANQUANT** - Nécessite lookup depuis Piano Token
- `user_id` ⚠️ **MANQUANT** - Nécessite lookup depuis Created By
- `client_id` ✅ (mappé depuis Client ID)
- `invoice_id` (optionnel)
- `estimate_id` (optionnel)
- `created_by` ✅ (mappé depuis Created By)
- `metadata` (optionnel, peut contenir infos piano)
- `created_at` (auto-généré)
- `updated_at` (auto-généré)

## Étape 2 : Plan de Mappage

| Colonne CSV | Colonne Supabase | Transformation | Notes |
|------------|------------------|----------------|-------|
| `Client ID` | `client_external_id` | Direct | ID Gazelle du client |
| `Client ID` | `entity_id` | Direct | ID de l'entité (client) |
| `Client ID` | `client_id` | Direct | Même valeur |
| `Type` | `entry_type` | Mapping | email→EMAIL, log→LOG, event→EVENT, etc. |
| `Type` | `event_type` | Direct | Type d'événement |
| `Timestamp` | `entry_date` | Parse + Format | `2024-11-11 06:05:22 UTC` → ISO format |
| `Timestamp` | `occurred_at` | Parse + Format | Même transformation |
| `Comment` | `description` | Direct | Description de l'événement |
| `System Message` | `title` | Direct | Titre/résumé |
| `Created By` | `created_by` | Direct | Nom d'utilisateur |
| `Piano Token` | `piano_id` | **LOOKUP REQUIS** | Chercher dans `gazelle_pianos` par token |
| `Piano Token` | `metadata` | JSON | Stocker infos piano si token présent |
| - | `external_id` | **GÉNÉRER** | Format: `tle_{hash}` ou `tle_{timestamp}_{client_id}` |
| - | `entity_type` | **DÉDUIRE** | "CLIENT" (toujours pour ce CSV) |

## ⚠️ Données Critiques Manquantes

### 1. **external_id** (CRITIQUE)
- **Problème**: Pas présent dans le CSV
- **Solution**: Générer un ID unique basé sur:
  - `{Type}_{Timestamp}_{Client ID}_{hash(Comment+System Message)}`
  - Format: `tle_{hash}` pour éviter les collisions

### 2. **piano_id** (IMPORTANT)
- **Problème**: CSV contient `Piano Token` mais pas `piano_id` Supabase
- **Solution**: 
  - Lookup dans `gazelle_pianos` par `external_id` = Piano Token
  - Si non trouvé, laisser `null`

### 3. **user_id** (OPTIONNEL)
- **Problème**: CSV contient `Created By` (nom) mais pas `user_id`
- **Solution**:
  - Lookup dans `users` par `first_name` + `last_name`
  - Si non trouvé, laisser `null` (pas critique)

## 📅 Format des Dates

**Format CSV**: `2024-11-11 06:05:22 UTC`
**Format Supabase**: ISO 8601 avec timezone: `2024-11-11T06:05:22+00:00`

**Transformation**:
```python
# CSV: "2024-11-11 06:05:22 UTC"
# → Parse: datetime.strptime(ts, "%Y-%m-%d %H:%M:%S UTC")
# → Convert: dt.replace(tzinfo=timezone.utc)
# → Supabase: dt.isoformat() → "2024-11-11T06:05:22+00:00"
```

## 🔄 Mapping des Types

| Type CSV | entry_type Supabase | Notes |
|----------|---------------------|-------|
| `email` | `EMAIL` | Événement email |
| `log` | `LOG` | Log système |
| `event` | `EVENT` | Événement général |
| `appointment` | `APPOINTMENT` | Rendez-vous |
| `invoice` | `INVOICE` | Facture |
| `service` | `SERVICE_ENTRY_MANUAL` | Entrée de service manuelle |
| `measurement` | `PIANO_MEASUREMENT` | Mesure de piano |

## ✅ Validation Requise

1. **Vérifier les doublons**: Utiliser `external_id` généré pour éviter les doublons
2. **Valider les dates**: S'assurer que toutes les dates sont valides
3. **Lookup piano_id**: Vérifier que les Piano Tokens existent dans `gazelle_pianos`
4. **Lookup user_id**: Optionnel, mais améliorer la qualité des données
