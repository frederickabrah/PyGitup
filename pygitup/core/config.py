
import os
import yaml
import getpass
from ..utils.ui import print_success, print_error, print_info, print_header, print_warning

# Default configuration
DEFAULT_CONFIG = {
    "defaults": {
        "commit_message": "Update from PyGitUp",
        "branch": "main"
    },
    "github": {
        "username": "",
        "token_file": "",
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

def get_config_dir():
    """Returns the platform-specific hidden directory for PyGitUp config."""
    home = os.path.expanduser("~")
    # Stealth location: hidden folder in home directory
    config_dir = os.path.join(home, ".pygitup_config")
    if not os.path.exists(config_dir):
        os.makedirs(config_dir, exist_ok=True)
    return config_dir

def load_config(config_path=None):
    """Load configuration from the stealth global path or return defaults."""
    config = DEFAULT_CONFIG.copy()
    
    if config_path is None:
        # Prioritize the stealth global path
        config_path = os.path.join(get_config_dir(), "config.yaml")
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                file_config = yaml.safe_load(f)
                if file_config:
                    for key in config:
                        if key in file_config:
                            config[key].update(file_config[key])
        except Exception as e:
            print_warning(f"Could not load stealth config: {e}")
    
    return config

def get_github_token(config):
    """Get GitHub token from config, file, or environment."""
    # Check if token is already in config (one-time setup)
    if config["github"].get("token"):
        return config["github"]["token"]

    if config["github"]["token_file"] and os.path.exists(config["github"]["token_file"]):
        try:
            with open(config["github"]["token_file"], 'r') as f:
                return f.read().strip()
        except Exception as e:
            print_warning(f"Could not read token file: {e}")
    
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    
    # If still not found, we really need it
    print_warning("No GitHub Token found in stealth storage.")
    token = getpass.getpass("🔑 Enter your GitHub Personal Access Token: ")
    return token

def get_github_username(config):
    """Get GitHub username from config or environment."""
    if config["github"]["username"]:
        return config["github"]["username"]
    
    username = os.environ.get("GITHUB_USERNAME")
    if username:
        return username
    
    return input("👤 Enter your GitHub username: ")

def configuration_wizard():
    """Guides the user through one-time stealth setup."""
    print_header("PyGitUp Stealth Setup")
    print_info("Saving credentials to a secure hidden location...")

    config = DEFAULT_CONFIG.copy()
    config_path = os.path.join(get_config_dir(), "config.yaml")

    config["github"]["username"] = input(f'GitHub username: ') or config["github"]["username"]
    # We save the token directly in the yaml now for the "Set and Forget" experience
    token = getpass.getpass("GitHub Token (Hidden): ")
    config["github"]["token"] = token 

    try:
        # Secure the file permissions (Owner Read/Write only)
        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False)
        
        # On Unix systems, make the file private
        if os.name != 'nt':
            os.chmod(config_path, 0o600)
            
        print_success(f"\nConfiguration locked in {config_path}")
    except Exception as e:
        print_error(f"\nError locking configuration: {e}")
