# Distinction Client vs Contact - Chat Intelligent

## 🎯 Principe Fondamental

**PRIORITÉ AU CONTACT** - La personne physique rencontrée sur place.

---

## 📋 Règles d'Affichage

### Niveau 1 (Cards - Vue Liste)

**Affichage Principal:**
```
M. Jean Tremblay          ← CONTACT (personne rencontrée)
📍 Rosemont (H2G)
🎹 Yamaha U1
```

**Si Client différent:**
```
M. Jean Tremblay
Facturer à: École de Musique XYZ    ← Mention discrète
📍 Rosemont (H2G)
```

### Niveau 2 (Drawer - Détails)

**Section 1: Sur Place (Contact)**
```
👤 SUR PLACE
M. Jean Tremblay
📞 514-xxx-xxxx
📍 4520 rue St-Denis, Montréal H2G 2J8
🔑 Code: 1234#
🦴 Chien: Max (golden retriever)
🅿️  Stationnement: Rue, zone payante
```

**Section 2: Facturation (Client)**
```
💼 FACTURATION
École de Musique XYZ
Solde impayé: 450$
Dernier paiement: 15 nov 2024
```

---

## 🔧 Implémentation Technique

### Tables Supabase

```sql
-- Table gazelle_contacts (personnes physiques)
CREATE TABLE gazelle_contacts (
    external_id TEXT PRIMARY KEY,
    first_name TEXT,
    last_name TEXT,
    phone TEXT,
    email TEXT,

    -- Infos "sur place"
    access_code TEXT,
    dog_name TEXT,
    parking_info TEXT,
    special_notes TEXT,

    -- Lien au client (facturation)
    client_id TEXT REFERENCES gazelle_clients(external_id)
);

-- Table gazelle_locations (adresses physiques)
CREATE TABLE gazelle_locations (
    id UUID PRIMARY KEY,
    contact_id TEXT REFERENCES gazelle_contacts(external_id),
    street TEXT,
    municipality TEXT,
    postal_code TEXT,
    region TEXT,
    notes TEXT
);

-- Table gazelle_appointments (rendez-vous)
ALTER TABLE gazelle_appointments ADD COLUMN contact_id TEXT REFERENCES gazelle_contacts(external_id);
ALTER TABLE gazelle_appointments ADD COLUMN location_id UUID REFERENCES gazelle_locations(id);
```

### Logique de Priorité

```python
def get_display_name(appointment):
    """
    Retourne le nom à afficher (TOUJOURS le contact en priorité).
    """
    # 1. Contact (priorité absolue)
    contact = appointment.get("contact")
    if contact:
        first_name = contact.get("first_name", "")
        last_name = contact.get("last_name", "")
        if first_name or last_name:
            return f"{first_name} {last_name}".strip()

    # 2. Client (fallback si pas de contact)
    client = appointment.get("client")
    if client:
        # Pour un client, vérifier si nom de personne ou entreprise
        company_name = client.get("company_name")
        if company_name:
            return company_name

    # 3. Dernier recours
    return "Contact non spécifié"


def get_billing_info(appointment):
    """
    Retourne les infos de facturation (client).
    Retourne None si contact == client.
    """
    contact = appointment.get("contact")
    client = appointment.get("client")

    # Si le contact EST le client, pas de mention séparée
    if contact and client:
        contact_external_id = contact.get("external_id")
        client_external_id = client.get("external_id")

        if contact_external_id == client_external_id:
            return None  # Même entité

    # Client différent du contact
    if client:
        return {
            "name": client.get("company_name"),
            "balance_due": client.get("balance_due"),
            "last_payment": client.get("last_payment_date")
        }

    return None
```

---

## 🔐 Sécurité des Codes d'Accès

**RÈGLE CRITIQUE:** Les codes d'accès sont TOUJOURS liés à l'**adresse physique** (location), jamais au client.

### Exemple Dangereux à Éviter:

```python
# ❌ MAUVAIS - Code lié au client
client = get_client(client_id)
access_code = client.access_code  # FAUX! Le siège social peut être ailleurs

# ✅ BON - Code lié à la location
location = get_location(appointment.location_id)
access_code = location.access_code  # Bon! C'est le code de CET endroit
```

### Structure Recommandée:

```python
class LocationSecurityInfo:
    """
    Infos de sécurité liées à UNE adresse physique.
    """
    location_id: str
    address: str  # Pour confirmer visuellement

    access_code: Optional[str]
    access_code_type: str  # "door", "building", "gate"
    access_instructions: Optional[str]  # "Sonner chez Mme Roy au 2e"

    dog_name: Optional[str]
    dog_breed: Optional[str]
    dog_notes: Optional[str]  # "Très gentil, laisser entrer sans frapper"

    parking_type: str  # "street", "driveway", "garage", "lot"
    parking_notes: Optional[str]

    special_access_notes: Optional[str]  # Ascenseur de service, etc.
```

---

## 📱 Wireframe UI

### Card (Niveau 1)

```
┌────────────────────────────────────────┐
│ ⏰ 09:00 - 11:00          🏷️ Nouveau   │
│                                        │
│ M. Jean Tremblay                       │
│ Facturer à: École de Musique XYZ       │  ← Discret, gris clair
│                                        │
│ 📍 Rosemont (H2G)                      │
│ 4520 rue St-Denis                      │
│                                        │
│ 🎹 Yamaha U1 (Droit)                   │
│                                        │
│ 📋 Apporter cordes #3                  │
└────────────────────────────────────────┘
```

