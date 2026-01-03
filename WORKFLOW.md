# Workflow de développement et déploiement

## Principe : Déploiement automatique continu

✅ **Oui, c'est possible !** Render déploie automatiquement à chaque push sur GitHub.

## Comment ça fonctionne

### 1. Développement local
```bash
# Tu travailles sur ton Mac
cd ~/Documents/assistant-gazelle-v5

# Tu modifies le code
# Tu testes localement
python api/main.py  # ou tes scripts
```

### 2. Commit et push
```bash
# Tu sauvegardes tes changements
git add .
git commit -m "Amélioration de la fonctionnalité X"
git push origin main
```

### 3. Déploiement automatique
- **Render détecte automatiquement** le push sur GitHub
- **Build automatique** : installe les dépendances
- **Déploiement** : remplace l'ancienne version par la nouvelle
- **Temps** : 2-3 minutes généralement

### 4. Résultat
- ✅ **Nouvelle version en ligne** automatiquement
- ✅ **Ancienne version reste active** pendant le déploiement (pas d'interruption)
- ✅ **Rollback automatique** si le déploiement échoue

## Workflow recommandé

### Branche `main` = Production (toujours en ligne)

```
┌─────────────────────────────────────────┐
│  Tu travailles localement               │
│  - Modifie le code                      │
│  - Teste sur ton Mac                    │
└──────────────┬──────────────────────────┘
               │
               │ git push origin main
               ▼
┌─────────────────────────────────────────┐
│  GitHub reçoit le push                   │
│  - Commit visible sur GitHub            │
└──────────────┬──────────────────────────┘
               │
               │ Render détecte automatiquement
               ▼
┌─────────────────────────────────────────┐
│  Render déploie                         │
│  - Build (2-3 min)                      │
│  - Déploiement (ancienne version reste │
│    active pendant le build)             │
│  - Nouvelle version remplace l'ancienne │
└──────────────┬──────────────────────────┘
               │
               ▼
        ✅ Nouvelle version en ligne !
        Tes utilisateurs voient les changements
```

## Bonnes pratiques

### 1. Toujours tester localement avant de pousser
```bash
# Teste ton API localement
uvicorn api.main:app --reload

# Vérifie que tout fonctionne
curl http://localhost:8000/health
```

### 2. Messages de commit clairs
```bash
git commit -m "Ajout: Module humidity-alerts avec notifications"
git commit -m "Fix: Correction du bug de synchronisation"
git commit -m "Amélioration: Performance de l'API clients"
```

### 3. Vérifier le déploiement
- Va sur ton dashboard Render après un push
- Tu verras le statut du déploiement en temps réel
- Si ça échoue, Render garde l'ancienne version active

## Gestion des erreurs

### Si le déploiement échoue
- ✅ L'ancienne version reste active (pas d'interruption)
- ✅ Render te montre l'erreur dans les logs
- ✅ Tu corriges et tu pushes à nouveau

### Rollback manuel (si nécessaire)
Dans Render :
1. Va dans **Deploys**
2. Clique sur un ancien déploiement qui fonctionnait
3. **Rollback to this deploy**

## Avantages de cette approche

✅ **Version toujours en ligne** : L'ancienne version reste active pendant le déploiement
✅ **Déploiement automatique** : Pas besoin de cliquer sur des boutons
✅ **Pas d'interruption** : Transition transparente
✅ **Simple** : Juste `git push` et c'est déployé
✅ **Sécurisé** : Si ça échoue, l'ancienne version reste active

## Exemple concret

```bash
# Lundi matin - Tu améliores l'API
vim api/main.py  # Tu ajoutes une nouvelle route
git add api/main.py
git commit -m "Ajout: Route /api/clients pour lister les clients"
git push origin main

# 2-3 minutes plus tard
# ✅ Nouvelle version en ligne avec la route /api/clients
# ✅ Tes utilisateurs peuvent l'utiliser immédiatement

# Mardi - Tu corriges un bug
vim core/sync.py  # Tu corriges un bug
git add core/sync.py
git commit -m "Fix: Correction du bug de synchronisation"
git push origin main

# 2-3 minutes plus tard
# ✅ Nouvelle version en ligne avec le bug corrigé
# ✅ Pas d'interruption pour tes utilisateurs
```

## Monitoring

Tu peux voir l'historique des déploiements dans Render :
- **Deploys** : Liste de tous les déploiements
- **Logs** : Logs en temps réel de ton API
- **Metrics** : Performance, requêtes, etc.








