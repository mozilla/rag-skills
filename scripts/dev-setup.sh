#!/bin/bash
# dev-setup.sh - Set up local development environment for testing skills
#
# Usage:
#   ./scripts/dev-setup.sh          # Set up symlinks
#   ./scripts/dev-setup.sh --clean  # Remove symlinks

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
CLAUDE_DIR="$HOME/.claude"
PLUGIN_NAME="semantic-rag-orchestrator"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

clean() {
    info "Cleaning up development symlinks..."
    if [ -L "$CLAUDE_DIR/skills/$PLUGIN_NAME" ]; then
        rm "$CLAUDE_DIR/skills/$PLUGIN_NAME"
        info "Removed skills symlink"
    fi
    info "Cleanup complete"
}

setup() {
    info "Setting up local development environment..."
    info "Repo root: $REPO_ROOT"

    mkdir -p "$CLAUDE_DIR/skills"

    if [ -L "$CLAUDE_DIR/skills/$PLUGIN_NAME" ]; then
        warn "Skills symlink already exists, removing..."
        rm "$CLAUDE_DIR/skills/$PLUGIN_NAME"
    elif [ -d "$CLAUDE_DIR/skills/$PLUGIN_NAME" ]; then
        error "A directory exists at $CLAUDE_DIR/skills/$PLUGIN_NAME"
        error "Please remove it manually or run with --clean first"
        exit 1
    fi

    ln -s "$REPO_ROOT/skills" "$CLAUDE_DIR/skills/$PLUGIN_NAME"
    info "Created skills symlink: ~/.claude/skills/$PLUGIN_NAME -> $REPO_ROOT/skills"

    echo ""
    info "Setup complete!"
    echo ""
    echo "To test your changes:"
    echo "  1. Start a new Claude Code session: claude"
    echo "  2. Your local skills are now active"
    echo "  3. Changes to files in this repo are reflected immediately"
    echo ""
    echo "To clean up when done:"
    echo "  ./scripts/dev-setup.sh --clean"
}

case "${1:-}" in
    --clean|-c) clean ;;
    --help|-h)
        echo "Usage: $0 [--clean|--help]"
        echo "Without arguments, creates symlinks for local testing."
        ;;
    "") setup ;;
    *)
        error "Unknown option: $1"
        exit 1
        ;;
esac
