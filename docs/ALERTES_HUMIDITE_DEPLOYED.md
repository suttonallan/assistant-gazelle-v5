# ✅ Système d'Alertes Humidité - DÉPLOYÉ

**Date de déploiement:** 2026-01-07
**Status:** ✅ Production - Testé et fonctionnel
**Migration:** PC Windows → Mac (Supabase) - Complète

---

## 🎯 Résumé

Le système d'alertes humidité détecte automatiquement les problèmes d'entretien (housse enlevée, PLS débranché) dans les notes de service des techniciens et envoie des notifications Slack à Louise et Nicolas **uniquement pour les problèmes non résolus**.

---

## ✅ Tests de Production

### Test Initial (100 entries - 2026-01-07)

```
📊 Résultats:
  - Scannées: 90 entries
  - Skipped: 10 entries (déjà dans historique)
  - Alertes trouvées: 2 (alimentation)
  - Notifications Slack: 2 envoyées ✅
  - Erreurs: 0
```

**Validation:**
- ✅ Pattern matching fonctionne
- ✅ Historique anti-doublons fonctionne (10 skipped)
- ✅ Détection problèmes réels (2 alertes)
- ✅ Notifications Slack envoyées
- ✅ Mention "(Mac)" dans les alertes

---

## 📊 Configuration Actuelle

### Fréquence de Scan
**4 fois par jour** via GitHub Actions:
- 8h AM - Montréal
- 12h PM - Montréal
- 4h PM - Montréal
- 8h PM - Montréal

### Mots-Clés Détectés

**Problèmes:**
- **Housse:** 10 mots-clés (housse enlevée, retirée, cover removed, etc.)
- **Alimentation:** 18 mots-clés (pls débranché, unplugged, déconnecté, etc.)

**Résolutions:**
- **Housse:** 11 mots-clés (replacée, remise, repositionnée, etc.)
- **Alimentation:** 12 mots-clés (rebranché, reconnecté, plugged back, etc.)

---

## 🔔 Notifications Slack

**Destinataires:**
- Louise: Webhook configuré ✅
- Nicolas: Webhook configuré ✅

**Format du message:**
```
🚨 *ALERTE HUMIDITÉ DÉTECTÉE* (Mac)

Type: ALIMENTATION
Description: débranché détecté
Client: cli_xxx
Piano: pia_xxx
Date: 2026-01-07T10:30:00Z
```

**Règle:**
- ✅ Envoyée si problème **NON résolu**
- ❌ PAS envoyée si problème résolu dans la même note

---

## 💾 Base de Données Supabase

### Tables Créées

1. **`humidity_alerts`** - Alertes détectées
   - Colonnes: id, timeline_entry_id, client_id, piano_id, alert_type, description, is_resolved, observed_at
   - UNIQUE constraint: (timeline_entry_id, alert_type)
   - Index: client_id, piano_id, alert_type, is_resolved, observed_at

2. **`humidity_alerts_history`** - Historique scan
   - Colonnes: timeline_entry_id (PK), scanned_at, found_issues
   - Évite de re-scanner les mêmes entries

3. **`humidity_alerts_active`** (Vue) - Alertes non résolues
   - JOIN avec gazelle_clients et gazelle_pianos
   - Utilisable pour dashboard

4. **`humidity_alerts_stats`** (Vue) - Statistiques
   - COUNT par type d'alerte
   - Résolues vs actives

---

## 📁 Fichiers Système

### Code Principal
- **[modules/alerts/humidity_scanner.py](../modules/alerts/humidity_scanner.py)** - Scanner (adapté du PC)
- **[modules/alerts/__init__.py](../modules/alerts/__init__.py)** - Export classe

### Configuration
- **[config/alerts/config.json](../config/alerts/config.json)** - Mots-clés
- **[config/TECHNICIAN_IDS.json](../config/TECHNICIAN_IDS.json)** - Webhooks Slack

### Automatisation
- **[.github/workflows/humidity_alerts_scanner.yml](../.github/workflows/humidity_alerts_scanner.yml)** - Scan automatique 4x/jour

### Tests
- **[scripts/test_humidity_scanner.py](../scripts/test_humidity_scanner.py)** - Tests pattern matching

### SQL
- **[sql/create_humidity_alerts_tables.sql](../sql/create_humidity_alerts_tables.sql)** - Schema Supabase

### Documentation
- **[docs/MIGRATION_HUMIDITY_ALERTS_V4_TO_V5.md](MIGRATION_HUMIDITY_ALERTS_V4_TO_V5.md)** - Guide migration
- **[docs/RAPPORT_MOTEUR_ALERTES.md](RAPPORT_MOTEUR_ALERTES.md)** - Analyse moteur
- **[docs/ALERTES_HUMIDITE_READY.md](ALERTES_HUMIDITE_READY.md)** - Guide pré-déploiement

---

## 🚀 Utilisation

### Scan Manuel
```bash
cd /Users/allansutton/Documents/assistant-gazelle-v5
python3 -c "from modules.alerts import HumidityScanner; HumidityScanner().scan_timeline_entries(100)"
```

### Scan Automatique
Le GitHub Action s'exécute automatiquement 4 fois par jour.

