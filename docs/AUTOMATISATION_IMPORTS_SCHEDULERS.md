# 🔄 Automatisation des Imports et Schedulers - Assistant Gazelle V5

**Date:** 2025-12-28
**Objectif:** Automatiser tous les imports de données Gazelle → Supabase et les tâches planifiées

---

## 📋 RÉSUMÉ EXÉCUTIF

### Tâches Automatisées Actuellement

| Tâche | Horaire | Statut | Fichier |
|-------|---------|--------|---------|
| **Rapport Timeline Google Sheets** | 02:00 | ✅ Automatisé | `api/reports.py` |
| **Alertes RV non confirmés (court terme)** | 16:00 | ✅ Automatisé | `api/alertes_rv.py` |
| **Alertes RV non confirmés (long terme)** | 09:00 | ✅ Automatisé | `api/alertes_rv.py` |

### Tâches à Automatiser

| Tâche | Fréquence | Priorité | Script |
|-------|-----------|----------|--------|
| **Sync Gazelle → Supabase** | Toutes les 2h | 🔴 CRITIQUE | `modules/sync_gazelle/sync_to_supabase.py` |
| **Backup Supabase** | Quotidien 03:00 | 🟡 Important | `scripts/backup_db.py` |

---

## 🔄 IMPORT 1: Synchronisation Gazelle → Supabase

### Description
Synchronise toutes les données depuis l'API Gazelle vers Supabase (clients, contacts, pianos, appointments, timeline).

### Fichier
`modules/sync_gazelle/sync_to_supabase.py`

### Tables Synchronisées
1. **gazelle_clients** - Informations clients
2. **gazelle_contacts** - Contacts associés aux clients
3. **gazelle_pianos** - Inventaire des pianos
4. **gazelle_appointments** - Rendez-vous des techniciens
5. **gazelle_timeline_entries** - Historique des services et mesures

### Fréquence Recommandée
**Toutes les 2 heures** (de 06:00 à 22:00)

**Horaires:** 06:00, 08:00, 10:00, 12:00, 14:00, 16:00, 18:00, 20:00, 22:00

### Pourquoi ?
- Les techniciens ajoutent des services durant la journée
- Les rendez-vous sont confirmés/modifiés en temps réel
- L'assistant conversationnel a besoin de données à jour
- Les rapports doivent refléter les dernières entrées

### Usage
- ✅ **Assistant conversationnel** (questions sur clients, pianos, RV)
- ✅ **Place des Arts** (demandes de rendez-vous)
- ✅ **Rapport Timeline** (données de services)
- ✅ **Alertes RV** (rendez-vous non confirmés)
- ✅ **Calcul frais de déplacement** (adresses clients)
- ✅ **Inventaire** (pianos actifs)

### Impact si non automatisé
🔴 **CRITIQUE** - Sans sync régulière:
- Assistant répond avec données obsolètes
- Rapport Timeline manque les derniers services
- Alertes RV ne détectent pas nouveaux RV
- Place des Arts affiche inventaire périmé

### Commande Manuelle
```bash
cd /Users/allansutton/Documents/assistant-gazelle-v5
python3 modules/sync_gazelle/sync_to_supabase.py
```

### Durée d'Exécution
- **Sync partielle (depuis last run):** ~30-60 secondes
- **Sync complète (full refresh):** ~2-5 minutes

### Dépendances
- ✅ Token OAuth Gazelle valide (renouvelé auto)
- ✅ Variables d'environnement Supabase
- ✅ Connexion Internet

---

## 📊 IMPORT 2: Rapport Timeline Google Sheets

### Description
Génère le rapport timeline avec les services et mesures dans Google Sheets (4 onglets: UQAM, Vincent, Place des Arts, Alertes Maintenance).

### Fichier
`api/reports.py` + `modules/reports/service_reports.py`

### Fréquence Actuelle
**02:00 quotidien** ✅ (déjà automatisé via APScheduler)

### Données Sources
- `gazelle_timeline_entries` (services + mesures)
- `gazelle_pianos` (infos piano)
- `gazelle_clients` (noms clients)
- `users` (techniciens)

### Mode de Fonctionnement
- **Append mode** (défaut): Ajoute seulement les nouvelles entrées depuis last run
- **Full refresh mode**: Régénère complètement les 4 onglets

