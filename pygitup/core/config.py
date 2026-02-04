import os
import yaml
import getpass
import json
import copy
import base64
import hashlib
from cryptography.fernet import Fernet
from ..utils.ui import print_success, print_error, print_info, print_header, print_warning

# Default configuration
DEFAULT_CONFIG = {
    "defaults": {
        "commit_message": "Update from PyGitUp",
        "branch": "main"
    },
    "github": {
        "username": "",
        "token": "",
        "token_file": "",
        "ai_api_key": "",
        "default_description": "Repository created with PyGitUp",
        "default_private": False
    },
    "batch": {
        "max_files": 100,
        "continue_on_error": False
    },
    "performance": {
        "max_parallel_uploads": 5,
        "timeout": 30
    },
    "logging": {
        "enabled": False,
        "file": "pygitup.log",
        "level": "INFO"
    },
    "templates": {
        "directory": "./templates"
    },
    "scheduling": {
        "offline_queue_file": ".pygitup_offline_queue"
    },
    "analytics": {
        "period": "last-month"
    }
}

def get_encryption_key():
    """Derives a stable encryption key from system characteristics."""
    try:
        # Create a unique but stable string based on system/user info
        sys_info = f"{os.uname().nodename if hasattr(os, 'uname') else os.name}_{getpass.getuser()}"
        key = base64.urlsafe_b64encode(hashlib.sha256(sys_info.encode()).digest()[:32])
        return key
    except Exception:
        # Fallback to a hardcoded string if system info is unavailable
        return b'pYgItUp_sTeAlTh_EnCrYpTiOn_KeY_001='

def encrypt_data(data):
    """Encrypts sensitive data using Fernet."""
    if not data: return ""
    f = Fernet(get_encryption_key())
    return f.encrypt(data.encode()).decode()

def decrypt_data(data):
    """Decrypts sensitive data. Returns original if it's not encrypted (legacy)."""
    if not data: return ""
    try:
        f = Fernet(get_encryption_key())
        return f.decrypt(data.encode()).decode()
    except Exception:
        return data

def get_config_dir():
    """Returns the platform-specific hidden directory for PyGitUp config."""
    home = os.path.expanduser("~")
    config_dir = os.path.join(home, ".pygitup_config")
    profiles_dir = os.path.join(config_dir, "profiles")
    if not os.path.exists(profiles_dir):
        os.makedirs(profiles_dir, exist_ok=True)
    return config_dir

def validate_config_path(config_path):
    """Ensures the config path stays within the stealth directory."""
    config_dir = os.path.abspath(get_config_dir())
    requested_path = os.path.abspath(config_path)
    if not requested_path.startswith(config_dir):
        raise ValueError("Security Alert: Unauthorized configuration path.")
    return True

def get_active_profile_path():
    """Returns the path to the active profile's config file."""
    config_dir = get_config_dir()
    settings_path = os.path.join(config_dir, "settings.json")
    active_profile = "default"
    if os.path.exists(settings_path):
        try:
            with open(settings_path, 'r') as f:
                settings = json.load(f)
                active_profile = settings.get("active_profile", "default")
        except Exception: pass
    return os.path.join(config_dir, "profiles", f"{active_profile}.yaml")

def set_active_profile(profile_name):
    """Sets the active profile in settings.json."""
    config_dir = get_config_dir()
    settings_path = os.path.join(config_dir, "settings.json")
    profile_path = os.path.join(config_dir, "profiles", f"{profile_name}.yaml")
    if not os.path.exists(profile_path):
        return False, f"Profile '{profile_name}' does not exist."
    try:
        with open(settings_path, 'w') as f:
            json.dump({"active_profile": profile_name}, f)
        return True, f"Switched to profile: {profile_name}"
    except Exception as e: return False, str(e)

def list_profiles():
    """Lists all available profiles."""
    profiles_dir = os.path.join(get_config_dir(), "profiles")
    if not os.path.exists(profiles_dir): return []
    return [f.replace(".yaml", "") for f in os.listdir(profiles_dir) if f.endswith(".yaml")]

