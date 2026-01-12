# 📚 INDEX - Alertes d'Humidité

**Documentation complète du système d'alertes d'humidité intégré au tableau de bord**

---

## 🚀 Par où commencer?

### Activation rapide (tu veux juste que ça marche)
👉 [QUICKSTART_ALERTES_HUMIDITE.md](QUICKSTART_ALERTES_HUMIDITE.md)
- 3 étapes, 2 minutes
- Commandes prêtes à copier-coller

### Checklist complète (tu veux tout tester)
👉 [CHECKLIST_ACTIVATION.md](CHECKLIST_ACTIVATION.md)
- Checklist étape par étape avec cases à cocher
- Tests de validation inclus
- Section dépannage

---

## 📖 Documentation

### Vue d'ensemble
👉 [RESUME_INTEGRATION_ALERTES.md](RESUME_INTEGRATION_ALERTES.md)
- Comment ça fonctionne (avec schémas visuels)
- Scénarios d'utilisation
- Fichiers créés/modifiés
- Questions fréquentes

### Guide d'activation détaillé
👉 [GUIDE_ACTIVATION_ALERTES_HUMIDITE.md](GUIDE_ACTIVATION_ALERTES_HUMIDITE.md)
- Activation pas à pas
- Tests de validation SQL
- Dépannage complet
- Configuration du scanner

### Référence technique complète
👉 [INTEGRATION_ALERTES_HUMIDITE_COMPLETE.md](INTEGRATION_ALERTES_HUMIDITE_COMPLETE.md)
- Architecture du système
- API endpoints
- Configuration avancée
- Prochaines évolutions possibles

---

## 🔧 Fichiers techniques

### Backend

**API Routes**
- [api/humidity_alerts_routes.py](api/humidity_alerts_routes.py) - Routes API complètes (517 lignes)
  - `/api/humidity-alerts/stats` - Statistiques globales
  - `/api/humidity-alerts/unresolved` - Liste 1 (Non résolues)
  - `/api/humidity-alerts/resolved` - Liste 2 (Résolues)
  - `/api/humidity-alerts/archived` - Liste 3 (Archivées)
  - `/api/humidity-alerts/institutional` - Alertes institutionnelles
  - `POST /api/humidity-alerts/resolve/{id}` - Résoudre une alerte
  - `POST /api/humidity-alerts/archive/{id}` - Archiver une alerte

**Scanner**
- [modules/alerts/humidity_scanner_safe.py](modules/alerts/humidity_scanner_safe.py) - Scanner production-safe (316 lignes)
  - Détection intelligente (summary + comment)
  - Protection contre crashes
  - Filtre temporel avec `occurredAtGte`

**Configuration**
- [config/alerts/config.json](config/alerts/config.json) - Keywords de détection
  - `alert_keywords` - Mots-clés pour détecter les problèmes
  - `resolution_keywords` - Mots-clés pour détecter les résolutions

### Base de données

**Migration SQL**
- [sql/add_archived_to_humidity_alerts_fixed.sql](sql/add_archived_to_humidity_alerts_fixed.sql) - Migration complète
  - Ajoute colonnes: `archived`, `resolved_at`, `resolution_notes`
  - Crée vue: `humidity_alerts_active`
  - Crée fonctions: `resolve_humidity_alert()`, `archive_humidity_alert()`
  - Crée index optimisés

### Frontend

**Composants**
- [frontend/src/components/HumidityAlertsDashboard.jsx](frontend/src/components/HumidityAlertsDashboard.jsx) - Dashboard complet (377 lignes)
  - 3 compteurs (Total / Non résolues / Résolues)
  - Onglets pour switcher entre listes
  - Boutons Résoudre/Archiver
  - Auto-refresh 30s

- [frontend/src/components/DashboardHome.jsx](frontend/src/components/DashboardHome.jsx) - Intégration dans dashboard principal
  - Carte conditionnelle d'alertes
  - Dashboard expandable
  - Fonction `loadHumidityStats()`

### Scripts

**Tests**
- [scripts/test_humidity_integration.sh](scripts/test_humidity_integration.sh) - Test automatique complet
  - Teste tous les endpoints
  - Valide les données
  - Résumé coloré

---

## 🎯 Guide d'utilisation

### Pour les utilisateurs

**Tableau de bord principal**
1. Ouvre l'onglet "Tableau de bord"
2. Si des alertes existent → Carte orange visible
3. Clique "🔍 Voir les détails" pour le dashboard complet
4. Actions disponibles:
   - ✅ Résoudre une alerte
   - 📦 Archiver une alerte

**Page Configuration**
1. Ouvre l'onglet "Configuration"
2. Section "Alertes Maintenance Institutionnelle"
3. Voir les stats complètes
4. Liste des institutions surveillées

### Pour les développeurs

**Lancer un scan manuel**
```bash
python -c "from modules.alerts.humidity_scanner_safe import HumidityScannerSafe; scanner = HumidityScannerSafe(); print(scanner.scan_new_entries(days_back=7))"
```

**Tester les endpoints**
```bash
./scripts/test_humidity_integration.sh
```

**Ajouter une institution**
1. Édite `api/humidity_alerts_routes.py` ligne 58
2. Ajoute le nom à la liste `INSTITUTIONAL_CLIENTS`

**Modifier les mots-clés**
1. Édite `config/alerts/config.json`
2. Ajoute tes keywords dans `alert_keywords` ou `resolution_keywords`

**Changer l'horaire du scan**
1. Édite `api/humidity_alerts_routes.py` ligne 488
2. Modifie `hour=16` pour l'heure désirée (format 24h)

---

## 🗂️ Structure des fichiers

