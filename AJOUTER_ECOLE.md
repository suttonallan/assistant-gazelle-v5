# Ajouter une nouvelle école - 10 secondes ⏱️

## Étape 1: Ouvrir le fichier de configuration

```bash
nano config/institutions.json
```

## Étape 2: Ajouter 3 lignes

```json
{
  "vincent-dindy": {
    "name": "Vincent d'Indy",
    "client_id": "cli_9UMLkteep8EsISbG"
  },
  "orford": {
    "name": "Orford",
    "client_id": "cli_ORFORD_ID_ICI"
  },
  "nouvelle-ecole": {
    "name": "Nouvelle École",
    "client_id": "cli_NOUVEL_ID_ICI"
  }
}
```

## Étape 3: Sauvegarder

C'est tout! **Aucune modification de code, aucune variable Render à toucher.**

## Comment utiliser la nouvelle école

```bash
# Charger les pianos
GET /api/nouvelle-ecole/pianos?include_inactive=false

# Historique d'activité
GET /api/nouvelle-ecole/activity?limit=20

# Statistiques
GET /api/nouvelle-ecole/stats
```

## Comment obtenir le client_id pour une nouvelle école

1. Va sur [gazelleapp.io](https://gazelleapp.io)
2. Connecte-toi avec le compte de l'école
3. Paramètres → API → Client ID
4. Copie le `cli_xxxxxxxxxxxxx`
5. Colle-le dans `institutions.json`

## Architecture

**Une seule route dynamique:**
```
GET /{institution}/pianos
GET /{institution}/activity
GET /{institution}/stats
```

**Une seule paire de clés Gazelle pour tout le monde:**
```
GAZELLE_CLIENT_ID=yCLgIwBusPMX9bZHtbzePvcNUisBQ9PeA4R93OwKwNE
GAZELLE_CLIENT_SECRET=CHiMzcYZ2cVgBCjQ7vDCxr3jIE5xkLZ_9v4VkU-O9Qc
```

Le client_id DANS la requête détermine quelle école est chargée (pas les env vars).

## Scalabilité

- ✅ Ajouter 10 écoles = ajouter 30 lignes JSON
- ✅ Pas de code à écrire
- ✅ Pas de deploy à faire
- ✅ Pas de variables Render à toucher
- ✅ Isolation automatique des données
