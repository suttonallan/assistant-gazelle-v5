# Configuration GitHub Actions pour Sync Timeline Incrémentiel

## 🎯 Objectif

Automatiser la synchronisation incrémentielle du Timeline (50 derniers items) chaque nuit à 2h, même si votre MacBook Air est fermé.

## 📋 Prérequis

1. **Compte GitHub** avec accès au repository
2. **Secrets GitHub** configurés dans Settings → Secrets and variables → Actions

## 🔐 Configuration des Secrets GitHub

Dans votre repository GitHub, allez dans:
**Settings → Secrets and variables → Actions → New repository secret**

Ajoutez les secrets suivants:

```
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
GAZELLE_CLIENT_ID
GAZELLE_CLIENT_SECRET
```

### Comment obtenir les valeurs:

1. **SUPABASE_URL** et **SUPABASE_SERVICE_ROLE_KEY**:
   - Votre fichier `.env` local
   - Ou depuis le dashboard Supabase: Settings → API

2. **GAZELLE_CLIENT_ID** et **GAZELLE_CLIENT_SECRET**:
   - Votre fichier `.env` local
   - Ou depuis le dashboard Gazelle API

⚠️ **Important**: Ne jamais commiter ces valeurs dans le code!

## 🚀 Activation du Workflow

### Étape 1: Pousser le fichier de workflow

Le fichier `.github/workflows/timeline_incremental_sync.yml` doit être dans votre repository:

```bash
git add .github/workflows/timeline_incremental_sync.yml
git commit -m "Ajout workflow GitHub Actions pour sync Timeline incrémentiel"
git push
```

### Étape 2: Vérifier l'activation

1. Allez dans votre repository GitHub
2. Cliquez sur l'onglet **Actions**
3. Le workflow devrait apparaître dans la liste
4. Il s'exécutera automatiquement tous les jours à 2h UTC

## ⏰ Configuration de l'horaire

Le workflow est configuré pour s'exécuter à **2h00 UTC** chaque jour.

**Conversion horaire:**
- **Heure d'hiver (EST)**: 2h UTC = 22h EST (la veille)
- **Heure d'été (EDT)**: 2h UTC = 21h EDT (la veille)

### Modifier l'horaire

Pour changer l'horaire, modifiez la ligne dans `.github/workflows/timeline_incremental_sync.yml`:

```yaml
- cron: '0 2 * * *'  # Format: minute heure jour mois jour-semaine
```

**Exemples:**
- `'0 2 * * *'` = 2h00 UTC chaque jour
- `'0 3 * * *'` = 3h00 UTC chaque jour
- `'30 1 * * *'` = 1h30 UTC chaque jour

## 📊 Vérification des exécutions

1. Allez dans **Actions** sur GitHub
2. Cliquez sur **Timeline Incremental Sync**
3. Vous verrez l'historique de toutes les exécutions
4. Cliquez sur une exécution pour voir les logs détaillés

## 🔧 Exécution manuelle

Vous pouvez aussi exécuter le workflow manuellement:

1. Allez dans **Actions**
2. Cliquez sur **Timeline Incremental Sync**
3. Cliquez sur **Run workflow** (bouton en haut à droite)
4. Cliquez sur **Run workflow** pour confirmer

## 🐛 Dépannage

### Le workflow ne s'exécute pas automatiquement

- Vérifiez que le fichier `.github/workflows/timeline_incremental_sync.yml` est bien commité et poussé
- Vérifiez que les secrets GitHub sont bien configurés
- Vérifiez les logs dans l'onglet **Actions**

### Erreur "Missing secrets"

- Vérifiez que tous les secrets sont configurés dans Settings → Secrets
- Les noms des secrets doivent correspondre exactement (sensible à la casse)

### Erreur d'authentification API

- Vérifiez que les clés API (Gazelle, Supabase) sont valides
- Les secrets peuvent avoir expiré, régénérez-les si nécessaire

## 📝 Notes importantes

1. **Coûts GitHub Actions**: 
   - Les workflows GitHub Actions sont gratuits pour les repositories publics
   - Pour les repositories privés, 2000 minutes/mois sont gratuites
   - Ce workflow prend ~30 secondes à s'exécuter = ~15 minutes/mois

2. **Limite d'items**:
   - Le script importe 50 items par défaut
   - Vous pouvez modifier `--limit` dans le workflow si nécessaire

3. **Doublons**:
   - L'UPSERT garantit qu'aucun doublon n'est créé
   - La clé unique est `external_id` dans Supabase

4. **Tri**:
   - Les items sont automatiquement triés par date de création descendante
   - Les 50 plus récents sont toujours importés

## 🔄 Workflow alternatif: Modifier le script principal

Si vous préférez modifier le script principal au lieu d'utiliser le script de test:

Modifiez `modules/sync_gazelle/sync_to_supabase.py`, ligne 585:

```python
# AVANT:
limit=None

# APRÈS (pour limiter à 50 items):
limit=50
```

Puis modifiez le workflow pour utiliser:

```yaml
run: |
  python3 -c "from modules.sync_gazelle.sync_to_supabase import GazelleToSupabaseSync; syncer = GazelleToSupabaseSync(); syncer.sync_timeline_entries()"
```

