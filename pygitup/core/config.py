
import os
import yaml
import getpass
import json
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

def get_config_dir():

    """Returns the platform-specific hidden directory for PyGitUp config."""

    home = os.path.expanduser("~")

    config_dir = os.path.join(home, ".pygitup_config")

    profiles_dir = os.path.join(config_dir, "profiles")

    

    if not os.path.exists(profiles_dir):

        os.makedirs(profiles_dir, exist_ok=True)

    return config_dir



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

        except Exception:

            pass

            

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

    except Exception as e:

        return False, str(e)



def list_profiles():

    """Lists all available profiles."""

    profiles_dir = os.path.join(get_config_dir(), "profiles")

    return [f.replace(".yaml", "") for f in os.listdir(profiles_dir) if f.endswith(".yaml")]



def load_config(config_path=None):

    """Load configuration from the active stealth profile or return defaults."""

    config = DEFAULT_CONFIG.copy()

    

    if config_path is None:

        config_path = get_active_profile_path()

    

    if os.path.exists(config_path):

        try:

            with open(config_path, 'r') as f:

                file_config = yaml.safe_load(f)

                if file_config:

                    # Deep merge dictionaries

                    for section in file_config:

                        if section in config:

                            config[section].update(file_config[section])

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

    print_warning("No GitHub Token found in active stealth profile.")

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



def configuration_wizard(profile_name=None):



    """Guides the user through one-time stealth setup for a specific profile."""



    print_header("PyGitUp Stealth Setup")



    



    if not profile_name:



        profile_name = input("🏷️ Enter a name for this profile (e.g., work, personal) [default]: ") or "default"



    



    config_path = os.path.join(get_config_dir(), "profiles", f"{profile_name}.yaml")



    existing_config = {}



    mode = "overwrite" # default







    if os.path.exists(config_path):



        print_warning(f"Configuration for profile '{profile_name}' already exists.")



        print("1: [red]Overwrite completely[/red]")



        print("2: [green]Fill missing values only[/green]")



        print("3: [white]Cancel[/white]")



        



        choice = input("\n👉 Choice (1-3): ")



        if choice == '3':



            print_info("Setup cancelled.")



            return



        elif choice == '2':



            mode = "fill_missing"



            # Load existing



            try:



                with open(config_path, 'r') as f:



                    existing_config = yaml.safe_load(f) or {}



            except Exception:



                pass







    print_info(f"Configuring profile: {profile_name} ({mode})")







    # Start with default structure, update with existing if filling



    config = DEFAULT_CONFIG.copy()



    if mode == "fill_missing" and existing_config:



        # Deep merge



        for section in existing_config:



            if section in config:



                config[section].update(existing_config[section])







    # Username



    current_user = config["github"].get("username", "")



    if mode == "overwrite" or not current_user:



        val = input(f'GitHub username: ')



        if val: config["github"]["username"] = val



    else:



        print_info(f"Username already set: {current_user}")







    # GitHub Token



    current_token = config["github"].get("token", "")



    if mode == "overwrite" or not current_token:



        val = getpass.getpass("GitHub Token (Hidden): ")



        if val: config["github"]["token"] = val



    else:



        print_info("GitHub Token already set.")







    # AI API Key



    current_ai = config["github"].get("ai_api_key", "")



    if mode == "overwrite" or not current_ai:



        val = getpass.getpass("Gemini API Key (Hidden): ")



        if val: config["github"]["ai_api_key"] = val



    else:



        print_info("Gemini API Key already set.")







    try:



        # Secure the file permissions



        with open(config_path, "w") as f:



            yaml.dump(config, f, default_flow_style=False)



        



        if os.name != 'nt':



            os.chmod(config_path, 0o600)



            



        # Automatically set as active if it's the only one or if user wants



        set_active_profile(profile_name)



        print_success(f"\nProfile '{profile_name}' updated and activated!")



    except Exception as e:



        print_error(f"\nError locking profile: {e}")
