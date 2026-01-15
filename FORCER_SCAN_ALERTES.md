# 🚀 FORCER LE SCAN DES ALERTES D'HUMIDITÉ

**Date:** 2026-01-12
**Statut:** ✅ ENDPOINT AJOUTÉ - PRÊT À DÉPLOYER

---

## 🎯 SOLUTION APPLIQUÉE

J'ai ajouté un **endpoint API pour forcer un scan manuel** des alertes d'humidité.

**Fichier modifié:** `api/humidity_alerts_routes.py` (ligne 465)

---

## 📋 ÉTAPES POUR ACTIVER

### 1️⃣ Déployer le Code sur Render

Le nouveau code avec l'endpoint `/scan` doit être déployé sur Render.

**Options:**

**A) Git Push Automatique** (si auto-deploy activé):
```bash
git add api/humidity_alerts_routes.py
git commit -m "feat: Ajouter endpoint scan manuel pour alertes humidité"
git push origin main
```

Render détectera le push et redéployera automatiquement.

**B) Deploy Manuel** (depuis Render Dashboard):
1. Va sur https://dashboard.render.com
2. Sélectionne le service `assistant-gazelle-v5-api`
3. Clique "Manual Deploy" → "Deploy latest commit"

---

### 2️⃣ Attendre le Redéploiement

Le redéploiement prend ~2-3 minutes.

**Vérifier que le service est UP:**
```bash
curl -s https://assistant-gazelle-v5-api.onrender.com/ | grep -o "humidity-alerts"
```

**Résultat attendu:** `humidity-alerts`

---

### 3️⃣ Déclencher le Scan

Une fois le service redéployé, appelle l'endpoint:

```bash
curl -X POST "https://assistant-gazelle-v5-api.onrender.com/api/humidity-alerts/scan"
```

**Paramètre optionnel** (scanner plus de jours):
```bash
curl -X POST "https://assistant-gazelle-v5-api.onrender.com/api/humidity-alerts/scan?days_back=14"
```

---

### 4️⃣ Vérifier les Résultats

**A) Réponse du Scan:**
```json
{
  "status": "success",
  "scanned": 1577,
  "alerts_found": 5,
  "new_alerts": 3,
  "errors": 0,
  "execution_time_seconds": 2.5,
  "days_back": 7
}
```

**B) Vérifier les Alertes Créées:**
```bash
curl -s "https://assistant-gazelle-v5-api.onrender.com/api/humidity-alerts/institutional" | python3 -m json.tool
```

**Résultat attendu:**
```json
{
  "alerts": [
    {
      "alert_type": "housse",
      "client_name": "Vincent d'Indy",
      "piano_make": "Steinway",
      "description": "Housse enlevée détectée",
      "is_resolved": false,
      "observed_at": "2026-01-10T14:30:00Z"
    }
  ],
  "stats": {
    "total": 5,
    "unresolved": 3,
    "resolved": 2
  }
}
```

**C) Rafraîchir le Frontend:**

Ouvre l'application web et va sur "Tableau de bord".

Les alertes devraient maintenant apparaître dans la section "Alertes Maintenance Institutionnelle".

---

## 🔍 TROUBLESHOOTING

### Erreur 404 "Not Found"

**Cause:** Le service n'a pas encore redéployé avec le nouveau code.

**Solution:** Attendre 2-3 minutes et réessayer.

---

### Erreur 500 "Erreur lors du scan"

**Cause possible 1:** Token OAuth Gazelle manquant

**Vérification:**
```bash
# Dans Render → Environment Variables
# Vérifier que ces variables existent:
SUPABASE_URL=https://beblgzvmjqkcillmcavk.supabase.co
SUPABASE_KEY=eyJ...
GAZELLE_CLIENT_ID=xxx
GAZELLE_CLIENT_SECRET=xxx
```

**Cause possible 2:** Le module `humidity_scanner_safe.py` a une erreur

**Solution:** Vérifier les logs Render pour voir l'erreur exacte.

---

### Scan Réussit mais Aucune Alerte Détectée

**Cause:** Aucune entrée dans les 7 derniers jours ne contient les mots-clés d'alerte.

