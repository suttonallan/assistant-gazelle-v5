# 🚀 QUICKSTART - Alertes d'Humidité

## TL;DR (Too Long; Didn't Read)

**3 commandes pour activer tout le système:**

```bash
# 1. Exécuter le SQL dans Supabase SQL Editor
#    Copie-colle le contenu de: sql/add_archived_to_humidity_alerts_fixed.sql

# 2. Tester l'API
./scripts/test_humidity_integration.sh

# 3. Démarrer le frontend
cd frontend && npm run dev
```

**C'est tout!** ✨

---

## Étape 1: SQL (30 secondes)

1. Ouvre https://supabase.com/dashboard
2. SQL Editor → New Query
3. Copie-colle `sql/add_archived_to_humidity_alerts_fixed.sql`
4. Run

**Vérification rapide:**
```sql
SELECT COUNT(*) FROM humidity_alerts_active;
```
Pas d'erreur? → ✅ Ça marche!

---

## Étape 2: Test API (30 secondes)

```bash
./scripts/test_humidity_integration.sh
```

**Attendu:** `🎉 TOUS LES TESTS SONT PASSÉS!`

---

## Étape 3: Frontend (30 secondes)

```bash
cd frontend
npm run dev
```

Ouvre http://localhost:5173 → Onglet "Tableau de bord"

**Si aucune alerte:** Page normale, pas de carte orange (c'est normal!)
**Si des alertes:** Carte orange visible avec bouton "Voir les détails"

---

## 🎯 Utilisation

### Dashboard principal

**Accès:** Onglet "Tableau de bord"

**Si alertes non résolues:**
- Carte orange apparaît automatiquement
- Clique "🔍 Voir les détails" → Dashboard complet
- Clique "✅ Résoudre" pour marquer une alerte comme résolue
- Clique "📦 Archiver" pour archiver une alerte

**Si aucune alerte:**
- Rien ne s'affiche (tableau de bord reste épuré)

### Page Configuration

**Accès:** Onglet "Configuration" → Section "Alertes Maintenance Institutionnelle"

**Contenu:**
- Stats complètes
- Liste des institutions surveillées
- Bouton "Actualiser" pour forcer un refresh

---

## 🔧 Commandes utiles

### Scanner manuel
```bash
# Scanner les 7 derniers jours
python -c "from modules.alerts.humidity_scanner_safe import HumidityScannerSafe; scanner = HumidityScannerSafe(); print(scanner.scan_new_entries(days_back=7))"
```

### Vérifier les stats
```bash
curl http://localhost:8000/api/humidity-alerts/stats | jq
```

### Tester les endpoints
```bash
# Non résolues
curl http://localhost:8000/api/humidity-alerts/unresolved | jq

# Résolues
curl http://localhost:8000/api/humidity-alerts/resolved | jq

# Archivées
curl http://localhost:8000/api/humidity-alerts/archived | jq
```

---

## 📝 Configuration

### Changer les institutions surveillées

Édite `api/humidity_alerts_routes.py` ligne 58:
```python
INSTITUTIONAL_CLIENTS = [
    'Vincent d\'Indy',
    'Place des Arts',
    'Orford',
    'Nouvelle Institution'  # ← Ajoute ici
]
```

### Changer l'horaire du scan automatique

Édite `api/humidity_alerts_routes.py` ligne 488:
```python
hour=16,  # ← Change l'heure ici (format 24h)
```

### Modifier les mots-clés de détection

Édite `config/alerts/config.json`:
```json
{
  "alert_keywords": {
    "housse": ["housse enlevée", "sans housse"],
    "nouveau_type": ["mot-clé 1", "mot-clé 2"]
  }
}
```

---

## 🆘 Problèmes courants

### Erreur 500 sur l'API
→ SQL pas exécuté. Retourne à l'Étape 1.

### Carte n'apparaît jamais
→ Normal si aucune alerte. Vérifie avec:
```bash
curl http://localhost:8000/api/humidity-alerts/stats
```

### Tests échouent
→ Vérifie que:
1. L'API tourne (`python api/main.py`)
2. Le SQL a été exécuté sur Supabase
3. Les variables d'environnement sont définies dans `.env`

---

## 📚 Documentation complète

- [CHECKLIST_ACTIVATION.md](CHECKLIST_ACTIVATION.md) - Checklist étape par étape
- [RESUME_INTEGRATION_ALERTES.md](RESUME_INTEGRATION_ALERTES.md) - Vue d'ensemble
- [GUIDE_ACTIVATION_ALERTES_HUMIDITE.md](GUIDE_ACTIVATION_ALERTES_HUMIDITE.md) - Guide détaillé
- [INTEGRATION_ALERTES_HUMIDITE_COMPLETE.md](INTEGRATION_ALERTES_HUMIDITE_COMPLETE.md) - Référence technique

---

## ✨ Fonctionnalités

### Détection automatique
- Scanner quotidien à 16h
- Détecte 4 types d'alertes:
  - 🛡️ Housse (enlevée/replacée)
  - ⚡ Alimentation (débranché/rebranché)
  - 💧 Réservoir (vide/rempli)
  - 🌡️ Environnement (fenêtre ouverte/fermée)

### 3 listes
1. **Non résolues** - Alertes actives nécessitant une action
2. **Résolues** - Alertes traitées mais visibles
3. **Archivées** - Alertes masquées de l'interface

### Actions disponibles
- **Résoudre** - Marque comme résolue (avec notes optionnelles)
- **Archiver** - Masque de l'interface
- **Actualiser** - Recharge les données

### Institutions surveillées
- Vincent d'Indy
- Place des Arts
- Orford

---

**C'est parti!** 🚀
