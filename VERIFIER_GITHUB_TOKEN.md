# 🔍 Comment vérifier si GITHUB_TOKEN est configuré sur Render

## Méthode 1 : Vérifier dans Render Dashboard

1. Va sur [render.com](https://render.com)
2. Clique sur ton service `assistant-gazelle-v5-api`
3. Va dans **Settings** → **Environment Variables**
4. Cherche `GITHUB_TOKEN` dans la liste
5. Si tu le vois : ✅ **Configuré**
6. Si tu ne le vois pas : ❌ **Non configuré**

## Méthode 2 : Tester l'API directement

### Test 1 : Vérifier les logs Render

1. Va sur Render → Ton service → **Logs**
2. Cherche des messages comme :
   - `⚠️ Impossible d'appliquer les modifications Gist: ...`
   - `GITHUB_TOKEN requis pour créer un Gist`
   - Si tu vois ces erreurs → Token **non configuré** ou **invalide**

### Test 2 : Tester l'endpoint qui utilise le Gist

```bash
# Tester l'endpoint qui charge les pianos (utilise le Gist pour les modifications)
curl https://assistant-gazelle-v5-api.onrender.com/vincent-dindy/pianos
```

**Si le token est configuré** :
- ✅ La réponse contient les pianos
- ✅ Pas d'erreur dans la réponse
- ⚠️ Si tu vois un warning dans les logs, c'est normal (le Gist n'existe peut-être pas encore)

**Si le token n'est PAS configuré** :
- ✅ La réponse contient quand même les pianos (depuis le CSV)
- ⚠️ Tu verras un warning dans les logs : `⚠️ Impossible d'appliquer les modifications Gist: ...`
- ❌ Les modifications des pianos ne seront pas sauvegardées

### Test 3 : Tester la mise à jour d'un piano

```bash
# Tester l'endpoint PUT pour mettre à jour un piano
curl -X PUT https://assistant-gazelle-v5-api.onrender.com/vincent-dindy/pianos/149654 \
  -H "Content-Type: application/json" \
  -d '{
    "status": "approved",
    "aFaire": "Test de mise à jour"
  }'
```

**Si le token est configuré** :
- ✅ Réponse : `{"success": true, "message": "Piano mis à jour avec succès", ...}`
- ✅ Les modifications sont sauvegardées dans le Gist

**Si le token n'est PAS configuré** :
- ❌ Erreur 400 : `"Configuration manquante: GITHUB_TOKEN requis pour créer un Gist"`
- ❌ Les modifications ne sont pas sauvegardées

## Méthode 3 : Vérifier dans les logs de l'API

Dans les logs Render, cherche ces messages :

### ✅ Token configuré (fonctionne)
```
✅ CSV trouvé: /opt/render/project/src/api/data/pianos_vincent_dindy.csv
✅ 91 pianos chargés (91 lignes traitées, 0 ignorées)
✅ Modifications Gist appliquées
```

### ⚠️ Token non configuré (fonctionne partiellement)
```
✅ CSV trouvé: /opt/render/project/src/api/data/pianos_vincent_dindy.csv
✅ 91 pianos chargés (91 lignes traitées, 0 ignorées)
⚠️ Impossible d'appliquer les modifications Gist: GITHUB_TOKEN requis pour créer un Gist
```

### ❌ Token invalide (erreur)
```
✅ CSV trouvé: /opt/render/project/src/api/data/pianos_vincent_dindy.csv
✅ 91 pianos chargés (91 lignes traitées, 0 ignorées)
⚠️ Impossible d'appliquer les modifications Gist: 401 Unauthorized
```

## 📝 Comment ajouter/configurer le token

### Si le token n'est pas configuré :

1. **Générer un token GitHub** :
   - Va sur [github.com/settings/tokens](https://github.com/settings/tokens)
   - Clique sur **Generate new token** → **Generate new token (classic)**
   - Donne-lui un nom : `assistant-gazelle-gist`
   - Coche **gist** (permission pour créer/modifier des Gists)
   - Clique sur **Generate token**
   - **COPIE le token** (tu ne le verras qu'une fois !)

2. **Ajouter sur Render** :
   - Va sur Render → Ton service → **Settings** → **Environment Variables**
   - Clique sur **Add Environment Variable**
   - **Key** : `GITHUB_TOKEN`
   - **Value** : colle ton token (commence par `ghp_...`)
   - Clique sur **Save Changes**

3. **Redéployer** :
   - Render redéploiera automatiquement
   - Ou clique sur **Manual Deploy** → **Deploy latest commit**

### Si le token est invalide/expiré :

1. Régénère un nouveau token sur GitHub
2. Remplace la valeur de `GITHUB_TOKEN` sur Render
3. Redéploie le service

## ✅ Résultat attendu

Une fois configuré correctement :
- ✅ Les pianos se chargent depuis le CSV
- ✅ Les modifications des pianos sont sauvegardées dans le Gist
- ✅ Les modifications persistent même après un redémarrage de Render
- ✅ Pas d'erreurs dans les logs

## 🔗 Vérification rapide

**Test rapide** : Va sur `https://assistant-gazelle-v5-api.onrender.com/vincent-dindy/pianos`

Si tu vois les 91 pianos → ✅ **Le CSV fonctionne**  
Si tu vois aussi les modifications appliquées → ✅ **Le Gist fonctionne** (token OK)  
Si tu vois un warning dans les logs → ⚠️ **Le token n'est pas configuré** (mais le CSV fonctionne)










