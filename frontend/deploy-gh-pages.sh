#!/bin/bash
# Script de déploiement pour GitHub Pages (branche gh-pages)

set -e  # Arrêter en cas d'erreur

echo "🚀 Déploiement du frontend sur GitHub Pages..."

# Aller dans le dossier frontend
cd "$(dirname "$0")"

# Vérifier qu'on est sur main
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "⚠️  Vous devez être sur la branche 'main' pour déployer"
    exit 1
fi

# Vérifier qu'il n'y a pas de modifications non commitées
if ! git diff-index --quiet HEAD --; then
    echo "⚠️  Il y a des modifications non commitées. Commitez d'abord!"
    exit 1
fi

# Installer les dépendances si nécessaire
if [ ! -d "node_modules" ]; then
    echo "📦 Installation des dépendances..."
    npm install
fi

# Build
echo "🔨 Build du projet..."
npm run build

# Sauvegarder le répertoire de build
BUILD_DIR=$(pwd)/dist

# Retourner à la racine
cd ..

# Créer ou nettoyer la branche gh-pages
echo "📋 Préparation de la branche gh-pages..."
git fetch origin gh-pages:gh-pages 2>/dev/null || git branch gh-pages
git checkout gh-pages

# Nettoyer tout sauf .git
find . -maxdepth 1 ! -name '.' ! -name '..' ! -name '.git' -exec rm -rf {} +

# Copier le build
echo "📦 Copie des fichiers du build..."
cp -r "$BUILD_DIR"/* .

# Ajouter un fichier .nojekyll pour éviter le traitement Jekyll
touch .nojekyll

# Commit et push
git add -A
git commit -m "deploy: Déployer frontend $(date +'%Y-%m-%d %H:%M')" || echo "Aucun changement à commiter"
git push origin gh-pages

# Retourner sur main
git checkout main

echo ""
echo "✅ Déploiement terminé!"
echo ""
echo "Le frontend sera disponible à:"
echo "https://[votre-username].github.io/assistant-gazelle-v5/"
echo ""
echo "Configuration GitHub Pages:"
echo "1. Allez sur GitHub → Settings → Pages"
echo "2. Source: Deploy from a branch"
echo "3. Branch: gh-pages / (root)"
echo "4. Save"
