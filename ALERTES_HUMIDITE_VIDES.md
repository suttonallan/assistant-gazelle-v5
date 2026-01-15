# 🚨 DIAGNOSTIC: Tableau Alertes Humidité Vide

**Date:** 2026-01-12 08:45
**Problème:** Le tableau d'alertes d'humidité est vide malgré la sync

---

## 🔍 DIAGNOSTIC COMPLET

### ✅ CE QUI FONCTIONNE

1. **API Backend Render:** ✅ Opérationnelle
   - URL: https://assistant-gazelle-v5-api.onrender.com
   - Module humidity-alerts: ✅ Présent

2. **Base de Données:** ✅ Connectée
   - Table `humidity_alerts`: ✅ Existe
   - Vue `humidity_alerts_active`: ✅ Existe

3. **Dernière Sync Gazelle:** ✅ Exécutée
   - Date: 2026-01-12 03:55 (ce matin)
   - Items: 12,045 (ancienne méthode complète)
   - Timeline entries: 1,577 synchronisées

### ❌ CE QUI NE FONCTIONNE PAS

1. **Table humidity_alerts vide:** 0 alertes
   - Test API: `GET /api/humidity-alerts/institutional` → `[]`
   - Test API: `GET /api/alertes/maintenance` → `[]`

2. **Aucun scan d'alertes exécuté:**
   - Le scanner d'humidité n'a jamais tourné
   - Les timeline entries synchronisées n'ont pas été scannées

---

## 🎯 CAUSE RACINE

**Le scanner d'alertes d'humidité est un processus SÉPARÉ de la sync Gazelle.**

### Timeline Sync ≠ Humidity Alerts Scan

```
┌─────────────────────────────────────────┐
│   SYNC GAZELLE (03:55 ce matin)        │
│   ✅ Clients, Contacts, Pianos          │
│   ✅ Timeline Entries (1,577)           │
│   ✅ Appointments                       │
└─────────────────────────────────────────┘
                 │
                 │ Les données sont dans Supabase
                 ▼
┌─────────────────────────────────────────┐
│   SCAN ALERTES HUMIDITÉ                 │
│   ❌ JAMAIS EXÉCUTÉ                     │
│   (devrait tourner à 16:00)             │
│                                         │
│   Lit: gazelle_timeline_entries        │
│   Écrit: humidity_alerts               │
└─────────────────────────────────────────┘
```

---

## 💡 SOLUTIONS POSSIBLES

### Solution 1: Attendre le Prochain Scan Automatique (16:00)

Si le scheduler est configuré correctement sur Render, il devrait scanner à 16:00 aujourd'hui.

**Vérification à 16:05:**
```bash
curl -s "https://assistant-gazelle-v5-api.onrender.com/api/humidity-alerts/institutional" | python3 -m json.tool
```

Si toujours vide → Le scheduler ne tourne pas sur Render.

---

### Solution 2: Ajouter un Endpoint de Scan Manuel (RECOMMANDÉ)

Ajouter un endpoint POST `/api/humidity-alerts/scan` qui déclenche le scan manuellement.

**Fichier à modifier:** `api/humidity_alerts_routes.py`

**Code à ajouter:**
```python
@router.post("/scan", response_model=Dict[str, Any])
async def trigger_manual_scan(days_back: int = 7):
    """
    Déclenche un scan manuel des alertes d'humidité.

    Args:
        days_back: Nombre de jours à scanner (défaut: 7)

    Returns:
        {
            "status": "success",
            "scanned": 1577,
            "alerts_found": 5,
            "new_alerts": 3,
            "errors": 0
        }
    """
    try:
        from modules.alerts.humidity_scanner_safe import HumidityScannerSafe

        scanner = HumidityScannerSafe()
        result = scanner.scan_new_entries(days_back=days_back)

        return {
            "status": "success",
            **result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur scan: {str(e)}")
```

**Puis appeler:**
```bash
curl -X POST "https://assistant-gazelle-v5-api.onrender.com/api/humidity-alerts/scan"
```

---

### Solution 3: Exécuter le Script Directement sur Render

Se connecter au shell Render et exécuter:
```bash
python3 scripts/cleanup_and_rescan_alerts.py
```

Ou:
```bash
python3 modules/alerts/humidity_scanner_safe.py
```

---

### Solution 4: Vérifier si le Scheduler Tourne sur Render

**Dans les logs Render, chercher:**
```
"Scheduler started"
"humidity_alerts_daily_scan"
"Scanner automatique d'alertes humidité"
```

**Si absent → Le scheduler n'est pas démarré au démarrage de l'app.**

