# 📊 GUIDE - GÉNÉRATION DE RÉSUMÉS POUR TECHNICIENS

**Date:** 2025-12-15
**Pour:** Cursor Mac
**Sujet:** Comment analyser les données et générer des résumés intelligents

---

## 🎯 OBJECTIF

Créer des résumés adaptatifs pour les techniciens avec **3 niveaux de détail:**

1. **Synthèse** (5 lignes) - Vue d'ensemble rapide
2. **Détaillé** (1-2 paragraphes) - Informations essentielles
3. **Complet** (format structuré) - Tous les détails

---

## 📋 TYPES DE RÉSUMÉS

### 1. Résumé Quotidien (Ma journée)

**Déclencheurs:**
- "Résume ma journée"
- ".mes rv"
- "Qu'est-ce que j'ai aujourd'hui?"

**Données à analyser:**
```sql
SELECT
    a.id,
    a.start_time,
    a.end_time,
    a.description,
    c.first_name || ' ' || c.last_name AS client_name,
    c.company_name,
    c.full_address,
    p.brand,
    p.model,
    p.serial_number,
    a.notes
FROM gazelle_appointments a
LEFT JOIN gazelle_clients c ON a.client_id = c.id
LEFT JOIN gazelle_pianos p ON a.piano_id = p.id
WHERE
    DATE(a.start_time) = CURRENT_DATE
    AND a.technician_id = %s  -- ID du technicien connecté
ORDER BY a.start_time
```

**Format de sortie:**

**Niveau SYNTHÈSE:**
```
📅 Aujourd'hui: 4 rendez-vous
• 9h00 - Yannick Nézet-Séguin (Accord Steinway)
• 11h30 - Université de Montréal (Réparation Yamaha)
• 14h00 - Studio XYZ (Expertise Kawai)
• 16h30 - Client ABC (Accord Bösendorfer)
```

**Niveau DÉTAILLÉ:**
```
📅 Résumé de votre journée (4 rendez-vous)

Matinée (2 rv):
- 9h00 à 10h30: Yannick Nézet-Séguin - Accord annuel de son Steinway D (série 123456)
  à Montréal. Client confirmé.
- 11h30 à 13h00: Université de Montréal - Réparation pédale du Yamaha C7 (série 789012)
  dans la salle de concert. Pièces à apporter: pédale sostenuto.

Après-midi (2 rv):
- 14h00 à 15h00: Studio XYZ - Expertise pré-achat d'un Kawai RX3 (série 345678).
  Préparer rapport détaillé.
- 16h30 à 18h00: Client ABC - Accord de maintenance d'un Bösendorfer 225 (série 901234).
  Dernier accord il y a 6 mois.
```

**Niveau COMPLET:**
```markdown
# 📅 JOURNÉE DU 2025-12-15 - NICOLAS

## Statistiques
- **Total rendez-vous:** 4
- **Temps total:** 6h30
- **Déplacements:** ~45 km
- **Clients confirmés:** 3/4

---

## 🌅 MATINÉE

### RV #1 - 9h00-10h30 (1h30)
**Client:** Yannick Nézet-Séguin ⭐ VIP
**Type:** Accord annuel
**Lieu:** 123 Rue Mozart, Montréal, H2X 1Y5
**Piano:** Steinway & Sons Model D (concert grand)
- Série: 123456
- Dernier accord: 2024-06-15 (6 mois)
**Notes:**
- Client très exigeant sur la précision
- Préfère un tempérament légèrement étiré dans les aigus
- Piano utilisé pour enregistrements professionnels
**Statut:** ✅ Confirmé par le client
**Préparation:**
- Apporter diapason de référence A=442 Hz
- Outils de régulation fine

---

### RV #2 - 11h30-13h00 (1h30)
**Client:** Université de Montréal
**Type:** Réparation pédale
**Lieu:** 2900 Boulevard Édouard-Montpetit, Salle Pollack
**Piano:** Yamaha C7 (grand queue)
- Série: 789012
**Problème rapporté:**
- Pédale sostenuto ne tient pas
- Bruit métallique lors de l'utilisation
**Pièces à apporter:**
- Kit pédale sostenuto Yamaha (référence: YAM-PED-SOS-01)
**Historique:**
- Dernier entretien: 2024-11-10 (1 mois)
- Piano utilisé intensivement (école de musique)
**Statut:** ✅ Confirmé

---

## 🌆 APRÈS-MIDI

### RV #3 - 14h00-15h00 (1h)
**Client:** Studio XYZ Recording
**Type:** Expertise pré-achat
**Lieu:** 456 Rue Saint-Laurent, local 300
**Piano:** Kawai RX3 (à évaluer)
- Série: 345678
- Année: 2018 (7 ans)
**Objectif:**
- Évaluation complète de l'état
- Estimation de la valeur
- Recommandations d'entretien nécessaire
**Livrables:**
- Rapport écrit détaillé
- Photos des points critiques
- Estimation de réparations si nécessaire
**Budget client:** ~25,000$ CAD
**Statut:** ⏳ À confirmer (relancer le client)

---

### RV #4 - 16h30-18h00 (1h30)
**Client:** Famille Tremblay
**Type:** Accord de maintenance
**Lieu:** 789 Avenue des Pins, Westmount
**Piano:** Bösendorfer 225 (semi-concert)
- Série: 901234
**Historique:**
- Contrat de maintenance annuel
- Dernier accord: 2024-06-20 (6 mois)
- Piano en excellent état général
**Notes:**
- Famille très satisfaite du service
- Piano joué quotidiennement (pianiste amateur avancé)
- Ambiance chaleur/humidité stable (bien contrôlée)
**Statut:** ✅ Confirmé

---

## 📍 ITINÉRAIRE SUGGÉRÉ

```
Départ maison →
1. Yannick (Plateau) 25 min →
2. UdeM (Outremont) 15 min →
[Pause lunch 30 min] →
3. Studio XYZ (Mile-End) 10 min →
4. Famille Tremblay (Westmount) 20 min →
Retour maison 25 min