```
assistant-gazelle-v5/
│
├── 📚 Documentation (TU ES ICI)
│   ├── ALERTES_HUMIDITE_INDEX.md ← INDEX PRINCIPAL
│   ├── QUICKSTART_ALERTES_HUMIDITE.md ← Démarrage rapide
│   ├── CHECKLIST_ACTIVATION.md ← Checklist complète
│   ├── RESUME_INTEGRATION_ALERTES.md ← Vue d'ensemble
│   ├── GUIDE_ACTIVATION_ALERTES_HUMIDITE.md ← Guide détaillé
│   └── INTEGRATION_ALERTES_HUMIDITE_COMPLETE.md ← Référence technique
│
├── 🔧 Backend
│   ├── api/
│   │   └── humidity_alerts_routes.py ← Routes API
│   ├── modules/
│   │   └── alerts/
│   │       └── humidity_scanner_safe.py ← Scanner
│   └── config/
│       └── alerts/
│           └── config.json ← Configuration keywords
│
├── 🗄️ Base de données
│   └── sql/
│       └── add_archived_to_humidity_alerts_fixed.sql ← Migration
│
├── 🎨 Frontend
│   └── frontend/src/components/
│       ├── HumidityAlertsDashboard.jsx ← Dashboard complet
│       └── DashboardHome.jsx ← Intégration tableau de bord
│
└── 🧪 Scripts
    └── scripts/
        └── test_humidity_integration.sh ← Tests automatiques
```

---

## 🎬 Parcours recommandés

### Scénario 1: "Je veux activer le système maintenant"
1. [QUICKSTART_ALERTES_HUMIDITE.md](QUICKSTART_ALERTES_HUMIDITE.md) ← Commence ici
2. [scripts/test_humidity_integration.sh](scripts/test_humidity_integration.sh) ← Teste que ça marche
3. **C'est tout!** ✅

### Scénario 2: "Je veux tout comprendre avant"
1. [RESUME_INTEGRATION_ALERTES.md](RESUME_INTEGRATION_ALERTES.md) ← Vue d'ensemble
2. [GUIDE_ACTIVATION_ALERTES_HUMIDITE.md](GUIDE_ACTIVATION_ALERTES_HUMIDITE.md) ← Guide complet
3. [CHECKLIST_ACTIVATION.md](CHECKLIST_ACTIVATION.md) ← Active avec checklist
4. [INTEGRATION_ALERTES_HUMIDITE_COMPLETE.md](INTEGRATION_ALERTES_HUMIDITE_COMPLETE.md) ← Référence technique

### Scénario 3: "Je veux personnaliser le système"
1. [INTEGRATION_ALERTES_HUMIDITE_COMPLETE.md](INTEGRATION_ALERTES_HUMIDITE_COMPLETE.md) ← Architecture
2. [config/alerts/config.json](config/alerts/config.json) ← Modifie les keywords
3. [api/humidity_alerts_routes.py](api/humidity_alerts_routes.py) ← Modifie les institutions/horaire

### Scénario 4: "Ça ne marche pas, je debug"
1. [CHECKLIST_ACTIVATION.md](CHECKLIST_ACTIVATION.md) Section "En cas de problème"
2. [GUIDE_ACTIVATION_ALERTES_HUMIDITE.md](GUIDE_ACTIVATION_ALERTES_HUMIDITE.md) Section "Dépannage"
3. [scripts/test_humidity_integration.sh](scripts/test_humidity_integration.sh) ← Tests diagnostiques

---

## 📊 État du système

### Composants

| Composant | Statut | Fichier |
|-----------|--------|---------|
| API Routes | ✅ Fonctionnel | [api/humidity_alerts_routes.py](api/humidity_alerts_routes.py) |
| Scanner | ✅ Fonctionnel | [modules/alerts/humidity_scanner_safe.py](modules/alerts/humidity_scanner_safe.py) |
| SQL Migration | ⚠️ À exécuter | [sql/add_archived_to_humidity_alerts_fixed.sql](sql/add_archived_to_humidity_alerts_fixed.sql) |
| Frontend Dashboard | ✅ Fonctionnel | [frontend/src/components/HumidityAlertsDashboard.jsx](frontend/src/components/HumidityAlertsDashboard.jsx) |
| Frontend Intégration | ✅ Fonctionnel | [frontend/src/components/DashboardHome.jsx](frontend/src/components/DashboardHome.jsx) |
| Tests | ✅ Prêt | [scripts/test_humidity_integration.sh](scripts/test_humidity_integration.sh) |
| Documentation | ✅ Complète | 6 fichiers markdown |

### Prochaine action

👉 **Exécuter le SQL sur Supabase** (30 secondes)

Voir [QUICKSTART_ALERTES_HUMIDITE.md](QUICKSTART_ALERTES_HUMIDITE.md) Étape 1

---

## 🆘 Support

### Erreur pendant l'activation?
→ [CHECKLIST_ACTIVATION.md](CHECKLIST_ACTIVATION.md) Section "En cas de problème"

### Question sur l'architecture?
→ [INTEGRATION_ALERTES_HUMIDITE_COMPLETE.md](INTEGRATION_ALERTES_HUMIDITE_COMPLETE.md)

### Besoin d'aide rapide?
→ [QUICKSTART_ALERTES_HUMIDITE.md](QUICKSTART_ALERTES_HUMIDITE.md) Section "Problèmes courants"

---

## 📅 Historique

- **2026-01-11** - Intégration complète dans le tableau de bord
  - Carte conditionnelle non-intrusive
  - Dashboard expandable
  - Documentation complète créée

---

**Dernière mise à jour:** 2026-01-11
**Auteurs:** Assistant Claude Code + Allan Sutton
**Version du système:** 1.0.0