### Google Sheet
- **Nom:** "Rapport Timeline de l'assistant v5"
- **ID:** 1ZZsMrIT0BEwHKQ6-BKGzFoXR3k99zCEzixp0tsRKUj8
- **Credentials:** `data/credentials_ptm.json`

### Colonnes (12)
1. DateEvenement
2. TypeEvenement
3. Description
4. NomClient
5. Marque
6. Modele
7. NumeroSerie
8. TypePiano
9. Annee
10. Local
11. Technicien
12. MesureHumidite

### Endpoint Manuel
```bash
# Append mode (nouvelles entrées seulement)
curl -X POST "http://localhost:8000/api/reports/timeline/generate?full_refresh=false"

# Full refresh (tout régénérer)
curl -X POST "http://localhost:8000/api/reports/timeline/generate?full_refresh=true"
```

### Statut
✅ **AUTOMATISÉ** - Tourne à 02:00 tous les jours

---

## 📧 IMPORT 3: Alertes RV Non Confirmés

### Description
Vérifie les rendez-vous non confirmés et envoie des emails d'alerte aux techniciens.

### Fichier
`api/alertes_rv.py` + `modules/alertes_rv/`

### Fréquence Actuelle
✅ **Automatisé** avec 2 jobs:

1. **Court terme (demain)**: 16:00 quotidien
   - Vérifie les RV de demain non confirmés
   - Envoie alertes immédiates

2. **Long terme (semaine)**: 09:00 quotidien
   - Vérifie les RV de la semaine non confirmés
   - Alerte préventive

### Données Sources
- `gazelle_appointments` (rendez-vous)
- `users` (techniciens + emails)

### Méthode d'Envoi
- **SendGrid API** (production)
- **SMTP** (dev/test)

### Endpoints Manuels
```bash
# Vérifier RV non confirmés (sans envoyer)
curl -X POST "http://localhost:8000/alertes-rv/check"

# Envoyer alertes manuellement
curl -X POST "http://localhost:8000/alertes-rv/send" \
  -H "Content-Type: application/json" \
  -d '{"triggered_by": "admin@example.com"}'
```

### Statut
✅ **AUTOMATISÉ** - Court terme 16:00, Long terme 09:00

---

## 💾 IMPORT 4: Backup Supabase

### Description
Sauvegarde complète de la base de données Supabase (dump SQL).

### Fichier
`scripts/backup_db.py`

### Fréquence Recommandée
**03:00 quotidien** (après le rapport timeline)

