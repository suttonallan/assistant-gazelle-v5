# 🏛️ Système d'Alertes d'Humidité - Assistant Gazelle V5

> **Intégration propre et non-intrusive dans le tableau de bord**

## ⚡ Activation en 3 étapes (2 minutes)

### 1️⃣ SQL (30 sec)
Ouvre [Supabase SQL Editor](https://supabase.com/dashboard) → Copie-colle `sql/add_archived_to_humidity_alerts_fixed.sql` → Run

### 2️⃣ Test (30 sec)
```bash
./scripts/test_humidity_integration.sh
```

### 3️⃣ Frontend (1 min)
```bash
cd frontend && npm run dev
```
Ouvre http://localhost:5173 → Onglet "Tableau de bord"

**✅ Terminé!** Si aucune alerte, la carte n'apparaît pas (normal).

---

## 🎯 Ce que ça fait

### Carte intelligente dans le tableau de bord
- **Apparaît uniquement** si des alertes non résolues existent
- Design orange/rouge pour attirer l'attention
- Stats en un coup d'œil (Total / Non résolues / Résolues)
- Bouton "Voir les détails" pour dashboard complet

### Scanner automatique
- Tourne **tous les jours à 16h**
- Détecte 4 types d'alertes:
  - 🛡️ Housse (enlevée/replacée)
  - ⚡ Alimentation (débranché/rebranché)
  - 💧 Réservoir (vide/rempli)
  - 🌡️ Environnement (fenêtre ouverte/température basse)

### 3 listes d'alertes
1. **Non résolues** - Alertes actives (action requise)
2. **Résolues** - Alertes traitées (visibles pour historique)
3. **Archivées** - Alertes masquées de l'interface

### Institutions surveillées
- Vincent d'Indy
- Place des Arts
- Orford

---

## 📚 Documentation

**Tu es pressé?**
👉 [QUICKSTART_ALERTES_HUMIDITE.md](QUICKSTART_ALERTES_HUMIDITE.md) - Démarrage rapide (2 min)

**Tu veux tout comprendre?**
👉 [ALERTES_HUMIDITE_INDEX.md](ALERTES_HUMIDITE_INDEX.md) - INDEX COMPLET

**Tu veux une checklist?**
👉 [CHECKLIST_ACTIVATION.md](CHECKLIST_ACTIVATION.md) - Checklist étape par étape

**Autres guides:**
- [RESUME_INTEGRATION_ALERTES.md](RESUME_INTEGRATION_ALERTES.md) - Vue d'ensemble visuelle
- [GUIDE_ACTIVATION_ALERTES_HUMIDITE.md](GUIDE_ACTIVATION_ALERTES_HUMIDITE.md) - Guide détaillé
- [INTEGRATION_ALERTES_HUMIDITE_COMPLETE.md](INTEGRATION_ALERTES_HUMIDITE_COMPLETE.md) - Référence technique

---

## 🎨 Design

### Avant (ce matin)
```
❌ Dashboard dédié qui "prenait toute la place"
❌ Context switch nécessaire
❌ Pas intégré au flux normal
```

### Maintenant
```
✅ Carte contextuelle (apparaît si nécessaire)
✅ Intégré dans le tableau de bord principal
✅ Expandable (détails on-demand)
✅ Non-intrusif (si aucune alerte → rien)
```

---

## 🔧 Architecture

```
Tableau de Bord (DashboardHome.jsx)
│
├── 🏛️ Carte Alertes (conditionnelle)
│   ├── Stats résumé
│   └── Bouton "Voir les détails"
│       └── → HumidityAlertsDashboard (complet)
│
├── 📈 Stats historique
└── 📋 Liste activités
```

**Backend:**
- Routes API: `api/humidity_alerts_routes.py` (517 lignes)
- Scanner: `modules/alerts/humidity_scanner_safe.py` (316 lignes)
- Config: `config/alerts/config.json`

**Frontend:**
- Dashboard: `frontend/src/components/HumidityAlertsDashboard.jsx` (377 lignes)
- Intégration: `frontend/src/components/DashboardHome.jsx` (modifié)

**Base de données:**
- Migration: `sql/add_archived_to_humidity_alerts_fixed.sql`

---

## 🚀 Commandes utiles

### Scanner manuel (7 derniers jours)
```bash
python -c "from modules.alerts.humidity_scanner_safe import HumidityScannerSafe; scanner = HumidityScannerSafe(); print(scanner.scan_new_entries(days_back=7))"
```

### Vérifier les stats
```bash
curl http://localhost:8000/api/humidity-alerts/stats | jq
```

### Tests complets
```bash
./scripts/test_humidity_integration.sh
```

---

## ⚙️ Configuration

### Ajouter une institution
Édite `api/humidity_alerts_routes.py` ligne 58:
```python
INSTITUTIONAL_CLIENTS = [
    'Vincent d\'Indy',
    'Place des Arts',
    'Orford',
    'Nouvelle Institution'  # ← Ajoute ici
]
```

### Changer l'horaire du scan
Édite `api/humidity_alerts_routes.py` ligne 488:
```python
hour=16,  # ← Change ici (format 24h)
```

### Personnaliser les mots-clés
Édite `config/alerts/config.json`:
```json
{
  "alert_keywords": {
    "housse": ["housse enlevée", "sans housse"],
    "mon_type": ["keyword1", "keyword2"]
  }
}
```

---

## 🆘 Problèmes?

### Erreur 500 sur l'API
→ Le SQL n'a pas été exécuté. Voir Étape 1.

### La carte n'apparaît jamais
→ Normal si `institutional_unresolved = 0`. Vérifie:
```bash
curl http://localhost:8000/api/humidity-alerts/stats
```

### Tests échouent
→ Checklist:
1. ✅ API tourne? (`python api/main.py`)
2. ✅ SQL exécuté sur Supabase?
3. ✅ Variables `.env` définies?

**Plus d'aide:** [CHECKLIST_ACTIVATION.md](CHECKLIST_ACTIVATION.md) Section "En cas de problème"

---

## ✨ Fonctionnalités

### Pour les utilisateurs
- ✅ Carte d'alerte visible uniquement si nécessaire
- ✅ Dashboard complet expandable
- ✅ Actions: Résoudre, Archiver
- ✅ Auto-refresh toutes les 30s
- ✅ Historique complet (3 listes)

### Pour les développeurs
- ✅ API REST complète (7 endpoints)
- ✅ Scanner production-safe (ne crashe jamais)
- ✅ Scheduler automatique quotidien
- ✅ Tests automatiques
- ✅ Documentation complète

---

## 📊 État actuel

| Composant | Statut |
|-----------|--------|
| Backend API | ✅ Fonctionnel |
| Scanner | ✅ Fonctionnel |
| Frontend | ✅ Fonctionnel |
| SQL Migration | ⚠️ À exécuter (une fois) |
| Tests | ✅ Prêt |
| Documentation | ✅ Complète |

**Prochaine action:** Exécuter le SQL sur Supabase (30 sec)

---

## 🎬 Exemple d'utilisation

**Lundi matin, Allan ouvre le tableau de bord:**

1. Voit immédiatement: "🏛️ 3 alertes d'humidité non résolues"
2. Clique "🔍 Voir les détails"
3. Liste affichée:
   - Vincent d'Indy: Housse enlevée (Steinway B)
   - Place des Arts: Débranché (Yamaha C7)
   - Orford: Réservoir vide (Baldwin)
4. Clique "✅ Résoudre" sur la première
5. Ajoute note: "Housse replacée, technicien averti"
6. Carte affiche maintenant: "2 alertes non résolues"

**Mercredi:** Toutes les alertes résolues → Carte disparaît → Dashboard épuré ✨

---

## 🏆 Avantages

1. **Non-intrusif** - Carte n'apparaît que si nécessaire
2. **Intégré** - Dans le flux normal du tableau de bord
3. **Performant** - Auto-refresh sans bloquer l'UI
4. **Robuste** - Scanner production-safe, ne crashe jamais
5. **Scalable** - Facile d'ajouter d'autres types d'alertes
6. **Bien documenté** - 6 guides complets

---

## 📅 Prochaines évolutions possibles

- [ ] Notifications email pour alertes critiques
- [ ] Rapport PDF mensuel des alertes
- [ ] Intégration dans l'assistant conversationnel
- [ ] Graphique d'évolution des alertes
- [ ] Photos attachées aux résolutions

---

## 📞 Support

**Index complet:** [ALERTES_HUMIDITE_INDEX.md](ALERTES_HUMIDITE_INDEX.md)

**Quickstart:** [QUICKSTART_ALERTES_HUMIDITE.md](QUICKSTART_ALERTES_HUMIDITE.md)

**Dépannage:** [CHECKLIST_ACTIVATION.md](CHECKLIST_ACTIVATION.md)

---

**Version:** 1.0.0
**Date:** 2026-01-11
**Auteurs:** Assistant Claude Code + Allan Sutton
**License:** Propriétaire (Assistant Gazelle V5)

---

**🚀 Prêt à activer? → [QUICKSTART_ALERTES_HUMIDITE.md](QUICKSTART_ALERTES_HUMIDITE.md)**
