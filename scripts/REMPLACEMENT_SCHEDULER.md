# 🔄 Remplacement Import Quotidien Scheduler

## 📋 Changement Effectué

Le scheduler quotidien (01:00) utilise maintenant **`smart_import_all_data.py`** au lieu de `sync_to_supabase.py` pour la partie **Timeline**.

## ✅ Avantages

1. **Filtre Anti-Bruit** : Rejette Mailchimp, emails ouverts, création/suppression rendez-vous
2. **Haute Valeur Uniquement** : Garde seulement les entrées techniques utiles
3. **Extraction de Mesures** : Humidité, température, fréquence dans metadata
4. **Même Performance** : 7 jours = ~30 secondes (comme avant)

## 🔧 Modification Technique

**Fichier:** `core/scheduler.py` ligne ~168

**Avant:**
```python
timeline_count = syncer.sync_timeline()  # Importe TOUT (y compris bruit)
```

**Après:**
```python
# Utilise smart_import avec filtre anti-bruit (7 derniers jours)
from scripts.smart_import_all_data import SmartImport
smart_importer = SmartImport(dry_run=False, delay=0.3)
timeline_result = smart_importer.import_timeline(since_date=since_date_iso)
timeline_count = timeline_result.get('imported', 0)
```

## 📊 Impact

| Aspect | Avant (sync_to_supabase) | Après (smart_import) |
|--------|-------------------------|---------------------|
| **Bruit** | ✅ Importe Mailchimp, emails | ❌ Rejette (filtre) |
| **Qualité** | Toutes les entrées | Haute valeur uniquement |
| **Mesures** | ❌ Non extraites | ✅ Extraites (metadata) |
| **Performance** | ~30 secondes | ~30 secondes |
| **Période** | 7 derniers jours | 7 derniers jours |

## 🎯 Résultat

**Chaque nuit à 01:00:**
- ✅ Clients, Contacts, Pianos (inchangé)
- ✅ **Timeline filtrée** (anti-bruit) - NOUVEAU
- ✅ Appointments (inchangé)

**Bénéfice:** L'assistant a accès à un historique propre, sans bruit administratif.

## ⚠️ Note

- Les autres parties (clients, pianos, appointments) continuent avec `sync_to_supabase.py`
- Seule la Timeline utilise `smart_import` pour le filtre anti-bruit
- Le scheduler continue de fonctionner normalement
