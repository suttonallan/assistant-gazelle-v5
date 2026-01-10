# ⚙️ Configuration des Déductions Intelligentes

## Vue d'ensemble

La Configuration des Déductions Intelligentes permet de gérer 3 systèmes de déduction automatique d'inventaire:

1. **🌐 Règle Globale**: Déduction automatique de toutes les fournitures/accessoires facturés
2. **🔧 Mapping de Services**: Recettes prédéfinies (Service X → consomme Y matériaux)
3. **🔍 Détection par Mots-Clés**: Scan des notes de factures pour détecter des consommations

Plus un système de **👁️ Preview Sécurisé** pour valider avant d'appliquer.

## Accès à l'interface

**Navigation**: Inventaire → Configuration → 🔧 Configuration Déductions

**Prérequis**:
- Être administrateur (Allan uniquement pour l'instant)
- Tables Supabase créées (voir scripts/create_deduction_tables.sql)

## 1. Règle Globale Automatique 🌐

### Principe

Active la déduction automatique pour TOUS les items de type "fourniture" ou "accessoire" présents sur les factures Gazelle.

### Activation

```
Interface → Configuration Déductions → Règle Globale
Cliquer sur "Activer"
```

### Comportement

Lorsqu'activée:
1. Le système analyse toutes les factures traitées
2. Pour chaque line item de type "fourniture" ou "accessoire":
   - Récupère le code produit
   - Récupère la quantité
   - Identifie le technicien de la facture
   - Crée une déduction automatique dans sync_logs
   - Met à jour l'inventaire du technicien (stock -= quantité)

### Types d'items couverts

Par défaut:
- `fourniture`
- `accessoire`

Configurable via l'API si nécessaire.

### Exemple

**Facture #2024-001 (Allan)**:
- Line Item: "Buvard blanc standard" (type: fourniture, qté: 1)
- Line Item: "Hygrostat sec" (type: accessoire, qté: 1)

**Résultat automatique**:
- Déduction: BUV-001 × 1 pour Allan
- Déduction: HYGRO-SEC × 1 pour Allan
- Logs créés dans sync_logs avec script_name = "Deduction_Inventaire_Auto"

### Configuration technique

**Table**: `system_settings`
**Clé**: `deduction_global_rule`
**Format**:
```json
{
  "enabled": true,
  "item_types": ["fourniture", "accessoire"],
  "description": "Toute fourniture ou accessoire sur facture déclenche déduction automatique",
  "updated_at": "2026-01-08T15:30:00Z"
}
```

## 2. Mapping de Services (Recettes) 🔧

### Principe

Définit des "recettes" prédéfinies: Si Service X est facturé → Déduire automatiquement Y matériaux.

### Exemples de Recettes

#### Entretien Annuel PLS
```
Service: "Entretien annuel PLS"
ID Gazelle: mit_EntretienAnnuelPLS
Matériaux consommés:
  - BUV-001 (Buvard) × 1
  - GAIN-001 (Gaine vinyle) × 1
```

#### Grand Entretien
```
Service: "Grand entretien"
ID Gazelle: mit_GrandEntretien
Matériaux consommés:
  - BUV-001 (Buvard) × 2
  - GAIN-001 (Gaine vinyle) × 1
  - DOUB-001 (Doublure feutre) × 1 (optionnel)
```

#### Tuning Complet
```
Service: "Tuning complet"
ID Gazelle: mit_TuningComplet
Matériaux consommés:
  - FEUTR-MART (Feutre marteau) × 3
  - COLLE-001 (Colle spéciale) × 0.5
```

### Création d'une règle

**Via Interface**:
1. Configuration Déductions → Services (Recettes)
2. Cliquer "+ Nouvelle Règle"
3. Remplir:
   - ID Service Gazelle (ex: `mit_EntretienAnnuelPLS`)
   - Code Produit (optionnel, pour référence locale)
4. Ajouter matériaux:
   - Code produit (ex: `BUV-001`)
   - Quantité (ex: `1.0`)
   - Optionnel (cocher si le matériau n'est pas toujours utilisé)
5. Cliquer "Enregistrer"

**Via API**:
```bash
curl -X POST http://localhost:5174/api/inventaire/service-consumption/rules/batch \
  -H "Content-Type: application/json" \
  -d '{
    "service_gazelle_id": "mit_EntretienAnnuelPLS",
    "service_code_produit": "ENT-PLS",
    "materials": [
      {"material_code_produit": "BUV-001", "quantity": 1.0, "is_optional": false},
      {"material_code_produit": "GAIN-001", "quantity": 1.0, "is_optional": false}
    ]
  }'
```

### Table Supabase

**Table**: `service_inventory_consumption`

**Structure**:
```sql
CREATE TABLE service_inventory_consumption (
    id SERIAL PRIMARY KEY,
    service_gazelle_id TEXT NOT NULL,
    service_code_produit TEXT,
    material_code_produit TEXT NOT NULL,
    quantity FLOAT DEFAULT 1.0,
    is_optional BOOLEAN DEFAULT false,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(service_gazelle_id, material_code_produit)
);
```

### Workflow d'application

1. Facture détectée avec Service X
2. Lookup dans `service_inventory_consumption`: `WHERE service_gazelle_id = X`
3. Pour chaque matériau trouvé:
   - Calculer quantité totale = `quantity × qté_service`
   - Créer déduction dans sync_logs
   - Mettre à jour inventaire technicien

## 3. Détection par Mots-Clés 🔍

### Principe

Scanne les notes/descriptions des factures pour détecter des mots-clés spécifiques et déclencher des déductions.

### Cas d'usage

Idéal pour les cas exceptionnels mentionnés dans les notes:
- "Buvard remplacé"
- "Hygrostat sec installé"
- "Corde cassée, remplacée par..."
- "Feutre de marteau usé"

### Exemples de règles

#### Règle 1: Buvard remplacé
```
Mot-clé: "Buvard remplacé"
→ Déduire: BUV-001 × 1
Sensible à la casse: Non
```

#### Règle 2: Hygrostat sec
```
Mot-clé: "Hygrostat sec"
→ Déduire: HYGRO-SEC × 1
Sensible à la casse: Non
Notes: "Installation d'un hygrostat sec mentionnée dans les notes"
```

#### Règle 3: Corde remplacée
```
Mot-clé: "corde remplacée"
→ Déduire: CORDE-STD × 1
Sensible à la casse: Non
```

### Création d'une règle

**Via Interface**:
1. Configuration Déductions → Mots-Clés
2. Cliquer "+ Nouvelle Règle"
3. Remplir:
   - Mot-clé à détecter (ex: "Buvard remplacé")
   - Code produit à déduire (ex: "BUV-001")
   - Quantité (ex: 1.0)
   - Sensible à la casse (généralement: Non)
   - Notes explicatives (optionnel)
4. Cliquer "Enregistrer"

**Via API**:
```bash
curl -X POST http://localhost:5174/api/inventaire/deduction-config/keyword-rules \
  -H "Content-Type: application/json" \
  -d '{
    "keyword": "Buvard remplacé",
    "material_code_produit": "BUV-001",
    "quantity": 1.0,
    "case_sensitive": false,
    "notes": "Déduction automatique quand buvard mentionné dans les notes"
  }'
```

### Table Supabase

**Table**: `keyword_deduction_rules`

**Structure**:
```sql
CREATE TABLE keyword_deduction_rules (
    id SERIAL PRIMARY KEY,
    keyword TEXT NOT NULL,
    material_code_produit TEXT NOT NULL,
    quantity FLOAT DEFAULT 1.0,
    case_sensitive BOOLEAN DEFAULT false,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Algorithme de détection

```python
for invoice in recent_invoices:
    notes = invoice.get_notes()  # ou description

    for rule in keyword_rules:
        keyword = rule.keyword

        if rule.case_sensitive:
            match = keyword in notes
        else:
            match = keyword.lower() in notes.lower()

        if match:
            # Créer déduction
            create_deduction(
                material_code=rule.material_code_produit,
                quantity=rule.quantity,
                technician=invoice.technician
            )
```

## 4. Preview Sécurisé 👁️

### Principe

**CRITIQUE**: Avant d'appliquer les déductions définitivement, le système génère un aperçu complet pour validation manuelle.

### Pourquoi c'est important

Protection contre:
- ❌ Erreurs de frappe dans Gazelle
- ❌ Règles mal configurées
- ❌ Déductions en double
- ❌ Stock négatif inattendu
- ❌ Mauvais mapping technicien

### Utilisation

1. Configuration Déductions → Preview Sécurisé
2. Sélectionner période (ex: 7 derniers jours)
3. Cliquer "🔄 Générer Preview"
4. **IMPORTANT**: Analyser les résultats:
   - Vérifier le nombre total de déductions
   - Vérifier par technicien
   - Vérifier les matériaux déduits
   - Regarder les avertissements
5. Si tout est correct: Cliquer "✅ Appliquer"

### Format du Preview

```json
{
  "success": true,
  "total_deductions": 12,
  "by_technician": {
    "Allan": [
      {
        "invoice_number": "2024-001",
        "service": "Entretien annuel PLS",
        "material_code": "BUV-001",
        "quantity": 1.0,
        "source": "service_rule"
      },
      {
        "invoice_number": "2024-002",
        "service": "Notes: Buvard remplacé",
        "material_code": "BUV-001",
        "quantity": 1.0,
        "source": "keyword_rule"
      }
    ],
    "Vincent": [
      {
        "invoice_number": "2024-003",
        "service": "Grand entretien",
        "material_code": "BUV-001",
        "quantity": 2.0,
        "source": "service_rule"
      }
    ]
  },
  "warnings": [
    "Stock de BUV-001 pour Vincent deviendrait négatif (-2)",
    "Matériau HYGRO-SEC-999 inconnu dans le catalogue"
  ],
  "period": {
    "days": 7,
    "invoices_analyzed": 10
  }
}
```

### Avertissements possibles

| Type | Message | Action recommandée |
|------|---------|-------------------|
| Stock négatif | "Stock de BUV-001 pour Allan deviendrait négatif (-5)" | Vérifier stock initial ou ajuster règles |
| Matériau inconnu | "Matériau XYZ-999 inconnu dans le catalogue" | Vérifier code produit dans la règle |
| Facture sans technicien | "Facture #2024-001 sans technicien identifiable" | Vérifier user_id Gazelle |
| Quantité anormale | "Déduction de 100× CORDE-001 sur une facture (anormal)" | Vérifier quantité dans règle |

### Application des déductions

Une fois validé, cliquer "✅ Appliquer" lance:
1. Création des logs dans `sync_logs` (script_name = "Deduction_Inventaire_Auto")
2. Mise à jour des stocks dans `inventaire_techniciens`
3. Retour des statistiques d'application

## Priorité des Règles

Lorsque plusieurs règles s'appliquent simultanément, l'ordre de priorité est:

1. **Mapping de Services** (le plus précis)
2. **Détection par Mots-Clés**
3. **Règle Globale** (le plus général)

**Important**: Une même déduction peut être créée plusieurs fois si plusieurs règles s'appliquent. Le preview permet de détecter ces doublons.

## Configuration Recommandée

### Étape 1: Commencer par les services fréquents

Créer des règles pour:
- Entretien annuel PLS
- Grand entretien
- Tuning complet
- Réparation standard

### Étape 2: Ajouter les mots-clés pour exceptions

Ajouter des règles pour:
- "Buvard remplacé"
- "Hygrostat sec"
- "Corde cassée"
- "Feutre usé"

### Étape 3: Activer la règle globale (optionnel)

Si la majorité des fournitures sont bien référencées, activer la règle globale pour automatiser complètement.

### Étape 4: Tester avec Preview

Toujours utiliser le Preview sur 1-2 jours avant de l'étendre à 7-30 jours.

## API Endpoints

### Règle Globale

```bash
# Récupérer config
GET /api/inventaire/deduction-config/global-rule

# Activer/Désactiver
PUT /api/inventaire/deduction-config/global-rule
Body: {"enabled": true, "item_types": ["fourniture", "accessoire"]}
```

### Services (Recettes)

```bash
# Lister toutes les règles
GET /api/inventaire/service-consumption/rules?group_by_service=true

# Créer règle simple
POST /api/inventaire/service-consumption/rules
Body: {
  "service_gazelle_id": "mit_EntretienPLS",
  "material_code_produit": "BUV-001",
  "quantity": 1.0
}

# Créer règle batch (plusieurs matériaux)
POST /api/inventaire/service-consumption/rules/batch
Body: {
  "service_gazelle_id": "mit_GrandEntretien",
  "materials": [
    {"material_code_produit": "BUV-001", "quantity": 2.0},
    {"material_code_produit": "GAIN-001", "quantity": 1.0}
  ]
}

# Supprimer règle
DELETE /api/inventaire/service-consumption/rules/{rule_id}
```

### Mots-Clés

```bash
# Lister toutes les règles
GET /api/inventaire/deduction-config/keyword-rules

# Créer règle
POST /api/inventaire/deduction-config/keyword-rules
Body: {
  "keyword": "Buvard remplacé",
  "material_code_produit": "BUV-001",
  "quantity": 1.0,
  "case_sensitive": false
}

# Supprimer règle
DELETE /api/inventaire/deduction-config/keyword-rules/{rule_id}
```

### Preview & Application

```bash
# Générer preview
POST /api/inventaire/deduction-config/preview?days=7

# Appliquer déductions
POST /api/inventaire/process-deductions?days=7
```

## Sécurité et Contrôles

### Permissions

- ✅ Admin (Allan): Accès complet à la configuration
- ❌ Techniciens: Lecture seule ou pas d'accès
- ❌ Gestionnaires: Lecture seule

### Validation des données

- Code produit doit exister dans `produits_catalogue`
- Quantité doit être > 0
- Service Gazelle ID format: `mit_...`
- Keyword minimum 3 caractères

### Logs d'audit

Toute modification de configuration est enregistrée:
- Qui a créé/modifié/supprimé
- Quand
- Quelle règle

## Troubleshooting

### Problème 1: Déductions non créées

**Symptôme**: Preview vide malgré des factures récentes

**Solutions**:
1. Vérifier que des règles existent
2. Vérifier les IDs Gazelle des services
3. Vérifier que les factures ont des line items
4. Vérifier le mapping technicien (user_id → nom)

### Problème 2: Stock négatif

**Symptôme**: Avertissement "Stock négatif" dans preview

**Solutions**:
1. Augmenter stock initial du technicien
2. Ajuster quantités dans les règles
3. Marquer certains matériaux comme "optionnels"

### Problème 3: Doublons de déductions

**Symptôme**: Même déduction créée 2×

**Solutions**:
1. Vérifier qu'une règle de service et une règle de mot-clé ne se chevauchent pas
2. Désactiver la règle globale si rules de services existent
3. Utiliser le preview pour détecter avant application

### Problème 4: Codes produits incorrects

**Symptôme**: Avertissement "Matériau XYZ inconnu"

**Solutions**:
1. Vérifier orthographe du code produit dans la règle
2. S'assurer que le produit existe dans `produits_catalogue`
3. Créer le produit si nécessaire

## Performance

### Métriques attendues

- **Preview 7 jours**: 2-5 secondes
- **Application 7 jours**: 5-10 secondes
- **100 règles actives**: Pas d'impact significatif

### Optimisations

- Index sur `service_gazelle_id` et `material_code_produit`
- Cache des règles en mémoire pendant traitement
- Traitement par batch de 100 factures

## Maintenance

### Mensuel

- Revoir les règles obsolètes
- Vérifier les avertissements fréquents
- Ajuster quantités selon la réalité

### Trimestriel

- Analyser les déductions pour détecter patterns
- Créer nouvelles règles pour services fréquents
- Nettoyer règles jamais utilisées

---

**Date**: 2026-01-08
**Auteur**: Claude
**Version**: 1.0
**Status**: ✅ Production Ready
