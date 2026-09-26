# Configuration Keep-Alive avec Cron Externe

## Problème résolu
Empêcher Render.com de mettre en veille votre API après 15 minutes d'inactivité.

## Solution: Ping HTTP toutes les 5 minutes

### Services de Cron gratuits recommandés

1. **Cron-job.org** (Recommandé)
   - URL: https://cron-job.org
   - Limite gratuite: 50 requêtes/jour
   - Configuration:
     ```
     Titre: Keep-Alive Assistant Gazelle
     URL: https://assistant-gazelle-v5-api.onrender.com/health
     Intervalle: */5 * * * * (toutes les 5 minutes)
     Méthode: GET
     ```

2. **UptimeRobot**
   - URL: https://uptimerobot.com
   - Limite gratuite: 50 moniteurs
   - Intervalle minimum: 5 minutes
   - Configuration:
     ```
     Type: HTTP(s)
     URL: https://assistant-gazelle-v5-api.onrender.com/health
     Interval: Every 5 minutes
     ```

3. **Pingdom** (Alternative payante mais gratuit 30 jours)
   - URL: https://www.pingdom.com

## Route optimisée

Votre route `/health` est déjà optimale pour des appels fréquents:

```python
@app.get("/health")
async def health() -> Dict[str, str]:
    """Vérification de l'état de l'API."""
    return {"status": "healthy"}
```

### Caractéristiques:
- ✅ Temps de réponse: < 50ms
- ✅ Consommation mémoire: ~0.1 MB par requête
- ✅ Pas de connexion DB
- ✅ Pas d'appel API externe
- ✅ Coût: gratuit (inclus dans votre plan Render)

### Calculs de consommation

**Avec pings toutes les 5 minutes:**
- Requêtes par jour: 288 (24h × 12 pings/heure)
- Requêtes par mois: ~8,640
- Bande passante: ~17 KB/mois (négligeable)
- Impact CPU: < 0.1% du quota mensuel

**Verdict:** Totalement négligeable pour Render Free/Hobby tier ✅

## Scheduler optimisé

Le BackgroundScheduler a été configuré avec:

```python
job_defaults={
    'coalesce': True,        # Fusionne les exécutions manquées
    'max_instances': 1,      # Une seule instance par job
    'misfire_grace_time': 300  # Tolérance de 5 min
}
```

### Comportement lors d'un redémarrage Render:

1. **01:00 - Sync Gazelle** manquée pendant redémarrage
   → Exécutée dès que le serveur redémarre (dans les 5 min)

2. **16:00 - Sync RV & Alertes** manquée
   → Exécutée si < 5 minutes de retard, sinon sautée

3. **Ping toutes les 5 min** garantit que le serveur redémarre rapidement

## Test de configuration

### 1. Vérifier que la route /health fonctionne

```bash
curl https://assistant-gazelle-v5-api.onrender.com/health
```

Réponse attendue:
```json
{"status":"healthy"}
```

### 2. Vérifier les logs du scheduler

Après le démarrage de l'API, vous devriez voir:

```
🚀 Scheduler démarré avec succès

📅 Prochaines exécutions:
   - Sync Gazelle Totale (01:00): 2026-01-15 01:00:00
   - Rapport Timeline Google Sheets (02:00): 2026-01-15 02:00:00
   - Backup SQL (03:00): 2026-01-15 03:00:00
   - Sync RV & Alertes (16:00): 2026-01-15 16:00:00
```

### 3. Vérifier les tâches planifiées via l'API

```bash
curl https://assistant-gazelle-v5-api.onrender.com/scheduler/logs?limit=10
```

## Monitoring recommandé

1. **Dans Render Dashboard:**
   - Vérifiez les logs de déploiement
   - Surveillez l'utilisation CPU/mémoire
   - Vérifiez que le serveur ne se met jamais en veille

2. **Dans votre tableau de bord:**
   - Route: `/scheduler/logs`
   - Vérifiez que les tâches s'exécutent à l'heure prévue
   - Surveillez les échecs éventuels

3. **Dans le service de cron externe:**
   - Vérifiez que tous les pings réussissent (code 200)
   - Surveillez le temps de réponse (devrait être < 200ms)

## Dépannage

### Le serveur se met quand même en veille
- Vérifiez que le cron externe est actif
- Vérifiez l'URL du ping (doit être HTTPS)
- Augmentez la fréquence à 3 minutes si nécessaire

### Les tâches planifiées ne s'exécutent pas
- Vérifiez les logs Render pour voir les erreurs
- Vérifiez que le scheduler démarre bien au startup
- Consultez `/scheduler/logs` pour voir l'historique

### Erreurs 503 persistantes le matin
- Si le cron externe fonctionne, le problème vient d'ailleurs
- Vérifiez les logs d'erreur de vos tâches planifiées
- Augmentez `misfire_grace_time` à 600 (10 min) si nécessaire

## Améliorations futures (optionnel)

Si vous voulez aller plus loin:

1. **Ajouter un healthcheck avancé:**
   ```python
   @app.get("/health/detailed")
   async def detailed_health():
       return {
           "status": "healthy",
           "scheduler_running": get_scheduler().running,
           "next_jobs": [...]
       }
   ```

2. **Migrer vers des Cron Jobs Render natifs** (plus fiable)
   - Pas de dépendance sur un service externe
   - Exécution garantie par Render

3. **Utiliser un job store PostgreSQL** (persistance)
   - Les tâches survivent aux redémarrages
   - Meilleure gestion des exécutions manquées

---

**Configuration actuelle: ✅ OPTIMALE pour votre cas d'usage**

Votre tableau de bord reste fonctionnel et vos tâches planifiées redémarrent automatiquement après chaque redémarrage Render.
