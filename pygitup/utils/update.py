import requests
import subprocess
import os
import sys
from .. import __version__
from .ui import print_info, print_success, print_error, print_warning

# Use the case-sensitive URL as reported by GitHub
GITHUB_RAW_VERSION_URL = "https://raw.githubusercontent.com/frederickabrah/PyGitup/main/pygitup/__init__.py"

def is_newer(latest, current):
    """Simple semantic version comparison."""
    try:
        l_parts = [int(x) for x in latest.split(".")]
        c_parts = [int(x) for x in current.split(".")]
        # Compare parts (1.5.0 > 1.4.0)
        for l, c in zip(l_parts, c_parts):
            if l > c: return True
            if l < c: return False
        return len(l_parts) > len(c_parts)
    except Exception:
        return False

def check_for_updates():
    """Checks GitHub for a newer version of PyGitUp by reading the raw source."""
    try:
        # We check the raw __init__.py because it's the most "real-time" source
        response = requests.get(GITHUB_RAW_VERSION_URL, timeout=3)
        if response.status_code == 200:
            content = response.text
            latest_version = "0.0.0"
            for line in content.splitlines():
                if "__version__" in line:
                    latest_version = line.split("=")[1].strip().strip('"').strip("'")
                    break
            
            if is_newer(latest_version, __version__):
                print_warning(f"🚀 A new update is available: v{latest_version} (Current: v{__version__})")
                confirm = input("Would you like to auto-update now? (y/n): ").lower()
                if confirm == 'y':
                    perform_update()
    except Exception:
        # Fail silently to not disturb the user's workflow if offline
        pass

def perform_update():
    """Executes a safe update by finding the package source and pulling."""
    print_info("Initiating self-update sequence...")
    
    # 1. Find the root of the PyGitUp installation
    # pygitup/utils/update.py -> pygitup/utils -> pygitup -> PyGitUp (root)
    try:
        current_file_path = os.path.abspath(__file__)
        package_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file_path)))
        
        original_cwd = os.getcwd()
        
        if os.path.exists(os.path.join(package_root, ".git")):
            print_info(f"Updating source at: {package_root}")
            os.chdir(package_root)
            
            # 2. Perform the pull
            result = subprocess.run(["git", "pull", "origin", "main"], capture_output=True, text=True)
            
            if result.returncode == 0:
                print_success("PyGitUp updated to the latest version!")
                print_info("Please restart the tool to apply changes.")
                os.chdir(original_cwd)
                sys.exit(0)
            else:
                print_error(f"Git Pull Failed: {result.stderr}")
        else:
            print_error("This installation is not managed by Git. Please update manually via 'pip install --upgrade .'")
            
        os.chdir(original_cwd)
    except Exception as e:
        print_error(f"Update sequence failed: {e}")