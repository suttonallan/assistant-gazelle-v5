# Intégration complète - Alertes d'Humidité dans Tableau de Bord

## 📋 Résumé de l'intégration

Le système d'alertes d'humidité est maintenant **intégré proprement** dans le tableau de bord principal sans "prendre toute la place".

## 🎯 Architecture finale

```
Assistant Gazelle V5
│
├── 📊 Tableau de Bord (DashboardHome.jsx)
│   ├── 🏛️ Carte Alertes Maintenance Institutionnelle
│   │   ├── Stats résumé (Total / Non résolues / Résolues)
│   │   └── Bouton "Voir les détails" (expandable)
│   │       └── → HumidityAlertsDashboard (complet)
│   ├── 📈 Stats historique
│   └── 📋 Liste activités récentes
│
├── ⚙️ Configuration (Page dédiée)
│   └── HumidityAlertsDashboard autonome
│
└── 🔌 Backend API
    ├── /api/humidity-alerts/stats
    ├── /api/humidity-alerts/unresolved
    ├── /api/humidity-alerts/resolved
    ├── /api/humidity-alerts/archived
    ├── /api/humidity-alerts/resolve/{id}
    └── /api/humidity-alerts/archive/{id}
```

## ✅ Ce qui a été fait

### 1. Backend (API)
- ✅ Routes complètes avec 3 listes (Non résolues / Résolues / Archivées)
- ✅ Actions: Résoudre et Archiver
- ✅ Stats globales et par institution
- ✅ Scheduler automatique quotidien (16h)
- ✅ Scanner production-safe avec détection intelligente

**Fichiers:**
- [api/humidity_alerts_routes.py](api/humidity_alerts_routes.py) - 517 lignes
- [modules/alerts/humidity_scanner_safe.py](modules/alerts/humidity_scanner_safe.py) - 316 lignes

### 2. Base de données
- ✅ Vue `humidity_alerts_active` (exclut les archivées)
- ✅ Fonctions PL/pgSQL `resolve_humidity_alert()` et `archive_humidity_alert()`
- ✅ Colonnes: `archived`, `resolved_at`, `resolution_notes`
- ✅ Index optimisés

**Fichiers:**
- [sql/add_archived_to_humidity_alerts_fixed.sql](sql/add_archived_to_humidity_alerts_fixed.sql)

### 3. Frontend

#### A. Composant autonome
- ✅ [frontend/src/components/HumidityAlertsDashboard.jsx](frontend/src/components/HumidityAlertsDashboard.jsx)
  - 3 compteurs (Total / Non résolues / Résolues)
  - Onglets pour switcher entre listes
  - Boutons Résoudre/Archiver
  - Auto-refresh 30s

#### B. Intégration dans DashboardHome
- ✅ Carte résumé "Alertes Maintenance Institutionnelle"
  - Apparaît **uniquement si des alertes non résolues existent**
  - Design orange/rouge pour attirer l'attention
  - Stats résumé en un coup d'œil
  - Bouton expandable pour voir les détails complets

**Fichiers modifiés:**
- [frontend/src/components/DashboardHome.jsx](frontend/src/components/DashboardHome.jsx)

## 🚀 Activation (3 étapes)

### Étape 1: Exécuter le SQL sur Supabase

**Option A: Via l'interface Supabase** (Recommandé)
1. Ouvre https://supabase.com/dashboard
2. Va dans **SQL Editor**
3. Copie-colle [sql/add_archived_to_humidity_alerts_fixed.sql](sql/add_archived_to_humidity_alerts_fixed.sql)
4. Clique sur **Run**

**Option B: Vérification rapide**
```bash
# Dans Supabase SQL Editor
SELECT * FROM humidity_alerts_active LIMIT 1;
```
Si ça marche → ✅ Le SQL est déjà appliqué!

### Étape 2: Tester l'API

```bash
# Lancer l'API (si pas déjà lancée)
cd /Users/allansutton/Documents/assistant-gazelle-v5
python api/main.py

# Dans un autre terminal, tester
./scripts/test_humidity_integration.sh
```

### Étape 3: Tester le frontend

```bash
cd frontend
npm run dev
```

Ouvre http://localhost:5173 et va sur l'onglet **"Tableau de bord"**.

**Comportement attendu:**

- **Si aucune alerte** → La carte n'apparaît pas (tout est propre ✨)
- **Si des alertes existent** → Carte orange visible avec stats + bouton "Voir les détails"

## 🧪 Tests

