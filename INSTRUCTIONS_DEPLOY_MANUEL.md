# 🚀 Déploiement Manuel - MÉTHODE SIMPLE

## Fichiers buildés prêts!

Les fichiers sont dans: `/Users/allansutton/Documents/assistant-gazelle-v5/frontend/dist/`

## Option 1: Upload via GitHub Web (PLUS SIMPLE)

1. **Ouvrir GitHub dans votre navigateur:**
   https://github.com/suttonallan/assistant-gazelle-v5

2. **Aller dans l'onglet "Actions"**

3. **Trouver le workflow "Deploy Frontend to GitHub Pages"**

4. **Cliquer sur "Run workflow"** (bouton en haut à droite)

5. Attendre 2-3 minutes

✅ **C'EST TOUT!** Le site sera mis à jour automatiquement.

---

## Option 2: Depuis votre Terminal Mac

Ouvrez **Terminal** (l'app native Mac, pas VS Code) et tapez:

```bash
cd /Users/allansutton/Documents/assistant-gazelle-v5
git push origin main
```

Si ça demande username/password:
- **Username:** suttonallan
- **Password:** [Votre Personal Access Token GitHub]

Pas de token? Créez-en un ici:
https://github.com/settings/tokens
(Cochez juste la case "repo")

---

## Option 3: Via GitHub Desktop (SI INSTALLÉ)

1. Ouvrir GitHub Desktop
2. Sélectionner le repo "assistant-gazelle-v5"
3. Cliquer "Push origin"

---

## Vérifier le déploiement

Une fois pushé, allez voir:
- **Actions:** https://github.com/suttonallan/assistant-gazelle-v5/actions
- **Site live:** https://suttonallan.github.io/assistant-gazelle-v5/

Le déploiement prend **2-3 minutes**.
