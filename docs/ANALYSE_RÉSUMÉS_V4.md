# 📊 ANALYSE - RÉSUMÉS V4 (Comment ça marchait)

**Date:** 2025-12-15
**Par:** Claude Code (Windows) - Analyse du code V4
**Pour:** Cursor Mac
**Sources:**
- `app/technician_day_summary.py` (548 lignes)
- `app/conversational_queries.py`
- `app/conversational_parser.py`

---

## 🎯 CE QU'ALLAN DEMANDAIT EN V4

### Types de résumés supportés:

1. **"Résume ma journée"** / **".mes rv"**
   - Résumé des rendez-vous du jour
   - Calcul automatique des trajets avec Google Maps
   - Temps de déplacement estimés
   - Heure de départ/arrivée pour chaque RV
   - Matériel à préparer (extrait des notes)

2. **"Résume ma semaine"**
   - Vue d'ensemble de tous les RV de la semaine
   - Statistiques agrégées

3. **"Résumé pour [client]"** (ex: "Résumé pour Michelle")
   - Historique complet du client
   - Tous les pianos du client
   - Derniers rendez-vous
   - Notes importantes

---

## 📊 COMMENT ÇA FONCTIONNAIT (Architecture V4)

### Fichier Principal: `technician_day_summary.py`

#### Fonction Centrale: `generate_day_summary()`

```python
def generate_day_summary(
    technician_id: str,  # Ex: "usr_HcCiFk7o0vZ9xAI0" (Nicolas)
    date: datetime,       # Date cible
    db_conn_str: str      # Connexion SQL Server
) -> Dict:
```

**Ce qu'elle fait:**

1. **Récupère les rendez-vous du jour** depuis SQL Server
2. **Pour chaque rendez-vous:**
   - Client name (CompanyName OU FirstName + LastName)
   - Piano (Make + Model + Location)
   - Heure début/fin
   - Description du service
   - Notes importantes
   - Statut confirmation

3. **Calcule les trajets** avec Google Maps API
   - Temps de trajet entre chaque RV
   - Distance en km
   - Heure de départ nécessaire (avec buffer de 5 min)
   - Trajet retour à la maison

4. **Extrait les rappels** des notes
   - Cherche "apporter", "kit", "pièces", "outils", "vérifier", "important"
   - Retourne max 5 rappels par RV

5. **Génère statistiques globales**
   - Temps total de trajet
   - Distance totale
   - Heure retour estimée à la maison

---

## 🔍 REQUÊTE SQL UTILISÉE

### Pour récupérer les rendez-vous:

```sql
SELECT
    a.Id,
    a.ClientId,
    a.PianoId,
    a.Description,
    CONVERT(VARCHAR(33), a.StartAt, 127) AS StartAtISO,  -- Format ISO
    a.Duration,
    a.Notes,
    a.ConfirmedByClient,
    c.CompanyName,                 -- Nom compagnie
    c.FirstName,                   -- OU prénom contact
    c.LastName,                    -- OU nom contact
    p.Make AS PianoMake,           -- Marque piano (Steinway, Yamaha...)
    p.Model AS PianoModel,         -- Modèle (D, C7...)
    p.Location AS PianoLocation,   -- Adresse physique
    p.Notes AS PianoNotes          -- Notes sur le piano
FROM Appointments a
LEFT JOIN Clients c ON a.ClientId = c.Id
LEFT JOIN Pianos p ON a.PianoId = p.Id
WHERE
    CAST(a.StartAt AS DATETIME) >= ?        -- Début de journée (00:00)
    AND CAST(a.StartAt AS DATETIME) < ?     -- Fin de journée (23:59)
    AND a.TechnicianId = ?                  -- ID technicien
    AND a.AppointmentStatus = 'ACTIVE'      -- Seulement actifs
ORDER BY a.StartAt                          -- Ordre chronologique
```

**Paramètres:**
- `?` = `date.replace(hour=0, minute=0, second=0)`
- `?` = `date.replace(hour=0, minute=0, second=0) + timedelta(days=1)`
- `?` = `technician_id` (ex: "usr_HcCiFk7o0vZ9xAI0")

---

## 🗺️ CALCUL DES TRAJETS (Google Maps)

### Configuration requise:

```python
# Variables d'environnement (.env)
GOOGLE_MAPS_API_KEY=AIzaSy...   # Clé API Google Maps
ALLAN_HOME_ADDRESS=123 rue X, Montréal
NICOLAS_HOME_ADDRESS=456 rue Y, Laval
JEANPHILIPPE_HOME_ADDRESS=789 rue Z, Montréal
```

