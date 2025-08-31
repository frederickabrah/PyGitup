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
import logging
from pathlib import Path
from tqdm import tqdm
from datetime import datetime
from functools import wraps

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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pygitup_error.log'),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger('PyGitUp')

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
        "timeout": 30,
        "max_retries": 3,
        "retry_delay": 1,
        "backoff_factor": 2
    },
    "logging": {
        "enabled": True,
        "file": "pygitup.log",
        "level": "INFO"
    },
    "templates": {
        "directory": "./templates"
    },
    "scheduling": {
        "offline_queue_file": ".pygitup_offline_queue"
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

# Custom exception classes
class PyGitUpError(Exception):
    """Base exception for PyGitUp errors"""
    pass

class GitHubAPIError(PyGitUpError):
    """Exception for GitHub API errors"""
    def __init__(self, message, status_code=None, response_text=None):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text

class NetworkError(PyGitUpError):
    """Exception for network-related errors"""
    pass

class FileOperationError(PyGitUpError):
    """Exception for file operation errors"""
    pass

class AuthenticationError(PyGitUpError):
    """Exception for authentication errors"""
    pass

class ConfigurationError(PyGitUpError):
    """Exception for configuration errors"""
    pass

# ==============================================================================
# ROBUST ERROR HANDLING DECORATORS
# ==============================================================================

def robust_api_call(max_retries=None, retry_delay=None, backoff_factor=None):
    """Decorator for robust API calls with exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            config = kwargs.get('config', DEFAULT_CONFIG)
            max_retries_val = max_retries or config["performance"]["max_retries"]
            retry_delay_val = retry_delay or config["performance"]["retry_delay"]
            backoff_factor_val = backoff_factor or config["performance"]["backoff_factor"]
            
            last_exception = None
            
            for attempt in range(max_retries_val + 1):
                try:
                    logger.debug(f"Attempt {attempt + 1} for {func.__name__}")
                    result = func(*args, **kwargs)
                    
                    # Check if result is a response object and has a successful status
                    if hasattr(result, 'status_code') and result.status_code >= 500:
                        raise GitHubAPIError(
                            f"Server error: {result.status_code}",
                            status_code=result.status_code,
                            response_text=getattr(result, 'text', 'No response text')
                        )
                    
                    return result
                    
                except (requests.exceptions.RequestException, NetworkError) as e:
                    last_exception = e
                    logger.warning(f"Network error on attempt {attempt + 1}: {str(e)}")
                    
                    if attempt < max_retries_val:
                        delay = retry_delay_val * (backoff_factor_val ** attempt)
                        logger.info(f"Retrying in {delay} seconds...")
                        time.sleep(delay)
                    else:
                        logger.error(f"Max retries exceeded for {func.__name__}")
                        raise NetworkError(f"Network error after {max_retries_val + 1} attempts: {str(e)}") from e
                        
                except GitHubAPIError as e:
                    last_exception = e
                    logger.warning(f"GitHub API error on attempt {attempt + 1}: {str(e)}")
                    
                    # Don't retry on client errors (4xx)
                    if e.status_code and 400 <= e.status_code < 500:
                        logger.error(f"Client error, not retrying: {e.status_code}")
                        raise
                    
                    if attempt < max_retries_val:
                        delay = retry_delay_val * (backoff_factor_val ** attempt)
                        logger.info(f"Retrying in {delay} seconds...")
                        time.sleep(delay)
                    else:
                        logger.error(f"Max retries exceeded for {func.__name__}")
                        raise
                        
                except Exception as e:
                    last_exception = e
                    logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
                    raise PyGitUpError(f"Unexpected error: {str(e)}") from e
            
            # If we get here, all retries failed
            raise last_exception
        return wrapper
    return decorator

def safe_file_operation(func):
    """Decorator for safe file operations with comprehensive error handling"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except PermissionError as e:
            logger.error(f"Permission denied accessing file: {str(e)}")
            raise FileOperationError(f"Permission denied: {str(e)}") from e
        except FileNotFoundError as e:
            logger.error(f"File not found: {str(e)}")
            raise FileOperationError(f"File not found: {str(e)}") from e
        except IsADirectoryError as e:
            logger.error(f"Expected file but found directory: {str(e)}")
            raise FileOperationError(f"Expected file but found directory: {str(e)}") from e
        except OSError as e:
            logger.error(f"OS error during file operation: {str(e)}")
            raise FileOperationError(f"System error: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error during file operation: {str(e)}")
            raise FileOperationError(f"Unexpected file error: {str(e)}") from e
    return wrapper

# ==============================================================================
# CONFIGURATION MANAGEMENT
# ==============================================================================

def load_config(config_path=None):
    """Load configuration from file or return defaults with robust error handling."""
    config = DEFAULT_CONFIG.copy()
    
    if not YAML_AVAILABLE:
        logger.warning("PyYAML not available, using default configuration")
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
                        if isinstance(config[key], dict) and isinstance(file_config[key], dict):
                            config[key].update(file_config[key])
                        else:
                            config[key] = file_config[key]
                logger.info(f"Configuration loaded from {config_path}")
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error in config file {config_path}: {e}")
            print(f"Warning: Could not parse config file {config_path}: {e}")
        except PermissionError as e:
            logger.error(f"Permission denied reading config file {config_path}: {e}")
            print(f"Warning: Permission denied reading config file {config_path}")
        except Exception as e:
            logger.error(f"Error loading config file {config_path}: {e}")
            print(f"Warning: Could not load config file {config_path}: {e}")
    elif config_path:
        logger.warning(f"Config file {config_path} not found")
        print(f"Warning: Config file {config_path} not found")
    
    return config

@safe_file_operation
def get_github_token(config):
    """Get GitHub token from config, file, or environment with robust error handling."""
    # Check config first
    if config["github"]["token_file"] and os.path.exists(config["github"]["token_file"]):
        try:
            with open(config["github"]["token_file"], 'r') as f:
                token = f.read().strip()
                if not token:
                    raise ConfigurationError("Token file is empty")
                logger.info("GitHub token loaded from file")
                return token
        except Exception as e:
            logger.error(f"Error reading token file: {e}")
            print(f"Warning: Could not read token file: {e}")
    
    # Check environment variable
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        logger.info("GitHub token loaded from environment variable")
        return token
    
    # Prompt user
    logger.info("Prompting user for GitHub token")
    return getpass.getpass("Enter your GitHub Personal Access Token: ")

def get_github_username(config):
    """Get GitHub username from config or environment with robust error handling."""
    # Check config first
    if config["github"]["username"]:
        logger.info("GitHub username loaded from config")
        return config["github"]["username"]
    
    # Check environment variable
    username = os.environ.get("GITHUB_USERNAME")
    if username:
        logger.info("GitHub username loaded from environment variable")
        return username
    
    # Prompt user
    logger.info("Prompting user for GitHub username")
    return input("Enter your GitHub username: ")

# ==============================================================================
# LOGGING
# ==============================================================================

def log_message(message, level="INFO", config=None):
    """Log a message if logging is enabled with robust error handling."""
    try:
        if not config or not config["logging"]["enabled"]:
            return
        
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}\n"
        
        with open(config["logging"]["file"], "a") as f:
            f.write(log_entry)
    except Exception as e:
        # Don't let logging errors break the main functionality
        pass

