# 🌉 Design: Pont Automatique Gazelle → Tournées Place des Arts

**Version**: 1.0
**Date**: 2026-01-04
**Auteur**: Claude (Assistant IA)
**Objectif**: Automatiser la création de tournées depuis les demandes PDA validées dans Gazelle

---

## 📋 Vue d'ensemble

Le pont automatique transforme le workflow manuel actuel en un système automatisé qui:

1. **Valide** les demandes PDA avec RV Gazelle
2. **Génère** automatiquement des tournées techniques
3. **Synchronise** bidirectionnellement entre demandes et pianos

### Workflow Actuel (Manuel) ❌
```
Demande PDA → Sync Gazelle (manuel) → Créer tournée (manuel) → Marquer complété (manuel)
```

### Workflow Cible (Automatisé) ✅
```
Demande PDA → [Validation Auto] → Tournée générée → Sync bidirectionnelle auto
```

---

## 🎯 Fonctionnalités Requises

### 1. Fonction de Validation: Sync Gazelle → "Créé Gazelle"

**Endpoint existant**: `POST /api/place-des-arts/sync-manual`
**Localisation**: [place_des_arts.py:753-846](../api/place_des_arts.py#L753-L846)

#### Logique actuelle:
```python
# 1. Récupérer demandes avec status='ASSIGN_OK'
# 2. Pour chaque demande, chercher RV dans Gazelle (via pda_validation.py)
# 3. Si trouvé → Mettre status='CREATED_IN_GAZELLE'
```

#### Améliorations requises:

**A. Déclenchement automatique** (au lieu de manuel)
- **Hook sur changement de statut**: Quand une demande passe à `ASSIGN_OK`, déclencher la validation automatiquement
- **Polling léger**: Alternative - vérifier toutes les 5 minutes s'il y a de nouvelles demandes `ASSIGN_OK`

**B. Enrichissement de la réponse**
```python
# Retourner plus d'infos pour la génération de tournée
{
    "success": True,
    "updated": 5,
    "ready_for_tour": [
        {
            "request_id": "pda_123",
            "technician_id": "usr_HcCiFk7o0vZ9xAI0",
            "appointment_date": "2026-01-15",
            "room": "401",
            "gazelle_appointment_id": "evt_xyz",
            "suggested_tour_name": "RV PdA-Nick-2026-01-15"
        }
    ]
}
```

---

### 2. Service de Génération de Tournée Auto

**Nouveau service**: `modules/place_des_arts/services/tour_generator.py`

#### Interface:
```python
class TourGenerator:
    """
    Génère automatiquement des tournées techniques pour Place des Arts.
    """

    def generate_tour_from_request(
        self,
        request_id: str,
        technician_id: str,
        appointment_date: str,
        room: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Génère une tournée pour une demande validée Gazelle.

        Logique:
        1. Chercher si une tournée existe déjà pour ce technicien + date
        2. Si oui → Ajouter le piano à la tournée existante
        3. Si non → Créer nouvelle tournée "RV PdA-{Tech}-{Date}"
        4. Lier la demande à la tournée (nouveau champ: request.tour_id)

        Returns:
            {
                "tour_id": "tournee_xyz",
                "tour_name": "RV PdA-Nick-2026-01-15",
                "created": bool,  # True si nouvelle tournée
                "piano_added": bool
            }
        """
        pass

    def find_or_create_tour(
        self,
        institution: str,  # "place-des-arts"
        technician_id: str,
        date: str,
        auto_generated: bool = True
    ) -> str:
        """
        Trouve une tournée existante ou en crée une nouvelle.

        Convention de nommage:
        - Manuelles: "[Institution] - [Tech] - [Date]"
        - Auto: "RV [Institution Abrégé]-[Tech Abrégé]-[Date]"

        Exemples:
        - "RV PdA-Nick-2026-01-15"
        - "RV PdA-Allan-2026-02-20"
        """
        pass

    def add_piano_to_tour(
        self,
        tour_id: str,
        piano_id: str,  # ID Gazelle du piano
        request_id: Optional[str] = None,
        notes: Optional[str] = None
    ) -> bool:
        """
        Ajoute un piano à une tournée existante.

        Utilise la table: vincent_dindy_piano_updates (ou nouvelle table PDA)
        Champs:
        - piano_id
        - status: 'proposed' (par défaut pour RV auto)
        - a_faire: Notes de la demande
        - tour_id: Lien vers la tournée (nouveau champ)
        - pda_request_id: Lien vers la demande (nouveau champ)
        """
        pass
```

#### Intégration au workflow:

**Endpoint nouveau**: `POST /api/place-des-arts/auto-generate-tour`
```python
@router.post("/auto-generate-tour")
async def auto_generate_tour(request_id: str):
    """
    Génère automatiquement une tournée pour une demande validée.

    Workflow:
    1. Vérifier que la demande a status='CREATED_IN_GAZELLE'
    2. Récupérer l'ID Gazelle du piano (via room/location)
    3. Appeler TourGenerator.generate_tour_from_request()
    4. Mettre à jour la demande avec tour_id
    5. Retourner la tournée créée/mise à jour
    """
    # Récupérer la demande
    storage = get_storage()
    request = storage.get_request(request_id)

    if request['status'] != 'CREATED_IN_GAZELLE':
        raise HTTPException(400, "Demande non validée Gazelle")

    # Trouver le piano Gazelle
    piano_id = await get_gazelle_piano_id(request_id)
    if not piano_id:
        raise HTTPException(404, "Piano Gazelle non trouvé")

    # Générer/mettre à jour tournée
    generator = TourGenerator()
    result = generator.generate_tour_from_request(
        request_id=request_id,
        technician_id=request['technician_id'],
        appointment_date=request['appointment_date'],
        room=request['room']
    )

    return result
```

---

### 3. Liaison Bidirectionnelle: Piano ↔ Demande

#### A. Piano marqué "Complété" → Demande "Complété"

**Localisation**: Hook dans `vincent_dindy.py` (ou nouveau fichier PDA-spécifique)

```python
@router.put("/pianos/{piano_id}")
async def update_piano_status(piano_id: str, status: str):
    """
    Met à jour le statut d'un piano dans une tournée.

    NOUVEAU: Si le piano est lié à une demande PDA, synchroniser le statut.
    """
    # Mise à jour normale du piano
    storage = get_storage()
    storage.update_piano_status(piano_id, status)

    # NOUVEAU: Vérifier si ce piano est lié à une demande PDA
    piano_updates = storage.get_piano_updates(piano_id)
    pda_request_id = piano_updates.get('pda_request_id')

    if pda_request_id and status == 'completed':
        # Synchroniser la demande PDA
        manager = EventManager(storage)
        manager.update_cell(
            request_id=pda_request_id,
            field='status',
            value='COMPLETED'
        )

        logging.info(f"✅ Demande PDA {pda_request_id} marquée COMPLETED (piano {piano_id})")

    return {"success": True}
```

#### B. Piano ajouté manuellement → Demande créée automatiquement

**Localisation**: Hook dans `add_piano_to_tour` (nouveau)

```python
async def add_piano_to_tour_pda(
    tour_id: str,
    piano_id: str,
    institution: str = "place-des-arts",
    create_empty_request: bool = True
):
    """
    Ajoute un piano à une tournée PDA.

    NOUVEAU: Si create_empty_request=True, créer une demande PDA vide liée.
    """
    # Ajouter le piano normalement
    storage = get_storage()
    storage.add_piano_to_tour(tour_id, piano_id)

    # NOUVEAU: Créer une demande PDA vide si demandé
    if create_empty_request and institution == "place-des-arts":
        # Récupérer infos de la tournée
        tour = storage.get_tour(tour_id)

        # Récupérer infos du piano
        piano = await get_piano_info(piano_id)

        # Créer demande vide
        request_data = {
            "id": f"pda_auto_{piano_id}_{int(time.time())}",
            "request_date": datetime.utcnow().date().isoformat(),
            "appointment_date": tour.get('date'),  # Date de la tournée
            "room": piano.get('location', ''),
            "piano": piano.get('make', ''),
            "technician_id": tour.get('technician_id'),
            "status": "MANUAL_ADD",  # Nouveau statut
            "notes": f"Ajouté manuellement à la tournée {tour.get('name')}",
            "tour_id": tour_id
        }

        manager = EventManager(storage)
        manager.create_request(request_data)

        # Lier le piano à la demande
        storage.update_piano(piano_id, {'pda_request_id': request_data['id']})

        logging.info(f"✅ Demande PDA auto-créée pour piano manuel {piano_id}")

    return {"success": True}
```

---

## 🗄️ Modifications Base de Données

### Tables existantes à modifier:

#### 1. `place_des_arts_requests`
```sql
ALTER TABLE place_des_arts_requests
ADD COLUMN tour_id TEXT,  -- Lien vers vincent_dindy_tournees
ADD COLUMN auto_generated BOOLEAN DEFAULT FALSE;  -- Indique si créée auto

CREATE INDEX idx_pda_requests_tour ON place_des_arts_requests(tour_id);
```

#### 2. `vincent_dindy_piano_updates` (ou nouvelle table PDA)
```sql
ALTER TABLE vincent_dindy_piano_updates
ADD COLUMN pda_request_id TEXT,  -- Lien vers place_des_arts_requests
ADD COLUMN institution TEXT DEFAULT 'vincent-dindy';

CREATE INDEX idx_piano_updates_pda ON vincent_dindy_piano_updates(pda_request_id);
CREATE INDEX idx_piano_updates_inst ON vincent_dindy_piano_updates(institution);
```

#### 3. `vincent_dindy_tournees`
```sql
ALTER TABLE vincent_dindy_tournees
ADD COLUMN institution TEXT DEFAULT 'vincent-dindy',
ADD COLUMN auto_generated BOOLEAN DEFAULT FALSE;

CREATE INDEX idx_tournees_inst ON vincent_dindy_tournees(institution);
```

---

## 🔄 Workflow Complet (Automatisé)

### Scénario 1: Nouvelle demande PDA → Tournée auto

```
1. Louise importe email Place des Arts
   ├─ Demandes créées: status='PENDING'
   └─ Affichées dans PlaceDesArtsDashboard

2. Louise assigne technicien + crée RV dans Gazelle
   ├─ Statut change: 'PENDING' → 'ASSIGN_OK'
   └─ Trigger: Validation automatique

3. [AUTO] Validation Gazelle (toutes les 5 min ou webhook)
   ├─ Cherche RV dans Gazelle (via pda_validation.py)
   ├─ Si trouvé: status='CREATED_IN_GAZELLE'
   └─ Trigger: Génération de tournée

4. [AUTO] Génération de tournée
   ├─ TourGenerator.generate_tour_from_request()
   ├─ Cherche/crée tournée "RV PdA-Nick-2026-01-15"
   ├─ Ajoute piano à la tournée (status='proposed')
   └─ Lie demande ↔ piano (via tour_id et pda_request_id)

5. Nick voit la tournée dans NickDashboard
   ├─ Tournée auto-générée visible
   ├─ Pianos listés avec notes de la demande
   └─ Clic sur piano → Marquer "Complété"

6. [AUTO] Sync bidirectionnelle
   ├─ Piano marqué 'completed' dans tournée
   ├─ Demande PDA passe à 'COMPLETED' automatiquement
   └─ Louise voit le statut à jour dans PlaceDesArtsDashboard
```

### Scénario 2: Ajout manuel de piano → Demande créée

```
1. Nick ajoute manuellement piano PDA à une tournée
   ├─ Via NickDashboard ou VDI_ManagementView
   └─ Trigger: Création demande auto

2. [AUTO] Création demande PDA vide
   ├─ Demande créée: status='MANUAL_ADD'
   ├─ Room = location du piano
   ├─ Date = date de la tournée
   └─ Notes = "Ajouté manuellement"

3. Louise voit la nouvelle demande
   ├─ Peut compléter les détails (for_who, requester, etc.)
   └─ Peut facturer normalement
```

---

## 📦 Standardisation pour UniversalManagementView

### Architecture cible:

```
UniversalManagementView (nouveau composant)
├─ Props:
│  ├─ institution: "vincent-dindy" | "place-des-arts" | "orford"
│  ├─ enableAutoBridge: boolean (PDA only)
│  └─ tourConfig: { nameFormat, autoGen, etc. }
│
├─ Hooks personnalisables:
│  ├─ onPianoStatusChange(piano, newStatus)
│  │  └─ Si institution=PDA → Sync demande
│  ├─ onPianoAdded(piano, tourId)
│  │  └─ Si institution=PDA → Créer demande
│  └─ onTourCreated(tour)
│     └─ Si institution=PDA → Lier aux demandes
│
└─ Services institution-specific:
   ├─ VDITourService (existant)
   ├─ PDATourService (nouveau - avec pont auto)
   └─ OrfordTourService (futur)
```

### Exemple d'utilisation:

```jsx
// PlaceDesArtsDashboard.jsx
<UniversalManagementView
  institution="place-des-arts"
  enableAutoBridge={true}
  tourConfig={{
    nameFormat: "RV PdA-{tech}-{date}",
    autoGenerate: true,
    syncWithRequests: true
  }}
  onPianoStatusChange={(piano, status) => {
    // Sync automatique demande PDA
    if (status === 'completed' && piano.pda_request_id) {
      updateRequestStatus(piano.pda_request_id, 'COMPLETED')
    }
  }}
/>
```

---

## 🛠️ Plan d'Implémentation

### Phase 1: Validation Auto (1-2h)
- [ ] Améliorer `/sync-manual` pour retourner `ready_for_tour`
- [ ] Ajouter webhook/polling pour déclenchement auto
- [ ] Tester avec demandes existantes

### Phase 2: Génération Tournée (2-3h)
- [ ] Créer `TourGenerator` service
- [ ] Implémenter `generate_tour_from_request()`
- [ ] Créer endpoint `/auto-generate-tour`
- [ ] Modifier schéma DB (ajouter colonnes)
- [ ] Tester création/mise à jour tournées

### Phase 3: Sync Bidirectionnelle (2h)
- [ ] Hook piano→demande (statut complété)
- [ ] Hook piano ajouté→demande créée
- [ ] Tests E2E du workflow complet

### Phase 4: UI Frontend (1h)
- [ ] Badge "Tournée créée" dans PlaceDesArtsDashboard
- [ ] Lien demande→tournée (cliquable)
- [ ] Indicateur "Auto-généré" dans NickDashboard

### Phase 5: Standardisation (2-3h)
- [ ] Créer `UniversalManagementView`
- [ ] Migrer VDI vers le composant universel
- [ ] Migrer PDA vers le composant universel
- [ ] Tests de régression

**Total estimé**: 8-11 heures

---

## 🎯 Métriques de Succès

1. **Automatisation**: 90%+ des demandes validées génèrent une tournée sans intervention manuelle
2. **Sync**: 100% des pianos complétés synchronisent la demande associée
3. **Réutilisabilité**: Code partagé entre VDI/PDA via `UniversalManagementView`
4. **Performance**: Génération de tournée < 500ms
5. **UX**: Louise gagne 10+ min/jour en workflow automatisé

---

## 📚 Références

### Code existant:
- [place_des_arts.py](../api/place_des_arts.py) - Routes API PDA
- [pda_validation.py](../assistant-v6/modules/assistant/services/pda_validation.py) - Validation RV Gazelle
- [VDI_ManagementView.jsx](../frontend/src/components/vdi/VDI_ManagementView.jsx) - Gestion tournées VDI
- [vincent_dindy.py](../api/vincent_dindy.py) - Routes API VDI (modèle pour PDA)

### Tables Supabase:
- `place_des_arts_requests` - Demandes PDA
- `vincent_dindy_tournees` - Tournées techniques
- `vincent_dindy_piano_updates` - Modifications pianos
- `gazelle_appointments` - Cache RV Gazelle

---

**Prochaine étape**: Validation du design avec Allan avant implémentation.
