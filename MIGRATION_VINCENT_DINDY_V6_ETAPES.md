# Migration Vincent d'Indy vers V6 - Étapes Finales

**Date:** 2025-12-30
**Status:** ⏳ En attente de migration Supabase

---

## 📊 Situation Actuelle

### ✅ Travail Complété

1. **Schema GraphQL Introspection** ✅
   - Fichier généré: `GAZELLE_SCHEMA_REFERENCE.md`
   - Méthode de filtrage trouvée: `allPianos(filters: { clientId: "..." })`
   - Client ID Vincent d'Indy: `cli_9UMLkteep8EsISbG`

2. **Script de Réconciliation** ✅
   - Fichier: [`scripts/reconcile_csv_with_gazelle.py`](scripts/reconcile_csv_with_gazelle.py)
   - Rapport généré: [`rapport_reconciliation_vincent_dindy.md`](rapport_reconciliation_vincent_dindy.md)
   - Résultats:
     - 89 pianos dans CSV ET Gazelle
     - 30 pianos UNIQUEMENT dans Gazelle (5 actifs, 25 inactifs)
     - 4 pianos UNIQUEMENT dans CSV (probablement erreurs de numéro de série)

3. **Scripts de Migration SQL** ✅
   - Fichier: [`scripts/add_is_in_csv_column.sql`](scripts/add_is_in_csv_column.sql)
   - Ajoute colonne `is_in_csv` BOOLEAN à la table `vincent_dindy_piano_updates`

### ⏳ Travail en Attente

1. **Migration Supabase** (Étape 1 - REQUISE)
2. **Modification API** (Étape 2)
3. **Renommage CSV** (Étape 3)
4. **Tests** (Étape 4)
5. **Déploiement** (Étape 5)

---

## 🚀 Étapes à Suivre

### Étape 1: Migration Supabase (OBLIGATOIRE)

**Action:** Ajouter la colonne `is_in_csv` à la table Supabase

**Méthode:**

1. Ouvrir le Dashboard Supabase:
   ```
   https://supabase.com/dashboard/project/beblgzvmjqkcillmcavk/sql/new
   ```

2. Copier et exécuter ce SQL:
   ```sql
   -- Ajouter la colonne is_in_csv à la table vincent_dindy_piano_updates
   ALTER TABLE vincent_dindy_piano_updates
   ADD COLUMN IF NOT EXISTS is_in_csv BOOLEAN DEFAULT TRUE;

   -- Commentaire sur la colonne
   COMMENT ON COLUMN vincent_dindy_piano_updates.is_in_csv IS
   'Indique si le piano fait partie du CSV officiel Vincent d''Indy. TRUE = dans CSV, FALSE = trouvé uniquement dans Gazelle';

   -- Index pour les requêtes filtrées
   CREATE INDEX IF NOT EXISTS idx_vincent_dindy_is_in_csv
   ON vincent_dindy_piano_updates(is_in_csv);
   ```

3. Vérifier que la migration a réussi:
   ```bash
   python3 scripts/apply_is_in_csv_migration.py
   ```

4. Appliquer les flags de réconciliation:
   ```bash
   python3 scripts/reconcile_csv_with_gazelle.py --apply
   ```

**Résultat attendu:**
```
✅ 119 mises à jour appliquées
   - 89 pianos marqués is_in_csv=TRUE
   - 30 pianos marqués is_in_csv=FALSE
```

---

### Étape 2: Modifier l'API Vincent d'Indy

**Fichier:** [`api/vincent_dindy.py`](api/vincent_dindy.py)

**Changements requis:**

#### 2.1 Ajouter Constante Client ID

```python
# Client ID Vincent d'Indy dans Gazelle
VINCENT_DINDY_CLIENT_ID = "cli_9UMLkteep8EsISbG"
```

#### 2.2 Remplacer la fonction `get_pianos()`

**Ancienne approche:** CSV + Supabase overlay

**Nouvelle approche:** Gazelle API + Supabase overlay

