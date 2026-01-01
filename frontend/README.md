# Frontend - Assistant Gazelle V5

Interface React pour le module Vincent-d'Indy.

## Développement local

```bash
npm install
npm run dev
```

## Build pour production

```bash
npm run build
```

Le dossier `dist/` contiendra les fichiers à déployer sur GitHub Pages.

## Configuration

L'URL de l'API est configurée dans `src/components/VincentDIndyDashboard.jsx` :

```javascript
const API_URL = import.meta.env.VITE_API_URL || 'https://assistant-gazelle-v5-api.onrender.com';
```

Pour changer l'URL de l'API, crée un fichier `.env` :

```
VITE_API_URL=https://ton-api-url.com
```

## Déploiement sur GitHub Pages

1. Build le projet : `npm run build`
2. Le dossier `dist/` contient les fichiers statiques
3. Configure GitHub Pages pour servir depuis `dist/` ou copie les fichiers dans `docs/`