Total déplacement: ~2h05
Total travail: 6h30
Journée totale: ~9h35
```

---

## ⚠️ POINTS D'ATTENTION

1. **RV #1 (Yannick):** Client VIP - ponctualité critique
2. **RV #2 (UdeM):** Vérifier disponibilité pièce avant départ
3. **RV #3 (Studio XYZ):** Apporter appareil photo + formulaire expertise
4. **RV #4:** Aucune alerte

---

## 📦 MATÉRIEL À PRÉPARER

- [ ] Outils d'accord standard
- [ ] Diapason A=442 Hz (pour Steinway)
- [ ] Kit pédale sostenuto Yamaha
- [ ] Appareil photo
- [ ] Formulaire d'expertise
- [ ] Outils de régulation fine
- [ ] Chiffons + produits d'entretien

---

## 💡 CONSEILS

- Prévoir 15 min de tampon entre RV #2 et #3 pour lunch
- Appeler Studio XYZ le matin pour confirmer RV #3
- Penser à facturer temps de déplacement pour expertise (#3)
```

---

## 📊 ALGORITHME DE GÉNÉRATION

### Étape 1: Récupérer les Données

```python
def get_technician_appointments(
    technician_id: str,
    date: datetime,
    include_context: bool = True
) -> Dict[str, Any]:
    """
    Récupère tous les rendez-vous d'un technicien pour une date donnée.

    Args:
        technician_id: ID du technicien
        date: Date cible
        include_context: Inclure historique client/piano

    Returns:
        Dictionnaire avec appointments + contexte
    """
    # Requête principale
    appointments = supabase.table('gazelle_appointments')\
        .select('''
            *,
            client:client_id(
                id, company_name, first_name, last_name,
                email, phone, full_address
            ),
            piano:piano_id(
                id, brand, model, serial_number,
                manufacturing_year, condition_notes
            ),
            technician:technician_id(
                id, first_name, last_name
            )
        ''')\
        .eq('technician_id', technician_id)\
        .gte('start_time', date.strftime('%Y-%m-%d 00:00:00'))\
        .lt('start_time', (date + timedelta(days=1)).strftime('%Y-%m-%d 00:00:00'))\
        .order('start_time')\
        .execute()

    if not include_context:
        return {'appointments': appointments.data}

    # Enrichir avec contexte
    enriched = []
    for appt in appointments.data:
        # Historique du client
        client_history = get_client_history(appt['client_id'], limit=5)

        # Derniers accords du piano
        piano_history = get_piano_history(appt['piano_id'], limit=3)

        # Timeline récente
        timeline = get_timeline_entries(
            client_id=appt['client_id'],
            piano_id=appt['piano_id'],
            limit=5
        )

        enriched.append({
            **appt,
            'client_history': client_history,
            'piano_history': piano_history,
            'timeline': timeline
        })

    return {
        'appointments': enriched,
        'stats': calculate_daily_stats(enriched)
    }
```