### Test automatique
```bash
./scripts/test_humidity_integration.sh
```

### Tests manuels

**1. Tester les stats**
```bash
curl http://localhost:8000/api/humidity-alerts/stats | jq
```

Devrait retourner:
```json
{
  "total_alerts": 0,
  "unresolved": 0,
  "resolved": 0,
  "by_type": {},
  "institutional_unresolved": 0
}
```

**2. Tester le scanner**
```bash
python -c "from modules.alerts.humidity_scanner_safe import HumidityScannerSafe; scanner = HumidityScannerSafe(); print(scanner.scan_new_entries(days_back=7))"
```

## 📝 Configuration

### Institutions surveillées

Défini dans [api/humidity_alerts_routes.py](api/humidity_alerts_routes.py:58-62):

```python
INSTITUTIONAL_CLIENTS = [
    'Vincent d\'Indy',
    'Place des Arts',
    'Orford'
]
```

### Keywords de détection

Défini dans [config/alerts/config.json](config/alerts/config.json):

```json
{
  "alert_keywords": {
    "housse": ["housse enlevée", "sans housse"],
    "alimentation": ["débranché", "unplugged"],
    "reservoir": ["réservoir vide", "tank empty"],
    "environnement": ["fenêtre ouverte", "température basse"]
  },
  "resolution_keywords": {
    "housse": ["replacée", "replaced"],
    "alimentation": ["rebranché", "reconnected"],
    "reservoir": ["rempli", "filled"],
    "environnement": ["fermée", "normale"]
  }
}
```

### Scheduler automatique

Le scanner tourne **automatiquement tous les jours à 16h** (heure de Montréal).

Pour modifier l'horaire, édite [api/humidity_alerts_routes.py](api/humidity_alerts_routes.py:488):

```python
_scheduler.add_job(
    _run_daily_scan,
    trigger="cron",
    hour=16,  # ← Modifier ici
    minute=0,
    id=JOB_ID,
)
```

## 🎨 Design de la carte

### Quand elle apparaît
- **Uniquement si `institutional_unresolved > 0`**
- Sinon, le tableau de bord reste épuré

### Couleurs
- Fond: Gradient orange-rouge (`from-orange-50 to-red-50`)
- Bordure gauche: Orange foncé (`border-orange-500`)
- Bouton: Orange (`bg-orange-600`)

### Contenu
1. Icône 🏛️ + Titre "Alertes Maintenance Institutionnelle"
2. Message: "X alerte(s) d'humidité non résolue(s)"
3. 3 mini-cartes: Total / Non résolues / Résolues
4. Bouton expandable: "🔍 Voir les détails"

Quand on clique sur "Voir les détails" → Le composant `HumidityAlertsDashboard` complet s'affiche en dessous.

## 📚 Documentation

- [GUIDE_ACTIVATION_ALERTES_HUMIDITE.md](GUIDE_ACTIVATION_ALERTES_HUMIDITE.md) - Guide d'activation détaillé
- [config/alerts/config.json](config/alerts/config.json) - Configuration des keywords

## 🔧 Dépannage

### Erreur 500 sur /api/humidity-alerts/stats
→ Le SQL n'a pas été exécuté sur Supabase. Voir Étape 1.

### La carte n'apparaît jamais
→ Normal si aucune alerte non résolue. Vérifie les stats:
```bash
curl http://localhost:8000/api/humidity-alerts/stats
```

### "Module HumidityAlertsDashboard not found"
→ Le fichier existe mais l'import est peut-être incorrect. Vérifie:
```bash
ls frontend/src/components/HumidityAlertsDashboard.jsx
```

## ✨ Avantages de cette approche

1. **Non-intrusive** - La carte n'apparaît que si nécessaire
2. **Modulaire** - Le composant `HumidityAlertsDashboard` est réutilisable
3. **Performant** - Auto-refresh toutes les 30s sans bloquer l'UI
4. **Production-safe** - Le scanner ne crashe jamais
5. **Scalable** - Facile d'ajouter d'autres types d'alertes

## 🎯 Prochaines étapes possibles

- [ ] Ajouter notifications email pour alertes critiques
- [ ] Créer un rapport PDF mensuel des alertes
- [ ] Intégrer dans l'assistant conversationnel ("Y a-t-il des problèmes d'humidité?")
- [ ] Ajouter un graphique d'évolution des alertes
- [ ] Permettre l'ajout de photos aux résolutions

---

**Intégration complétée le:** 2026-01-11
**Auteur:** Assistant Claude Code avec Allan
