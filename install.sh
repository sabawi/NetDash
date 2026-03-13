#!/bin/bash
# NetDash - Installation Script
# Detects OS/distro and installs all dependencies

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/venv"

# ── Colours ────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'
info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()      { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
die()     { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }
header()  { echo -e "\n${BOLD}── $* ──${NC}"; }

# ── Detect OS ──────────────────────────────────────────────
OS="$(uname -s)"
ARCH="$(uname -m)"
info "OS: $OS  Arch: $ARCH"

# ── macOS ──────────────────────────────────────────────────
install_macos() {
    header "macOS setup"

    # Homebrew
    if ! command -v brew &>/dev/null; then
        warn "Homebrew not found — installing..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        # Apple Silicon brew lives at /opt/homebrew
        [ "$ARCH" = "arm64" ] && eval "$(/opt/homebrew/bin/brew shellenv)"
    else
        ok "Homebrew: $(brew --version | head -1)"
    fi

    # Tools via Homebrew (nmap, whois — traceroute ships with macOS)
    for pkg in nmap whois; do
        if brew list --formula "$pkg" &>/dev/null 2>&1; then
            ok "$pkg already installed"
        else
            info "brew install $pkg ..."
            brew install "$pkg"
        fi
    done

    # Python 3
    if ! command -v python3 &>/dev/null; then
        info "Installing python3 via Homebrew..."
        brew install python3
    else
        ok "python3: $(python3 --version)"
    fi
}

# ── Linux ──────────────────────────────────────────────────
install_linux() {
    header "Linux setup"

    if command -v apt-get &>/dev/null; then
        PKG_MGR="apt"
    elif command -v dnf &>/dev/null; then
        PKG_MGR="dnf"
    elif command -v yum &>/dev/null; then
        PKG_MGR="yum"
    elif command -v pacman &>/dev/null; then
        PKG_MGR="pacman"
    else
        die "No supported package manager found (apt / dnf / yum / pacman)"
    fi
    info "Package manager: $PKG_MGR"

    install_pkg() {
        local pkg="$1"
        case "$PKG_MGR" in
            apt)
                dpkg -s "$pkg" &>/dev/null 2>&1 && { ok "$pkg already installed"; return; }
                sudo apt-get install -y -qq "$pkg" && ok "Installed $pkg" || warn "Could not install $pkg (optional)"
                ;;
            dnf|yum)
                rpm -q "$pkg" &>/dev/null 2>&1 && { ok "$pkg already installed"; return; }
                sudo "$PKG_MGR" install -y -q "$pkg" && ok "Installed $pkg" || warn "Could not install $pkg (optional)"
                ;;
            pacman)
                pacman -Q "$pkg" &>/dev/null 2>&1 && { ok "$pkg already installed"; return; }
                sudo pacman -S --noconfirm --quiet "$pkg" && ok "Installed $pkg" || warn "Could not install $pkg (optional)"
                ;;
        esac
    }

    case "$PKG_MGR" in
        apt)
            info "apt-get update..."
            sudo apt-get update -qq
            for pkg in python3 python3-pip python3-venv \
                       nmap traceroute whois fping arp-scan net-tools psmisc; do
                install_pkg "$pkg"
            done
            ;;
        dnf|yum)
            for pkg in python3 python3-pip nmap traceroute whois fping net-tools psmisc; do
                install_pkg "$pkg"
            done
            ;;
        pacman)
            for pkg in python python-pip nmap traceroute whois fping net-tools psmisc; do
                install_pkg "$pkg"
            done
            ;;
    esac
}

# ── Run OS install ─────────────────────────────────────────
case "$OS" in
    Darwin) install_macos ;;
    Linux)  install_linux ;;
    *)      die "Unsupported OS: $OS" ;;
esac

# ── Verify Python ──────────────────────────────────────────
header "Python check"
PYTHON=$(command -v python3 2>/dev/null || command -v python 2>/dev/null)
[ -z "$PYTHON" ] && die "python3 not found"

PY_MAJOR=$("$PYTHON" -c "import sys; print(sys.version_info.major)")
PY_MINOR=$("$PYTHON" -c "import sys; print(sys.version_info.minor)")
PY_VER="$PY_MAJOR.$PY_MINOR"
( [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 8 ] ) || die "Python 3.8+ required, found $PY_VER"
ok "Python $PY_VER ($PYTHON)"

# ── Virtual environment ────────────────────────────────────
header "Virtual environment"
if [ -d "$VENV" ] && [[ " $* " != *" --reinstall "* ]]; then
    ok "venv exists — skipping (pass --reinstall to rebuild)"
else
    [ -d "$VENV" ] && { info "Removing existing venv..."; rm -rf "$VENV"; }
    info "Creating venv at $VENV..."
    "$PYTHON" -m venv "$VENV"
    ok "venv created"
fi

# ── Python packages ────────────────────────────────────────
header "Python packages"
source "$VENV/bin/activate"
pip install --quiet --upgrade pip
pip install --quiet -r "$SCRIPT_DIR/requirements.txt"
ok "All packages installed"
deactivate

# ── Permissions ────────────────────────────────────────────
chmod +x "$SCRIPT_DIR/start.sh" "$SCRIPT_DIR/stop.sh" "$SCRIPT_DIR/install.sh"
ok "Scripts are executable"

# ── Notes ──────────────────────────────────────────────────
header "Notes"
if [ "$OS" = "Linux" ]; then
    echo "  • nmap port/service scans may need sudo to detect OS fingerprints."
    echo "    Run:  sudo chmod +s \$(which nmap)   to allow without sudo (optional)."
fi
if [ "$OS" = "Darwin" ]; then
    echo "  • Some nmap scan types require root on macOS."
    echo "    Run:  sudo nmap ...   if fast/service scans return no results."
fi

echo ""
echo -e "${GREEN}${BOLD}╔══════════════════════════════════════╗${NC}"
echo -e "${GREEN}${BOLD}║   NetDash ready to run               ║${NC}"
echo -e "${GREEN}${BOLD}╚══════════════════════════════════════╝${NC}"
echo ""
echo "  Start:  ./start.sh"
echo "  Stop:   ./stop.sh"
echo "  URL:    http://localhost:8123"
echo ""