### Drawer (Niveau 2)

```
┌────────────────────────────────────────┐
│ M. Jean Tremblay                    ✕  │
│ ────────────────────────────────────── │
│                                        │
│ 👤 SUR PLACE                           │
│ ────────────────────────────────────── │
│ 📞 514-555-1234                        │
│ 📍 4520 rue St-Denis                   │
│    Montréal H2G 2J8                    │
│                                        │
│ 🔑 Code: 1234#                         │
│ 🦴 Chien: Max (golden retriever)       │
│    Très gentil, laisser entrer         │
│                                        │
│ 🅿️  Stationnement: Rue, zone payante   │
│                                        │
│ ────────────────────────────────────── │
│                                        │
│ 💼 FACTURATION                         │
│ ────────────────────────────────────── │
│ École de Musique XYZ                   │
│ Solde impayé: 450,00$                  │
│ Dernier paiement: 15 nov 2024          │
│                                        │
│ ────────────────────────────────────── │
│                                        │
│ 📖 HISTORIQUE                          │
│ Dernière visite le 15 nov 2024...      │
│                                        │
└────────────────────────────────────────┘
```

---

## 🎨 Style Visuel

### Hiérarchie d'Importance

1. **Contact (Principal)** - Font 18px, Bold, Noir
2. **Client (Facturation)** - Font 12px, Regular, Gris 600
3. **Adresse** - Font 14px, Regular, Gris 800
4. **Codes d'accès** - Font 14px, Monospace, Orange (sécurité)

### Codes Couleur

```css
.contact-name {
  font-size: 18px;
  font-weight: 700;
  color: #1a202c;
}

.billing-client {
  font-size: 12px;
  color: #718096;
  font-style: italic;
}

.access-code {
  font-family: 'Monaco', monospace;
  color: #dd6b20;
  background: #fef5e7;
  padding: 4px 8px;
  border-radius: 4px;
}

.section-header {
  font-size: 14px;
  font-weight: 600;
  color: #2d3748;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
```

---

## 🔄 Migration V5 → V6

### Phase 1: Enrichissement V5 (Temporaire)

Puisque les données actuelles n'ont pas de structure Contact/Client séparée:

```python
# Hack temporaire pour V5
def extract_contact_from_v5(appointment):
    """
    Extrait les infos 'contact' depuis les champs V5 actuels.
    """
    # Dans V5, on suppose que le "client" est en fait le contact
    client = appointment.get("client") or {}

    return {
        "name": client.get("company_name"),  # Peut être un nom de personne
        "phone": client.get("phone"),
        "address": {
            "street": client.get("default_location_street"),
            "municipality": client.get("default_location_municipality"),
            "postal_code": client.get("default_location_postal_code")
        }
    }


def extract_billing_from_v5(appointment):
    """
    Pour V5, on n'a pas de client séparé.
    Retourner None (pas d'affichage facturation séparée).
    """
    return None
```

### Phase 2: Tables V6 Complètes

Avec le Reconciler V6, les relations seront normalisées:

```
Appointment
  → Contact (personne physique)
     → Location (adresse avec codes)
     → Client (facturation)
```

---

## ✅ Checklist Implémentation

- [ ] Créer table `gazelle_contacts`
- [ ] Créer table `gazelle_locations`
- [ ] Ajouter colonnes `contact_id`, `location_id` à `gazelle_appointments`
- [ ] Modifier `_map_to_overview()` pour prioriser contact
- [ ] Modifier `_map_to_comfort_info()` pour utiliser location
- [ ] Ajouter `billing_info` au schema `AppointmentDetail`
- [ ] Mettre à jour UI (Card + Drawer)
- [ ] Ajouter tests pour distinction Contact/Client
- [ ] Documentation utilisateur

---

## 📝 Notes de Conception

### Pourquoi cette distinction?

**Exemple réel:**
- **Contact:** M. Jean Tremblay, 514-555-1234, 4520 rue St-Denis
- **Client:** École de Musique XYZ, 5000 boulevard Saint-Laurent (siège social)

Le technicien a besoin:
1. Du nom de **Jean** (personne à rencontrer)
2. De l'adresse de **Jean** (où aller)
3. Du code d'accès de **l'immeuble de Jean**
4. De savoir que **l'école** paie la facture (pas Jean personnellement)

Si on confond Client/Contact:
- ❌ Technicien cherche l'école au 5000 boulevard → MAUVAISE adresse
- ❌ Code d'accès du siège social → NE FONCTIONNE PAS chez Jean
- ❌ Appelle l'école au lieu de Jean → Personne ne répond

### Cas d'Usage Multiples

1. **Particulier = Client = Contact**
   - M. Dupont possède son piano
   - Affichage: "M. Dupont"
   - Pas de mention "Facturer à"

2. **École/Institution**
   - Contact: M. Tremblay (prof)
   - Client: École XYZ
   - Affichage: "M. Tremblay" + "Facturer à: École XYZ"

3. **Entreprise avec Multiples Contacts**
   - Contact A: Salle 301 (Mme Roy)
   - Contact B: Salle 102 (M. Lee)
   - Client: Université de Montréal
   - Chaque contact a SON code, SON adresse, SON chien

---

**Status:** 📋 Spécification complète
**Next:** Implémentation V6 avec tables normalisées
