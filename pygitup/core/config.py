import os
import yaml
import getpass

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

def load_config(config_path=None):
    """Load configuration from file or return defaults."""
    config = DEFAULT_CONFIG.copy()
    
    if config_path is None:
        possible_paths = [
            "./pygitup.yaml",
            "./.pygituprc",
            os.path.expanduser("~/.pygituprc"),
            os.path.expanduser("~/.pygitup.yaml")
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                config_path = path
                break
    
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                file_config = yaml.safe_load(f)
                for key in config:
                    if key in file_config:
                        config[key].update(file_config[key])
        except Exception as e:
            print(f"Warning: Could not load config file {config_path}: {e}")
    
    return config

def get_github_token(config):
    """Get GitHub token from config, file, or environment."""
    if config["github"]["token_file"] and os.path.exists(config["github"]["token_file"]):
        try:
            with open(config["github"]["token_file"], 'r') as f:
                return f.read().strip()
        except Exception as e:
            print(f"Warning: Could not read token file: {e}")
    
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    
    return getpass.getpass("Enter your GitHub Personal Access Token: ")

def get_github_username(config):
    """Get GitHub username from config or environment."""
    if config["github"]["username"]:
        return config["github"]["username"]
    
    username = os.environ.get("GITHUB_USERNAME")
    if username:
        return username
    
    return input("Enter your GitHub username: ")

def configuration_wizard():
    """Guides the user through creating a pygitup.yaml configuration file."""
    print("\n--- PyGitUp Configuration Wizard ---")
    print("This wizard will help you create a pygitup.yaml file to store your default settings.")

    config = DEFAULT_CONFIG.copy()

    config["github"]["username"] = input(f'Enter your GitHub username (default: {config["github"]["username"]}): ') or config["github"]["username"]
    config["github"]["token_file"] = input(f'Enter the path to your GitHub token file (default: {config["github"]["token_file"]}): ') or config["github"]["token_file"]
    config["defaults"]["commit_message"] = input(f'Enter your default commit message (default: {config["defaults"]["commit_message"]}): ') or config["defaults"]["commit_message"]
    config["defaults"]["branch"] = input(f'Enter your default branch name (default: {config["defaults"]["branch"]}): ') or config["defaults"]["branch"]

    try:
        with open("pygitup.yaml", "w") as f:
            yaml.dump(config, f, default_flow_style=False)
        print("\nConfiguration saved successfully to pygitup.yaml!")
    except Exception as e:
        print(f"\nError saving configuration: {e}")