### Fonction: `get_directions(origin, destination, departure_time)`

**API utilisée:** Google Maps Distance Matrix API

```python
url = "https://maps.googleapis.com/maps/api/distancematrix/json"
params = {
    'origins': "123 rue X, Montréal",        # Adresse départ
    'destinations': "456 rue Y, Laval",      # Adresse arrivée
    'key': GOOGLE_MAPS_API_KEY,
    'units': 'metric',                       # Kilomètres
    'language': 'fr',                        # Français
    'departure_time': timestamp              # Pour trafic en temps réel
}
```

**Réponse parsée:**
```json
{
    "duration_seconds": 1800,        // 30 minutes
    "duration_text": "30 mins",
    "distance_meters": 25000,        // 25 km
    "distance_text": "25.0 km",
    "error": null
}
```

### Algorithme de calcul:

```python
# Pour chaque rendez-vous:
previous_location = tech_home_address  # Départ maison

for appt in appointments:
    # 1. Récupérer adresse client (de Piano.Location ou Client.Address)
    client_address = get_client_address(appt.client_id)

    # 2. Calculer trajet depuis location précédente
    directions = get_directions(
        previous_location,
        client_address,
        departure_time=previous_end_time
    )

    # 3. Calculer heure de départ nécessaire
    travel_minutes = directions['duration_seconds'] / 60
    travel_minutes += 5  # Buffer de sécurité

    departure_time = appt.start_time - timedelta(minutes=travel_minutes)

    # 4. Mettre à jour pour prochain RV
    previous_location = client_address
    previous_end_time = appt.start_time + timedelta(minutes=appt.duration)

# Calculer retour à la maison après dernier RV
final_return = get_directions(previous_location, tech_home_address)
```

---

## 📝 EXTRACTION DES RAPPELS

### Fonction: `extract_reminders_from_notes(notes)`

**Mots-clés recherchés:**

```python
keywords = {
    'apporter': ['apporter', 'amener', 'prendre'],
    'kit': ['kit entretien', 'kit', 'trousse'],
    'pièces': ['pièces', 'pièce', 'rondelle', 'vis', 'marteau'],
    'outils': ['outils', 'outil', 'tournevis', 'clé'],
    'vérifier': ['vérifier', 'vérif', 'check'],
    'important': ['important', 'attention', 'urgent']
}
```

**Exemple de notes:**
```
"Piano désaccordé. Apporter kit d'entretien complet.
Vérifier état des marteaux. Important: client VIP."
```

**Rappels extraits:**
```
[
    "Apporter kit d'entretien complet",
    "Vérifier état des marteaux",
    "Important: client VIP"
]
```

---

## 📄 FORMAT DE SORTIE V4

### Résumé Basique (format texte):

```
📅 RÉSUMÉ DE JOURNÉE - Nicolas
Date: 15 décembre 2025

🚗 DÉPART DE LA MAISON: 8h25

📍 RENDEZ-VOUS #1 - 9h00
   Client: Yannick Nézet-Séguin
   Piano: Steinway & Sons D
   Description: Accord annuel
   Durée: 90 minutes
   Adresse: 123 Rue Mozart, Montréal, H2X 1Y5
   ⚠️ Rappels: Apporter diapason A=442 Hz
   ✅ Confirmé

   🚗 Départ: 8h25 (35 mins de trajet, 28.5 km)
   🏁 Arrivée estimée: 9h00
   🏁 Fin estimée: 10h30

📍 RENDEZ-VOUS #2 - 11h30
   Client: Université de Montréal
   Piano: Yamaha C7
   Description: Réparation pédale sostenuto
   Durée: 90 minutes
   Adresse: 2900 Boulevard Édouard-Montpetit, Salle Pollack
   ⚠️ Rappels: Apporter kit pédale Yamaha
   ✅ Confirmé

   🚗 Départ: 11h05 (25 mins de trajet, 12.3 km)
   🏁 Arrivée estimée: 11h30
   🏁 Fin estimée: 13h00

📍 RENDEZ-VOUS #3 - 14h00
   Client: Studio XYZ Recording
   Piano: Kawai RX3
   Description: Expertise pré-achat
   Durée: 60 minutes
   Adresse: 456 Rue Saint-Laurent, local 300
   ⚠️ Rappels: Apporter appareil photo, formulaire expertise
   ⏳ Non confirmé

   🚗 Départ: 13h20 (40 mins de trajet, 18.2 km)
   🏁 Arrivée estimée: 14h00
   🏁 Fin estimée: 15h00

📊 RÉSUMÉ
   Temps total de trajet: 100 minutes
   Distance totale: 59.0 km
   🏠 Retour à la maison estimé: 15h45
```

