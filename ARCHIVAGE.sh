#!/bin/bash
# Script d'archivage des prototypes obsolètes
# Date: 2025-12-09
# Auteur: Allan Sutton

set -e  # Arrêter en cas d'erreur

echo "============================================================"
echo "🗂️  Archivage des prototypes obsolètes"
echo "============================================================"
echo ""

# Répertoire de base
BASE_DIR="/Users/allansutton/Documents/assistant-gazelle-v5"
ARCHIVE_DIR="${BASE_DIR}/_archives/2025-12-09"

# Vérifier qu'on est dans le bon répertoire
if [ ! -f "${BASE_DIR}/requirements.txt" ]; then
    echo "❌ Erreur: requirements.txt introuvable. Êtes-vous dans le bon répertoire?"
    exit 1
fi

# Créer le dossier d'archives
echo "📁 Création du dossier d'archives..."
mkdir -p "${ARCHIVE_DIR}"

# Liste des éléments à archiver
ITEMS_TO_ARCHIVE=(
    "assistant-gazelle-web"
    "GazelleV5_Inventaire_Export"
)

# Archiver chaque élément
for item in "${ITEMS_TO_ARCHIVE[@]}"; do
    if [ -e "${BASE_DIR}/${item}" ]; then
        echo "📦 Archivage: ${item}..."
        mv "${BASE_DIR}/${item}" "${ARCHIVE_DIR}/"
        echo "   ✅ ${item} archivé"
    else
        echo "   ⚠️  ${item} introuvable (déjà archivé?)"
    fi
done

# Créer README d'archivage
echo ""
echo "📝 Création du README d'archivage..."
cat > "${ARCHIVE_DIR}/README.md" << 'EOF'
# Archives - 2025-12-09

## Contenu

### assistant-gazelle-web/
**Type**: Prototype Flask
**Créé par**: Cursor PC
**Date création**: Nov 2024
**Statut**: Obsolète - Remplacé par FastAPI

**Contenu archivé**:
- `app/inventory_routes.py` - Routes Flask inventaire
- `scripts/inventory_checker.py` - Script vérification stock (legacy)
- `scripts/export_inventory_data.py` - Script export (legacy)
- `data/gazelle_web.db` - Base SQLite locale
- `run_web.py` - Serveur Flask

**Remplacé par**:
- Backend: `api/inventaire.py` (FastAPI)
- Client DB: `core/supabase_storage.py`
- Scripts: `scripts/inventory_checker_v5.py`
- Base données: Supabase (PostgreSQL cloud)

---

### GazelleV5_Inventaire_Export/
**Type**: Scripts d'export Gazelle legacy
**Date création**: Dec 2024
**Statut**: Obsolète - Code copié et adapté

**Contenu archivé**:
- `inventory_checker.py` - Vérification stock (schéma Gazelle legacy)
- `export_inventory_data.py` - Export données Gazelle
- `INSTRUCTIONS_IMPORT.md` - Instructions d'import
- `requirements.txt` - Dépendances

**Différences avec V5**:
- Tables Gazelle: `inv.Products`, `inv.Inventory`, `inv.ProductDisplay`
- Tables V5: `produits_catalogue`, `inventaire_techniciens`, `transactions_inventaire`
- Connexion: psycopg2 directe vs `SupabaseStorage` client

**Remplacé par**:
- `scripts/inventory_checker_v5.py` (adapté pour V5)
- Utilise le schéma Supabase V5
- Intégré avec `core/supabase_storage.py`

---

## Raison de l'archivage

Ces prototypes ont servi à développer et tester les fonctionnalités d'inventaire.
Le code utile a été extrait, adapté et intégré au projet principal FastAPI + React.

**Chronologie**:
1. Nov 2024: Cursor PC crée `assistant-gazelle-web/` (prototype Flask)
2. Dec 2024: Scripts Gazelle legacy exportés dans `GazelleV5_Inventaire_Export/`
3. Dec 9 2024: Intégration complète dans projet principal V5
4. Dec 9 2024: Archivage des prototypes

## Conservation

Ces archives sont conservées uniquement pour référence historique et audit.

**⚠️ NE PAS UTILISER CE CODE DIRECTEMENT**

Utilisez le projet principal:
- Backend: `/api/inventaire.py`
- Scripts: `/scripts/inventory_checker_v5.py`
- Documentation: `/docs/INTEGRATION_INVENTAIRE_COMPLETE.md`

## Restauration (si nécessaire)

Pour consulter le code archivé:
```bash
cd /Users/allansutton/Documents/assistant-gazelle-v5/_archives/2025-12-09/
ls -la
```

Pour restaurer (déconseillé):
```bash
mv _archives/2025-12-09/assistant-gazelle-web .
```

---

**Date d'archivage**: 2025-12-09
**Archivé par**: Allan Sutton
**Statut**: ARCHIVÉ - NE PAS UTILISER
EOF

echo "   ✅ README créé"

# Résumé
echo ""
echo "============================================================"
echo "✅ Archivage terminé"
echo "============================================================"
echo ""
echo "📂 Emplacement des archives:"
echo "   ${ARCHIVE_DIR}"
echo ""
echo "📦 Éléments archivés:"
for item in "${ITEMS_TO_ARCHIVE[@]}"; do
    if [ -e "${ARCHIVE_DIR}/${item}" ]; then
        SIZE=$(du -sh "${ARCHIVE_DIR}/${item}" | cut -f1)
        echo "   ✅ ${item} (${SIZE})"
    fi
done
echo ""
echo "📁 Structure du projet maintenant:"
echo "   assistant-gazelle-v5/"
echo "   ├── api/                    # Backend FastAPI"
echo "   ├── core/                   # Logique métier"
echo "   ├── modules/                # Modules fonctionnels"
echo "   ├── scripts/                # Scripts automation"
echo "   ├── frontend/               # Interface React"
echo "   ├── data/                   # Données statiques"
echo "   ├── docs/                   # Documentation"
echo "   └── _archives/              # Archives (nouveaux)"
echo ""
echo "✨ Projet nettoyé et organisé!"
echo ""
echo "⏭️  Prochaines étapes:"
echo "   1. Vérifier que tout fonctionne:"
echo "      python3 -m uvicorn api.main:app --reload"
echo "   2. Commit les changements:"
echo "      git add ."
echo "      git commit -m 'Archivage prototypes obsolètes'"
echo "   3. Consulter la documentation:"
echo "      cat docs/ARCHITECTURE_PROJET_COMPLET.md"
echo ""