### Étape 2: Analyser et Classifier

```python
def analyze_appointment(appt: Dict) -> Dict[str, Any]:
    """
    Analyse un rendez-vous et extrait les informations clés.

    Returns:
        Dictionnaire avec:
            - priority: low/medium/high/vip
            - alerts: Liste d'alertes
            - preparation: Matériel/actions nécessaires
            - context_notes: Notes contextuelles importantes
    """
    alerts = []
    preparation = []
    priority = 'medium'

    # 1. Vérifier statut VIP du client
    if is_vip_client(appt['client']):
        priority = 'vip'
        alerts.append("⭐ Client VIP - Service premium attendu")

    # 2. Vérifier confirmation
    if not appt.get('confirmed_by_client'):
        alerts.append("⏳ À confirmer - Appeler le client")
        priority = max(priority, 'medium')

    # 3. Analyser type de service
    service_type = classify_service_type(appt)

    if service_type == 'repair':
        alerts.append("🔧 Réparation - Vérifier disponibilité pièces")
        preparation.extend(get_repair_parts_needed(appt))

    elif service_type == 'expertise':
        alerts.append("📋 Expertise - Apporter formulaire + appareil photo")
        preparation.extend([
            "Formulaire d'expertise vierge",
            "Appareil photo ou smartphone",
            "Lampe de poche",
            "Mètre ruban"
        ])

    # 4. Vérifier historique problèmes
    recent_issues = get_recent_issues(appt['piano_id'])
    if recent_issues:
        alerts.append(f"⚠️ {len(recent_issues)} problème(s) récent(s) sur ce piano")

    # 5. Vérifier délai depuis dernier service
    last_service = get_last_service_date(appt['piano_id'])
    if last_service:
        days_since = (datetime.now() - last_service).days
        if days_since > 365:
            alerts.append(f"📅 Dernier service il y a {days_since} jours (>1 an)")

    # 6. Analyser notes précédentes
    if appt.get('notes'):
        if 'exigeant' in appt['notes'].lower():
            priority = max(priority, 'high')
        if 'urgent' in appt['notes'].lower():
            priority = 'high'

    return {
        'priority': priority,
        'alerts': alerts,
        'preparation': preparation,
        'service_type': service_type,
        'estimated_duration': estimate_duration(appt, service_type),
        'context_notes': extract_context_notes(appt)
    }
```

### Étape 3: Générer le Résumé

```python
def generate_summary(
    appointments: List[Dict],
    level: str = 'detailed'  # 'synthesis' | 'detailed' | 'complete'
) -> str:
    """
    Génère le résumé selon le niveau de détail demandé.

    Args:
        appointments: Liste des rendez-vous avec contexte
        level: Niveau de détail

    Returns:
        Résumé formaté en markdown
    """
    if level == 'synthesis':
        return generate_synthesis(appointments)

    elif level == 'detailed':
        return generate_detailed_summary(appointments)

    elif level == 'complete':
        return generate_complete_summary(appointments)

    else:
        raise ValueError(f"Niveau inconnu: {level}")


def generate_synthesis(appointments: List[Dict]) -> str:
    """Génère résumé synthétique (5 lignes max)."""
    total = len(appointments)

    lines = [f"📅 Aujourd'hui: {total} rendez-vous"]

    for appt in appointments[:4]:  # Max 4 premiers
        time = appt['start_time'].strftime('%Hh%M')
        client = get_client_display_name(appt['client'])
        service = get_service_short_desc(appt)

        lines.append(f"• {time} - {client} ({service})")

    if total > 4:
        lines.append(f"• ... et {total - 4} autres")

    return '\n'.join(lines)


def generate_detailed_summary(appointments: List[Dict]) -> str:
    """Génère résumé détaillé (1-2 paragraphes par période)."""
    morning = [a for a in appointments if a['start_time'].hour < 12]
    afternoon = [a for a in appointments if a['start_time'].hour >= 12]

    sections = [
        f"📅 Résumé de votre journée ({len(appointments)} rendez-vous)\n"
    ]

    if morning:
        sections.append("Matinée (" + str(len(morning)) + " rv):")
        for appt in morning:
            sections.append(format_detailed_appointment(appt))
        sections.append("")

    if afternoon:
        sections.append("Après-midi (" + str(len(afternoon)) + " rv):")
        for appt in afternoon:
            sections.append(format_detailed_appointment(appt))

    return '\n'.join(sections)


def format_detailed_appointment(appt: Dict) -> str:
    """Formate un rendez-vous pour le niveau détaillé."""
    time_start = appt['start_time'].strftime('%Hh%M')
    time_end = appt['end_time'].strftime('%Hh%M')

    client = get_client_display_name(appt['client'])
    service = appt['description'] or "Service pianistique"

    piano_desc = f"{appt['piano']['brand']} {appt['piano']['model']}"
    serial = appt['piano']['serial_number']

    location = get_short_address(appt['client']['full_address'])

    # Contexte additionnel
    context = []

    # Statut confirmation
    if appt.get('confirmed_by_client'):
        context.append("Client confirmé")
    else:
        context.append("⏳ À confirmer")

    # Dernier service
    last_service = get_last_service_date(appt['piano_id'])
    if last_service:
        months_ago = (datetime.now() - last_service).days // 30
        if months_ago > 0:
            context.append(f"Dernier accord il y a {months_ago} mois")

    # Notes importantes
    if appt.get('notes'):
        # Extraire première phrase des notes
        first_sentence = appt['notes'].split('.')[0]
        if len(first_sentence) < 100:
            context.append(first_sentence)

    context_str = '. '.join(context) if context else ""

    return (
        f"- {time_start} à {time_end}: {client} - {service} de son "
        f"{piano_desc} (série {serial}) à {location}. {context_str}"
    )
```

