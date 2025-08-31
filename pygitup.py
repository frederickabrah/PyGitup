import os
import subprocess
import requests
import base64
import getpass
import argparse
import yaml
import json
import sys
import time
from pathlib import Path
from tqdm import tqdm

# Try to import optional dependencies
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False

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
    }
}

# ==============================================================================
# CONFIGURATION MANAGEMENT
# ==============================================================================

def load_config(config_path=None):
    """Load configuration from file or return defaults."""
    config = DEFAULT_CONFIG.copy()
    
    if not YAML_AVAILABLE:
        return config
    
    if config_path is None:
        # Look for config file in current directory or home directory
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
                # Merge with defaults
                for key in config:
                    if key in file_config:
                        config[key].update(file_config[key])
        except Exception as e:
            print(f"Warning: Could not load config file {config_path}: {e}")
    
    return config

def get_github_token(config):
    """Get GitHub token from config, file, or environment."""
    # Check config first
    if config["github"]["token_file"] and os.path.exists(config["github"]["token_file"]):
        try:
            with open(config["github"]["token_file"], 'r') as f:
                return f.read().strip()
        except Exception as e:
            print(f"Warning: Could not read token file: {e}")
    
    # Check environment variable
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    
    # Prompt user
    return getpass.getpass("Enter your GitHub Personal Access Token: ")

def get_github_username(config):
    """Get GitHub username from config or environment."""
    # Check config first
    if config["github"]["username"]:
        return config["github"]["username"]
    
    # Check environment variable
    username = os.environ.get("GITHUB_USERNAME")
    if username:
        return username
    
    # Prompt user
    return input("Enter your GitHub username: ")

# ==============================================================================
# LOGGING
# ==============================================================================

def log_message(message, level="INFO", config=None):
    """Log a message if logging is enabled."""
    if not config or not config["logging"]["enabled"]:
        return
    
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {level}: {message}\n"
    
    try:
        with open(config["logging"]["file"], "a") as f:
            f.write(log_entry)
    except Exception as e:
        pass  # Silently fail on logging errors

# ==============================================================================
# SECTION 1: UPLOAD/UPDATE A SINGLE FILE
# ==============================================================================

def get_single_file_input(config, args=None):
    """Gets user input for the file upload details."""
    if args and args.repo:
        repo_name = args.repo
    else:
        repo_name = input("Enter the name of the target GitHub repository: ")

    if args and args.file:
        local_file_path = args.file
        print(f"Selected file: {local_file_path}")
    else:
        print("\n--- Select a file to upload ---")
        local_file_path = None
        try:
            current_directory = os.getcwd()
            print(f"Listing files in: {current_directory}")
            
            files = [item for item in os.listdir('.') if os.path.isfile(item)]

            if not files:
                print("No files found in the current directory.")
            else:
                for i, filename in enumerate(files):
                    print(f"{i + 1}: {filename}")
                
                print("\nEnter the number of the file to upload, or type a different path manually.")
                choice = input("> ")

                try:
                    file_index = int(choice) - 1
                    if 0 <= file_index < len(files):
                        local_file_path = files[file_index]
                        print(f"You selected: {local_file_path}")
                    else:
                        print("Invalid number.")
                except ValueError:
                    local_file_path = choice
                    print(f"You entered path: {local_file_path}")

        except Exception as e:
            print(f"Could not list files interactively ({e}).")

    if not local_file_path:
        print("Please provide the file path manually.")
        local_file_path = input("Enter the full local path of the file to upload: ")

    if args and args.path:
        repo_file_path = args.path
    else:
        repo_file_path = input("Enter the path for the file in the repository (e.g., folder/file.txt): ")

    if args and args.message:
        commit_message = args.message
    else:
        default_msg = config["defaults"]["commit_message"]
        commit_message = input(f"Enter the commit message (default: {default_msg}): ")
        if not commit_message:
            commit_message = default_msg

    return repo_name, local_file_path, repo_file_path, commit_message

