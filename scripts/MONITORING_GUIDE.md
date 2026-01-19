# 🔍 Guide de Monitoring en Temps Réel - Backfill Historique

**Date:** 2026-01-18
**Pour:** Allan - Surveillance active du backfill

---

## 🎯 Objectif

**NE PLUS ATTENDRE 1 HEURE** pour découvrir qu'un script a planté.
**VOIR EN DIRECT** ce qui se passe, entrée par entrée, batch par batch.

---

## 🚀 Démarrage Rapide

### Option 1: Dashboard Interactif (RECOMMANDÉ 🌟)

```bash
# Terminal 1: Lancer le backfill (si pas déjà lancé)
python3 scripts/history_recovery_year_by_year.py --start-year 2024 --end-year 2024

# Terminal 2: Lancer le monitoring en temps réel
python3 scripts/watch_backfill.py --years 2024 --interval 3
```

**Ce que tu verras:**
```
================================================================================
🔍 MONITORING BACKFILL EN TEMPS RÉEL
================================================================================
⏰ Démarré: 09:15:32
⏱️  Uptime: 127s
🔄 Rafraîchissement: toutes les 3 secondes (Ctrl+C pour quitter)
================================================================================

📊 TOTAL DANS SUPABASE: 45,234 entrées

📅 PAR ANNÉE:
--------------------------------------------------------------------------------
Année      Entrées         Taux                 Statut
--------------------------------------------------------------------------------
2024       12,567          45.3 e/s (ETA: ~14 min)  🟢 En cours (actif)
2023       8,432           Stable               ✅ Avancé
2022       24,235          Stable               ✅ Avancé
--------------------------------------------------------------------------------

📝 DERNIÈRES ENTRÉES IMPORTÉES:
--------------------------------------------------------------------------------
  • tme_abc123def456     | SERVICE_ENTRY_MANUAL | 2024-11-15 14:23:00
  • tme_xyz789ghi012     | PIANO_MEASUREMENT    | 2024-11-15 14:20:15
  • tme_jkl345mno678     | APPOINTMENT          | 2024-11-15 14:18:42
--------------------------------------------------------------------------------

💡 AIDE:
  - Le dashboard se rafraîchit automatiquement
  - Taux = entrées/seconde (ETA = temps estimé restant)
  - Si le taux est 'Stable', l'import est peut-être terminé ou bloqué
  - Ctrl+C pour quitter
================================================================================
```

**Avantages:**
- ✅ Vue d'ensemble claire
- ✅ Taux d'import en temps réel (entrées/seconde)
- ✅ ETA estimé
- ✅ Dernières entrées importées
- ✅ Rafraîchissement automatique

---

### Option 2: Logs Verbeux (dans le script lui-même)

Le script `history_recovery_year_by_year.py` a été amélioré avec des **logs en temps réel**:

```bash
# Lancer le script avec logs verbeux
python3 scripts/history_recovery_year_by_year.py --start-year 2024 --end-year 2024
```

**Ce que tu verras maintenant:**
```
======================================================================
📅 ANNÉE 2024
======================================================================
📥 Récupération des entrées depuis Gazelle...
   🔍 Période: 2024-01-01T00:00:00Z → 2024-12-31T23:59:59Z
   ⏳ Pagination en cours (100 entrées/page)...

✅ 50,234 entrées récupérées pour 2024

💾 Import dans Supabase par batch de 500...
📦 Total de 101 batches à traiter

  📍 Batch 1/101 | Entrées 0-500/50,234 (1.0%)
  🔍 Premier record keys: ['external_id', 'client_id', 'piano_id', ...]
  🔍 entry_type du premier: SERVICE_ENTRY_MANUAL
     ⏳ UPSERT de 500 records... ✅ 500 entrées | Total: 500/50,234

  📍 Batch 2/101 | Entrées 500-1,000/50,234 (2.0%)
     ⏳ UPSERT de 500 records... ✅ 500 entrées | Total: 1,000/50,234

  📍 Batch 3/101 | Entrées 1,000-1,500/50,234 (3.0%)
     ⏳ UPSERT de 500 records... ✅ 500 entrées | Total: 1,500/50,234

  [...]

  📍 Batch 42/101 | Entrées 20,500-21,000/50,234 (40.8%)
     ⏳ UPSERT de 500 records... ❌ ÉCHOUÉ!
     🔄 Retry entrée par entrée (500 records)... ✅ 487 succès, ❌ 13 erreurs

  [...]

======================================================================
✅ Année 2024 : 49,821 entrées importées
❌ Erreurs : 413
======================================================================
```

