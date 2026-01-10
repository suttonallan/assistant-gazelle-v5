# Ajustement Fréquence - Workflow Scan Humidité

## 🎯 Changement

Réduction de la fréquence d'exécution du workflow de scan d'humidité.

---

## ⏱️ Avant vs Après

### AVANT (❌ Trop fréquent)
```yaml
schedule:
  - cron: '0 13 * * *'  # 8h AM
  - cron: '0 17 * * *'  # 12h PM
  - cron: '0 21 * * *'  # 4h PM
  - cron: '0 1 * * *'   # 8h PM
```

**Problème:** 4 exécutions par jour = coût inutile + surcharge

---

### APRÈS (✅ Optimal)
```yaml
schedule:
  # 1 fois par jour: 9h AM (heure Montréal)
  - cron: '0 14 * * *'  # 9h AM Montréal = 14h UTC
```

**Bénéfices:**
- ✅ Exécution quotidienne suffisante (détection sous 24h)
- ✅ Heure stratégique (début de journée, techniciens disponibles)
- ✅ Réduit coût GitHub Actions (4x moins d'exécutions)

---

## 💡 Rationale

### Pourquoi 1 fois par jour suffit?

**Contexte humidité:**
- Les problèmes d'humidité se développent sur plusieurs jours
- Détection sous 24h est largement suffisante
- Les techniciens travaillent en journée (pas besoin de scan nocturne)

**Scan à 9h AM:**
- Capture les services du jour précédent
- Notifie en début de journée (action immédiate possible)
- Évite les heures creuses (nuit/weekend)

---

## 📊 Impact

| Métrique | Avant | Après | Économie |
|----------|-------|-------|----------|
| Exécutions/jour | 4 | 1 | **-75%** |
| Exécutions/mois | ~120 | ~30 | **-90 runs/mois** |
| Coût GitHub Actions | Élevé | Minimal | **75% économie** |

---

## 🧪 Test Manuel

Si besoin de tester immédiatement:

1. **Va sur GitHub Actions:**
   - https://github.com/allansutton/assistant-gazelle-v5/actions/workflows/humidity_alerts_scanner.yml

2. **Clique "Run workflow"**

3. **Sélectionne la branche** (main)

4. **Clique "Run workflow"** (bouton vert)

**Résultat:** Exécution immédiate sans attendre le cron quotidien.

---

## 📝 Prochains Ajustements Possibles

Si tu constates que la fréquence n'est pas adaptée:

### Option A: 2 fois par jour
```yaml
schedule:
  - cron: '0 14 * * *'  # 9h AM Montréal
  - cron: '0 21 * * *'  # 4h PM Montréal
```

**Cas d'usage:** Détection plus rapide (matin + après-midi)

### Option B: Jours ouvrables seulement
```yaml
schedule:
  - cron: '0 14 * * 1-5'  # 9h AM du lundi au vendredi
```

**Cas d'usage:** Pas besoin de scan weekend (techniciens absents)

---

## ✅ Checklist Complète

- [x] Réduire fréquence à 1x/jour
- [x] Choisir heure stratégique (9h AM)
- [x] Workflow_dispatch activé (test manuel)
- [ ] Configurer secrets GitHub (voir `FIX_GITHUB_SECRETS_HUMIDITY.md`)
- [ ] Tester une exécution manuelle

---

## 📚 Références

- **Workflow modifié**: [.github/workflows/humidity_alerts_scanner.yml](../.github/workflows/humidity_alerts_scanner.yml)
- **Guide secrets**: [FIX_GITHUB_SECRETS_HUMIDITY.md](FIX_GITHUB_SECRETS_HUMIDITY.md)
- **Module scan**: [modules/alerts/humidity_scanner.py](../modules/alerts/humidity_scanner.py)

---

## 🎉 Résultat

✅ **Fréquence optimisée**: 1 fois par jour à 9h AM
✅ **Coût réduit**: -75% d'exécutions GitHub Actions
✅ **Efficacité maintenue**: Détection sous 24h largement suffisante
