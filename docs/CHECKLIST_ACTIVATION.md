# ✅ Checklist d'activation - Alertes d'Humidité

## Étape 1: Exécuter le SQL sur Supabase ⏱️ 2 minutes

### Option A: Via l'interface web (Recommandé)

- [ ] 1. Ouvrir https://supabase.com/dashboard
- [ ] 2. Sélectionner ton projet Gazelle V5
- [ ] 3. Cliquer sur **SQL Editor** dans le menu de gauche
- [ ] 4. Cliquer sur **New Query**
- [ ] 5. Ouvrir le fichier `sql/add_archived_to_humidity_alerts_fixed.sql`
- [ ] 6. Copier tout le contenu (Cmd+A puis Cmd+C)
- [ ] 7. Coller dans l'éditeur SQL de Supabase (Cmd+V)
- [ ] 8. Cliquer sur **Run** (ou Ctrl+Enter)
- [ ] 9. Vérifier qu'il n'y a **pas d'erreurs** (message de succès en vert)

### Vérification que ça a fonctionné

Dans le même éditeur SQL de Supabase, exécute cette requête:

```sql
-- Test 1: Vérifier que la vue existe
SELECT COUNT(*) as count FROM humidity_alerts_active;
```

**Attendu:** Un nombre (même 0) sans erreur ✅

```sql
-- Test 2: Vérifier que les colonnes existent
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'humidity_alerts'
  AND column_name IN ('archived', 'resolved_at', 'resolution_notes');
```

**Attendu:** 3 lignes retournées ✅

```sql
-- Test 3: Vérifier que les fonctions existent
SELECT routine_name
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND routine_name IN ('resolve_humidity_alert', 'archive_humidity_alert');
```

**Attendu:** 2 lignes retournées ✅

---

## Étape 2: Tester l'API ⏱️ 1 minute

- [ ] 1. Ouvrir un terminal
- [ ] 2. Naviguer vers le dossier du projet:
  ```bash
  cd /Users/allansutton/Documents/assistant-gazelle-v5
  ```

- [ ] 3. Démarrer l'API (si pas déjà démarrée):
  ```bash
  python api/main.py
  ```

- [ ] 4. Attendre le message: `✅ API PRÊTE`

- [ ] 5. Dans un **nouveau terminal**, exécuter le script de test:
  ```bash
  ./scripts/test_humidity_integration.sh
  ```

**Attendu:**
```
🧪 TEST D'INTÉGRATION - ALERTES D'HUMIDITÉ
==========================================

1️⃣  TEST DES ENDPOINTS API
----------------------------
Test: Stats globales... ✅ OK (HTTP 200)
Test: Alertes non résolues... ✅ OK (HTTP 200)
Test: Alertes résolues... ✅ OK (HTTP 200)
Test: Alertes archivées... ✅ OK (HTTP 200)
Test: Alertes institutionnelles... ✅ OK (HTTP 200)

2️⃣  VÉRIFICATION DES DONNÉES
----------------------------
Récupération stats... ✅ OK
   Total: 0
   Non résolues: 0
   Résolues: 0

3️⃣  RÉSUMÉ
----------------------------
Tests réussis: 6/6
Tests échoués: 0/6

🎉 TOUS LES TESTS SONT PASSÉS!
```

---

## Étape 3: Tester le Frontend ⏱️ 2 minutes

- [ ] 1. Dans un **nouveau terminal**, naviguer vers le frontend:
  ```bash
  cd /Users/allansutton/Documents/assistant-gazelle-v5/frontend
  ```

- [ ] 2. Démarrer le frontend (si pas déjà démarré):
  ```bash
  npm run dev
  ```

- [ ] 3. Ouvrir le navigateur sur http://localhost:5173

- [ ] 4. Cliquer sur l'onglet **"Tableau de bord"**

### Scénario A: Aucune alerte (Normal au début)

**Attendu:**
- Page se charge sans erreur
- Pas de carte orange d'alertes
- Stats normales affichées (Total modifications, etc.)

**✅ C'est bon!** Le système fonctionne, il n'y a juste pas d'alertes pour le moment.

### Scénario B: Des alertes existent

**Attendu:**
- Carte orange visible en haut: "🏛️ Alertes Maintenance Institutionnelle"
- Stats affichées: Total / Non résolues / Résolues
- Bouton "🔍 Voir les détails" présent

- [ ] 5. Cliquer sur "🔍 Voir les détails"