def load_config(config_path=None):
    """Load configuration from the active stealth profile or return defaults."""
    config = copy.deepcopy(DEFAULT_CONFIG)
    if config_path is None:
        config_path = get_active_profile_path()
    else:
        try: validate_config_path(config_path)
        except ValueError as e:
            print_error(str(e))
            return config

    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                file_config = yaml.safe_load(f)
                if file_config:
                    for section in file_config:
                        if section in config:
                            config[section].update(file_config[section])
                    
                    # Decrypt sensitive fields
                    config["github"]["token"] = decrypt_data(config["github"].get("token"))
                    config["github"]["ai_api_key"] = decrypt_data(config["github"]["ai_api_key"])
        except Exception as e: print_warning(f"Could not load stealth config: {e}")
    return config

def get_github_token(config):
    """Get GitHub token from config, file, or environment."""
    token = config["github"].get("token")
    if token: return token.strip()
    
    # Check environment variable
    token = os.environ.get("GITHUB_TOKEN")
    if token: return token.strip()
    
    print_warning("No GitHub Token found in active stealth profile.")
    token = getpass.getpass("🔑 Enter your GitHub Personal Access Token: ").strip()
    return token

def get_github_username(config):
    """Get GitHub username from config."""
    user = config["github"].get("username")
    return user.strip() if user else input("👤 Enter your GitHub username: ").strip()

def configuration_wizard(profile_name=None):
    """Guides the user through one-time stealth setup with encryption."""
    print_header("PyGitUp Stealth Setup")
    if not profile_name:
        profile_name = input("🏷️ Enter profile name [default]: ") or "default"
    
    config_path = os.path.join(get_config_dir(), "profiles", f"{profile_name}.yaml")
    existing_config = {}
    mode = "overwrite"

    if os.path.exists(config_path):
        print_warning(f"Profile '{profile_name}' already exists.")
        print("1: [red]Overwrite[/red] | 2: [green]Fill Missing[/green] | 3: [white]Cancel[/white]")
        choice = input("\n👉 Choice: ")
        if choice == '3': return
        if choice == '2':
            mode = "fill_missing"
            try:
                with open(config_path, 'r') as f:
                    existing_config = yaml.safe_load(f) or {}
            except Exception: pass

    print_info(f"Configuring: {profile_name} ({mode})")
    config = copy.deepcopy(DEFAULT_CONFIG)
    if mode == "fill_missing" and existing_config:
        for section in existing_config:
            if section in config: config[section].update(existing_config[section])
        # Decrypt sensitive data for editing
        config["github"]["token"] = decrypt_data(config["github"].get("token"))
        config["github"]["ai_api_key"] = decrypt_data(config["github"]["ai_api_key"])

    # Inputs
    u = input(f"GitHub Username [{'set' if config['github']['username'] else 'empty'}]: ").strip()
    if u: config["github"]["username"] = u
    
    t = getpass.getpass(f"GitHub Token [{'set' if config['github']['token'] else 'empty'}]: ").strip()
    if t: config["github"]["token"] = t
    
    a = getpass.getpass(f"Gemini AI Key [{'set' if config['github']['ai_api_key'] else 'empty'}]: ").strip()
    if a: config["github"]["ai_api_key"] = a

    try:
        # Encrypt sensitive data before saving
        save_config = copy.deepcopy(config)
        save_config["github"]["token"] = encrypt_data(config["github"]["token"])
        save_config["github"]["ai_api_key"] = encrypt_data(config["github"]["ai_api_key"])

        with open(config_path, "w") as f:
            yaml.dump(save_config, f, default_flow_style=False)
        
        if os.name != 'nt': os.chmod(config_path, 0o600)
        set_active_profile(profile_name)
        print_success(f"Profile '{profile_name}' secured and activated!")
    except Exception as e: print_error(f"Error locking profile: {e}")
