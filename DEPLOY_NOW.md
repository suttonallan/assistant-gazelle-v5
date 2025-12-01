# 🚀 Guide de déploiement rapide - Vincent-d'Indy

## Étape 1 : Pousser le code sur GitHub

```bash
git push origin main
```

## Étape 2 : Créer le service sur Render

1. Va sur [render.com](https://render.com)
2. **Sign up** avec GitHub (si pas déjà fait)
3. Clique sur **New** → **Web Service**
4. **Connect** ton repo `assistant-gazelle-v5`
5. Configure :

### Configuration de base
- **Name**: `assistant-gazelle-v5-api`
- **Environment**: `Python 3`
- **Region**: Choisis le plus proche (ex: `Oregon (US West)`)
- **Branch**: `main`
- **Root Directory**: *(laisse vide)*

### Build & Start
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`

### Variables d'environnement
Clique sur **Advanced** → **Environment Variables**, ajoute :

```
GAZELLE_CLIENT_ID=yCLgIwBusPMX9bZHtbzePvcNUisBQ9PeA4R93OwKwNE
GAZELLE_CLIENT_SECRET=CHiMzcYZ2cVgBCjQ7vDCxr3jIE5xkLZ_9v4VkU-O9Qc
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**Pour obtenir GITHUB_TOKEN** :
1. Va sur [github.com/settings/tokens](https://github.com/settings/tokens)
2. **Generate new token** → **Generate new token (classic)**
3. Donne-lui un nom (ex: "assistant-gazelle-gist")
4. Coche **gist** (permission pour créer/modifier des Gists)
5. **Generate token** → **COPIE le token** (tu ne le verras qu'une fois !)
6. Colle-le dans la variable `GITHUB_TOKEN` sur Render

*(Les valeurs GAZELLE viennent de `config/# OAuth2 credentials.md`)*

### ✅ Stockage persistant avec GitHub Gist

**Les rapports sont stockés dans un Gist GitHub privé** (gratuit et persistant).

- ✅ Gratuit
- ✅ Persistant (même si Render redémarre)
- ✅ Privé (seul toi y as accès)
- ✅ Simple à utiliser
- ✅ Ne complique pas le code (on peut toujours pousser vers Gazelle plus tard)

6. Clique sur **Create Web Service**
7. Attends 2-3 minutes pour le build

## Étape 3 : Tester l'API

Une fois déployé, tu auras une URL comme :
`https://assistant-gazelle-v5-api.onrender.com`

### Test rapide

```bash
# Vérifier que l'API fonctionne
curl https://assistant-gazelle-v5-api.onrender.com/health

# Voir les endpoints disponibles
curl https://assistant-gazelle-v5-api.onrender.com/

# Voir les stats (vide pour l'instant)
curl https://assistant-gazelle-v5-api.onrender.com/vincent-dindy/stats
```

### Soumettre un rapport de test

```bash
curl -X POST https://assistant-gazelle-v5-api.onrender.com/vincent-dindy/reports \
  -H "Content-Type: application/json" \
  -d '{
    "technician_name": "Jean Dupont",
    "client_name": "École Vincent-d'\''Indy",
    "date": "2025-12-01",
    "report_type": "maintenance",
    "description": "Réparation du piano à queue",
    "notes": "Tout fonctionne bien maintenant",
    "hours_worked": 2.5
  }'
```

## Endpoints disponibles

- `GET /` - Info sur l'API
- `GET /health` - Vérification de santé
- `POST /vincent-dindy/reports` - Soumettre un rapport
- `GET /vincent-dindy/reports` - Lister les rapports
- `GET /vincent-dindy/reports/{report_id}` - Voir un rapport spécifique
- `GET /vincent-dindy/stats` - Statistiques

## Documentation interactive

Une fois déployé, va sur :
`https://assistant-gazelle-v5-api.onrender.com/docs`

Tu verras l'interface Swagger pour tester l'API directement dans le navigateur !

## ✅ Stockage persistant avec GitHub Gist

Les rapports sont automatiquement sauvegardés dans un Gist GitHub privé :
- ✅ **Gratuit** et illimité (tant que le Gist fait moins de 1MB)
- ✅ **Persistant** : les données survivent aux redémarrages
- ✅ **Privé** : seul toi y as accès
- ✅ **Simple** : pas de configuration complexe

Le Gist est créé automatiquement au premier rapport soumis.

## Prochaines étapes

1. ✅ API déployée et fonctionnelle
2. ✅ Les rapports sont sauvegardés dans GitHub Gist (persistant)
3. 📝 **Plus tard** : Créer un endpoint pour pousser les rapports vers Gazelle
4. 🎨 Plus tard : Créer un frontend pour les techniciens

