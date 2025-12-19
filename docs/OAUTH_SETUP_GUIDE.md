# Guide: Configuration OAuth2 Gazelle

## Problème actuel

Les rapports Gazelle sont vides car le "handshake" OAuth2 n'est pas complet. Le backend reçoit le `code` temporaire mais ne l'échange pas contre les tokens `access_token` et `refresh_token`.

## Solution implémentée

Le flow OAuth2 Authorization Code a été complété:

1. **Échange du code** → Le callback `/gazelle_oauth_callback` échange maintenant le code contre les tokens
2. **Stockage cloud** → Les tokens sont sauvegardés dans Supabase `system_settings` (persistant)
3. **Auto-refresh** → Le `refresh_token` permet de rester connecté indéfiniment

## Étapes de configuration

### 1. Créer la table `system_settings` sur Supabase

1. Aller sur [Supabase Dashboard](https://supabase.com/dashboard)
2. Sélectionner votre projet
3. Aller dans **SQL Editor**
4. Copier-coller le contenu de `docs/SUPABASE_SYSTEM_SETTINGS.sql`
5. Cliquer **Run**

### 2. Déclencher le flow OAuth

Une fois la table créée, vous devez déclencher le flow OAuth une première fois:

1. Aller sur: https://gazelleapp.io/developer/oauth/authorize?client_id=MZ8EpbZ79YtuhlJE8v0G__5qAvJoMLWOY0sSHX-xakA&response_type=code&redirect_uri=https://assistant-gazelle-v5-api.onrender.com/gazelle_oauth_callback

2. Vous serez redirigé vers Gazelle pour autoriser l'application

3. Après autorisation, Gazelle vous redirigera vers le callback qui:
   - Échange le code contre les tokens
   - Sauvegarde les tokens dans Supabase
   - Affiche un message de succès

### 3. Vérifier que le token est sauvegardé

Dans Supabase, aller dans **Table Editor** → `system_settings`:

Vous devriez voir une entrée:
- `key`: `gazelle_oauth_token`
- `value`: JSON avec `access_token`, `refresh_token`, `expires_in`

### 4. Test

Une fois le token sauvegardé, testez l'API:

```bash
curl https://assistant-gazelle-v5-api.onrender.com/gazelle/check-appointments
```

Vous devriez maintenant voir des rendez-vous au lieu d'une erreur.

## Avantages

✅ **Données réelles** - Les rapports se rempliront avec les vraies données Gazelle
✅ **Timeline access** - Accès complet aux événements timeline et notes
✅ **Automatisation** - Le `refresh_token` maintient la connexion active
✅ **Cloud storage** - Fonctionne sur Render (filesystem éphémère)

## Dépannage

**Erreur "Table not found"**:
→ Vous n'avez pas créé la table `system_settings`. Suivre l'étape 1.

**Erreur "GAZELLE_CLIENT_ID manquant"**:
→ Vérifier que les variables d'environnement sont configurées sur Render.

**Token expiré**:
→ Refaire l'étape 2 pour générer un nouveau token.

## Fichiers modifiés

- `core/supabase_storage.py` - Ajout méthodes `save_system_setting` / `get_system_setting`
- `api/main.py` - Callback OAuth sauvegarde dans Supabase
- `docs/SUPABASE_SYSTEM_SETTINGS.sql` - Script SQL création table
