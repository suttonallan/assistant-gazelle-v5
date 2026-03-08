#!/usr/bin/env bash
# =============================================================================
# batch_fix.sh — Script de correction en batch
# Assistant Gazelle V5 (Python backend + React frontend)
#
# Usage:
#   ./scripts/batch_fix.sh          # Tout corriger (Python + Frontend)
#   ./scripts/batch_fix.sh python   # Python seulement
#   ./scripts/batch_fix.sh frontend # Frontend seulement
#   ./scripts/batch_fix.sh --check  # Mode vérification (sans modifier)
# =============================================================================

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

MODE="${1:-all}"
CHECK_ONLY=false
ERRORS=0
FIXES=0

if [[ "$MODE" == "--check" ]]; then
    CHECK_ONLY=true
    MODE="${2:-all}"
fi

log_info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERREUR]${NC} $1"; ERRORS=$((ERRORS + 1)); }
log_fix()   { echo -e "${GREEN}[FIX]${NC} $1"; FIXES=$((FIXES + 1)); }

# =============================================================================
# Installation des outils si nécessaire
# =============================================================================
ensure_python_tools() {
    local tools_needed=()
    command -v ruff &>/dev/null || tools_needed+=(ruff)
    python3 -c "import autopep8" 2>/dev/null || tools_needed+=(autopep8)

    if [[ ${#tools_needed[@]} -gt 0 ]]; then
        log_info "Installation des outils Python: ${tools_needed[*]}"
        pip install --quiet "${tools_needed[@]}"
    fi
}

ensure_frontend_tools() {
    if [[ -d "$ROOT_DIR/frontend/node_modules" ]]; then
        return 0
    fi
    log_info "Installation des dépendances frontend..."
    (cd "$ROOT_DIR/frontend" && npm install --silent)
}

# =============================================================================
# Corrections Python
# =============================================================================
fix_python() {
    log_info "━━━ Correction Python ━━━"
    ensure_python_tools

    local py_dirs=("api" "core" "modules" "scripts" "config")
    local py_files=()

    for dir in "${py_dirs[@]}"; do
        if [[ -d "$ROOT_DIR/$dir" ]]; then
            while IFS= read -r -d '' f; do
                py_files+=("$f")
            done < <(find "$ROOT_DIR/$dir" -name "*.py" -type f -print0 2>/dev/null)
        fi
    done

    # Fichiers Python à la racine
    while IFS= read -r -d '' f; do
        py_files+=("$f")
    done < <(find "$ROOT_DIR" -maxdepth 1 -name "*.py" -type f -print0 2>/dev/null)

    local total=${#py_files[@]}
    log_info "Fichiers Python trouvés: $total"

    if [[ $total -eq 0 ]]; then
        log_warn "Aucun fichier Python trouvé."
        return 0
    fi

    # --- 1. Ruff: lint + auto-fix ---
    log_info "Ruff: analyse et correction..."
    if command -v ruff &>/dev/null; then
        if $CHECK_ONLY; then
            if ruff check "${py_files[@]}" 2>/dev/null; then
                log_ok "Ruff: aucun problème détecté"
            else
                log_error "Ruff: problèmes détectés (lancer sans --check pour corriger)"
            fi
        else
            local ruff_output
            ruff_output=$(ruff check --fix --unsafe-fixes "${py_files[@]}" 2>&1) || true
            if echo "$ruff_output" | grep -q "Fixed"; then
                log_fix "Ruff: corrections appliquées"
                echo "$ruff_output" | grep "Fixed" | head -5
            else
                log_ok "Ruff: aucun problème"
            fi
        fi
    fi

    # --- 2. Ruff format ---
    log_info "Ruff format: formatage du code..."
    if command -v ruff &>/dev/null; then
        if $CHECK_ONLY; then
            if ruff format --check "${py_files[@]}" 2>/dev/null; then
                log_ok "Ruff format: code déjà formaté"
            else
                log_error "Ruff format: fichiers à reformater"
            fi
        else
            local fmt_output
            fmt_output=$(ruff format "${py_files[@]}" 2>&1) || true
            if echo "$fmt_output" | grep -q "file"; then
                log_fix "Ruff format: fichiers reformatés"
            else
                log_ok "Ruff format: rien à reformater"
            fi
        fi
    fi

    # --- 3. Corrections manuelles courantes ---
    log_info "Corrections manuelles..."
    local manual_fixes=0

    for f in "${py_files[@]}"; do
        # Supprimer les espaces en fin de ligne (trailing whitespace)
        if grep -qP '\s+$' "$f" 2>/dev/null; then
            if ! $CHECK_ONLY; then
                sed -i 's/[[:space:]]*$//' "$f"
            fi
            manual_fixes=$((manual_fixes + 1))
        fi

        # Assurer un saut de ligne final
        if [[ -s "$f" ]] && [[ "$(tail -c 1 "$f" | wc -l)" -eq 0 ]]; then
            if ! $CHECK_ONLY; then
                echo "" >> "$f"
            fi
            manual_fixes=$((manual_fixes + 1))
        fi
    done

    if [[ $manual_fixes -gt 0 ]]; then
        if $CHECK_ONLY; then
            log_error "$manual_fixes fichiers avec espaces en fin de ligne ou sans saut de ligne final"
        else
            log_fix "$manual_fixes fichiers: espaces en fin de ligne / saut de ligne final"
        fi
    else
        log_ok "Pas de trailing whitespace ni de saut de ligne manquant"
    fi

    # --- 4. Vérification des imports inutilisés ---
    log_info "Vérification des imports (ruff)..."
    if command -v ruff &>/dev/null; then
        local unused
        unused=$(ruff check --select F401 "${py_files[@]}" 2>/dev/null | head -20) || true
        if [[ -n "$unused" ]]; then
            log_warn "Imports potentiellement inutilisés (F401):"
            echo "$unused" | head -10
        else
            log_ok "Pas d'imports inutilisés détectés"
        fi
    fi

    # --- 5. Détection de problèmes de sécurité basiques ---
    log_info "Vérification sécurité basique..."
    local security_issues=0

    for f in "${py_files[@]}"; do
        # Détection de eval() potentiellement dangereux
        if grep -nP '\beval\s*\(' "$f" 2>/dev/null | grep -v '^\s*#' | grep -v 'test' >/dev/null; then
            log_warn "eval() trouvé dans: $f"
            security_issues=$((security_issues + 1))
        fi

        # Détection de exec() potentiellement dangereux
        if grep -nP '\bexec\s*\(' "$f" 2>/dev/null | grep -v '^\s*#' >/dev/null; then
            log_warn "exec() trouvé dans: $f"
            security_issues=$((security_issues + 1))
        fi
    done

    if [[ $security_issues -eq 0 ]]; then
        log_ok "Pas de problèmes de sécurité basiques détectés"
    fi
}

# =============================================================================
# Corrections Frontend (React/JS)
# =============================================================================
fix_frontend() {
    log_info "━━━ Correction Frontend ━━━"

    local frontend_dir="$ROOT_DIR/frontend"
    if [[ ! -d "$frontend_dir/src" ]]; then
        log_warn "Dossier frontend/src introuvable, frontend ignoré."
        return 0
    fi

    local jsx_files=()
    while IFS= read -r -d '' f; do
        jsx_files+=("$f")
    done < <(find "$frontend_dir/src" \( -name "*.jsx" -o -name "*.js" -o -name "*.ts" -o -name "*.tsx" \) -type f -print0 2>/dev/null)

    local total=${#jsx_files[@]}
    log_info "Fichiers JS/JSX trouvés: $total"

    if [[ $total -eq 0 ]]; then
        log_warn "Aucun fichier frontend trouvé."
        return 0
    fi

    # --- 1. Trailing whitespace + newline finale ---
    log_info "Nettoyage espaces et sauts de ligne..."
    local cleaned=0
    for f in "${jsx_files[@]}"; do
        if grep -qP '\s+$' "$f" 2>/dev/null; then
            if ! $CHECK_ONLY; then
                sed -i 's/[[:space:]]*$//' "$f"
            fi
            cleaned=$((cleaned + 1))
        fi
        if [[ -s "$f" ]] && [[ "$(tail -c 1 "$f" | wc -l)" -eq 0 ]]; then
            if ! $CHECK_ONLY; then
                echo "" >> "$f"
            fi
            cleaned=$((cleaned + 1))
        fi
    done

    if [[ $cleaned -gt 0 ]]; then
        if $CHECK_ONLY; then
            log_error "$cleaned fichiers frontend avec problèmes de whitespace"
        else
            log_fix "$cleaned fichiers frontend nettoyés"
        fi
    else
        log_ok "Frontend: pas de whitespace superflu"
    fi

    # --- 2. Détection console.log restants ---
    log_info "Détection des console.log..."
    local console_count=0
    for f in "${jsx_files[@]}"; do
        local count
        count=$(grep -c 'console\.log' "$f" 2>/dev/null) || count=0
        console_count=$((console_count + count))
    done

    if [[ $console_count -gt 0 ]]; then
        log_warn "$console_count console.log trouvés dans le frontend"
        grep -rn 'console\.log' "$frontend_dir/src" --include="*.jsx" --include="*.js" 2>/dev/null | head -10
    else
        log_ok "Pas de console.log dans le frontend"
    fi

    # --- 3. Vérification du build ---
    if ! $CHECK_ONLY; then
        log_info "Vérification du build frontend..."
        if (cd "$frontend_dir" && npm run build 2>&1) >/dev/null 2>&1; then
            log_ok "Build frontend réussi"
        else
            log_error "Build frontend échoué — vérifier les erreurs manuellement"
        fi
    fi

    # --- 4. Détection de clés/secrets en dur ---
    log_info "Détection de secrets potentiels..."
    local secrets_found=0
    for f in "${jsx_files[@]}"; do
        if grep -nP '(sk-|api_key|password|secret)\s*[:=]\s*["\x27][^"\x27]{8,}' "$f" 2>/dev/null | grep -v 'process\.env' | grep -v 'import\.meta\.env' >/dev/null; then
            log_warn "Secret potentiel dans: $f"
            secrets_found=$((secrets_found + 1))
        fi
    done

    if [[ $secrets_found -eq 0 ]]; then
        log_ok "Pas de secrets en dur détectés"
    fi
}

# =============================================================================
# Corrections CSS
# =============================================================================
fix_css() {
    log_info "━━━ Correction CSS ━━━"

    local css_files=()
    while IFS= read -r -d '' f; do
        css_files+=("$f")
    done < <(find "$ROOT_DIR/frontend/src" -name "*.css" -type f -print0 2>/dev/null)

    local total=${#css_files[@]}
    log_info "Fichiers CSS trouvés: $total"

    for f in "${css_files[@]}"; do
        # Trailing whitespace
        if grep -qP '\s+$' "$f" 2>/dev/null; then
            if ! $CHECK_ONLY; then
                sed -i 's/[[:space:]]*$//' "$f"
            fi
            log_fix "CSS nettoyé: $(basename "$f")"
        fi
    done
}

# =============================================================================
# Vérification .env et fichiers sensibles
# =============================================================================
check_sensitive_files() {
    log_info "━━━ Vérification fichiers sensibles ━━━"

    # Vérifier que .env n'est pas commité
    if git ls-files --error-unmatch .env 2>/dev/null; then
        log_error ".env est suivi par git — à ajouter dans .gitignore!"
    else
        log_ok ".env n'est pas suivi par git"
    fi

    # Vérifier .gitignore
    if [[ -f "$ROOT_DIR/.gitignore" ]]; then
        for pattern in ".env" "node_modules" "__pycache__" "*.pyc" "dist"; do
            if grep -q "$pattern" "$ROOT_DIR/.gitignore" 2>/dev/null; then
                log_ok ".gitignore contient: $pattern"
            else
                log_warn ".gitignore manque: $pattern"
            fi
        done
    else
        log_error "Pas de fichier .gitignore!"
    fi
}

# =============================================================================
# Rapport final
# =============================================================================
print_report() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  RAPPORT DE CORRECTION EN BATCH${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    if $CHECK_ONLY; then
        echo -e "  Mode: ${YELLOW}VÉRIFICATION SEULEMENT${NC}"
    else
        echo -e "  Mode: ${GREEN}CORRECTION${NC}"
    fi

    echo -e "  Corrections appliquées: ${GREEN}${FIXES}${NC}"
    echo -e "  Erreurs/Avertissements: ${RED}${ERRORS}${NC}"
    echo ""

    if [[ $ERRORS -eq 0 ]]; then
        echo -e "  ${GREEN}✓ Tout est en ordre!${NC}"
    else
        echo -e "  ${YELLOW}⚠ $ERRORS problème(s) nécessitent attention${NC}"
    fi

    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# =============================================================================
# Exécution
# =============================================================================
echo ""
echo -e "${BLUE}╔═══════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Script de Correction en Batch — Gazelle V5     ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════╝${NC}"
echo ""

case "$MODE" in
    python)
        fix_python
        ;;
    frontend)
        fix_frontend
        fix_css
        ;;
    all)
        fix_python
        fix_frontend
        fix_css
        check_sensitive_files
        ;;
    *)
        echo "Usage: $0 [all|python|frontend] [--check]"
        echo "       $0 --check [all|python|frontend]"
        exit 1
        ;;
esac

print_report
exit $ERRORS
