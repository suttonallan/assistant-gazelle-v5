# 🔄 Migration Système Alertes Humidité V4 → V5

**Date:** 2026-01-07
**Source:** PC Windows `c:\Allan Python projets\humidity_alerts\`
**Destination:** Mac `/Users/allansutton/Documents/assistant-gazelle-v5/`

---

## 📋 Checklist Migration

### ✅ Étape 1: Structure Créée (FAIT)

- [x] Dossier `modules/alerts/`
- [x] Dossier `config/alerts/`
- [x] Template `humidity_scanner.py`
- [x] Template `config.json`
- [x] SQL `create_humidity_alerts_tables.sql`

### ⏳ Étape 2: Copier Code du PC (À FAIRE)

#### Fichier 1: humidity_alert_system.py
```bash
# Sur PC Windows:
c:\Allan Python projets\humidity_alerts\humidity_alert_system.py
```

**Sections à copier:**

1. **Fonction `detect_issue()` (lignes 139-170)**
   - Pattern matching exact
   - Détection housse / alimentation / réservoir
   - Vérification résolution

   → Copier dans `modules/alerts/humidity_scanner.py:detect_issue()`

2. **Fonction `analyze_with_ai()` (lignes 172-236)**
   - Appel OpenAI GPT-4o-mini
   - Confidence score
   - Fallback si pattern matching échoue

   → Copier dans `modules/alerts/humidity_scanner.py:analyze_with_ai()`

#### Fichier 2: config.json
```bash
# Sur PC Windows:
c:\Allan Python projets\humidity_alerts\config.json
```

**Contenu complet à copier:**
- Tous les mots-clés `alert_keywords`
- Tous les mots-clés `resolution_keywords`

→ Remplacer `config/alerts/config.json`

#### Fichier 3: Documentation
```bash
# Sur PC Windows:
\\tsclient\assistant-gazelle-v5\docs\MOTEUR_ALERTES_HUMIDITE_V4_ANALYSE.md
```

→ Copier vers `docs/MOTEUR_ALERTES_HUMIDITE_V4_ANALYSE.md`

---

## 🔧 Étape 3: Configuration Supabase

### 3.1 Créer Tables

Exécuter dans Supabase SQL Editor:
```bash
cat sql/create_humidity_alerts_tables.sql
```

Tables créées:
- `humidity_alerts` - Alertes détectées
- `humidity_alerts_history` - Timeline entries scannées
- `humidity_alerts_active` (vue) - Alertes non résolues
- `humidity_alerts_stats` (vue) - Statistiques par type

### 3.2 Ajouter Variables d'Environnement

Dans `.env`:
```bash
# OpenAI pour fallback IA
OPENAI_API_KEY=sk-...

# Webhooks Slack (déjà configurés dans config.json)
SLACK_WEBHOOK_LOUISE=https://hooks.slack.com/services/YOUR/WEBHOOK/URL_HERE
SLACK_WEBHOOK_NICOLAS=https://hooks.slack.com/services/YOUR/WEBHOOK/URL_HERE
```

---

## 🤖 Étape 4: Automatisation (APScheduler)

### 4.1 Créer Scheduler

Fichier: `scripts/schedule_humidity_scanner.py`

```python
#!/usr/bin/env python3
"""
Scheduler pour scan automatique alertes humidité.

Fréquence: Tous les jours à 8h AM (heure Montréal)
"""

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from modules.alerts import HumidityScanner


def run_humidity_scan():
    """Exécute le scan d'alertes humidité."""
    print(f"\n{'='*70}")
    print(f"🔍 SCAN AUTOMATIQUE ALERTES HUMIDITÉ")
    print(f"{'='*70}\n")

    scanner = HumidityScanner()
    stats = scanner.scan_timeline_entries(limit=500)

    print(f"\n📊 Résultats:")
    print(f"  - Scannées: {stats['scanned']}")
    print(f"  - Alertes trouvées: {stats['alerts_found']}")
    print(f"  - Notifications envoyées: {stats['notifications_sent']}")
    print(f"  - Erreurs: {stats['errors']}")


