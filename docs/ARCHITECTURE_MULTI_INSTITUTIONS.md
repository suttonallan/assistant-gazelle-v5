# Architecture multi-institutions

## Vue d'ensemble

Ce document décrit l'architecture pour supporter plusieurs institutions (Vincent-d'Indy, Place des Arts, etc.) tout en maintenant la compatibilité avec le système actuel.

## Structure des données

### Table `institutions` (Supabase)
```sql
CREATE TABLE institutions (
  id TEXT PRIMARY KEY,
  nom TEXT NOT NULL,
  gazelle_location_name TEXT, -- Nom de la location dans Gazelle
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Données initiales
INSERT INTO institutions (id, nom, gazelle_location_name) VALUES
  ('inst_vincent_dindy', 'Vincent-d''Indy', 'Vincent-d''Indy'),
  ('inst_place_des_arts', 'Place des Arts', 'Place des Arts');
```

### Table `tournees_accords` (modification)
```sql
ALTER TABLE tournees_accords
ADD COLUMN institution_id TEXT REFERENCES institutions(id) DEFAULT 'inst_vincent_dindy';
```

## Flux de synchronisation Gazelle

### Par institution
1. Nick crée une tournée et sélectionne une institution
2. L'API charge les pianos depuis Gazelle filtrés par `location`
3. Les modifications sont sauvegardées avec référence à l'institution
4. Chaque institution a son propre ensemble de pianos

### Endpoint API
```python
@router.get("/pianos/institution/{institution_id}")
async def get_pianos_by_institution(institution_id: str):
    # 1. Récupérer l'institution depuis Supabase
    institution = storage.get_data("institutions", filters={"id": institution_id})

    # 2. Charger les pianos depuis Gazelle avec filtre location
    pianos = gazelle_client.get_pianos(location=institution['gazelle_location_name'])

    # 3. Retourner les pianos
    return {"pianos": pianos, "institution": institution}
```

## Interface utilisateur

### Dashboard Nick - Création de tournée
```javascript
// Ajouter sélection d'institution
const [institutions, setInstitutions] = useState([])
const [newTournee, setNewTournee] = useState({
  nom: '',
  institution_id: 'inst_vincent_dindy', // Défaut
  date_debut: '',
  date_fin: '',
  notes: ''
})

// Charger les institutions
useEffect(() => {
  fetch('/api/institutions/list')
    .then(res => res.json())
    .then(data => setInstitutions(data.institutions))
}, [])

// Dans le formulaire
<select
  value={newTournee.institution_id}
  onChange={(e) => setNewTournee({...newTournee, institution_id: e.target.value})}
>
  {institutions.map(inst => (
    <option key={inst.id} value={inst.id}>{inst.nom}</option>
  ))}
</select>
```

### VincentDIndyDashboard - Filtrage par institution
```javascript
// Accepter institutionId comme prop
const VincentDIndyDashboard = ({ currentUser, tourneeId, institutionId = 'inst_vincent_dindy' }) => {

  // Charger les pianos filtrés par institution
  const loadPianosFromAPI = async () => {
    const url = institutionId
      ? `${API_URL}/pianos/institution/${institutionId}`
      : `${API_URL}/pianos` // Fallback pour compatibilité

    const data = await getPianos(url)
    setPianos(data.pianos || [])
  }
}
```

## Migration progressive

### Phase 1: Infrastructure (sans UI)
- ✅ Créer table `institutions`
- ✅ Ajouter colonne `institution_id` aux tournées
- ✅ Créer endpoint API `/institutions/list`
- ✅ Créer endpoint API `/pianos/institution/{id}`

### Phase 2: Interface (compatibilité)
- ✅ Ajouter sélecteur institution dans formulaire tournée
- ✅ Valeur par défaut = Vincent-d'Indy
- ✅ Filtrer pianos selon institution sélectionnée
- ✅ Tout fonctionne comme avant si aucune sélection

### Phase 3: Synchronisation Gazelle
- ✅ Configurer mapping institution ↔ location Gazelle
- ✅ Synchroniser pianos par institution
- ✅ Permettre ajout de nouvelles institutions

## Compatibilité arrière

**IMPORTANT**: Le système actuel continue de fonctionner sans modification:
- Si `institution_id` n'est pas spécifié → Vincent-d'Indy par défaut
- Si `tourneeId` n'est pas fourni → affiche tous les pianos (comportement actuel)
- L'interface Vincent-d'Indy reste identique pour l'admin

## Exemple de flux complet

1. Nick crée une tournée "Place des Arts - Janvier 2025"
2. Sélectionne institution "Place des Arts"
3. Clique sur "🎹 Voir les pianos"
4. Le dashboard charge uniquement les pianos de Place des Arts depuis Gazelle
5. Nick peut gérer cette tournée comme Vincent-d'Indy
6. Les modifications sont isolées par institution

## Questions ouvertes

1. **Permissions**: Nick peut-il créer des tournées pour toutes les institutions ?
2. **Inventaire**: L'inventaire technicien est-il partagé ou par institution ?
3. **Alertes**: Les alertes RV doivent-elles être filtrées par institution ?
