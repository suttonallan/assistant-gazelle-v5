# Chat Intelligent - Requêtes SQL

Documentation des requêtes SQL utilisées par le Chat Intelligent (Bridge V5/V6).

---

## Vue d'ensemble d'une Journée

### Requête Supabase (PostgREST)

```sql
SELECT
    -- Appointment
    a.external_id,
    a.appointment_date,
    a.appointment_time,
    a.notes,
    a.technicien,

    -- Client (joined)
    c.external_id as client_id,
    c.company_name,
    c.default_contact_name,
    c.default_location_street,
    c.default_location_municipality,
    c.default_location_region,

    -- Piano (joined)
    p.external_id as piano_id,
    p.make as piano_make,
    p.model as piano_model,
    p.type as piano_type,
    p.serial_number

FROM gazelle_appointments a
LEFT JOIN gazelle_clients c ON a.client_id = c.external_id
LEFT JOIN gazelle_pianos p ON a.piano_id = p.external_id

WHERE a.appointment_date = '2025-12-29'  -- Date spécifique
  AND a.technicien = 'Nicolas Lessard'   -- Optionnel: filter par technicien

ORDER BY a.appointment_time ASC;
```

### Via PostgREST (Format API)

```http
GET /gazelle_appointments?
    select=external_id,appointment_date,appointment_time,notes,technicien,
           client:client_id(external_id,company_name,default_contact_name,default_location_street,default_location_municipality,default_location_region),
           piano:piano_id(external_id,make,model,type,serial_number)
    &appointment_date=eq.2025-12-29
    &order=appointment_time.asc
```

---

## Détails d'un Rendez-vous

### Requête Complète avec Timeline

```sql
-- 1. Récupérer l'appointment
SELECT
    a.*,
    c.*,
    p.*
FROM gazelle_appointments a
LEFT JOIN gazelle_clients c ON a.client_id = c.external_id
LEFT JOIN gazelle_pianos p ON a.piano_id = p.external_id
WHERE a.external_id = 'apt_abc123';

-- 2. Récupérer timeline entries du piano
SELECT
    t.occurred_at,
    t.entry_type,
    t.title,
    t.details,
    u.first_name,
    u.last_name
FROM gazelle_timeline_entries t
LEFT JOIN users u ON t.user_id = u.id
WHERE t.piano_id = 'pno_xyz789'
ORDER BY t.occurred_at DESC
LIMIT 10;
```

### Via PostgREST

```http
-- Appointment avec relations
GET /gazelle_appointments?
    select=*,client:client_id(*),piano:piano_id(*)
    &external_id=eq.apt_abc123

-- Timeline du piano
GET /gazelle_timeline_entries?
    select=occurred_at,entry_type,title,details,user:user_id(first_name,last_name)
    &piano_id=eq.pno_xyz789
    &order=occurred_at.desc
    &limit=10
```

---

## Calculer Dernière Visite

```sql
-- Dernière visite pour un piano spécifique
SELECT
    occurred_at as last_visit_date,
    EXTRACT(DAY FROM NOW() - occurred_at) as days_since_last_visit
FROM gazelle_timeline_entries
WHERE piano_id = 'pno_xyz789'
  AND entry_type = 'SERVICE_ENTRY_MANUAL'
ORDER BY occurred_at DESC
LIMIT 1;
```

---

## Détecter Nouveau Client

```sql
-- Vérifier si premier service pour ce client
SELECT
    COUNT(*) as previous_services
FROM gazelle_timeline_entries t
JOIN gazelle_pianos p ON t.piano_id = p.external_id
WHERE p.client_id = 'cln_abc123'
  AND t.entry_type = 'SERVICE_ENTRY_MANUAL';

-- Si previous_services = 0 → nouveau client
```

---

## Alertes Actives

```sql
-- Vérifier alertes non résolues pour un client/piano
SELECT
    description,
    date_observation,
    notes
FROM maintenance_alerts
WHERE client_id = 'cln_abc123'
  AND is_resolved = FALSE
ORDER BY date_observation DESC;
```

---

## Extraction Action Items

### Via Pattern Matching (PostgreSQL)

```sql
-- Extraire "À apporter" depuis notes
SELECT
    external_id,
    substring(notes FROM 'à apporter[:\s]+([^\n]+)') as action_items_raw
FROM gazelle_appointments
WHERE appointment_date = '2025-12-29'
  AND notes ILIKE '%à apporter%';
```

### En Python (Parsing avancé)

```python
import re

def extract_action_items(notes: str) -> List[str]:
    """Extrait action items depuis notes."""
    items = []

    # Pattern "À apporter:"
    match = re.search(r'à apporter[:\s]+([^\n]+)', notes, re.IGNORECASE)
    if match:
        raw_items = match.group(1).split(',')
        items.extend([item.strip() for item in raw_items])

    # Pattern "TODO:"
    todos = re.findall(r'todo[:\s]+([^\n]+)', notes, re.IGNORECASE)
    items.extend(todos)

    return items[:5]  # Limiter
```

