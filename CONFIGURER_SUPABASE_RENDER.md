# 🔧 Configurer Supabase sur Render.com

## Problème
Les modifications faites en local ne se synchronisent pas en ligne parce que Render.com n'a pas les variables d'environnement Supabase configurées.

## Solution : Ajouter les variables d'environnement sur Render

### Étape 1 : Récupérer vos identifiants Supabase

Depuis votre fichier `.env` local :

```bash
grep -E "SUPABASE_URL|SUPABASE_KEY" .env
```

Vous devriez voir :
```
SUPABASE_URL=https://beblgzvmjqkcillmcavk.supabase.co
SUPABASE_KEY=eyJhbG...votre_clé_ici...
```

### Étape 2 : Ajouter les variables sur Render

1. Allez sur [render.com](https://render.com)
2. Cliquez sur votre service **assistant-gazelle-v5-api**
3. Allez dans **Environment** (menu de gauche)
4. Cliquez sur **Add Environment Variable**
5. Ajoutez les deux variables :

   **Variable 1 :**
   - **Key**: `SUPABASE_URL`
   - **Value**: `https://beblgzvmjqkcillmcavk.supabase.co`

   **Variable 2 :**
   - **Key**: `SUPABASE_KEY`
   - **Value**: `eyJhbG... (votre clé complète)`

6. Cliquez sur **Save Changes**

### Étape 3 : Render va automatiquement redéployer

- Render détecte la modification des variables
- Il redémarre automatiquement le service (2-3 minutes)
- ✅ La synchronisation fonctionnera !

### Étape 4 : Vérifier que ça fonctionne

Une fois Render redéployé, lancez depuis votre terminal local :

```bash
source .env
python3 scripts/check_sync.py
```

Vous devriez voir :
```
✅ Local et Production synchronisés (X pianos à faire)
```

## Comment éviter que ça n'arrive plus

1. **Utilisez toujours le script de vérification** avant de travailler :
   ```bash
   source .env && python3 scripts/check_sync.py
   ```

2. **Vérifiez les logs** après une sauvegarde :
   ```bash
   tail -f backend.log  # En local
   ```

3. **Testez toujours en production** après un changement important :
   ```bash
   curl https://assistant-gazelle-v5-api.onrender.com/vincent-dindy/pianos | jq '.pianos | length'
   ```

## Résumé

- ✅ **Local** : Utilise Supabase (configuré dans `.env`)
- ✅ **Production** : Doit aussi utiliser Supabase (configuré sur Render.com)
- ✅ **Les deux partagent la même base de données** → synchronisation automatique !

Une fois configuré, toutes vos modifications (sélections, statuts, etc.) seront instantanément synchronisées entre local et production.
