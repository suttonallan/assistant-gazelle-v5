#!/bin/bash
# Script de déploiement manuel pour GitHub Pages

echo "🚀 Déploiement du frontend..."

# Aller dans le dossier frontend
cd "$(dirname "$0")"

# Installer les dépendances si nécessaire
if [ ! -d "node_modules" ]; then
    echo "📦 Installation des dépendances..."
    npm install
fi

# Build
echo "🔨 Build du projet..."
npm run build

# Copier dans docs/ (méthode manuelle)
if [ -d "../docs" ]; then
    echo "📋 Copie vers docs/..."
    rm -rf ../docs/*
    cp -r dist/* ../docs/
    echo "✅ Fichiers copiés dans docs/"
    echo ""
    echo "Prochaines étapes:"
    echo "1. git add docs/"
    echo "2. git commit -m 'Deploy frontend'"
    echo "3. git push origin main"
else
    echo "⚠️  Le dossier docs/ n'existe pas. Crée-le d'abord."
fi

echo ""
echo "✅ Build terminé !"





