# Prompt: Correction des incohérences techniciens PDA vs Gazelle

## Contexte du problème

Le système Assistant Gazelle V5 gère des demandes de service pour Place des Arts (PDA). Chaque demande peut être liée à un rendez-vous (RV) dans Gazelle via un `appointment_id`. 

**Problème critique** : Les techniciens assignés dans la base de données PDA (`place_des_arts_requests.technician_id`) ne correspondent pas toujours aux techniciens assignés dans Gazelle (`gazelle_appointments.technicien`).

**Règle fondamentale** : **Gazelle est la source de vérité absolue** pour les techniciens. Si un RV existe dans Gazelle avec un technicien assigné, ce technicien doit être reflété dans PDA.

## Exemples d'incohérences observées

1. **15 janvier - ONJ (matin et soir)** : 
   - PDA affiche : Allan
   - Gazelle a : Nick (dans les RV "Place des Arts ONJ avant 9h" et "Place des Arts ONJ à 18h")
   - **Attendu** : Nick

2. **14 janvier - Clémence** :
   - PDA affiche : Allan
   - Gazelle a : Nick (dans le RV "Place des Arts Clémence à 13h")
   - **Attendu** : Nick

3. **11 janvier - Gala Chinois** :
   - PDA affiche : Aucun technicien
   - Gazelle a : JP (dans le RV "Place des Arts Gala chinois avant 9h")
   - **Attendu** : JP

4. **11 janvier - Lord of the rings** :
   - PDA affiche : Aucun technicien
   - Gazelle a : JP (dans le RV "Place des Arts Lord of the rings avant 12h")
   - **Attendu** : JP

5. **11 janvier - Ferland** :
   - PDA affiche : Aucun technicien
   - Gazelle a : Nick (dans le RV "Place des Arts Ferland avant 10h")
   - **Attendu** : Nick

6. **9 janvier - Tire le Coyote (soir)** :
   - PDA affiche : Allan
   - Gazelle a : Nick (dans le RV "Place des Arts Tire le coyote à 18h")
   - **Attendu** : Nick

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

## Problèmes identifiés

### 1. Liens RV incorrects
Les demandes PDA sont parfois liées aux **mauvais RV** dans Gazelle. Par exemple :
- Une demande "ONJ" est liée à un RV "Admin" d'Allan au lieu du RV "Place des Arts ONJ" de Nick
- Cela cause des incohérences car le technicien du mauvais RV est copié dans PDA

### 2. Matching insuffisant
La fonction `_find_matching_appointment()` dans `modules/place_des_arts/services/gazelle_sync.py` ne priorise pas assez les RV avec "Place des Arts" dans le titre et ne vérifie pas assez les mots-clés de la demande.

### 3. Synchronisation incomplète
Même quand les RV sont correctement liés, la synchronisation des techniciens n'est pas toujours effectuée systématiquement.

## Tâches à accomplir

### Tâche 1 : Corriger les liens RV incorrects
Pour chaque demande avec un `appointment_id`, vérifier que le RV lié correspond bien à la demande :
- Le titre du RV doit contenir "Place des Arts" + des mots-clés de la demande (`for_who` ou `room`)
- Si plusieurs RV existent le même jour, choisir celui qui correspond le mieux (titre, salle, heure)
- Si le RV lié ne correspond pas, trouver le bon RV et mettre à jour `appointment_id`

### Tâche 2 : Forcer la synchronisation des techniciens
Pour TOUTES les demandes avec un `appointment_id` :
- Récupérer le technicien depuis Gazelle (`gazelle_appointments.technicien` où `external_id = appointment_id`)
- Si le technicien dans Gazelle existe et diffère de celui dans PDA, **mettre à jour PDA** avec le technicien de Gazelle
- Si le technicien dans Gazelle existe mais pas dans PDA, **ajouter le technicien** dans PDA
- Gazelle est toujours la source de vérité

### Tâche 3 : Améliorer le matching
Améliorer `_find_matching_appointment()` pour :
- **Prioriser fortement** les RV avec "Place des Arts" dans le titre (+10 points)
- Vérifier que le titre contient des mots-clés de `for_who` (+3 points par mot significatif)
- Vérifier la correspondance de la salle dans le titre ou la location (+5 points)
- Vérifier la correspondance de l'heure si disponible (+4 points)

### Tâche 4 : Normaliser les IDs alternatifs
Si un technicien a un ID alternatif (ex: `usr_QmEpdeM2xMgZVkDS` pour JP), le normaliser vers l'ID standard (`usr_ReUSmIJmBF86ilY1`) lors de l'affichage et de la synchronisation.

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

## Script de correction immédiate

Créer un script `scripts/force_sync_all_technicians_pda.py` qui :
1. Récupère toutes les demandes avec `appointment_id`
2. Pour chaque demande, récupère le technicien depuis Gazelle
3. Compare avec le technicien dans PDA
4. Met à jour PDA si différent (mode dry-run par défaut, `--apply` pour exécuter)

## Critères de succès

✅ Toutes les demandes avec un `appointment_id` ont un `technician_id` qui correspond exactement à `gazelle_appointments.technicien`

✅ Les demandes sont liées aux bons RV (ceux avec "Place des Arts" + mots-clés de la demande dans le titre)

✅ Le matching des RV est amélioré pour éviter les erreurs futures

✅ Un script permet de forcer la synchronisation complète si nécessaire

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

---

**Objectif final** : Éliminer toutes les incohérences entre les techniciens dans PDA et Gazelle, en s'assurant que Gazelle reste la source de vérité unique.