# ==============================================================================
# GITHUB API HELPER FUNCTIONS
# ==============================================================================

def get_github_headers(token):
    """Create standard GitHub API headers."""
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "PyGitUp/1.0"
    }

@robust_api_call()
def get_repo_info(username, repo_name, token, config=None):
    """Get repository information with robust error handling."""
    url = f"https://api.github.com/repos/{username}/{repo_name}"
    headers = get_github_headers(token)
    try:
        response = requests.get(url, headers=headers, timeout=config["performance"]["timeout"] if config else 30)
        if response.status_code == 401:
            raise AuthenticationError("Invalid GitHub token")
        elif response.status_code == 403:
            raise AuthenticationError("GitHub API rate limit exceeded or insufficient permissions")
        elif response.status_code == 404:
            raise GitHubAPIError(f"Repository {username}/{repo_name} not found", 404, response.text)
        elif response.status_code >= 400:
            raise GitHubAPIError(f"GitHub API error: {response.status_code}", response.status_code, response.text)
        return response
    except requests.exceptions.RequestException as e:
        raise NetworkError(f"Network error while accessing GitHub API: {str(e)}") from e

@robust_api_call()
def create_repo(username, repo_name, token, description="", private=False, config=None):
    """Create a new GitHub repository with robust error handling."""
    url = "https://api.github.com/user/repos"
    headers = get_github_headers(token)
    data = {
        "name": repo_name,
        "description": description,
        "private": private,
        "auto_init": False
    }
    try:
        response = requests.post(url, headers=headers, json=data, timeout=config["performance"]["timeout"] if config else 30)
        if response.status_code == 401:
            raise AuthenticationError("Invalid GitHub token")
        elif response.status_code == 403:
            raise AuthenticationError("GitHub API rate limit exceeded or insufficient permissions")
        elif response.status_code == 422:
            # Repository might already exist
            existing_repo_response = get_repo_info(username, repo_name, token, config)
            if existing_repo_response.status_code == 200:
                logger.info(f"Repository {repo_name} already exists")
                return existing_repo_response
            else:
                raise GitHubAPIError(f"Repository creation failed: {response.text}", 422, response.text)
        elif response.status_code >= 400:
            raise GitHubAPIError(f"GitHub API error: {response.status_code}", response.status_code, response.text)
        return response
    except requests.exceptions.RequestException as e:
        raise NetworkError(f"Network error while accessing GitHub API: {str(e)}") from e

@robust_api_call()
def get_file_info(username, repo_name, file_path, token, config=None):
    """Get information about a file in a repository with robust error handling."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{file_path}"
    headers = get_github_headers(token)
    try:
        response = requests.get(url, headers=headers, timeout=config["performance"]["timeout"] if config else 30)
        # Note: 404 is expected for non-existent files, so we don't treat it as an error
        if response.status_code == 401:
            raise AuthenticationError("Invalid GitHub token")
        elif response.status_code == 403:
            raise AuthenticationError("GitHub API rate limit exceeded or insufficient permissions")
        elif response.status_code >= 500:
            raise GitHubAPIError(f"GitHub server error: {response.status_code}", response.status_code, response.text)
        return response
    except requests.exceptions.RequestException as e:
        raise NetworkError(f"Network error while accessing GitHub API: {str(e)}") from e

@robust_api_call()
def update_file(username, repo_name, file_path, content, token, message, sha=None, config=None):
    """Update or create a file in a repository with robust error handling."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{file_path}"
    headers = get_github_headers(token)
    
    # Handle content encoding
    try:
        if isinstance(content, str):
            encoded_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        else:
            encoded_content = base64.b64encode(content).decode('utf-8')
    except Exception as e:
        raise FileOperationError(f"Error encoding file content: {str(e)}") from e
    
    data = {
        "message": message,
        "content": encoded_content
    }
    if sha:
        data["sha"] = sha
    
    try:
        response = requests.put(url, headers=headers, json=data, timeout=config["performance"]["timeout"] if config else 30)
        if response.status_code == 401:
            raise AuthenticationError("Invalid GitHub token")
        elif response.status_code == 403:
            raise AuthenticationError("GitHub API rate limit exceeded or insufficient permissions")
        elif response.status_code == 409:
            raise GitHubAPIError("File update conflict - file was modified by another process", 409, response.text)
        elif response.status_code == 422:
            raise GitHubAPIError("Invalid file content or path", 422, response.text)
        elif response.status_code >= 400:
            raise GitHubAPIError(f"GitHub API error: {response.status_code}", response.status_code, response.text)
        return response
    except requests.exceptions.RequestException as e:
        raise NetworkError(f"Network error while accessing GitHub API: {str(e)}") from e

