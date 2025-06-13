#!/bin/bash
# FinGPT Quick Installer for macOS
# Simplified installer that uses the new monorepo setup
# Usage: Run from the root folder

#-------------------#
# Helper Functions  #
#-------------------#
press_any_key_to_exit() {
    echo
    echo "Press any key to exit..."
    read -n 1 -s
    exit "$1"
}

echo
echo "========== FinGPT Quick Installer for macOS =========="
echo "This installer will set up FinGPT using the unified build system."
echo

###############################################################################
# 1. Check Prerequisites
###############################################################################
echo "📋 Checking prerequisites..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed."
    echo "   Please install Python 3.10+ from https://www.python.org/downloads/"
    echo "   Or via Homebrew: brew install python@3.10"
    press_any_key_to_exit 1
fi
echo "✅ Python found: $(python3 --version)"

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed."
    echo "   Please install Node.js 18+ from https://nodejs.org/"
    echo "   Or via Homebrew: brew install node"
    press_any_key_to_exit 1
fi
echo "✅ Node.js found: $(node --version)"

# Check port 8000
if lsof -Pi :8000 -sTCP:LISTEN -t &> /dev/null; then
    echo "⚠️  Port 8000 is in use. Please close any running servers."
    echo -n "Continue anyway? (y/n): "
    read -n 1 continue_choice
    echo
    if [ "$continue_choice" != "y" ]; then
        press_any_key_to_exit 1
    fi
fi

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

###############################################################################
# 2. Run Unified Installer
###############################################################################
echo
echo "🚀 Running unified installer..."

# Check if we have the new setup
if [ -f "$SCRIPT_DIR/Makefile" ] && command -v make &> /dev/null; then
    # Use Makefile
    echo "Using Makefile build system..."
    make install
elif [ -f "$SCRIPT_DIR/scripts/install_all.py" ]; then
    # Use Python installer directly
    echo "Using Python installer..."
    python3 "$SCRIPT_DIR/scripts/install_all.py"
else
    echo "❌ New installer scripts not found!"
    echo "   Please ensure you have the latest version from Git."
    press_any_key_to_exit 1
fi

###############################################################################
# 3. Create .env file if needed
###############################################################################
ENV_PATH="$SCRIPT_DIR/Main/backend/.env"
if [ ! -f "$ENV_PATH" ]; then
    echo
    echo "📝 Creating .env file..."
    cat > "$ENV_PATH" << 'EOF'
# FinGPT Environment Configuration
# Add your OpenAI API key below:
API_KEY7=your-api-key-here

# Optional: Add other API keys
# ANTHROPIC_API_KEY=your-anthropic-key-here
EOF
    
    echo "⚠️  Please edit $ENV_PATH and add your OpenAI API key!"
fi

###############################################################################
# 4. Quick Start Options
###############################################################################
echo
echo "✨ Installation complete!"
echo
echo "Quick start options:"
echo
echo "1. Start Development Mode (recommended):"
echo "   make dev"
echo "   # Or without make:"
echo "   python3 scripts/dev_setup.py"
echo "   This will start both backend and frontend servers"
echo
echo "2. Manual Start:"
echo "   # Terminal 1 - Backend:"
echo "   cd Main/backend"
echo "   python3 manage.py runserver"
echo "   # Terminal 2 - Frontend (optional):"
echo "   cd Main/frontend"
echo "   npm run watch"
echo
echo "3. Load Extension in Chrome:"
echo "   - Open chrome://extensions"
echo "   - Enable Developer mode"
echo "   - Click 'Load unpacked'"
echo "   - Select: Main/frontend/dist"
echo
echo "📚 For more options, run: make help"

# Optional: Auto-start development mode
echo
echo -n "Start development servers now? (y/n): "
read -n 1 auto_start
echo
if [ "$auto_start" = "y" ]; then
    echo
    echo "Starting development mode..."
    if command -v make &> /dev/null; then
        make dev
    else
        python3 "$SCRIPT_DIR/scripts/dev_setup.py"
    fi
fi

press_any_key_to_exit 0