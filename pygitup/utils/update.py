
import requests
import subprocess
import os
import sys
import re
from .. import __version__
from .ui import print_info, print_success, print_error, print_warning

# CAUTION: Case-sensitive URL
GITHUB_RAW_VERSION_URL = "https://raw.githubusercontent.com/frederickabrah/PyGitUp/main/pygitup/__init__.py"

def is_newer(latest, current):
    """Robust semantic version comparison."""
    try:
        # Extract digits only to be safe
        l_parts = [int(re.sub(r'\D', '', x)) for x in latest.split(".")]
        c_parts = [int(re.sub(r'\D', '', x)) for x in current.split(".")]
        
        for i in range(max(len(l_parts), len(c_parts))):
            l = l_parts[i] if i < len(l_parts) else 0
            c = c_parts[i] if i < len(c_parts) else 0
            if l > c: return True
            if l < c: return False
        return False
    except Exception:
        return False

def check_for_updates():
    """Checks GitHub for a newer version using robust Regex parsing."""
    try:
        response = requests.get(GITHUB_RAW_VERSION_URL, timeout=5)
        if response.status_code == 200:
            content = response.text
            # Regex to find __version__ = "X.Y.Z" regardless of spaces or comments
            match = re.search(r'__version__\s*=\s*["\']([^"\\]+)["\']', content)
            if match:
                latest_version = match.group(1)
                
                if is_newer(latest_version, __version__):
                    print_warning(f"🚀 A new update is available: v{latest_version} (Current: v{__version__})")
                    confirm = input("Would you like to auto-update now? (y/n): ").lower()
                    if confirm == 'y':
                        perform_update()
    except Exception as e:
        if os.environ.get("PYGITUP_DEBUG"):
            print_warning(f"Update check skipped: {e}")

def perform_update():
    """Executes a deep full-system update."""
    print_info("Initiating Deep Update sequence...")
    
    try:
        current_file_path = os.path.abspath(__file__)
        package_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file_path)))
        original_cwd = os.getcwd()
        
        if os.path.exists(os.path.join(package_root, ".git")):
            print_info(f"Synchronizing source at: {package_root}")
            os.chdir(package_root)
            
            # 1. Pull latest code
            result = subprocess.run(["git", "pull", "origin", "main"], capture_output=True, text=True)
            
            if result.returncode == 0:
                print_success("Code successfully synchronized.")
                
                # 2. Update dependencies and entry points
                print_info("Updating system environment...")
                subprocess.run([sys.executable, "-m", "pip", "install", "-e", "."], capture_output=True)
                
                print_success("PyGitUp v2.0.1 is now installed!")
                print_info("Please restart the tool to enter God Mode.")
                os.chdir(original_cwd)
                sys.exit(0)
            else:
                print_error(f"Sync Failed: {result.stderr}")
        else:
            print_error("This installation is not managed by Git. Update manually via 'pip install --upgrade .'")
            
        os.chdir(original_cwd)
    except Exception as e:
        print_error(f"Update sequence failed: {e}")
