# 📊 Rapport: Moteur d'Analyse des Notes de Service

**Date:** 2026-01-07
**Auteur:** Claude Code
**Contexte:** Migration PC → Mac, recherche logique détection mots-clés humidité

---

## 🔍 Recherche Effectuée

### Fichiers Analysés

1. **[api/chat/service.py](../api/chat/service.py)** - Moteur principal d'extraction
   - Classe `V5DataProvider`
   - Fonctions d'extraction par regex

2. **[core/slack_notifier.py](../core/slack_notifier.py)** - Infrastructure notifications
   - Webhooks par technicien
   - Méthodes `notify_admin()`, `notify_technician()`

3. **[modules/assistant/services/parser.py](../modules/assistant/services/parser.py)** - Parser conversationnel
   - QueryType TIMELINE
   - Extraction entités

---

## 🎯 Moteur Actuel (V5 Mac)

### Localisation
**Fichier:** [api/chat/service.py](../api/chat/service.py:1104-1140)

### Méthode: REGEX

#### Action Items (`_extract_action_items`)
```python
# Pattern 1: "À apporter: X, Y, Z"
r'à apporter[:\s]+([^\n]+)'

# Pattern 2: "TODO: X"
r'todo[:\s]+([^\n]+)'

# Pattern 3: Dernière ligne (objets à apporter)
# Si ligne < 30 chars et pas de point final → action item
```

#### Détections Piano
```python
has_dampp_chaser = piano.get("dampp_chaser_installed", False)
```

#### Alertes Timeline
- 🌡️ Température: <18°C ou >26°C
- 💧 Humidité: <30% ou >60%
- 💰 Paiement: Keywords `['lent à payer', 'retard', 'relance']`
- ⚠️ Problèmes: Keywords `['problème', 'casse', 'défaut']`

---

## ❌ Mots-Clés MANQUANTS

Les mots-clés suivants **NE SONT PAS** détectés actuellement:

- ❌ "housse retirée" / "cover removed"
- ❌ "PL débranché" / "player débranché"
- ❌ "réservoir vide" / "reservoir vide"

---

## 📋 EN ATTENTE

### Fichier du PC à analyser:
- `\\tsclient\assistant-gazelle-v5\docs\MOTEUR_ALERTES_HUMIDITE_V4_ANALYSE.md`

**Contenu attendu:**
- Analyse complète du moteur V4
- Mots-clés exacts du config.json
- Logique détection humidité
- Patterns regex utilisés

### Config JSON à récupérer
- Localisation: Mentionné dans analyse V4
- Contenu: Liste complète mots-clés alertes

---

## 🔨 Prochaines Étapes

### 1. Copier fichier analyse V4
```bash
cp /Volumes/tsclient/assistant-gazelle-v5/docs/MOTEUR_ALERTES_HUMIDITE_V4_ANALYSE.md \
   /Users/allansutton/Documents/assistant-gazelle-v5/docs/
```

### 2. Lire et extraire patterns
- Lire analyse complète
- Extraire config.json
- Identifier tous les mots-clés

### 3. Implémenter détection
Créer nouvelle fonction dans [api/chat/service.py](../api/chat/service.py):

```python
def _extract_humidity_alerts(self, notes: str) -> List[Dict[str, str]]:
    """
    Détecte alertes humidité dans les notes.

    Returns:
        Liste de dicts: [{"type": "housse", "message": "..."}, ...]
    """
    alerts = []
    notes_lower = notes.lower()

    # Pattern housse retirée
    if any(kw in notes_lower for kw in ['housse retirée', 'cover removed', 'housse enlevée']):
        alerts.append({
            "type": "housse",
            "severity": "warning",
            "message": "⚠️ Housse retirée - Vérifier humidité"
        })

    # Pattern player débranché
    if any(kw in notes_lower for kw in ['pl débranché', 'player débranché', 'pls débranché']):
        alerts.append({
            "type": "player",
            "severity": "critical",
            "message": "🔌 Player débranché - Rebrancher système"
        })

    # Pattern réservoir vide
    if any(kw in notes_lower for kw in ['réservoir vide', 'reservoir vide', 'tank empty']):
        alerts.append({
            "type": "reservoir",
            "severity": "critical",
            "message": "💧 Réservoir vide - Remplir immédiatement"
        })

    return alerts
```

### 4. Intégrer notifications Slack
Utiliser [core/slack_notifier.py](../core/slack_notifier.py) pour notifier technicien

```python
from core.slack_notifier import SlackNotifier

# Dans _map_to_overview ou _map_to_comfort_info
humidity_alerts = self._extract_humidity_alerts(notes)

for alert in humidity_alerts:
    if alert['severity'] == 'critical':
        SlackNotifier.notify_admin(
            f"🚨 ALERTE CRITIQUE\n"
            f"Client: {client_name}\n"
            f"{alert['message']}"
        )
```

---

## 📊 Infrastructure Disponible

### ✅ Slack Notifier
- [core/slack_notifier.py](../core/slack_notifier.py:1-152)
- Webhooks configurés via .env:
  - `SLACK_WEBHOOK_ALLAN`
  - `SLACK_WEBHOOK_NICOLAS`
  - `SLACK_WEBHOOK_JEANPHILIPPE`
  - `SLACK_WEBHOOK_ADMIN_1` (Louise)
  - `SLACK_WEBHOOK_ADMIN_2` (Nicolas)

### ✅ Extraction Notes
- [api/chat/service.py](../api/chat/service.py:1104-1448)
- Fonctions regex prêtes
- Architecture modulaire

---

## 🎯 Objectif Final

Détecter automatiquement les alertes d'humidité dans les notes de service et:
1. ✅ Afficher dans l'interface (action items)
2. ✅ Notifier technicien via Slack
3. ✅ Logger dans timeline summary
4. ✅ Créer alertes visuelles (badges rouges)

---

**Status:** ⏳ EN ATTENTE du fichier MOTEUR_ALERTES_HUMIDITE_V4_ANALYSE.md
