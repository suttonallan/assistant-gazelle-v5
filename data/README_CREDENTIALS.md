# Credentials Google Sheets

## 📁 Fichier: credentials_ptm.json

**Ce fichier contient les credentials du Service Account Google pour accéder au Google Sheet "Rapport Timeline Google".**

### 🔐 Informations du Service Account

- **Email:** pianosheets-bot@piano-sheets-471218.iam.gserviceaccount.com
- **Project ID:** piano-sheets-471218
- **Type:** Service Account

### 📊 Google Sheet accessible

- **Nom:** "Rapport Timeline Google"
- **ID:** 1Y2Ggi2O1aTVa-lsyhl88FF6XWCTRs6h_DIYwYUEZjV8
- **URL:** https://docs.google.com/spreadsheets/d/1Y2Ggi2O1aTVa-lsyhl88FF6XWCTRs6h_DIYwYUEZjV8

**Onglets:**
- Vincent
- Place des Arts
- UQAM
- Alertes Maintenance

### ✅ Permissions vérifiées (2025-12-22)

- ✅ Lecture
- ✅ Écriture
- ✅ Suppression de lignes
- ✅ Création d'onglets

### 🔒 Sécurité

⚠️ **IMPORTANT:** Ce fichier est dans `.gitignore` et ne doit **JAMAIS** être commis dans Git.

**Fichier protégé par gitignore:**
```gitignore
data/credentials_ptm.json
```

### 💻 Utilisation dans le code

```python
from google.oauth2.service_account import Credentials
import gspread
from pathlib import Path

# Charger les credentials
credentials_path = Path(__file__).parent.parent / "data" / "credentials_ptm.json"

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_file(credentials_path, scopes=scope)
client = gspread.authorize(creds)

# Ouvrir le spreadsheet
spreadsheet = client.open("Rapport Timeline Google")
```

### 📚 Voir aussi

- [CHEMINS_FICHIERS_RAPPORTS.md](../docs/CHEMINS_FICHIERS_RAPPORTS.md) - Structure des fichiers V5
- [MIGRATION_RAPPORTS_GOOGLE_SHEETS_V5.md](../docs/MIGRATION_RAPPORTS_GOOGLE_SHEETS_V5.md) - Guide migration

---

**Copié depuis PC Windows:** 2025-12-22
**Source:** `c:\Allan Python projets\sous_projets\ptm_reports\credentials_ptm.json`
