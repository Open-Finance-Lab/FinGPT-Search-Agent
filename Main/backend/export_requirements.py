#!/usr/bin/env python3
"""
Export platform-specific requirements files from Poetry.
"""
import subprocess
import sys
import platform
from pathlib import Path

def main():
    """Export requirements files for different platforms."""
    backend_dir = Path(__file__).parent
    requirements_dir = backend_dir.parent.parent / "Requirements"
    
    print("Exporting platform-specific requirements files...")
    
    # Export Windows requirements
    print("Exporting Windows requirements...")
    cmd = [
        "poetry", "export",
        "-f", "requirements.txt",
        "--without-hashes",
        "-o", str(requirements_dir / "requirements_win.txt"),
        "--with-credentials"
    ]
    result = subprocess.run(cmd, cwd=backend_dir, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error exporting Windows requirements: {result.stderr}")
        return 1
    
    # For Mac/Linux, we need to manually filter out Windows-specific packages
    print("Exporting Mac/Linux requirements...")
    # First export all
    cmd = [
        "poetry", "export",
        "-f", "requirements.txt",
        "--without-hashes",
        "-o", str(requirements_dir / "requirements_mac_temp.txt"),
        "--with-credentials"
    ]
    result = subprocess.run(cmd, cwd=backend_dir, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error exporting Mac requirements: {result.stderr}")
        return 1
    
    # Read and filter the requirements
    temp_file = requirements_dir / "requirements_mac_temp.txt"
    mac_file = requirements_dir / "requirements_mac.txt"
    
    if temp_file.exists():
        with open(temp_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Filter out Windows-specific packages and adjust Django version
        filtered_lines = []
        for line in lines:
            # Skip Windows-specific packages
            if 'pywin32' in line.lower():
                continue
            # Replace Django version for Mac/Linux
            if line.startswith('django==5.1.11'):
                line = 'Django==4.2.23\n'
            filtered_lines.append(line)
        
        # Write filtered requirements
        with open(mac_file, 'w', encoding='utf-8') as f:
            f.writelines(filtered_lines)
        
        # Clean up temp file
        temp_file.unlink()
    
    print("Requirements files exported successfully!")
    print(f"  - Windows: {requirements_dir / 'requirements_win.txt'}")
    print(f"  - Mac/Linux: {requirements_dir / 'requirements_mac.txt'}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())