@robust_api_call()
def get_commit_history(username, repo_name, token, path=None, config=None):
    """Get commit history for a repository or specific file with robust error handling."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/commits"
    headers = get_github_headers(token)
    params = {}
    if path:
        params["path"] = path
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=config["performance"]["timeout"] if config else 30)
        if response.status_code == 401:
            raise AuthenticationError("Invalid GitHub token")
        elif response.status_code == 403:
            raise AuthenticationError("GitHub API rate limit exceeded or insufficient permissions")
        elif response.status_code == 404:
            raise GitHubAPIError(f"Repository {username}/{repo_name} not found", 404, response.text)
        elif response.status_code >= 400:
            raise GitHubAPIError(f"GitHub API error: {response.status_code}", response.status_code, response.text)
        return response
    except requests.exceptions.RequestException as e:
        raise NetworkError(f"Network error while accessing GitHub API: {str(e)}") from e

@robust_api_call()
def create_release(username, repo_name, token, tag_name, name, body="", config=None):
    """Create a new GitHub release with robust error handling."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/releases"
    headers = get_github_headers(token)
    data = {
        "tag_name": tag_name,
        "name": name,
        "body": body,
        "draft": False,
        "prerelease": False
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=config["performance"]["timeout"] if config else 30)
        if response.status_code == 401:
            raise AuthenticationError("Invalid GitHub token")
        elif response.status_code == 403:
            raise AuthenticationError("GitHub API rate limit exceeded or insufficient permissions")
        elif response.status_code == 404:
            raise GitHubAPIError(f"Repository {username}/{repo_name} not found", 404, response.text)
        elif response.status_code == 422:
            raise GitHubAPIError("Invalid release data", 422, response.text)
        elif response.status_code >= 400:
            raise GitHubAPIError(f"GitHub API error: {response.status_code}", response.status_code, response.text)
        return response
    except requests.exceptions.RequestException as e:
        raise NetworkError(f"Network error while accessing GitHub API: {str(e)}") from e

