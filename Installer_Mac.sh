#!/bin/bash

###############################################################################
# Helper: Safe Exit
###############################################################################
press_any_key_to_exit() {
  echo
  echo "Press any key to exit..."
  # Wait for a single keypress (silent, no echo)
  read -n 1 -s
  exit "$1"
}

echo
echo "========== FinGPT Installer for macOS =========="

###############################################################################
# 1. Check if Python is installed
###############################################################################
echo
echo "Checking if Python 3 is installed..."
if ! command -v python3 &> /dev/null
then
    echo
    echo "ERROR: Python 3 is not installed on this system."
    echo "Please install Python 3.9+ from https://www.python.org/downloads/ (or via Homebrew)."
    press_any_key_to_exit 1
else
    echo "Python 3 found at: $(which python3)"
fi

###############################################################################
# 2. Check if Django’s default port (8000) is already in use
###############################################################################
echo
echo "Checking if port 8000 is already in use..."
# We'll use lsof to detect a process bound to :8000
if lsof -Pi :8000 -sTCP:LISTEN -t &> /dev/null
then
    echo
    echo "ERROR: Port 8000 is in use. Possibly another Django or a different server is running."
    echo "Please stop that process, then rerun this script."
    press_any_key_to_exit 1
else
    echo "Port 8000 appears to be free."
fi

###############################################################################
# 3. Create / Activate Virtual Environment
###############################################################################
echo
echo "Ensuring a virtual environment is set up..."

# We’ll store the venv in "FinGPTenv" in the script's directory.
# Get current script directory (works even if run via relative path).
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_PATH="${SCRIPT_DIR}/FinGPTenv"

if [ ! -d "$VENV_PATH" ]; then
    echo "Creating a new virtual environment at: $VENV_PATH"
    python3 -m venv "$VENV_PATH"
    if [ $? -ne 0 ]; then
        echo "ERROR: Could not create virtual environment. Check your Python installation."
        press_any_key_to_exit 1
    fi
else
    echo "Virtual environment folder already exists at $VENV_PATH."
fi

echo "Activating the virtual environment..."
# Source the venv's activate script
source "${VENV_PATH}/bin/activate" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "ERROR: Could not activate virtual environment at ${VENV_PATH}/bin/activate"
    press_any_key_to_exit 1
fi

###############################################################################
# 4. Install Dependencies
###############################################################################
echo
echo "Upgrading pip in the virtual environment..."
pip install --upgrade pip

# Check if Poetry is available
BACKEND_PATH="${SCRIPT_DIR}/Main/backend"
if command -v poetry &> /dev/null && [ -f "${BACKEND_PATH}/pyproject.toml" ]; then
    echo
    echo "Poetry detected. Using Poetry to manage dependencies..."
    
    # Export requirements files using Poetry
    echo "Exporting platform-specific requirements..."
    cd "$BACKEND_PATH"
    poetry run export-requirements
    cd "$SCRIPT_DIR"
    
    echo "Requirements files updated from Poetry configuration."
fi

# Use requirements_mac.txt for macOS
REQUIREMENTS_FILE="${SCRIPT_DIR}/Requirements/requirements_mac.txt"
if [ ! -f "$REQUIREMENTS_FILE" ]; then
    echo "ERROR: requirements_mac.txt not found at $REQUIREMENTS_FILE"
    press_any_key_to_exit 1
fi

echo
echo "Installing dependencies from requirements_mac.txt..."
pip install -r "$REQUIREMENTS_FILE"
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install dependencies."
    press_any_key_to_exit 1
fi
echo "All dependencies installed successfully."

###############################################################################
# 5. Start Django Back-End
###############################################################################
echo
echo "Starting Django back-end..."

# Path to your Django project folder: ChatBot-Fin/chat_server
SERVER_PATH="${SCRIPT_DIR}/Main/backend"
if [ ! -d "$SERVER_PATH" ]; then
    echo "ERROR: Main/backend folder not found at $SERVER_PATH"
    press_any_key_to_exit 1
fi

# We can run it in the background with nohup or open a new Terminal window

# Option A: Start server in background (nohup)
#   This will let the user keep using the same terminal.
#   Press Ctrl+C here won't kill the server (since it's backgrounded).
# cd "$SERVER_PATH"
# nohup python manage.py runserver 0.0.0.0:8000 > server_log.txt 2>&1 &
# SERVER_PID=$!
# echo "Django server running in background (PID: $SERVER_PID). Logs: server_log.txt"

# Option B: Open a new Terminal window and run the server
#   This is trickier on macOS, but we can do:
#     open -a "Terminal" <command>
#   We'll create a small script and ask Terminal to open it.
TEMP_SCRIPT="${SCRIPT_DIR}/run_django_temp.sh"
cat <<EOF > "$TEMP_SCRIPT"
#!/bin/bash
cd "$SERVER_PATH"
source "${VENV_PATH}/bin/activate"
python manage.py runserver 0.0.0.0:8000
EOF
chmod +x "$TEMP_SCRIPT"

echo "Launching Django server in a new Terminal window..."
open -a Terminal "$TEMP_SCRIPT"

###############################################################################
# 6. (Optional) Attempt to remove existing FinGPT extension
###############################################################################
# On macOS, there's no official "CLI uninstall" for dev/unpacked Chrome extensions.
# If your extension is from the Web Store, you can attempt a forced uninstall by ID,
# but it's not straightforward. We'll omit it here or do a best-effort kill Chrome.

echo
echo "Attempting to remove any existing FinGPT extension (best effort) -- skipping specialized uninstall on macOS."

###############################################################################
# 7. Close Chrome (if open) and load/refresh FinGPT extension
###############################################################################
echo
echo "Attempting to close Chrome if running..."
pkill -f "Google Chrome" 2>/dev/null
echo "Chrome closed (or was not running)."

echo
echo "🔧 Building and verifying FinGPT extension..."
ORIGINAL_DIR=$(pwd)
# Change to extension directory (relative to script location)
cd "$SCRIPT_DIR/Main/frontend" || exit 1
npm i # Install dependencies
npm run build:full # Build frontend and verify dist/ contents
cd "$ORIGINAL_DIR"

BUILD_STATUS=$?
if [ $BUILD_STATUS -ne 0 ]; then
  echo "❌ Build or file check failed. Aborting further steps."
  exit 1
else
  echo "✅ Build passed! Proceeding..."
fi

echo
echo "Loading FinGPT extension in Chrome..."
EXTENSION_PATH="${SCRIPT_DIR}/Main/frontend/dist"
if [ ! -d "$EXTENSION_PATH" ]; then
    echo "ERROR: Extension source folder not found at $EXTENSION_PATH"
    press_any_key_to_exit 1
fi

# Common Chrome path on macOS
CHROME_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
if [ ! -f "$CHROME_PATH" ]; then
    echo "ERROR: Google Chrome not found at /Applications/Google Chrome.app."
    echo "Please install Chrome or update the path in this script."
    press_any_key_to_exit 1
fi

# Launch Chrome with the extension
"$CHROME_PATH" --load-extension="$EXTENSION_PATH" &>/dev/null &

###############################################################################
# 8. Done!
###############################################################################
echo
echo "========== FinGPT Installation Complete (macOS) =========="
echo "The Django server is launching in a separate Terminal window."
echo "Chrome has been launched with the FinGPT extension loaded."
echo "You can now start using the FinGPT Agent!"
press_any_key_to_exit 0
