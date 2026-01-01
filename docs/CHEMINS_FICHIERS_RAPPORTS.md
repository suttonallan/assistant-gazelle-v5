# Chemins des fichiers - Rapports Google Sheets

## 📁 Localisation des fichiers V4 et V5

### 🖥️ Fichiers V4 (PC Windows)

#### Script principal Timeline
**Chemin complet:**
```
c:\Allan Python projets\sous_projets\ptm_reports\ptm_report_sheets.py
```

**Dossier:**
```
c:\Allan Python projets\sous_projets\ptm_reports\
```

**Structure V4:**
```
sous_projets/ptm_reports/
├── ptm_report_sheets.py          # Script principal timeline (297 lignes)
├── credentials_ptm.json           # Google Service Account
└── README.md                      # Documentation
```

#### Rapport Alertes Maintenance
**Chemin complet:**
```
c:\Allan Python projets\maintenance_alerts_report.py
```

---

### 🍎 Fichiers de référence V4 (Déjà copiés dans Mac)

**Fichiers copiés dans `reference_v4/`:**
```
assistant-gazelle-v5/reference_v4/
├── ptm_report_sheets.py           # ✅ Copié depuis PC
├── maintenance_alerts_report.py   # ✅ Copié depuis PC
└── (autres fichiers Place des Arts...)
```

**Credentials copiés:**
```
assistant-gazelle-v5/data/
└── credentials_ptm.json           # ✅ Copié depuis PC
```

---

### 🆕 Structure V5 à créer (Cursor Mac)

#### Dossier modules/reports/

**Créer cette structure:**
```
assistant-gazelle-v5/modules/reports/
├── __init__.py                    # Module init
├── timeline_report.py             # ← CRÉER (adapté de ptm_report_sheets.py)
├── alerts_report.py               # ← CRÉER (adapté de maintenance_alerts_report.py)
└── google_sheets_client.py        # ← CRÉER (client Google Sheets réutilisable)
```

#### API endpoints

**Créer:**
```
assistant-gazelle-v5/api/reports.py
```

**Endpoints à implémenter:**
- `POST /api/reports/timeline` - Générer rapport timeline
- `POST /api/reports/alerts` - Générer rapport alertes
- `GET /api/reports/status` - Statut dernière exécution

---

## 📋 Mapping V4 → V5

### timeline_report.py (V5)

**Source V4:**
```
reference_v4/ptm_report_sheets.py
```

**Adapter:**
1. Remplacer `pyodbc` → `SupabaseStorage`
2. Remplacer requête SQL → query Supabase avec filtres
3. Garder logique regroupement services + mesures
4. Garder conversion timezone UTC → Montreal
5. Garder upload Google Sheets (identique)

**Fonction principale:**
```python
# V4 (ligne 58-143)
def get_institution_data(conn, filter_sql):
    """Version finale avec une logique d'association robuste (groupby/merge) par DATE."""
    # SQL query avec LEFT JOIN Pianos, Clients, Users
    # Agrégation mesures par piano + date
    # Fusion avec services

# V5 (à créer)
def get_institution_data(storage, institution_filter):
    """Version V5 avec Supabase - même logique"""
    # Query Supabase avec .select().eq().gte()
    # Même agrégation mesures
    # Même logique de fusion
```

---

### alerts_report.py (V5)

**Source V4:**
```
reference_v4/maintenance_alerts_report.py
```

**Adapter:**
1. Remplacer SQL Server → Supabase
2. Créer table `maintenance_alerts` si nécessaire
3. Même format Google Sheets

---

### google_sheets_client.py (V5)

**Réutilisable pour les 2 rapports:**

```python
from google.oauth2.service_account import Credentials
import gspread
from pathlib import Path

class GoogleSheetsClient:
    """Client Google Sheets réutilisable pour tous les rapports"""

    def __init__(self, credentials_path: str = None):
        if not credentials_path:
            credentials_path = Path(__file__).parent.parent / "data" / "credentials_ptm.json"

        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_file(credentials_path, scopes=scope)
        self.client = gspread.authorize(creds)

    def open_spreadsheet(self, name: str):
        """Ouvre un spreadsheet par nom"""
        return self.client.open(name)

    def update_worksheet(self, spreadsheet, sheet_name: str, df):
        """Met à jour un onglet avec un DataFrame"""
        # Code de ptm_report_sheets.py lignes 155-184
        pass
```

---

## 🔐 Credentials Google Sheets

**Service Account:**
- **Email:** `pianosheets-bot@piano-sheets-471218.iam.gserviceaccount.com`
- **Project:** `piano-sheets-471218`
- **Fichier:** `data/credentials_ptm.json` ✅ Déjà copié

