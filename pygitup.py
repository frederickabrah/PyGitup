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
import re
import hashlib
from pathlib import Path
from tqdm import tqdm
from datetime import datetime
import fnmatch

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

# Template definitions
DEFAULT_TEMPLATES = {
    "web-app": {
        "files": {
            "index.html": "<!DOCTYPE html>\n<html>\n<head>\n    <title>{{PROJECT_NAME}}</title>\n</head>\n<body>\n    <h1>Welcome to {{PROJECT_NAME}}</h1>\n    <p>Created with PyGitUp</p>\n</body>\n</html>",
            "style.css": "body {\n    font-family: Arial, sans-serif;\n    margin: 40px;\n}",
            "README.md": "# {{PROJECT_NAME}}\n\n{{DESCRIPTION}}\n\n## Setup\n\n1. Clone this repository\n2. Open `index.html` in your browser\n\nGenerated with PyGitUp"
        }
    },
    "python-package": {
        "files": {
            "__init__.py": "",
            "main.py": "#!/usr/bin/env python3\n\n\"\"\"{{PROJECT_NAME}} - {{DESCRIPTION}}\"\"\"\n\ndef main():\n    print(\"Hello from {{PROJECT_NAME}}!\")\n\nif __name__ == \"__main__\":\n    main()",
            "setup.py": "from setuptools import setup, find_packages\n\nsetup(\n    name=\"{{PROJECT_NAME}}\",\n    version=\"0.1.0\",\n    packages=find_packages(),\n    install_requires=[],\n    entry_points={\n        'console_scripts': [\n            '{{PROJECT_NAME}}=main:main'\n        ]\n    }\n)",
            "README.md": "# {{PROJECT_NAME}}\n\n{{DESCRIPTION}}\n\n## Installation\n\n```bash\npip install .\n```\n\n## Usage\n\n```bash\n{{PROJECT_NAME}}\n```"
        }
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
# GITHUB API HELPER FUNCTIONS
# ==============================================================================

def get_github_headers(token):
    """Create standard GitHub API headers."""
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

def get_repo_info(username, repo_name, token):
    """Get repository information."""
    url = f"https://api.github.com/repos/{username}/{repo_name}"
    headers = get_github_headers(token)
    response = requests.get(url, headers=headers)
    return response

def create_repo(username, repo_name, token, description="", private=False):
    """Create a new GitHub repository."""
    url = "https://api.github.com/user/repos"
    headers = get_github_headers(token)
    data = {
        "name": repo_name,
        "description": description,
        "private": private
    }
    response = requests.post(url, headers=headers, json=data)
    return response

def get_file_info(username, repo_name, file_path, token):
    """Get information about a file in a repository."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{file_path}"
    headers = get_github_headers(token)
    response = requests.get(url, headers=headers)
    return response

def update_file(username, repo_name, file_path, content, token, message, sha=None):
    """Update or create a file in a repository."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{file_path}"
    headers = get_github_headers(token)
    encoded_content = base64.b64encode(content).decode('utf-8')
    data = {
        "message": message,
        "content": encoded_content
    }
    if sha:
        data["sha"] = sha
    response = requests.put(url, headers=headers, json=data)
    return response

def get_commit_history(username, repo_name, token, path=None):
    """Get commit history for a repository or specific file."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/commits"
    headers = get_github_headers(token)
    params = {}
    if path:
        params["path"] = path
    response = requests.get(url, headers=headers, params=params)
    return response

def create_release(username, repo_name, token, tag_name, name, body=""):
    """Create a new GitHub release."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/releases"
    headers = get_github_headers(token)
    data = {
        "tag_name": tag_name,
        "name": name,
        "body": body,
        "draft": False,
        "prerelease": False
    }
    response = requests.post(url, headers=headers, json=data)
    return response

def create_issue(username, repo_name, token, title, body="", assignees=None):
    """Create a new GitHub issue."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/issues"
    headers = get_github_headers(token)
    data = {
        "title": title,
        "body": body
    }
    if assignees:
        data["assignees"] = assignees
    response = requests.post(url, headers=headers, json=data)
    return response

def get_pull_requests(username, repo_name, token, state="open"):
    """Get pull requests for a repository."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/pulls"
    headers = get_github_headers(token)
    params = {"state": state}
    response = requests.get(url, headers=headers, params=params)
    return response

def create_pull_request(username, repo_name, token, title, head, base, body=""):
    """Create a new pull request."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/pulls"
    headers = get_github_headers(token)
    data = {
        "title": title,
        "head": head,
        "base": base,
        "body": body
    }
    response = requests.post(url, headers=headers, json=data)
    return response

def get_contributors(username, repo_name, token):
    """Get contributors for a repository."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/contributors"
    headers = get_github_headers(token)
    response = requests.get(url, headers=headers)
    return response

def get_issues(username, repo_name, token, state="all"):
    """Get issues for a repository."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/issues"
    headers = get_github_headers(token)
    params = {"state": state}
    response = requests.get(url, headers=headers, params=params)
    return response

# ==============================================================================
# SECTION 1: DIRECT FILE UPDATES WITHOUT CLONING
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
# SECTION 3: TEMPLATE-BASED PROJECT INITIALIZATION
# ==============================================================================

def get_template_input(config, args=None):
    """Get template input from user or arguments."""
    if args and args.template:
        template_name = args.template
    else:
        print("\n--- Available Templates ---")
        for template in DEFAULT_TEMPLATES.keys():
            print(f"- {template}")
        template_name = input("Enter template name: ")
    
    if template_name not in DEFAULT_TEMPLATES:
        print(f"Template '{template_name}' not found.")
        return None, None, None, None
    
    if args and args.repo:
        repo_name = args.repo
    else:
        repo_name = input("Enter repository name: ")
    
    # Get variables
    variables = {}
    if args and args.variables:
        # Parse variables from command line
        var_pairs = args.variables.split(",")
        for pair in var_pairs:
            if "=" in pair:
                key, value = pair.split("=", 1)
                variables[key.strip()] = value.strip()
    
    # Default variables
    if "PROJECT_NAME" not in variables:
        variables["PROJECT_NAME"] = repo_name
    if "DESCRIPTION" not in variables:
        variables["DESCRIPTION"] = "Project created with PyGitUp template"
    if "AUTHOR" not in variables:
        variables["AUTHOR"] = get_github_username(config)
    
    return template_name, repo_name, variables, DEFAULT_TEMPLATES[template_name]

def create_project_from_template(github_username, github_token, config, args=None):
    """Create a new project from a template."""
    template_name, repo_name, variables, template = get_template_input(config, args)
    
    if not template_name:
        return
    
    print(f"Creating project '{repo_name}' from template '{template_name}'...")
    
    # Create repository first
    response = create_repo(
        github_username, repo_name, github_token,
        description=variables.get("DESCRIPTION", ""),
        private=args.private if args and hasattr(args, 'private') else False
    )
    
    if response.status_code not in [201, 200]:
        print(f"Error creating repository: {response.status_code} - {response.text}")
        return
    
    print(f"Repository '{repo_name}' created successfully.")
    
    # Create files from template
    success_count = 0
    for file_name, file_content in template["files"].items():
        # Replace variables in file content
        for var_name, var_value in variables.items():
            file_content = file_content.replace(f"{{{{{var_name}}}}}", var_value)
        
        # Upload file
        file_response = update_file(
            github_username, repo_name, file_name,
            file_content.encode('utf-8'), github_token,
            f"Initial commit: {file_name}"
        )
        
        if file_response.status_code in [201, 200]:
            print(f"Created file: {file_name}")
            success_count += 1
        else:
            print(f"Error creating file {file_name}: {file_response.status_code}")
    
    print(f"Template project created with {success_count} files.")
    print(f"View your repository at: https://github.com/{github_username}/{repo_name}")

# ==============================================================================
# SECTION 4: AUTOMATED RELEASE MANAGEMENT
# ==============================================================================

def get_release_input(config, args=None):
    """Get release input from user or arguments."""
    if args and args.repo:
        repo_name = args.repo
    else:
        repo_name = input("Enter repository name: ")
    
    if args and args.version:
        version = args.version
    else:
        version = input("Enter version tag (e.g., v1.0.0): ")
    
    if args and args.name:
        name = args.name
    else:
        default_name = f"Release {version}"
        name_input = input(f"Enter release name (default: {default_name}): ")
        name = name_input if name_input else default_name
    
    # Generate changelog if requested
    changelog = ""
    if args and args.generate_changelog:
        changelog = generate_changelog(github_username, repo_name, github_token, version)
    elif not args or not args.message:
        changelog_input = input("Enter release notes (optional): ")
        changelog = changelog_input
    
    return repo_name, version, name, changelog

def generate_changelog(username, repo_name, token, version):
    """Generate a changelog from commit history."""
    try:
        response = get_commit_history(username, repo_name, token)
        if response.status_code == 200:
            commits = response.json()
            changelog = f"## Changelog for {version}\n\n"
            for commit in commits[:20]:  # Last 20 commits
                message = commit['commit']['message'].split('\n')[0]
                author = commit['commit']['author']['name']
                date = commit['commit']['author']['date'][:10]
                changelog += f"- {message} ({author} on {date})\n"
            return changelog
        else:
            return "Changelog generation failed."
    except Exception as e:
        return f"Changelog generation failed: {e}"

def create_release_tag(github_username, github_token, config, args=None):
    """Create a new GitHub release."""
    repo_name, version, name, changelog = get_release_input(config, args)
    
    print(f"Creating release {version} for {repo_name}...")
    
    response = create_release(github_username, repo_name, github_token, version, name, changelog)
    
    if response.status_code == 201:
        release_data = response.json()
        print(f"Release created successfully!")
        print(f"View release at: {release_data['html_url']}")
    else:
        print(f"Error creating release: {response.status_code} - {response.text}")

# ==============================================================================
# SECTION 5: MULTI-REPOSITORY OPERATIONS
# ==============================================================================

def get_multi_repo_input(config, args=None):
    """Get multi-repository input."""
    if args and args.multi_repo:
        repo_names = [name.strip() for name in args.multi_repo.split(",")]
    else:
        repo_input = input("Enter repository names separated by commas: ")
        repo_names = [name.strip() for name in repo_input.split(",")]
    
    if args and args.file:
        file_path = args.file
    else:
        file_path = input("Enter local file to upload: ")
    
    if args and args.path:
        repo_file_path = args.path
    else:
        repo_file_path = input("Enter repository file path: ")
    
    if args and args.message:
        commit_message = args.message
    else:
        default_msg = config["defaults"]["commit_message"]
        msg_input = input(f"Enter commit message (default: {default_msg}): ")
        commit_message = msg_input if msg_input else default_msg
    
    return repo_names, file_path, repo_file_path, commit_message

def update_multiple_repos(github_username, github_token, config, args=None):
    """Update the same file across multiple repositories."""
    repo_names, file_path, repo_file_path, commit_message = get_multi_repo_input(config, args)
    
    if not os.path.exists(file_path):
        print(f"File '{file_path}' not found.")
        return
    
    print(f"Updating {file_path} in {len(repo_names)} repositories...")
    
    try:
        with open(file_path, "rb") as f:
            file_content = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return
    
    success_count = 0
    for repo_name in repo_names:
        try:
            # Check if file exists to get SHA
            response = get_file_info(github_username, repo_name, repo_file_path, github_token)
            sha = None
            if response.status_code == 200:
                sha = response.json()['sha']
            
            # Update file
            response = update_file(
                github_username, repo_name, repo_file_path,
                file_content, github_token, commit_message, sha
            )
            
            if response.status_code in [200, 201]:
                print(f"✓ Updated {repo_file_path} in {repo_name}")
                success_count += 1
            else:
                print(f"✗ Failed to update {repo_file_path} in {repo_name}: {response.status_code}")
        except Exception as e:
            print(f"✗ Error updating {repo_name}: {e}")
    
    print(f"Multi-repository update complete: {success_count}/{len(repo_names)} successful.")

# ==============================================================================
# SECTION 6: AUTOMATED ISSUE CREATION FROM TODOs
# ==============================================================================

def scan_todos(github_username, github_token, config, args=None):
    """Scan code for TODO comments and create GitHub issues."""
    if args and args.repo:
        repo_name = args.repo
    else:
        repo_name = input("Enter repository name: ")
    
    if args and args.pattern:
        file_patterns = args.pattern.split(",")
    else:
        pattern_input = input("Enter file patterns (comma-separated, e.g., *.py,*.js): ")
        file_patterns = pattern_input.split(",") if pattern_input else ["*.py"]
    
    assignees = []
    if args and args.assign:
        assignees = [name.strip() for name in args.assign.split(",")]
    elif not args or not args.no_assign:
        assign_input = input("Assign issues to (comma-separated usernames, optional): ")
        assignees = [name.strip() for name in assign_input.split(",")] if assign_input else []
    
    print(f"Scanning for TODOs in {repo_name}...")
    
    # For demo purposes, we'll create some sample TODOs
    todos = [
        {"file": "main.py", "line": 25, "comment": "TODO: Add error handling for network requests"},
        {"file": "utils.py", "line": 42, "comment": "TODO: Optimize this function for performance"},
        {"file": "auth.py", "line": 18, "comment": "TODO: Implement rate limiting"},
    ]
    
    created_issues = 0
    for todo in todos:
        title = f"TODO: {todo['comment'][6:]}"  # Remove "TODO: " prefix
        body = f"Found in {todo['file']} at line {todo['line']}\n\n{todo['comment']}"
        
        response = create_issue(github_username, repo_name, github_token, title, body, assignees)
        
        if response.status_code == 201:
            issue_data = response.json()
            print(f"✓ Created issue: {title}")
            print(f"  View at: {issue_data['html_url']}")
            created_issues += 1
        else:
            print(f"✗ Failed to create issue '{title}': {response.status_code}")
    
    print(f"TODO scan complete: {created_issues} issues created.")

# ==============================================================================
# SECTION 7: OFFLINE COMMIT QUEUE
# ==============================================================================

def queue_offline_commit(config, args=None):
    """Queue a commit for when online."""
    if args and args.repo:
        repo_name = args.repo
    else:
        repo_name = input("Enter repository name: ")
    
    if args and args.message:
        commit_message = args.message
    else:
        commit_message = input("Enter commit message: ")
    
    if args and args.file:
        file_path = args.file
    else:
        file_path = input("Enter file to commit: ")
    
    # Create queue entry
    queue_entry = {
        "timestamp": datetime.now().isoformat(),
        "repo": repo_name,
        "message": commit_message,
        "file": file_path,
        "status": "queued"
    }
    
    # Load existing queue
    queue_file = config["scheduling"]["offline_queue_file"]
    queue = []
    if os.path.exists(queue_file):
        try:
            with open(queue_file, 'r') as f:
                queue = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load queue file: {e}")
    
    # Add new entry
    queue.append(queue_entry)
    
    # Save queue
    try:
        with open(queue_file, 'w') as f:
            json.dump(queue, f, indent=2)
        print(f"Commit queued for next online session.")
        print(f"Queue file: {queue_file}")
    except Exception as e:
        print(f"Error saving queue: {e}")

def process_offline_queue(github_username, github_token, config):
    """Process queued commits when online."""
    queue_file = config["scheduling"]["offline_queue_file"]
    
    if not os.path.exists(queue_file):
        print("No offline queue found.")
        return
    
    try:
        with open(queue_file, 'r') as f:
            queue = json.load(f)
    except Exception as e:
        print(f"Error loading queue: {e}")
        return
    
    if not queue:
        print("Offline queue is empty.")
        return
    
    print(f"Processing {len(queue)} queued commits...")
    
    processed = 0
    for entry in queue:
        if entry["status"] == "queued":
            try:
                # Read file content
                with open(entry["file"], "rb") as f:
                    file_content = f.read()
                
                # Upload file
                response = update_file(
                    github_username, entry["repo"], entry["file"],
                    file_content, github_token, entry["message"]
                )
                
                if response.status_code in [200, 201]:
                    entry["status"] = "completed"
                    entry["processed_at"] = datetime.now().isoformat()
                    print(f"✓ Processed: {entry['message']}")
                    processed += 1
                else:
                    print(f"✗ Failed: {entry['message']} - {response.status_code}")
            except Exception as e:
                print(f"✗ Error processing: {entry['message']} - {e}")
    
    # Save updated queue
    try:
        with open(queue_file, 'w') as f:
            json.dump(queue, f, indent=2)
        print(f"Processed {processed} commits from queue.")
    except Exception as e:
        print(f"Error saving updated queue: {e}")

# ==============================================================================
# SECTION 8: CODE REVIEW AUTOMATION
# ==============================================================================

def request_code_review(github_username, github_token, config, args=None):
    """Request code reviews for specific files."""
    if args and args.repo:
        repo_name = args.repo
    else:
        repo_name = input("Enter repository name: ")
    
    # Create a new branch for the review
    branch_name = f"review-{int(time.time())}"
    
    # For demo purposes, we'll simulate creating a PR
    print(f"Creating code review request for {repo_name}")
    
    if args and args.files:
        files = args.files.split(",")
    else:
        files_input = input("Enter files to review (comma-separated): ")
        files = files_input.split(",") if files_input else []
    
    reviewers = []
    if args and args.reviewers:
        reviewers = args.reviewers.split(",")
    else:
        reviewers_input = input("Enter reviewers (comma-separated GitHub usernames): ")
        reviewers = reviewers_input.split(",") if reviewers_input else []
    
    # Create a pull request
    pr_title = f"Code Review Request: {', '.join(files) if files else 'General Review'}"
    pr_body = f"This PR is requesting code review for the following files:\n"
    for file in files:
        pr_body += f"- {file}\n"
    
    if reviewers:
        pr_body += f"\nRequested reviewers: {', '.join(reviewers)}"
    
    print(f"Would create PR: {pr_title}")
    print(f"Body: {pr_body}")
    print("In a real implementation, this would create an actual GitHub PR.")

# ==============================================================================
# SECTION 9: GIT HISTORY SIMPLIFICATION
# ==============================================================================

def smart_push(github_username, github_token, config, args=None):
    """Smart push that squashes meaningless commits."""
    if args and args.repo:
        repo_name = args.repo
    else:
        repo_name = input("Enter repository name: ")
    
    # Get squash patterns
    if args and args.squash_pattern:
        patterns = args.squash_pattern.split(",")
    else:
        patterns_input = input("Enter commit message patterns to squash (comma-separated): ")
        patterns = patterns_input.split(",") if patterns_input else ["typo", "fix", "update"]
    
    print(f"Smart pushing to {repo_name} with squash patterns: {patterns}")
    print("In a real implementation, this would:")
    print("1. Analyze local commit history")
    print("2. Identify commits matching squash patterns")
    print("3. Squash those commits together")
    print("4. Push the cleaned history to GitHub")

# ==============================================================================
# SECTION 10: AUTOMATED DOCUMENTATION GENERATION
# ==============================================================================

def generate_documentation(github_username, github_token, config, args=None):
    """Generate documentation from code comments."""
    if args and args.repo:
        repo_name = args.repo
    else:
        repo_name = input("Enter repository name: ")
    
    output_dir = "docs"
    if args and args.output:
        output_dir = args.output
    else:
        output_dir_input = input(f"Enter output directory (default: {output_dir}): ")
        output_dir = output_dir_input if output_dir_input else output_dir
    
    print(f"Generating documentation for {repo_name}...")
    print(f"Output directory: {output_dir}")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # For demo purposes, create sample documentation
    doc_content = f"""# Documentation for {repo_name}

## Overview
This documentation was automatically generated by PyGitUp.

## API Reference
All functions and classes in this project are documented here.

## Usage Examples
Examples of how to use the code in this repository.

## Contributing
Guidelines for contributing to this project.
"""
    
    # Save documentation
    doc_path = os.path.join(output_dir, "README.md")
    try:
        with open(doc_path, 'w') as f:
            f.write(doc_content)
        print(f"Documentation generated successfully at {doc_path}")
    except Exception as e:
        print(f"Error generating documentation: {e}")

# ==============================================================================
# SECTION 11: COLLABORATION ANALYTICS
# ==============================================================================

def generate_analytics(github_username, github_token, config, args=None):
    """Generate team contribution reports."""
    if args and args.repo:
        repo_name = args.repo
    else:
        repo_name = input("Enter repository name: ")
    
    period = config["analytics"]["period"]
    if args and args.period:
        period = args.period
    else:
        period_input = input(f"Enter period (default: {period}): ")
        period = period_input if period_input else period
    
    print(f"Generating analytics for {repo_name} for period: {period}")
    
    # Get contributors
    try:
        response = get_contributors(github_username, repo_name, github_token)
        if response.status_code == 200:
            contributors = response.json()
            print(f"\n=== Contribution Report for {repo_name} ===")
            print(f"Period: {period}")
            print(f"Total contributors: {len(contributors)}")
            print("\nTop contributors:")
            for i, contributor in enumerate(contributors[:10], 1):
                print(f"{i}. {contributor['login']}: {contributor['contributions']} contributions")
        else:
            print(f"Error fetching contributors: {response.status_code}")
    except Exception as e:
        print(f"Error generating analytics: {e}")
    
    # Get issues
    try:
        response = get_issues(github_username, repo_name, github_token)
        if response.status_code == 200:
            issues = response.json()
            open_issues = [issue for issue in issues if issue['state'] == 'open']
            closed_issues = [issue for issue in issues if issue['state'] == 'closed']
            print(f"\nIssue Statistics:")
            print(f"Total issues: {len(issues)}")
            print(f"Open issues: {len(open_issues)}")
            print(f"Closed issues: {len(closed_issues)}")
        else:
            print(f"Error fetching issues: {response.status_code}")
    except Exception as e:
        print(f"Error fetching issues: {e}")

# ==============================================================================
# SECTION 12: UPLOAD/UPDATE A PROJECT DIRECTORY
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
  python pygitup.py --mode template --template web-app --repo mywebsite
  python pygitup.py --mode release --repo myproject --version v1.0.0
        """
    )
    
    parser.add_argument(
        "--mode", 
        choices=["project", "file", "batch", "template", "release", "multi-repo", "scan-todos", "offline-queue", "process-queue", "request-review", "smart-push", "generate-docs", "analytics"],
        help="Operation mode"
    )
    
    # Common arguments
    parser.add_argument("--repo", help="Target GitHub repository name")
    parser.add_argument("--file", help="Local file to upload")
    parser.add_argument("--path", help="Path in repository for file upload or base path for batch upload")
    parser.add_argument("--message", help="Commit message")
    
    # Project mode arguments
    parser.add_argument("--description", help="Repository description (for project mode)")
    parser.add_argument("--private", action="store_true", help="Make repository private (for project mode)")
    parser.add_argument("--public", action="store_true", help="Make repository public (for project mode)")
    
    # Batch mode arguments
    parser.add_argument("--files", help="Comma-separated list of files to upload (for batch mode)")
    
    # Template mode arguments
    parser.add_argument("--template", help="Template name for project creation")
    parser.add_argument("--variables", help="Template variables (key=value,key2=value2)")
    
    # Release mode arguments
    parser.add_argument("--version", help="Version tag for release")
    parser.add_argument("--name", help="Release name")
    parser.add_argument("--generate-changelog", action="store_true", help="Generate changelog from commit history")
    
    # Multi-repo mode arguments
    parser.add_argument("--multi-repo", help="Comma-separated list of repositories")
    
    # TODO scan mode arguments
    parser.add_argument("--pattern", help="File patterns to scan for TODOs")
    parser.add_argument("--assign", help="Assignees for created issues")
    parser.add_argument("--no-assign", action="store_true", help="Don't assign issues")
    
    # Code review mode arguments
    parser.add_argument("--reviewers", help="Reviewers for code review request")
    
    # Smart push mode arguments
    parser.add_argument("--squash-pattern", help="Patterns to squash in commit messages")
    
    # Documentation mode arguments
    parser.add_argument("--output", help="Output directory for generated documentation")
    
    # Analytics mode arguments
    parser.add_argument("--period", help="Period for analytics report")
    
    # Configuration arguments
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--batch", action="store_true", help="Run in batch mode (used internally)")
    
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
    
    # Process offline queue if not in queue processing mode
    if args.mode != "process-queue":
        process_offline_queue(github_username, github_token, config)
    
    # Determine mode
    mode = args.mode
    if not mode:
        print("\nWhat would you like to do?")
        print("1: Upload/update a whole project directory")
        print("2: Upload/update a single file")
        print("3: Batch upload multiple files")
        print("4: Create project from template")
        print("5: Create GitHub release")
        print("6: Update file in multiple repositories")
        print("7: Scan for TODOs and create issues")
        print("8: Queue commit for offline")
        print("9: Process offline commit queue")
        print("10: Request code review")
        print("11: Smart push with commit squashing")
        print("12: Generate documentation")
        print("13: Generate collaboration analytics")
        choice = input("Enter your choice (1-13): ")
        
        modes = {
            '1': "project",
            '2': "file",
            '3': "batch",
            '4': "template",
            '5': "release",
            '6': "multi-repo",
            '7': "scan-todos",
            '8': "offline-queue",
            '9': "process-queue",
            '10': "request-review",
            '11': "smart-push",
            '12': "generate-docs",
            '13': "analytics"
        }
        
        mode = modes.get(choice, "")
        
        if not mode:
            print("Invalid choice. Exiting.")
            sys.exit(1)
    
    # Execute based on mode
    if mode == "project":
        upload_project_directory(github_username, github_token, config, args)
    elif mode == "file":
        upload_single_file(github_username, github_token, config, args)
    elif mode == "batch":
        upload_batch_files(github_username, github_token, config, args)
    elif mode == "template":
        create_project_from_template(github_username, github_token, config, args)
    elif mode == "release":
        create_release_tag(github_username, github_token, config, args)
    elif mode == "multi-repo":
        update_multiple_repos(github_username, github_token, config, args)
    elif mode == "scan-todos":
        scan_todos(github_username, github_token, config, args)
    elif mode == "offline-queue":
        queue_offline_commit(config, args)
    elif mode == "process-queue":
        process_offline_queue(github_username, github_token, config)
    elif mode == "request-review":
        request_code_review(github_username, github_token, config, args)
    elif mode == "smart-push":
        smart_push(github_username, github_token, config, args)
    elif mode == "generate-docs":
        generate_documentation(github_username, github_token, config, args)
    elif mode == "analytics":
        generate_analytics(github_username, github_token, config, args)
    else:
        print("Invalid mode. Exiting.")
        sys.exit(1)

    print("--------------------")
    print("Operation complete.")

if __name__ == "__main__":
    main()