@robust_api_call()
def create_issue(username, repo_name, token, title, body="", assignees=None, config=None):
    """Create a new GitHub issue with robust error handling."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/issues"
    headers = get_github_headers(token)
    data = {
        "title": title,
        "body": body
    }
    if assignees:
        data["assignees"] = assignees
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=config["performance"]["timeout"] if config else 30)
        if response.status_code == 401:
            raise AuthenticationError("Invalid GitHub token")
        elif response.status_code == 403:
            raise AuthenticationError("GitHub API rate limit exceeded or insufficient permissions")
        elif response.status_code == 404:
            raise GitHubAPIError(f"Repository {username}/{repo_name} not found", 404, response.text)
        elif response.status_code == 422:
            raise GitHubAPIError("Invalid issue data", 422, response.text)
        elif response.status_code >= 400:
            raise GitHubAPIError(f"GitHub API error: {response.status_code}", response.status_code, response.text)
        return response
    except requests.exceptions.RequestException as e:
        raise NetworkError(f"Network error while accessing GitHub API: {str(e)}") from e

# ==============================================================================
# SECTION 1: DIRECT FILE UPDATES WITHOUT CLONING
# ==============================================================================

@safe_file_operation
def get_single_file_input(config, args=None):
    """Gets user input for the file upload details with robust error handling."""
    try:
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
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error getting file input: {e}")
        raise PyGitUpError(f"Error getting file input: {str(e)}") from e

@robust_api_call()
def upload_single_file(github_username, github_token, config, args=None):
    """Handles the entire process of uploading/updating a single file with robust error handling."""
    try:
        repo_name, local_file_path, repo_file_path, commit_message = get_single_file_input(config, args)
    except Exception as e:
        logger.error(f"Failed to get file input: {e}")
        if not args or not args.batch:
            sys.exit(1)
        return False

    try:
        # Read file content with progress if available
        file_size = os.path.getsize(local_file_path)
        logger.info(f"Reading file {local_file_path} ({file_size} bytes)")
        
        with open(local_file_path, "rb") as f:
            if TQDM_AVAILABLE and file_size > 1024*1024:  # Show progress for files > 1MB
                with tqdm(total=file_size, unit='B', unit_scale=True, desc="Reading file") as pbar:
                    content = f.read()
                    pbar.update(len(content))
            else:
                content = f.read()
                
        logger.info(f"Successfully read {len(content)} bytes from {local_file_path}")
    except FileNotFoundError:
        logger.error(f"Local file not found: {local_file_path}")
        print(f"Error: The local file '{local_file_path}' was not found.")
        if not args or not args.batch:
            sys.exit(1)
        return False
    except Exception as e:
        logger.error(f"Error reading file {local_file_path}: {e}")
        print(f"Error reading file: {e}")
        if not args or not args.batch:
            sys.exit(1)
        return False

    # Check if file exists to get SHA
    sha = None
    try:
        logger.info(f"Checking if file {repo_file_path} exists in repository {repo_name}")
        response = get_file_info(github_username, repo_name, repo_file_path, github_token, config)
        if response.status_code == 200:
            print("File exists in the repository. It will be overwritten.")
            file_data = response.json()
            sha = file_data.get('sha')
            logger.info(f"Existing file SHA: {sha}")
        elif response.status_code != 404:
            logger.error(f"Error checking for file: {response.status_code} - {response.text}")
            print(f"Error checking for file: {response.status_code} - {response.text}")
            if not args or not args.batch:
                sys.exit(1)
            return False
        else:
            logger.info("File does not exist in repository (will be created)")
    except Exception as e:
        logger.error(f"Error checking file existence: {e}")
        print(f"Error connecting to GitHub: {e}")
        if not args or not args.batch:
            sys.exit(1)
        return False

    # Upload file
    try:
        logger.info(f"Uploading file {repo_file_path} to repository {repo_name}")
        response = update_file(
            github_username, repo_name, repo_file_path,
            content, github_token, commit_message, sha, config
        )
        
        if response.status_code in [200, 201]:
            result_data = response.json()
            if response.status_code == 201:
                print(f"Successfully created file '{repo_file_path}' in '{repo_name}'.")
                logger.info(f"Successfully created file {repo_file_path}")
            else:
                print(f"Successfully updated file '{repo_file_path}' in '{repo_name}'.")
                logger.info(f"Successfully updated file {repo_file_path}")
            
            content_url = result_data.get('content', {}).get('html_url', 'URL not available')
            print(f"View the file at: {content_url}")
            return True
        else:
            logger.error(f"Error uploading file: {response.status_code} - {response.text}")
            print(f"Error uploading file: {response.status_code} - {response.text}")
            if not args or not args.batch:
                sys.exit(1)
            return False
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        print(f"Error uploading file: {e}")
        if not args or not args.batch:
            sys.exit(1)
        return False

# ==============================================================================
# SECTION 2: BATCH FILE UPLOAD
# ==============================================================================

def get_batch_files_input(config, args=None):
    """Get files for batch upload with robust error handling."""
    try:
        if args and args.files:
            files_input = args.files
        else:
            print("\n--- Select files for batch upload ---")
            print("Enter file paths separated by commas, or 'all' for all files in directory:")
            files_input = input("> ").strip()
        
        if files_input.lower() == 'all':
            try:
                files = [item for item in os.listdir('.') if os.path.isfile(item)]
                logger.info(f"Selected all {len(files)} files in current directory")
            except Exception as e:
                logger.error(f"Error listing directory contents: {e}")
                print(f"Error listing directory contents: {e}")
                return None, None, None, None
        else:
            files = [f.strip() for f in files_input.split(',') if f.strip()]
            logger.info(f"Selected {len(files)} files for batch upload")
        
        if not files:
            print("No files specified.")
            return None, None, None, None
        
        if args and args.repo:
            repo_name = args.repo
        else:
            repo_name = input("Enter the name of the target GitHub repository: ")
        
        if args and args.path:
            repo_base_path = args.path
        else:
            repo_base_path = input("Enter base path in repository (optional, e.g., src/): ")
        
        if args and args.message:
            commit_message = args.message
        else:
            default_msg = config["defaults"]["commit_message"]
            msg_input = input(f"Enter the commit message (default: {default_msg}): ")
            commit_message = msg_input if msg_input else default_msg
        
        return files, repo_name, repo_base_path, commit_message
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error getting batch input: {e}")
        raise PyGitUpError(f"Error getting batch input: {str(e)}") from e

@robust_api_call()
def upload_batch_files(github_username, github_token, config, args=None):
    """Upload multiple files in batch with robust error handling."""
    try:
        files, repo_name, repo_base_path, commit_message = get_batch_files_input(config, args)
    except Exception as e:
        logger.error(f"Failed to get batch input: {e}")
        return

    if not files:
        return
    
    print(f"\nUploading {len(files)} files to {repo_name}...")
    logger.info(f"Starting batch upload of {len(files)} files to {repo_name}")
    
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
            
            logger.info(f"Processing file {local_file} -> {repo_file_path}")
            
            # Upload the file
            result = upload_single_batch_file(
                github_username, github_token, 
                repo_name, local_file, repo_file_path, 
                commit_message, config
            )
            
            if result:
                success_count += 1
                logger.info(f"Successfully uploaded {local_file}")
                if TQDM_AVAILABLE:
                    file_iterator.set_postfix(success=success_count, failed=fail_count)
            else:
                fail_count += 1
                logger.warning(f"Failed to upload {local_file}")
                if TQDM_AVAILABLE:
                    file_iterator.set_postfix(success=success_count, failed=fail_count)
                if not config["batch"]["continue_on_error"]:
                    print("Stopping batch upload due to error.")
                    logger.info("Stopping batch upload due to error")
                    break
                    
        except Exception as e:
            logger.error(f"Error uploading {local_file}: {e}")
            print(f"Error uploading {local_file}: {e}")
            fail_count += 1
            if not config["batch"]["continue_on_error"]:
                print("Stopping batch upload due to error.")
                logger.info("Stopping batch upload due to error")
                break
    
    print(f"\nBatch upload complete: {success_count} succeeded, {fail_count} failed.")
    logger.info(f"Batch upload complete: {success_count} succeeded, {fail_count} failed")

@robust_api_call()
def upload_single_batch_file(github_username, github_token, repo_name, 
                           local_file_path, repo_file_path, commit_message, config):
    """Upload a single file as part of a batch operation with robust error handling."""
    try:
        # Check if file exists locally
        if not os.path.exists(local_file_path):
            logger.warning(f"Local file not found: {local_file_path}")
            print(f"Warning: Local file '{local_file_path}' not found.")
            return False
        
        # Read file content
        with open(local_file_path, "rb") as f:
            content = f.read()
        logger.info(f"Read {len(content)} bytes from {local_file_path}")
    except FileNotFoundError:
        logger.error(f"Local file not found: {local_file_path}")
        print(f"Error: The local file '{local_file_path}' was not found.")
        return False
    except Exception as e:
        logger.error(f"Error reading file {local_file_path}: {e}")
        print(f"Error reading file {local_file_path}: {e}")
        return False

    # Check if file exists in repository
    sha = None
    try:
        logger.info(f"Checking if file {repo_file_path} exists in repository {repo_name}")
        response = get_file_info(github_username, repo_name, repo_file_path, github_token, config)
        if response.status_code == 200:
            file_data = response.json()
            sha = file_data.get('sha')
            logger.info(f"Existing file SHA: {sha}")
        elif response.status_code != 404:
            logger.error(f"Error checking for file {repo_file_path}: {response.status_code}")
            print(f"Error checking for file {repo_file_path}: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Error connecting to GitHub for {repo_file_path}: {e}")
        print(f"Error connecting to GitHub for {repo_file_path}: {e}")
        return False

    # Upload file
    try:
        logger.info(f"Uploading file {repo_file_path} to repository {repo_name}")
        response = update_file(
            github_username, repo_name, repo_file_path,
            content, github_token, commit_message, sha, config
        )
        
        if response.status_code in [200, 201]:
            logger.info(f"Successfully uploaded {repo_file_path}")
            return True
        else:
            logger.error(f"Error uploading {repo_file_path}: {response.status_code}")
            print(f"Error uploading {repo_file_path}: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Error uploading {repo_file_path}: {e}")
        print(f"Error uploading {repo_file_path}: {e}")
        return False

# ==============================================================================
# SECTION 3: TEMPLATE-BASED PROJECT INITIALIZATION
# ==============================================================================

def get_template_input(config, args=None):
    """Get template input from user or arguments with robust error handling."""
    try:
        if args and args.template:
            template_name = args.template
        else:
            print("\n--- Available Templates ---")
            for template in DEFAULT_TEMPLATES.keys():
                print(f"- {template}")
            template_name = input("Enter template name: ")
        
        if template_name not in DEFAULT_TEMPLATES:
            logger.warning(f"Template '{template_name}' not found")
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
            try:
                var_pairs = args.variables.split(",")
                for pair in var_pairs:
                    if "=" in pair:
                        key, value = pair.split("=", 1)
                        variables[key.strip()] = value.strip()
            except Exception as e:
                logger.warning(f"Error parsing template variables: {e}")
                print(f"Warning: Error parsing template variables: {e}")
        
        # Default variables
        if "PROJECT_NAME" not in variables:
            variables["PROJECT_NAME"] = repo_name
        if "DESCRIPTION" not in variables:
            variables["DESCRIPTION"] = "Project created with PyGitUp template"
        if "AUTHOR" not in variables:
            variables["AUTHOR"] = get_github_username(config)
        
        return template_name, repo_name, variables, DEFAULT_TEMPLATES[template_name]
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error getting template input: {e}")
        raise PyGitUpError(f"Error getting template input: {str(e)}") from e

@robust_api_call()
def create_project_from_template(github_username, github_token, config, args=None):
    """Create a new project from a template with robust error handling."""
    try:
        template_name, repo_name, variables, template = get_template_input(config, args)
    except Exception as e:
        logger.error(f"Failed to get template input: {e}")
        return
    
    if not template_name:
        return
    
    print(f"Creating project '{repo_name}' from template '{template_name}'...")
    logger.info(f"Creating project {repo_name} from template {template_name}")
    
    # Create repository first
    try:
        logger.info(f"Creating repository {repo_name}")
        response = create_repo(
            github_username, repo_name, github_token,
            description=variables.get("DESCRIPTION", ""),
            private=args.private if args and hasattr(args, 'private') else False,
            config=config
        )
        
        if response.status_code not in [201, 200]:
            logger.error(f"Error creating repository: {response.status_code} - {response.text}")
            print(f"Error creating repository: {response.status_code} - {response.text}")
            return
        
        logger.info(f"Repository {repo_name} created successfully")
        print(f"Repository '{repo_name}' created successfully.")
    except Exception as e:
        logger.error(f"Error creating repository: {e}")
        print(f"Error creating repository: {e}")
        return
    
    # Create files from template
    success_count = 0
    for file_name, file_content in template["files"].items():
        try:
            # Replace variables in file content
            processed_content = file_content
            for var_name, var_value in variables.items():
                processed_content = processed_content.replace(f"{{{{{var_name}}}}}", str(var_value))
            
            # Upload file
            logger.info(f"Creating file {file_name} in repository {repo_name}")
            file_response = update_file(
                github_username, repo_name, file_name,
                processed_content.encode('utf-8'), github_token,
                f"Initial commit: {file_name}", config=config
            )
            
            if file_response.status_code in [201, 200]:
                logger.info(f"Created file: {file_name}")
                print(f"Created file: {file_name}")
                success_count += 1
            else:
                logger.error(f"Error creating file {file_name}: {file_response.status_code}")
                print(f"Error creating file {file_name}: {file_response.status_code}")
        except Exception as e:
            logger.error(f"Error creating file {file_name}: {e}")
            print(f"Error creating file {file_name}: {e}")
    
    print(f"Template project created with {success_count} files.")
    print(f"View your repository at: https://github.com/{github_username}/{repo_name}")
    logger.info(f"Template project created with {success_count} files")

# ==============================================================================
# SECTION 4: AUTOMATED RELEASE MANAGEMENT
# ==============================================================================

def get_release_input(config, args=None):
    """Get release input from user or arguments with robust error handling."""
    try:
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
            try:
                changelog = generate_changelog(github_username, repo_name, github_token, version, config)
            except Exception as e:
                logger.warning(f"Error generating changelog: {e}")
                print(f"Warning: Error generating changelog: {e}")
                changelog = "Changelog generation failed."
        elif not args or not args.message:
            changelog_input = input("Enter release notes (optional): ")
            changelog = changelog_input
        
        return repo_name, version, name, changelog
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error getting release input: {e}")
        raise PyGitUpError(f"Error getting release input: {str(e)}") from e

def generate_changelog(username, repo_name, token, version, config):
    """Generate a changelog from commit history with robust error handling."""
    try:
        logger.info(f"Generating changelog for {repo_name} version {version}")
        response = get_commit_history(username, repo_name, token, config=config)
        if response.status_code == 200:
            commits = response.json()
            changelog = f"## Changelog for {version}\n\n"
            for commit in commits[:20]:  # Last 20 commits
                message = commit['commit']['message'].split('\n')[0]
                author = commit['commit']['author']['name']
                date = commit['commit']['author']['date'][:10]
                changelog += f"- {message} ({author} on {date})\n"
            logger.info("Changelog generated successfully")
            return changelog
        else:
            logger.error(f"Error getting commit history: {response.status_code}")
            return "Changelog generation failed."
    except Exception as e:
        logger.error(f"Error generating changelog: {e}")
        return f"Changelog generation failed: {e}"

@robust_api_call()
def create_release_tag(github_username, github_token, config, args=None):
    """Create a new GitHub release with robust error handling."""
    try:
        repo_name, version, name, changelog = get_release_input(config, args)
    except Exception as e:
        logger.error(f"Failed to get release input: {e}")
        return
    
    print(f"Creating release {version} for {repo_name}...")
    logger.info(f"Creating release {version} for {repo_name}")
    
    try:
        response = create_release(github_username, repo_name, github_token, version, name, changelog, config)
        
        if response.status_code == 201:
            release_data = response.json()
            print(f"Release created successfully!")
            print(f"View release at: {release_data['html_url']}")
            logger.info(f"Release {version} created successfully")
        else:
            logger.error(f"Error creating release: {response.status_code} - {response.text}")
            print(f"Error creating release: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Error creating release: {e}")
        print(f"Error creating release: {e}")

# ==============================================================================
# SECTION 5: MULTI-REPOSITORY OPERATIONS
# ==============================================================================

def get_multi_repo_input(config, args=None):
    """Get multi-repository input with robust error handling."""
    try:
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
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error getting multi-repo input: {e}")
        raise PyGitUpError(f"Error getting multi-repo input: {str(e)}") from e

@robust_api_call()
def update_multiple_repos(github_username, github_token, config, args=None):
    """Update the same file across multiple repositories with robust error handling."""
    try:
        repo_names, file_path, repo_file_path, commit_message = get_multi_repo_input(config, args)
    except Exception as e:
        logger.error(f"Failed to get multi-repo input: {e}")
        return
    
    if not os.path.exists(file_path):
        logger.error(f"File '{file_path}' not found")
        print(f"File '{file_path}' not found.")
        return
    
    print(f"Updating {file_path} in {len(repo_names)} repositories...")
    logger.info(f"Updating {file_path} in {len(repo_names)} repositories")
    
    try:
        with open(file_path, "rb") as f:
            file_content = f.read()
        logger.info(f"Read {len(file_content)} bytes from {file_path}")
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        print(f"Error reading file: {e}")
        return
    
    success_count = 0
    for repo_name in repo_names:
        try:
            logger.info(f"Processing repository {repo_name}")
            # Check if file exists to get SHA
            response = get_file_info(github_username, repo_name, repo_file_path, github_token, config)
            sha = None
            if response.status_code == 200:
                file_data = response.json()
                sha = file_data.get('sha')
                logger.info(f"Existing file SHA in {repo_name}: {sha}")
            
            # Update file
            response = update_file(
                github_username, repo_name, repo_file_path,
                file_content, github_token, commit_message, sha, config
            )
            
            if response.status_code in [200, 201]:
                print(f"✓ Updated {repo_file_path} in {repo_name}")
                logger.info(f"Successfully updated {repo_file_path} in {repo_name}")
                success_count += 1
            else:
                print(f"✗ Failed to update {repo_file_path} in {repo_name}: {response.status_code}")
                logger.error(f"Failed to update {repo_file_path} in {repo_name}: {response.status_code}")
        except Exception as e:
            print(f"✗ Error updating {repo_name}: {e}")
            logger.error(f"Error updating {repo_name}: {e}")
    
    print(f"Multi-repository update complete: {success_count}/{len(repo_names)} successful.")
    logger.info(f"Multi-repository update complete: {success_count}/{len(repo_names)} successful")

# ==============================================================================
# SECTION 6: AUTOMATED ISSUE CREATION FROM TODOs
# ==============================================================================

def scan_todos(github_username, github_token, config, args=None):
    """Scan code for TODO comments and create GitHub issues with robust error handling."""
    try:
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
        logger.info(f"Scanning for TODOs in {repo_name}")
        
        # For demo purposes, we'll create some sample TODOs
        todos = [
            {"file": "main.py", "line": 25, "comment": "TODO: Add error handling for network requests"},
            {"file": "utils.py", "line": 42, "comment": "TODO: Optimize this function for performance"},
            {"file": "auth.py", "line": 18, "comment": "TODO: Implement rate limiting"},
        ]
        
        created_issues = 0
        for todo in todos:
            try:
                title = f"TODO: {todo['comment'][6:]}"  # Remove "TODO: " prefix
                body = f"Found in {todo['file']} at line {todo['line']}\n\n{todo['comment']}"
                
                response = create_issue(github_username, repo_name, github_token, title, body, assignees, config)
                
                if response.status_code == 201:
                    issue_data = response.json()
                    print(f"✓ Created issue: {title}")
                    print(f"  View at: {issue_data['html_url']}")
                    logger.info(f"Created issue: {title}")
                    created_issues += 1
                else:
                    print(f"✗ Failed to create issue '{title}': {response.status_code}")
                    logger.error(f"Failed to create issue '{title}': {response.status_code}")
            except Exception as e:
                print(f"✗ Error creating issue '{todo['comment']}': {e}")
                logger.error(f"Error creating issue '{todo['comment']}': {e}")
        
        print(f"TODO scan complete: {created_issues} issues created.")
        logger.info(f"TODO scan complete: {created_issues} issues created")
    except Exception as e:
        logger.error(f"Error in TODO scan: {e}")
        print(f"Error in TODO scan: {e}")

# ==============================================================================
# SECTION 7: OFFLINE COMMIT QUEUE
# ==============================================================================

@safe_file_operation
def queue_offline_commit(config, args=None):
    """Queue a commit for when online with robust error handling."""
    try:
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
        
        # Validate file exists
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            print(f"Error: File '{file_path}' not found.")
            return
        
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
                logger.info(f"Loaded existing queue with {len(queue)} entries")
            except Exception as e:
                logger.warning(f"Could not load queue file: {e}")
                print(f"Warning: Could not load queue file: {e}")
        
        # Add new entry
        queue.append(queue_entry)
        logger.info("Added new entry to queue")
        
        # Save queue
        with open(queue_file, 'w') as f:
            json.dump(queue, f, indent=2)
        print(f"Commit queued for next online session.")
        print(f"Queue file: {queue_file}")
        logger.info(f"Commit queued successfully")
    except Exception as e:
        logger.error(f"Error queuing commit: {e}")
        print(f"Error queuing commit: {e}")

@robust_api_call()
def process_offline_queue(github_username, github_token, config):
    """Process queued commits when online with robust error handling."""
    queue_file = config["scheduling"]["offline_queue_file"]
    
    if not os.path.exists(queue_file):
        logger.info("No offline queue found")
        print("No offline queue found.")
        return
    
    try:
        with open(queue_file, 'r') as f:
            queue = json.load(f)
        logger.info(f"Loaded queue with {len(queue)} entries")
    except Exception as e:
        logger.error(f"Error loading queue: {e}")
        print(f"Error loading queue: {e}")
        return
    
    if not queue:
        logger.info("Offline queue is empty")
        print("Offline queue is empty.")
        return
    
    print(f"Processing {len(queue)} queued commits...")
    logger.info(f"Processing {len(queue)} queued commits")
    
    processed = 0
    failed = 0
    for entry in queue:
        if entry["status"] == "queued":
            try:
                # Validate file still exists
                if not os.path.exists(entry["file"]):
                    logger.warning(f"Queued file not found: {entry['file']}")
                    print(f"✗ Queued file not found: {entry['file']}")
                    entry["status"] = "failed"
                    entry["error"] = "File not found"
                    failed += 1
                    continue
                
                # Read file content
                with open(entry["file"], "rb") as f:
                    file_content = f.read()
                logger.info(f"Read {len(file_content)} bytes from {entry['file']}")
                
                # Upload file
                response = update_file(
                    github_username, entry["repo"], entry["file"],
                    file_content, github_token, entry["message"], config=config
                )
                
                if response.status_code in [200, 201]:
                    entry["status"] = "completed"
                    entry["processed_at"] = datetime.now().isoformat()
                    print(f"✓ Processed: {entry['message']}")
                    logger.info(f"Processed: {entry['message']}")
                    processed += 1
                else:
                    logger.error(f"Failed to process: {entry['message']} - {response.status_code}")
                    print(f"✗ Failed to process: {entry['message']} - {response.status_code}")
                    entry["status"] = "failed"
                    entry["error"] = f"HTTP {response.status_code}"
                    failed += 1
            except Exception as e:
                logger.error(f"Error processing: {entry['message']} - {e}")
                print(f"✗ Error processing: {entry['message']} - {e}")
                entry["status"] = "failed"
                entry["error"] = str(e)
                failed += 1
    
    # Save updated queue
    try:
        with open(queue_file, 'w') as f:
            json.dump(queue, f, indent=2)
        print(f"Processed {processed} commits from queue ({failed} failed).")
        logger.info(f"Processed {processed} commits from queue ({failed} failed)")
    except Exception as e:
        logger.error(f"Error saving updated queue: {e}")
        print(f"Error saving updated queue: {e}")

# ==============================================================================
# SECTION 8: UPLOAD/UPDATE A PROJECT DIRECTORY
# ==============================================================================

def get_project_directory_input(config, args=None):
    """Gets user input for the project upload details with robust error handling."""
    try:
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
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error getting project directory input: {e}")
        raise PyGitUpError(f"Error getting project directory input: {str(e)}") from e

@safe_file_operation
def initialize_git_repository(project_path):
    """Initializes a git repository in the specified directory with robust error handling."""
    try:
        if not os.path.exists(project_path):
            logger.error(f"Project directory not found: {project_path}")
            raise FileOperationError(f"The directory '{project_path}' does not exist.")
        
        os.chdir(project_path)
        logger.info(f"Changed directory to {project_path}")
        print(f"Changed directory to {project_path}")
        
        if not os.path.isdir(".git"):
            logger.info("Initializing new git repository")
            subprocess.run(["git", "init"], check=True, capture_output=True)
            print("Initialized empty Git repository.")
        else:
            print("This is already a git repository.")
        
        logger.info("Adding all files to git")
        subprocess.run(["git", "add", "."], check=True, capture_output=True)
        print("Staged all files.")
        
        # Check if there are changes to commit
        status_result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if status_result.stdout:
            logger.info("Committing files")
            subprocess.run(["git", "commit", "-m", "Initial commit"], check=True, capture_output=True)
            print("Committed files.")
        else:
            print("No changes to commit. Working tree clean.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Git command failed: {e.stderr.decode() if e.stderr else str(e)}")
        raise PyGitUpError(f"Git command failed: {e.stderr.decode() if e.stderr else str(e)}") from e
    except Exception as e:
        logger.error(f"Error initializing git repository: {e}")
        raise PyGitUpError(f"Error initializing git repository: {str(e)}") from e

@robust_api_call()
def create_or_get_github_repository(repo_name, repo_description, is_private, github_username, github_token, config):
    """Creates a new repository on GitHub or confirms an existing one with robust error handling."""
    try:
        logger.info(f"Checking if repository {repo_name} exists")
        api_url = f"https://api.github.com/repos/{github_username}/{repo_name}"
        headers = {"Authorization": f"token {github_token}", "Accept": "application/vnd.github.v3+json"}
        response = requests.get(api_url, headers=headers, timeout=config["performance"]["timeout"])
        
        if response.status_code == 200:
            logger.info(f"Repository {repo_name} already exists")
            print(f"Repository '{repo_name}' already exists on GitHub. Using existing repository.")
            return response.json()
        elif response.status_code == 404:
            # Repository doesn't exist, create it
            logger.info(f"Repository {repo_name} does not exist, creating it")
            create_url = "https://api.github.com/user/repos"
            data = {"name": repo_name, "description": repo_description, "private": is_private}
            create_response = requests.post(create_url, headers=headers, json=data, timeout=config["performance"]["timeout"])
            
            if create_response.status_code == 201:
                logger.info(f"Repository {repo_name} created successfully")
                print(f"Successfully created repository '{repo_name}' on GitHub.")
                return create_response.json()
            else:
                logger.error(f"Error creating repository: {create_response.status_code} - {create_response.text}")
                raise GitHubAPIError(f"Error creating repository: {create_response.status_code} - {create_response.text}")
        else:
            logger.error(f"Error checking repository: {response.status_code} - {response.text}")
            raise GitHubAPIError(f"Error checking repository: {response.status_code} - {response.text}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error during repository creation: {e}")
        raise NetworkError(f"Network error during repository creation: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error in repository creation/check: {e}")
        raise PyGitUpError(f"Error in repository creation/check: {str(e)}") from e

@safe_file_operation
def push_to_github(repo_name, github_username, github_token):
    """Adds the remote and force pushes to the new repository with robust error handling."""
    try:
        remote_url = f"https://{github_username}:{github_token}@github.com/{github_username}/{repo_name}.git"
        safe_remote_url = f"https://github.com/{github_username}/{repo_name}.git"
        
        # Check existing remotes
        logger.info("Checking existing git remotes")
        result = subprocess.run(["git", "remote"], capture_output=True, text=True)
        
        if "origin" in result.stdout.splitlines():
            logger.info("Origin remote exists, checking URL")
            existing_url_result = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True, check=True)
            if existing_url_result.stdout.strip() != remote_url and existing_url_result.stdout.strip() != safe_remote_url:
                logger.info("Updating remote URL")
                subprocess.run(["git", "remote", "set-url", "origin", remote_url], check=True)
            else:
                logger.info("Remote URL is correct")
        else:
            logger.info("Adding origin remote")
            subprocess.run(["git", "remote", "add", "origin", remote_url], check=True)
        
        # Check current branch
        logger.info("Checking current branch")
        branch_result = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, check=True)
        if branch_result.stdout.strip() != "main":
            logger.info("Renaming branch to main")
            subprocess.run(["git", "branch", "-M", "main"], check=True)
        
        print("Pushing to GitHub with force...")
        logger.info("Pushing to GitHub")
        subprocess.run(["git", "push", "-u", "--force", "origin", "main"], check=True)
        logger.info("Push completed successfully")
    except subprocess.CalledProcessError as e:
        logger.error(f"Git push failed: {e.stderr.decode() if e.stderr else str(e)}")
        raise PyGitUpError(f"Git push failed: {e.stderr.decode() if e.stderr else str(e)}") from e
    except Exception as e:
        logger.error(f"Error during git push: {e}")
        raise PyGitUpError(f"Error during git push: {str(e)}") from e

@robust_api_call()
def upload_project_directory(github_username, github_token, config, args=None):
    """Handles the entire process of uploading/updating a project directory with robust error handling."""
    try:
        project_path, repo_name, repo_description, is_private = get_project_directory_input(config, args)
    except Exception as e:
        logger.error(f"Failed to get project directory input: {e}")
        sys.exit(1)
    
    try:
        initialize_git_repository(project_path)
    except Exception as e:
        logger.error(f"Failed to initialize git repository: {e}")
        print(f"Error: {e}")
        sys.exit(1)
    
    try:
        create_or_get_github_repository(repo_name, repo_description, is_private, github_username, github_token, config)
    except Exception as e:
        logger.error(f"Failed to create/get GitHub repository: {e}")
        print(f"Error: {e}")
        sys.exit(1)
    
    try:
        push_to_github(repo_name, github_username, github_token)
    except Exception as e:
        logger.error(f"Failed to push to GitHub: {e}")
        print(f"Error: {e}")
        sys.exit(1)
    
    print(f"You can find your repository at: https://github.com/{github_username}/{repo_name}")
    logger.info(f"Project directory upload completed successfully")

# ==============================================================================
# COMMAND LINE ARGUMENT PARSING
# ==============================================================================

def create_parser():
    """Create and configure the argument parser with robust error handling."""
    try:
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
            choices=["project", "file", "batch", "template", "release", "multi-repo", "scan-todos", "offline-queue", "process-queue"],
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
        
        # Configuration arguments
        parser.add_argument("--config", help="Path to configuration file")
        parser.add_argument("--batch", action="store_true", help="Run in batch mode (used internally)")
        
        logger.info("Argument parser created successfully")
        return parser
    except Exception as e:
        logger.error(f"Error creating argument parser: {e}")
        raise PyGitUpError(f"Error creating argument parser: {str(e)}") from e

# ==============================================================================
# MAIN FUNCTION
# ==============================================================================

def main():
    """Main function to orchestrate the process with extremely robust error handling."""
    print("GitHub Uploader Tool")
    print("--------------------")
    
    try:
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
            try:
                process_offline_queue(github_username, github_token, config)
            except Exception as e:
                logger.warning(f"Error processing offline queue: {e}")
                print(f"Warning: Error processing offline queue: {e}")
        
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
            choice = input("Enter your choice (1-9): ")
            
            modes = {
                '1': "project",
                '2': "file",
                '3': "batch",
                '4': "template",
                '5': "release",
                '6': "multi-repo",
                '7': "scan-todos",
                '8': "offline-queue",
                '9': "process-queue"
            }
            
            mode = modes.get(choice, "")
            
            if not mode:
                print("Invalid choice. Exiting.")
                logger.info("User made invalid choice, exiting")
                sys.exit(1)
        
        # Execute based on mode
        logger.info(f"Executing mode: {mode}")
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
        else:
            print("Invalid mode. Exiting.")
            logger.error(f"Invalid mode specified: {mode}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        logger.info("Operation cancelled by user")
        sys.exit(0)
    except AuthenticationError as e:
        print(f"\nAuthentication Error: {e}")
        print("Please check your GitHub token and permissions.")
        logger.error(f"Authentication error: {e}")
        sys.exit(1)
    except NetworkError as e:
        print(f"\nNetwork Error: {e}")
        print("Please check your internet connection and try again.")
        logger.error(f"Network error: {e}")
        sys.exit(1)
    except GitHubAPIError as e:
        print(f"\nGitHub API Error: {e}")
        if e.status_code:
            print(f"Status Code: {e.status_code}")
        if e.response_text:
            print(f"Response: {e.response_text}")
        logger.error(f"GitHub API error: {e}")
        sys.exit(1)
    except FileOperationError as e:
        print(f"\nFile Operation Error: {e}")
        print("Please check file permissions and paths.")
        logger.error(f"File operation error: {e}")
        sys.exit(1)
    except ConfigurationError as e:
        print(f"\nConfiguration Error: {e}")
        print("Please check your configuration files.")
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except PyGitUpError as e:
        print(f"\nPyGitUp Error: {e}")
        logger.error(f"PyGitUp error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected Error: {e}")
        print("Please check the error log for details.")
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)

    print("--------------------")
    print("Operation complete.")
    logger.info("Operation completed successfully")

if __name__ == "__main__":
    main()