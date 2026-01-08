# 🛠️ Commandes Utiles - Système Alertes Humidité

Guide rapide des commandes pour gérer le système d'alertes humidité.

---

## 🚀 Scan Manuel

### Scan Rapide (10 entries)
```bash
cd /Users/allansutton/Documents/assistant-gazelle-v5
python3 -c "from modules.alerts import HumidityScanner; HumidityScanner().scan_timeline_entries(10)"
```

### Scan Standard (100 entries)
```bash
python3 -c "from modules.alerts import HumidityScanner; HumidityScanner().scan_timeline_entries(100)"
```

### Scan Complet (500 entries)
```bash
python3 -c "from modules.alerts import HumidityScanner; HumidityScanner().scan_timeline_entries(500)"
```

### Scan avec Stats Détaillées
```bash
python3 -c "
from modules.alerts import HumidityScanner

scanner = HumidityScanner()
stats = scanner.scan_timeline_entries(100)

print('\n📊 STATISTIQUES DÉTAILLÉES:')
print(f'  Scannées: {stats[\"scanned\"]}')
print(f'  Déjà scannées (skipped): {stats[\"skipped\"]}')
print(f'  Alertes trouvées: {stats[\"alerts_found\"]}')
print(f'  Notifications Slack: {stats[\"notifications_sent\"]}')
print(f'  Erreurs: {stats[\"errors\"]}')
"
```

---

## 🧪 Tests

### Test Pattern Matching
```bash
python3 scripts/test_humidity_scanner.py
```

### Test Manuel d'une Note
```bash
python3 -c "
from modules.alerts import HumidityScanner

scanner = HumidityScanner()

# Remplacer par votre note de test
note = 'Housse enlevée pendant la visite'

result = scanner.detect_issue(
    note,
    scanner.config['alert_keywords'],
    scanner.config['resolution_keywords']
)

if result:
    alert_type, description, is_resolved = result
    print(f'✅ Détecté: {alert_type}')
    print(f'   Description: {description}')
    print(f'   Résolu: {is_resolved}')
else:
    print('❌ Rien détecté')
"
```

### Test Webhook Slack
```bash
python3 -c "
from core.slack_notifier import SlackNotifier

# Test webhook Louise
SlackNotifier.send_simple_message(
    'https://hooks.slack.com/services/YOUR/WEBHOOK/URL_HERE',
    '🧪 Test notification système alertes humidité (Mac)'
)

print('✅ Notification test envoyée à Louise')
"
```

---

## 📊 Requêtes Supabase

### Voir Alertes Actives (Non Résolues)
```sql
SELECT
    alert_type,
    description,
    client_name,
    piano_make,
    piano_model,
    observed_at
FROM humidity_alerts_active
ORDER BY observed_at DESC
LIMIT 20;
```

### Compter Alertes par Type
```sql
SELECT * FROM humidity_alerts_stats;
```

### Historique des Scans (Derniers 7 jours)
```sql
SELECT
    DATE(scanned_at) as date,
    COUNT(*) as total_scanned,
    SUM(CASE WHEN found_issues THEN 1 ELSE 0 END) as alertes_trouvees
FROM humidity_alerts_history
WHERE scanned_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE(scanned_at)
ORDER BY date DESC;
```

### Alertes du Jour
```sql
SELECT
    alert_type,
    description,
    is_resolved,
    observed_at
FROM humidity_alerts
WHERE DATE(observed_at) = CURRENT_DATE
ORDER BY observed_at DESC;
```

### Marquer Alerte comme Résolue
```sql
-- Via fonction
SELECT resolve_humidity_alert('UUID_ICI');

-- Ou directement
UPDATE humidity_alerts
SET is_resolved = TRUE, updated_at = NOW()
WHERE id = 'UUID_ICI';
```

### Supprimer une Alerte
```sql
DELETE FROM humidity_alerts
WHERE id = 'UUID_ICI';
```

### Réinitialiser Historique (⚠️ Attention)
```sql
-- Cela forcera à re-scanner toutes les entries
TRUNCATE humidity_alerts_history;
```

---

## 🔧 Configuration

### Ajouter un Mot-Clé d'Alerte
```bash
# Éditer le fichier
nano config/alerts/config.json

# Ajouter dans "alert_keywords" > "housse" ou "alimentation"
# Exemple:
# "housse": [
#   "housse enlevée",
#   "NOUVEAU MOT-CLÉ ICI"
# ]
```

### Voir Configuration Actuelle
```bash
python3 -c "
from modules.alerts import HumidityScanner
import json

scanner = HumidityScanner()

print('📋 MOTS-CLÉS ALERTES:')
for alert_type, keywords in scanner.config['alert_keywords'].items():
    print(f'\n{alert_type.upper()}:')
    for kw in keywords:
        print(f'  - {kw}')

print('\n\n📋 MOTS-CLÉS RÉSOLUTIONS:')
for alert_type, keywords in scanner.config['resolution_keywords'].items():
    print(f'\n{alert_type.upper()}:')
    for kw in keywords:
        print(f'  - {kw}')
"
```

