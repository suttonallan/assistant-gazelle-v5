# 📊 DATA_RELATIONS.md - Carte Routière des Relations de Données

**Date création:** 2025-12-29
**Statut:** SOURCE DE VÉRITÉ UNIQUE - Ne JAMAIS coder sans consulter ce document

---

## 🎯 Pourquoi ce document existe

**PROBLÈME RÉSOLU:** Sans ce document, l'IA (et les développeurs) font des suppositions fausses sur les relations entre tables, causant des bugs comme :
- Chercher `piano_id` directement sur `appointment` (alors qu'il est NULL)
- Ignorer que les pianos sont liés au CLIENT, pas au rendez-vous
- Supposer qu'un contact = un client (alors que c'est séparé)

**RÈGLE D'OR:** Avant de coder une requête qui touche plusieurs tables, LIRE cette section.

---

## 🗺️ Carte des Relations (Vue d'ensemble)

```
┌─────────────────┐
│   Appointment   │ (Rendez-vous)
│  evt_xxxxxxx    │
└────────┬────────┘
         │
         ├─► client_external_id ──┐
         │                        │
         │                        ▼
         │              ┌──────────────────┐
         │              │     Client       │ (Entreprise/Institution)
         │              │  cli_xxxxxxx     │
         │              └────────┬─────────┘
         │                       │
         │                       ├─► company_name (ex: "SEC-Cibèle")
         │                       ├─► address, city, postal_code
         │                       │
         │                       └─► Pianos (1 client → N pianos)
         │                                 │
         │                                 ▼
         │                       ┌──────────────────┐
         │                       │      Piano       │
         │                       │  pia_xxxxxxx     │
         │                       └────────┬─────────┘
         │                                │
         │                                └─► Timeline Entries
         │                                          │
         │                                          ▼
         │                                ┌───────────────────┐
         │                                │ Timeline Entry    │
         │                                │                   │
         │                                └───────────────────┘
         │
         └─► location, notes (infos du RV)
```

---

## ✅ RÈGLES CRITIQUES (Check-list avant de coder)

### Règle 1: JAMAIS de lien direct Appointment → Piano

```python
# ❌ FAUX - Cette relation n'existe PAS dans Supabase
appointment.piano_id  # NULL la plupart du temps

# ✅ BON - Toujours passer par le Client
appointment.client_external_id → client.pianos[]
```

