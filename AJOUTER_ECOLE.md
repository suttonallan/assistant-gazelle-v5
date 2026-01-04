# Ajouter une nouvelle école - 10 secondes ⏱️

## Architecture professionnelle

✅ **Backend 100% agnostique** - Aucun code à modifier
✅ **Configuration en base de données** - Pas de fichiers JSON
✅ **ZÉRO hardcoded credentials** - Tout dans Supabase

## Étape 1: Connexion à Supabase

1. Va sur [supabase.com](https://supabase.com)
2. Ouvre ton projet
3. SQL Editor → New query

## Étape 2: Ajouter l'institution (10 secondes)

```sql
INSERT INTO institutions (slug, name, gazelle_client_id, options)
VALUES ('orford', 'Orford', 'cli_OBTENU_DEPUIS_GAZELLE', '{}');
```

**C'est tout!** Routes disponibles immédiatement:
```
GET /api/orford/pianos
GET /api/orford/activity
GET /api/orford/stats
```

## Comment obtenir le client_id Gazelle

1. Va sur [gazelleapp.io](https://gazelleapp.io)
2. Connecte-toi avec le compte de l'école
3. Paramètres → API → Client ID
4. Copie le `cli_xxxxxxxxxxxxx`
5. Colle-le dans la requête SQL ci-dessus

## Options spéciales (Place des Arts)

Pour une institution qui a des fonctionnalités supplémentaires:

```sql
INSERT INTO institutions (slug, name, gazelle_client_id, options)
VALUES (
  'place-des-arts',
  'Place des Arts',
  'cli_HbEwl9rN11pSuDEU',
  '{"has_requests": true, "has_email_parser": true}'
);
```

Les options sont utilisées par le frontend pour afficher ou masquer des fonctionnalités.

## Architecture

```
Frontend → GET /api/{slug}/pianos
              ↓
Backend → SELECT * FROM institutions WHERE slug = {slug}
              ↓
Config chargée: {name, gazelle_client_id, options}
              ↓
Gazelle API → allPianos(clientId: gazelle_client_id)
              ↓
Fusion Supabase overlays
              ↓
Response: {pianos: [...], count: 42, institution: "Orford"}
```

## Modifier une institution

```sql
-- Changer le nom affiché
UPDATE institutions
SET name = 'Nouveau Nom'
WHERE slug = 'orford';

-- Désactiver temporairement
UPDATE institutions
SET active = false
WHERE slug = 'orford';

-- Changer le client_id
UPDATE institutions
SET gazelle_client_id = 'cli_NOUVEAU_ID'
WHERE slug = 'orford';
```

## Lister toutes les institutions

```bash
curl https://api.example.com/api/institutions/list

{
  "institutions": [
    {"slug": "vincent-dindy", "name": "Vincent d'Indy", "options": {}},
    {"slug": "orford", "name": "Orford", "options": {}},
    {"slug": "place-des-arts", "name": "Place des Arts", "options": {"has_requests": true}}
  ],
  "count": 3
}
```

## Avantages

- ✅ **Scalable**: Ajouter 100 écoles = 100 INSERT SQL
- ✅ **Zero-code**: Aucune modification backend/frontend
- ✅ **Zero-deploy**: Aucun redémarrage requis
- ✅ **Audit**: Toutes les modifs sont tracées dans Supabase
- ✅ **Permissions**: RLS contrôle qui peut modifier quoi
- ✅ **Cache**: Config mise en cache 60 secondes (performance)

## Variables d'environnement (inchangées)

```bash
# Backend (Render) - Une seule paire pour TOUT LE MONDE
GAZELLE_CLIENT_ID=yCLgIwBusPMX9bZHtbzePvcNUisBQ9PeA4R93OwKwNE
GAZELLE_CLIENT_SECRET=CHiMzcYZ2cVgBCjQ7vDCxr3jIE5xkLZ_9v4VkU-O9Qc

# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGci...
```

Le `client_id` spécifique dans la requête Gazelle détermine quelle école est chargée.
