# 📚 Référence API GraphQL Gazelle

**Source :** https://gazelleapp.io/docs/graphql/private/schema/privatequery.doc.html  
**Date :** 2025-01-XX

---

## 🔍 Queries Principales

### Client

```graphql
client(id: String!): PrivateClient
```

**Champs disponibles dans `PrivateClient` :**
- `id`
- `companyName`
- `status`
- `tags`
- `defaultContact { id firstName lastName }`
- `contacts { nodes { id firstName lastName } }` (tous les contacts)
- `pianos { nodes { id make model serialNumber type year location notes } }` (tous les pianos)
- `createdAt`
- `updatedAt`

### Contact

```graphql
contact(id: String!): PrivateContact
```

**Champs disponibles dans `PrivateContact` :**
- `id`
- `firstName`
- `lastName`
- `clientId`

### Piano

```graphql
piano(id: String!, pianoId: String): PrivatePiano
```

**Champs disponibles dans `PrivatePiano` :**
- `id`
- `clientId`
- `make`
- `model`
- `serialNumber`
- `type`
- `year`
- `location`
- `notes`

### Event (Rendez-vous)

```graphql
event(eventId: String!): PrivateEvent
```

**Champs disponibles dans `PrivateEvent` :**
- `id`
- `client { id }`
- `start`
- `confirmedByClient`
- `technician { id }`
- `piano { id }`

### Timeline Entries

La documentation montre qu'il existe des queries pour les timeline entries, mais la structure exacte doit être vérifiée dans la doc complète.

---

## 📦 Queries Paginées (Batched)

### Clients

```graphql
allClientsBatched(
  first: Int
  after: String
): PrivateClientConnection
```

**Note :** Cette query n'existe peut-être pas directement. Utiliser `client(id: String!)` pour chaque client.

### Events (Rendez-vous)

```graphql
allEventsBatched(
  first: Int
  after: String
  filters: PrivateAllEventsFilter
): PrivateEventConnection
```

**Filtres disponibles :**
- `startOn: ISO8601Date`
- `endOn: ISO8601Date`
- `type: [EventType!]` (ex: `["APPOINTMENT"]`)
- `clientId: String`

---

## 🔧 Queries pour Contacts et Pianos

### Récupérer les contacts d'un client

```graphql
query GetClientContacts($clientId: ID!) {
  client(id: $clientId) {
    id
    contacts {
      nodes {
        id
        firstName
        lastName
      }
    }
  }
}
```

### Récupérer les pianos d'un client

```graphql
query GetClientPianos($clientId: ID!) {
  client(id: $clientId) {
    id
    pianos {
      nodes {
        id
        clientId
        make
        model
        serialNumber
        type
        year
        location
        notes
      }
    }
  }
}
```

---

## 📝 Notes Importantes

1. **Pas de `allClientsBatched`** : Il faut utiliser `allEventsBatched` pour trouver les clients via leurs rendez-vous, puis utiliser `client(id: String!)` pour récupérer les détails complets.

2. **Contacts et Pianos** : Accessibles via `client(id: String!)` dans les champs `contacts` et `pianos`.

3. **Timeline Entries** : La structure exacte doit être vérifiée dans la documentation complète du schéma.

---

**Dernière mise à jour :** 2025-01-XX

