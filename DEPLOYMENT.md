# Guide de déploiement - Assistant Gazelle V5

## Architecture

- **Backend (API)**: Render.com
- **Frontend**: GitHub Pages (gratuit, simple, parfait pour sites statiques)

## Étape 1 : Préparer le repo GitHub

✅ Déjà fait : Le repo `assistant-gazelle-v5` est sur GitHub avec la structure modulaire.

## Étape 2 : Déployer l'API sur Render

1. Va sur [render.com](https://render.com) → **Sign up** avec GitHub
2. **New** → **Web Service**
3. **Connect** ton repo `assistant-gazelle-v5`
4. Configure :
   - **Name**: `assistant-gazelle-v5-api`
   - **Root Directory**: *(laisse vide, c'est à la racine)*
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
5. **Environment Variables** (à ajouter dans Render) :
   - `GAZELLE_CLIENT_ID`: (depuis config/# OAuth2 credentials.md)
   - `GAZELLE_CLIENT_SECRET`: (depuis config/# OAuth2 credentials.md)
6. **Persistent Disk** (dans Settings après création) :
   - Active **Persistent Disk** (gratuit jusqu'à 1GB)
   - Le code détecte automatiquement le chemin
7. **Create** → Attends 2-3 min
8. Note l'URL : `https://assistant-gazelle-v5-api.onrender.com`

**Optionnel - Backup automatique** :
- Dans Render : **New** → **Cron Job**
- **Command**: `python scripts/backup_db.py`
- **Schedule**: `0 2 * * *` (tous les jours à 2h)
- Connecte le même repo `assistant-gazelle-v5`

## Étape 3 : Déployer le Frontend sur GitHub Pages

Quand le frontend sera créé :

1. Crée un dossier `frontend/` ou `docs/` dans le repo
2. Dans GitHub : **Settings** → **Pages**
3. **Source**: `main` branch, folder: `frontend` (ou `docs`)
4. **Save**
5. Ton site sera disponible sur : `https://suttonallan.github.io/assistant-gazelle-v5/`

**Avantages GitHub Pages** :
- ✅ Gratuit
- ✅ Déploiement automatique à chaque push
- ✅ Pas besoin de compte supplémentaire
- ✅ Parfait pour sites statiques (React, Vue, HTML/CSS/JS)

**Note** : Pour les variables d'environnement (comme l'URL de l'API), utilise un fichier de config JavaScript ou hardcode l'URL dans le code (c'est OK pour un petit projet).

## Base de données SQLite en production

### Configuration SQLite avec volume persistant (Render)

SQLite fonctionne parfaitement pour un petit projet ! Configuration simple :

1. Dans Render, après avoir créé le service :
   - Va dans **Settings** de ton service
   - Active **Persistent Disk** (gratuit jusqu'à 1GB)
   - Le chemin sera automatiquement disponible via `RENDER_PERSISTENT_DISK_PATH`

2. Le code utilise automatiquement le bon chemin :
   - **Production (Render)** : Volume persistant (données sauvegardées)
   - **Développement local** : Fichier à la racine du projet

3. **Sauvegarde automatique** (optionnel) :
   - Le script `scripts/backup_db.py` crée des backups
   - Sur Render, ajoute un **Cron Job** pour exécuter le backup quotidiennement :
     - **Command**: `python scripts/backup_db.py`
     - **Schedule**: `0 2 * * *` (tous les jours à 2h du matin)

**Avantages** :
- ✅ Simple, pas de configuration complexe
- ✅ Gratuit
- ✅ Pas d'authentification à gérer
- ✅ Les données persistent entre les redémarrages
- ✅ Parfait pour petit projet avec peu d'utilisateurs

**Limitations** :
- ⚠️ Un seul processus peut écrire à la fois (OK pour petit projet)
- ⚠️ Pas de sauvegarde automatique par défaut (ajoute le cron job)

## Déploiement automatique continu

✅ **Chaque push sur GitHub déclenche automatiquement un nouveau déploiement !**

**Workflow simple** :
1. Tu modifies le code localement
2. `git commit` et `git push`
3. Render détecte automatiquement le push
4. Build et déploiement automatique (2-3 min)
5. ✅ Nouvelle version en ligne !

**Avantages** :
- ✅ Version toujours en ligne (l'ancienne reste active pendant le build)
- ✅ Pas d'interruption pour tes utilisateurs
- ✅ Rollback automatique si le déploiement échoue
- ✅ Simple : juste `git push` et c'est déployé

Voir `WORKFLOW.md` pour plus de détails.

## Notes importantes

- Les fichiers `config/token.json` et `config/# OAuth2 credentials.md` sont ignorés par Git (protégés)
- Les credentials doivent être ajoutés comme variables d'environnement dans Render
- La base de données SQLite persiste entre les déploiements grâce au volume persistant

