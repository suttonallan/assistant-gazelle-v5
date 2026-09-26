# 🚨 DIAGNOSTIC FINAL - Alertes d'Humidité Vides

**Date:** 2026-01-12 09:30
**Statut:** ⚠️ PROBLÈME MAJEUR IDENTIFIÉ

---

## 🎯 RÉSUMÉ EXÉCUTIF

**Le tableau d'alertes est vide parce que les entrées SERVICE (notes d'accordage) ne sont JAMAIS synchronisées depuis Gazelle vers Supabase.**

---

## 🔍 INVESTIGATION COMPLÈTE

### Test 1: Scanner Local ✅

```bash
python3 scripts/scan_institutional_alerts.py
```

**Résultat:** 6 alertes détectées via l'API Gazelle GraphQL
- Vincent d'Indy: 3 alertes (alimentation, environnement x2)
- Place des Arts: 3 alertes (environnement x3)
- Orford: 0 alertes

**Conclusion:** Les alertes EXISTENT dans Gazelle, le scanner fonctionne.

---

### Test 2: Scan depuis Supabase ❌

```bash
python3 scripts/scan_alerts_from_supabase.py
```

**Résultat:** 0 alerte détectée
- 614 entrées scannées (7 jours)
- 951 entrées scannées (14 jours)
- Aucun mot-clé trouvé

**Conclusion:** Les données dans Supabase ne contiennent pas les alertes.

---

### Test 3: Vérification Types d'Entrées ⚠️

```sql
SELECT entry_type, COUNT(*)
FROM gazelle_timeline_entries
WHERE occurred_at >= NOW() - INTERVAL '14 days'
GROUP BY entry_type;
```

**Résultat:**
- APPOINTMENT: 178 entrées
- CONTACT_EMAIL_AUTOMATED: ~400 entrées
- **SERVICE: 0 entrées** ❌

---

### Test 4: Recherche Historique SERVICE ❌

```sql
SELECT COUNT(*)
FROM gazelle_timeline_entries
WHERE entry_type = 'SERVICE';
```

**Résultat:** **0 entrées SERVICE dans toute la base !**

---

## 🚨 PROBLÈME RACINE

### Les Entrées SERVICE Ne Sont Jamais Synchronisées

**Pourquoi c'est critique:**
1. Les alertes d'humidité se trouvent dans les notes d'accordage
2. Les notes d'accordage sont des entrées de type SERVICE
3. Les entrées SERVICE ne sont JAMAIS synchronisées vers Supabase
4. Donc: Aucune alerte ne peut être détectée dans Supabase

**Diagramme du Problème:**

```
┌──────────────────────────────────────────┐
│   API GAZELLE (GraphQL)                  │
│                                          │
│   ✅ Entrées SERVICE existent           │
│   ✅ Alertes détectables (6 trouvées)   │
└──────────────┬───────────────────────────┘
               │
               │ Sync Timeline
               │ (sync_to_supabase.py)
               ▼
┌──────────────────────────────────────────┐
│   SUPABASE                               │
│   gazelle_timeline_entries              │
│                                          │
│   ✅ APPOINTMENTS: 178                  │
│   ✅ CONTACT_EMAIL: ~400                │
│   ❌ SERVICE: 0 (JAMAIS SYNCHRONISÉ)   │
└──────────────┬───────────────────────────┘
               │
               │ Scan Alertes
               │ (humidity_scanner)
               ▼
┌──────────────────────────────────────────┐
│   TABLE humidity_alerts                  │
│                                          │
│   ❌ VIDE (aucune alerte détectée)      │
└──────────────────────────────────────────┘
```

---

## 🔍 VÉRIFICATION DANS LE CODE

### Fichier: modules/sync_gazelle/sync_to_supabase.py

**Méthode:** `sync_timeline_entries()`

**À vérifier:**
1. Est-ce que le code filtre les types d'entrées ?
2. Y a-t-il un filtre `entry_type != SERVICE` ?
3. Les entrées SERVICE sont-elles ignorées volontairement ?

**Ligne à chercher dans le code:**
```python
# Chercher des filtres comme:
if entry_type == 'APPOINTMENT':  # Ou similaire
    continue

# Ou des conditions qui skipent SERVICE
```

---

## ✅ SOLUTIONS POSSIBLES

### Solution 1: Vérifier le Code de Sync (PRIORITÉ)

**Action:**
1. Ouvrir `modules/sync_gazelle/sync_to_supabase.py`
2. Chercher la méthode `sync_timeline_entries()`
3. Vérifier s'il y a un filtre sur `entry_type`
4. S'assurer que les entrées SERVICE sont incluses