---

## 🧠 INTELLIGENCE CONTEXTUELLE

### Détection de Patterns

```python
def detect_patterns(appointments: List[Dict]) -> List[str]:
    """
    Détecte des patterns intéressants dans la journée.

    Returns:
        Liste de suggestions/observations
    """
    suggestions = []

    # 1. Concentration géographique
    locations = [a['client']['full_address'] for a in appointments]
    if has_geographic_cluster(locations):
        suggestions.append(
            "💡 Plusieurs rendez-vous dans le même quartier - "
            "Optimiser l'itinéraire peut économiser 30 min"
        )

    # 2. Clients récurrents
    client_ids = [a['client_id'] for a in appointments]
    recurring = [cid for cid in client_ids if client_ids.count(cid) > 1]
    if recurring:
        suggestions.append(
            f"🔁 {len(set(recurring))} client(s) avec plusieurs rendez-vous aujourd'hui"
        )

    # 3. Même piano plusieurs fois
    piano_ids = [a['piano_id'] for a in appointments if a.get('piano_id')]
    recurring_pianos = [pid for pid in piano_ids if piano_ids.count(pid) > 1]
    if recurring_pianos:
        suggestions.append(
            "⚠️ Même piano prévu plusieurs fois - Vérifier s'il y a doublon"
        )

    # 4. Longue journée
    if len(appointments) > 6:
        total_hours = sum([
            (a['end_time'] - a['start_time']).total_seconds() / 3600
            for a in appointments
        ])
        if total_hours > 8:
            suggestions.append(
                f"⏰ Longue journée prévue ({total_hours:.1f}h de travail) - "
                "Prévoir pauses"
            )

    # 5. Matériel spécial requis
    special_tools = set()
    for appt in appointments:
        analysis = analyze_appointment(appt)
        special_tools.update(analysis.get('preparation', []))

    if len(special_tools) > 5:
        suggestions.append(
            f"🧰 {len(special_tools)} items spéciaux à préparer - "
            "Vérifier disponibilité la veille"
        )

    return suggestions
```

### Calcul Itinéraire Optimisé

```python
def calculate_optimized_route(appointments: List[Dict]) -> Dict:
    """
    Calcule l'itinéraire optimisé pour minimiser les déplacements.

    Returns:
        Dictionnaire avec:
            - route: Liste ordonnée des rendez-vous
            - total_distance: Distance totale (km)
            - total_time: Temps de déplacement total
            - savings: Économie vs ordre chronologique
    """
    # Extraire coordonnées (ou addresses)
    locations = []
    for appt in appointments:
        loc = {
            'appointment_id': appt['id'],
            'address': appt['client']['full_address'],
            'time_window': (appt['start_time'], appt['end_time']),
            # Géocodage si disponible
            'lat': appt.get('latitude'),
            'lon': appt.get('longitude')
        }
        locations.append(loc)

    # Algorithme de routage (simplifié)
    # Dans la vraie version, utiliser API Google Maps ou OSM

    # Pour l'instant: tri chronologique + détection clusters géo
    ordered = sorted(appointments, key=lambda a: a['start_time'])

    # Calcul distances approximatives
    total_km = estimate_total_distance(ordered)
    total_time_min = estimate_travel_time(ordered)

    return {
        'route': ordered,
        'total_distance_km': total_km,
        'total_travel_time_min': total_time_min,
        'suggestions': generate_route_suggestions(ordered)
    }
```

