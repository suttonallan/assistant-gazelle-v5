# Configuration Place des Arts - Inventaire Pianos

## ✅ Modifications effectuées

### 1. Endpoint API Place des Arts (`api/place_des_arts.py`)
- ✅ Ajout de `/api/place-des-arts/pianos` qui récupère les pianos depuis Gazelle
- ✅ Filtre par client ID Place des Arts (pas Vincent d'Indy)
- ✅ Utilise `PLACE_DES_ARTS_CLIENT_ID` depuis la variable d'environnement `GAZELLE_CLIENT_ID_PDA`

### 2. Hook `usePianos` adapté (`refactor/vdi/hooks/usePianos.ts`)
- ✅ Détection automatique de l'établissement
- ✅ Utilise `/api/place-des-arts/pianos` pour Place des Arts
- ✅ Utilise `/api/vincent-dindy/pianos` pour Vincent d'Indy

### 3. Composant `PDAInventoryTable`
- ✅ Récupère les pianos Place des Arts depuis Gazelle (pas ceux de Vincent d'Indy)
- ✅ Mapping abréviations ↔ pianos Gazelle
- ✅ Alertes pour mappings incertains
- ✅ Système de jumelage avec interface visuelle

## 🔧 Configuration requise

### Étape 1: Trouver le Client ID Place des Arts

**Option A - Script automatique:**
```bash
python3 scripts/find_place_des_arts_client_id.py
```

**Option B - Manuel:**
1. Se connecter à Gazelle: https://gazelleapp.io
2. Aller dans la section Clients
3. Rechercher "Place des Arts"
4. Ouvrir le client et copier l'ID depuis l'URL (format: `cli_...`)

### Étape 2: Configurer le Client ID

**Dans `.env` (recommandé):**
```bash
GAZELLE_CLIENT_ID_PDA=cli_VOTRE_ID_ICI
```

**Ou directement dans `api/place_des_arts.py` ligne 32:**
```python
PLACE_DES_ARTS_CLIENT_ID = "cli_VOTRE_ID_ICI"
```

### Étape 3: Exécuter la migration SQL

Dans Supabase Dashboard → SQL Editor, exécuter:
1. `refactor/vdi/sql/009_create_pda_piano_mappings.sql` - Créer la table de mapping
2. `refactor/vdi/sql/010_add_uncertainty_to_pda_mappings.sql` - Ajouter colonnes d'incertitude (si table existe déjà)

## 📋 Utilisation

Une fois configuré, l'inventaire Place des Arts:
- ✅ Récupère uniquement les pianos du client Place des Arts depuis Gazelle
- ✅ Affiche les abréviations utilisées dans les demandes
- ✅ Permet de mapper les abréviations avec les vrais pianos
- ✅ Affiche des alertes pour les mappings incertains
- ✅ Confronte les demandes avec les pianos mappés

## 🎯 Prochaines étapes

1. Trouver et configurer le Client ID Place des Arts
2. Tester l'endpoint `/api/place-des-arts/pianos`
3. Vérifier que les pianos récupérés sont bien ceux de Place des Arts
4. Utiliser le composant `PDAInventoryTable` dans l'interface




