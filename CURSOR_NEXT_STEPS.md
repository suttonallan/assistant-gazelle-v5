# Plan d'implémentation - Dashboard multi-institutions

## ✅ Ce qui est fait (Session actuelle)

### 1. Système de rapports unifié avec push Gazelle
- ✅ Endpoint `/api/vincent-dindy/reports` fonctionnel
- ✅ Sauvegarde dans Supabase (`technician_reports`)
- ✅ Push automatique vers Gazelle avec `createEvent` → `completeEvent` + `serviceHistoryNotes`
- ✅ Migration SQL : Colonne `service_history_notes` ajoutée
- ✅ Frontend envoie `piano_id` et `service_history_notes`
- ✅ Workflow Luke respecté (createEvent active → completeEvent)

### 2. Détection automatique d'alertes d'humidité
- ✅ Module `core/humidity_alert_detector.py` créé
- ✅ Détecte mots-clés : "humidité haute/basse", "dampp-chaser", "housse retirée"
- ✅ Hook intégré dans endpoint `/reports`
- ✅ Fonctionne pour 3 institutions : vincent-dindy, place-des-arts, orford

### 3. Corrections critiques
- ✅ Table `technician_reports` recréée avec bon schéma
- ✅ Types timeline corrigés (SERVICE → NOTE)
- ✅ Index `occurredAtGet` ajouté (recommandation Gamini)
- ✅ Suppression de l'appel obsolète `complete-service` dans frontend

## 🚧 À faire maintenant

### Étape 1 : Supprimer les tournées de Vincent d'Indy

**Fichier** : `frontend/src/components/VincentDIndyDashboard.jsx`

**Actions** :
1. Supprimer tout le code lié aux tournées :
   - État `tournees`, `selectedTourneeId`, `newTournee`
   - Fonctions `addPianoToTournee`, `removePianoFromTournee`, `getTourneePianos`
   - Import du composant `VDI_TourneesManager`
   - Condition d'affichage du manager de tournées

2. Simplifier la logique de sélection :
   - Utiliser `selectedIds` directement (pas de lien avec tournées)
   - Garder uniquement la coloration jaune/ambre/vert basée sur `status`

3. Nettoyer localStorage :
   - Supprimer `localStorage.getItem('tournees_accords')`

**Code à conserver** :
- Vue technicien avec statuts (pending, work_in_progress, completed)
- Filtres par étage, usage, local
- Sauvegarde des rapports vers `/api/vincent-dindy/reports`

---

### Étape 2 : Créer le dashboard Orford (copie de Vincent d'Indy)

**Fichier à créer** : `frontend/src/components/OrfordDashboard.jsx`

**Instructions** :
1. Copier `VincentDIndyDashboard.jsx` → `OrfordDashboard.jsx`
2. Remplacer toutes les références :
   - `vincent-dindy` → `orford`
   - `Vincent-d'Indy` → `Orford Musique`
   - `École Vincent-d'Indy` → `Orford Musique`

3. Props du composant :
```javascript
const OrfordDashboard = ({
  currentUser,
  initialView = 'nicolas',
  hideNickView = false,
  institution = 'orford'
}) => {
```

4. API_URL identique (endpoint unifié) :
```javascript
const API_URL = import.meta.env.VITE_API_URL || ...
```

**Intégration dans App.jsx** :
```javascript
import OrfordDashboard from './components/OrfordDashboard';

// Dans le switch institution :
case 'orford':
  return <OrfordDashboard currentUser={currentUser} initialView="nicolas" />;
```

---

### Étape 3 : Créer le dashboard Place des Arts (avec RV du jour)

**Fichiers à créer** :
1. `frontend/src/components/PlaceDesArtsDashboard.jsx`
2. `api/place_des_arts.py` (endpoint pour RV)

**Backend - Endpoint RV du jour** :

Créer dans `api/place_des_arts.py` :

