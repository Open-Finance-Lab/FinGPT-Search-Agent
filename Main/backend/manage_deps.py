#!/usr/bin/env python3
"""
Dependency management helper script for FinGPT backend.
This script provides easy commands to manage dependencies with uv.
"""
import subprocess
import sys
import os
from pathlib import Path

PYTHON_VERSION = "3.12"

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
        print("FinGPT Backend Dependency Manager (uv)")
        print("=======================================")
        print("\nUsage: python manage_deps.py <command>")
        print("\nCommands:")
        print(f"  install      - Install backend dependencies (Python {PYTHON_VERSION}, no docs)")
        print(f"  install-dev  - Install backend + docs dependencies (Python {PYTHON_VERSION})")
        print("  add <pkg>    - Add a new package")
        print("  remove <pkg> - Remove a package")
        print("  update       - Update all packages")
        print("  lock         - Update lock file")
        print("  sync         - Sync environment with lock file")
        print("\nExamples:")
        print("  python manage_deps.py install")
        print("  python manage_deps.py add pandas")
        print("  python manage_deps.py sync")
        return 1

    command = sys.argv[1]

    # Check if uv is installed
    uv_check = subprocess.run("uv --version", shell=True, capture_output=True)
    if uv_check.returncode != 0:
        print("❌ uv is not installed. Please install it first:")
        print("   curl -LsSf https://astral.sh/uv/install.sh | sh")
        print("\nOr on Windows:")
        print("   powershell -c \"irm https://astral.sh/uv/install.ps1 | iex\"")
        print("\nOr visit: https://github.com/astral-sh/uv")
        return 1

    def sync(args=""):
        base_cmd = f"uv sync --python {PYTHON_VERSION} --frozen".strip()
        if args:
            base_cmd = f"{base_cmd} {args}"
        return run_command(base_cmd, cwd=backend_dir)

    if command == "install":
        print(f"Installing backend dependencies with Python {PYTHON_VERSION}...")
        print("Docs are skipped by default to keep the environment lean.")
        return sync()

    elif command == "install-dev":
        print(f"Installing backend + docs dependencies with Python {PYTHON_VERSION}...")
        return sync("--group docs")

    elif command == "add":
        if len(sys.argv) < 3:
            print("❌ Please specify a package to add")
            print("Example: python manage_deps.py add pandas")
            return 1
        packages = " ".join(sys.argv[2:])
        print(f"Adding {packages}...")
        return run_command(f"uv add {packages}", cwd=backend_dir)

    elif command == "remove":
        if len(sys.argv) < 3:
            print("❌ Please specify a package to remove")
            return 1
        packages = " ".join(sys.argv[2:])
        print(f"Removing {packages}...")
        return run_command(f"uv remove {packages}", cwd=backend_dir)

    elif command == "update":
        print(f"Updating all packages for Python {PYTHON_VERSION}...")
        return run_command(f"uv lock --upgrade --python {PYTHON_VERSION}", cwd=backend_dir)

    elif command == "lock":
        print(f"Refreshing lock file for Python {PYTHON_VERSION}...")
        return run_command(f"uv lock --python {PYTHON_VERSION}", cwd=backend_dir)

    elif command == "sync":
        print(f"Syncing environment with lock file using Python {PYTHON_VERSION}...")
        return sync()

    else:
        print(f"❌ Unknown command: {command}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