**Google Sheet:**
- **Nom:** "Rapport Timeline Google"
- **ID:** `1Y2Ggi2O1aTVa-lsyhl88FF6XWCTRs6h_DIYwYUEZjV8`
- **URL:** https://docs.google.com/spreadsheets/d/1Y2Ggi2O1aTVa-lsyhl88FF6XWCTRs6h_DIYwYUEZjV8

**Onglets existants:**
- Vincent
- Place des Arts
- UQAM
- Alertes Maintenance

**Permissions vérifiées:**
- ✅ Lecture
- ✅ Écriture
- ✅ Suppression
- ✅ Création d'onglets

---

## 🎯 Instructions pour Cursor Mac

### Étape 1: Créer la structure

```bash
# Dans assistant-gazelle-v5/
mkdir -p modules/reports
touch modules/reports/__init__.py
touch modules/reports/google_sheets_client.py
touch modules/reports/timeline_report.py
touch modules/reports/alerts_report.py
touch api/reports.py
```

### Étape 2: Implémenter google_sheets_client.py

**Code de base disponible dans:**
- `reference_v4/ptm_report_sheets.py` lignes 145-198

**Adapter:**
- Classe réutilisable
- Gestion erreurs
- Logging

### Étape 3: Implémenter timeline_report.py

**Logique principale:**
```python
from modules.core.storage import SupabaseStorage
from modules.reports.google_sheets_client import GoogleSheetsClient
import pandas as pd

def generate_timeline_report():
    """Génère le rapport timeline - V5"""

    # 1. Connexion Supabase
    storage = SupabaseStorage()

    # 2. Pour chaque institution
    institutions = {
        "UQAM": "company_name.ilike.%UQAM%,company_name.ilike.%Pierre-Péladeau%",
        "Vincent": "company_name.ilike.%Vincent-d'Indy%",
        "Place des Arts": "company_name.ilike.%Place des Arts%"
    }

    # 3. Récupérer données Supabase (depuis timeline_entries + pianos + clients)
    for sheet_name, filter_query in institutions.items():
        df = get_institution_data(storage, filter_query)

        # 4. Upload vers Google Sheets
        sheets_client = GoogleSheetsClient()
        spreadsheet = sheets_client.open_spreadsheet("Rapport Timeline Google")
        sheets_client.update_worksheet(spreadsheet, sheet_name, df)
```

**Référence V4:**
- `reference_v4/ptm_report_sheets.py` lignes 58-143 (logique SQL)
- Adapter pour Supabase queries

### Étape 4: Implémenter alerts_report.py

**Référence V4:**
- `reference_v4/maintenance_alerts_report.py`

**Table Supabase:**
```sql
CREATE TABLE IF NOT EXISTS maintenance_alerts (
    id TEXT PRIMARY KEY,
    piano_id TEXT REFERENCES gazelle_pianos(id),
    client_name TEXT,
    alert_type TEXT,
    description TEXT,
    severity TEXT,
    created_at TIMESTAMPTZ,
    resolved BOOLEAN DEFAULT false
);
```

### Étape 5: Créer API endpoints

**Fichier:** `api/reports.py`

```python
from fastapi import APIRouter
from modules.reports.timeline_report import generate_timeline_report
from modules.reports.alerts_report import generate_alerts_report

router = APIRouter(prefix="/api/reports", tags=["reports"])

@router.post("/timeline")
async def create_timeline_report():
    """Génère le rapport timeline Google Sheets"""
    result = generate_timeline_report()
    return {"success": True, "message": "Rapport timeline généré"}

@router.post("/alerts")
async def create_alerts_report():
    """Génère le rapport alertes maintenance"""
    result = generate_alerts_report()
    return {"success": True, "message": "Rapport alertes généré"}
```

---

## ✅ Checklist de migration

- [ ] Créer dossier `modules/reports/`
- [ ] Implémenter `google_sheets_client.py`
- [ ] Implémenter `timeline_report.py` (adapter SQL → Supabase)
- [ ] Implémenter `alerts_report.py`
- [ ] Créer table `maintenance_alerts` dans Supabase
- [ ] Créer endpoints API dans `api/reports.py`
- [ ] Tester génération rapport V5
- [ ] Comparer output V4 vs V5
- [ ] Valider identiques
- [ ] Documentation

---

## 📚 Documentation de référence

**Voir aussi:**
- [MIGRATION_RAPPORTS_GOOGLE_SHEETS_V5.md](MIGRATION_RAPPORTS_GOOGLE_SHEETS_V5.md) - Guide complet migration
- [reference_v4/ptm_report_sheets.py](../reference_v4/ptm_report_sheets.py) - Code source V4 timeline
- [reference_v4/maintenance_alerts_report.py](../reference_v4/maintenance_alerts_report.py) - Code source V4 alertes

---

**Créé:** 2025-12-22
**Par:** Claude Code (Windows)
**Pour:** Cursor Mac
**Statut:** ✅ PRÊT - Tous les chemins documentés
