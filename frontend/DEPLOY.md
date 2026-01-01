# Déploiement du Frontend sur GitHub Pages

## Méthode 1 : Déploiement automatique avec GitHub Actions (Recommandé)

### Étape 1 : Créer le workflow GitHub Actions

Crée le fichier `.github/workflows/deploy-frontend.yml` à la racine du projet :

```yaml
name: Deploy Frontend to GitHub Pages

on:
  push:
    branches:
      - main
    paths:
      - 'frontend/**'

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pages: write
      id-token: write
    
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      
      - name: Install dependencies
        working-directory: ./frontend
        run: npm ci
      
      - name: Build
        working-directory: ./frontend
        run: npm run build
        env:
          VITE_API_URL: ${{ secrets.VITE_API_URL || 'https://assistant-gazelle-v5-api.onrender.com' }}
      
      - name: Setup Pages
        uses: actions/configure-pages@v4
      
      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: './frontend/dist'
      
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

### Étape 2 : Configurer GitHub Pages

1. Va sur GitHub → Settings → Pages
2. Source : **GitHub Actions** (pas "Deploy from a branch")
3. Save

### Étape 3 : Ajouter la variable d'environnement (optionnel)

Si tu veux changer l'URL de l'API :
1. Va sur GitHub → Settings → Secrets and variables → Actions
2. New repository secret
3. Name : `VITE_API_URL`
4. Value : `https://assistant-gazelle-v5-api.onrender.com`

### Résultat

À chaque push dans `frontend/`, GitHub Actions va :
1. Installer les dépendances
2. Builder le projet
3. Déployer automatiquement sur GitHub Pages

Ton site sera disponible sur : `https://suttonallan.github.io/assistant-gazelle-v5/`

---

## Méthode 2 : Déploiement manuel (Simple)

### Étape 1 : Build le projet

```bash
cd frontend
npm install
npm run build
```

### Étape 2 : Copier dans docs/

```bash
# Depuis la racine du projet
cp -r frontend/dist/* docs/
```

### Étape 3 : Configurer GitHub Pages

1. Va sur GitHub → Settings → Pages
2. Source : **Deploy from a branch**
3. Branch : `main`
4. Folder : `/docs`
5. Save

### Étape 4 : Commit et push

```bash
git add docs/
git commit -m "Deploy frontend to GitHub Pages"
git push origin main
```

Ton site sera disponible sur : `https://suttonallan.github.io/assistant-gazelle-v5/`

---

## Configuration de l'URL de l'API

Par défaut, l'API est configurée pour : `https://assistant-gazelle-v5-api.onrender.com`

Pour changer :
1. Crée un fichier `frontend/.env` :
   ```
   VITE_API_URL=https://ton-api-url.com
   ```
2. Rebuild : `npm run build`

---

## Vérification

Une fois déployé, teste :
- L'interface se charge correctement
- Les onglets fonctionnent (Préparation, Validation, Technicien)
- La sauvegarde d'un rapport fonctionne (vue Technicien)