**Fix:** Ajouter dans `api/main.py`:
```python
from core.scheduler import start_scheduler

@app.on_event("startup")
async def startup_event():
    # Démarrer le scheduler
    start_scheduler()
    print("✅ Scheduler démarré")
```

---

## 🧪 TESTS À FAIRE MAINTENANT

### Test 1: Vérifier si les Timeline Entries sont bien là

```bash
# Via l'API locale (si tu as les env vars)
python3 -c "
from core.supabase_storage import SupabaseStorage
storage = SupabaseStorage()
response = storage.client.table('gazelle_timeline_entries').select('*', count='exact').execute()
print(f'Timeline entries in DB: {response.count}')
"
```

**Attendu:** ~1,577 ou plus

---

### Test 2: Chercher manuellement des mots-clés

```bash
# Via Supabase SQL Editor
SELECT COUNT(*)
FROM gazelle_timeline_entries
WHERE
    lower(description) LIKE '%housse%'
    OR lower(description) LIKE '%débranché%'
    OR lower(description) LIKE '%rallonge%'
    OR lower(title) LIKE '%housse%';
```

**Si > 0:** Il y a des alertes potentielles à détecter !

---

### Test 3: Vérifier les Logs Render

Dans le dashboard Render:
1. Va sur le service `assistant-gazelle-v5-api`
2. Onglet "Logs"
3. Cherche: `humidity`, `scanner`, `alert`, `16:00`

**Résultats possibles:**
- ✅ "Scanner d'alertes exécuté" → Il tourne mais n'a rien trouvé
- ❌ Aucune mention → Le scanner ne tourne jamais
- ⚠️ "Erreur" → Le scanner crash

---

## 📋 PLAN D'ACTION RECOMMANDÉ

### MAINTENANT (Local)

1. ✅ Lire ce document
2. ✅ Identifier la cause (scheduler ou endpoint manquant)

### OPTION A: Si Scheduler Manquant

1. Ajouter l'endpoint de scan manuel (Solution 2)
2. Déployer sur Render
3. Appeler `POST /api/humidity-alerts/scan`

### OPTION B: Si Scheduler Existe mais ne Tourne Pas

1. Vérifier `api/main.py` pour `start_scheduler()`
2. Si manquant, ajouter et redéployer
3. Attendre 16:00 ou redémarrer le service Render

### OPTION C: Si Scheduler Tourne mais Crash

1. Lire les logs Render pour voir l'erreur
2. Fixer l'erreur (probablement token OAuth manquant)
3. Redéployer

---

## 🎯 QUICKFIX - ENDPOINT DE SCAN

Voici le code complet à ajouter dans `api/humidity_alerts_routes.py`:

```python
@router.post("/scan")
async def trigger_manual_scan(days_back: int = 7) -> Dict[str, Any]:
    """
    Déclenche un scan manuel des alertes d'humidité.

    Ce endpoint permet de forcer un scan sans attendre le scheduler.

    Args:
        days_back: Nombre de jours à scanner (défaut: 7)

    Returns:
        {
            "status": "success",
            "scanned": 1577,
            "alerts_found": 5,
            "new_alerts": 3,
            "errors": 0,
            "execution_time_seconds": 2.5
        }
    """
    try:
        from modules.alerts.humidity_scanner_safe import HumidityScannerSafe
        import time

        start_time = time.time()

        scanner = HumidityScannerSafe()
        result = scanner.scan_new_entries(days_back=days_back)

        execution_time = time.time() - start_time

        return {
            "status": "success",
            "scanned": result.get('scanned', 0),
            "alerts_found": result.get('alerts_found', 0),
            "new_alerts": result.get('new_alerts', 0),
            "errors": result.get('errors', 0),
            "execution_time_seconds": round(execution_time, 2)
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du scan: {str(e)}"
        )
```

**Une fois ajouté et déployé:**
```bash
curl -X POST "https://assistant-gazelle-v5-api.onrender.com/api/humidity-alerts/scan"
```

---

## 📊 RÉSUMÉ

| Composant | État | Action |
|-----------|------|--------|
| API Backend | ✅ OK | Aucune |
| Table humidity_alerts | ✅ Existe | Aucune |
| Timeline entries | ✅ Synchronisées (1,577) | Aucune |
| **Scanner d'alertes** | ❌ **Jamais exécuté** | **Ajouter endpoint scan** |
| Scheduler 16:00 | ❓ Inconnu | Vérifier logs Render |

---

**Action immédiate recommandée:** Ajouter l'endpoint `/scan` pour pouvoir forcer un scan manuellement.

---

**Document créé le:** 2026-01-12 08:45
**Par:** Assistant Claude Code
**Statut:** ⚠️ DIAGNOSTIC COMPLET - ACTION REQUISE
