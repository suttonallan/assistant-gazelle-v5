# Fix: Erreur GitHub Actions - Scan Humidité

## 🐛 Problème Détecté

### Erreur dans Workflow

```
ValueError: SUPABASE_URL et SUPABASE_KEY (ou SUPABASE_SERVICE_ROLE_KEY) requis.
Ajoutez-les dans les variables d'environnement.
```

**Workflow affecté**: `.github/workflows/humidity_alerts_scanner.yml`

---

## 🔍 Cause Racine

Le workflow GitHub Actions `humidity_alerts_scanner.yml` nécessite 3 secrets configurés:

1. `SUPABASE_URL`
2. `SUPABASE_SERVICE_ROLE_KEY`
3. `OPENAI_API_KEY`

**Problème**: Ces secrets n'étaient pas injectés dans le repository GitHub.

---

## ✅ Solution

### Option 1: Script Automatique (Recommandé)

Utilise le script de configuration automatique:

```bash
cd /Users/allansutton/Documents/assistant-gazelle-v5
bash scripts/setup_github_secrets.sh
```

**Ce script injecte automatiquement:**
- ✅ `SUPABASE_URL`
- ✅ `SUPABASE_SERVICE_ROLE_KEY`
- ✅ `GAZELLE_CLIENT_ID`
- ✅ `GAZELLE_CLIENT_SECRET`
- ✅ `OPENAI_API_KEY` (depuis `.env`)

**Prérequis:**
1. GitHub CLI installé: `brew install gh`
2. Authentifié: `gh auth login`
3. Fichier `.env` avec `OPENAI_API_KEY=sk-...`

---

### Option 2: Configuration Manuelle

Si tu préfères configurer manuellement via l'interface GitHub:

1. **Va sur GitHub:**
   - https://github.com/allansutton/assistant-gazelle-v5/settings/secrets/actions

2. **Ajoute ces secrets:**

| Secret Name | Valeur |
|-------------|--------|
| `SUPABASE_URL` | `https://beblgzvmjqkcillmcavk.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | `eyJhbGc...` (voir `.env`) |
| `OPENAI_API_KEY` | `sk-...` (voir `.env`) |

3. **Clique "Add secret"** pour chaque entrée

---

## 🧪 Vérification

### 1. Vérifier les secrets configurés

```bash
gh secret list
```

**Résultat attendu:**
```
GAZELLE_CLIENT_ID           Updated 2026-01-09
GAZELLE_CLIENT_SECRET       Updated 2026-01-09
OPENAI_API_KEY              Updated 2026-01-09
SUPABASE_SERVICE_ROLE_KEY   Updated 2026-01-09
SUPABASE_URL                Updated 2026-01-09
```

### 2. Tester le workflow manuellement

1. **Va sur GitHub Actions:**
   - https://github.com/allansutton/assistant-gazelle-v5/actions/workflows/humidity_alerts_scanner.yml

2. **Clique "Run workflow"**

3. **Vérifie les logs:**
   ```
   🌡️ SCAN ALERTES HUMIDITÉ
   ======================================================================
   🔧 Initialisation SupabaseStorage...
   ✅ SupabaseStorage initialisé

   📊 RÉSULTATS:
     Scannées: 200
     Skipped: 180
     Alertes: 3
     Notifications: 1
     Erreurs: 0

   ✅ Scan terminé avec succès!
   ```

---

## 📊 Modifications Effectuées

### 1. Workflow: `humidity_alerts_scanner.yml`

**Ligne 35:** Correction du nom du secret

**AVANT (❌):**
```yaml
env:
  SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
```

**APRÈS (✅):**
```yaml
env:
  SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}
```

**Raison:** Le code backend utilise `SUPABASE_SERVICE_ROLE_KEY`, pas `SUPABASE_KEY`.

---

### 2. Script: `setup_github_secrets.sh`

**Ajout de OPENAI_API_KEY:**

```bash
# Secret 5: OPENAI_API_KEY (pour alertes humidité)
echo "5/5 - Injection de OPENAI_API_KEY..."
if [ -f .env ]; then
    OPENAI_KEY=$(grep "^OPENAI_API_KEY=" .env | cut -d '=' -f2-)
    if [ -n "$OPENAI_KEY" ]; then
        echo "$OPENAI_KEY" | gh secret set OPENAI_API_KEY
        echo "✅ OPENAI_API_KEY injecté depuis .env"
    fi
fi
```

**Impact:** Le workflow `humidity_alerts_scanner.yml` peut maintenant appeler l'API OpenAI pour analyser les descriptions de services et détecter les mentions d'humidité.

---

## 🎯 Workflow Humidité

### Fonctionnement

Le workflow `humidity_alerts_scanner.yml` s'exécute **1 fois par jour**:
- 9h AM (Montreal) = 14h UTC

**Action:** Scanne les 200 dernières entrées de la timeline Gazelle pour détecter les mentions d'humidité.

**Si détecté:**
1. Crée une alerte dans `humidity_alerts`
2. Envoie une notification (si configuré)
3. Marque l'entrée comme traitée

---

## 🔄 Prochaines Étapes

1. ✅ **Workflow corrigé** (SUPABASE_KEY → SUPABASE_SERVICE_ROLE_KEY)
2. ⏳ **Exécuter le script** pour injecter les secrets:
   ```bash
   bash scripts/setup_github_secrets.sh
   ```
3. ⏳ **Tester manuellement** le workflow sur GitHub Actions
4. ⏳ **Vérifier les logs** pour confirmer le succès

---

## 📚 Références

- **Workflow**: [.github/workflows/humidity_alerts_scanner.yml](../.github/workflows/humidity_alerts_scanner.yml)
- **Script config**: [scripts/setup_github_secrets.sh](../scripts/setup_github_secrets.sh)
- **Module scan**: [modules/alerts/humidity_scanner.py](../modules/alerts/humidity_scanner.py)
- **GitHub Secrets**: https://github.com/allansutton/assistant-gazelle-v5/settings/secrets/actions

---

## ✅ Résumé

| Problème | Solution | Status |
|----------|----------|--------|
| Secret `SUPABASE_KEY` manquant | Changé en `SUPABASE_SERVICE_ROLE_KEY` | ✅ Corrigé |
| Secret `OPENAI_API_KEY` manquant | Ajouté au script de config | ✅ Corrigé |
| Workflow échoue au démarrage | Injecter les secrets avec script | ⏳ À faire |

**Prochaine action:** Exécute `bash scripts/setup_github_secrets.sh` pour finaliser la configuration.
