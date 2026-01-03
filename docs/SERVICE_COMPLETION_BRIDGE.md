# Service Completion Bridge - Documentation

## Vue d'ensemble

Le **Service Completion Bridge** est le pont modulaire entre les systèmes d'Assistant (Vincent d'Indy, Place des Arts, etc.) et le moteur de push Gazelle.

```
┌─────────────────┐
│   Assistant     │
│  (Vincent, IA)  │
└────────┬────────┘
         │
         │ complete_service_session(piano_id, notes, institution)
         ▼
┌─────────────────────────────────────────────┐
│  Service Completion Bridge (Modulaire)     │
│  - Validation                               │
│  - Mapping institution → client_id          │
│  - Mapping technicien → user_id             │
└────────┬────────────────────────────────────┘
         │
         │ push_technician_service_with_measurements()
         ▼
┌─────────────────────────────────────────────┐
│  Gazelle Push Engine                        │
│  1. Update Last Tuned (manualLastService)   │
│  2. Create Event + Complete with notes      │
│  3. Parse temp/humidity → Measurement       │
│  4. Set piano INACTIVE                      │
└─────────────────────────────────────────────┘
```

## Fichiers clés

### 1. Pont modulaire
**Fichier**: [core/service_completion_bridge.py](../core/service_completion_bridge.py)

**Fonction principale**: `complete_service_session()`

**Responsabilités**:
- ✅ Valider les arguments (piano_id, notes, institution)
- ✅ Résoudre les mappings (institution → client_id, technicien → user_id)
- ✅ Appeler le moteur Gazelle avec les bons paramètres
- ✅ Retourner un résultat standardisé
- ✅ Logger toutes les étapes pour debugging

**Modulairité**:
```python
# Pour Vincent d'Indy
result = complete_service_session(
    piano_id="ins_abc123",
    service_notes="Accord 440 Hz, 22°C, 45%",
    institution="vincent-dindy",
    technician_name="Nicolas"
)

# Pour Place des Arts (demain)
result = complete_service_session(
    piano_id="ins_xyz789",
    service_notes="Réparation pédale forte",
    institution="place-des-arts",  # ← Juste changer ça!
    technician_name="Isabelle"
)
```

### 2. Endpoint API
**Fichier**: [api/vincent_dindy.py](../api/vincent_dindy.py:383-537)

**Endpoint**: `POST /vincent-dindy/pianos/{piano_id}/complete-service`

**Responsabilités**:
- ✅ Récupérer les données du piano depuis Supabase
- ✅ Vérifier que le piano est marqué comme `completed`
- ✅ Extraire les notes de service (travail + observations)
- ✅ Appeler le pont modulaire
- ✅ Mettre à jour `sync_status` dans Supabase

**Usage**:
```javascript
// Frontend - Après que l'utilisateur clique "Travail complété"
const response = await fetch(
    `/api/vincent-dindy/pianos/${pianoId}/complete-service?technician_name=Nicolas`,
    { method: 'POST' }
);

const result = await response.json();
console.log('Gazelle Event ID:', result.gazelle_event_id);
```

### 3. Moteur Gazelle
**Fichier**: [core/gazelle_api_client.py](../core/gazelle_api_client.py:1242-1410)

**Fonction**: `push_technician_service_with_measurements()`

**Ordre d'exécution garanti**:
1. **Update Last Tuned** (manualLastService) ← Mise à jour du champ "Date d'accord"
2. **Create Event** → **Complete Event** avec `serviceHistoryNotes` ← Création de l'entrée dans l'historique
3. **Parse temp/humidity** → **Create Measurement** ← Création de la mesure si détectée
4. **Set piano INACTIVE** ← Remise du piano en INACTIVE après toutes les opérations

**Note critique**: Le piano ne doit être remis en INACTIVE **qu'après** confirmation de réception des notes ET des mesures. Ceci est géré automatiquement par la fonction.

## Mappings

### Institutions → Client ID Gazelle

Défini dans [core/service_completion_bridge.py](../core/service_completion_bridge.py:27-32)

```python
INSTITUTION_CLIENT_MAPPING = {
    "vincent-dindy": "cli_3VDsY1hbbEqnMlN2",
    "place-des-arts": None,  # À définir
    "orford": None,          # À définir
}
```

**Pour ajouter une nouvelle institution**:
```python
from core.service_completion_bridge import register_institution

register_institution("place-des-arts", "cli_XYZ123")
```

