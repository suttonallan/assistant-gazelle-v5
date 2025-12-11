# 📥 Stratégie d'Import - Contacts et Pianos

## 🎯 Problème

L'API GraphQL Gazelle ne permet pas actuellement d'importer directement les **contacts** et **pianos** via les queries disponibles. Il faut donc une stratégie hybride pour gérer :

1. **Import initial** : Récupérer les données existantes
2. **Imports futurs** : Gérer les nouveaux contacts/pianos qui arrivent avec de nouveaux clients

---

## 🔄 Solution Hybride

### Phase 1 : Import Initial (Maintenant)

**Option A : Depuis SQL Server (Recommandé pour l'import initial)**

Si vous avez accès à la base SQL Server existante, on peut copier les contacts et pianos directement :

```bash
# Dans .env
USE_SQL_SERVER_FOR_INITIAL_IMPORT=true
SQL_SERVER_CONN_STR=DRIVER={ODBC Driver 17 for SQL Server};SERVER=...;DATABASE=...;UID=...;PWD=...
```

Le script `import_gazelle_to_sqlite.py` utilisera automatiquement `import_contacts_pianos_from_sql_server.py` pour copier les données.

**Option B : Depuis l'API GraphQL (Une fois la doc disponible)**

Une fois que vous m'aurez donné le lien vers la doc API Gazelle, je pourrai implémenter les queries GraphQL correctes pour récupérer :
- Les contacts d'un client : `client(id: $clientId) { contacts { ... } }`
- Les pianos d'un client : `client(id: $clientId) { pianos { ... } }`

---

### Phase 2 : Imports Futurs (Après l'import initial)

**Stratégie recommandée :**

1. **Pour les nouveaux clients** : Utiliser l'API GraphQL pour récupérer leurs contacts et pianos lors de l'import quotidien
2. **Pour les clients existants** : 
   - Si un nouveau piano est ajouté dans Gazelle → le récupérer via l'API lors du prochain import
   - Si un nouveau contact est ajouté → le récupérer via l'API lors du prochain import

**Implémentation future :**

```python
def import_new_contacts_and_pianos_from_api(conn, client_ids):
    """
    Importe les contacts et pianos depuis l'API GraphQL.
    À utiliser pour les imports quotidiens après l'import initial.
    """
    # Query pour chaque client :
    # query GetClientDetails($clientId: ID!) {
    #   client(id: $clientId) {
    #     contacts { nodes { id firstName lastName } }
    #     pianos { nodes { id make model serialNumber ... } }
    #   }
    # }
    pass
```

---

## 📋 Plan d'Action

### Étape 1 : Import Initial (Maintenant)

✅ **Option A** : Utiliser SQL Server si disponible
- Activer `USE_SQL_SERVER_FOR_INITIAL_IMPORT=true` dans `.env`
- Configurer `SQL_SERVER_CONN_STR`
- Lancer `import_gazelle_to_sqlite.py`

✅ **Option B** : Attendre la doc API
- Vous me donnez le lien vers la doc API Gazelle
- J'implémente les queries GraphQL correctes
- On relance l'import

### Étape 2 : Imports Quotidiens (Futur)

Une fois la doc API disponible, je créerai :

1. **`import_daily_updates.py`** : Script pour les imports quotidiens
   - Récupère les nouveaux clients
   - Pour chaque nouveau client, récupère ses contacts et pianos via l'API
   - Met à jour SQLite

2. **Fonction dans `import_gazelle_to_sqlite.py`** :
   - `import_contacts_from_api(client_ids)` : Récupère contacts via GraphQL
   - `import_pianos_from_api(client_ids)` : Récupère pianos via GraphQL

---

## 🔧 Configuration

### Variables d'environnement (`.env`)

```bash
# Pour l'import initial depuis SQL Server
USE_SQL_SERVER_FOR_INITIAL_IMPORT=true
SQL_SERVER_CONN_STR=DRIVER={ODBC Driver 17 for SQL Server};SERVER=...;DATABASE=...;UID=...;PWD=...

# Pour l'API GraphQL (toujours nécessaire)
GAZELLE_CLIENT_ID=...
GAZELLE_CLIENT_SECRET=...
GAZELLE_REFRESH_TOKEN=...
```

---

## 📝 Notes

- **Import initial** : SQL Server est plus rapide et plus fiable (toutes les données d'un coup)
- **Imports futurs** : API GraphQL est nécessaire pour récupérer les nouveaux contacts/pianos
- **Hybride** : On peut utiliser SQL Server pour l'initial, puis API pour les mises à jour

---

**Date de création :** 2025-01-XX  
**Statut :** En attente de la doc API Gazelle pour compléter l'implémentation

