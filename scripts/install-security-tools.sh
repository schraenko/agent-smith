#!/usr/bin/env bash
# Install gitleaks (Go binary, not available via pip).
# Supports: macOS (Homebrew), Linux (direct binary download).
#
# Usage: bash scripts/install-security-tools.sh
#
# Note: bandit and pip-audit are installed via `pip install -e ".[dev]"`
#       and do not require this script.

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_ok() { echo -e "${GREEN}✅ $1${NC}"; }
log_warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_err() { echo -e "${RED}❌ $1${NC}"; }

if command -v gitleaks &> /dev/null; then
    log_ok "gitleaks already installed: $(gitleaks version 2>/dev/null || echo 'unknown version')"
    exit 0
fi

GITLEAKS_VERSION="${GITLEAKS_VERSION:-8.18.4}"

case "$(uname -s)" in
    Darwin)
        if ! command -v brew &> /dev/null; then
            log_err "Homebrew not found. Install from: https://brew.sh"
            echo "  Or download manually: https://github.com/gitleaks/gitleaks/releases"
            exit 1
        fi
        echo "Installing gitleaks via Homebrew..."
        brew install gitleaks
        ;;
    Linux)
        echo "Installing gitleaks v${GITLEAKS_VERSION} (Linux binary)..."
        ARCH="$(uname -m)"
        case "$ARCH" in
            x86_64) BINARY="gitleaks_${GITLEAKS_VERSION}_linux_amd64.tar.gz" ;;
            aarch64|arm64) BINARY="gitleaks_${GITLEAKS_VERSION}_linux_arm64.tar.gz" ;;
            *)
                log_err "Unsupported architecture: $ARCH"
                echo "  Download manually: https://github.com/gitleaks/gitleaks/releases"
                exit 1
                ;;
        esac

        TMP_DIR="$(mktemp -d)"
        trap 'rm -rf "$TMP_DIR"' EXIT

        if command -v wget &> /dev/null; then
            wget -q "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/${BINARY}" -O "$TMP_DIR/gitleaks.tar.gz"
        elif command -v curl &> /dev/null; then
            curl -sL "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/${BINARY}" -o "$TMP_DIR/gitleaks.tar.gz"
        else
            log_err "Neither wget nor curl found. Install one or download manually."
            exit 1
        fi

        tar -xzf "$TMP_DIR/gitleaks.tar.gz" -C "$TMP_DIR"
        sudo mv "$TMP_DIR/gitleaks" /usr/local/bin/gitleaks
        ;;
    MINGW*|MSYS*|CYGWIN*)
        log_warn "Windows detected. Install via Scoop: scoop install gitleaks"
        echo "  Or download: https://github.com/gitleaks/gitleaks/releases"
        exit 1
        ;;
    *)
        log_err "Unsupported OS: $(uname -s)"
        echo "  Install manually: https://github.com/gitleaks/gitleaks/releases"
        exit 1
        ;;
esac

if command -v gitleaks &> /dev/null; then
    log_ok "gitleaks installed: $(gitleaks version 2>/dev/null || echo 'unknown version')"
else
    log_err "gitleaks installation failed"
    exit 1
fi