---

## 🎨 PERSONNALISATION PAR TECHNICIEN

### Préférences Stockées

```python
# Table: technician_preferences
{
    'technician_id': 'tech_123',
    'summary_level_default': 'detailed',  # synthesis | detailed | complete
    'include_travel_time': True,
    'include_preparation_list': True,
    'include_client_notes': True,
    'include_piano_history': False,
    'highlight_vip_clients': True,
    'morning_briefing_time': '07:00',  # Heure envoi email auto
    'reminder_before_first_appt_min': 30
}
```

### Adaptation Automatique

```python
def adapt_summary_to_preferences(
    summary: str,
    technician_id: str
) -> str:
    """
    Adapte le résumé selon les préférences du technicien.
    """
    prefs = get_technician_preferences(technician_id)

    # Ajuster niveau de détail
    if prefs['summary_level_default'] == 'synthesis':
        summary = condense_to_synthesis(summary)

    # Ajouter/retirer sections
    if prefs['include_travel_time']:
        summary += "\n\n" + generate_travel_section(appointments)

    if prefs['include_preparation_list']:
        summary += "\n\n" + generate_preparation_checklist(appointments)

    # Highlight VIP
    if prefs['highlight_vip_clients']:
        summary = highlight_vip_markers(summary)

    return summary
```

---

## 📤 MODES DE LIVRAISON

### 1. API Endpoint (Temps Réel)

```python
@router.post("/assistant/chat")
async def chat(request: ChatRequest):
    """
    Endpoint principal de l'assistant conversationnel.

    Exemples:
        - "Résume ma journée"
        - ".mes rv"
        - "Résume ma semaine"
    """
    question = request.question

    # Parser la question
    parsed = parser.parse(question)

    if parsed['query_type'] == QueryType.APPOINTMENTS:
        # Déterminer période
        date = parsed.get('date', datetime.now())
        level = parsed.get('detail_level', 'detailed')

        # Récupérer rendez-vous
        appointments = get_technician_appointments(
            technician_id=request.user_id,
            date=date,
            include_context=True
        )

        # Générer résumé
        summary = generate_summary(
            appointments['appointments'],
            level=level
        )

        return {
            'response': summary,
            'data': appointments,
            'suggestions': detect_patterns(appointments['appointments'])
        }
```

### 2. Email Automatique (Briefing Matinal)

```python
async def send_morning_briefing(technician_id: str):
    """
    Envoie le briefing matinal par email.

    Appelé par tâche cron quotidienne à 7h du matin.
    """
    prefs = get_technician_preferences(technician_id)

    # Récupérer rendez-vous du jour
    appointments = get_technician_appointments(
        technician_id=technician_id,
        date=datetime.now(),
        include_context=True
    )

    if not appointments['appointments']:
        # Pas de rendez-vous aujourd'hui
        return

    # Générer résumé complet
    summary = generate_complete_summary(appointments['appointments'])

    # Préparer email HTML
    email_html = render_email_template(
        'morning_briefing.html',
        {
            'technician_name': get_technician_name(technician_id),
            'date': datetime.now().strftime('%Y-%m-%d'),
            'summary': markdown_to_html(summary),
            'stats': appointments['stats'],
            'route_map': generate_route_map_url(appointments['appointments'])
        }
    )

    # Envoyer
    send_email(
        to=get_technician_email(technician_id),
        subject=f"📅 Briefing du {datetime.now().strftime('%d %B %Y')}",
        html_body=email_html
    )
```

### 3. Notification Push (Rappels)