**Informations en direct:**
- ✅ **Progression** → `Batch X/Y | Entrées A-B/Total (% complété)`
- ✅ **Statut UPSERT** → `⏳ En cours... ✅ Succès | ❌ Échec`
- ✅ **Total cumulé** → `Total: 1,500/50,234`
- ✅ **Retry détaillé** → Si batch échoue, affiche combien de retries ont réussi

---

## 📊 Commandes Utiles

### Monitorer Plusieurs Années

```bash
# Monitorer 2024, 2023, 2022
python3 scripts/watch_backfill.py --years 2024 2023 2022

# Monitorer toutes les années (2016-2024)
python3 scripts/watch_backfill.py --years 2024 2023 2022 2021 2020 2019 2018 2017 2016
```

### Rafraîchissement Plus Rapide

```bash
# Rafraîchissement chaque seconde (au lieu de 3)
python3 scripts/watch_backfill.py --years 2024 --interval 1
```

### Vérifier Manuellement dans Supabase

```sql
-- Compter les entrées par année
SELECT
    EXTRACT(YEAR FROM occurred_at) as year,
    COUNT(*) as count
FROM gazelle_timeline_entries
WHERE occurred_at >= '2016-01-01'
GROUP BY EXTRACT(YEAR FROM occurred_at)
ORDER BY year DESC;

-- Voir les 10 dernières entrées importées
SELECT
    external_id,
    entry_type,
    occurred_at,
    created_at
FROM gazelle_timeline_entries
ORDER BY created_at DESC
LIMIT 10;

-- Vérifier les doublons (devrait être 0)
SELECT external_id, COUNT(*) as count
FROM gazelle_timeline_entries
GROUP BY external_id
HAVING COUNT(*) > 1;
```

---

## 🚨 Détection de Problèmes

### Scénario 1: Le Taux Devient "Stable" et Reste à 0

**Signification:** L'import s'est arrêté (terminé ou bloqué)

**Action:**
1. Vérifier dans le terminal du script si un message d'erreur s'affiche
2. Si c'est terminé: Message "✅ Année 2024 : X entrées importées"
3. Si c'est bloqué: Aucun message depuis 1+ minute → Vérifier les logs

---

### Scénario 2: Taux Très Lent (<5 e/s)

**Signification:** Import très lent (problème réseau ou API)

**Actions possibles:**
1. **Réseau lent:** Attendre, le script continuera
2. **API Gazelle lente:** Attendre, pagination automatique
3. **Supabase lent:** Vérifier le dashboard Supabase (pas de quota dépassé)

---

### Scénario 3: "❌ ÉCHOUÉ!" puis Retry

**Signification:** Batch a échoué (probablement FK manquante), retry en cours

**Ce qui se passe:**
1. Le script tente d'insérer 500 entrées en batch → Échoue
2. Le script réessaie **entrée par entrée** avec `user_id=NULL`
3. Affiche combien ont réussi vs échoué

**Action:** Aucune, c'est normal! Le script gère automatiquement.

**Exemple:**
```
📍 Batch 42/101
   ⏳ UPSERT de 500 records... ❌ ÉCHOUÉ!
   🔄 Retry entrée par entrée (500 records)... ✅ 487 succès, ❌ 13 erreurs
```
→ Sur 500 entrées, 487 ont été importées, 13 ont échoué (user_id FK manquante)

---

### Scénario 4: Dashboard Montre 0 Entrées Après 5+ Minutes

**Signification:** Problème avec le script ou aucune donnée récupérée

**Actions:**
1. Vérifier le terminal du script: Y a-t-il un message d'erreur?
2. Vérifier Supabase manuellement (SQL ci-dessus)
3. Vérifier les credentials API Gazelle (`.env`)

---

## 🛠️ Dépannage

### Le Dashboard Ne S'Affiche Pas

**Erreur possible:** Module Supabase manquant

**Solution:**
```bash
pip install supabase
```

---

### Le Script `history_recovery` Ne Lance Pas

**Erreur possible:** Token Gazelle expiré

**Solution:**
```bash
# Vérifier le token
cat config/token.json

# Si expiré, régénérer (voir docs/OAUTH_SETUP_GUIDE.md)
```

---

### Dashboard Affiche "Aucune entrée récente"

