#!/usr/bin/env python3
"""
Export platform-specific requirements files from Poetry configuration.
This script generates requirements_win.txt and requirements_mac.txt files.
"""
import subprocess
import sys
import os
from pathlib import Path

def export_requirements():
    """Export platform-specific requirements files."""
    
    # Get the project root directory (parent of backend)
    backend_dir = Path(__file__).parent.parent
    project_root = backend_dir.parent.parent
    requirements_dir = project_root / "Requirements"
    
    # Ensure Requirements directory exists
    requirements_dir.mkdir(exist_ok=True)
    
    print("Exporting platform-specific requirements files...")
    
    # Define platform configurations
    platforms = {
        'win': {
            'file': 'requirements_win.txt',
            'marker': 'sys_platform == "win32"'
        },
        'mac': {
            'file': 'requirements_mac.txt', 
            'marker': 'sys_platform == "darwin"'
        }
    }
    
    # Export requirements for each platform
    for platform, config in platforms.items():
        output_file = requirements_dir / config['file']
        
        # Use poetry export with platform markers
        cmd = [
            'poetry', 'export',
            '--format', 'requirements.txt',
            '--output', str(output_file),
            '--without-hashes',
            '--with', 'docs'  # Include documentation dependencies
        ]
        
        try:
            # First, export all dependencies
            print(f"Generating {config['file']}...")
            result = subprocess.run(cmd, cwd=backend_dir, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"Error exporting {platform} requirements: {result.stderr}")
                continue
                
            # Post-process to handle platform-specific dependencies
            with open(output_file, 'r') as f:
                lines = f.readlines()
            
            # Filter out platform-specific lines that don't match current platform
            filtered_lines = []
            for line in lines:
                # Skip comments about platform markers for other platforms
                if platform == 'win' and 'sys_platform == "darwin"' in line:
                    continue
                elif platform == 'mac' and 'sys_platform == "win32"' in line:
                    continue
                    
                # Keep the line if it's not platform-specific or matches our platform
                filtered_lines.append(line)
            
            # Write filtered content back
            with open(output_file, 'w') as f:
                f.writelines(filtered_lines)
                
            print(f"✅ Successfully exported {config['file']}")
            
        except FileNotFoundError:
            print("❌ Error: Poetry not found. Please install Poetry first:")
            print("   pip install poetry")
            return 1
        except Exception as e:
            print(f"❌ Error exporting {platform} requirements: {e}")
            return 1
    
    print("\n✅ All requirements files exported successfully!")
    print(f"Files created in: {requirements_dir}")
    return 0

def main():
    """Main entry point for the script."""
    return export_requirements()

if __name__ == "__main__":
    sys.exit(main())