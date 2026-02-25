import os
import yaml
import getpass
import json
import copy
import base64
import hashlib
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False
from ..utils.ui import print_success, print_error, print_info, print_header, print_warning, console

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

# Global cache for the session key so we don't ask for password on every single read
_SESSION_KEY = None

def derive_key(password, salt):
    """Derives a strong key from a password using PBKDF2."""
    if not HAS_CRYPTO: return None
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))

def get_master_key(salt):
    """Retrieves or prompts for the master session key."""
    global _SESSION_KEY
    if _SESSION_KEY: return _SESSION_KEY
    
    # Securely prompt for password once per session
    print_warning("🔐 Vault Locked: Master Password required for this session.")
    password = getpass.getpass("🔑 Enter Master Password: ")
    
    _SESSION_KEY = derive_key(password, salt)
    return _SESSION_KEY

def encrypt_data(data, salt):
    """Encrypts sensitive data with a password-derived key. Requires cryptography."""
    if not data: return ""
    if HAS_CRYPTO:
        try:
            key = get_master_key(salt)
            f = Fernet(key)
            return f.encrypt(data.encode()).decode()
        except Exception as e:
            print_error(f"Encryption failed: {e}")
            return ""
    else:
        print_error("CRITICAL: 'cryptography' library missing. Cannot encrypt sensitive data.")
        print_info("Install it now: pip install cryptography")
        raise RuntimeError("Insecure storage attempt blocked.")

def decrypt_data(data, salt):
    """Decrypts sensitive data with a password-derived key. Requires cryptography."""
    if not data: return ""
    if not HAS_CRYPTO:
        print_error("CRITICAL: 'cryptography' library missing. Cannot decrypt sensitive data.")
        return ""

    try:
        key = get_master_key(salt)
        f = Fernet(key)
        return f.decrypt(data.encode()).decode().strip()
    except Exception:
        # Don't print error here to avoid noise during background loads,
        # but return empty to signify failure.
        return ""

def get_config_dir():
    """Returns the platform-specific hidden directory for PyGitUp config."""
    home = os.path.expanduser("~")
    config_dir = os.path.join(home, ".pygitup_config")
    profiles_dir = os.path.join(config_dir, "profiles")
    if not os.path.exists(profiles_dir):
        os.makedirs(profiles_dir, exist_ok=True)
    return config_dir

def validate_config_path(config_path):
    config_dir = os.path.abspath(get_config_dir())
    requested_path = os.path.abspath(config_path)
    if not requested_path.startswith(config_dir):
        raise ValueError("Security Alert: Unauthorized configuration path.")
    return True

def get_active_profile_path():
    config_dir = get_config_dir()
    settings_path = os.path.join(config_dir, "settings.json")
    active_profile = "default"
    if os.path.exists(settings_path):
        try:
            with open(settings_path, 'r') as f:
                settings = json.load(f)
                active_profile = settings.get("active_profile", "default")
        except (json.JSONDecodeError, IOError):
            # Fallback to default if settings are corrupted or unreadable
            active_profile = "default"
    return os.path.join(config_dir, "profiles", f"{active_profile}.yaml")

def set_active_profile(profile_name):
    config_dir = get_config_dir()
    settings_path = os.path.join(config_dir, "settings.json")
    profile_path = os.path.join(config_dir, "profiles", f"{profile_name}.yaml")
    if not os.path.exists(profile_path):
        return False, f"Profile '{profile_name}' does not exist."
    try:
        with open(settings_path, 'w') as f:
            json.dump({"active_profile": profile_name}, f)
        # Clear session key on switch to force re-auth for new profile
        global _SESSION_KEY
        _SESSION_KEY = None
        os.environ.pop("PYGITUP_PASSWORD", None)
        return True, f"Switched to profile: {profile_name}"
    except Exception as e: return False, str(e)

def list_profiles():
    profiles_dir = os.path.join(get_config_dir(), "profiles")
    if not os.path.exists(profiles_dir): return []
    return [f.replace(".yaml", "") for f in os.listdir(profiles_dir) if f.endswith(".yaml")]

