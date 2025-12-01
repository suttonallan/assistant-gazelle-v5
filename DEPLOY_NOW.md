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
```

*(Ces valeurs viennent de `config/# OAuth2 credentials.md`)*

### Volume persistant (pour les rapports)
Après avoir créé le service :
1. Va dans **Settings**
2. Active **Persistent Disk** (gratuit jusqu'à 1GB)
3. Le code détectera automatiquement le chemin

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

## Prochaines étapes

1. ✅ API déployée et fonctionnelle
2. 🔄 Les rapports sont sauvegardés dans `reports/` (volume persistant)
3. 📝 Plus tard : Créer un script pour pousser les rapports vers Gazelle
4. 🎨 Plus tard : Créer un frontend pour les techniciens