### Pourquoi 03:00 ?
- Après le rapport timeline (02:00)
- Avant le début de journée (pas d'activité utilisateur)
- Minimise la charge sur Supabase

### Tables Sauvegardées
- Toutes les tables `gazelle_*`
- Table `users`
- Table `produits_catalogue`
- Autres tables critiques

### Destination Backup
À définir:
- Option 1: Google Drive
- Option 2: AWS S3
- Option 3: Stockage local + Git LFS
- Option 4: Supabase Storage

### Commande Manuelle
```bash
cd /Users/allansutton/Documents/assistant-gazelle-v5
python3 scripts/backup_db.py
```

### Statut
❌ **À AUTOMATISER**

---

## 🕐 PLANNING QUOTIDIEN COMPLET

### Horaire Optimal

| Heure | Tâche | Durée | Description |
|-------|-------|-------|-------------|
| **02:00** | 📊 Rapport Timeline | ~5 min | Génération Google Sheets (append mode) |
| **03:00** | 💾 Backup Supabase | ~10 min | Sauvegarde complète DB |
| **06:00** | 🔄 Sync Gazelle | ~1 min | Import données (partiel) |
| **08:00** | 🔄 Sync Gazelle | ~1 min | Import données (partiel) |
| **09:00** | 📧 Alertes RV (long terme) | ~2 min | Emails semaine prochaine |
| **10:00** | 🔄 Sync Gazelle | ~1 min | Import données (partiel) |
| **12:00** | 🔄 Sync Gazelle | ~1 min | Import données (partiel) |
| **14:00** | 🔄 Sync Gazelle | ~1 min | Import données (partiel) |
| **16:00** | 📧 Alertes RV (court terme) | ~2 min | Emails demain |
| **16:00** | 🔄 Sync Gazelle | ~1 min | Import données (partiel) |
| **18:00** | 🔄 Sync Gazelle | ~1 min | Import données (partiel) |
| **20:00** | 🔄 Sync Gazelle | ~1 min | Import données (partiel) |
| **22:00** | 🔄 Sync Gazelle | ~1 min | Import données (partiel - dernier) |

### Weekends
- **Sync Gazelle**: Seulement 08:00, 12:00, 18:00
- **Alertes RV**: Normales (16:00 + 09:00)
- **Rapport Timeline**: Normal (02:00)
- **Backup**: Normal (03:00)

---

## 🔧 IMPLÉMENTATION: Scheduler Centralisé

### Nouveau Fichier à Créer
`api/scheduler.py`

### Architecture
```python
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import pytz

# Import des fonctions à scheduler
from modules.sync_gazelle.sync_to_supabase import GazelleToSupabaseSync
from modules.reports.service_reports import ServiceReports
from scripts.backup_db import backup_supabase

MONTREAL_TZ = pytz.timezone("America/Toronto")

class MasterScheduler:
    """Scheduler centralisé pour toutes les tâches automatisées."""

    def __init__(self):
        self.scheduler = BackgroundScheduler(timezone="America/Toronto")

    def start(self):
        """Démarre tous les jobs planifiés."""

        # 1. Sync Gazelle (toutes les 2h, 06h-22h)
        self.scheduler.add_job(
            self._sync_gazelle,
            trigger='cron',
            hour='6,8,10,12,14,16,18,20,22',
            id='sync_gazelle_2h'
        )

        # 2. Rapport Timeline (02:00)
        self.scheduler.add_job(
            self._generate_timeline_report,
            trigger='cron',
            hour=2,
            minute=0,
            id='timeline_report_daily'
        )

        # 3. Backup Supabase (03:00)
        self.scheduler.add_job(
            self._backup_database,
            trigger='cron',
            hour=3,
            minute=0,
            id='backup_supabase_daily'
        )

        # Démarrer le scheduler
        self.scheduler.start()
        print("✅ Master Scheduler démarré")

    def _sync_gazelle(self):
        """Job: Sync Gazelle → Supabase."""
        try:
            print(f"[{datetime.now()}] 🔄 Début sync Gazelle...")
            sync = GazelleToSupabaseSync()
            sync.run_sync()
            print(f"[{datetime.now()}] ✅ Sync Gazelle terminé")
        except Exception as e:
            print(f"[{datetime.now()}] ❌ Erreur sync Gazelle: {e}")

    def _generate_timeline_report(self):
        """Job: Génération rapport timeline."""
        try:
            print(f"[{datetime.now()}] 📊 Début rapport timeline...")
            service = ServiceReports()
            service.generate_reports(append=True)
            print(f"[{datetime.now()}] ✅ Rapport timeline terminé")
        except Exception as e:
            print(f"[{datetime.now()}] ❌ Erreur rapport timeline: {e}")

    def _backup_database(self):
        """Job: Backup Supabase."""
        try:
            print(f"[{datetime.now()}] 💾 Début backup Supabase...")
            backup_supabase()
            print(f"[{datetime.now()}] ✅ Backup terminé")
        except Exception as e:
            print(f"[{datetime.now()}] ❌ Erreur backup: {e}")
```

### Intégration dans `api/main.py`
```python
from api.scheduler import MasterScheduler

# Global scheduler
_master_scheduler = None

@app.on_event("startup")
async def startup_scheduler():
    """Démarre le scheduler centralisé."""
    global _master_scheduler
    _master_scheduler = MasterScheduler()
    _master_scheduler.start()

@app.on_event("shutdown")
async def shutdown_scheduler():
    """Arrête le scheduler."""
    if _master_scheduler:
        _master_scheduler.scheduler.shutdown()
```

---

## ⚙️ CONFIGURATION PAR ENVIRONNEMENT

### Local (développement)
- Sync Gazelle: **Manuel** (on-demand)
- Rapport Timeline: **Manuel**
- Alertes RV: **Désactivées**
- Backup: **Manuel**

### Staging (test)
- Sync Gazelle: **Toutes les 4h**
- Rapport Timeline: **02:00**
- Alertes RV: **Mode test (sans envoi)**
- Backup: **Manuel**

### Production (Render)
- Sync Gazelle: **Toutes les 2h (06h-22h)**
- Rapport Timeline: **02:00**
- Alertes RV: **16:00 + 09:00**
- Backup: **03:00**

### Variable d'Environnement
```bash
# .env
SCHEDULER_ENABLED=true  # false en local/dev
SCHEDULER_ENV=production  # local | staging | production
```

---

## 📊 MONITORING ET LOGS

### Table Supabase: `scheduler_logs`
```sql
CREATE TABLE IF NOT EXISTS scheduler_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_name TEXT NOT NULL,
    status TEXT NOT NULL,  -- 'success' | 'error'
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    duration_seconds INTEGER,
    error_message TEXT,
    details JSONB
);
```

### Endpoints de Monitoring
```bash
# Statut de tous les jobs
GET /api/scheduler/status

# Historique d'un job
GET /api/scheduler/logs/{job_name}?limit=50

# Forcer exécution manuelle
POST /api/scheduler/run/{job_name}
```

---

## 🚨 GESTION DES ERREURS

### Stratégie de Retry
- **Sync Gazelle**: 3 tentatives (délai: 5 min)
- **Rapport Timeline**: 2 tentatives (délai: 10 min)
- **Backup**: 1 tentative (alert admin si échec)

### Alertes Email
En cas d'échec critique:
- Envoyer email à `allan@example.com`
- Inclure logs d'erreur
- Suggestions de résolution

### Mécanisme de Fallback
Si sync Gazelle échoue 3 fois:
- Logger l'erreur dans Supabase
- Continuer avec les données existantes
- Réessayer au prochain cycle

---

## ✅ CHECKLIST D'IMPLÉMENTATION

### Phase 1: Scheduler Centralisé
- [ ] Créer `api/scheduler.py`
- [ ] Implémenter `MasterScheduler`
- [ ] Intégrer dans `api/main.py`
- [ ] Tester en local

### Phase 2: Sync Gazelle Automatique
- [ ] Refactoriser `sync_to_supabase.py` pour être appelable
- [ ] Ajouter job dans scheduler (2h)
- [ ] Tester sync partielle
- [ ] Vérifier performance

### Phase 3: Backup Automatique
- [ ] Créer script `backup_db.py` fonctionnel
- [ ] Choisir destination backup (S3/Drive)
- [ ] Ajouter job dans scheduler (03:00)
- [ ] Tester backup complet

### Phase 4: Monitoring
- [ ] Créer table `scheduler_logs`
- [ ] Implémenter logging dans chaque job
- [ ] Créer endpoints monitoring
- [ ] Dashboard Supabase pour visualiser logs

### Phase 5: Déploiement Production
- [ ] Tester en staging
- [ ] Configurer variables env production
- [ ] Déployer sur Render
- [ ] Monitorer 1 semaine

---

## 📞 DÉPANNAGE

### Scheduler ne démarre pas
1. Vérifier `SCHEDULER_ENABLED=true` dans `.env`
2. Vérifier logs startup FastAPI
3. Vérifier dépendances: `pip install apscheduler pytz`

### Sync Gazelle échoue
1. Vérifier token OAuth Gazelle valide
2. Tester manuellement: `python3 modules/sync_gazelle/sync_to_supabase.py`
3. Vérifier connexion Supabase

### Rapport Timeline vide
1. Vérifier données dans `gazelle_timeline_entries`
2. Vérifier credentials Google Sheets
3. Tester endpoint: `POST /api/reports/timeline/generate`

### Backup échoue
1. Vérifier espace disque
2. Vérifier permissions destination
3. Vérifier connexion Supabase

---

## 🎯 OBJECTIFS

### Court Terme (Cette Semaine)
- ✅ Rapport Timeline automatisé (FAIT)
- ✅ Alertes RV automatisées (FAIT)
- ⏳ Sync Gazelle automatique (À FAIRE)

### Moyen Terme (Ce Mois)
- ⏳ Backup automatique (À FAIRE)
- ⏳ Monitoring dashboard (À FAIRE)
- ⏳ Retry logic robuste (À FAIRE)

### Long Terme (Prochain Trimestre)
- ⏳ Alertes proactives (prédiction maintenance)
- ⏳ Sync bidirectionnelle (Supabase → Gazelle)
- ⏳ ML pour optimisation horaires sync

---

**Créé:** 2025-12-28
**Par:** Claude Code
**Pour:** Automatisation complète Assistant Gazelle V5
