# 🎓 Système d'Entraînement des Sommaires - Guide Utilisateur

Système local d'entraînement pour raffiner les formats de sommaires de journée et d'informations client avec les vraies données de Piano-Tek.

## 🎯 Objectif

Permettre d'itérer sur les formats de sommaires en:
- Testant différents formats avec les vraies données
- Donnant du feedback en langage naturel
- Comparant les formats côte à côte
- Sauvegardant les préférences

**Inspiré du système V4** mais avec feedback moderne et conversationnel.

## 🚀 Démarrage Rapide

```bash
python3 scripts/train_summaries.py
```

Interface locale uniquement (pas web, pas partie de l'assistant).

## 📋 Menu Principal

### 1. Tester sommaire de journée

Génère un résumé de journée avec les RV réels de Gazelle.

**Options:**
- **Date:** Aujourd'hui / Demain / Date spécifique
- **Technicien:** Tous / Nick / Jean-Philippe / Allan
- **Format:** Compact / Détaillé / V4 Style

**Exemple de sortie (Format Compact):**
```
📅 2025-12-16
==================================================

3 rendez-vous:

1. 09:00 - Accordage - Yannick Nézet-Séguin
2. 14:30 - Réparation - Conservatoire de Montréal
3. 16:00 - Inspection - Studio Piano Plus
```

**Exemple de sortie (Format Détaillé):**
```
📅 2025-12-16
==================================================

3 rendez-vous:

1. 🕐 09:00 - Accordage
   👤 Yannick Nézet-Séguin
   📍 123 Rue Example, Montréal
   📞 514-555-1234

2. 🕐 14:30 - Réparation
   👤 Conservatoire de Montréal
   📍 4750 Avenue Henri-Julien, Montréal
   📞 514-555-5678
```

**Exemple de sortie (Format V4):**
```
📅 2025-12-16
==================================================

3 rendez-vous:

1. 09:00 - Yannick Nézet-Séguin
  Adresse: 123 Rue Example, Montréal
  Service: Accordage
  ⚠️ RAPPEL: !! Apporter cordes de remplacement
```

### 2. Tester sommaire client

Génère un résumé d'informations client avec pianos et historique.

**Options:**
- **Recherche:** Nom du client
- **Sélection:** Parmi les résultats trouvés
- **Format:** Compact / Détaillé / V4 Style

**Exemple de sortie (Format Compact):**
```
👤 Yannick Nézet-Séguin
📍 Montréal
🎹 2 piano(s)
📅 Dernier RV: 2025-12-10
```

**Exemple de sortie (Format Détaillé):**
```
👤 **Yannick Nézet-Séguin**
==================================================

📍 123 Rue Example, Montréal H2X 1Y5
📞 514-555-1234
📧 yns@osm.ca

🎹 **Pianos (2):**
  - Steinway Grand Piano (S/N: 123456)
  - Yamaha C7 (S/N: 789012)

📅 **Derniers RV:**
  - 2025-12-10: Accordage
  - 2025-11-15: Réparation
  - 2025-10-20: Inspection
```

### 3. Voir historique d'entraînement

Affiche tous les tests précédents avec les feedbacks donnés.

**Exemple:**
```
HISTORIQUE D'ENTRAÎNEMENT (5 sessions)
======================================================================

1. [2025-12-16T14:30:00] day_summary
   Format: detailed
   Note implicite: ⭐⭐⭐⭐ (4/5)
   💬 Feedback:
      Très bon mais manque le temps de déplacement
      Devrait inclure le numéro de téléphone

2. [2025-12-16T14:25:00] client_summary
   Format: compact
   Note: ⭐⭐⭐ (3/5)
   💬 Manque les détails des pianos
```

### 4. Comparer formats côte à côte

Génère les 3 formats en parallèle pour la même journée ou le même client.

Idéal pour décider quel format convient le mieux!

## 💬 Système de Feedback

Deux modes disponibles:

### Mode 1: Feedback Détaillé (Recommandé)

Feedback en langage naturel, comme si tu parlais à un assistant.

**Exemples:**
```
Tu aurais dû inclure le numéro de téléphone
La réponse devrait mentionner la distance de déplacement
Manque le temps estimé entre les RV
```

```
Excellente présentation, très claire
Tu pourrais ajouter les reminders des notes
Mais dans l'ensemble c'est parfait
```

**Extraction automatique de note:**
Le système détecte automatiquement une note implicite:

| Feedback contient | Note Implicite |
|------------------|---------------|
| excellent, parfait, impeccable | 5/5 ⭐⭐⭐⭐⭐ |
| très bon, bien | 4/5 ⭐⭐⭐⭐ |
| correct, acceptable, ok | 3/5 ⭐⭐⭐ |
| insuffisant, mauvais, manque | 2/5 ⭐⭐ |
| terrible, inutilisable | 1/5 ⭐ |

### Mode 2: Note Rapide

Simple note de 1 à 5 avec commentaire optionnel.

**Exemple:**
```
Note (1-5): 4
Commentaire: Bon mais manque ville
```

## 📁 Fichiers Générés

### `summary_training_results.json`

Stocke tous les résultats d'entraînement avec:
- Timestamp
- Type de sommaire (day/client)
- Format utilisé
- Sommaire généré
- Feedback donné
- Note (explicite ou implicite)

**Structure:**
```json
[
  {
    "timestamp": "2025-12-16T14:30:00",
    "type": "day_summary",
    "date": "2025-12-16",
    "technicien": "Nick",
    "format_style": "detailed",
    "appointments_count": 3,
    "summary": "📅 2025-12-16 - Nick\n...",
    "feedback": {
      "mode": "natural",
      "feedback": "Tu aurais dû inclure...",
      "implicit_rating": 3
    }
  }
]
```

## 🔄 Workflow Recommandé

### 1. Explorer les Formats

```bash
python3 scripts/train_summaries.py
# Menu: 4 (Comparer formats)
```

Compare les 3 formats pour une même journée ou client.

### 2. Tester avec Vraies Données

```bash
# Menu: 1 (Sommaire de journée)
# Choix: Aujourd'hui / Nick / Détaillé
```

Génère un sommaire réel avec les RV du jour.

### 3. Donner Feedback Détaillé

```
💬 Feedback en langage naturel:
Tu aurais dû dire:
"9:00 - Yannick Nézet-Séguin (514-555-1234)
📍 123 Rue Example, Montréal (15 min de ton dernier RV)
🎹 Steinway Grand Piano
⚠️ Apporter cordes de remplacement"

Au lieu de juste:
"9:00 - Accordage - Yannick Nézet-Séguin"

Manquent: téléphone, adresse, temps de déplacement, type de piano, reminders
```

### 4. Itérer

- Tester différents formats
- Raffiner selon les feedbacks
- Comparer les résultats
- Converger vers le format idéal

### 5. Analyser les Résultats

```bash
# Tous les feedbacks naturels
cat scripts/summary_training_results.json | jq '.[] | select(.feedback.mode == "natural") | .feedback.feedback'

# Feedbacks avec problèmes (≤ 2)
cat scripts/summary_training_results.json | jq '.[] | select((.feedback.implicit_rating // .feedback.rating) <= 2)'

# Notes moyennes par format
cat scripts/summary_training_results.json | jq -r '.[] | "\(.format_style)|\(.feedback.rating // .feedback.implicit_rating)"' | awk -F'|' '{sum[$1]+=$2; count[$1]++} END {for (f in sum) print f": "sum[f]/count[f]}'
```

## 🎨 Les 3 Formats Expliqués

### Format Compact

**Usage:** Aperçu rapide, liste simple

**Avantages:**
- ✅ Concis, facile à scanner
- ✅ Tient sur un écran
- ✅ Idéal pour SMS ou notification

**Inconvénients:**
- ❌ Manque détails (adresse, téléphone)
- ❌ Pas de context (distance, reminders)

**Quand l'utiliser:**
- Réponse rapide "mes rv"
- Notifications push
- Aperçu journée

### Format Détaillé

**Usage:** Informations complètes, planification

**Avantages:**
- ✅ Toutes les infos nécessaires
- ✅ Adresse et téléphone inclus
- ✅ Format structuré et clair

**Inconvénients:**
- ❌ Plus verbeux
- ❌ Peut être trop d'infos pour aperçu rapide

**Quand l'utiliser:**
- Planification de journée
- Recherche client détaillée
- Préparation de visite

### Format V4 Style

**Usage:** Compatible avec l'ancien système

**Avantages:**
- ✅ Familier pour utilisateurs V4
- ✅ Inclut reminders extraits
- ✅ Format texte simple

**Inconvénients:**
- ❌ Pas d'emojis (moins moderne)
- ❌ Structure moins claire

**Quand l'utiliser:**
- Transition depuis V4
- Export texte brut
- Intégration anciens outils

## 💡 Exemples de Feedbacks Utiles

### ✅ Feedback Excellent

```
Tu aurais dû dire:
"9:00 - Yannick Nézet-Séguin
📍 123 Rue Example, Montréal (20 min de déplacement)
📞 514-555-1234
🎹 Steinway Grand Piano (S/N: 123456)
⚠️ RAPPEL: Apporter cordes de remplacement"

Au lieu de:
"9:00 - Accordage - Yannick Nézet-Séguin"

Manquent:
- Adresse complète
- Temps de déplacement
- Téléphone direct
- Détails du piano
- Reminders extraits des notes
```

→ Feedback actionnable avec exemple concret

### ✅ Feedback Bon

```
La réponse devrait inclure:
- Le numéro de téléphone du client
- L'adresse complète (pas juste la ville)
- Le temps de déplacement estimé depuis le RV précédent
- Les reminders importants (lignes avec !!)
```

→ Liste claire de ce qui manque

### ❌ Feedback Moins Utile

```
Pas bien
À améliorer
Manque des choses
```

→ Pas assez spécifique pour être actionnable

## 🔍 Commandes d'Analyse

### Voir tous les feedbacks naturels

```bash
cat scripts/summary_training_results.json | jq -r '.[] | select(.feedback.mode == "natural") | .feedback.feedback'
```

### Feedbacks par format

```bash
# Format compact
cat scripts/summary_training_results.json | jq '.[] | select(.format_style == "compact")'

# Format détaillé
cat scripts/summary_training_results.json | jq '.[] | select(.format_style == "detailed")'

# Format V4
cat scripts/summary_training_results.json | jq '.[] | select(.format_style == "v4")'
```

### Notes moyennes

```bash
# Par format
cat scripts/summary_training_results.json | jq -r '.[] | "\(.format_style)|\(.feedback.rating // .feedback.implicit_rating // 0)"' | awk -F'|' '{sum[$1]+=$2; count[$1]++} END {for (f in sum) print f": "sum[f]/count[f]}'

# Par type (day vs client)
cat scripts/summary_training_results.json | jq -r '.[] | "\(.type)|\(.feedback.rating // .feedback.implicit_rating // 0)"' | awk -F'|' '{sum[$1]+=$2; count[$1]++} END {for (f in sum) print f": "sum[f]/count[f]}'
```

### Patterns communs dans feedbacks

```bash
# Mentions de "devrait"
cat scripts/summary_training_results.json | jq -r '.[] | select(.feedback.mode == "natural") | .feedback.feedback' | grep -i "devrait"

# Mentions de "manque"
cat scripts/summary_training_results.json | jq -r '.[] | select(.feedback.mode == "natural") | .feedback.feedback' | grep -i "manque"

# Mentions de téléphone
cat scripts/summary_training_results.json | jq -r '.[] | select(.feedback.mode == "natural") | .feedback.feedback' | grep -i "téléphone"

# Mentions de distance/déplacement
cat scripts/summary_training_results.json | jq -r '.[] | select(.feedback.mode == "natural") | .feedback.feedback' | grep -i "déplacement\|distance"
```

## 🔗 Différences avec V4

### V4 (Ancien Système)

**Architecture:**
- SQL Server direct
- Google Maps Distance Matrix API
- Scripts Python ad-hoc
- Génération texte brut

**Formats:**
- Un seul format fixe
- Pas de feedback
- Pas d'itération

**Données:**
- Snapshots statiques
- Pas de mise à jour temps réel

### V5 Training System (Nouveau)

**Architecture:**
- Supabase REST API
- Données temps réel
- Interface interactive
- Feedback en langage naturel

**Formats:**
- 3 formats paramétrables
- Comparaison côte à côte
- Itération rapide

**Feedback:**
- Notes implicites automatiques
- Historique complet
- Analyse de patterns

**Extension Future:**
- Google Maps API peut être ajouté
- Templates personnalisables
- Export de préférences

## 🚀 Prochaines Étapes Possibles

### Court Terme

- [ ] Tester les 3 formats avec vraies données
- [ ] Collecter 10+ feedbacks par format
- [ ] Identifier le format préféré pour chaque usage

### Moyen Terme

- [ ] Ajouter Google Maps Distance Matrix API
- [ ] Calculer temps de déplacement entre RV
- [ ] Extraction intelligente de reminders

### Long Terme

- [ ] Générer templates basés sur feedbacks
- [ ] Export de configuration de format
- [ ] Intégration dans l'assistant principal

## 📖 Ressources

- [README_SYSTEME_TEST.md](README_SYSTEME_TEST.md) - Système de test de l'assistant
- [README_FEEDBACK_NATUREL.md](README_FEEDBACK_NATUREL.md) - Guide feedback naturel
- [docs/ANALYSIS_V4_SUMMARIES.md](../docs/ANALYSIS_V4_SUMMARIES.md) - Analyse V4

---

**Créé:** 2025-12-16
**Version:** 1.0
**Type:** Local uniquement (pas web, pas partie de l'assistant)
**Utilise:** Vraies données Supabase en temps réel