def upload_single_file(github_username, github_token, config, args=None):
    """Handles the entire process of uploading/updating a single file."""
    repo_name, local_file_path, repo_file_path, commit_message = get_single_file_input(config, args)

    api_url = f"https://api.github.com/repos/{github_username}/{repo_name}/contents/{repo_file_path}"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    try:
        with open(local_file_path, "rb") as f:
            # Show progress bar if available
            if TQDM_AVAILABLE:
                file_size = os.path.getsize(local_file_path)
                with tqdm(total=file_size, unit='B', unit_scale=True, desc="Reading file") as pbar:
                    content = f.read()
                    pbar.update(len(content))
                encoded_content = base64.b64encode(content).decode('utf-8')
            else:
                encoded_content = base64.b64encode(f.read()).decode('utf-8')
    except FileNotFoundError:
        print(f"Error: The local file '{local_file_path}' was not found.")
        if not args or not args.batch:
            sys.exit(1)
        return False
    except Exception as e:
        print(f"Error reading file: {e}")
        if not args or not args.batch:
            sys.exit(1)
        return False

    sha = None
    try:
        response = requests.get(api_url, headers=headers, timeout=config["performance"]["timeout"])
        if response.status_code == 200:
            print("File exists in the repository. It will be overwritten.")
            sha = response.json()['sha']
        elif response.status_code != 404:
            print(f"Error checking for file: {response.status_code} - {response.text}")
            if not args or not args.batch:
                sys.exit(1)
            return False
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to GitHub: {e}")
        if not args or not args.batch:
            sys.exit(1)
        return False

    data = {"message": commit_message, "content": encoded_content}
    if sha:
        data["sha"] = sha

    try:
        response = requests.put(api_url, headers=headers, json=data, timeout=config["performance"]["timeout"])
        response.raise_for_status()
        if response.status_code == 201:
            print(f"Successfully created file '{repo_file_path}' in '{repo_name}'.")
        elif response.status_code == 200:
            print(f"Successfully updated file '{repo_file_path}' in '{repo_name}'.")
        print(f"View the file at: {response.json()['content']['html_url']}")
        return True
    except requests.exceptions.HTTPError as e:
        print(f"Error uploading file: {e.response.status_code} - {e.response.text}")
        if not args or not args.batch:
            sys.exit(1)
        return False
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to GitHub: {e}")
        if not args or not args.batch:
            sys.exit(1)
        return False

# ==============================================================================
# SECTION 2: BATCH FILE UPLOAD
# ==============================================================================

def get_batch_files_input(config, args=None):
    """Get files for batch upload."""
    if args and args.files:
        files = args.files
    else:
        print("\n--- Select files for batch upload ---")
        print("Enter file paths separated by commas, or 'all' for all files in directory:")
        files_input = input("> ").strip()
        
        if files_input.lower() == 'all':
            files = [item for item in os.listdir('.') if os.path.isfile(item)]
        else:
            files = [f.strip() for f in files_input.split(',') if f.strip()]
    
    if not files:
        print("No files specified.")
        return None, None, None
    
    repo_name = None
    if args and args.repo:
        repo_name = args.repo
    else:
        repo_name = input("Enter the name of the target GitHub repository: ")
    
    repo_base_path = ""
    if args and args.path:
        repo_base_path = args.path
    else:
        repo_base_path = input("Enter base path in repository (optional, e.g., src/): ")
    
    default_msg = config["defaults"]["commit_message"]
    commit_message = ""
    if args and args.message:
        commit_message = args.message
    else:
        commit_message = input(f"Enter the commit message (default: {default_msg}): ")
        if not commit_message:
            commit_message = default_msg
    
    return files, repo_name, repo_base_path, commit_message

def upload_batch_files(github_username, github_token, config, args=None):
    """Upload multiple files in batch."""
    files, repo_name, repo_base_path, commit_message = get_batch_files_input(config, args)
    
    if not files:
        return
    
    print(f"\nUploading {len(files)} files to {repo_name}...")
    
    # Use progress bar if available
    file_iterator = tqdm(files, desc="Uploading files") if TQDM_AVAILABLE else files
    
    success_count = 0
    fail_count = 0
    
    for local_file in file_iterator:
        try:
            # Determine repository path
            if repo_base_path:
                repo_file_path = os.path.join(repo_base_path, os.path.basename(local_file)).replace("\\", "/")
            else:
                repo_file_path = os.path.basename(local_file)
            
            # Upload the file
            result = upload_single_batch_file(
                github_username, github_token, 
                repo_name, local_file, repo_file_path, 
                commit_message, config
            )
            
            if result:
                success_count += 1
            else:
                fail_count += 1
                if not config["batch"]["continue_on_error"]:
                    print("Stopping batch upload due to error.")
                    break
                    
        except Exception as e:
            print(f"Error uploading {local_file}: {e}")
            fail_count += 1
            if not config["batch"]["continue_on_error"]:
                break
    
    print(f"\nBatch upload complete: {success_count} succeeded, {fail_count} failed.")

