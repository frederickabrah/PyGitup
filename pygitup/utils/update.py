
import requests
import subprocess
import os
from .. import __version__
from .ui import print_info, print_success, print_error, print_warning

GITHUB_REPO_URL = "https://api.github.com/repos/frederickabrah/PyGitUp/releases/latest"

def check_for_updates():
    """Checks GitHub for a newer version of PyGitUp."""
    try:
        # We use a short timeout to not hang startup
        response = requests.get(GITHUB_REPO_URL, timeout=3)
        if response.status_code == 200:
            latest_release = response.json()
            latest_version = latest_release.get("tag_name", "").replace("v", "")
            
            if is_newer(latest_version, __version__):
                print_warning(f"🚀 A new version of PyGitUp is available: v{latest_version} (Current: v{__version__})")
                confirm = input("Would you like to update now? (y/n): ").lower()
                if confirm == 'y':
                    perform_update()
        elif response.status_code == 404:
            # Fallback: Check setup.py on main branch if no releases yet
            check_fallback_version()
    except Exception:
        # Silently fail if offline or API is down
        pass

def is_newer(latest, current):
    """Simple semantic version comparison."""
    try:
        l_parts = [int(x) for x in latest.split(".")]
        c_parts = [int(x) for x in current.split(".")]
        return l_parts > c_parts
    except Exception:
        return False

def check_fallback_version():
    """Fallback: Check version in setup.py on the main branch."""
    try:
        url = "https://raw.githubusercontent.com/frederickabrah/PyGitUp/main/pygitup/__init__.py"
        resp = requests.get(url, timeout=3)
        if resp.status_code == 200:
            content = resp.text
            for line in content.splitlines():
                if "__version__" in line:
                    latest_v = line.split("=")[1].strip().strip('"').strip("'")
                    if is_newer(latest_v, __version__):
                        print_warning(f"🚀 A new update is available on GitHub (v{latest_v})")
                        confirm = input("Would you like to pull the latest changes? (y/n): ").lower()
                        if confirm == 'y':
                            perform_update()
    except Exception:
        pass

def perform_update():
    """Executes a safe update via git pull."""
    print_info("Attempting to update PyGitUp...")
    try:
        # Check if we are in a git repo
        if os.path.isdir(".git"):
            # Use git pull
            result = subprocess.run(["git", "pull", "origin", "main"], capture_output=True, text=True)
            if result.returncode == 0:
                print_success("PyGitUp has been updated successfully! Please restart the tool.")
                exit(0)
            else:
                print_error(f"Update failed: {result.stderr}")
        else:
            print_error("Automatic update only supported for Git installations. Please run 'pip install --upgrade .'")
    except Exception as e:
        print_error(f"An error occurred during update: {e}")
