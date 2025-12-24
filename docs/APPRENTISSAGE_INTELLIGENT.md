# 🧠 Système d'Apprentissage Intelligent - Place des Arts

## Vue d'ensemble

Le système d'apprentissage intelligent permet au parser Place des Arts d'améliorer sa précision au fil du temps en apprenant des corrections manuelles de l'utilisateur.

### Comment ça fonctionne

1. **Parsing automatique** - Le texte collé est parsé avec un score de confiance (0-1)
2. **Détection de faible confiance** - Si confiance < 100%, un formulaire éditable s'affiche
3. **Correction manuelle** - L'utilisateur corrige les champs mal parsés
4. **Enregistrement** - Les corrections sont sauvegardées dans `parsing_corrections`
5. **Apprentissage futur** - Les patterns de correction améliorent le parser

---

## 🗄️ Configuration Supabase

### Étape 1: Créer la table `parsing_corrections`

Exécute ce SQL dans Supabase SQL Editor:

```sql
CREATE TABLE IF NOT EXISTS public.parsing_corrections (
    id BIGSERIAL PRIMARY KEY,

    -- Texte original parsé
    original_text TEXT NOT NULL,

    -- Champs parsés automatiquement
    parsed_date TEXT,
    parsed_room TEXT,
    parsed_for_who TEXT,
    parsed_diapason TEXT,
    parsed_piano TEXT,
    parsed_time TEXT,
    parsed_requester TEXT,
    parsed_confidence DECIMAL(3, 2),

    -- Champs corrigés manuellement
    corrected_date TEXT,
    corrected_room TEXT,
    corrected_for_who TEXT,
    corrected_diapason TEXT,
    corrected_piano TEXT,
    corrected_time TEXT,
    corrected_requester TEXT,

    -- Métadonnées
    corrected_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT unique_text_correction UNIQUE (original_text, corrected_by)
);

CREATE INDEX IF NOT EXISTS idx_parsing_corrections_created
    ON public.parsing_corrections(created_at DESC);

COMMENT ON TABLE public.parsing_corrections IS
'Stocke les corrections manuelles du parser Place des Arts pour apprentissage intelligent';

-- RLS (Row Level Security)
ALTER TABLE public.parsing_corrections ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all authenticated users to read corrections"
    ON public.parsing_corrections
    FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Allow all authenticated users to insert corrections"
    ON public.parsing_corrections
    FOR INSERT
    TO authenticated
    WITH CHECK (true);
```

---

## 🎨 Interface Utilisateur

### Mode lecture seule (Confiance >= 100%)

- Affichage simple des champs parsés
- Badge vert "✓ Haute confiance"
- Bouton "✎ Modifier" optionnel

### Mode édition (Confiance < 100%)

- Fond bleu clair avec bordure bleue
- Formulaire avec champs éditables:
  - **Date RDV** (input date)
  - **Heure** (input texte)
  - **Salle** (select avec options WP, TM, MS, SD, C5, SCL, ODM)
  - **Diapason** (input texte)
  - **Pour qui** (input texte) - L'artiste/événement
  - **Demandeur** (input texte) - La personne qui fait la demande
  - **Piano** (input texte)
- Boutons:
  - "✓ Valider et apprendre" (vert) - Sauvegarde et enregistre pour apprentissage
  - "Annuler" (gris) - Retour en mode lecture

### Badges de confiance

- 🟢 **Haute confiance** (≥80%) - Vert
- 🟡 **Moyenne confiance** (60-79%) - Jaune
- 🔴 **Faible confiance** (<60%) - Rouge

---

## 🔌 API Endpoints

### POST `/place-des-arts/learn`

Enregistre une correction pour apprentissage.

**Request:**
```json
{
  "original_text": "Texte collé complet...",
  "parsed_date": "2026-01-14",
  "parsed_room": "5E",
  "parsed_for_who": "Clémence",
  "parsed_requester": null,
  "corrected_date": "2026-01-14",
  "corrected_room": "C5",
  "corrected_for_who": "Clémence",
  "corrected_requester": "Isabelle",
  "corrected_by": "asutton@piano-tek.com"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Correction enregistrée pour apprentissage futur"
}
```

