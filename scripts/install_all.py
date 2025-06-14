#!/usr/bin/env python3
"""
Unified installation script for FinGPT monorepo.
Handles both backend (Python/Poetry) and frontend (Node/npm) dependencies.
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
        
    def run_command(self, cmd, cwd=None, shell=True):
        """Run a command and handle errors."""
        print(f"Running: {cmd}")
        result = subprocess.run(cmd, cwd=cwd, shell=shell, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error: {result.stderr}")
            return False
        if result.stdout:
            print(result.stdout)
        return True
    
    def check_prerequisites(self):
        """Check if required tools are installed."""
        print("🔍 Checking prerequisites...")
        
        # Check Python
        if not self.run_command("python --version" if self.is_windows else "python3 --version"):
            print("❌ Python not found. Please install Python 3.10+")
            return False
            
        # Check Node.js
        if not self.run_command("node --version"):
            print("❌ Node.js not found. Please install Node.js 18+")
            return False
            
        # Check npm
        if not self.run_command("npm --version"):
            print("❌ npm not found. Please install npm")
            return False
            
        print("✅ All prerequisites found!")
        return True
    
    def setup_virtual_environment(self):
        """Create and activate Python virtual environment."""
        print("\n🐍 Setting up Python virtual environment...")
        
        venv_path = self.root_dir / self.venv_name
        
        if not venv_path.exists():
            print(f"Creating virtual environment: {self.venv_name}")
            python_cmd = "python" if self.is_windows else "python3"
            if not self.run_command(f"{python_cmd} -m venv {self.venv_name}", cwd=self.root_dir):
                return False
        
        # Return activation command for user
        if self.is_windows:
            activate_cmd = f"{self.venv_name}\\Scripts\\activate"
        else:
            activate_cmd = f"source {self.venv_name}/bin/activate"
            
        print(f"\n📌 To activate the virtual environment, run:")
        print(f"   {activate_cmd}")
        return True
    
    def install_poetry(self):
        """Install Poetry if not already installed."""
        print("\n📦 Checking Poetry installation...")
        
        if self.run_command("poetry --version"):
            print("✅ Poetry is already installed")
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
        print("\n🔧 Installing backend dependencies...")
        
        if not self.backend_dir.exists():
            print(f"❌ Backend directory not found: {self.backend_dir}")
            return False
            
        # Install with Poetry
        print("Installing Python packages with Poetry...")
        if not self.run_command("poetry install", cwd=self.backend_dir):
            print("⚠️  Poetry install failed, trying pip...")
            # Fallback to pip
            req_file = "requirements_win.txt" if self.is_windows else "requirements_mac.txt"
            req_path = self.root_dir / "Requirements" / req_file
            if req_path.exists():
                if not self.run_command(f"pip install -r {req_path}"):
                    return False
                # Install mcp[cli] separately
                mcp_cmd = "pip install mcp[cli]" if self.is_windows else "pip install 'mcp[cli]'"
                self.run_command(mcp_cmd)
            else:
                print(f"❌ Requirements file not found: {req_path}")
                return False
                
        # Export requirements
        print("Exporting platform-specific requirements...")
        self.run_command("poetry run export-requirements", cwd=self.backend_dir)
        
        print("✅ Backend dependencies installed!")
        return True
    
    def install_frontend_dependencies(self):
        """Install frontend Node.js dependencies."""
        print("\n🎨 Installing frontend dependencies...")
        
        if not self.frontend_dir.exists():
            print(f"❌ Frontend directory not found: {self.frontend_dir}")
            return False
            
        # Install npm packages
        print("Installing Node.js packages...")
        if not self.run_command("npm install", cwd=self.frontend_dir):
            return False
            
        # Build frontend
        print("Building frontend...")
        if not self.run_command("npm run build:full", cwd=self.frontend_dir):
            print("⚠️  Frontend build failed. You may need to build manually.")
            
        print("✅ Frontend dependencies installed!")
        return True
    
    def create_env_file(self):
        """Create .env file if it doesn't exist."""
        env_path = self.backend_dir / ".env"
        if not env_path.exists():
            print("\n📝 Creating .env file...")
            print("⚠️  Please add your OpenAI API key to Main/backend/.env:")
            print("   OPENAI_API_KEY=your-api-key-here")
            env_path.write_text("# Add your OpenAI API key here\nOPENAI_API_KEY=your-api-key-here\n")
    
    def print_next_steps(self):
        """Print next steps for the user."""
        print("\n" + "="*50)
        print("🎉 Installation Complete!")
        print("="*50)
        print("\nNext steps:")
        print("1. Activate the virtual environment:")
        if self.is_windows:
            print(f"   {self.venv_name}\\Scripts\\activate")
        else:
            print(f"   source {self.venv_name}/bin/activate")
        print("\n2. Add your OpenAI API key to Main/backend/.env")
        print("\n3. Start the backend server:")
        print("   cd Main/backend")
        print("   python manage.py runserver")
        print("\n4. Load the extension in your browser")
        print("   - Open Chrome extensions page")
        print("   - Enable Developer mode")
        print("   - Load unpacked: Main/frontend/dist")
    
    def run(self):
        """Run the complete installation process."""
        print("🚀 FinGPT Monorepo Installer")
        print("============================\n")
        
        if not self.check_prerequisites():
            return 1
            
        if not self.setup_virtual_environment():
            return 1
            
        # Note: Poetry should be installed in the activated venv
        print("\n⚠️  Please activate the virtual environment and run this script again")
        print("   to continue with the installation.")
        
        # Check if we're in a venv
        if not os.environ.get('VIRTUAL_ENV'):
            return 0
            
        if not self.install_poetry():
            print("⚠️  Poetry installation failed, but continuing...")
            
        if not self.install_backend_dependencies():
            return 1
            
        if not self.install_frontend_dependencies():
            return 1
            
        self.create_env_file()
        self.print_next_steps()
        
        return 0

def main():
    installer = MonorepoInstaller()
    sys.exit(installer.run())

if __name__ == "__main__":
    main()