**Commande:**
```bash
grep -n "entry_type\|SERVICE" modules/sync_gazelle/sync_to_supabase.py
```

---

### Solution 2: Forcer une Sync Complète Historique

Si les entrées SERVICE n'ont jamais été synchronisées, une sync complète historique les récupérerait.

**MAIS:** Tu as justement optimisé pour éviter les syncs complètes (fenêtre 7 jours).

**Dilemme:**
- Fenêtre 7 jours = ⚡ Rapide mais ne récupère pas l'historique SERVICE
- Sync complète = 🐢 Lente mais récupère tout

**Compromis:**
- Faire UNE sync complète unique pour récupérer les entrées SERVICE historiques
- Puis revenir à la fenêtre 7 jours pour les mises à jour

---

### Solution 3: Scanner Directement via API Gazelle

Utiliser le scanner qui interroge directement l'API Gazelle GraphQL au lieu de Supabase.

**Avantage:**
- Fonctionne immédiatement (6 alertes déjà détectées)
- Pas besoin de fix de sync

**Inconvénient:**
- Plus lent (API externe)
- Nécessite token OAuth

**Le scanner `scan_institutional_alerts.py` a déjà trouvé 6 alertes !**

Mais il a eu des erreurs 400 en essayant de les créer dans Supabase (contraintes de clés étrangères).

---

## 🎯 RECOMMANDATION

### OPTION A: Fix Rapide - Scanner API Gazelle + Fix Erreurs 400

1. ✅ Utiliser `scripts/scan_institutional_alerts.py` (fonctionne)
2. ❌ Fixer les erreurs 400 (contraintes de BD)
3. ✅ Créer les alertes dans Supabase
4. ✅ Afficher dans le frontend

**Temps estimé:** 30 minutes

---

### OPTION B: Fix Complet - Synchroniser les Entrées SERVICE

1. Modifier `sync_to_supabase.py` pour inclure SERVICE
2. Faire UNE sync complète historique
3. Revenir à la fenêtre 7 jours
4. Les alertes seront détectées automatiquement

**Temps estimé:** 2-3 heures

---

### OPTION C: Hybrid - Scanner API + Sync Future

1. Utiliser le scanner API maintenant (6 alertes)
2. Fixer la sync pour inclure SERVICE
3. Les futures alertes seront détectées automatiquement

**Temps estimé:** 1 heure

---

## 📋 PROCHAINES ÉTAPES IMMÉDIATES

### Étape 1: Identifier Pourquoi SERVICE N'est Pas Synchronisé

```bash
# Chercher dans le code
grep -A 10 -B 10 "entry_type" modules/sync_gazelle/sync_to_supabase.py | grep -i service
```

### Étape 2: Tester le Scanner API Gazelle

```bash
# Le scanner a déjà détecté 6 alertes
python3 scripts/scan_institutional_alerts.py
```

**Erreurs 400 à investiguer:**
- Contraintes de clés étrangères (piano_id invalide?)
- Champs manquants

### Étape 3: Décision

**Choix A:** Fix rapide avec scanner API (30 min)
**Choix B:** Fix complet sync SERVICE (2-3h)
**Choix C:** Hybrid (1h)

---

## 📊 DONNÉES COLLECTÉES

### Sync Gazelle (Dernière: 03:55)

- Items synchronisés: 12,045
- Timeline entries: 1,577
- Durée: 1,598 secondes (~26 min)
- Statut: Warning (46 erreurs)

### Scanner API Gazelle

- Vincent d'Indy: 11 entrées scannées → 3 alertes
- Place des Arts: 40 entrées scannées → 3 alertes
- Orford: 0 entrées scannées → 0 alertes
- **Total: 6 alertes détectées**

### Base Supabase

- Timeline entries totales: ~100,000+
- Timeline entries 7 jours: 614
- Timeline entries 14 jours: 951
- **Entrées SERVICE: 0** ❌

---

## 🎓 LEÇON APPRISE

**Les alertes d'humidité dépendent des notes d'accordage (SERVICE).**

Si les entrées SERVICE ne sont pas synchronisées, le système d'alertes ne peut PAS fonctionner, peu importe la qualité du scanner.

**Pipeline complet requis:**
```
Gazelle API → Sync SERVICE → Supabase → Scanner → Alertes → Frontend
     ✅            ❌            ✅         ✅        ❌        ❌
```

**Maillon cassé:** Sync SERVICE

---

**Diagnostic créé le:** 2026-01-12 09:30
**Par:** Assistant Claude Code
**Statut:** ⚠️ PROBLÈME RACINE IDENTIFIÉ - DÉCISION REQUISE
