# ⏸️ Pause Scheduler Cette Nuit

## 🎯 Problème

Le script `smart_import_all_data.py` est en train d'importer l'historique depuis 2016.

Le scheduler automatique est programmé pour 01:00 (heure Montréal).

**Risque:** Les deux processus pourraient écrire en parallèle dans Supabase.

## ✅ Solution: UPSERT Protège

**Bonne nouvelle:** Les deux utilisent UPSERT donc **pas de doublons**.

**MAIS:**
- ⚠️ Deux processus qui écrivent en parallèle = **ralentissement**
- ⚠️ Risque de surcharge API Supabase
- ⚠️ Logs mélangés = confusion

## 💡 Recommandations

### Option 1: Laisser Faire (Si le Script Finira Avant 01:00)

**Si le script smart_import finit avant 01:00:**
- ✅ Aucune action nécessaire
- ✅ Le scheduler continuera normalement après

**Temps estimé smart_import:** 20-60 minutes (selon volume depuis 2016)

### Option 2: Désactiver le Scheduler Pour Cette Nuit (Recommandé)

**Si le script risque de tourner encore à 01:00:**

#### Méthode A: Via API (si disponible)
```bash
# Désactiver la tâche pour cette nuit
curl -X POST http://localhost:8000/api/scheduler/pause/sync_gazelle_totale
```

#### Méthode B: Modifier temporairement scheduler.py

**Comment faire:**
1. Ouvrir `core/scheduler.py`
2. Trouver la ligne `CronTrigger(hour=1, minute=0, ...)`
3. Commenter temporairement ou changer l'heure
4. Redémarrer l'API

**Exemple modification:**
```python
# Temporairement désactivé pour import massif
# trigger=CronTrigger(hour=1, minute=0, timezone='America/Montreal'),
trigger=CronTrigger(hour=2, minute=0, timezone='America/Montreal'),  # Désactivé pour cette nuit
```

### Option 3: Surveiller et Désactiver si Nécessaire

**Vérifier à 00:45 si le script tourne encore:**
```bash
# Vérifier si smart_import tourne encore
ps aux | grep smart_import_all_data

# Si oui, désactiver le scheduler temporairement
# (voir Méthode B ci-dessus)
```

## 🎯 Ma Recommandation

**Pour cette nuit:**

1. **Vérifier la progression du script** à 00:30 et 00:45
   ```bash
   tail -30 import_*.log | grep -E "RÉSUMÉ|importées|Filtre"
   ```

2. **Si le script tourne encore à 00:45:**
   - Désactiver temporairement le scheduler (Méthode B)
   - OU laisser faire (UPSERT protège, juste un peu plus lent)

3. **Après le script terminé:**
   - Réactiver le scheduler pour demain soir
   - OU laisser (il tournera à 02:00 pour le rapport)

## 📊 Statut Actuel

**Script smart_import:** En cours (PID visible avec `ps aux | grep smart_import`)

**Scheduler:** Programmé pour 01:00 Montréal

**Estimation temps restant:** 20-60 minutes depuis le lancement

**Conclusion:** Probablement terminé avant 01:00, mais vérifier à 00:45 pour être sûr.