if __name__ == "__main__":
    # Timezone Montréal
    montreal_tz = pytz.timezone('America/Montreal')

    # Créer scheduler
    scheduler = BlockingScheduler(timezone=montreal_tz)

    # Trigger: Tous les jours à 8h AM
    trigger = CronTrigger(
        hour=8,
        minute=0,
        timezone=montreal_tz
    )

    scheduler.add_job(
        run_humidity_scan,
        trigger=trigger,
        id='humidity_scan_daily',
        name='Scan quotidien alertes humidité',
        replace_existing=True
    )

    print(f"🤖 Scheduler démarré - Scan quotidien à 8h AM (Montréal)")
    print(f"Prochaine exécution: {scheduler.get_jobs()[0].next_run_time}")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\n👋 Scheduler arrêté")
```

### 4.2 Tester Manuellement

```bash
# Test avec 10 entries
python -c "from modules.alerts import HumidityScanner; HumidityScanner().scan_timeline_entries(10)"

# Lancer scheduler (Ctrl+C pour arrêter)
python scripts/schedule_humidity_scanner.py
```

---

## 📊 Étape 5: Vérification

### 5.1 Tester Pattern Matching

```python
from modules.alerts import HumidityScanner

scanner = HumidityScanner()

# Test housse
result = scanner.detect_issue(
    "Housse enlevée pendant la visite",
    scanner.config['alert_keywords'],
    scanner.config['resolution_keywords']
)
print(result)  # ('housse', 'Housse détectée: housse enlevée', False)

# Test résolu
result = scanner.detect_issue(
    "PLS débranché. Rebranché après inspection.",
    scanner.config['alert_keywords'],
    scanner.config['resolution_keywords']
)
print(result)  # ('alimentation', 'Alimentation détectée: pls débranché', True)
```

### 5.2 Vérifier Tables Supabase

```sql
-- Voir alertes actives
SELECT * FROM humidity_alerts_active;

-- Stats
SELECT * FROM humidity_alerts_stats;

-- Historique
SELECT COUNT(*) FROM humidity_alerts_history;
```

### 5.3 Tester Slack

```python
from modules.alerts import HumidityScanner

scanner = HumidityScanner()
scanner._send_slack_notification(
    'housse',
    'Test notification',
    {'client_external_id': 'cli_test', 'piano_id': 'pia_test', 'occurred_at': '2026-01-07'}
)
```

---

## 🎯 Différences V4 → V5

| Aspect | V4 (PC Windows) | V5 (Mac) |
|--------|----------------|----------|
| **Base de données** | SQL Server | Supabase (PostgreSQL) |
| **Storage** | Connexion directe SQL | REST API Supabase |
| **Rapport** | Google Sheets (maintenance_alerts_report.py) | Vues Supabase |
| **Scheduler** | Windows Task Scheduler | APScheduler Python |
| **Config** | Fichier local | JSON + variables .env |
| **Slack** | Webhooks hardcodés | SlackNotifier centralisé |

---

## 📝 Notes Importantes

### Mots-Clés Critiques

**Problèmes:**
- Housse: "housse enlevée", "sans housse", "cover removed"
- Alimentation: "PLS débranché", "unplugged", "déconnecté", "débranché"
- Réservoir: "réservoir vide", "reservoir empty", "tank empty"

**Résolutions:**
- Housse: "replacée", "replaced", "remise"
- Alimentation: "rebranché", "reconnected", "plugged"
- Réservoir: "rempli", "refilled"

### OpenAI Fallback

- Modèle: `gpt-4o-mini`
- Confidence minimum: 0.6 (60%)
- Coût: ~0.15$ USD / 1M tokens input
- Utilisé SEULEMENT si pattern matching échoue

### Slack Notifications

- Envoyées SEULEMENT pour alertes **non résolues**
- 2 destinataires: Louise + Nicolas
- Format: Type | Description | Client | Piano | Date

---

## ⏱️ Temps Estimé

- **Migration code:** 1-2 heures
- **Tests:** 1 heure
- **Automatisation:** 30 minutes
- **Documentation:** 30 minutes

**Total:** 3-4 heures

---

## ✅ Validation Finale

Avant de déployer:

- [ ] Code `detect_issue()` copié et testé
- [ ] Code `analyze_with_ai()` copié et testé
- [ ] Config complète avec tous les mots-clés
- [ ] Tables Supabase créées
- [ ] Test scan manuel réussi
- [ ] Test notification Slack réussie
- [ ] Scheduler configuré et testé
- [ ] Documentation à jour

---

**Prêt pour migration!** 🚀