**Cause:** Import pas encore commencé ou terminé depuis longtemps

**Action:** Vérifier le total global:
- Si total > 0 → Import précédent, pas de nouvel import actif
- Si total = 0 → Problème, script n'a rien importé

---

## 📈 Métriques de Performance Attendues

### Import 2024 (≈50,000 entrées)

| Métrique | Valeur Attendue |
|----------|----------------|
| **Taux moyen** | 30-50 entrées/seconde |
| **Durée totale** | 15-30 minutes |
| **Batches** | ≈100 batches (500 entrées/batch) |
| **Erreurs** | <5% du total (≈2,500 max) |

### Taux Typiques

- 🟢 **50+ e/s** → Excellent (réseau rapide)
- 🟡 **20-50 e/s** → Bon (normal)
- 🟠 **10-20 e/s** → Lent (réseau ou API)
- 🔴 **<10 e/s** → Très lent (problème possible)

---

## 🎓 Exemples de Sessions

### Session Normale (Tout Va Bien)

```bash
# Terminal 1
$ python3 scripts/history_recovery_year_by_year.py --start-year 2024 --end-year 2024

======================================================================
📅 ANNÉE 2024
======================================================================
📥 Récupération... ✅ 50,234 entrées récupérées

💾 Import par batch de 500...
  📍 Batch 1/101 | 0-500/50,234 (1.0%)
     ⏳ UPSERT... ✅ 500 entrées | Total: 500/50,234
  📍 Batch 2/101 | 500-1,000/50,234 (2.0%)
     ⏳ UPSERT... ✅ 500 entrées | Total: 1,000/50,234
  [...]
  📍 Batch 101/101 | 50,000-50,234/50,234 (100.0%)
     ⏳ UPSERT... ✅ 234 entrées | Total: 50,234/50,234

✅ Année 2024 : 50,234 entrées importées
❌ Erreurs : 0
======================================================================
```

```bash
# Terminal 2
$ python3 scripts/watch_backfill.py --years 2024

📊 TOTAL: 50,234 entrées

Année      Entrées         Taux                 Statut
2024       50,234          Stable               ✅ Avancé

✅ Import terminé avec succès!
```

---

### Session Avec Erreurs (Gérées Automatiquement)

```bash
# Terminal 1
  📍 Batch 42/101 | 20,500-21,000/50,234 (40.8%)
     ⏳ UPSERT... ❌ ÉCHOUÉ!
     ⚠️  Erreur: Foreign key violation (user_id)
     🔄 Retry entrée par entrée... ✅ 487 succès, ❌ 13 erreurs

  📍 Batch 43/101 | 21,000-21,500/50,234 (41.8%)
     ⏳ UPSERT... ✅ 500 entrées | Total: 21,487/50,234

[Import continue normalement...]

✅ Année 2024 : 49,821 entrées importées
❌ Erreurs : 413
```

**Résultat:** Sur 50,234 entrées, 49,821 importées (99.2% de succès)

---

## 🏁 Conclusion

### Avant (Situation Frustrante)
- ❌ Lancer script, attendre 1 heure
- ❌ Découvrir qu'il a planté après 5 minutes
- ❌ Aucune idée de la progression
- ❌ Relancer et re-attendre 1 heure

### Maintenant (Contrôle Total)
- ✅ **Dashboard en temps réel** → Progression visible
- ✅ **Logs verbeux** → Chaque batch affiché
- ✅ **Taux + ETA** → Savoir combien de temps reste
- ✅ **Détection immédiate** → Voir les erreurs quand elles arrivent
- ✅ **Gestion automatique** → Retry sur erreurs FK

---

## 🎯 Commandes Favorites (Aide-Mémoire)

```bash
# 1. Lancer backfill 2024
python3 scripts/history_recovery_year_by_year.py --start-year 2024 --end-year 2024

# 2. Monitorer en temps réel (autre terminal)
python3 scripts/watch_backfill.py --years 2024

# 3. Vérifier manuellement (Supabase SQL)
SELECT COUNT(*) FROM gazelle_timeline_entries WHERE occurred_at >= '2024-01-01';

# 4. Voir les dernières entrées
SELECT * FROM gazelle_timeline_entries ORDER BY created_at DESC LIMIT 10;
```

---

**Créé le:** 2026-01-18
**Par:** Claude Code (ton génie aidant 🧞)
**Pour:** Allan Sutton
**Statut:** ✅ PRÊT À L'EMPLOI