### Techniciens → User ID Gazelle

Défini dans [core/service_completion_bridge.py](../core/service_completion_bridge.py:34-40)

```python
TECHNICIAN_USER_MAPPING = {
    "Nicolas": "usr_RJdEjJR8mOKGqn2f",
    "Isabelle": None,  # À définir
    "JP": None,        # À définir
}
```

**Pour ajouter un nouveau technicien**:
```python
from core.service_completion_bridge import register_technician

register_technician("Isabelle", "usr_ABC123")
```

## Flux de données

### 1. Validation de service côté Assistant

**Fichier**: [frontend/src/components/vdi/VDI_TechnicianView.jsx](../frontend/src/components/vdi/VDI_TechnicianView.jsx:169-187)

```jsx
<Checkbox
    checked={isWorkCompleted}
    onChange={(e) => setIsWorkCompleted(e.target.checked)}
>
    ✅ Travail complété (prêt pour Gazelle)
</Checkbox>

<Button onClick={() => saveTravail()}>
    💾 Sauvegarder → Suivant
</Button>
```

### 2. Sauvegarde dans Supabase

**Fichier**: [frontend/src/components/VincentDIndyDashboard.jsx](../frontend/src/components/VincentDIndyDashboard.jsx:406-466)

```javascript
const saveTravail = async (id) => {
    const updates = {
        travail,
        observations,
        isWorkCompleted,
        status: isWorkCompleted ? 'completed' : 'work_in_progress'
    };

    await savePianoToAPI(id, updates);
    // → PUT /vincent-dindy/pianos/{id}
};
```

### 3. Transition d'état automatique

**Fichier**: [api/vincent_dindy.py](../api/vincent_dindy.py:338-352)

```python
# Si is_work_completed = true → status = 'completed'
if update_data.get('is_work_completed') == True:
    update_data['status'] = 'completed'
    update_data['completed_at'] = datetime.now().isoformat()
```

### 4. Push vers Gazelle (Option 1: Auto)

**Déclenchement**: Immédiatement après `saveTravail()` si `auto_push=true`

```javascript
// Frontend - Appel automatique après sauvegarde
if (isWorkCompleted) {
    await fetch(
        `/api/vincent-dindy/pianos/${pianoId}/complete-service?auto_push=true`,
        { method: 'POST' }
    );
}
```

### 5. Push vers Gazelle (Option 2: Manuel par Nick)

**Déclenchement**: Nick clique sur "Push vers Gazelle"

**Fichier**: [frontend/src/components/VincentDIndyDashboard.jsx](../frontend/src/components/VincentDIndyDashboard.jsx:770-802)

```javascript
const handlePushToGazelle = async () => {
    const response = await fetch('/api/vincent-dindy/push-to-gazelle', {
        method: 'POST',
        body: JSON.stringify({
            tournee_id: selectedTourneeId,
            technician_id: 'usr_HcCiFk7o0vZ9xAI0'
        })
    });
};
```

## Résultat standardisé

```python
{
    'success': True,
    'piano_id': 'ins_abc123',
    'gazelle_event_id': 'evt_xyz789',
    'last_tuned_updated': True,
    'service_note_created': True,
    'measurement_created': True,
    'measurement_values': {'temperature': 22, 'humidity': 45},
    'piano_set_inactive': True,
    'error': None,
    'timestamp': '2026-01-03T12:00:00',
    'metadata': {...}
}
```

## Garanties

### Ordre d'exécution

✅ **GARANTI**: Le piano est remis en INACTIVE **après** toutes les opérations:
1. Last Tuned mis à jour ✅
2. Service note créée dans l'historique ✅
3. Measurement créée (si temp/humidity détectée) ✅
4. **PUIS** piano remis en INACTIVE ✅

### Atomicité

⚠️ **NON GARANTI**: Si une étape échoue, les étapes précédentes ne sont PAS annulées.

Exemple:
- Last Tuned mis à jour ✅
- Service note créée ✅
- **Measurement échoue** ❌
- Piano remis en INACTIVE quand même ✅

**Rationale**: On préfère avoir des données partielles dans Gazelle plutôt que rien du tout.

### Idempotence

⚠️ **NON GARANTI**: Appeler deux fois avec les mêmes données créera deux événements dans Gazelle.

**Mitigation**: Le `sync_status` dans Supabase empêche les doubles push accidentels.

## Tests

### Test manuel