---

## 🤖 GitHub Actions

### Lancer Manuellement
```bash
# Via GitHub interface:
# 1. Aller sur github.com/your-repo
# 2. Onglet "Actions"
# 3. Workflow "🌡️ Scan Alertes Humidité"
# 4. Bouton "Run workflow"

# Ou via CLI GitHub:
gh workflow run humidity_alerts_scanner.yml
```

### Voir Derniers Runs
```bash
gh run list --workflow=humidity_alerts_scanner.yml --limit 10
```

### Voir Logs d'un Run
```bash
# Remplacer RUN_ID par l'ID du run
gh run view RUN_ID --log
```

---

## 📈 Monitoring

### Stats Rapides
```bash
python3 -c "
import requests
import os
from dotenv import load_dotenv

load_dotenv()

url = os.getenv('SUPABASE_URL') + '/rest/v1/humidity_alerts_stats'
headers = {
    'apikey': os.getenv('SUPABASE_KEY'),
    'Authorization': f'Bearer {os.getenv(\"SUPABASE_KEY\")}'
}

response = requests.get(url, headers=headers)
stats = response.json()

print('📊 STATISTIQUES GLOBALES:')
for stat in stats:
    print(f'\n{stat[\"alert_type\"].upper()}:')
    print(f'  Total: {stat[\"total\"]}')
    print(f'  Actives: {stat[\"active\"]}')
    print(f'  Résolues: {stat[\"resolved\"]}')
"
```

### Dernières Alertes
```bash
python3 -c "
import requests
import os
from dotenv import load_dotenv

load_dotenv()

url = os.getenv('SUPABASE_URL') + '/rest/v1/humidity_alerts_active'
headers = {
    'apikey': os.getenv('SUPABASE_KEY'),
    'Authorization': f'Bearer {os.getenv(\"SUPABASE_KEY\")}'
}

params = {'limit': 5, 'order': 'observed_at.desc'}
response = requests.get(url, headers=headers, params=params)
alerts = response.json()

print('🚨 DERNIÈRES ALERTES ACTIVES:')
for alert in alerts:
    print(f'\n{alert[\"alert_type\"].upper()}')
    print(f'  Client: {alert.get(\"client_name\", \"N/A\")}')
    print(f'  Description: {alert[\"description\"]}')
    print(f'  Date: {alert[\"observed_at\"]}')
"
```

---

## 🐛 Dépannage

### Vérifier Connexion Supabase
```bash
python3 -c "
from core.supabase_storage import SupabaseStorage
storage = SupabaseStorage()
print(f'✅ Connecté: {storage.api_url}')
"
```

### Test Complet du Système
```bash
python3 -c "
from modules.alerts import HumidityScanner

print('🧪 TEST COMPLET DU SYSTÈME')
print('=' * 70)

# 1. Test initialisation
print('\n1. Test initialisation...')
scanner = HumidityScanner()
print('   ✅ Scanner initialisé')

# 2. Test pattern matching
print('\n2. Test pattern matching...')
result = scanner.detect_issue(
    'Housse enlevée pendant la visite',
    scanner.config['alert_keywords'],
    scanner.config['resolution_keywords']
)
if result:
    print(f'   ✅ Détection OK: {result[0]}')
else:
    print('   ❌ ERREUR: Pattern matching ne fonctionne pas')

# 3. Test scan (1 entry)
print('\n3. Test scan (1 entry)...')
stats = scanner.scan_timeline_entries(limit=1)
print(f'   ✅ Scan OK: {stats}')

print('\n✅ TOUS LES TESTS RÉUSSIS!')
"
```

### Logs Détaillés
```bash
# Activer logs Python
python3 -c "
import logging
logging.basicConfig(level=logging.DEBUG)

from modules.alerts import HumidityScanner
scanner = HumidityScanner()
scanner.scan_timeline_entries(5)
"
```

---

## 📝 Notes

- **Fréquence recommandée:** 4 scans/jour (configuré dans GitHub Action)
- **Limite par scan:** 100-200 entries (suffisant pour 6h de services)
- **Coût:** Gratuit (dans limites Supabase free tier)
- **Performance:** ~5-10 secondes par scan

---

## 🆘 Support

- **GitHub Actions logs:** github.com/your-repo/actions
- **Supabase logs:** app.supabase.com/project/YOUR_PROJECT/logs
- **Documentation:** [ALERTES_HUMIDITE_DEPLOYED.md](ALERTES_HUMIDITE_DEPLOYED.md)
