# Workflow — RV conjoint apprenti (clone d'un rendez-vous)

## Contexte

Gazelle ne supporte qu'un seul technicien par event (`userId` singulier).
Pour qu'un apprenti accompagne un technicien principal, on crée 2 events
séparés liés par convention, plus on annote l'event original.

## Contraintes critiques

**1. Le 2ᵉ event (accompagnateur) DOIT être `type: PERSONAL`**, pas `APPOINTMENT`.
Sinon le client reçoit deux avis de rendez-vous identiques.

**2. Le titre de l'event ORIGINAL peut être annoté librement.**
Vérifié en prod le 2026-04-12 : le champ `title` de l'event n'apparaît
PAS dans l'email de confirmation envoyé au client. On peut donc
modifier le titre de l'event principal pour ajouter « + Nom
Accompagnateur » ou « (en collaboration avec Nom) » sans polluer
l'expérience client.

## Flow

### 1. Lire l'event source

```python
# Utiliser allEventsBatched avec filtre
query = """
query($filters: PrivateAllEventsFilter) {
    allEventsBatched(first: 5, filters: $filters) {
        nodes {
            id title start duration type status notes
            user { id defaultContact { firstName lastName } }
            client { id defaultContact { firstName lastName } }
            location { ... }
            allEventPianos(first: 10) {
                nodes { piano { id make model } isTuning }
            }
        }
    }
}
"""
```

### 2. Construire le clone

```python
clone_input = {
    "title": f"[Accompagnement] {original_title}",
    "start": original_start,       # même heure
    "duration": original_duration,  # même durée
    "type": "PERSONAL",            # ★ PAS APPOINTMENT ★
    "userId": apprentice_user_id,   # JP, Margot, etc.
    "notes": f"Accompagnement de {tech_principal_name} chez {client_name}.\n"
             f"Event principal: {original_event_id}",
    # NE PAS inclure clientId si ça risque de trigger une notification
    # Mettre le nom du client dans le titre/notes à la place
}
```

### 3. Créer le clone

```python
mutation = """
mutation CreateEvent($input: PrivateEventInput!) {
    createEvent(input: $input) {
        event { id title start type status }
        mutationErrors { fieldName messages }
    }
}
"""
result = gz._execute_query(mutation, {"input": clone_input})
```

### 4. Annoter l'event original (titre + notes)

Le champ `title` n'étant pas visible au client (vérifié 2026-04-12),
on peut l'annoter librement. Approche recommandée :

```python
# Récupérer l'event original
source = get_event_by_id("evt_xxx")

# Nouveau titre avec annotation de collaboration
new_title = f"{source['title']} + {apprentice_firstname}"

# Nouvelles notes avec lien bidirectionnel
new_notes = (
    (source.get('notes') or '')
    + f"\n\nAccompagné par {apprentice_full_name} "
    f"(event: {clone_event_id})"
)

# Update via updateEvent mutation (à tester la première fois)
update_event(source['id'], {"title": new_title, "notes": new_notes})
```

Mutation `updateEvent` à confirmer lors du premier usage réel — pas
encore testée dans ce skill.

## Valeurs EventType connues

`APPOINTMENT | PERSONAL | MEMO | SYNCED`

## User IDs techniciens

À récupérer depuis `techniciens_config.py` ou `allUsers` Gazelle.
Pas hardcodés dans le workflow — résoudre dynamiquement.

## Comportement en cas d'annulation

Si l'event principal est annulé, penser à annuler aussi le clone.
Pattern à définir (pas encore implémenté).