```bash
# Test avec un piano réel
python3 -c "
from core.service_completion_bridge import complete_service_session

result = complete_service_session(
    piano_id='ins_RXJMSDTckzu2Xswd',
    service_notes='Test accord 440 Hz, température 22°C, humidité 45%',
    institution='vincent-dindy',
    technician_name='Nicolas'
)

print('✅ Success:', result['success'])
print('📝 Event ID:', result['gazelle_event_id'])
print('🌡️  Measurement:', result['measurement_values'])
"
```

### Test via API

```bash
# 1. Marquer un piano comme complété
curl -X PUT http://localhost:8001/vincent-dindy/pianos/ins_RXJMSDTckzu2Xswd \
  -H "Content-Type: application/json" \
  -d '{
    "travail": "Accord 440 Hz",
    "observations": "Température 22°C, humidité 45%",
    "isWorkCompleted": true
  }'

# 2. Pousser vers Gazelle
curl -X POST "http://localhost:8001/vincent-dindy/pianos/ins_RXJMSDTckzu2Xswd/complete-service?technician_name=Nicolas"
```

## Évolution future

### Ajout d'une nouvelle institution

1. **Ajouter le mapping**:
   ```python
   register_institution("nouvelle-institution", "cli_ABC123")
   ```

2. **Utiliser le pont**:
   ```python
   complete_service_session(
       piano_id="ins_xyz",
       service_notes="...",
       institution="nouvelle-institution"  # ← Juste changer ça!
   )
   ```

3. **Aucun changement de code nécessaire** ✅

### Ajout d'un nouveau technicien

1. **Ajouter le mapping**:
   ```python
   register_technician("Nouveau Technicien", "usr_XYZ123")
   ```

2. **Utiliser dans l'appel**:
   ```python
   complete_service_session(
       technician_name="Nouveau Technicien"
   )
   ```

## Questions fréquentes

### Q: Que se passe-t-il si le piano est déjà INACTIVE?

**R**: Le pipeline vérifie le statut actuel. Si déjà INACTIVE, il ne fait rien (pas d'erreur).

### Q: Peut-on pousser un piano sans température/humidité?

**R**: Oui! Le parsing de temp/humidity est optionnel. Si non détecté, seule la note de service est créée.

### Q: Comment savoir si le push a réussi?

**R**: Vérifier `result['success']` et `result['gazelle_event_id']`. Si `gazelle_event_id` est non-null, le push a réussi.

### Q: Peut-on re-pousser un piano déjà pushé?

**R**: Oui, mais cela créera un **nouvel événement** dans Gazelle. Le `sync_status` dans Supabase devrait empêcher les doubles push accidentels.

### Q: Quelle est la différence entre `auto_push=true` et le push manuel?

**R**:
- `auto_push=true`: Push immédiat après complétion (utilisé par l'Assistant)
- Push manuel: Nick clique sur "Push vers Gazelle" pour pousher plusieurs pianos en batch

Les deux utilisent le même moteur de push sous le capot.

## Prévention des régressions

### Checklist avant modification

Avant de modifier le Service Completion Bridge ou le moteur Gazelle:

1. ☐ Lire cette documentation
2. ☐ Comprendre l'ordre d'exécution garanti
3. ☐ Tester avec un piano réel dans Gazelle Staging
4. ☐ Vérifier que le piano est bien remis en INACTIVE
5. ☐ Vérifier que l'historique contient bien la note
6. ☐ Vérifier que la mesure est bien créée (si temp/humidity)
7. ☐ Mettre à jour cette documentation si nécessaire

### Logs à surveiller

```
🚀 SERVICE COMPLETION BRIDGE
Piano ID: ins_abc123
...
🔄 Updating Last Tuned date for piano ins_abc123 to 2026-01-03...
✅ Piano mis à jour: ins_abc123 - manualLastService: 2026-01-03

🔄 Creating service note in Gazelle history...
✅ Événement de service créé: evt_xyz789
✅ Événement complété avec serviceHistoryNotes (historique créé)

🔍 Parsed temperature/humidity: 22°C, 45%
🔄 Creating measurement in Gazelle...
✅ Measurement created: msr_123 (22°C, 45%)

✅ Piano remis en INACTIVE après toutes les opérations (note + mesures)
```

Si vous ne voyez PAS tous ces logs, quelque chose a échoué.

## Contact

Pour toute question ou modification, contacter:
- Allan Sutton (développeur principal)
- Nicolas Lessard (technicien principal Vincent d'Indy)