### GET `/place-des-arts/learning-stats`

Retourne des statistiques d'apprentissage.

**Response:**
```json
{
  "success": true,
  "stats": {
    "total_corrections": 15,
    "fields_corrected": {
      "date": 2,
      "room": 8,
      "for_who": 5,
      "diapason": 1,
      "piano": 3,
      "time": 4,
      "requester": 12
    },
    "recent_corrections": [...]
  }
}
```

---

## 📊 Exemples d'utilisation

### Exemple 1: Confusion "Pour qui" vs "Demandeur"

**Texte collé:**
```
14-Jan
5E
Clémence
440
Piano Baldwin (9')
A 13h
Isabelle
```

**Parsing initial:**
- Pour qui: Clémence ✓
- Demandeur: Isabelle ✓
- Confiance: 105% → Mode lecture seule

**Résultat:** Pas de correction nécessaire, confiance élevée

### Exemple 2: Salle mal reconnue

**Texte collé:**
```
5 décembre
Cinquième salle
Concert Chopin
442
Steinway D
14h30
IC
```

**Parsing initial:**
- Room: "Cinquième salle" (non normalisé)
- Confiance: 75% → Mode édition

**Correction manuelle:**
- Room: C5 (sélectionné dans le dropdown)

**Apprentissage:** Le système apprend que "Cinquième salle" → C5

---

## 🚀 Prochaines étapes (Améliorations futures)

1. **Machine Learning**
   - Analyser les corrections pour détecter des patterns
   - Ajuster automatiquement les règles de parsing

2. **Suggestions intelligentes**
   - Proposer des corrections basées sur l'historique
   - Auto-complétion des champs fréquemment corrigés

3. **Dashboard d'analyse**
   - Visualisation des champs les plus problématiques
   - Statistiques de progression de la précision

4. **Export des règles apprises**
   - Permettre d'exporter les règles pour les partager
   - Importer des règles d'autres systèmes

---

## 📝 Notes techniques

### Fichiers modifiés/créés

**Backend:**
- `api/place_des_arts.py` - Ajout endpoints `/learn` et `/learning-stats`
- `modules/place_des_arts/services/email_parser.py` - Support "5E" normalisé en "C5"

**Frontend:**
- `frontend/src/components/place_des_arts/EditablePreviewItem.jsx` - Nouveau composant
- `frontend/src/components/place_des_arts/PlaceDesArtsDashboard.jsx` - Intégration
- `frontend/src/App.jsx` - Passage de `currentUser` à PlaceDesArtsDashboard

**SQL:**
- `scripts/create_parsing_corrections_table.sql` - Création table

### Architecture

```
┌─────────────────────┐
│  Texte collé        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  parse_email_text() │
│  (email_parser.py)  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Confiance < 1.0?   │
└──────────┬──────────┘
           │
    ┌──────┴──────┐
    │ Oui         │ Non
    ▼             ▼
┌─────────────┐ ┌──────────────┐
│ Mode édition│ │ Mode lecture │
└──────┬──────┘ └──────────────┘
       │
       ▼
┌─────────────────────┐
│ Correction manuelle │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ POST /learn         │
│ (sauvegarde)        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ parsing_corrections │
│ (Supabase)          │
└─────────────────────┘
```

---

## ✅ Checklist de déploiement

- [ ] Créer la table `parsing_corrections` dans Supabase
- [ ] Vérifier les policies RLS
- [ ] Tester le parsing avec le texte d'Isabelle
- [ ] Vérifier que le mode édition s'affiche pour confiance < 1.0
- [ ] Tester la sauvegarde d'une correction
- [ ] Vérifier les stats d'apprentissage via `/learning-stats`
- [ ] Documenter les cas d'usage pour l'équipe

---

Créé le: 2024-12-23
Auteur: Claude Code
