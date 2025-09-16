#!/usr/bin/env python3
"""
Unified installation script for FinGPT monorepo.
Handles both backend (Python/Poetry) and frontend (Node/npm) dependencies.
Works across all system languages by using UTF-8 encoding.
"""
import subprocess
import sys
import os
from pathlib import Path
import platform

class MonorepoInstaller:
    def __init__(self):
        self.root_dir = Path(__file__).parent.parent
        self.backend_dir = self.root_dir / "Main" / "backend"
        self.frontend_dir = self.root_dir / "Main" / "frontend"
        self.venv_name = "FinGPTenv"
        self.is_windows = platform.system() == "Windows"
        
        # Set UTF-8 for all output
        if self.is_windows:
            # Force UTF-8 mode on Windows
            os.environ['PYTHONIOENCODING'] = 'utf-8'
            os.environ['PYTHONUTF8'] = '1'
            try:
                # Try to set console to UTF-8
                subprocess.run(['chcp', '65001'], shell=True, capture_output=True)
            except:
                pass
        
    def run_command(self, cmd, cwd=None, shell=True):
        """Run a command and handle errors with proper encoding."""
        print(f"Running: {cmd}")
        
        # Set up environment with UTF-8
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUTF8'] = '1'
        if self.is_windows:
            # Force npm to use UTF-8 on Windows
            env['npm_config_unicode'] = 'true'
        
        # Run command with UTF-8 encoding
        result = subprocess.run(
            cmd, cwd=cwd, shell=shell, capture_output=True,
            text=True, encoding='utf-8', errors='replace', env=env
        )
        
        if result.returncode != 0:
            print(f"Error: {result.stderr}")
            return False
        if result.stdout:
            print(result.stdout)
        return True
    
    def check_prerequisites(self):
        """Check if required tools are installed."""
        print("Checking prerequisites...")
        
        # Check Python
        if not self.run_command("python --version" if self.is_windows else "python3 --version"):
            print("ERROR: Python not found. Please install Python 3.10+")
            return False
            
        # Check Node.js
        if not self.run_command("node --version"):
            print("ERROR: Node.js not found. Please install Node.js 18+")
            return False
            
        # Check npm
        if not self.run_command("npm --version"):
            print("ERROR: npm not found. Please install npm")
            return False
            
        print("OK: All prerequisites found!")
        return True
    
    def setup_virtual_environment(self):
        """Set up Python virtual environment."""
        print("\nSetting up Python virtual environment...")
        
        venv_path = self.root_dir / self.venv_name
        
        if not venv_path.exists():
            print(f"Creating virtual environment: {self.venv_name}")
            cmd = f"python -m venv {self.venv_name}" if self.is_windows else f"python3 -m venv {self.venv_name}"
            if not self.run_command(cmd, cwd=self.root_dir):
                return False
                
        activate_cmd = f"{self.venv_name}\\Scripts\\activate" if self.is_windows else f"source {self.venv_name}/bin/activate"
            
        print(f"\nTo activate the virtual environment, run:")
        print(f"   {activate_cmd}")
        return True
    
    def install_poetry(self):
        """Install Poetry if not already installed."""
        print("\nChecking Poetry installation...")
        
        if self.run_command("poetry --version"):
            print("OK: Poetry is already installed")
            return True
            
        print("Installing Poetry...")
        if self.is_windows:
            install_cmd = "(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -"
            return self.run_command(install_cmd, shell=True)
        else:
            install_cmd = "curl -sSL https://install.python-poetry.org | python3 -"
            return self.run_command(install_cmd, shell=True)
    
    def install_backend_dependencies(self):
        """Install backend Python dependencies using Poetry."""
        print("\nInstalling backend dependencies...")
        
        if not self.backend_dir.exists():
            print(f"ERROR: Backend directory not found: {self.backend_dir}")
            return False
            
        # Install with Poetry (use --no-root to avoid README.md issue)
        print("Installing Python packages with Poetry...")
        if not self.run_command("poetry install --no-root", cwd=self.backend_dir):
            print("WARNING: Poetry install failed, trying pip...")
            # Fallback to pip
            req_file = "requirements_win.txt" if self.is_windows else "requirements_mac.txt"
            req_path = self.root_dir / "Requirements" / req_file
            if req_path.exists():
                if not self.run_command(f"pip install -r {req_path}"):
                    return False
                # Install mcp[cli] separately
                if self.is_windows:
                    self.run_command("pip install mcp[cli]")
                else:
                    self.run_command("pip install 'mcp[cli]'")
                    
        # Export requirements
        print("Exporting requirements files...")
        export_script = self.backend_dir / "export_requirements.py"
        if export_script.exists():
            self.run_command(f"python {export_script}", cwd=self.backend_dir)
        else:
            # Try direct poetry export as fallback
            print("WARNING: export_requirements.py not found, trying direct export...")
            self.run_command("poetry export -f requirements.txt --without-hashes -o ../../Requirements/requirements_win.txt", cwd=self.backend_dir)
            
        print("OK: Backend dependencies installed!")
        return True
    
    def install_frontend_dependencies(self):
        """Install frontend dependencies and build."""
        print("\nInstalling frontend dependencies...")
        
        if not self.frontend_dir.exists():
            print(f"ERROR: Frontend directory not found: {self.frontend_dir}")
            return False
            
        print("Installing Node.js packages...")
        if not self.run_command("npm install", cwd=self.frontend_dir):
            return False
            
        print("Building frontend...")
        # Try build:full first, fallback to build if it fails
        if not self.run_command("npm run build:full", cwd=self.frontend_dir):
            print("WARNING: build:full failed, trying standard build...")
            if not self.run_command("npm run build", cwd=self.frontend_dir):
                print("WARNING: Build failed, trying webpack directly...")
                if not self.run_command("npx webpack --config webpack.config.js", cwd=self.frontend_dir):
                    print("ERROR: Frontend build failed")
                    return False
            
        print("OK: Frontend dependencies installed!")
        return True
    
    def create_env_file(self):
        """Create .env file if it doesn't exist."""
        env_path = self.backend_dir / ".env"
        if not env_path.exists():
            print("\nCreating .env file...")
            env_content = """# FinGPT API Configuration
# Add your API keys below

# Required: At least one of these API keys
OPENAI_API_KEY=your-openai-api-key-here
ANTHROPIC_API_KEY=your-anthropic-api-key-here
DEEPSEEK_API_KEY=your-deepseek-api-key-here

# Note: MCP features currently only work with OpenAI models
"""
            env_path.write_text(env_content, encoding='utf-8')
            print(f"Created .env file at: {env_path}")
            return True
        else:
            print(f"\n.env file already exists at: {env_path}")
            return False
    
    def check_api_keys(self):
        """Check if at least one API key is configured."""
        env_path = self.backend_dir / ".env"
        if not env_path.exists():
            return False
            
        with open(env_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check if any real API key is present (not the placeholder)
        has_openai = 'OPENAI_API_KEY=' in content and 'your-openai-api-key-here' not in content
        has_anthropic = 'ANTHROPIC_API_KEY=' in content and 'your-anthropic-api-key-here' not in content
        has_deepseek = 'DEEPSEEK_API_KEY=' in content and 'your-deepseek-api-key-here' not in content
        
        return has_openai or has_anthropic or has_deepseek
    
    def prompt_for_api_keys(self):
        """Prompt user to add API keys before continuing."""
        env_path = self.backend_dir / ".env"
        
        print("\n" + "="*60)
        print("IMPORTANT: API Key Configuration Required")
        print("="*60)
        print("\nFinGPT requires at least one API key to function.")
        print(f"\nPlease edit the .env file at:\n   {env_path}")
        print("\nAdd at least one of the following:")
        print("  - OPENAI_API_KEY=your-actual-key")
        print("  - ANTHROPIC_API_KEY=your-actual-key")
        print("  - DEEPSEEK_API_KEY=your-actual-key")
        print("\nNote: MCP features require an OpenAI API key.")
        print("\n" + "="*60)
        
        while True:
            response = input("\nHave you added your API key(s)? (y/n): ").lower()
            if response == 'y':
                if self.check_api_keys():
                    print("OK: API key(s) detected!")
                    return True
                else:
                    print("WARNING: No valid API keys found. Please check your .env file.")
                    print("Make sure to replace the placeholder text with your actual API key.")
            elif response == 'n':
                print("\nPlease add your API key(s) to the .env file before continuing.")
                print("You can get API keys from:")
                print("  - OpenAI: https://platform.openai.com/api-keys")
                print("  - Anthropic: https://console.anthropic.com/")
                print("  - DeepSeek: https://platform.deepseek.com/")
            else:
                print("Please enter 'y' or 'n'")
    
    def print_next_steps(self):
        """Print next steps for the user."""
        print("\n" + "="*50)
        print("Installation Complete!")
        print("="*50)
        
        print("\nNext steps:")
        print("1. Activate the virtual environment:")
        activate_cmd = f"   {self.venv_name}\\Scripts\\activate" if self.is_windows else f"   source {self.venv_name}/bin/activate"
        print(activate_cmd)
        
        print("\n2. Start the development server:")
        dev_cmd = "   python scripts\\dev_setup.py" if self.is_windows else "   python3 scripts/dev_setup.py"
        print(dev_cmd)
        
        print("\n3. Load the browser extension:")
        print("   - Open Chrome and go to chrome://extensions")
        print("   - Enable Developer mode")
        print("   - Click 'Load unpacked'")
        print("   - Select: Main/frontend/dist")
        
        print("\n4. Start using FinGPT:")
        print("   - Navigate to a financial website")
        print("   - The FinGPT chat interface should appear")
    
    def offer_start_dev_server(self):
        """Offer to start the development server."""
        print("\n" + "-"*50)
        response = input("\nWould you like to start the development server now? (y/n): ").lower()
        if response == 'y':
            print("\nStarting development server...")
            dev_script = self.root_dir / "scripts" / "dev_setup.py"
            if dev_script.exists():
                python_cmd = "python" if self.is_windows else "python3"
                subprocess.run([python_cmd, str(dev_script)])
            else:
                print("ERROR: dev_setup.py not found!")
                print("You can start it manually with:")
                print("   python scripts\\dev_setup.py" if self.is_windows else "   python3 scripts/dev_setup.py")
    
    def run(self):
        """Run the installation process."""
        print("FinGPT Monorepo Installer")
        print("=" * 50)
        print()
        
        if not self.check_prerequisites():
            return 1
            
        if not self.setup_virtual_environment():
            return 1
            
        # Check if we're in a venv - check multiple indicators
        in_venv = (
            os.environ.get('VIRTUAL_ENV') or 
            sys.prefix != sys.base_prefix or
            hasattr(sys, 'real_prefix') or
            # Additional check for Windows - check if FinGPTenv is in the path
            (self.is_windows and 'fingptenv' in sys.executable.lower())
        )
        if not in_venv:
            print("\nWARNING: Please activate the virtual environment and run this script again")
            print("   to continue with the installation.")
            print("   Tip: run '.\\make.ps1 install' in PowerShell to auto-create and activate FinGPTenv.")
            return 0
            
        if not self.install_poetry():
            print("WARNING: Poetry installation failed, but continuing...")
            
        if not self.install_backend_dependencies():
            return 1
            
        if not self.install_frontend_dependencies():
            return 1
            
        # Create .env file and prompt for API keys
        env_created = self.create_env_file()
        
        # Always check for API keys
        if not self.check_api_keys():
            print("\n" + "!"*60)
            print("IMPORTANT: You must configure API keys before starting the server!")
            print("!"*60)
            self.prompt_for_api_keys()
        
        self.print_next_steps()
        
        # Only offer to start dev server if API keys are configured
        if self.check_api_keys():
            self.offer_start_dev_server()
        else:
            print("\n" + "!"*60)
            print("Remember to add your API keys before starting the server!")
            print("!"*60)
        
        return 0

def main():
    installer = MonorepoInstaller()
    sys.exit(installer.run())

if __name__ == "__main__":
    main()