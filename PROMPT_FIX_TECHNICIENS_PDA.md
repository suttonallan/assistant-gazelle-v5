# Prompt: Vérification et correction complète des demandes PDA historiques

## Contexte et état actuel

Le système Assistant Gazelle V5 gère des demandes de service pour Place des Arts (PDA). Chaque demande peut être liée à un rendez-vous (RV) dans Gazelle via un `appointment_id`. 

**✅ Corrections récentes réussies** : Les incohérences de techniciens pour les demandes de janvier 2026 ont été corrigées avec succès. Les demandes sont maintenant correctement liées aux bons RV et les techniciens sont synchronisés depuis Gazelle.

**Règle fondamentale** : **Gazelle est la source de vérité absolue** pour :
- Les techniciens assignés (`gazelle_appointments.technicien`)
- Les statuts des RV (`gazelle_appointments.status`)
- L'existence et les détails des RV

## Problème actuel : Demandes historiques (décembre 2025 et antérieures)

**Situation observée** : 
- La plupart des demandes de décembre 2025 sont encore en statut **PENDING** (affichées en "rose nouveau" dans l'interface)
- Seulement 2 demandes du 21 décembre ont un RV lié et sont en statut **CREATED_IN_GAZELLE**
- Beaucoup de demandes n'ont pas de `appointment_id` lié, mais des RV correspondants existent probablement dans Gazelle
- Les statuts ne reflètent pas l'état réel des RV dans Gazelle (probablement tous complétés)
- Les techniciens peuvent ne pas être synchronisés depuis Gazelle

**Objectif** : Vérifier et corriger **TOUTES** les demandes historiques (décembre 2025 et antérieures) pour s'assurer que :
1. ✅ Chaque demande avec un RV correspondant dans Gazelle est liée (`appointment_id` correct)
2. ✅ Le statut reflète l'état réel du RV dans Gazelle (COMPLETED si le RV est complété)
3. ✅ Le technicien assigné correspond exactement à celui dans Gazelle

## Exemples de demandes de décembre à corriger

**Analyse des demandes de décembre 2025** :
- **18 demandes** au total en décembre
- **16 demandes** en statut PENDING sans RV lié (affichées en "rose nouveau")
- **2 demandes** du 21 décembre avec RV lié (Charlie Brown Xmas, Glenn Miller)

**Exemples de corrections nécessaires** :

1. **5 décembre - Noël tout en jazz** :
   - Statut PDA : PENDING
   - Technicien PDA : Nick
   - RV lié : Aucun
   - **Action** : Chercher RV correspondant dans Gazelle, lier, synchroniser technicien et statut

2. **6 décembre - Concert 2 pianos (4 demandes)** :
   - Statut PDA : PENDING
   - Technicien PDA : Nick
   - RV lié : Aucun
   - **Action** : Chercher les 4 RV correspondants dans Gazelle, lier chacun, synchroniser

3. **21 décembre - Charlie Brown Xmas** :
   - Statut PDA : CREATED_IN_GAZELLE
   - Statut Gazelle : ACTIVE
   - **Action** : Vérifier si le RV est complété, mettre à jour le statut si nécessaire

4. **26-28 décembre - Parapapam (6 demandes)** :
   - Statut PDA : PENDING
   - Technicien PDA : Mixte (Allan et Nick)
   - RV lié : Aucun
   - **Action** : Chercher les RV correspondants, lier, synchroniser technicien et statut

## Structure de la base de données

### Table `place_des_arts_requests`
- `id` : ID unique de la demande
- `appointment_id` : ID du RV dans Gazelle (peut être NULL)
- `technician_id` : ID du technicien assigné (peut être NULL)
- `appointment_date` : Date du rendez-vous (format YYYY-MM-DD)
- `room` : Salle (ex: "5E", "TM", "WP")
- `for_who` : Nom de l'événement/client (ex: "ONJ", "Clémence", "Gala Chinois")
- `status` : Statut de la demande (ex: "CREATED_IN_GAZELLE", "PENDING", "COMPLETED")

### Table `gazelle_appointments`
- `external_id` : ID unique du RV (correspond à `appointment_id` dans PDA)
- `technicien` : ID du technicien assigné dans Gazelle (peut être NULL)
- `title` : Titre du RV (ex: "Place des Arts ONJ avant 9h")
- `start_datetime` : Date et heure de début (format ISO)
- `status` : Statut du RV dans Gazelle (ex: "ACTIVE", "COMPLETE", "COMPLETED", "CANCELLED")

### IDs des techniciens
```python
REAL_TECHNICIAN_IDS = {
    'usr_HcCiFk7o0vZ9xAI0': 'Nick',      # Nicolas Lessard
    'usr_ofYggsCDt2JAVeNP': 'Allan',     # Allan Sutton
    'usr_ReUSmIJmBF86ilY1': 'JP',       # Jean-Philippe Reny
    'usr_HihJsEgkmpTEziJo': 'À attribuer',  # Placeholder "À attribuer"
    'usr_QmEpdeM2xMgZVkDS': 'JP (alt)',  # ID alternatif pour JP (à normaliser vers usr_ReUSmIJmBF86ilY1)
}
```

## Problèmes identifiés pour les demandes historiques

### 1. Demandes sans RV lié
Beaucoup de demandes historiques n'ont pas de `appointment_id` alors que des RV correspondants existent probablement dans Gazelle. Il faut :
- Chercher les RV correspondants dans Gazelle par date, titre, salle
- Lier les demandes aux bons RV
- Synchroniser technicien et statut

### 2. Statuts incorrects
Les demandes sont en statut **PENDING** alors que les RV correspondants dans Gazelle sont probablement **COMPLETED**. Il faut :
- Vérifier le statut du RV dans Gazelle
- Mettre à jour le statut de la demande : `COMPLETED` si le RV est complété, `CREATED_IN_GAZELLE` si le RV existe mais n'est pas complété

### 3. Techniciens non synchronisés
Même pour les demandes avec RV lié, les techniciens peuvent ne pas être synchronisés depuis Gazelle. Il faut :
- Récupérer le technicien depuis Gazelle pour chaque demande liée
- Mettre à jour `technician_id` dans PDA si différent

### 4. Matching amélioré (déjà fait)
La fonction `_find_matching_appointment()` a été améliorée pour prioriser les RV avec "Place des Arts" dans le titre. Cette logique doit être utilisée pour lier les demandes historiques.

## Tâches à accomplir pour les demandes historiques

### Tâche 1 : Trouver et lier les RV manquants
Pour **TOUTES** les demandes historiques (décembre 2025 et antérieures) **sans `appointment_id`** :
1. Récupérer tous les RV Gazelle pour la date de la demande
2. Utiliser `_find_matching_appointment()` (déjà améliorée) pour trouver le meilleur match :
   - Prioriser les RV avec "Place des Arts" dans le titre (+10 points)
   - Vérifier les mots-clés de `for_who` dans le titre (+3 points par mot)
   - Vérifier la correspondance de la salle (+5 points)
   - Vérifier la correspondance de l'heure (+4 points)
3. Si un match est trouvé, lier la demande au RV (`appointment_id`)
4. Synchroniser immédiatement le technicien et le statut depuis Gazelle

### Tâche 2 : Vérifier et corriger les statuts
Pour **TOUTES** les demandes historiques (avec ou sans RV lié) :
1. Si la demande a un `appointment_id` :
   - Récupérer le statut du RV dans Gazelle
   - Si le RV est `COMPLETE` ou `COMPLETED` → mettre à jour le statut de la demande à `COMPLETED`
   - Si le RV existe mais n'est pas complété → mettre à jour le statut à `CREATED_IN_GAZELLE`
   - Si le RV n'existe plus → mettre à jour le statut à `PENDING` (ou `CANCELLED` si approprié)
2. Si la demande n'a pas de `appointment_id` mais qu'un RV correspondant est trouvé :
   - Lier la demande (Tâche 1)
   - Appliquer la logique de statut ci-dessus

### Tâche 3 : Synchroniser tous les techniciens
Pour **TOUTES** les demandes historiques avec un `appointment_id` :
1. Récupérer le technicien depuis Gazelle (`gazelle_appointments.technicien` où `external_id = appointment_id`)
2. Si le technicien dans Gazelle existe :
   - Si différent de celui dans PDA → **mettre à jour PDA** avec le technicien de Gazelle
   - Si absent dans PDA → **ajouter le technicien** dans PDA
3. Gazelle est toujours la source de vérité absolue

### Tâche 4 : Normaliser les IDs alternatifs
Si un technicien a un ID alternatif (ex: `usr_QmEpdeM2xMgZVkDS` pour JP), le normaliser vers l'ID standard (`usr_ReUSmIJmBF86ilY1`) lors de la synchronisation et de l'affichage.

## Fichiers à modifier

1. **`modules/place_des_arts/services/gazelle_sync.py`**
   - Améliorer `_find_matching_appointment()` (lignes ~323-397)
   - S'assurer que `_link_request_to_appointment()` met toujours à jour le technicien depuis Gazelle
   - S'assurer que `sync_requests_with_gazelle()` synchronise systématiquement les techniciens

2. **`api/place_des_arts.py`**
   - Dans `GET /requests`, enrichir avec le technicien de Gazelle et forcer la mise à jour si incohérence
   - Dans `POST /check-completed`, synchroniser aussi les techniciens

3. **`frontend/src/components/place_des_arts/PlaceDesArtsDashboard.jsx`**
   - Ajouter une fonction `normalizeTechnicianId()` pour convertir les IDs alternatifs
   - Utiliser cette normalisation dans la logique des couleurs

## Script de correction complète des demandes historiques

Créer un script `scripts/fix_historical_pda_requests.py` qui :

1. **Récupère toutes les demandes historiques** (décembre 2025 et antérieures)
2. **Pour chaque demande** :
   - Si pas de `appointment_id` : Chercher un RV correspondant dans Gazelle et lier
   - Si `appointment_id` existe : Vérifier que c'est le bon RV (matching amélioré)
   - Synchroniser le technicien depuis Gazelle
   - Synchroniser le statut depuis Gazelle (COMPLETED si RV complété, CREATED_IN_GAZELLE si RV existe)
3. **Mode dry-run par défaut**, `--apply` pour exécuter
4. **Logger toutes les corrections** pour traçabilité

**Note** : Le script `scripts/force_sync_all_technicians_pda.py` existe déjà et peut être utilisé pour synchroniser les techniciens. Le nouveau script doit être plus complet et gérer aussi les liens RV et les statuts.

## Critères de succès

### Pour les demandes historiques (décembre 2025 et antérieures) :

✅ **Toutes les demandes avec un RV correspondant dans Gazelle sont liées** (`appointment_id` correct)

✅ **Tous les statuts reflètent l'état réel des RV dans Gazelle** :
   - `COMPLETED` si le RV est complété dans Gazelle
   - `CREATED_IN_GAZELLE` si le RV existe mais n'est pas complété
   - `PENDING` seulement si aucun RV correspondant n'existe

✅ **Tous les techniciens sont synchronisés depuis Gazelle** :
   - `technician_id` dans PDA = `technicien` dans Gazelle pour chaque demande liée
   - Gazelle est la source de vérité absolue

✅ **Aucune demande historique n'est en "rose nouveau" (PENDING) si un RV correspondant existe dans Gazelle**

✅ **Le script de correction est créé et fonctionnel** pour traiter toutes les demandes historiques en une seule exécution

### Validation finale :

Après correction, exécuter cette requête pour vérifier qu'il n'y a plus d'incohérences :

```sql
-- Vérifier les incohérences restantes
SELECT 
    pda.id,
    pda.appointment_date,
    pda.room,
    pda.for_who,
    pda.status as status_pda,
    ga.status as status_gazelle,
    pda.technician_id as tech_pda,
    ga.technicien as tech_gazelle
FROM place_des_arts_requests pda
LEFT JOIN gazelle_appointments ga ON ga.external_id = pda.appointment_id
WHERE pda.appointment_date < '2026-01-01'
  AND (
    -- Demandes avec RV mais statut incorrect
    (pda.appointment_id IS NOT NULL AND ga.status IN ('COMPLETE', 'COMPLETED') AND pda.status != 'COMPLETED')
    OR
    -- Demandes avec RV mais technicien incorrect
    (pda.appointment_id IS NOT NULL AND ga.technicien IS NOT NULL AND (pda.technician_id IS NULL OR pda.technician_id != ga.technicien))
    OR
    -- Demandes sans RV mais qui devraient en avoir un (à vérifier manuellement)
    (pda.appointment_id IS NULL AND pda.status = 'PENDING')
  )
ORDER BY pda.appointment_date DESC;
```

Cette requête doit retourner **0 résultats** après correction complète.

## Exemple de requête SQL pour vérifier

```sql
-- Trouver les incohérences
SELECT 
    pda.id,
    pda.appointment_date,
    pda.room,
    pda.for_who,
    pda.technician_id as tech_pda,
    ga.technicien as tech_gazelle,
    ga.title as gazelle_title
FROM place_des_arts_requests pda
JOIN gazelle_appointments ga ON ga.external_id = pda.appointment_id
WHERE pda.appointment_id IS NOT NULL
  AND ga.technicien IS NOT NULL
  AND (pda.technician_id IS NULL OR pda.technician_id != ga.technicien)
ORDER BY pda.appointment_date DESC;
```

## Notes importantes

- **Ne jamais écraser un technicien de Gazelle avec un technicien de PDA** - Gazelle est toujours la source de vérité
- **Respecter le mode dry-run** dans les scripts pour permettre la vérification avant application
- **Logger toutes les corrections** pour traçabilité
- **Gérer les cas où plusieurs RV existent le même jour** - choisir le meilleur match, pas le premier

## Code de référence

Le code utilise :
- `SupabaseStorage` pour accéder à la base de données
- `storage.client.table('place_des_arts_requests')` pour les demandes PDA
- `storage.client.table('gazelle_appointments')` pour les RV Gazelle
- Format de date ISO : `YYYY-MM-DD` ou `YYYY-MM-DDTHH:MM:SS`

## Résumé de la mission

**Objectif principal** : Vérifier et corriger **TOUTES** les demandes historiques (décembre 2025 et antérieures) pour démontrer que nous maîtrisons complètement le système.

**Actions requises** :
1. 🔍 **Identifier** toutes les demandes historiques sans RV lié
2. 🔗 **Lier** chaque demande au bon RV dans Gazelle (matching intelligent)
3. 👤 **Synchroniser** tous les techniciens depuis Gazelle (source de vérité)
4. ✅ **Corriger** tous les statuts pour refléter l'état réel des RV dans Gazelle
5. 📊 **Valider** qu'il ne reste aucune incohérence

**Résultat attendu** : 
- ✅ Toutes les demandes historiques ont le bon statut (COMPLETED si RV complété)
- ✅ Toutes les demandes historiques ont le bon technicien assigné (synchronisé depuis Gazelle)
- ✅ Aucune demande n'est en "rose nouveau" (PENDING) si un RV correspondant existe
- ✅ Le système est cohérent et maîtrisé à 100%

**Preuve de maîtrise** : Après correction, toutes les demandes historiques doivent être parfaitement synchronisées avec Gazelle, démontrant une compréhension complète du système et de ses règles.
