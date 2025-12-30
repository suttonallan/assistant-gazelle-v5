# Rapport de Réconciliation CSV ↔ Gazelle

**Client:** École Vincent-d'Indy
**Date:** 2025-12-30 17:48:34

---

## 📊 Statistiques

- **Pianos dans Gazelle:** 119
  - Actifs: 59
  - Inactifs: 60
- **Pianos dans CSV:** 91
- **Pianos dans les deux:** 89
- **Pianos seulement dans Gazelle:** 30
- **Pianos seulement dans CSV:** 4

---

## 🆕 Pianos dans Gazelle mais PAS dans CSV

**Total:** 30 pianos

| Gazelle ID | Serial | Marque | Modèle | Local | Status | Dernier Accord |
|------------|--------|--------|--------|-------|--------|----------------|
| `ins_nTxq6YunlmFoFQG0` | j35390909 | Yamaha (arch) | b2PE | VD428 | ACTIVE | 2025-12-07 |
| `ins_n4gZXgPH1A3T3oOz` | j35385892 | Yamaha (Arch) | b2PE | VD427 | ACTIVE | 2025-12-07 |
| `ins_xUC9uZOAVLTxHa3N` | 6448371 | Yamaha Arch | C2x | VD103 | ACTIVE | 2025-08-20 |
| `ins_k9bbjnCI3QEZPh38` | A53983 | Kawai | UST-8G | VD 402  | ACTIVE | 2025-08-11 |
| `ins_iEoxy3WdsYMBU9q1` | None | Test Créé | dans Vincent | None | ACTIVE | None |
| `ins_POxzML5ZRYlGNVZB` | 31604579 | Yamaha |  | VD412 | INACTIVE | 2025-08-25 |
| `ins_1HdzW806WqxPo2Gh` | 6473767 | Yamaha | C2x | VD401 | INACTIVE | 2022-05-15 |
| `ins_1CKUmb1GdOl3OA5r` | j35389808 | Yamaha (Arch) | b2PE | VD431 | INACTIVE | 2022-05-15 |
| `ins_PqJl5eSGnw2V7q14` | j35390572 | Yamaha (Arch) | b2PE | VD423 | INACTIVE | 2022-02-06 |
| `ins_KFaThhExoYDxJg2p` | j35390560 | Yamaha | b2PE | VD102 | INACTIVE | 2022-01-12 |
| `ins_MjCOA7CxuxsyimqL` | j35390458 | Yamaha | b2PE | VD302 | INACTIVE | 2022-01-12 |
| `ins_xSgMnPKFzinUdu6p` | J35385785 | Yamaha (Arch) | b2PE | VD429 | INACTIVE | 2022-01-09 |
| `ins_06Fj9CL99R6AeyxS` | j35381483 | Yamaha | b2PE | VD418 | INACTIVE | 2021-12-03 |
| `ins_VqkDuKaQiQjMry6l` | j35390563 | Yamaha (Arch) | b2PE | VD405 | INACTIVE | 2021-09-02 |
| `ins_ogbgCzIewrvtBGxh` | J30258953 | Arch Yamaha | b2PE | None | INACTIVE | 2019-05-20 |
| `ins_uFBcTDxsxNEyfvj7` | J31280884 | Arch 2012 Yamaha | b2PE |  | INACTIVE | 2019-05-20 |
| `ins_9JbES9m3LYOIB6Oi` | J32305324 | Arch 2013 Yamaha | B2PEC  | Room #304 | INACTIVE | 2019-02-06 |
| `ins_J85xpLf5OFYj5mqu` | J32304991 | Arch 2012 Yamaha | b2PE |  | INACTIVE | 2019-01-10 |
| `ins_RXJMSDTckzu2Xswd` | J32304976 | Arch 2012 Yamaha | b2PE |  | INACTIVE | 2019-01-10 |
| `ins_33YsPMGAEDfE3z37` | 6382524 | Arch Yamaha Q | C2 x | Room #402 | INACTIVE | 2019-01-09 |
| `ins_L84qCDwxGeEVxVtB` | j32305513 | Arch 2012 Yamaha | b2 PE |  | INACTIVE | 2018-11-23 |
| `ins_PjSfxJxGk8tjH8lE` | B2PM J31303042 | Arch 2013 Yamaha |  |  | INACTIVE | 2018-08-31 |
| `ins_Y1ktgXTFYT2hhNMe` | FO33454 | Kawai | None | Room #? | INACTIVE | None |
| `ins_yroRvSXfMXioix5R` | None | Steinway | Bessette | Room #403 | INACTIVE | None |
| `ins_J0b590glsw2SX2Sc` | 952286 | Yamaha | None | Room #505 | INACTIVE | None |
| `ins_pAstUgDBEZlHJxDh` | None | Pratte | None | Room #204 | INACTIVE | None |
| `ins_5fpmqJhh6KQb8rSE` | ZH14999 | Roland | HP-1300E | VD319 | INACTIVE | None |
| `ins_oZl1geNsmIxypXJm` | ZK10203 | Roland | HP-2-PE | VD503 | INACTIVE | None |
| `ins_yrxrIpoTzMwNKv97` | None | Mason & Hamlin | None | Room #Parloir | INACTIVE | None |
| `ins_jP2NxJ4TE0FlmxEn` | ZR10850 | Roland | HP-2-PE | Room #236 | INACTIVE | None |

---

## ⚠️ Pianos dans CSV mais PAS dans Gazelle

**Total:** 4 pianos

| Serial CSV | Marque | Local |
|------------|--------|-------|
| 204 | Pratte | 240 |
| 319 | Roland | 319 |
| B1604579 | Yamaha P22 | 412 |
| Parloir | Mason & Hamlin | Parloir  |

**⚠️ Action requise:** Ces pianos sont dans votre CSV mais introuvables dans Gazelle.
Raisons possibles:
- Piano vendu/retiré de Gazelle
- Erreur de numéro de série dans CSV
- Piano attribué à un autre client dans Gazelle

---

## 💡 Recommandations

### Pianos dans Gazelle uniquement (30)

- **5 pianos actifs** non listés dans CSV
  → Décision: Ajouter au CSV ou marquer comme 'hors inventaire' dans l'interface?

- **25 pianos inactifs** non listés dans CSV
  → Ces pianos ne sont probablement plus à l'école (vendus, retirés)
  → Recommandation: Les masquer par défaut dans l'interface

### Pianos dans CSV uniquement (4)

⚠️ **Action requise:** Vérifier ces pianos manuellement
- Vérifier les numéros de série dans Gazelle
- Confirmer s'ils sont toujours à l'école
- Les retirer du CSV si vendus/transférés

---

**Prochaine étape:**

Exécuter avec `--apply` pour marquer les pianos dans Supabase:
```bash
python3 scripts/reconcile_csv_with_gazelle.py --apply
```