# 📋 COMMANDES D'IMPORT ANNÉE PAR ANNÉE

**Stratégie:** Option C - Contrôle maximal  
**Durée:** ~30 minutes par année  
**Avantage:** Validation complète entre chaque import

---

## 🎯 ORDRE RECOMMANDÉ (Du plus récent au plus ancien)

### Année 2023 (la plus récente à importer)
```bash
cd /Users/allansutton/Documents/assistant-gazelle-v5
python3 scripts/history_recovery_year_by_year.py --start-year 2023 --end-year 2023
```
**Durée:** ~30 minutes  
**Entrées attendues:** ~18,000  
**Status actuel:** 14,293 entrées (partiel)

---

### Année 2022
```bash
python3 scripts/history_recovery_year_by_year.py --start-year 2022 --end-year 2022
```
**Durée:** ~30 minutes  
**Entrées attendues:** ~17,000  
**Status actuel:** 15,721 entrées (partiel)

---

### Année 2021
```bash
python3 scripts/history_recovery_year_by_year.py --start-year 2021 --end-year 2021
```
**Durée:** ~30 minutes  
**Entrées attendues:** ~16,000  
**Status actuel:** 13,716 entrées (partiel)

---

### Année 2020
```bash
python3 scripts/history_recovery_year_by_year.py --start-year 2020 --end-year 2020
```
**Durée:** ~30 minutes  
**Entrées attendues:** ~15,000  
**Status actuel:** 12,992 entrées (partiel)

---

### Année 2019
```bash
python3 scripts/history_recovery_year_by_year.py --start-year 2019 --end-year 2019
```
**Durée:** ~30 minutes  
**Entrées attendues:** ~15,000  
**Status actuel:** 14,879 entrées (partiel)

---

### Année 2018
```bash
python3 scripts/history_recovery_year_by_year.py --start-year 2018 --end-year 2018
```
**Durée:** ~30 minutes  
**Entrées attendues:** ~15,000  
**Status actuel:** 13,045 entrées (partiel)

---

### Année 2017
```bash
python3 scripts/history_recovery_year_by_year.py --start-year 2017 --end-year 2017
```
**Durée:** ~25 minutes  
**Entrées attendues:** ~12,000  
**Status actuel:** 10,968 entrées (partiel)

---

### Année 2016 (la plus ancienne)
```bash
python3 scripts/history_recovery_year_by_year.py --start-year 2016 --end-year 2016
```
**Durée:** ~25 minutes  
**Entrées attendues:** ~12,000  
**Status actuel:** 5,044 entrées (partiel)

---

## ✅ APRÈS CHAQUE IMPORT

### Vérifier le succès
```bash
# Voir le résumé final
tail -30 recovery_ANNÉE.log | grep -E "RÉSUMÉ|entrées importées|Erreurs"

# Exemple pour 2023
tail -30 recovery_2023.log | grep -E "RÉSUMÉ|entrées importées|Erreurs"
```

### Vérifier dans Supabase
```python
python3 << 'EOF'
from core.supabase_storage import SupabaseStorage
s = SupabaseStorage()

# Remplacer 2023 par l'année concernée
result = s.client.table('gazelle_timeline_entries')\
    .select('id', count='exact')\
    .gte('occurred_at', '2023-01-01')\
    .lt('occurred_at', '2024-01-01')\
    .limit(1)\
    .execute()

print(f"✅ Total 2023: {result.count:,} entrées")
EOF
```

---

## 📊 PROGRESSION TOTALE

Utilise ce script pour voir ta progression globale:

```bash
python3 << 'EOF'
from core.supabase_storage import SupabaseStorage
s = SupabaseStorage()

print("\n" + "="*60)
print("📊 PROGRESSION IMPORT HISTORIQUE")
print("="*60 + "\n")

total = 0
for year in range(2016, 2026):
    result = s.client.table('gazelle_timeline_entries')\
        .select('id', count='exact')\
        .gte('occurred_at', f'{year}-01-01')\
        .lt('occurred_at', f'{year+1}-01-01')\
        .limit(1)\
        .execute()
    
    count = result.count if hasattr(result, 'count') else 0
    total += count
    
    status = "✅" if count > 15000 else "🔄" if count > 10000 else "⚠️"
    print(f"{year}: {status} {count:>7,} entrées")

print(f"\n{'TOTAL':<5}: {total:>10,} entrées")
print(f"Objectif: 180,000")
print(f"Progrès: {total*100/180000:.1f}%")
print("\n" + "="*60 + "\n")
EOF
```

---

## 🎯 PLANNING SUGGÉRÉ

### Scénario 1: Sprint intensif (1-2 jours)
- **Aujourd'hui:** 2023, 2022, 2021, 2020 (2h)
- **Demain:** 2019, 2018, 2017, 2016 (2h)

### Scénario 2: Rythme normal (1 semaine)
- **Lundi:** 2023
- **Mardi:** 2022
- **Mercredi:** 2021
- **Jeudi:** 2020
- **Vendredi:** 2019, 2018, 2017, 2016

### Scénario 3: Tranquille (au fil de l'eau)
- Une année quand tu as 30 min de libre
- Pas de pression, ça se fait progressivement

---

## ⚠️ EN CAS DE PROBLÈME

### Le script plante
```bash
# Relancer juste cette année
python3 scripts/history_recovery_year_by_year.py --start-year 2023 --end-year 2023

# Voir les logs
tail -100 recovery_2023.log
```

### Vérifier qu'aucun import ne tourne déjà
```bash
ps aux | grep history_recovery
```

### Tuer un import en cours si nécessaire
```bash
pkill -f history_recovery
```

---

## 💡 ASTUCE PRO

Pour lancer plusieurs années d'affilée sans supervision:

```bash
# Lance 2023, puis 2022, puis 2021 automatiquement
python3 scripts/history_recovery_year_by_year.py --start-year 2023 --end-year 2023 && \
python3 scripts/history_recovery_year_by_year.py --start-year 2022 --end-year 2022 && \
python3 scripts/history_recovery_year_by_year.py --start-year 2021 --end-year 2021
```

---

**Créé le:** 18 janvier 2026  
**Mode:** Option C - Contrôle maximal année par année
