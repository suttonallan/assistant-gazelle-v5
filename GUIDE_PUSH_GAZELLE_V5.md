# 🦌 Guide: Pousser l'historique de service vers Gazelle (V5)

## ⚠️ PREMIÈRE FOIS - MODE SÉCURISÉ

Ce guide vous accompagne pour pousser l'historique de service des pianos Place des Arts vers Gazelle **pour la première fois** depuis la V5 (Supabase).

---

## 📋 Prérequis

1. **Client API Gazelle configuré** : 
   - Fichier `config/token.json` avec vos tokens OAuth2
   - Fichier `config/.env` avec `GAZELLE_CLIENT_ID` et `GAZELLE_CLIENT_SECRET`

2. **Supabase configuré** :
   - Variables d'environnement `SUPABASE_URL` ou `SUPABASE_HOST`
   - `SUPABASE_PASSWORD` défini

3. **Demandes Place des Arts** : 
   - Des demandes avec `AppointmentId` mais sans `ServiceHistoryId`

**✅ Compatible Mac et Windows**

---

## 🚀 Utilisation

### Étape 1: Vérifier les prérequis

```bash
# Vérifier que le fichier token existe
ls config/token.json

# Vérifier les variables Supabase
echo $SUPABASE_URL  # Sur Mac/Linux
# ou
echo %SUPABASE_URL%  # Sur Windows

# Vérifier les variables Gazelle
cat config/.env | grep GAZELLE
```

### Étape 2: Lancer le script

```bash
cd /path/to/assistant-gazelle-v5  # Mac
# ou
cd "\\tsclient\assistant-gazelle-v5"  # Windows

python3 scripts/push_service_history_to_gazelle.py
```

---

## 📊 Ce que fait le script

### Étape 1: Test de connexion (lecture seule)
- ✅ Utilise le client API Gazelle existant (`core/gazelle_api_client.py`)
- ✅ Vérifie que vous pouvez vous connecter à Gazelle
- ✅ Teste en récupérant quelques clients
- ❌ Si échec: Vérifiez vos tokens dans `config/token.json` et `config/.env`

### Étape 2: Identification des demandes
- 🔍 Trouve les demandes Place des Arts qui ont:
  - Un `AppointmentId` (RV créé dans Gazelle)
  - Pas de `ServiceHistoryId` (pas encore poussé)
  - Status = `ASSIGN_OK` ou `COMPLETED`

### Étape 3: Test sur UNE seule demande
- 🧪 **IMPORTANT**: Teste d'abord sur UNE seule demande
- ⚠️  Demande votre confirmation avant de créer l'entrée
- ✅ Crée une TimelineEntry dans Gazelle via l'API
- 💾 Met à jour Supabase avec le `ServiceHistoryId`

### Étape 4: Poussée du reste (optionnel)
- 🚀 Après validation du test, propose de pousser le reste
- 📊 Affiche les résultats (succès/échecs)

---

## 🔍 Vérification après le test

Après avoir poussé UNE demande de test:

1. **Vérifier dans Gazelle**:
   - Allez sur le piano concerné
   - Vérifiez que l'entrée timeline apparaît
   - Vérifiez que les détails sont corrects

2. **Vérifier dans Supabase**:
   ```sql
   SELECT "Id", "AppointmentId", "ServiceHistoryId", "Status"
   FROM "PlaceDesArtsRequests"
   WHERE "ServiceHistoryId" IS NOT NULL
   ORDER BY "UpdatedAt" DESC
   ```

3. **Si tout est OK**: Relancez le script et acceptez de pousser le reste

---

## ⚠️ Structure de la mutation GraphQL

**IMPORTANT**: La mutation `createTimelineEntry` doit être vérifiée dans la documentation Gazelle.

Le script utilise cette structure (à ajuster si nécessaire):

```graphql
mutation CreateTimelineEntry {
  createTimelineEntry(input: {
    pianoId: "pno_xxxxx"
    occurredAt: "2025-01-27T14:30:00Z"
    entryType: SERVICE_ENTRY_MANUAL
    title: "Place des Arts - WP"
    details: "Pour: Francos - Paige\nSalle: WP\nDiapason: 440 Hz\n\nNotes: ..."
  }) {
    id
    occurredAt
    entryType
    title
    details
  }
}
```