```python
@router.get("/pianos", response_model=Dict[str, Any])
async def get_pianos(include_inactive: bool = False):
    """
    Récupère tous les pianos depuis Gazelle.

    Args:
        include_inactive: Si True, inclut les pianos hors CSV (is_in_csv=False)

    Architecture:
    - Gazelle API = Source de vérité (119 pianos total)
    - Filtre par défaut = is_in_csv=TRUE OU status=ACTIVE
    - Supabase = Modifications dynamiques + flags is_in_csv
    """
    try:
        import logging
        logging.info(f"🔍 Chargement des pianos depuis Gazelle (client: {VINCENT_DINDY_CLIENT_ID})")

        # 1. Charger TOUS les pianos depuis Gazelle
        api_client = get_api_client()

        if not api_client:
            raise HTTPException(status_code=500, detail="Client API Gazelle non disponible")

        query = """
        query GetVincentDIndyPianos($clientId: String!) {
          allPianos(first: 200, filters: { clientId: $clientId }) {
            nodes {
              id
              serialNumber
              make
              model
              location
              type
              status
              notes
              calculatedLastService
              calculatedNextService
              serviceIntervalMonths
            }
          }
        }
        """

        variables = {"clientId": VINCENT_DINDY_CLIENT_ID}
        result = api_client._execute_query(query, variables)
        gazelle_pianos = result.get("data", {}).get("allPianos", {}).get("nodes", [])

        logging.info(f"📋 {len(gazelle_pianos)} pianos chargés depuis Gazelle")

        # 2. Charger les modifications depuis Supabase (flags + overlays)
        storage = get_supabase_storage()
        supabase_updates = storage.get_all_piano_updates()

        logging.info(f"☁️  {len(supabase_updates)} modifications Supabase trouvées")

        # 3. FUSION: Transformer pianos Gazelle + appliquer overlays Supabase
        pianos = []

        for gz_piano in gazelle_pianos:
            gz_id = gz_piano['id']
            serial = gz_piano.get('serialNumber', gz_id)  # Fallback au gazelle_id si pas de serial

            # Trouver les updates Supabase (matcher par serial OU gazelle_id)
            updates = {}
            for piano_id, data in supabase_updates.items():
                if (piano_id == serial or
                    data.get('gazelle_id') == gz_id):
                    updates = data
                    break

            # Vérifier le flag is_in_csv
            is_in_csv = updates.get('is_in_csv', False)  # Par défaut False si pas dans Supabase

            # Filtrage: Par défaut, montrer seulement is_in_csv=TRUE OU status=ACTIVE
            if not include_inactive:
                if not is_in_csv and gz_piano.get('status') != 'ACTIVE':
                    continue  # Ignorer les pianos inactifs hors CSV

            # Construire l'objet piano
            piano = {
                "id": serial,  # Garder serial comme ID pour compatibilité frontend
                "gazelleId": gz_id,
                "local": gz_piano.get('location', ''),
                "piano": gz_piano.get('make', ''),
                "modele": gz_piano.get('model', ''),
                "serie": serial,
                "type": gz_piano.get('type', 'UPRIGHT')[0] if gz_piano.get('type') else 'D',  # 'GRAND' → 'G', 'UPRIGHT' → 'U'
                "usage": "",  # Pas disponible dans Gazelle
                "dernierAccord": gz_piano.get('calculatedLastService', ''),
                "prochainAccord": gz_piano.get('calculatedNextService', ''),
                "status": updates.get('status', 'normal'),
                "aFaire": updates.get('a_faire', ''),
                "travail": updates.get('travail', ''),
                "observations": updates.get('observations', gz_piano.get('notes', '')),
                "isInCsv": is_in_csv,  # Nouveau flag pour le frontend
                "gazelleStatus": gz_piano.get('status', 'UNKNOWN')  # Status Gazelle
            }

            pianos.append(piano)

        logging.info(f"✅ {len(pianos)} pianos retournés (include_inactive={include_inactive})")

        return {
            "pianos": pianos,
            "count": len(pianos),
            "source": "gazelle",
            "clientId": VINCENT_DINDY_CLIENT_ID
        }

    except Exception as e:
        import traceback
        error_detail = f"Erreur lors de la récupération des pianos: {str(e)}\n{traceback.format_exc()}"
        logging.error(f"❌ {error_detail}")
        raise HTTPException(status_code=500, detail=error_detail)
```

**Changements clés:**
- ✅ Charge depuis Gazelle au lieu du CSV
- ✅ Filtre par `clientId: "cli_9UMLkteep8EsISbG"`
- ✅ Respecte le flag `is_in_csv` depuis Supabase
- ✅ Par défaut: montre seulement `is_in_csv=TRUE` OU `status=ACTIVE`
- ✅ Paramètre optionnel `include_inactive` pour tout afficher

---

### Étape 3: Renommer le CSV (Backup)

**Action:** Archiver le CSV pour éviter qu'il soit utilisé par erreur

```bash
cd /Users/allansutton/Documents/assistant-gazelle-v5/api/data
mv pianos_vincent_dindy.csv pianos_vincent_dindy.csv.old
```

**Résultat:** Le CSV devient `.old` et ne sera plus chargé

---

### Étape 4: Tests

#### 4.1 Test Local

```bash
# Démarrer l'API locale
python3 -m uvicorn api.main:app --reload --port 8000
```

```bash
# Tester l'endpoint
curl http://localhost:8000/vincent-dindy/pianos | python3 -m json.tool
```

**Vérifications:**
- ✅ Retourne ~94 pianos (89 du CSV + 5 actifs hors CSV)
- ✅ Chaque piano a `gazelleId` (format `ins_xxxxx`)
- ✅ Champ `isInCsv` présent (true/false)
- ✅ `dernierAccord` peuplé depuis Gazelle

#### 4.2 Test avec Pianos Inactifs

```bash
curl "http://localhost:8000/vincent-dindy/pianos?include_inactive=true" | python3 -m json.tool
```