def load_config(config_path=None):
    """Load configuration from the active profile."""
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
                    # Deep merge: copy ALL sections from file_config to config
                    for section in file_config:
                        if section in config and isinstance(config[section], dict) and isinstance(file_config[section], dict):
                            config[section].update(file_config[section])
                        else:
                            # For non-dict sections or new sections, just copy
                            config[section] = file_config[section]

                    # Extract salt and decrypt
                    salt_hex = config.get("security", {}).get("salt", "")
                    if salt_hex:
                        salt = bytes.fromhex(salt_hex)
                        config["github"]["token"] = decrypt_data(config["github"].get("token"), salt)
                        config["github"]["ai_api_key"] = decrypt_data(config["github"].get("ai_api_key"), salt)
        except Exception as e: 
            print_warning(f"Could not load config: {e}")
    return config

def get_github_token(config):
    token = config["github"].get("token")
    if token: return token.strip()
    token = os.environ.get("GITHUB_TOKEN")
    if token: return token.strip()
    return ""

def get_github_username(config):
    user = config["github"].get("username")
    return user.strip() if user else ""

def configuration_wizard(profile_name=None):
    """Guides the user through one-time encrypted setup."""
    print_header("PyGitUp Secure Setup")
    if not profile_name:
        profile_name = input("🏷️ Enter profile name [default]: ") or "default"
    
    config_path = os.path.join(get_config_dir(), "profiles", f"{profile_name}.yaml")
    existing_config = {}
    mode = "overwrite"

    if os.path.exists(config_path):
        print_warning(f"Profile '{profile_name}' already exists.")
        console.print("\n[bold]Choose an action:[/bold]")
        console.print("  1: [red]Overwrite[/red] (Reset all credentials)")
        console.print("  2: [green]Fill Missing[/green] (Keep existing, add new ones)")
        console.print("  3: [white]Cancel[/white]")
        
        choice = input("\n👉 Choice: ").strip()
        if choice == '3': return
        if choice == '2':
            mode = "fill_missing"
            try:
                with open(config_path, 'r') as f:
                    existing_config = yaml.safe_load(f) or {}
            except (yaml.YAMLError, IOError) as e:
                print_warning(f"Could not read existing profile: {e}. Starting fresh.")
                existing_config = {}

    console.print(f"\n[cyan]Context: {profile_name}[/cyan] | Mode: {mode}\n")
    
    # 1. Set Master Password
    password = getpass.getpass("🔐 Set Master Password for this profile: ")
    confirm = getpass.getpass("🔐 Confirm Password: ")
    if password != confirm:
        print_error("Passwords do not match.")
        return
    
    # Generate new salt for this profile
    salt = os.urandom(16)
    # Cache key for this session
    global _SESSION_KEY
    _SESSION_KEY = derive_key(password, salt)
    
    config = copy.deepcopy(DEFAULT_CONFIG)
    if mode == "fill_missing" and existing_config:
        # Transfer existing non-sensitive config
        for section in existing_config:
            if section in config and section != "security":
                config[section].update(existing_config[section])

    u = input(f"GitHub Username: ").strip()
    if u: config["github"]["username"] = u
    
    t = getpass.getpass(f"GitHub Token (Hidden): ").strip()
    if t: config["github"]["token"] = t
    
    a = getpass.getpass(f"Gemini AI Key (Hidden): ").strip()
    if a: config["github"]["ai_api_key"] = a

    try:
        save_config = copy.deepcopy(config)
        save_config["security"] = {"salt": salt.hex()}
        save_config["github"]["token"] = encrypt_data(config["github"]["token"], salt)
        save_config["github"]["ai_api_key"] = encrypt_data(config["github"]["ai_api_key"], salt)

        with open(config_path, "w") as f:
            yaml.dump(save_config, f, default_flow_style=False)
        
        if os.name != 'nt': os.chmod(config_path, 0o600)
        set_active_profile(profile_name)
        print_success(f"Profile '{profile_name}' encrypted and locked!")
    except Exception as e: print_error(f"Error locking profile: {e}")

def check_crypto_installed():
    if not HAS_CRYPTO:
        print_warning("CRITICAL SECURITY RISK: 'cryptography' library missing.")
        print_info("Install immediately: pkg install python-cryptography")