### Structure JSON (pour API):

```json
{
    "success": true,
    "date": "2025-12-15",
    "technician_id": "usr_HcCiFk7o0vZ9xAI0",
    "appointments": [
        {
            "appointment_number": 1,
            "client_name": "Yannick Nézet-Séguin",
            "start_time": "09:00",
            "start_datetime": "2025-12-15T09:00:00-05:00",
            "duration_minutes": 90,
            "description": "Accord annuel",
            "piano": "Steinway & Sons D",
            "confirmed": true,
            "reminders": ["Apporter diapason A=442 Hz"],
            "address": "123 Rue Mozart, Montréal, H2X 1Y5",
            "departure_time": "08:25",
            "travel_time": "35 mins",
            "travel_distance": "28.5 km",
            "estimated_arrival": "09:00"
        },
        // ... autres RV
    ],
    "total_travel_time": 6000,  // secondes
    "total_travel_time_formatted": "100 minutes",
    "total_travel_distance": 59000,  // mètres
    "total_travel_distance_formatted": "59.0 km",
    "estimated_home_return": "15:45",
    "errors": []
}
```

---

## 🔧 ADAPTATION POUR V5 (Supabase)

### Changements nécessaires:

#### 1. Connexion Base de Données

**V4 (SQL Server):**
```python
conn = pyodbc.connect(db_conn_str)
cursor = conn.cursor()
cursor.execute(query, [start_date, end_date, technician_id])
```

**V5 (Supabase REST API):**
```python
from core.supabase_storage import SupabaseStorage

storage = SupabaseStorage()
appointments = storage.get_data(
    "gazelle_appointments",
    filters={
        "technician_id": technician_id,
        "start_time__gte": start_date.isoformat(),
        "start_time__lt": end_date.isoformat()
    },
    order="start_time.asc"
)
```

#### 2. Syntaxe SQL

**V4:**
```sql
CONVERT(VARCHAR(33), a.StartAt, 127) AS StartAtISO
CAST(a.StartAt AS DATETIME)
ISNULL(c.CompanyName, '')
```

**V5 (PostgreSQL):**
```sql
TO_CHAR(a.start_time, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS start_at_iso
a.start_time::timestamp
COALESCE(c.company_name, '')
```

#### 3. Noms de Tables/Colonnes

| V4 (SQL Server) | V5 (Supabase) |
|-----------------|---------------|
| `Appointments` | `gazelle_appointments` |
| `Clients` | `gazelle_clients` |
| `Contacts` | `gazelle_contacts` |
| `Pianos` | `gazelle_pianos` |
| `StartAt` | `start_time` |
| `CompanyName` | `company_name` |
| `FirstName` | `first_name` |
| `TechnicianId` | `technician_id` |

#### 4. Google Maps (Identique)

**✅ Aucun changement nécessaire** - Utiliser exactement la même logique:
- `GOOGLE_MAPS_API_KEY` dans .env
- Distance Matrix API
- Parsing des réponses

---

## 🎯 CE QUE CURSOR MAC DOIT IMPLÉMENTER

### Niveau 1: Résumé Basique (PRIORITÉ)

**Endpoint:** `POST /assistant/chat`

**Question:** "Résume ma journée" / ".mes rv"

**Algorithme:**

```python
async def generate_day_summary(technician_id: str, date: datetime):
    # 1. Récupérer rendez-vous
    appointments = supabase.table('gazelle_appointments')\
        .select('''
            *,
            client:client_id(company_name, first_name, last_name),
            piano:piano_id(brand, model, location, notes),
            technician:technician_id(first_name, last_name)
        ''')\
        .eq('technician_id', technician_id)\
        .gte('start_time', date.strftime('%Y-%m-%d 00:00:00'))\
        .lt('start_time', (date + timedelta(days=1)).strftime('%Y-%m-%d 00:00:00'))\
        .order('start_time')\
        .execute()

    # 2. Pour chaque RV: calculer trajets (Google Maps)
    enriched_appointments = []
    previous_location = get_technician_home(technician_id)

    for appt in appointments.data:
        # Calculer trajet
        client_address = appt['piano']['location'] or get_client_address(appt['client_id'])
        directions = get_directions(previous_location, client_address)

        # Extraire rappels
        reminders = extract_reminders_from_notes(appt['notes'])

        enriched_appointments.append({
            **appt,
            'travel_time': directions['duration_text'],
            'travel_distance': directions['distance_text'],
            'reminders': reminders,
            'departure_time': calculate_departure_time(appt['start_time'], directions['duration_seconds'])
        })

        previous_location = client_address

    # 3. Formater résumé
    return format_day_summary_text(enriched_appointments)
```

