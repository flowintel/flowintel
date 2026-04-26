#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VERSION_FILE="$SCRIPT_DIR/version"
CONF_DIR="$SCRIPT_DIR/conf"
CONFIG_FILE="$CONF_DIR/config.py"
DEFAULT_FILE="$CONF_DIR/config.py.default"
CONFIG_MODULE_FILE="$CONF_DIR/config_module.py"
DEFAULT_MODULE_FILE="$CONF_DIR/config_module.py.default"

VENV_DIR="${VENV_DIR:-.venv}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

function print_status { echo -e "${GREEN}[✓]${NC} $1"; }
function print_error { echo -e "${RED}[✗]${NC} $1"; }
function print_warning { echo -e "${YELLOW}[!]${NC} $1"; }
function print_info { echo -e "${BLUE}[i]${NC} $1"; }

SCRIPT_NAME="$(basename "$0")"

function verify_all {
    echo ""
    echo "========================================"
    echo "  Vérification de l'environnement Flowintel"
    echo "========================================"
    echo ""

    local errors=0
    local warnings=0

    print_info "Vérification de Python..."
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
        print_status "Python trouvé: $PYTHON_VERSION"
    else
        print_error "Python 3 non trouvé"
        errors=$((errors + 1))
    fi

    print_info "Vérification de uv..."
    if command -v uv &> /dev/null; then
        UV_VERSION=$(uv --version | awk '{print $2}')
        print_status "uv trouvé: $UV_VERSION"
    else
        print_error "uv non trouvé (installez avec: curl -LsSf https://astral.sh/uv/install.sh | sh)"
        errors=$((errors + 1))
    fi

    print_info "Vérification de Bun..."
    if command -v bun &> /dev/null; then
        BUN_VERSION=$(bun --version | awk '{print $1}')
        print_status "Bun trouvé: $BUN_VERSION"
    else
        print_warning "Bun non trouvé (installez avec: curl -fsSL https://bun.sh/install | bash)"
        warnings=$((warnings + 1))
    fi

    print_info "Vérification de Node.js..."
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        print_status "Node.js trouvé: $NODE_VERSION"
    else
        print_warning "Node.js non trouvé"
        warnings=$((warnings + 1))
    fi

    print_info "Vérification de Git..."
    if command -v git &> /dev/null; then
        GIT_VERSION=$(git --version | awk '{print $3}')
        print_status "Git trouvé: $GIT_VERSION"
    else
        print_error "Git non trouvé"
        errors=$((errors + 1))
    fi

    print_info "Vérification du fichier de version..."
    if [ -f "$VERSION_FILE" ]; then
        APP_VERSION=$(cat "$VERSION_FILE")
        print_status "Version Flowintel: $APP_VERSION"
    else
        print_error "Fichier version non trouvé"
        errors=$((errors + 1))
    fi

    print_info "Vérification des fichiers de configuration..."
    if [ -f "$CONFIG_FILE" ]; then
        print_status "config.py trouvé"
    elif [ -f "$DEFAULT_FILE" ]; then
        cp "$DEFAULT_FILE" "$CONFIG_FILE"
        print_status "config.py créé depuis default"
    else
        print_error "config.py et default non trouvés"
        errors=$((errors + 1))
    fi

    if [ -f "$CONFIG_MODULE_FILE" ]; then
        print_status "config_module.py trouvé"
    elif [ -f "$DEFAULT_MODULE_FILE" ]; then
        cp "$DEFAULT_MODULE_FILE" "$CONFIG_MODULE_FILE"
        print_status "config_module.py créé depuis default"
    else
        print_error "config_module.py et default non trouvés"
        errors=$((errors + 1))
    fi

    print_info "Vérification des dépendances Python..."
    if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
        print_status "requirements.txt trouvé"
    else
        print_error "requirements.txt non trouvé"
        errors=$((errors + 1))
    fi

    print_info "Vérification des dépendances Node.js..."
    if [ -f "$SCRIPT_DIR/app/assets/package.json" ]; then
        print_status "package.json trouvé"
        if [ -f "$SCRIPT_DIR/app/assets/bun.lock" ]; then
            print_status "bun.lock trouvé"
        else
            print_warning "bun.lock absent"
            warnings=$((warnings + 1))
        fi
    fi

    print_info "Vérification de PostgreSQL..."
    if command -v psql &> /dev/null; then
        PSQL_VERSION=$(psql --version | awk '{print $3}')
        print_status "PostgreSQL trouvé: $PSQL_VERSION"
    else
        print_warning "PostgreSQL client non trouvé (optionnel si Docker)"
        warnings=$((warnings + 1))
    fi

    print_info "Vérification de Valkey/Redis..."
    if command -v valkey-server &> /dev/null; then
        VALKEY_VERSION=$(valkey-server --version | awk '{print $2}')
        print_status "Valkey trouvé: $VALKEY_VERSION"
    elif command -v redis-server &> /dev/null; then
        REDIS_VERSION=$(redis-server --version | awk '{print $2}')
        print_status "Redis trouvé: $REDIS_VERSION"
    else
        print_warning "Valkey/Redis non trouvé"
        warnings=$((warnings + 1))
    fi

    print_info "Vérification de screen..."
    if command -v screen &> /dev/null; then
        SCREEN_VERSION=$(screen --version | awk '{print $3}')
        print_status "screen trouvé: $SCREEN_VERSION"
    else
        print_warning "screen non trouvé"
        warnings=$((warnings + 1))
    fi

    print_info "Vérification de misp-modules..."
    if command -v misp-modules &> /dev/null; then
        MISP_MODULES_VERSION=$(misp-modules --version 2>&1 | head -1 || echo "inconnu")
        print_status "misp-modules trouvé: $MISP_MODULES_VERSION"
    else
        print_warning "misp-modules non trouvé (optionnel)"
        warnings=$((warnings + 1))
    fi

    print_info "Vérification de Pandoc..."
    if command -v pandoc &> /dev/null; then
        PANDOC_VERSION=$(pandoc --version | head -1 | awk '{print $2}')
        print_status "Pandoc trouvé: $PANDOC_VERSION"
    else
        print_warning "Pandoc non trouvé"
        warnings=$((warnings + 1))
    fi

    echo ""
    echo "========================================"
    if [ $errors -eq 0 ]; then
        print_status "Toutes les vérifications passées"
    else
        print_warning "$errors erreur(s), $warnings avertissement(s)"
    fi
    echo "========================================"
    echo ""

    return $errors
}

