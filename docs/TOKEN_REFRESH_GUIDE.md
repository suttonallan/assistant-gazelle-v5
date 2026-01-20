# Guide de Renouvellement du Token Gazelle

## 🔄 Système d'Auto-Refresh

Le système gère maintenant **automatiquement** le refresh du token OAuth Gazelle:

✅ **Auto-détection** de l'expiration
✅ **Auto-refresh** lors d'erreurs 401
✅ **Sauvegarde automatique** dans Supabase

## 🆕 Obtenir un Token Initial (si complètement expiré)

Quand le `refresh_token` est expiré (après ~30 jours), il faut obtenir un nouveau token complet:

### Méthode 1: Via l'Interface Web Gazelle (Recommandé)

1. **Se connecter** à https://gazelleapp.io
2. **Ouvrir les Developer Tools** (F12)
3. **Aller dans Network/Réseau**
4. **Rafraîchir la page** ou faire une action
5. **Trouver une requête** vers `gazelleapp.io/graphql/private/`
6. **Copier le token** dans les Headers:
   ```
   Authorization: Bearer VOTRE_TOKEN_ICI
   ```

### Méthode 2: Script Python (si OAuth configuré)

```bash
python3 scripts/get_new_token_manual.py
```

## 💾 Mettre à Jour le Token dans Supabase

### Option A: Via le script auto_refresh (si vous avez le token)

```python
from core.supabase_storage import SupabaseStorage
import time

storage = SupabaseStorage()

token_data = {
    'access_token': 'VOTRE_NOUVEAU_TOKEN',
    'refresh_token': 'VOTRE_REFRESH_TOKEN',  # Si disponible
    'expires_in': 2592000,  # 30 jours en secondes
    'created_at': int(time.time())
}

storage.save_system_setting('gazelle_oauth_token', token_data)
print("✅ Token sauvegardé!")
```

### Option B: Directement dans Supabase UI

1. Aller sur https://beblgzvmjqkcillmcavk.supabase.co
2. Ouvrir la table `system_settings`
3. Trouver la ligne avec `key = 'gazelle_oauth_token'`
4. Mettre à jour le JSON `value`:
   ```json
   {
     "access_token": "NOUVEAU_TOKEN",
     "refresh_token": "NOUVEAU_REFRESH_TOKEN",
     "expires_in": 2592000,
     "created_at": 1737334800
   }
   ```

## 🧪 Tester le Token

```bash
# Vérifier l'état
python3 scripts/auto_refresh_token.py

# Tester l'API
python3 -c "
from core.gazelle_api_client import GazelleAPIClient
client = GazelleAPIClient()
result = client.get_clients(limit=1)
print(f'✅ API fonctionnelle: {len(result)} client')
"
```

## 🔒 Sécurité

- ❌ **NE JAMAIS** committer de tokens dans Git
- ✅ Les tokens sont stockés dans Supabase (sécurisé)
- ✅ Le système auto-refresh évite les expirations

## 📅 Fréquence de Refresh

- **Token expiration**: 30 jours (2592000 secondes)
- **Auto-refresh**: Automatique à chaque erreur 401
- **Script préventif**: `scripts/auto_refresh_token.py` (peut être dans un cron)

## 🚨 En Cas de Problème

Si vous voyez des erreurs 401 persistantes:

```bash
# 1. Vérifier l'état du token
python3 scripts/auto_refresh_token.py

# 2. Forcer un refresh
python3 scripts/auto_refresh_token.py --force

# 3. Si échec, obtenir un nouveau token (voir Méthode 1 ci-dessus)
```

## 🎯 Une Fois Configuré

Le système gère tout automatiquement! Vous n'avez plus à vous soucier des tokens:

✅ `GazelleAPIClient` détecte les 401 et rafraîchit automatiquement
✅ Les scripts de sync fonctionnent sans intervention
✅ Le token est toujours à jour dans Supabase
