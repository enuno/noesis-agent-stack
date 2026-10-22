#!/bin/bash
# GitHub Actions Validator - Tool Installation Script
# Installs act and actionlint tools locally in the current directory

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLS_DIR="${SCRIPT_DIR}/.tools"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Create tools directory if it doesn't exist
mkdir -p "${TOOLS_DIR}"

# Function to install act
install_act() {
    log_info "Installing act (nektos/act)..."

    # Check if act already exists in tools directory
    if [ -f "${TOOLS_DIR}/act" ]; then
        log_warn "act already exists in ${TOOLS_DIR}, removing..."
        rm -f "${TOOLS_DIR}/act"
    fi

    # Check if act exists in PATH
    if command -v act &> /dev/null; then
        log_info "act found in PATH, creating symlink..."
        ln -sf "$(command -v act)" "${TOOLS_DIR}/act"
    else
        log_error "act is not installed and this Noesis-reviewed skill copy will not"
        log_error "auto-pipe https://raw.githubusercontent.com/nektos/act/master/install.sh into bash."
        log_warn  "Install act yourself (verify the script first), e.g.:"
        log_warn  "  curl --proto '=https' --tlsv1.2 -sSf https://raw.githubusercontent.com/nektos/act/master/install.sh -o /tmp/act-install.sh"
        log_warn  "  less /tmp/act-install.sh   # review it"
        log_warn  "  bash /tmp/act-install.sh -b \"${TOOLS_DIR}\""
        log_warn  "then re-run this script."
        return 1
    fi

    if [ -f "${TOOLS_DIR}/act" ]; then
        log_info "act installed successfully at ${TOOLS_DIR}/act"
        "${TOOLS_DIR}/act" --version
    else
        log_error "Failed to install act"
        return 1
    fi
}

# Function to install actionlint
install_actionlint() {
    log_info "Installing actionlint (rhysd/actionlint)..."

    # Check if actionlint already exists in tools directory
    if [ -f "${TOOLS_DIR}/actionlint" ]; then
        log_warn "actionlint already exists in ${TOOLS_DIR}, removing..."
        rm -f "${TOOLS_DIR}/actionlint"
    fi

    # Check if actionlint exists in PATH
    if command -v actionlint &> /dev/null; then
        log_info "actionlint found in PATH, creating symlink..."
        ln -sf "$(command -v actionlint)" "${TOOLS_DIR}/actionlint"
    else
        log_error "actionlint is not installed and this Noesis-reviewed skill copy will not"
        log_error "auto-pipe a remote script into bash."
        log_warn  "Install actionlint yourself (verify the script first), e.g.:"
        log_warn  "  curl https://raw.githubusercontent.com/rhysd/actionlint/main/scripts/download-actionlint.bash -o /tmp/dl-actionlint.bash"
        log_warn  "  less /tmp/dl-actionlint.bash   # review it"
        log_warn  "  bash /tmp/dl-actionlint.bash"
        log_warn  "then re-run this script."
        return 1
    fi

    if [ -f "${TOOLS_DIR}/actionlint" ]; then
        log_info "actionlint installed successfully at ${TOOLS_DIR}/actionlint"
        "${TOOLS_DIR}/actionlint" --version
    else
        log_error "Failed to install actionlint"
        return 1
    fi
}

# Main installation
main() {
    log_info "=== GitHub Actions Validator - Tool Installation ==="
    log_info "Installing tools to: ${TOOLS_DIR}"
    echo ""

    install_act
    echo ""
    install_actionlint
    echo ""

    log_info "=== Installation Complete ==="
    log_info "Tools installed at: ${TOOLS_DIR}"
    log_info "act: ${TOOLS_DIR}/act"
    log_info "actionlint: ${TOOLS_DIR}/actionlint"
    echo ""
    log_info "Add ${TOOLS_DIR} to your PATH or use absolute paths:"
    echo "  export PATH=\"${TOOLS_DIR}:\$PATH\""
}

main "$@"