function migrate {
    echo ""
    echo "========================================"
    echo "  Migration vers uv et bun"
    echo "========================================"
    echo ""

    print_info "Génération de uv.lock..."
    uv pip compile requirements.txt -o uv.lock --python-version 3.12 2>/dev/null || true
    if [ -f "uv.lock" ]; then
        print_status "uv.lock généré"
    else
        print_error "Échec de la génération de uv.lock"
    fi

    print_info "Migration Node.js vers bun.lock..."
    cd "$SCRIPT_DIR/app/assets"

    if [ -f "bun.lock" ]; then
        print_status "bun.lock déjà présent"
    elif [ -f "package.json" ]; then
        bun install
        print_status "bun.lock généré"
    fi

    cd "$SCRIPT_DIR"
    print_status "Migration terminée"
}

function install_deps {
    echo ""
    echo "========================================"
    echo "  Installation des dépendances"
    echo "========================================"
    echo ""

    if [ ! -d "$VENV_DIR" ]; then
        print_info "Création du virtualenv..."
        python3 -m venv "$VENV_DIR"
        print_status "Virtualenv créé"
    fi

    print_info "Activation du virtualenv..."
    source "$VENV_DIR/bin/activate"

    print_info "Installation des dépendances Python avec uv..."
    uv pip install -r requirements.txt
    print_status "Dépendances Python installées"

    cd "$SCRIPT_DIR/app/assets"
    if [ -f "package.json" ]; then
        print_info "Installation des dépendances Node.js avec Bun..."
        bun install
        print_status "Dépendances Node.js installées"
    fi

    cd "$SCRIPT_DIR"
    print_status "Installation terminée"
}

function delete_temp_files {
    echo ""
    echo "========================================"
    echo "  Suppression des fichiers temporaires"
    echo "========================================"
    echo ""

    local deleted=0

    if [ -f "$SCRIPT_DIR/app/assets/package-lock.json" ]; then
        rm "$SCRIPT_DIR/app/assets/package-lock.json"
        print_status "package-lock.json supprimé"
        deleted=$((deleted + 1))
    fi

    if [ $deleted -eq 0 ]; then
        print_info "Aucun fichier temporaire à supprimer"
    else
        print_status "$deleted fichier(s) supprimé(s)"
    fi
}

function launch {
    print_info "Lancement de Flowintel..."

    source "$VENV_DIR/bin/activate" 2>/dev/null || true
    export FLASKENV="${FLASKENV:-development}"
    export HISTORY_DIR="$SCRIPT_DIR/history"

    mkdir -p logs

    print_info "Démarrage de Valkey..."
    if ! pgrep -x "valkey-server" > /dev/null; then
        screen -dmS "valkey" bash -c "valkey-server --port 6379 2>&1 | tee -a logs/valkey.log"
        sleep 2
        print_status "Valkey démarré"
    else
        print_status "Valkey déjà en cours"
    fi

    print_info "Démarrage du bot de notifications..."
    screen -dmS "fcm" bash -c "python3 startNotif.py 2>&1 | tee -a logs/fcm.log"
    sleep 1
    print_status "Bot notifications démonté"

    print_info "Lancement de l'application Flask..."
    python3 app.py
}

function usage {
    echo "Usage: $SCRIPT_NAME [commande]"
    echo ""
    echo "Commandes disponibles:"
    echo "  verify, check     Vérifier l'environnement et les dépendances"
    echo "  migrate          Migrer vers uv et bun (génère uv.lock, bun.lock)"
    echo "  install          Installer les dépendances"
    echo "  clean            Supprimer les fichiers temporaires"
    echo "  launch, run      Lancer l'application"
    echo "  all              Vérifier + nettoyer + installer + lancer"
    echo "  help             Afficher cette aide"
    echo ""
    echo "Variables d'environnement:"
    echo "  VENV_DIR         Répertoire du virtualenv (défaut: .venv)"
    echo "  FLASKENV         Environnement Flask (development/production)"
    echo "  DB_HOST          Hôte PostgreSQL"
    echo "  DB_PORT          Port PostgreSQL"
    echo "  DB_USER          Utilisateur PostgreSQL"
    echo ""
}

case "${1:-}" in
    verify|v|check)
        verify_all
        ;;
    migrate|m)
        migrate
        ;;
    install|i)
        install_deps
        ;;
    delete_temp_files|clean|c)
        delete_temp_files
        ;;
    launch|run|l)
        launch
        ;;
    help|h|--help)
        usage
        ;;
    all|a)
        verify_all || exit 1
        delete_temp_files
        install_deps
        launch
        ;;
    *)
        verify_all || exit 1
        delete_temp_files
        install_deps
        launch
        ;;
esac