### Niveau 2: Résumé Intelligent (APRÈS)

**Avec analyse contextuelle:**
- Priorités VIP
- Alertes problèmes pianos
- Suggestions optimisation itinéraire

**Voir:** [GUIDE_RÉSUMÉS_TECHNICIENS.md](GUIDE_RÉSUMÉS_TECHNICIENS.md)

---

## 📊 DONNÉES REQUISES

### Tables Supabase nécessaires:

1. ✅ **gazelle_appointments** (⚠️ actuellement vide - besoin sync)
   - `id`, `client_id`, `technician_id`, `piano_id`
   - `start_time`, `end_time`, `duration`
   - `description`, `notes`
   - `confirmed_by_client`, `appointment_status`

2. ✅ **gazelle_clients** (1,000 enregistrements)
   - `id`, `company_name`, `first_name`, `last_name`
   - `full_address`, `email`, `phone`

3. ⚠️ **gazelle_contacts** (actuellement vide - besoin sync)
   - `id`, `client_id`
   - `first_name`, `last_name`, `role`

4. ✅ **gazelle_pianos** (924 enregistrements)
   - `id`, `client_id`
   - `brand`, `model`, `serial_number`
   - `location` (CRUCIAL pour adresses)
   - `notes`

### Variables d'environnement:

```bash
# .env V5
GOOGLE_MAPS_API_KEY=AIzaSy...          # Pour calcul trajets
ALLAN_HOME_ADDRESS=...                 # Adresse maison Allan
NICOLAS_HOME_ADDRESS=...               # Adresse maison Nicolas
JEANPHILIPPE_HOME_ADDRESS=...          # Adresse maison Jean-Philippe
```

---

## ✅ CHECKLIST MIGRATION

**Pour avoir les résumés fonctionnels comme V4:**

- [ ] 1. Synchroniser `gazelle_appointments` (BLOQUEUR)
- [ ] 2. Configurer `GOOGLE_MAPS_API_KEY` dans .env
- [ ] 3. Configurer adresses maison techniciens dans .env
- [ ] 4. Créer fonction `get_directions()` (copier V4 tel quel)
- [ ] 5. Créer fonction `extract_reminders_from_notes()` (copier V4)
- [ ] 6. Créer fonction `generate_day_summary()` (adapter SQL → Supabase)
- [ ] 7. Créer fonction `format_day_summary_text()` (copier V4)
- [ ] 8. Intégrer dans endpoint `/assistant/chat`
- [ ] 9. Tester avec données réelles
- [ ] 10. Valider avec Allan (comparer V4 vs V5)

---

## 💡 EXEMPLE D'UTILISATION V5

**Requête utilisateur:**
```bash
curl -X POST http://localhost:8000/assistant/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "question": "Résume ma journée"
  }'
```

**Réponse attendue:**
```json
{
    "response": "📅 RÉSUMÉ DE JOURNÉE - Nicolas\n\nDate: 15 décembre 2025\n\n🚗 DÉPART DE LA MAISON: 8h25\n\n📍 RENDEZ-VOUS #1 - 9h00\n...",
    "data": {
        "appointments": [...],
        "total_travel_time_formatted": "100 minutes",
        "total_travel_distance_formatted": "59.0 km",
        "estimated_home_return": "15:45"
    },
    "suggestions": [
        "💡 Tous les rendez-vous dans un rayon de 15 km",
        "⚠️ RV #3 non confirmé - appeler le client"
    ]
}
```

---

## 🎯 DIFFÉRENCE CLÉ V4 → V5

**V4:**
- Résumé **sur demande** (appelé via API)
- Format texte uniquement
- Pas d'intelligence contextuelle

**V5 (À IMPLÉMENTER):**
- Résumé **sur demande** (comme V4)
- + **Envoi automatique** le matin (email/Slack)
- + **3 niveaux de détail** (synthèse/détaillé/complet)
- + **Intelligence contextuelle** (VIP, alertes, suggestions)
- + **Optimisation itinéraire** (ordre optimal des RV)

**Voir guide complet:** [GUIDE_RÉSUMÉS_TECHNICIENS.md](GUIDE_RÉSUMÉS_TECHNICIENS.md)

---

**Créé:** 2025-12-15 12:30 EST
**Par:** Claude Code (Windows) - Analyse code V4
**Pour:** Cursor Mac
**Sources:** V4 production code (548 lignes analysées)
**Statut:** ✅ ANALYSE COMPLÈTE - PRÊT POUR IMPLÉMENTATION V5
