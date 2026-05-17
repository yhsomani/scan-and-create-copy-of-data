import os
import subprocess
import sys
from pathlib import Path

def build():
    print("Starting Antigravity Enterprise Build Sequence...")
    
    # 1. Clean previous builds
    for folder in ["build", "dist"]:
        if os.path.exists(folder):
            print(f"Cleaning {folder}...")
            import shutil
            shutil.rmtree(folder)

    # 2. PyInstaller command
    # --noconsole: Hide terminal window
    # --onefile: Bundle into a single EXE
    # --name: Name of the output file
    # --add-data: Include static assets (if any)
    
    cmd = [
        "pyinstaller",
        "--noconsole",
        "--onefile",
        "--name=AntigravityScanner",
        "--clean",
        "main.py"
    ]
    
    # Add hidden imports for dynamic modules
    hidden_imports = [
        "app.views.scan_view",
        "app.views.analytics_view",
        "app.views.history_view",
        "app.views.security_view",
        "app.views.plugin_view",
        "app.views.settings_view"
    ]
    
    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])

    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    
    print("\nBuild Complete! Executable found in 'dist/AntigravityScanner.exe'")

if __name__ == "__main__":
    build()