```python
from fastapi import APIRouter
from core.supabase_storage import SupabaseStorage
from datetime import date

router = APIRouter(prefix="/api/place-des-arts", tags=["place-des-arts"])

@router.get("/appointments/today")
async def get_today_appointments():
    """
    Récupère les rendez-vous du jour pour Place des Arts depuis Supabase.
    Sync matinale à 7h00 via cron job.
    """
    storage = SupabaseStorage()
    today = date.today().isoformat()

    # Requête Supabase : appointments du jour pour Place des Arts
    response = storage.client.table('appointments')\
        .select('*')\
        .eq('client_id', 'cli_HbEwl9rN11pSuDEU')\  # ID Place des Arts
        .gte('start_datetime', today)\
        .lt('start_datetime', f'{today}T23:59:59')\
        .order('start_datetime')\
        .execute()

    return {
        "appointments": response.data,
        "count": len(response.data),
        "date": today
    }
```

**Frontend - PlaceDesArtsDashboard** :

Structure similaire à Vincent d'Indy MAIS :

1. **État supplémentaire** :
```javascript
const [appointments, setAppointments] = useState([]);
const [selectedAppointment, setSelectedAppointment] = useState(null);
```

2. **Chargement initial** :
```javascript
useEffect(() => {
  loadAppointments();
}, []);

const loadAppointments = async () => {
  const response = await fetch(`${API_URL}/api/place-des-arts/appointments/today`);
  const data = await response.json();
  setAppointments(data.appointments);
};
```

3. **Filtrage des pianos** :
```javascript
// Afficher SEULEMENT les pianos des rendez-vous
const pianoIds = appointments.flatMap(apt => apt.piano_ids || []);
const filteredPianos = pianos.filter(p => pianoIds.includes(p.gazelleId));
```

4. **Vues** :
   - Volet "Demandes" : Liste des RV avec horaires
   - Volet "Technicien" : Pianos des RV (même interface que VDI)

---

### Étape 4 : Cron job sync matinale PDA

**Fichier** : `core/scheduler.py`

Ajouter :
```python
from modules.sync_gazelle.sync_appointments import sync_pda_appointments_today

scheduler.add_job(
    sync_pda_appointments_today,
    trigger="cron",
    hour=7,
    minute=0,
    id="pda_morning_sync",
    timezone="America/Montreal"
)
```

**Créer** : `modules/sync_gazelle/sync_appointments.py`

```python
def sync_pda_appointments_today():
    """Sync des RV du jour pour Place des Arts à 7h00."""
    from core.gazelle_api_client import GazelleAPIClient
    from datetime import date

    client = GazelleAPIClient()
    today = date.today().isoformat()

    # Query Gazelle pour RV du jour
    query = """
    query GetTodayAppointments($clientId: String!, $date: Date!) {
      appointments(
        clientId: $clientId,
        startDateGte: $date,
        startDateLt: $date
      ) {
        nodes {
          id
          title
          start
          duration
          allEventPianos { nodes { piano { id } } }
        }
      }
    }
    """

    result = client._execute_query(query, {
        "clientId": "cli_HbEwl9rN11pSuDEU",
        "date": today
    })

    # Sauvegarder dans Supabase
    # ... (code de sauvegarde)
```

---

## 🎯 Résumé des actions

1. ✂️ **Supprimer tournées** de VincentDIndyDashboard
2. 📋 **Copier** VincentDIndyDashboard → OrfordDashboard (changement `institution` seulement)
3. 🏢 **Créer** PlaceDesArtsDashboard avec système de RV
4. ⏰ **Ajouter** cron job sync matinale PDA à 7h00

## 📝 Notes importantes

- **Backend unifié** : Endpoint `/api/{institution}/reports` fonctionne pour les 3
- **Détection alertes** : Automatique pour les 3 institutions
- **Push Gazelle** : Utilise le même bridge modulaire
- **Schéma Supabase** : Aligné avec Gazelle (`service_history_notes`)

## 🔗 Fichiers clés

- Backend rapports : `api/vincent_dindy.py` (endpoint `/reports`)
- Bridge Gazelle : `core/service_completion_bridge.py`
- Détecteur alertes : `core/humidity_alert_detector.py`
- Frontend VDI : `frontend/src/components/VincentDIndyDashboard.jsx`
- Migration SQL : `sql/fix_technician_reports_schema.sql`

---

**Date** : 2026-01-14
**Status** : Système de rapports ✅ | Dashboards multi-institutions 🚧