**Attendu:**
- Dashboard complet s'affiche en dessous
- Liste des alertes visible
- Boutons "✅ Résoudre" et "📦 Archiver" présents

- [ ] 6. (Optionnel) Tester la résolution d'une alerte:
  - Cliquer sur "✅ Résoudre" sur une alerte
  - Confirmer dans la popup
  - L'alerte passe dans l'onglet "Résolues"

---

## Étape 4: Vérifier la page Configuration ⏱️ 30 secondes

- [ ] 1. Cliquer sur l'onglet **"Configuration"** dans le menu

- [ ] 2. Vérifier que la section "Alertes Maintenance Institutionnelle" est visible

**Attendu:**
- Section visible avec les mêmes stats
- Bouton "Actualiser" fonctionne
- Institutions surveillées affichées: Vincent d'Indy, Place des Arts, Orford

---

## Étape 5: (Optionnel) Lancer un scan manuel ⏱️ 1 minute

Pour tester le scanner et générer des alertes de test:

```bash
python -c "
from modules.alerts.humidity_scanner_safe import HumidityScannerSafe
scanner = HumidityScannerSafe()
result = scanner.scan_new_entries(days_back=30)
print(f'Scan terminé: {result}')
"
```

**Attendu:**
```
🔍 Scan depuis: 2025-12-12T...
📊 500 entrées récupérées
📅 X entrées dans les 30 dernier(s) jour(s)
✅ Scan terminé: X entrées scannées, Y alertes détectées, Z nouvelles
```

Si des alertes sont détectées, elles apparaîtront maintenant dans le tableau de bord!

---

## ✅ Checklist finale

- [ ] SQL exécuté sur Supabase (Étape 1)
- [ ] API démarre sans erreur
- [ ] Tests API passent tous (6/6)
- [ ] Frontend se charge sans erreur
- [ ] Tableau de bord s'affiche correctement
- [ ] Page Configuration fonctionne
- [ ] (Optionnel) Scanner manuel fonctionne

---

## 🆘 En cas de problème

### Erreur: "relation humidity_alerts_active does not exist"

**Solution:** Le SQL n'a pas été exécuté. Retourne à l'Étape 1.

### Erreur: "column archived does not exist"

**Solution:** Les colonnes n'ont pas été ajoutées. Exécute manuellement dans Supabase:
```sql
ALTER TABLE humidity_alerts ADD COLUMN IF NOT EXISTS archived BOOLEAN DEFAULT FALSE;
ALTER TABLE humidity_alerts ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMPTZ;
ALTER TABLE humidity_alerts ADD COLUMN IF NOT EXISTS resolution_notes TEXT;
```

### Erreur 500 sur /api/humidity-alerts/stats

**Solution:** Vérifie que:
1. L'API tourne (`python api/main.py`)
2. Les variables d'environnement Supabase sont définies dans `.env`
3. Le SQL a bien été exécuté

### La carte n'apparaît jamais

**Solution:** Normal si `institutional_unresolved = 0`. Vérifie avec:
```bash
curl http://localhost:8000/api/humidity-alerts/stats | jq
```

Si `"institutional_unresolved": 0` → Tout va bien, il n'y a juste pas d'alertes!

### Frontend: "Module not found: HumidityAlertsDashboard"

**Solution:** Vérifie que le fichier existe:
```bash
ls frontend/src/components/HumidityAlertsDashboard.jsx
```

S'il n'existe pas, il a été supprimé par erreur. Récupère-le depuis le commit précédent.

---

## 📚 Documentation complète

Pour plus de détails, consulte:

- [RESUME_INTEGRATION_ALERTES.md](RESUME_INTEGRATION_ALERTES.md) - Vue d'ensemble visuelle
- [GUIDE_ACTIVATION_ALERTES_HUMIDITE.md](GUIDE_ACTIVATION_ALERTES_HUMIDITE.md) - Guide détaillé
- [INTEGRATION_ALERTES_HUMIDITE_COMPLETE.md](INTEGRATION_ALERTES_HUMIDITE_COMPLETE.md) - Référence technique

---

## 🎉 Félicitations!

Si toutes les étapes sont cochées, le système d'alertes d'humidité est **entièrement opérationnel** et **proprement intégré** dans le tableau de bord!

Le scanner automatique tournera tous les jours à 16h pour détecter de nouvelles alertes.

---

**Date d'activation:** _______________
**Testé par:** _______________
**Statut:** ⬜ En attente  ⬜ En cours  ⬜ Terminé ✅
