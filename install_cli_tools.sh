#!/bin/bash
# ============================================================
# SAP BTP CLI & CF CLI - Installation Script
# ============================================================
# This script installs the SAP BTP CLI and Cloud Foundry CLI
# on Linux (amd64). For macOS or other platforms, please
# refer to the official documentation.
#
# Usage:
#   chmod +x install_cli_tools.sh
#   ./install_cli_tools.sh
# ============================================================

set -euo pipefail

echo "=========================================="
echo " SAP BTP CLI & CF CLI Installer"
echo "=========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# --- Detect OS and Architecture ---
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

case "$ARCH" in
    x86_64)  ARCH_LABEL="amd64" ;;
    aarch64) ARCH_LABEL="arm64" ;;
    arm64)   ARCH_LABEL="arm64" ;;
    *)
        echo -e "${RED}Unsupported architecture: $ARCH${NC}"
        exit 1
        ;;
esac

echo "Detected OS: $OS ($ARCH_LABEL)"
echo ""

# --- Install BTP CLI ---
echo "-------------------------------------------"
echo "1. Installing SAP BTP CLI..."
echo "-------------------------------------------"

if command -v btp &> /dev/null; then
    echo -e "${GREEN}BTP CLI already installed: $(which btp)${NC}"
    btp --version 2>/dev/null || true
else
    echo "Downloading BTP CLI..."
    BTP_URL=""
    case "$OS" in
        linux)
            BTP_URL="https://tools.hana.ondemand.com/additional/btp-cli-linux-amd64-latest.tar.gz"
            if [ "$ARCH_LABEL" = "arm64" ]; then
                BTP_URL="https://tools.hana.ondemand.com/additional/btp-cli-linux-arm64-latest.tar.gz"
            fi
            ;;
        darwin)
            BTP_URL="https://tools.hana.ondemand.com/additional/btp-cli-darwin-amd64-latest.tar.gz"
            if [ "$ARCH_LABEL" = "arm64" ]; then
                BTP_URL="https://tools.hana.ondemand.com/additional/btp-cli-darwin-arm64-latest.tar.gz"
            fi
            ;;
        *)
            echo -e "${RED}Unsupported OS for automatic BTP CLI install: $OS${NC}"
            echo "Please download manually from: https://tools.hana.ondemand.com/#cloud-btpcli"
            ;;
    esac

    if [ -n "$BTP_URL" ]; then
        TMPDIR=$(mktemp -d)
        echo "Downloading from: $BTP_URL"
        if curl -fsSL "$BTP_URL" -o "$TMPDIR/btp-cli.tar.gz" 2>/dev/null; then
            tar -xzf "$TMPDIR/btp-cli.tar.gz" -C "$TMPDIR"
            # Find the btp binary
            BTP_BIN=$(find "$TMPDIR" -name "btp" -o -name "btp.exe" | head -1)
            if [ -n "$BTP_BIN" ]; then
                sudo mv "$BTP_BIN" /usr/local/bin/btp
                sudo chmod +x /usr/local/bin/btp
                echo -e "${GREEN}BTP CLI installed to /usr/local/bin/btp${NC}"
            else
                echo -e "${YELLOW}Could not find btp binary in download.${NC}"
                echo "Trying npm installation..."
                if command -v npm &> /dev/null; then
                    npm install -g @sap/btp-cli
                else
                    echo -e "${RED}npm not found. Please install BTP CLI manually.${NC}"
                    echo "Download from: https://tools.hana.ondemand.com/#cloud-btpcli"
                fi
            fi
        else
            echo -e "${YELLOW}Direct download failed. Trying npm...${NC}"
            if command -v npm &> /dev/null; then
                npm install -g @sap/btp-cli
            else
                echo -e "${RED}Could not install BTP CLI. Please install manually.${NC}"
                echo "Download from: https://tools.hana.ondemand.com/#cloud-btpcli"
            fi
        fi
        rm -rf "$TMPDIR"
    fi
fi

echo ""

# --- Install CF CLI ---
echo "-------------------------------------------"
echo "2. Installing Cloud Foundry CLI (cf v8)..."
echo "-------------------------------------------"

if command -v cf &> /dev/null; then
    echo -e "${GREEN}CF CLI already installed: $(which cf)${NC}"
    cf --version 2>/dev/null || true
else
    echo "Installing CF CLI..."
    case "$OS" in
        linux)
            # Try the official CF CLI install script
            if curl -fsSL "https://packages.cloudfoundry.org/stable?release=linux64-binary&version=v8&source=github" -o /tmp/cf-cli.tgz 2>/dev/null; then
                tar -xzf /tmp/cf-cli.tgz -C /tmp
                sudo mv /tmp/cf8 /usr/local/bin/cf 2>/dev/null || sudo mv /tmp/cf /usr/local/bin/cf 2>/dev/null || true
                sudo chmod +x /usr/local/bin/cf
                rm -f /tmp/cf-cli.tgz
                echo -e "${GREEN}CF CLI installed to /usr/local/bin/cf${NC}"
            else
                echo -e "${RED}Failed to download CF CLI.${NC}"
                echo "Please install manually from: https://github.com/cloudfoundry/cli/releases"
            fi
            ;;
        darwin)
            if command -v brew &> /dev/null; then
                brew install cloudfoundry/tap/cf-cli@8
            else
                echo -e "${RED}Please install CF CLI using Homebrew:${NC}"
                echo "  brew install cloudfoundry/tap/cf-cli@8"
            fi
            ;;
        *)
            echo -e "${RED}Unsupported OS for automatic CF CLI install: $OS${NC}"
            echo "Please install from: https://github.com/cloudfoundry/cli/releases"
            ;;
    esac
fi

echo ""

# --- Install Python dependencies ---
echo "-------------------------------------------"
echo "3. Installing Python dependencies..."
echo "-------------------------------------------"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
    pip install -r "$SCRIPT_DIR/requirements.txt" 2>/dev/null || pip3 install -r "$SCRIPT_DIR/requirements.txt" 2>/dev/null || {
        echo -e "${YELLOW}Could not install Python dependencies automatically.${NC}"
        echo "Please run: pip install -r requirements.txt"
    }
else
    pip install pyyaml 2>/dev/null || pip3 install pyyaml 2>/dev/null || {
        echo -e "${YELLOW}Could not install PyYAML. Please run: pip install pyyaml${NC}"
    }
fi

echo ""
echo "=========================================="
echo -e "${GREEN} Installation complete!${NC}"
echo "=========================================="
echo ""
echo "Verify installation:"
echo "  btp --version"
echo "  cf --version"
echo "  python3 -c 'import yaml; print(\"PyYAML OK\")'"
echo ""