**Pour lancer manuellement:**
1. Aller sur GitHub → Actions
2. Sélectionner "🌡️ Scan Alertes Humidité"
3. Cliquer "Run workflow"

### Consulter les Alertes
```sql
-- Dans Supabase SQL Editor

-- Voir alertes actives (non résolues)
SELECT * FROM humidity_alerts_active
ORDER BY observed_at DESC;

-- Stats
SELECT * FROM humidity_alerts_stats;

-- Historique scan
SELECT
  DATE(scanned_at) as date,
  COUNT(*) as entries_scanned,
  SUM(CASE WHEN found_issues THEN 1 ELSE 0 END) as issues_found
FROM humidity_alerts_history
GROUP BY DATE(scanned_at)
ORDER BY date DESC;
```

---

## 🔧 Maintenance

### Ajouter un Mot-Clé

Éditer [config/alerts/config.json](../config/alerts/config.json):

```json
{
  "alert_keywords": {
    "housse": [
      "nouveau mot-clé ici"
    ]
  }
}
```

### Marquer Alerte comme Résolue

```sql
-- Via fonction Supabase
SELECT resolve_humidity_alert('UUID_DE_L_ALERTE');

-- Ou directement
UPDATE humidity_alerts
SET is_resolved = TRUE, updated_at = NOW()
WHERE id = 'UUID_DE_L_ALERTE';
```

### Vider l'Historique (Réinitialiser)

```sql
-- ⚠️ ATTENTION: Cela ré-scannera toutes les entries
TRUNCATE humidity_alerts_history;
```

---

## 📈 Métriques de Performance

### Charge par Scan
- **Entries scannées:** ~50-90 par scan (dépend de la fréquence)
- **Requêtes Supabase:** 3 par scan (historique + entries + save)
- **Durée:** ~5-10 secondes
- **Coût OpenAI:** $0 (pattern matching suffit généralement)

### Charge Totale (4 scans/jour)
- **Entries/jour:** ~200-300 entries
- **Requêtes Supabase/jour:** ~12 requêtes
- **Coût:** Gratuit (dans les limites Supabase free tier)

---

## 🔒 Sécurité

### Secrets GitHub
Configurés dans GitHub → Settings → Secrets:
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `OPENAI_API_KEY` (optionnel)

### Webhooks Slack
Stockés dans [config/TECHNICIAN_IDS.json](../config/TECHNICIAN_IDS.json):
- Louise: Configuré ✅
- Nicolas: Configuré ✅

---

## 🐛 Dépannage

### Problème: Aucune alerte détectée
**Solution:** Vérifier que les mots-clés correspondent aux notes réelles:
```python
from modules.alerts import HumidityScanner
scanner = HumidityScanner()
result = scanner.detect_issue(
    "VOTRE NOTE ICI",
    scanner.config['alert_keywords'],
    scanner.config['resolution_keywords']
)
print(result)
```

### Problème: Notifications Slack non reçues
**Solution:** Tester les webhooks:
```python
from core.slack_notifier import SlackNotifier
SlackNotifier.send_simple_message(
    "WEBHOOK_URL",
    "Test message"
)
```

### Problème: Erreur "duplicate key"
**Normal:** L'alerte existe déjà dans la base. L'erreur est ignorée automatiquement.

### Problème: GitHub Action échoue
**Solutions:**
1. Vérifier que les secrets sont configurés
2. Vérifier les logs dans GitHub Actions
3. Tester localement avec les mêmes commandes

---

## 📊 Logs et Monitoring

### Consulter les Logs GitHub Actions
1. GitHub → Actions
2. Sélectionner le workflow "🌡️ Scan Alertes Humidité"
3. Cliquer sur un run pour voir les logs

### Exemple de Log Réussi
```
📚 10 entries déjà scannées dans l'historique
📥 100 timeline entries récupérées
✅ Alerte enregistrée: alimentation - NON RÉSOLU
✅ Message Slack envoyé avec succès
✅ Scan terminé: {'scanned': 90, 'alerts_found': 2, 'notifications_sent': 2, 'errors': 0, 'skipped': 10}
```

---

## 🎯 Prochaines Améliorations (Optionnel)

- [ ] Dashboard web pour visualiser les alertes
- [ ] Email notifications en plus de Slack
- [ ] Détection "réservoir vide" (pas encore de données de test)
- [ ] Rapport hebdomadaire automatique
- [ ] Intégration avec calendrier pour prioriser alertes

---

## ✅ Checklist Post-Déploiement

- [x] Code adapté du PC vers Mac
- [x] Tables Supabase créées
- [x] Tests pattern matching réussis
- [x] Test scan réel réussi (100 entries)
- [x] Notifications Slack fonctionnelles
- [x] Historique anti-doublons fonctionnel
- [x] GitHub Action configurée (4x/jour)
- [x] Documentation complète
- [x] Secrets GitHub configurés

---

**🎉 SYSTÈME EN PRODUCTION - PRÊT À UTILISER !**

Le système scannera automatiquement les timeline entries 4 fois par jour et notifiera Louise et Nicolas de tout problème d'humidité non résolu détecté dans les notes de service.
