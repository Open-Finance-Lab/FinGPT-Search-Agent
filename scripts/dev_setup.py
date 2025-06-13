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
        
    def run_backend(self):
        """Run Django development server."""
        print("🚀 Starting Django backend server...")
        cmd = ["python", "manage.py", "runserver"] if self.is_windows else ["python3", "manage.py", "runserver"]
        
        try:
            process = subprocess.Popen(
                cmd,
                cwd=self.backend_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            self.processes.append(process)
            
            # Stream output
            for line in iter(process.stdout.readline, ''):
                if line:
                    print(f"[Backend] {line.strip()}")
                    
        except Exception as e:
            print(f"❌ Backend error: {e}")
            
    def run_frontend_watch(self):
        """Run frontend in watch mode."""
        print("🎨 Starting frontend build watcher...")
        
        try:
            process = subprocess.Popen(
                ["npm", "run", "watch"],
                cwd=self.frontend_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            self.processes.append(process)
            
            # Stream output
            for line in iter(process.stdout.readline, ''):
                if line:
                    print(f"[Frontend] {line.strip()}")
                    
        except Exception as e:
            print(f"❌ Frontend error: {e}")
    
    def check_watch_script(self):
        """Check if watch script exists in package.json."""
        package_json = self.frontend_dir / "package.json"
        if package_json.exists():
            import json
            with open(package_json) as f:
                data = json.load(f)
                scripts = data.get("scripts", {})
                if "watch" not in scripts:
                    print("⚠️  No 'watch' script found in package.json")
                    print("   Adding watch script...")
                    scripts["watch"] = "webpack --watch --config webpack.config.js"
                    data["scripts"] = scripts
                    with open(package_json, "w") as f:
                        json.dump(data, f, indent=2)
                    return False
        return True
    
    def run(self):
        """Run both backend and frontend in development mode."""
        print("🚀 FinGPT Development Mode")
        print("=========================\n")
        
        # Check virtual environment
        if not os.environ.get('VIRTUAL_ENV'):
            print("⚠️  No virtual environment detected!")
            print("   Please activate your virtual environment first:")
            if self.is_windows:
                print("   FinGPTenv\\Scripts\\activate")
            else:
                print("   source FinGPTenv/bin/activate")
            return 1
        
        # Check if watch script exists
        self.check_watch_script()
        
        try:
            # Start backend in a thread
            backend_thread = threading.Thread(target=self.run_backend)
            backend_thread.daemon = True
            backend_thread.start()
            
            # Give backend time to start
            time.sleep(2)
            
            # Start frontend in a thread
            frontend_thread = threading.Thread(target=self.run_frontend_watch)
            frontend_thread.daemon = True
            frontend_thread.start()
            
            print("\n✅ Development servers started!")
            print("   Backend: http://localhost:8000")
            print("   Frontend: Watching for changes...")
            print("\n📌 Press Ctrl+C to stop all servers\n")
            
            # Keep main thread alive
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n\n🛑 Shutting down development servers...")
            for process in self.processes:
                process.terminate()
            print("✅ All servers stopped")
            return 0
        except Exception as e:
            print(f"❌ Error: {e}")
            return 1

def main():
    runner = DevRunner()
    sys.exit(runner.run())

if __name__ == "__main__":
    main()