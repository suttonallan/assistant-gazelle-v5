# Configuration Google Service Account pour Rapports Timeline

## 🎯 Objectif

Permettre au système de générer automatiquement des rapports Timeline dans Google Sheets sans intervention manuelle.

## 📋 Prérequis

- Accès à [Google Cloud Console](https://console.cloud.google.com)
- Droits administrateur sur le projet Google Cloud
- Accès éditeur aux Google Sheets cibles

## 🔧 Étapes de Configuration

### 1. Créer un Service Account

1. Aller sur [Google Cloud Console](https://console.cloud.google.com)
2. Sélectionner le projet: **ptm-gmail-api** (ou créer un nouveau projet)
3. Aller dans **IAM & Admin** → **Service Accounts**
4. Cliquer sur **+ CREATE SERVICE ACCOUNT**

Informations à renseigner:
- **Service account name**: `assistant-gazelle-reports`
- **Service account ID**: `assistant-gazelle-reports` (auto-généré)
- **Description**: `Service account pour génération automatique des rapports Timeline v5`

5. Cliquer sur **CREATE AND CONTINUE**

### 2. Accorder les Permissions

**Rôle à assigner**: Aucun rôle nécessaire au niveau du projet
(Les permissions seront données directement dans Google Sheets)

Cliquer sur **CONTINUE** → **DONE**

### 3. Créer une Clé JSON

1. Dans la liste des Service Accounts, cliquer sur l'email du service account créé
2. Aller dans l'onglet **KEYS**
3. Cliquer sur **ADD KEY** → **Create new key**
4. Sélectionner **JSON**
5. Cliquer sur **CREATE**

Le fichier JSON sera téléchargé automatiquement. Il ressemble à:

```json
{
  "type": "service_account",
  "project_id": "ptm-gmail-api",
  "private_key_id": "abc123...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "assistant-gazelle-reports@ptm-gmail-api.iam.gserviceaccount.com",
  "client_id": "123456789...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/..."
}
```

### 4. Installer Localement

```bash
# Copier le fichier téléchargé dans le projet
cp ~/Downloads/ptm-gmail-api-*.json ~/Documents/assistant-gazelle-v5/google-credentials.json

# Configurer la variable d'environnement
echo 'export GOOGLE_APPLICATION_CREDENTIALS="$HOME/Documents/assistant-gazelle-v5/google-credentials.json"' >> ~/.zshrc

# Recharger le shell
source ~/.zshrc
```

**⚠️ Important**: Le fichier `google-credentials.json` est dans `.gitignore` et ne sera **jamais** committé sur GitHub.

### 5. Donner Accès aux Google Sheets

Pour chaque Google Sheet où le rapport doit être généré:

1. Ouvrir le Google Sheet
2. Cliquer sur **Share** (Partager)
3. Ajouter l'email du Service Account:
   ```
   assistant-gazelle-reports@ptm-gmail-api.iam.gserviceaccount.com
   ```
4. Donner le rôle: **Editor** (Éditeur)
5. Cliquer sur **Send**

**Google Sheets concernés**:
- [Rapport Timeline v5](https://docs.google.com/spreadsheets/d/1ZZsMrIT0BEwHKQ6-BKGzFoXR3k99zCEzixp0tsRKUj8)

### 6. Configurer GitHub Actions

1. Aller sur [GitHub Repository Settings](https://github.com/suttonallan/assistant-gazelle-v5/settings/secrets/actions)
2. Cliquer sur **New repository secret**
3. Nom: `GOOGLE_SERVICE_ACCOUNT_JSON`
4. Valeur: Copier **tout le contenu** du fichier JSON (y compris les accolades)
5. Cliquer sur **Add secret**

## ✅ Vérification

### Test Local

```bash
python3 -c "
from modules.reports.service_reports import run_reports
result = run_reports(append=False)
print('Rapport généré:', result)
"
```

### Test GitHub Actions

Déclencher manuellement le workflow:
1. Aller sur [Actions](https://github.com/suttonallan/assistant-gazelle-v5/actions)
2. Sélectionner **Full Gazelle Sync (Nightly)**
3. Cliquer sur **Run workflow**
4. Attendre la fin de l'exécution
5. Vérifier le Google Sheet

## 🔒 Sécurité

### Fichiers à NE JAMAIS Committer

- `google-credentials.json`
- `*credentials*.json`
- `token.json`

Ces fichiers sont déjà dans `.gitignore`.

### Rotation des Clés

Recommandé tous les 90 jours:
1. Créer une nouvelle clé dans Google Cloud Console
2. Mettre à jour localement et dans GitHub Secrets
3. Supprimer l'ancienne clé

### Permissions Minimales

Le Service Account a seulement:
- ❌ Aucun accès au projet Google Cloud
- ✅ Accès Editor aux Google Sheets partagés explicitement

## 📞 Support

En cas de problème:
1. Vérifier que le Service Account email est bien partagé sur le Google Sheet
2. Vérifier que `GOOGLE_APPLICATION_CREDENTIALS` pointe vers le bon fichier
3. Vérifier que le secret GitHub est bien configuré
4. Consulter les logs du workflow GitHub Actions

## 📚 Références

- [Google Cloud Service Accounts](https://cloud.google.com/iam/docs/service-accounts)
- [gspread Authentication](https://docs.gspread.org/en/latest/oauth2.html#service-account)
- [GitHub Encrypted Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