---

## Performance: Optimisations

### Index Recommandés

```sql
-- Pour queries fréquentes
CREATE INDEX idx_appointments_date ON gazelle_appointments(appointment_date);
CREATE INDEX idx_appointments_tech ON gazelle_appointments(technicien);
CREATE INDEX idx_timeline_piano_date ON gazelle_timeline_entries(piano_id, occurred_at DESC);
CREATE INDEX idx_timeline_type ON gazelle_timeline_entries(entry_type);
```

### Materialized View (Optionnel)

Pour améliorer performance si beaucoup de rendez-vous:

```sql
-- Vue matérialisée: appointments avec dernière visite
CREATE MATERIALIZED VIEW mv_appointments_enriched AS
SELECT
    a.external_id,
    a.appointment_date,
    a.appointment_time,
    a.client_id,
    a.piano_id,
    c.company_name,
    c.default_location_municipality as neighborhood,
    p.make as piano_make,
    p.model as piano_model,
    (
        SELECT occurred_at
        FROM gazelle_timeline_entries t
        WHERE t.piano_id = a.piano_id
          AND t.entry_type = 'SERVICE_ENTRY_MANUAL'
        ORDER BY occurred_at DESC
        LIMIT 1
    ) as last_visit_date
FROM gazelle_appointments a
LEFT JOIN gazelle_clients c ON a.client_id = c.external_id
LEFT JOIN gazelle_pianos p ON a.piano_id = p.external_id;

-- Refresh quotidien (CRON)
REFRESH MATERIALIZED VIEW mv_appointments_enriched;
```

---

## Migration V5 → V6

### Mapping des Tables

| V5 Table                  | V6 Table (Futur)           | Notes                          |
|---------------------------|----------------------------|--------------------------------|
| `gazelle_appointments`    | `appointments`             | ID Gazelle natifs              |
| `gazelle_clients`         | `clients`                  | Soft deletes, audit trail      |
| `gazelle_pianos`          | `pianos`                   | Version tracking               |
| `gazelle_timeline_entries`| `timeline_entries`         | Partitioning par mois          |
| `users`                   | `users`                    | Déjà migré (Gazelle IDs)       |

### Fonction de Transformation

```python
def map_v5_to_v6_response(v5_data: Dict) -> AppointmentOverview:
    """
    Transforme données V5 brutes en schéma standard.

    Cette fonction ISOLE la logique de transformation.
    En V6, on remplacera juste la source de données.
    """
    client = v5_data.get("client") or {}
    piano = v5_data.get("piano") or {}

    return AppointmentOverview(
        appointment_id=v5_data["external_id"],
        client_id=client.get("external_id"),
        piano_id=piano.get("external_id"),
        time_slot=v5_data.get("appointment_time", "Non spécifié"),
        date=v5_data["appointment_date"],
        client_name=client.get("company_name") or "Client inconnu",
        neighborhood=client.get("default_location_municipality") or "",
        address_short=client.get("default_location_street", "")[:50],
        piano_brand=piano.get("make"),
        piano_model=piano.get("model"),
        piano_type=piano.get("type"),
        # ... autres champs
    )
```

---

## Tests SQL

### Vérifier Données Disponibles

```sql
-- Combien de RDV pour demain?
SELECT COUNT(*)
FROM gazelle_appointments
WHERE appointment_date = CURRENT_DATE + INTERVAL '1 day';

-- Quartiers les plus fréquents
SELECT
    c.default_location_municipality,
    COUNT(*) as count
FROM gazelle_appointments a
JOIN gazelle_clients c ON a.client_id = c.external_id
WHERE a.appointment_date >= CURRENT_DATE
GROUP BY c.default_location_municipality
ORDER BY count DESC
LIMIT 10;

-- Pianos sans timeline
SELECT
    p.external_id,
    p.make,
    p.model
FROM gazelle_pianos p
LEFT JOIN gazelle_timeline_entries t ON p.external_id = t.piano_id
WHERE t.id IS NULL;
```

---

## Prochaines Étapes V6

1. **Staging Tables** - Créer `stg_appointments` pour buffer
2. **Reconciler** - Implémenter matching intelligent client/piano
3. **Incremental Sync** - Sync seulement nouveaux/modifiés
4. **Caching** - Redis pour queries fréquentes (journée du jour)
5. **Real-time** - WebSocket pour updates live

Voir [STRATEGIE_V6.md](../v6/docs/STRATEGIE_V6.md) pour détails architecture complète.
