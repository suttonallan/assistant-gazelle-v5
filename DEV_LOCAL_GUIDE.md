# 🛠️ Guide de développement local - Vincent-d'Indy

## 📋 Prérequis

1. **Python 3.9+** ✅ (installé)
2. **Node.js 18+** ⚠️ (à installer via Homebrew)
3. **npm** (inclus avec Node.js)

---

## 🚀 Installation initiale

### 1. Installer Node.js

```bash
# Installer Homebrew (si pas déjà fait)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Installer Node.js
brew install node

# Vérifier l'installation
node --version
npm --version
```

### 2. Configurer les variables d'environnement

Éditez le fichier `.env` à la racine du projet :

```bash
# Ouvrir le fichier .env
nano .env
```

Remplissez les valeurs suivantes (copiez-les depuis Render) :

```env
# GitHub Gist (obligatoire pour la persistance)
GITHUB_TOKEN=ghp_votre_token_ici
GITHUB_GIST_ID=votre_gist_id_ici

# Base de données SQL Server (optionnel pour Vincent-d'Indy)
DB_SERVER=votre_serveur.database.windows.net
DB_NAME=PianoTek
DB_USER=votre_utilisateur
DB_PASSWORD=votre_mot_de_passe
```

### 3. Installer les dépendances

**Backend (déjà fait)** :
```bash
pip3 install -r requirements.txt
```

**Frontend (à faire après installation de Node.js)** :
```bash
cd frontend
npm install
```

---

## 🏃 Démarrage rapide

### Option A : Deux terminaux séparés (recommandé)

**Terminal 1 - Backend** :
```bash
./start-backend.sh
```

**Terminal 2 - Frontend** :
```bash
./start-frontend.sh
```

### Option B : Commandes manuelles

**Backend** :
```bash
python3 -m uvicorn api.main:app --reload --port 8000
```

**Frontend** :
```bash
cd frontend
npm run dev
```

---

## 🌐 URLs de développement

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend** | http://localhost:5173 | Interface React/Vite |
| **Backend API** | http://localhost:8000 | FastAPI |
| **API Docs** | http://localhost:8000/docs | Documentation Swagger |

---

## 📝 Workflow de développement

### 1. Modifier le code

- **Frontend** : `frontend/src/components/VincentDIndyDashboard.jsx`
- **Backend** : `api/vincent_dindy.py`

### 2. Tester en temps réel

- Le frontend se recharge automatiquement (Vite HMR)
- Le backend se recharge automatiquement (uvicorn --reload)

### 3. Quand satisfait : commit et push

```bash
# Voir les changements
git status
git diff

# Créer un commit
git add .
git commit -m "Description des changements"

# Pousser vers GitHub (déploiement automatique)
git push
```

---

## 🔧 Dépannage

### Erreur : "Module not found"

**Backend** :
```bash
pip3 install -r requirements.txt
```

**Frontend** :
```bash
cd frontend
npm install
```

### Erreur : "Port already in use"

**Backend (port 8000)** :
```bash
lsof -ti:8000 | xargs kill -9
```

**Frontend (port 5173)** :
```bash
lsof -ti:5173 | xargs kill -9
```

### Backend ne démarre pas : "GITHUB_TOKEN requis"

Vérifiez que le fichier `.env` contient :
```env
GITHUB_TOKEN=ghp_...
GITHUB_GIST_ID=...
```

### Frontend ne se connecte pas au backend

Vérifiez que :
1. Le backend est lancé sur `http://localhost:8000`
2. Le fichier `frontend/src/components/VincentDIndyDashboard.jsx` utilise la bonne URL API

---

## 📊 Utiliser la base de données PianoTek (optionnel)

Si vous voulez connecter la base de données locale :

1. Remplissez les variables dans `.env` :
   ```env
   DB_SERVER=votre_serveur.database.windows.net
   DB_NAME=PianoTek
   DB_USER=votre_utilisateur
   DB_PASSWORD=votre_mot_de_passe
   ```

2. Installez les dépendances SQL Server :
   ```bash
   pip3 install pyodbc
   ```

3. Redémarrez le backend

---

## 🎯 Prochaines étapes

1. ✅ Installer Homebrew
2. ✅ Installer Node.js
3. ✅ Installer dépendances npm (`cd frontend && npm install`)
4. ✅ Configurer `.env`
5. ✅ Lancer les deux serveurs
6. ✅ Développer en local sans attendre le déploiement !

---

**Dernière mise à jour** : 2025-12-02
**Responsable** : Allan Sutton
**Assistant** : Claude Code