def upload_single_batch_file(github_username, github_token, repo_name, 
                           local_file_path, repo_file_path, commit_message, config):
    """Upload a single file as part of a batch operation."""
    api_url = f"https://api.github.com/repos/{github_username}/{repo_name}/contents/{repo_file_path}"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    try:
        with open(local_file_path, "rb") as f:
            encoded_content = base64.b64encode(f.read()).decode('utf-8')
    except FileNotFoundError:
        print(f"Error: The local file '{local_file_path}' was not found.")
        return False
    except Exception as e:
        print(f"Error reading file {local_file_path}: {e}")
        return False

    sha = None
    try:
        response = requests.get(api_url, headers=headers, timeout=config["performance"]["timeout"])
        if response.status_code == 200:
            sha = response.json()['sha']
        elif response.status_code != 404:
            print(f"Error checking for file {repo_file_path}: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to GitHub for {repo_file_path}: {e}")
        return False

    data = {"message": commit_message, "content": encoded_content}
    if sha:
        data["sha"] = sha

    try:
        response = requests.put(api_url, headers=headers, json=data, timeout=config["performance"]["timeout"])
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error uploading {repo_file_path}: {e}")
        return False

# ==============================================================================
# SECTION 3: UPLOAD/UPDATE A PROJECT DIRECTORY
# ==============================================================================

def get_project_directory_input(config, args=None):
    """Gets user input for the project upload details."""
    if args and args.path:
        project_path = args.path
    else:
        project_path = input("Enter the full path to your project directory: ")
    
    if args and args.repo:
        repo_name = args.repo
    else:
        repo_name = input("Enter the desired name for your GitHub repository: ")
    
    if args and args.description is not None:
        repo_description = args.description
    else:
        default_desc = config["github"]["default_description"]
        repo_description = input(f"Enter a description for your repository (default: {default_desc}): ")
        if not repo_description:
            repo_description = default_desc
    
    if args and args.private is not None:
        is_private = args.private
    else:
        default_private = config["github"]["default_private"]
        is_private_input = input(f"Make the repository private? (y/n, default: {'y' if default_private else 'n'}): ").lower()
        if is_private_input in ['y', 'yes']:
            is_private = True
        elif is_private_input in ['n', 'no']:
            is_private = False
        else:
            is_private = default_private

    return project_path, repo_name, repo_description, is_private

def initialize_git_repository(project_path):
    """Initializes a git repository in the specified directory."""
    try:
        os.chdir(project_path)
        print(f"Changed directory to {project_path}")
        if not os.path.isdir(".git"):
            subprocess.run(["git", "init"], check=True)
            print("Initialized empty Git repository.")
        else:
            print("This is already a git repository.")
        subprocess.run(["git", "add", "."], check=True)
        print("Staged all files.")
        status_result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if status_result.stdout:
             subprocess.run(["git", "commit", "-m", "Initial commit"], check=True)
             print("Committed files.")
        else:
            print("No changes to commit. Working tree clean.")
    except FileNotFoundError:
        print(f"Error: The directory '{project_path}' does not exist.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while running a git command: {e}")
        sys.exit(1)

def create_or_get_github_repository(repo_name, repo_description, is_private, github_username, github_token):
    """Creates a new repository on GitHub or confirms an existing one."""
    api_url = f"https://api.github.com/repos/{github_username}/{repo_name}"
    headers = {"Authorization": f"token {github_token}", "Accept": "application/vnd.github.v3+json"}
    try:
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            print(f"Repository '{repo_name}' already exists on GitHub. Using existing repository.")
            return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error checking for existing repository: {e}")
        sys.exit(1)
    create_url = "https://api.github.com/user/repos"
    data = {"name": repo_name, "description": repo_description, "private": is_private}
    try:
        response = requests.post(create_url, headers=headers, json=data)
        response.raise_for_status()
        print(f"Successfully created repository '{repo_name}' on GitHub.")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to GitHub: {e}")
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"Error creating repository: {e.response.status_code} - {e.response.text}")
        sys.exit(1)