**Vérification manuelle (Supabase SQL Editor):**
```sql
SELECT COUNT(*)
FROM gazelle_timeline_entries
WHERE
    occurred_at >= NOW() - INTERVAL '7 days'
    AND (
        lower(description) LIKE '%housse%'
        OR lower(description) LIKE '%débranché%'
        OR lower(description) LIKE '%rallonge%'
        OR lower(title) LIKE '%housse%'
    );
```

**Si résultat = 0:** Aucune alerte dans la période (c'est normal!)

**Si résultat > 0:** Le scanner a raté certains mots-clés. Vérifier la config dans `config/alerts/config.json`.

---

## 📊 CE QUE FAIT LE SCAN

### Étapes du Scanner

1. **Connexion à Supabase** ✅
2. **Récupération des timeline entries** (7 derniers jours)
3. **Scan des mots-clés:**
   - 🛡️ Housse: "housse enlevée", "sans housse"
   - ⚡ Alimentation: "débranché", "rallonge"
   - 💧 Réservoir: "réservoir vide", "tank empty"
   - 🌡️ Environnement: "fenêtre ouverte", "température basse"
4. **Création des alertes** dans `humidity_alerts`
5. **Déduplication:** Si l'alerte existe déjà (même timeline_entry_id), skip

### Clients Institutionnels Surveillés

- 🏛️ Vincent d'Indy (cli_9UMLkteep8EsISbG)
- 🏛️ Place des Arts (cli_a8lkjsdf9sdfkljs)
- 🏛️ Orford (cli_orford123456789)

---

## ⏰ SCAN AUTOMATIQUE

Le scan est aussi planifié pour tourner automatiquement **tous les jours à 16:00** via le scheduler.

**Vérifier si le scheduler tourne:**

Dans les logs Render, chercher:
```
"✅ [Humidity Alerts] Scheduler démarré"
"📅 Job configuré: humidity_alerts_daily_scan à 16:00"
```

**Si absent:** Le scheduler ne démarre pas. Vérifier `api/main.py` pour s'assurer qu'il importe et démarre le module humidity_alerts.

---

## 🎓 DIFFÉRENCE SCAN MANUEL vs AUTOMATIQUE

| Aspect | Scan Manuel (POST /scan) | Scan Automatique (16:00) |
|--------|--------------------------|--------------------------|
| **Déclenchement** | À la demande (curl) | Automatique (scheduler) |
| **Quand l'utiliser** | Test, debug, forcer maintenant | Production normale |
| **Période** | Paramétrable (days_back) | 7 jours fixe |
| **Logs** | Réponse JSON immédiate | Dans logs Render |

---

## ✅ CHECKLIST FINALE

### Avant Déploiement
- [x] ✅ Code ajouté dans `api/humidity_alerts_routes.py`
- [ ] ⏳ Commiter et pusher le code
- [ ] ⏳ Vérifier auto-deploy activé sur Render

### Après Déploiement
- [ ] ⏳ Attendre redéploiement (2-3 min)
- [ ] ⏳ Tester `POST /api/humidity-alerts/scan`
- [ ] ⏳ Vérifier `GET /api/humidity-alerts/institutional`
- [ ] ⏳ Rafraîchir frontend et voir les alertes

### Validation
- [ ] ⏳ Alertes apparaissent dans le tableau de bord
- [ ] ⏳ Compteur "Alertes Maintenance Institutionnelle" > 0
- [ ] ⏳ Possibilité d'agrandir et voir le détail

---

## 🚀 COMMANDES RAPIDES

### Déployer et Tester (Tout-en-Un)

```bash
# 1. Commiter et pusher
git add api/humidity_alerts_routes.py
git commit -m "feat: Ajouter endpoint scan manuel alertes humidité"
git push origin main

# 2. Attendre 3 minutes pour le redéploiement
echo "⏳ Attente redéploiement..." && sleep 180

# 3. Tester le scan
curl -X POST "https://assistant-gazelle-v5-api.onrender.com/api/humidity-alerts/scan"

# 4. Vérifier les résultats
curl -s "https://assistant-gazelle-v5-api.onrender.com/api/humidity-alerts/institutional" | python3 -m json.tool

echo "✅ Scan terminé ! Rafraîchis le frontend (F5) pour voir les alertes."
```

---

**Document créé le:** 2026-01-12 08:50
**Par:** Assistant Claude Code
**Statut:** ✅ PRÊT À DÉPLOYER