```python
async def send_appointment_reminder(
    appointment_id: str,
    minutes_before: int = 30
):
    """
    Envoie rappel avant un rendez-vous.

    Args:
        appointment_id: ID du rendez-vous
        minutes_before: Minutes avant le RV
    """
    appt = get_appointment(appointment_id)

    # Générer résumé court
    reminder_text = (
        f"⏰ Rendez-vous dans {minutes_before} min\n"
        f"{appt['client']['first_name']} {appt['client']['last_name']}\n"
        f"{appt['description']}\n"
        f"{appt['client']['full_address']}"
    )

    # Envoyer notification
    send_push_notification(
        user_id=appt['technician_id'],
        title="Rappel rendez-vous",
        body=reminder_text,
        action_url=f"/appointments/{appointment_id}"
    )
```

---

## 🧪 EXEMPLES DE REQUÊTES

### Exemple 1: Résumé Quotidien Basique

**Question:** "Résume ma journée"

**Réponse (Niveau DÉTAILLÉ):**
```
📅 Résumé de votre journée (3 rendez-vous)

Matinée (1 rv):
- 9h00 à 10h30: Yannick Nézet-Séguin - Accord annuel de son Steinway D
  (série 123456) à Montréal. Client confirmé. Dernier accord il y a 6 mois.

Après-midi (2 rv):
- 14h00 à 15h30: Université de Montréal - Réparation pédale du Yamaha C7
  (série 789012) dans la Salle Pollack. ⏳ À confirmer. Piano utilisé intensivement.
- 16h00 à 17h00: Studio XYZ - Expertise pré-achat d'un Kawai RX3
  (série 345678). Client confirmé. Apporter formulaire d'expertise.

💡 Suggestions:
- Tous les rendez-vous sont dans un rayon de 10 km - Itinéraire optimisé
- Appeler UdeM pour confirmer RV #2
- Préparer kit d'expertise pour RV #3
```

### Exemple 2: Résumé Hebdomadaire

**Question:** "Résume ma semaine"

**Réponse:**
```
📅 SEMAINE DU 15-21 DÉCEMBRE 2025

## Statistiques Générales
- **Total rendez-vous:** 18
- **Temps travail:** 27h30
- **Déplacements:** ~180 km
- **Clients différents:** 15

## Répartition par Jour

**Lundi 15 déc** - 4 RV (6h30)
- Matin: Yannick (Steinway), UdeM (Yamaha)
- PM: Studio XYZ (expertise), Famille Tremblay (Bösendorfer)

**Mardi 16 déc** - 3 RV (5h)
- Conservatoire (3 pianos droits)
- Client ABC (Accord Kawai)
- École de musique (Réparation Yamaha)

**Mercredi 17 déc** - 2 RV (3h)
- Entreprise XYZ (Expertise)
- Particulier (Accord Steinway)

**Jeudi 18 déc** - 5 RV (7h30) ⚠️ Journée chargée
- [...détails...]

**Vendredi 19 déc** - 4 RV (5h30)
- [...détails...]

## Top 5 Priorités

1. ⭐ Jeudi 9h: Yannick Nézet-Séguin (VIP) - Accord avant concert
2. 🔧 Mardi 14h: Conservatoire - Réparation urgente piano concert
3. 📋 Mercredi 10h: Expertise pour vente piano d'époque rare
4. ⏰ Vendredi 8h: Premier RV de la semaine - Ponctualité!
5. 📞 Lundi: Confirmer 3 rendez-vous non confirmés

## Matériel à Prévoir Cette Semaine

- Kit réparation mécanique complet (mardi)
- Appareil photo + formulaires expertise (mercredi)
- Outils régulation fine (jeudi - piano concert)
- Pièces de rechange courantes

## Revenus Estimés

- Total facturé: ~4,200$ CAD
- Déplacements: ~360$ CAD
- **Total: ~4,560$ CAD**
```

---

## 🎯 CRITÈRES DE QUALITÉ

Un bon résumé doit:

✅ **Être actionnable** - Le technicien sait exactement quoi faire
✅ **Être contextualisé** - Informations historiques pertinentes
✅ **Être priorisé** - Ce qui est urgent/important en premier
✅ **Être optimisé** - Suggestions d'itinéraire, préparation
✅ **Être personnalisé** - Adapté aux préférences du technicien
✅ **Être concis** - Pas de surcharge d'information
✅ **Être visuel** - Emojis, formatage pour lecture rapide

---

**Créé:** 2025-12-15 11:30 EST
**Par:** Claude Code (Windows)
**Pour:** Cursor Mac
**Statut:** 📋 GUIDE COMPLET POUR IMPLÉMENTATION