**Pourquoi:** Un rendez-vous est lié à un CLIENT (l'entreprise), pas à un piano spécifique. Le client peut avoir plusieurs pianos.

---

### Règle 2: Client → Pianos (relation 1-N)

```python
# ✅ BON - Récupérer TOUS les pianos d'un client
pianos = supabase.table('gazelle_pianos')\
    .select('*')\
    .eq('client_external_id', client_id)\
    .execute()

# Si plusieurs pianos:
# - Option 1: Afficher TOUS les pianos
# - Option 2: Déduire le piano depuis les notes du RV
# - Option 3: Prendre le dernier entretenu (via timeline)
```

**Cas réel:**
- Client: "SEC-Cibèle" (cli_m6YUpP2thu95fnc6)
- Pianos: [Kawai GL-10 SN:F197120]
- Notes du RV: "Piano à queue Kawai GL-10, F197120" → confirme quel piano

---

### Règle 3: Client → Timeline (historique des interventions)

**CORRECTION CRITIQUE 2025-12-29:** Les timeline entries sont liées au **CLIENT**, pas au piano individuel.

```python
# ✅ BON - Historique via CLIENT (pas piano)
timeline = supabase.table('gazelle_timeline_entries')\
    .select('entry_date,title,description,event_type')\
    .eq('client_external_id', client_id)\
    .order('entry_date', desc=True)\
    .execute()

# ❌ FAUX - piano_id est presque toujours NULL
timeline = supabase.table('gazelle_timeline_entries')\
    .eq('piano_id', piano_id)\
    .execute()
# Résultat: 0 ou 1 entrée au lieu de dizaines
```

**Colonnes correctes:**
- Date: `entry_date` (PAS `occurred_at` qui est ancien)
- Détails: `description` (PAS `details` - cette colonne n'existe pas)
- Type: `event_type` ou `entry_type`
- Lien: `client_external_id` (PAS `piano_id` qui est souvent NULL)

---

## 🔍 Cas d'Usage: Afficher l'historique d'un RV

### Scénario: Chat Intelligent - Détails du RV "SEC-Cibèle"

```python
# Étape 1: Récupérer le rendez-vous
appointment = supabase.table('gazelle_appointments')\
    .select('*, client:client_external_id(*)')\
    .eq('external_id', 'evt_xxxxx')\
    .execute()

# Étape 2: Vérifier si le RV a un client
client = appointment.data[0].get('client')
if not client:
    # Événement personnel (pas de client)
    return "Aucun historique disponible"

# Étape 3: Récupérer les pianos du client (optionnel - pour affichage)
client_id = client.get('external_id')
pianos = supabase.table('gazelle_pianos')\
    .select('external_id,make,model,serial_number')\
    .eq('client_external_id', client_id)\
    .execute()

# Étape 4: Récupérer la timeline du CLIENT (pas par piano)
timeline = supabase.table('gazelle_timeline_entries')\
    .select('entry_date,title,description,event_type')\
    .eq('client_external_id', client_id)\
    .order('entry_date', desc=True)\
    .limit(10)\
    .execute()

# Étape 5: Retourner les résultats
return {
    'pianos': pianos.data,
    'timeline': timeline.data
}
```

**Exemple de résultat (SEC-Cibèle):**
- ✅ 1 piano: Kawai GL-10 (SN: F197120)
- ✅ 6 entrées timeline (dernière: 2025-06-10)
- ✅ Détails: Accord 440hz, température 24°C, humidité 33%

---

## 🚨 Erreurs Courantes et Solutions

### Erreur 1: "Could not find a relationship 'piano_external_id'"

**Cause:** Essayer de faire `piano:piano_external_id(*)` dans le select

**Solution:** Pas de relation directe. Récupérer les pianos via le client :
```python
# Étape 1: Récupérer RV avec client
appointment = supabase.table('gazelle_appointments')\
    .select('*, client:client_external_id(*)')\
    .eq('external_id', appointment_id)\
    .execute()

# Étape 2: Récupérer pianos séparément
client_id = appointment.data[0]['client']['external_id']
pianos = supabase.table('gazelle_pianos')\
    .select('*')\
    .eq('client_external_id', client_id)\
    .execute()
```

---

### Erreur 2: "Timeline vide alors que le client existe"

**Cause 1:** Utilisation de `piano_id` au lieu de `client_external_id`
**Cause 2:** Utilisation de colonnes inexistantes (`details` au lieu de `description`)

**Solution:**
```python
# ❌ FAUX - Ces approches ne fonctionnent pas
timeline = supabase.table('gazelle_timeline_entries')\
    .select('piano_id,occurred_at,title,details')\  # Colonnes incorrectes
    .eq('piano_id', piano_id)\  # piano_id est NULL
    .execute()

# ✅ BON - Approche correcte
timeline = supabase.table('gazelle_timeline_entries')\
    .select('client_external_id,entry_date,title,description')\  # Colonnes correctes
    .eq('client_external_id', client_id)\  # Filtrer par client
    .order('entry_date', desc=True)\
    .execute()
```

**Test de validation (SEC-Cibèle):**
```python
client_id = "cli_m6YUpP2thu95fnc6"
timeline = supabase.table('gazelle_timeline_entries')\
    .select('entry_date,title,description')\
    .eq('client_external_id', client_id)\
    .execute()

print(f"Résultat: {len(timeline.data)} entrées")
# ✅ Attendu: 6 entrées
# ❌ Si 0: vérifier que vous utilisez bien client_external_id
```

---

### Erreur 3: "Afficher 'SEC-Cibèle' au lieu de 'Sophie Lambert'"

**Cause:** Confusion Client (entreprise) vs Contact (personne physique)

**Solution implémentée (2025-12-29):**

```python
# Extraction du contact depuis notes
contact_name = _extract_contact_name(notes, location)
# Pattern: "Prénom Nom" (ex: "Sophie Lambert")

institution_name = client.get("company_name")  # "SEC-Cibèle"

# Affichage:
# - Niveau 1 Card: Contact en GROS (Sophie Lambert)
# - Niveau 1 Card: Institution en italic gris ("Facturer à: SEC-Cibèle")
# - Niveau 2 Drawer: Détails complets de facturation
```

**Fichiers modifiés:**
- `api/chat/service.py` - Fonction `_extract_contact_name()` (ligne 442)
- `api/chat/schemas.py` - Nouveau champ `billing_client` (ligne 33)
- `frontend/src/components/ChatIntelligent.jsx` - Affichage dual (lignes 285-295)

---

### Erreur 4: "Notes Gazelle vides/inutiles affichées au technicien"

**Cause:** Affichage de toutes les notes auto-générées par Gazelle sans filtre

**Exemples de notes inutiles:**
- "Note Gazelle" (sans contenu)
- "An appointment was created for this client"
- "Appointment was completed"

**Solution implémentée (2025-12-29):**

```python
def _is_useful_note(text: str) -> bool:
    """Filtre les notes auto-générées par Gazelle."""

    # Patterns de notes inutiles
    useless_patterns = [
        "note gazelle",
        "an appointment was created",
        "appointment was completed"
    ]

    # Rejeter si contient un pattern inutile
    for pattern in useless_patterns:
        if pattern in text.lower():
            return False

    # Rejeter si trop courte (< 10 chars)
    return len(text.strip()) >= 10
```

**Application:**
1. **Notes confort:** Filtrées avant affichage (ne PAS tronquer si utiles)
2. **Timeline entries:** Gardées si titre OU description utile
3. **Résultat:** SEC-Cibèle passe de 6 à 4 entrées timeline (2 notes Gazelle filtrées)

**Fichier modifié:**
- `api/chat/service.py` - Fonction `_is_useful_note()` (ligne 405)
- Application dans `_map_to_comfort_info()` (ligne 619)
- Application dans `get_appointment_detail()` (ligne 388)

---

### Erreur 5: "Timeline entries affichent seulement le titre, pas la description"

**Cause:** Frontend affiche `entry.summary` (titre) mais ignore `entry.details` (description complète)

**Symptômes:**
- User voit: "Accord 440hz..." (tronqué avec ...)
- Manque: température, humidité, détails complets
- Information semble répétée (titre répété sans contexte)

**Solution:**
```javascript
// ❌ FAUX - Affiche seulement le titre
<Typography variant="body2">{entry.summary}</Typography>

// ✅ BON - Affiche titre ET description
{entry.summary && (
  <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 0.5 }}>
    {entry.summary}
  </Typography>
)}
{entry.details && (
  <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
    {entry.details}
  </Typography>
)}
```

**Schéma backend (TimelineEntry):**
- `summary`: Titre court (ex: "Accord 440hz")
- `details`: Description complète avec toutes les infos techniques

**Règle:** TOUJOURS afficher les deux champs si disponibles. Le titre seul ne suffit JAMAIS.

**Fichier:** `frontend/src/components/ChatIntelligent.jsx` (lignes 458-467)

---

## 📋 Checklist de Validation (Avant de commit)

Avant de merger du code qui touche aux relations de données :

- [ ] J'ai consulté ce document
- [ ] Je passe par `client` pour accéder aux `pianos`
- [ ] Je ne cherche PAS `piano_id` directement sur `appointment`
- [ ] J'ai vérifié que `gazelle_timeline_entries` contient des données
- [ ] J'ai testé avec un RV réel (ex: "SEC-Cibèle")
- [ ] L'historique s'affiche correctement

---

## 🔗 Documents Connexes

- `DATA_DICTIONARY.md` - Schéma complet des tables
- `IDENTITY_MAPPING.md` - Client vs Contact (à créer)
- `TIME_SYSTEM.md` - Gestion des timezones (à créer)
- `SYNC_STRATEGY.md` - Import des données Gazelle
- [REGLE_IDS_GAZELLE.md](../../docs/REGLE_IDS_GAZELLE.md) - IDs techniciens comme source de vérité

**⚠️ IMPORTANT:** Ce document est la SOURCE DE VÉRITÉ pour toutes les relations de données. Consulter AVANT toute requête multi-table.

---

## 📝 Changelog

### 2025-12-29: Création initiale + Corrections majeures

**Bugs résolus:**
1. Chat Intelligent affichait "Aucun historique" pour tous les clients
2. Utilisation de colonnes inexistantes (`details` au lieu de `description`)
3. Filtrage par `piano_id` (NULL) au lieu de `client_external_id`
4. Utilisation de `occurred_at` (ancien) au lieu de `entry_date`
5. Affichage "SEC-Cibèle" au lieu du contact humain ("Sophie Lambert")
6. Notes Gazelle inutiles polluaient l'interface technicien
7. Notes utiles étaient tronquées (manque d'info pour le technicien)
8. Frontend affichait SEULEMENT le titre (summary) sans la description complète (details)

**Solutions implémentées:**

**A. Timeline (Historique):**
- Navigation corrigée: Appointment → Client → Timeline (SANS passer par Piano)
- Colonnes corrigées: `entry_date`, `description`, `event_type`
- Filtrage corrigé: `client_external_id` au lieu de `piano_id`

**B. Contact vs Client (Affichage dual):**
- Extraction automatique contact depuis notes (pattern "Prénom Nom")
- Card Niveau 1: Contact en gros + "Facturer à: Institution" en gris
- Nouveau champ `billing_client` dans schéma

**C. Filtrage notes inutiles:**
- Fonction `_is_useful_note()` filtre notes auto-générées Gazelle
- Patterns filtrés: "Note Gazelle", "appointment was created", etc.
- Notes utiles affichées EN ENTIER (pas tronquées)

**D. Action items:**
- Détection "Buvards bouteille" (dernière ligne des notes)
- Affiché en chips avec "À apporter:"

**E. Timeline - Résumé intelligent narratif avec ALERTES:**
- User feedback 1: "c'est pas tellement la liste des entrés du timeline que je veux, c'est une résumé intelligent"
- User feedback 2: "la promptitude du paiement si nécessaire: 'le client a été long à payer, lui demander de payer sur le champ'"
- User feedback 3: "montrer ce qui sort de l'ordinaire"

Fonction `_generate_timeline_summary()` analyse et met en évidence LES EXCEPTIONS:
1. **ALERTES (affichées EN PREMIER):**
   - 💰 Paiements lents → "ALERTE PAIEMENT: Client lent à payer - Demander paiement sur le champ!"
   - 🌡️ Climat anormal → "ALERTE CLIMAT: 15°C, 25% - Conditions hors norme!"
   - ⚠️ Problèmes techniques → "ATTENTION: Piano fragile, mécanisme sensible"

2. **Contexte normal:**
   - Régularité des visites (depuis quand, fréquence)
   - Dernière visite avec détails importants
   - Notes "à faire la prochaine fois" ou action items

Format: "💰 ALERTE PAIEMENT: Client lent à payer! Client régulier depuis 2020 (1x/an). Dernière visite: 2025-06-10 par Nicolas. 📝 Note: Apporter buvards bouteille"

Frontend: Affiche SEULEMENT le résumé narratif (pas la liste détaillée d'entrées)

**F. Dampp Chaser (Piano Life Saver) - Indicateur "PLS":**
- User feedback: "dans le message primaire, montrer 'pls' s'il y a un dampp chaser"
- Ajout du champ `has_dampp_chaser` dans `AppointmentOverview`
- Récupération de `dampp_chaser_installed` depuis `gazelle_pianos`
- Affichage chip "PLS" (bleu, petit) à côté du modèle de piano
- Permet au technicien de savoir immédiatement qu'il y a un système d'humidité

**G. Questions de suivi (Follow-up queries):**
- User feedback: "je veux pouvoir demander une questions de suivi, par ex: heure de départ recommandée"
- Détection de questions: "heure de départ", "distance totale", "combien de km"
- Calcul automatique basé sur le contexte de la journée:
  1. **Heure de départ recommandée:** Premier RDV - Temps trajet - Préparation (15 min)
  2. **Distance totale:** Estimation basée sur nombre de quartiers (~20km base + 15km/quartier)
- Affichage dans box bleu avec bordure gauche (info.light)
- Type de réponse: `text_response` dans `ChatResponse`

**H. Accessibilité du Chat (Bouton flottant):**
- User feedback: "il faut pouvoir accéder à ce volet en cliquant sur le symbole de chat en bas à droite, pour tous"
- Bouton FAB (Floating Action Button) en bas à droite de toutes les pages
- Position: bottom: 80px, right: 24px (pour ne pas chevaucher assistant widget)
- Ouvre un Drawer Material-UI qui slide depuis la droite
- Largeur responsive: 100% mobile, 90% tablet, 600px desktop
- Accessible à TOUS les utilisateurs (admin, technicien, assistant)

**Fichiers modifiés:**
- `api/chat/service.py` - Toutes les corrections + Dampp Chaser + questions de suivi
- `api/chat/schemas.py` - Nouveaux champs: `billing_client`, `has_dampp_chaser`, `text_response`
- `frontend/src/components/ChatIntelligent.jsx` - Affichage dual contact/client + timeline + chip PLS + text_response
- `frontend/src/App.jsx` - Bouton flottant + Drawer pour Chat Intelligent

**Tests validés:**
- ✅ RV "SEC-Cibèle": 4 entrées timeline utiles (avant: 6 avec notes vides)
- ✅ Détails complets: Accord 440hz, température 24°C, humidité 33%
- ✅ Dates correctes (dernière visite: 2025-06-10)
- ✅ Action items: "À apporter: Buvards bouteille"
- ✅ Notes utiles affichées en entier (pas tronquées)

---

**Auteur:** Assistant Gazelle Team
**Version:** 1.0 - Document Vivant
**Prochaine mise à jour:** Après import timeline + test complet