### Si la mutation échoue

1. **Vérifier la documentation Gazelle**:
   - URL: https://gazelleapp.io/docs/graphql/private/schema/
   - Chercher "createTimelineEntry" ou "timeline" mutations

2. **Ajuster le script**:
   - Modifier la fonction `create_timeline_entry_mutation()` dans le script
   - Vérifier les noms de champs (camelCase vs snake_case)
   - Vérifier les types (String vs DateTime, etc.)

---

## 📦 Dépendances Python

Le script utilise les modules existants de V5:

```bash
# Dépendances déjà installées dans V5
pip3 install psycopg2-binary requests python-dotenv
```

**Le script utilise automatiquement:**
- `core/gazelle_api_client.py` - Client API Gazelle
- `core/db_utils.py` - Utilitaires base de données (si nécessaire)

---

## 🐛 Dépannage

### Erreur: "Fichier token introuvable"
- **Solution**: Vérifiez que `config/token.json` existe
- Si absent: Utilisez un autre script d'import pour générer le token

### Erreur: "GAZELLE_CLIENT_ID non défini"
- **Solution**: Vérifiez que `config/.env` contient:
  ```
  GAZELLE_CLIENT_ID=votre_client_id
  GAZELLE_CLIENT_SECRET=votre_client_secret
  ```

### Erreur: "Token expiré"
- **Solution**: Le client API rafraîchit automatiquement le token
- Si ça échoue: Régénérez le token OAuth

### Erreur: "Supabase non configuré"
- **Solution**: Définissez `SUPABASE_URL` ou `SUPABASE_HOST` dans `.env`
- Format: `SUPABASE_URL=https://xxx.supabase.co`

### Erreur: "Pas de PianoId Gazelle"
- **Cause**: La demande n'a pas de `AppointmentId` ou le RV n'a pas de `PianoId`
- **Solution**: Vérifiez que les rendez-vous sont bien synchronisés depuis Gazelle

### Erreur GraphQL: "Field not found"
- **Cause**: La mutation `createTimelineEntry` n'existe pas ou a un nom différent
- **Solution**: Vérifiez la documentation Gazelle et ajustez le script

---

## 📝 Format des données poussées

Pour chaque demande, le script crée une TimelineEntry avec:

- **Titre**: `"Place des Arts - {Salle}"` (ex: "Place des Arts - WP")
- **Détails**:
  ```
  Pour: {ForWho}
  Salle: {Room}
  Diapason: {Diapason} Hz
  
  Notes: {Notes} (si présent)
  ```
- **Date**: Date du rendez-vous (`AppointmentDate` ou `StartAt`)
- **Type**: `SERVICE_ENTRY_MANUAL`
- **PianoId**: ID Gazelle du piano (depuis `Appointments.PianoId`)

---

## ✅ Checklist avant de pousser

- [ ] Tokens OAuth valides (`config/token.json`)
- [ ] Variables Gazelle configurées (`config/.env`)
- [ ] Variables Supabase configurées (`.env`)
- [ ] Au moins une demande avec `AppointmentId` et sans `ServiceHistoryId`
- [ ] Documentation Gazelle consultée pour vérifier la mutation
- [ ] Backup de Supabase (recommandé)

---

## 🎯 Après la première fois

Une fois que vous avez validé que tout fonctionne:

1. Le script peut être relancé régulièrement pour pousser les nouvelles demandes
2. Vous pouvez automatiser avec un script planifié (cron/task scheduler)
3. Les demandes déjà poussées (avec `ServiceHistoryId`) seront ignorées

---

## 📞 Support

Si vous rencontrez des problèmes:

1. Vérifiez les logs du script (affichés dans le terminal)
2. Vérifiez la documentation Gazelle GraphQL
3. Testez d'abord avec UNE seule demande
4. Vérifiez que les données dans Gazelle sont correctes après le test

---

**Bon courage pour votre première poussée vers Gazelle! 🚀**