def push_to_github(repo_name, github_username, github_token):
    """Adds the remote and force pushes to the new repository."""
    remote_url = f"https://{github_username}:{github_token}@github.com/{github_username}/{repo_name}.git"
    safe_remote_url = f"https://github.com/{github_username}/{repo_name}.git"
    try:
        result = subprocess.run(["git", "remote"], capture_output=True, text=True)
        if "origin" in result.stdout.splitlines():
            existing_url_result = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True, check=True)
            if existing_url_result.stdout.strip() != remote_url and existing_url_result.stdout.strip() != safe_remote_url:
                subprocess.run(["git", "remote", "set-url", "origin", remote_url], check=True)
            else:
                subprocess.run(["git", "remote", "set-url", "origin", remote_url], check=True)
        else:
            subprocess.run(["git", "remote", "add", "origin", remote_url], check=True)
        branch_result = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, check=True)
        if branch_result.stdout.strip() != "main":
            subprocess.run(["git", "branch", "-M", "main"], check=True)
        print("Pushing to GitHub with force...")
        subprocess.run(["git", "push", "-u", "--force", "origin", "main"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while pushing to GitHub: {e}")
        sys.exit(1)

def upload_project_directory(github_username, github_token, config, args=None):
    """Handles the entire process of uploading/updating a project directory."""
    project_path, repo_name, repo_description, is_private = get_project_directory_input(config, args)
    initialize_git_repository(project_path)
    create_or_get_github_repository(repo_name, repo_description, is_private, github_username, github_token)
    push_to_github(repo_name, github_username, github_token)
    print(f"You can find your repository at: https://github.com/{github_username}/{repo_name}")

# ==============================================================================
# COMMAND LINE ARGUMENT PARSING
# ==============================================================================

def create_parser():
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        description="PyGitUp - Effortless GitHub Uploads",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pygitup.py --mode file --repo myrepo --file myfile.py
  python pygitup.py --mode project --path ./myproject --private
  python pygitup.py --mode batch --repo myrepo --files file1.py,file2.py
        """
    )
    
    parser.add_argument(
        "--mode", 
        choices=["project", "file", "batch"],
        help="Operation mode"
    )
    
    parser.add_argument(
        "--repo",
        help="Target GitHub repository name"
    )
    
    parser.add_argument(
        "--file",
        help="Local file to upload (for file mode)"
    )
    
    parser.add_argument(
        "--files",
        help="Comma-separated list of files to upload (for batch mode)"
    )
    
    parser.add_argument(
        "--path",
        help="Path in repository for file upload or base path for batch upload"
    )
    
    parser.add_argument(
        "--message",
        help="Commit message"
    )
    
    parser.add_argument(
        "--description",
        help="Repository description (for project mode)"
    )
    
    parser.add_argument(
        "--private",
        action="store_true",
        help="Make repository private (for project mode)"
    )
    
    parser.add_argument(
        "--public",
        action="store_true",
        help="Make repository public (for project mode)"
    )
    
    parser.add_argument(
        "--config",
        help="Path to configuration file"
    )
    
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Run in batch mode (used internally)"
    )
    
    return parser

# ==============================================================================
# MAIN FUNCTION
# ==============================================================================

def main():
    """Main function to orchestrate the process."""
    print("GitHub Uploader Tool")
    print("--------------------")

    # Parse command line arguments
    parser = create_parser()
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Get credentials
    github_username = get_github_username(config)
    github_token = get_github_token(config)
    
    # Determine mode
    mode = args.mode
    if not mode:
        print("\nWhat would you like to do?")
        print("1: Upload/update a whole project directory")
        print("2: Upload/update a single file")
        print("3: Batch upload multiple files")
        choice = input("Enter your choice (1, 2, or 3): ")
        
        if choice == '1':
            mode = "project"
        elif choice == '2':
            mode = "file"
        elif choice == '3':
            mode = "batch"
        else:
            print("Invalid choice. Exiting.")
            sys.exit(1)
    
    # Execute based on mode
    if mode == "project":
        upload_project_directory(github_username, github_token, config, args)
    elif mode == "file":
        upload_single_file(github_username, github_token, config, args)
    elif mode == "batch":
        upload_batch_files(github_username, github_token, config, args)
    else:
        print("Invalid mode. Exiting.")
        sys.exit(1)

    print("--------------------")
    print("Operation complete.")

if __name__ == "__main__":
    main()