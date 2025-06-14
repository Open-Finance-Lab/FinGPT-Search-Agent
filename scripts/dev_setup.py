#!/usr/bin/env python3
"""
Development setup script for FinGPT.
Starts both backend and frontend in development mode with hot-reloading.
"""
import subprocess
import sys
import os
from pathlib import Path
import platform
import threading
import time

class DevRunner:
    def __init__(self):
        self.root_dir = Path(__file__).parent.parent
        self.backend_dir = self.root_dir / "Main" / "backend"
        self.frontend_dir = self.root_dir / "Main" / "frontend"
        self.is_windows = platform.system() == "Windows"
        self.processes = []
        
        # Set UTF-8 encoding
        if self.is_windows:
            os.environ['PYTHONIOENCODING'] = 'utf-8'
            os.environ['PYTHONUTF8'] = '1'
            try:
                subprocess.run(['chcp', '65001'], shell=True, capture_output=True)
            except:
                pass
        
    def run_backend(self):
        """Run Django development server."""
        print("Starting Django backend server...")
        
        # Use the same Python executable that's running this script
        # This ensures we use the virtual environment's Python
        python_exe = sys.executable
        cmd = [python_exe, "manage.py", "runserver"]
        
        # Set up environment with UTF-8 and current environment
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUTF8'] = '1'
        
        try:
            process = subprocess.Popen(
                cmd,
                cwd=self.backend_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1,
                env=env
            )
            self.processes.append(process)
            
            # Stream output
            backend_started = False
            for line in iter(process.stdout.readline, ''):
                if line:
                    print(f"[Backend] {line.strip()}")
                    # Check if backend actually started
                    if "Starting development server" in line:
                        backend_started = True
                    # Check for errors
                    if "ModuleNotFoundError" in line or "Error" in line:
                        print(f"[Backend] ERROR DETECTED: Backend failed to start properly")
                        if not backend_started:
                            return
                    
        except Exception as e:
            print(f"ERROR: Backend error: {e}")
            
    def run_frontend_watch(self):
        """Run frontend in watch mode."""
        print("Starting frontend build watcher...")
        
        # Use shell=True on Windows to find npm in PATH
        if self.is_windows:
            cmd = "npm run watch"
            shell = True
        else:
            cmd = ["npm", "run", "watch"]
            shell = False
        
        # Set up environment with UTF-8
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        if self.is_windows:
            env['npm_config_unicode'] = 'true'
        
        try:
            process = subprocess.Popen(
                cmd,
                cwd=self.frontend_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1,
                shell=shell,
                env=env
            )
            self.processes.append(process)
            
            # Stream output
            for line in iter(process.stdout.readline, ''):
                if line:
                    print(f"[Frontend] {line.strip()}")
                    
        except Exception as e:
            print(f"ERROR: Frontend error: {e}")
            print("Make sure npm is installed and in your PATH")
    
    def check_watch_script(self):
        """Check if watch script exists in package.json."""
        package_json = self.frontend_dir / "package.json"
        if package_json.exists():
            import json
            with open(package_json, encoding='utf-8') as f:
                data = json.load(f)
                scripts = data.get("scripts", {})
                if "watch" not in scripts:
                    print("WARNING: No 'watch' script found in package.json")
                    print("   Adding watch script...")
                    scripts["watch"] = "webpack --watch --config webpack.config.js"
                    data["scripts"] = scripts
                    with open(package_json, "w", encoding='utf-8') as f:
                        json.dump(data, f, indent=2)
                    return False
        return True
    
    def check_dependencies(self):
        """Check if required dependencies are installed."""
        print("Checking backend dependencies...")
        
        # Check for django-cors-headers using the same Python as the script
        result = subprocess.run(
            [sys.executable, "-c", "import corsheaders"],
            capture_output=True
        )
        
        if result.returncode != 0:
            print("WARNING: django-cors-headers not installed. Installing...")
            install_result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "django-cors-headers"],
                capture_output=True,
                text=True
            )
            if install_result.returncode == 0:
                print("OK: django-cors-headers installed successfully")
            else:
                print(f"ERROR: Failed to install django-cors-headers: {install_result.stderr}")
                print("Please run: pip install django-cors-headers")
                return False
        else:
            print("OK: django-cors-headers is installed")
        
        return True
    
    def run(self):
        """Run both backend and frontend in development mode."""
        print("FinGPT Development Mode")
        print("=========================\n")
        
        # Show which Python we're using
        print(f"Using Python: {sys.executable}")
        print(f"Python version: {sys.version.split()[0]}\n")
        
        # Check virtual environment
        in_venv = (
            os.environ.get('VIRTUAL_ENV') or 
            sys.prefix != sys.base_prefix or
            hasattr(sys, 'real_prefix')
        )
        
        if not in_venv:
            print("WARNING: No virtual environment detected!")
            print("   Please activate your virtual environment first:")
            if self.is_windows:
                print("   FinGPTenv\\Scripts\\activate")
            else:
                print("   source FinGPTenv/bin/activate")
            return 1
        else:
            print(f"Virtual environment: {os.environ.get('VIRTUAL_ENV', sys.prefix)}\n")
        
        # Check dependencies
        if not self.check_dependencies():
            return 1
        
        # Check if watch script exists
        self.check_watch_script()
        
        try:
            # Start backend in a thread
            backend_thread = threading.Thread(target=self.run_backend)
            backend_thread.daemon = True
            backend_thread.start()
            
            # Give backend time to start
            time.sleep(3)
            
            # Start frontend in a thread
            frontend_thread = threading.Thread(target=self.run_frontend_watch)
            frontend_thread.daemon = True
            frontend_thread.start()
            
            print("\nDevelopment servers starting...")
            print("   Backend: http://localhost:8000")
            print("   Frontend: Watching for changes...")
            print("\nPress Ctrl+C to stop all servers\n")
            
            # Keep main thread alive
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n\nShutting down development servers...")
            for process in self.processes:
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except:
                    process.kill()
            print("All servers stopped")
            return 0
        except Exception as e:
            print(f"ERROR: {e}")
            return 1

def main():
    runner = DevRunner()
    sys.exit(runner.run())

if __name__ == "__main__":
    main()