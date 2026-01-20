# 📊 Recette Complète - Rapport Timeline v5

**Date de création :** 2026-01-19  
**Version :** 1.0  
**Auteur :** Assistant Claude + Allan Sutton

---

## 🎯 Vue d'ensemble

Le **Rapport Timeline v5** est un Google Sheet automatisé qui consolide toutes les activités de service pour les clients institutionnels (UQAM, Vincent d'Indy, Place des Arts), avec un onglet spécial pour les alertes de maintenance.

**Google Sheet :** https://docs.google.com/spreadsheets/d/1ZZsMrIT0BEwHKQ6-BKGzFoXR3k99zCEzixp0tsRKUj8

---

## 📋 Structure du Rapport

### Onglets

Le rapport contient **4 onglets** :

1. **UQAM** - Université du Québec à Montréal
2. **Vincent** - École de musique Vincent-d'Indy (2 entités)
3. **Place des Arts** - Place des Arts de Montréal
4. **Alertes Maintenance** - Alertes critiques pour tous les clients institutionnels

### Colonnes (7 au total)

| Colonne | Description | Exemple |
|---------|-------------|---------|
| **DateEvenement** | Date de l'événement (fuseau Montréal) | 2026-01-19 |
| **TypeEvenement** | Type : Service, Mesure, ou Alerte | Service |
| **Description** | Notes du technicien | Accord 440Hz, housse retirée |
| **Piano** | Infos piano regroupées | Steinway D #590097 (GRAND, 2012) |
| **Local** | Salle/Local du piano | Salle Wilfrid-Pelletier |
| **Technicien** | Prénom Nom du technicien | Nicolas Lessard |
| **MesureHumidite** | Température et humidité | 21°, 36% |

---

## 🔄 Pipeline de Génération

### 1. Source des Données

**Table Supabase :** `gazelle_timeline_entries`

**Types d'entrées récupérés :**
- `SERVICE_ENTRY_MANUAL` - Notes de service des techniciens
- `PIANO_MEASUREMENT` - Mesures de température/humidité

**Requête avec JOINs :**
```sql
SELECT 
    external_id, description, title, entry_date, occurred_at,
    entity_id, entity_type, event_type, entry_type, piano_id, user_id,
    piano:gazelle_pianos(make, model, serial_number, type, year, location, client_external_id),
    user:users(first_name, last_name)
FROM gazelle_timeline_entries
WHERE entry_type IN ('SERVICE_ENTRY_MANUAL', 'PIANO_MEASUREMENT')
ORDER BY occurred_at DESC
```

**Pagination :** 1000 entrées par page (nécessaire car base > 23,000 entrées)

---

### 2. Déduplication Critique

**Problème identifié :** Les données ont été importées **DEUX FOIS** avec des préfixes différents :
- `tle_` (ancien système d'import)
- `tme_` (nouveau système d'import)

**Solution appliquée :**

```python
# Grouper par signature (date + description)
signature = f"{date[:10]}|||{description[:200]}"

# Priorité : garder tme_ si doublon, sinon garder le premier
if len(group) > 1:
    tme_entries = [e for e in group if e.get("external_id", "").startswith("tme_")]
    if tme_entries:
        return tme_entries[0]  # Priorité au nouveau système
    else:
        return group[0]
```

**Impact :** ~4,500 doublons éliminés (19% des données)

---

### 3. Catégorisation par Client

**Mapping des clients vers les onglets :**

```python
CLIENT_KEYWORDS = {
    "UQAM": ["uqam"],
    "Vincent": ["vincent"],
    "Place des Arts": ["place des arts"],
}
```

**Logique :**
- Cherche les mots-clés dans le **nom du client** (via `client_external_id`)
- Une entrée peut apparaître dans **plusieurs onglets** si elle matche plusieurs clients

---

### 4. Détection des Alertes Maintenance

**Source de référence :** `core/humidity_alert_detector.py`

**Conditions pour l'onglet "Alertes Maintenance" :**

1. **Client institutionnel** (UQAM, Vincent, Place des Arts)
2. **+**
3. **Mot-clé d'alerte** dans la description

**Mots-clés officiels (38 au total) :**

#### 🛡️ Housse retirée (6 variantes)
```
housse retirée, housse enlevée, sans housse, pas de housse
```

#### ⚡ Dampp-Chaser / Alimentation (13 variantes)
```
dampp chaser débranché, dampp-chaser débranché, dampp chaser off,
dampp chaser éteint, dampp chaser ne fonctionne, pls débranché,
système débranché, débranché, rebranché, rallonge, besoin rallonge
```

#### 💧 Réservoir (4 variantes)
```
réservoir vide, reservoir vide, tank empty, réservoir à remplir
```

#### 🌡️ Environnement critique (7 variantes)
```
fenêtre ouverte, fenetre ouverte, température trop basse,
trop froid, humidité trop élevée, humidité très basse,
conditions inadéquates
```

#### 💦 Humidité extrême (8 variantes)
```
humidité haute, humidité élevée, très humide, trop humide,
humidité basse, humidité faible, très sec, trop sec
```

**Important :** Les mots-clés génériques comme "temp" ou "humidité" seuls sont **exclus** pour éviter les faux positifs sur les mesures normales.

---

### 5. Extraction des Mesures

**Sources :**
1. **Description du service** - Parsing regex pour trouver °C et %
2. **Entrées PIANO_MEASUREMENT** - Mesures automatiques du même piano + même jour

**Formats détectés :**
```
20C, 33%
20°C, 33%
23° Celsius, humidité relative 35%
68F, 40% (Fahrenheit)
```

**Logique de priorisation :**
- Si **mesure complète** (température + humidité) → utiliser celle-là
- Sinon, si **humidité seule** → utiliser l'humidité
- Dédupliquer si plusieurs mesures identiques

**Groupement par piano+date :**
```python
key = (piano_id, date_only)
measurements_by_piano_date[key] = [mesures...]
```

---

### 6. Formatage de la Colonne "Piano"

**Fonction :** `_format_piano_info(make, model, serial, piano_type, year)`

**Logique :**

```python
# 1. Marque + Modèle
if make and model:
    parts.append(f"{make} {model}")

# 2. Numéro de série
if serial:
    parts.append(f"#{serial}")

# 3. Type et Année entre parenthèses
if piano_type or year:
    parts.append(f"({type}, {year})")
```

**Exemples de sortie :**
- `Steinway D #590097 (GRAND, 2012)`
- `Yamaha C2 #6570952 (GRAND, 2023)`
- `Mason & Hamlin (UPRIGHT)`
- `Roland HP-2-PE #ZR10850 (DIGITAL)`

---

### 7. Conversion de Fuseau Horaire

**Source :** UTC (Supabase)  
**Destination :** America/Montreal (fuseau local)

```python
from zoneinfo import ZoneInfo
MONTREAL_TZ = ZoneInfo("America/Montreal")

dt = datetime.fromisoformat(occurred_at)
if dt.tzinfo is None:
    dt = dt.replace(tzinfo=timezone.utc)
date_montreal = dt.astimezone(MONTREAL_TZ).strftime("%Y-%m-%d")
```

---

### 8. Insertion dans Google Sheets

**Méthode :** `append_rows()` (batch)

**Pourquoi pas `insert_rows()` ?**
- `insert_rows()` créait des bugs de duplication
- `append_rows()` ajoute à la fin, plus fiable

**Gestion des doublons :**
```python
# Si append=True (mode incrémental)
existing_signatures = _get_existing_row_signatures(ws)
new_rows = _filter_duplicate_rows(rows, existing_signatures)

# Signature : date + description (200 premiers chars)
signature = f"{row[0]}|||{row[2][:200]}"
```

**Mode REPLACE (append=False) :**
- Clear complet de la feuille
- Recréation de l'en-tête
- Insertion de toutes les lignes

---

## ⏰ Planification Automatique

### Scheduler

**Fichier :** `core/scheduler.py`

**Job configuré :**
```python
scheduler.add_job(
    task_generate_rapport_timeline,
    trigger='cron',
    hour=2,
    minute=0,
    timezone=pytz.timezone('America/Montreal'),
    id='rapport_timeline_daily'
)
```

**Fréquence :** Tous les jours à **02:00 AM** (Montréal)

**Mode :** Incrémental (`append=True`)
- Récupère seulement les entrées depuis la dernière exécution
- Évite les doublons grâce aux signatures
- Paramètre `reports_timeline_last_run` stocké dans `system_settings`

---

## 🔧 Architecture du Code

### Fichiers Principaux

```
modules/reports/service_reports.py          # Moteur principal du rapport
core/scheduler.py                           # Planification automatique
core/humidity_alert_detector.py             # Définition des mots-clés d'alertes
```

### Classes et Fonctions Clés

#### `ServiceReports` (classe principale)

```python
class ServiceReports:
    def __init__(self, storage, sheet_name, credentials_path):
        """Initialise connexion Supabase et Google Sheets"""
    
    def generate_reports(self, since=None, append=True):
        """Point d'entrée principal - génère le rapport complet"""
    
    def _fetch_timeline_entries(self, since):
        """Récupère timeline entries avec pagination"""
    
    def _build_rows_from_timeline(self, entries, clients_map):
        """Construit les lignes du rapport avec toute la logique"""
    
    def _categories_for_entry(self, client_name, description):
        """Détermine les onglets cibles (UQAM, Vincent, etc.)"""
    
    def _format_piano_info(self, make, model, serial, type, year):
        """Formate la colonne Piano regroupée"""
    
    def _extract_measurements_from_text(self, text):
        """Parse température et humidité avec regex"""
```

#### Fonction utilitaire

```python
def run_reports(since=None, append=True):
    """Entrypoint simple pour exécution manuelle"""
    service = ServiceReports()
    return service.generate_reports(since=since, append=append)
```

---

## 🚀 Utilisation

### Génération Manuelle Complète

```python
from modules.reports.service_reports import run_reports

# Mode REPLACE : tout regénérer depuis le début
result = run_reports(since=None, append=False)

print(result)
# {'UQAM': 29, 'Vincent': 1740, 'Place des Arts': 153, 'Alertes Maintenance': 56}
```

### Génération Incrémentale

```python
from datetime import datetime, timedelta

# Récupérer seulement les 7 derniers jours
since = datetime.now() - timedelta(days=7)
result = run_reports(since=since, append=True)
```

### Ligne de Commande

```bash
cd /Users/allansutton/Documents/assistant-gazelle-v5

# Génération complète
python3 -c "from modules.reports.service_reports import run_reports; run_reports(since=None, append=False)"

# Génération incrémentale (7 derniers jours)
python3 -c "
from modules.reports.service_reports import run_reports
from datetime import datetime, timedelta
run_reports(since=datetime.now()-timedelta(days=7), append=True)
"
```

---

## 📊 Statistiques Actuelles

**Données dans Supabase :**
- Total entrées : 23,869
- Après déduplication : 19,342 (-19%)
- Période couverte : 2016-2026

**Répartition par onglet :**
- **UQAM** : 29 entrées
- **Vincent** : 1,740 entrées
- **Place des Arts** : 153 entrées
- **Alertes Maintenance** : 56 alertes

**Performance :**
- Temps de génération complète : ~23 secondes
- Pagination : 24 pages × 1000 entrées

---

## 🔍 Troubleshooting

### Problème : Doublons dans le rapport

**Symptôme :** Mêmes lignes apparaissent 2 fois

**Cause :** Données importées avec `tle_` et `tme_` (deux systèmes)

**Solution :** Déjà appliquée - déduplication automatique par signature (date + description)

### Problème : Alertes manquantes

**Vérifier :**
1. Le client est-il institutionnel ? (UQAM, Vincent, Place des Arts)
2. Le mot-clé est-il dans la liste officielle ? (voir `core/humidity_alert_detector.py`)
3. Le mot-clé est-il dans la description de l'entrée ?

**Test manuel :**
```python
from modules.reports.service_reports import ServiceReports

service = ServiceReports()
text = "École de musique Vincent-d'Indy debranché"
tabs = service._categories_for_entry("Vincent", text)
print(tabs)  # Devrait inclure 'Alertes Maintenance'
```

### Problème : Rapport pas mis à jour automatiquement

**Vérifier :**
1. Le backend est-il en cours d'exécution ?
2. Le scheduler est-il actif ?

```bash
# Vérifier les logs du scheduler
grep "rapport_timeline_daily" logs/scheduler.log

# Forcer une exécution manuelle
python3 -c "from modules.reports.service_reports import run_reports; run_reports()"
```

### Problème : Mesures d'humidité manquantes

**Causes possibles :**
1. Format non reconnu par le regex
2. Mesure et service sur des jours différents
3. Piano_id manquant

**Formats supportés :**
- `20C, 33%` ✅
- `20°, 33%` ✅
- `Température 20°, humidité 33%` ✅
- `juste 33%` ⚠️ (humidité seule, accepté)

---

## 🎓 Historique des Modifications

### Version 1.0 (2026-01-19)

**Changements majeurs :**

1. ✅ **Pagination complète** - 24 pages au lieu de 1000 entrées max
2. ✅ **Déduplication tle_/tme_** - Élimine 4,527 doublons
3. ✅ **Colonne Piano regroupée** - 5 colonnes → 1 colonne lisible
4. ✅ **Suppression NomClient** - Redondant dans chaque onglet
5. ✅ **Mots-clés alertes officiels** - 38 mots-clés de `humidity_alert_detector.py`
6. ✅ **Filtrage strict alertes** - Seulement clients institutionnels
7. ✅ **Structure finale** - 7 colonnes (vs 12 à l'origine)

**Réduction :** 42% de colonnes en moins !

---

## 📚 Références

**Fichiers sources :**
- `modules/reports/service_reports.py` - Code principal
- `core/scheduler.py` - Planification
- `core/humidity_alert_detector.py` - Mots-clés alertes
- `v6/RAPPORT_TIMELINE_V5_RECETTE.md` - Ce document

**Documentation liée :**
- `docs/INTEGRATION_ALERTES_HUMIDITE_COMPLETE.md` - Système d'alertes
- `docs/GUIDE_ACTIVATION_ALERTES_HUMIDITE.md` - Activation alertes

**Google Sheet :**
- https://docs.google.com/spreadsheets/d/1ZZsMrIT0BEwHKQ6-BKGzFoXR3k99zCEzixp0tsRKUj8

---

## ✅ Checklist de Maintenance

### Mensuel
- [ ] Vérifier que le rapport se génère automatiquement (check logs à 02h00)
- [ ] Valider que les stats correspondent (~1,740 entrées Vincent)
- [ ] Vérifier absence de doublons dans les onglets

### Trimestriel
- [ ] Revoir les mots-clés d'alertes (nouveaux cas ?)
- [ ] Valider la déduplication (nouveaux préfixes ?)
- [ ] Optimiser les performances si >50,000 entrées

### Annuel
- [ ] Archiver l'ancien rapport (créer une copie datée)
- [ ] Nettoyer les anciennes entrées (>10 ans)

---

**Document créé le :** 2026-01-19  
**Dernière mise à jour :** 2026-01-19  
**Maintenu par :** Allan Sutton
