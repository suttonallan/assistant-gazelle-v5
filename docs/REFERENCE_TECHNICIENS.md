# Référence: Techniciens Piano Technique Montréal

## 📋 Vue d'ensemble

Ce document centralise toutes les informations sur les techniciens pour la migration V5.

---

## 👥 TECHNICIENS ACTIFS

### 1. Allan Sutton

| Propriété | Valeur |
|-----------|--------|
| **Gazelle ID** | `usr_ofYggsCDt2JAVeNP` |
| **Email** | `asutton@piano-tek.com` |
| **Alias email** | `allan@piano-tek.com` |
| **Nom complet** | Allan Sutton |
| **Rôle** | Admin / Technicien |
| **Adresse domicile** | 780 Lanthier, Montréal, QC H4N 2A1 |

### 2. Nicolas Lessard

| Propriété | Valeur |
|-----------|--------|
| **Gazelle ID** | `usr_HcCiFk7o0vZ9xAI0` |
| **Email** | `nlessard@piano-tek.com` |
| **Alias email** | `nicolas@piano-tek.com` |
| **Nom complet** | Nicolas Lessard |
| **Rôle** | Technicien |
| **Adresse domicile** | 3520A Rue Sainte-Famille, Montréal, QC |

### 3. Jean-Philippe Reny

| Propriété | Valeur |
|-----------|--------|
| **Gazelle ID** | `usr_ReUSmIJmBF86ilY1` |
| **Email** | `jpreny@gmail.com` |
| **Nom complet** | Jean-Philippe Reny |
| **Alias** | `jeanphilippe`, `jp` |
| **Rôle** | Technicien |
| **Adresse domicile** | 2127 Rue Saint-André, Montréal, QC |

### 4. Louise (Assistante)

| Propriété | Valeur |
|-----------|--------|
| **Gazelle ID** | `usr_aCJfmM8WZHShuCIM` |
| **Email** | `louise@piano-tek.com` |
| **Nom complet** | Louise |
| **Rôle** | Assistante administrative |
| **Note** | **PAS un technicien** - Ne reçoit pas d'alertes RV, pas d'adresse domicile nécessaire |

---

## 🗂️ Mapping Python pour V5

### Dictionnaire principal (ID → Infos)

```python
TECHNICIANS = {
    'usr_ofYggsCDt2JAVeNP': {
        'name': 'Allan',
        'full_name': 'Allan Sutton',
        'email': 'asutton@piano-tek.com',
        'role': 'admin',
        'home_address': '780 Lanthier, Montréal, QC H4N 2A1'
    },
    'usr_HcCiFk7o0vZ9xAI0': {
        'name': 'Nicolas',
        'full_name': 'Nicolas Lessard',
        'email': 'nlessard@piano-tek.com',
        'role': 'technician',
        'home_address': '3520A Rue Sainte-Famille, Montréal, QC'
    },
    'usr_ReUSmIJmBF86ilY1': {
        'name': 'Jean-Philippe',
        'full_name': 'Jean-Philippe Reny',
        'email': 'jpreny@gmail.com',
        'role': 'technician',
        'home_address': '2127 Rue Saint-André, Montréal, QC'
    },
    'usr_aCJfmM8WZHShuCIM': {
        'name': 'Louise',
        'full_name': 'Louise',
        'email': 'louise@piano-tek.com',
        'role': 'assistant',
        'home_address': None  # Pas un technicien
    }
}
```

### Mapping nom → ID (pour recherches)

```python
TECHNICIAN_IDS = {
    'allan': 'usr_ofYggsCDt2JAVeNP',
    'nicolas': 'usr_HcCiFk7o0vZ9xAI0',
    'jeanphilippe': 'usr_ReUSmIJmBF86ilY1',
    'jp': 'usr_ReUSmIJmBF86ilY1',  # Alias
    'louise': 'usr_aCJfmM8WZHShuCIM'
}
```

### Mapping ID → nom (pour affichage)

```python
ID_TO_NAME = {
    'usr_ofYggsCDt2JAVeNP': 'Allan',
    'usr_HcCiFk7o0vZ9xAI0': 'Nicolas',
    'usr_ReUSmIJmBF86ilY1': 'Jean-Philippe',
    'usr_aCJfmM8WZHShuCIM': 'Louise'
}
```

---

## 📧 Configuration Email (Environment Variables)

Pour le système d'alertes V5, ajouter au `.env`:

```env
# Techniciens - Alertes RV non confirmés
TECH_usr_ofYggsCDt2JAVeNP_NAME=Allan
TECH_usr_ofYggsCDt2JAVeNP_EMAIL=asutton@piano-tek.com

TECH_usr_HcCiFk7o0vZ9xAI0_NAME=Nicolas
TECH_usr_HcCiFk7o0vZ9xAI0_EMAIL=nlessard@piano-tek.com

TECH_usr_ReUSmIJmBF86ilY1_NAME=Jean-Philippe
TECH_usr_ReUSmIJmBF86ilY1_EMAIL=jpreny@gmail.com

# Louise (assistante - optionnel)
TECH_usr_aCJfmM8WZHShuCIM_NAME=Louise
TECH_usr_aCJfmM8WZHShuCIM_EMAIL=louise@piano-tek.com

# Email expéditeur
FROM_EMAIL=info@piano-tek.com
FROM_NAME=Piano Technique Montréal
ADMIN_EMAIL=asutton@piano-tek.com
```