**Vérifications:**
- ✅ Retourne 119 pianos (tous les pianos Gazelle)
- ✅ Pianos avec `isInCsv=false` et `gazelleStatus=INACTIVE` inclus

#### 4.3 Test Frontend

```bash
cd frontend
npm run dev
```

**Vérifications:**
- ✅ Dashboard Vincent d'Indy charge correctement
- ✅ Sélection de tournées fonctionne (avec gazelleId)
- ✅ Aucun piano manquant vs avant

---

### Étape 5: Déploiement

#### 5.1 Commit des Changements

```bash
git add api/vincent_dindy.py
git add scripts/reconcile_csv_with_gazelle.py
git add scripts/add_is_in_csv_column.sql
git add scripts/apply_is_in_csv_migration.py
git add MIGRATION_VINCENT_DINDY_V6_ETAPES.md
git add rapport_reconciliation_vincent_dindy.md

git commit -m "$(cat <<'EOF'
feat(vincent-dindy): Migration V6 - Charger pianos depuis Gazelle API

Migration complète du système Vincent d'Indy pour utiliser Gazelle comme source de vérité.

**Changements majeurs:**

API - Nouveau endpoint `/vincent-dindy/pianos`:
- Charge 119 pianos depuis Gazelle API (client ID: cli_9UMLkteep8EsISbG)
- Filtre par défaut: is_in_csv=TRUE OU status=ACTIVE (~94 pianos)
- Paramètre optionnel `?include_inactive=true` pour tout afficher
- Élimine dépendance au CSV (archivé en .old)

Supabase - Nouvelle colonne `is_in_csv`:
- TRUE = Piano dans CSV officiel (89 pianos)
- FALSE = Piano trouvé uniquement dans Gazelle (30 pianos)

Scripts de migration:
- `scripts/reconcile_csv_with_gazelle.py` - Réconciliation CSV ↔ Gazelle
- `scripts/add_is_in_csv_column.sql` - Migration SQL Supabase
- Rapport: `rapport_reconciliation_vincent_dindy.md`

**Avantages:**
✅ Nouveaux pianos ajoutés dans Gazelle apparaissent automatiquement
✅ Dates de dernier accord synchronisées depuis Gazelle
✅ Source de vérité unique (Gazelle)
✅ CSV devient obsolète (backup seulement)

**Statistiques:**
- Gazelle: 119 pianos total (59 actifs, 60 inactifs)
- CSV ancien: 91 pianos
- Match: 89 pianos
- Nouveaux pianos actifs découverts: 5
- Pianos inactifs hors CSV: 25

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"
```

#### 5.2 Push vers GitHub

```bash
git push origin main
```

#### 5.3 Vérification Render

- Render détectera le push et redéploiera automatiquement
- Vérifier les logs de déploiement
- Tester l'endpoint production:
  ```bash
  curl https://assistant-gazelle-v5-api.onrender.com/vincent-dindy/pianos
  ```

---

## 📈 Résultats Attendus

### Avant (V5 - CSV)
- Source: Fichier CSV statique (91 pianos)
- Nouveaux pianos: Nécessitent modification manuelle du CSV
- Dates d'accord: Manuelles (Supabase overlay)
- Pianos inactifs: Cachés dans le CSV

### Après (V6 - Gazelle)
- Source: API Gazelle (119 pianos, filtré à ~94 par défaut)
- Nouveaux pianos: Apparaissent automatiquement si ajoutés dans Gazelle
- Dates d'accord: Synchronisées depuis Gazelle (`calculatedLastService`)
- Pianos inactifs: Visibles avec `?include_inactive=true`

---

## 🔄 Extensions Futures

1. **Sync bidirectionnel**
   - Notes du technicien → Timeline Gazelle (via mutation GraphQL)
   - Date dernier accord mise à jour → Gazelle

2. **Autres institutions**
   - Appliquer la même approche pour Place des Arts, Orford, etc.
   - Client IDs à trouver:
     - Place des Arts: `cli_????????`
     - Orford: `cli_????????`

3. **Interface améliorée**
   - Toggle "Afficher pianos hors inventaire" dans le frontend
   - Badge "Nouveau" pour pianos actifs pas dans CSV
   - Badge "Inactif" pour pianos avec status=INACTIVE

---

## 📚 Fichiers de Référence

| Fichier | Description |
|---------|-------------|
| [`GAZELLE_SCHEMA_REFERENCE.md`](GAZELLE_SCHEMA_REFERENCE.md) | Schéma GraphQL complet de Gazelle |
| [`rapport_reconciliation_vincent_dindy.md`](rapport_reconciliation_vincent_dindy.md) | Rapport détaillé CSV ↔ Gazelle |
| [`scripts/reconcile_csv_with_gazelle.py`](scripts/reconcile_csv_with_gazelle.py) | Script de réconciliation |
| [`scripts/add_is_in_csv_column.sql`](scripts/add_is_in_csv_column.sql) | Migration SQL Supabase |

---

**Version:** 1.0
**Dernière mise à jour:** 2025-12-30
**Auteur:** Claude Sonnet 4.5 + Allan Sutton
