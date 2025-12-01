# Prompt de diagnostic pour Claude Code

## Contexte du problème

Le site web `https://suttonallan.github.io/assistant-gazelle-v5/` fonctionne et s'affiche correctement, mais **la liste des pianos est vide**. 

### Architecture
- **Frontend** : React + Vite, déployé sur GitHub Pages
- **Backend** : FastAPI, déployé sur Render.com
- **Données** : CSV avec 90 pianos dans `data_csv_test/pianos_vincent_dindy.csv`

### Ce qui fonctionne
- ✅ Le site se charge
- ✅ L'interface s'affiche
- ✅ Le workflow GitHub Actions déploie correctement
- ✅ L'API est accessible sur Render

### Ce qui ne fonctionne pas
- ❌ La liste des pianos est vide (devrait afficher 90 pianos)

## Fichiers à analyser

### 1. API Backend (`api/vincent_dindy.py`)
- Endpoint `/vincent-dindy/pianos` qui lit le CSV
- Fonction `get_csv_path()` qui cherche le fichier CSV
- Gestion des erreurs et logs de debug

### 2. Frontend (`frontend/src/components/VincentDIndyDashboard.jsx`)
- `useEffect` qui charge les pianos au montage
- Appel à `getPianos(API_URL)` depuis `vincentDIndyApi.js`
- Gestion des états `loading`, `error`, `pianos`

### 3. API Client Frontend (`frontend/src/api/vincentDIndyApi.js`)
- Fonction `getPianos(apiUrl)` qui fait `fetch` vers `/vincent-dindy/pianos`

### 4. Configuration
- `frontend/vite.config.js` : base path pour GitHub Pages
- `.github/workflows/deploy-frontend.yml` : variable `VITE_API_URL`
- `.gitignore` : le CSV est exclu sauf `!data_csv_test/pianos_vincent_dindy.csv`

## Questions à résoudre

1. **Le CSV est-il bien déployé sur Render ?**
   - Le fichier est dans Git (`git ls-files` le confirme)
   - Mais Render clone depuis GitHub, donc il devrait être là
   - Le chemin sur Render pourrait être différent

2. **L'API retourne-t-elle des données ?**
   - Tester directement : `https://assistant-gazelle-v5-api.onrender.com/vincent-dindy/pianos`
   - Vérifier les logs Render pour voir les erreurs

3. **Le frontend appelle-t-il la bonne URL ?**
   - `VITE_API_URL` est défini dans le workflow GitHub Actions
   - Valeur par défaut : `https://assistant-gazelle-v5-api.onrender.com`
   - Vérifier que c'est bien injecté au build

4. **Y a-t-il des erreurs CORS ?**
   - L'API a `allow_origins=["*"]` donc ça devrait être OK

5. **Le format des données correspond-il ?**
   - Le CSV a : `local,Piano,# série,Priorité ,Type,À faire`
   - Le code cherche : `"local"`, `"Piano"`, `"# série"`, `"Priorité"` ou `"Priorité "`, `"Type"`, `"À faire"`

## Code récent modifié

### `api/vincent_dindy.py`
- Ajout de logs détaillés avec `logging.info()`
- Amélioration de `get_csv_path()` pour essayer plusieurs chemins
- Retourne des infos de debug dans la réponse JSON

### `frontend/src/components/VincentDIndyDashboard.jsx`
- Ajout de `console.log()` pour tracer le chargement
- Meilleure gestion des erreurs avec affichage du message

## Actions de diagnostic à faire

1. **Vérifier les logs Render** pour voir si le CSV est trouvé
2. **Tester l'endpoint API directement** dans le navigateur
3. **Vérifier la console du navigateur** sur le site déployé
4. **Vérifier que `VITE_API_URL` est bien défini** dans le build GitHub Actions

## Prompt pour Claude Code

```
Analyse complète du problème : le site web fonctionne mais la liste des pianos est vide.

Contexte :
- Frontend React déployé sur GitHub Pages
- Backend FastAPI déployé sur Render.com
- CSV avec 90 pianos dans data_csv_test/pianos_vincent_dindy.csv
- Le CSV est bien dans Git (confirmé par git ls-files)

Fichiers clés à examiner :
1. api/vincent_dindy.py - endpoint /vincent-dindy/pianos qui lit le CSV
2. frontend/src/components/VincentDIndyDashboard.jsx - charge les pianos au montage
3. frontend/src/api/vincentDIndyApi.js - fonction getPianos()
4. .github/workflows/deploy-frontend.yml - variable VITE_API_URL

Questions à résoudre :
1. Le CSV est-il accessible sur Render ? (le chemin pourrait être différent)
2. L'API retourne-t-elle des données ? (tester directement l'endpoint)
3. Le frontend appelle-t-il la bonne URL ? (VITE_API_URL est-il injecté au build ?)
4. Y a-t-il des erreurs dans la console du navigateur ?
5. Le format du CSV correspond-il à ce que le code attend ?

Actions récentes :
- Ajout de logs détaillés dans l'API
- Amélioration de get_csv_path() pour essayer plusieurs chemins
- Ajout de console.log() dans le frontend pour tracer

Analyse tous les fichiers pertinents et propose :
1. Les causes probables du problème
2. Comment vérifier chaque hypothèse
3. Les corrections à apporter si nécessaire
4. Un plan de test pour valider la solution
```

## Informations supplémentaires à vérifier

### Dans la console du navigateur (sur le site déployé)
- Messages `🔄 Chargement des pianos depuis: ...`
- Messages `✅ Données reçues: ...` ou `❌ Erreur API: ...`
- Erreurs réseau dans l'onglet Network

### Dans les logs Render
- Messages `🔍 Recherche du CSV à: ...`
- Messages `✅ CSV trouvé: ...` ou `❌ Fichier CSV non trouvé: ...`
- Erreurs Python complètes

### Test direct de l'API
- Ouvrir : `https://assistant-gazelle-v5-api.onrender.com/vincent-dindy/pianos`
- Vérifier la réponse JSON :
  - Si `{"pianos": [], "count": 0, "error": true, "message": "..."}` → le CSV n'est pas trouvé
  - Si `{"pianos": [...], "count": 90}` → l'API fonctionne, problème côté frontend
  - Si erreur 500 → problème dans le code Python