---

## 🗄️ Structure Table `users` Supabase

Pour remplacer le mapping hardcodé, créer une table `users`:

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    gazelle_user_id TEXT UNIQUE NOT NULL,
    username TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'technician', 'assistant')),
    home_address TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insérer les techniciens
INSERT INTO users (gazelle_user_id, username, full_name, email, role, home_address) VALUES
('usr_ofYggsCDt2JAVeNP', 'allan', 'Allan Sutton', 'asutton@piano-tek.com', 'admin', '780 Lanthier, Montréal, QC H4N 2A1'),
('usr_HcCiFk7o0vZ9xAI0', 'nicolas', 'Nicolas Lessard', 'nlessard@piano-tek.com', 'technician', '3520A Rue Sainte-Famille, Montréal, QC'),
('usr_ReUSmIJmBF86ilY1', 'jeanphilippe', 'Jean-Philippe Reny', 'jpreny@gmail.com', 'technician', '2127 Rue Saint-André, Montréal, QC'),
('usr_aCJfmM8WZHShuCIM', 'louise', 'Louise', 'louise@piano-tek.com', 'assistant', NULL);

-- Index pour recherches rapides
CREATE INDEX idx_users_gazelle_id ON users(gazelle_user_id);
CREATE INDEX idx_users_username ON users(username);
```

---

## 🔍 Requêtes Utiles

### Récupérer email d'un technicien

```python
# Via SupabaseStorage
from modules.core.storage import SupabaseStorage

storage = SupabaseStorage()
user = storage.client.table('users').select('email').eq('gazelle_user_id', 'usr_HcCiFk7o0vZ9xAI0').single().execute()
tech_email = user.data['email']  # nlessard@piano-tek.com
```

### Récupérer tous les techniciens actifs

```python
technicians = storage.client.table('users').select('*').in_('role', ['admin', 'technician']).eq('is_active', True).execute()

for tech in technicians.data:
    print(f"{tech['full_name']} ({tech['gazelle_user_id']}): {tech['email']}")
```

---

## 📍 Google Maps - Adresses Domicile

Pour calcul de kilométrage (voir [CONFIG_GOOGLE_MAPS.md](CONFIG_GOOGLE_MAPS.md)):

```python
HOME_BY_TECH = {
    "Allan Sutton": "780 Lanthier, Montréal, QC H4N 2A1",
    "Nicolas Lessard": "3520A Rue Sainte-Famille, Montréal, QC",
    "Jean-Philippe Reny": "2127 Rue Saint-André, Montréal, QC"
}

# Ou via Gazelle ID
HOME_BY_GAZELLE_ID = {
    "usr_ofYggsCDt2JAVeNP": "780 Lanthier, Montréal, QC H4N 2A1",
    "usr_HcCiFk7o0vZ9xAI0": "3520A Rue Sainte-Famille, Montréal, QC",
    "usr_ReUSmIJmBF86ilY1": "2127 Rue Saint-André, Montréal, QC"
}
```

---

## ⚠️ ATTENTION: IDs Gazelle Historiques

**NE PAS UTILISER** ces anciens IDs trouvés dans des fichiers archivés:

| Nom | ❌ Ancien ID (INVALIDE) | ✅ ID Actuel (CORRECT) |
|-----|-------------------------|------------------------|
| Allan | `usr_QHPg6jTVYWdLDgMz` | `usr_ofYggsCDt2JAVeNP` |
| Nicolas | `usr_U9E5bLxrFiXqTbE8` | `usr_HcCiFk7o0vZ9xAI0` |

**Source de vérité:** `check_unconfirmed_appointments.py` (fichier le plus récent et actif)

---

## 📝 Notes Migration V5

1. **Pour Job 16h00 (alertes RV non confirmés):**
   - Utiliser le mapping `TECHNICIANS` ci-dessus
   - Filtrer seulement les techniciens actifs (exclure Louise)
   - Envoyer emails aux adresses principales (`asutton@`, `nlessard@`, `jpreny@`)

2. **Pour Résumés quotidiens:**
   - Utiliser adresses domicile pour calcul de distance (Google Maps)
   - Exclure Louise (pas de RV technicien)

3. **Pour Assistant conversationnel:**
   - Supporter alias: `jp` → `jeanphilippe`
   - Mapping nom → ID pour recherches
   - Mapping ID → nom pour affichage

4. **Option Base de données (recommandé):**
   - Créer table `users` dans Supabase
   - Éviter hardcoding
   - Facilite ajout/modification de techniciens
   - Permet gestion via API/dashboard

---

**Créé:** 2025-12-20
**Par:** Claude Code (Windows)
**Pour:** Cursor Mac - Migration V5
**Source:** check_unconfirmed_appointments.py, email_config.py, calcul_kilometres_trimestre.py
