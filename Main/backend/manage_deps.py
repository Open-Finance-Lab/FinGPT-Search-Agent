#!/usr/bin/env python3
"""
Dependency management helper script for FinGPT backend.
This script provides easy commands to manage dependencies with Poetry.
"""
import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, cwd=None):
    """Run a command and return the result."""
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode

def main():
    """Main entry point."""
    backend_dir = Path(__file__).parent
    
    if len(sys.argv) < 2:
        print("FinGPT Backend Dependency Manager")
        print("=================================")
        print("\nUsage: python manage_deps.py <command>")
        print("\nCommands:")
        print("  install      - Install all dependencies")
        print("  add <pkg>    - Add a new package")
        print("  remove <pkg> - Remove a package")
        print("  update       - Update all packages")
        print("  export       - Export platform-specific requirements files")
        print("  shell        - Activate Poetry shell")
        print("\nExamples:")
        print("  python manage_deps.py install")
        print("  python manage_deps.py add pandas")
        print("  python manage_deps.py export")
        return 1
    
    command = sys.argv[1]
    
    # Check if Poetry is installed
    poetry_check = subprocess.run("poetry --version", shell=True, capture_output=True)
    if poetry_check.returncode != 0:
        print("❌ Poetry is not installed. Please install it first:")
        print("   pip install poetry")
        print("\nOr visit: https://python-poetry.org/docs/#installation")
        return 1
    
    if command == "install":
        print("Installing dependencies...")
        return run_command("poetry install", cwd=backend_dir)
        
    elif command == "add":
        if len(sys.argv) < 3:
            print("❌ Please specify a package to add")
            print("Example: python manage_deps.py add pandas")
            return 1
        packages = " ".join(sys.argv[2:])
        print(f"Adding {packages}...")
        return run_command(f"poetry add {packages}", cwd=backend_dir)
        
    elif command == "remove":
        if len(sys.argv) < 3:
            print("❌ Please specify a package to remove")
            return 1
        packages = " ".join(sys.argv[2:])
        print(f"Removing {packages}...")
        return run_command(f"poetry remove {packages}", cwd=backend_dir)
        
    elif command == "update":
        print("Updating all packages...")
        return run_command("poetry update", cwd=backend_dir)
        
    elif command == "export":
        print("Exporting platform-specific requirements files...")
        return run_command("poetry run export-requirements", cwd=backend_dir)
        
    elif command == "shell":
        print("Activating Poetry shell...")
        return run_command("poetry shell", cwd=backend_dir)
        
    else:
        print(f"❌ Unknown command: {command}")
        return 1

if __name__ == "__main__":
    sys.exit(main())