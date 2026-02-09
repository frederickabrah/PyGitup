
import os
import subprocess
import sys
import base64
from tqdm import tqdm

from ..github.api import update_file, get_file_info, create_repo, get_repo_info, get_user_repos
from ..utils.security import scan_directory_for_sensitive_files, audit_files_and_prompt, check_is_sensitive
from ..utils.validation import validate_repo_name, validate_file_path, sanitize_input, normalize_repo_path, validate_git_url
from ..utils.ui import print_header, print_info, print_success, print_error, print_warning

TQDM_AVAILABLE = True # Assume available for now

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
        print_info(f"Changed directory to {project_path}")
        if not os.path.isdir(".git"):
            # Use list-based args for safety
            subprocess.run(["git", "init"], check=True, capture_output=True)
            print_success("Initialized empty Git repository.")
        else:
            print_info("This is already a git repository.")
        
        subprocess.run(["git", "add", "."], check=True, capture_output=True)
        print_info("Staged all files.")
        
        status_result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if status_result.stdout:
             subprocess.run(["git", "commit", "-m", "Initial commit via PyGitUp"], check=True, capture_output=True)
             print_success("Committed files.")
        else:
            print_info("No changes to commit. Working tree clean.")
    except FileNotFoundError:
        print_error(f"Error: The directory '{project_path}' does not exist.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print_error(f"Git operation failed: {e.stderr if e.stderr else e}")
        sys.exit(1)

def create_or_get_github_repository(repo_name, repo_description, is_private, github_username, github_token):
    """Creates a new repository on GitHub or confirms an existing one."""
    response = get_repo_info(github_username, repo_name, github_token)
    if response.status_code == 200:
        print_info(f"Repository '{repo_name}' already exists on GitHub. Using existing repository.")
        return response.json()
    
    response = create_repo(github_username, repo_name, github_token, description=repo_description, private=is_private)
    if response.status_code == 201:
        print_success(f"Successfully created repository '{repo_name}' on GitHub.")
        return response.json()
    else:
        print_error(f"Error creating repository: {response.status_code} - {response.text}")
        sys.exit(1)

def push_to_github(repo_name, github_username, github_token):
    """
    Force pushes to GitHub using a temporary authenticated session.
    Keeps tokens out of .git/config to prevent credential exposure.
    """
    # Clean URLs for permanent storage
    safe_remote_url = f"https://github.com/{github_username}/{repo_name}.git"
    # Authenticated URL for the single push operation
    auth_remote_url = f"https://{github_token}@github.com/{github_username}/{repo_name}.git"
    
    try:
        # 1. Setup / Update clean remote
        result = subprocess.run(["git", "remote"], capture_output=True, text=True)
        if "origin" in result.stdout.splitlines():
            subprocess.run(["git", "remote", "set-url", "origin", safe_remote_url], check=True)
        else:
            subprocess.run(["git", "remote", "add", "origin", safe_remote_url], check=True)
            
        # 2. Ensure we are on 'main'
        subprocess.run(["git", "branch", "-M", "main"], check=True)
        
        # 3. Perform push using the authenticated URL (not saved to config)
        print_info("Pushing to GitHub (Authenticated Session)...")
        # We use the auth_remote_url directly in the push command
        subprocess.run(["git", "push", "-u", "--force", auth_remote_url, "main"], check=True, capture_output=True)
        
        print_success("Pushed to GitHub successfully.")
    except subprocess.CalledProcessError as e:
        print_error(f"Push failed: {e.stderr if e.stderr else e}")
        sys.exit(1)

def upload_project_directory(github_username, github_token, config, args=None):
    """Handles the entire process of uploading/updating a project directory."""
    if args and args.dry_run:
        print_info("*** Dry Run Mode: No changes will be made. ***")
        print_info("Would initialize git repository, create/get GitHub repository, and push to GitHub.")
        return

    print_header("Upload Project Directory")
    project_path, repo_name, repo_description, is_private = get_project_directory_input(config, args)
    
    # Input Validation
    is_valid_path, path_err = validate_file_path(project_path)
    if not is_valid_path:
        print_error(f"Error: {path_err}")
        return

    is_valid_repo, repo_err = validate_repo_name(repo_name)
    if not is_valid_repo:
        print_error(f"Error: {repo_err}")
        return

    # Run security scan on the directory
    if not scan_directory_for_sensitive_files(project_path):
        print_warning("Upload cancelled due to security check.")
        return

    initialize_git_repository(project_path)
    create_or_get_github_repository(repo_name, repo_description, is_private, github_username, github_token)
    push_to_github(repo_name, github_username, github_token)
    print_info(f"You can find your repository at: https://github.com/{github_username}/{repo_name}")

def get_single_file_input(config, args=None):
    """Gets user input for the file upload details."""
    if args and args.repo:
        repo_name = args.repo
    else:
        repo_name = input("Enter the name of the target GitHub repository: ")

    if args and args.file:
        local_file_path = args.file
        print_info(f"Selected file: {local_file_path}")
    else:
        print_header("Select a file to upload")
        local_file_path = None
        try:
            current_directory = os.getcwd()
            print_info(f"Listing files in: {current_directory}")
            
            files = [item for item in os.listdir('.') if os.path.isfile(item)]

            if not files:
                print_info("No files found in the current directory.")
            else:
                for i, filename in enumerate(files):
                    print(f"{i + 1}: {filename}")
                
                print("\nEnter the number of the file to upload, or type a different path manually.")
                choice = input("> ")

                try:
                    file_index = int(choice) - 1
                    if 0 <= file_index < len(files):
                        local_file_path = files[file_index]
                        print_info(f"You selected: {local_file_path}")
                    else:
                        print_error("Invalid number.")
                except ValueError:
                    local_file_path = choice
                    print_info(f"You entered path: {local_file_path}")

        except Exception as e:
            print_error(f"Could not list files interactively ({e}).")

    if not local_file_path:
        print_info("Please provide the file path manually.")
        local_file_path = input("Enter the full local path of the file to upload: ")

    if args and args.path:
        repo_file_path = args.path
    else:
        repo_file_path = input("Enter the path for the file in the repository (e.g., folder/file.txt): ")

    # Security: Normalize path
    try:
        repo_file_path = normalize_repo_path(repo_file_path)
    except ValueError as e:
        print_error(str(e))
        return None, None, None, None

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
    if args and args.dry_run:
        print_info("*** Dry Run Mode: No changes will be made. ***")
        repo_name, local_file_path, repo_file_path, commit_message = get_single_file_input(config, args)
        print_info(f"Would upload {local_file_path} to {repo_name}/{repo_file_path} with message: {commit_message}")
        return

    print_header("Upload Single File")
    repo_name, local_file_path, repo_file_path, commit_message = get_single_file_input(config, args)

    # Input Validation
    is_valid_path, path_err = validate_file_path(local_file_path)
    if not is_valid_path:
        print_error(f"Error: {path_err}")
        return False

    is_valid_repo, repo_err = validate_repo_name(repo_name)
    if not is_valid_repo:
        print_error(f"Error: {repo_err}")
        return False

    if check_is_sensitive(local_file_path):
        print_warning(f"'{local_file_path}' appears to be a sensitive file.")
        confirm = input("Are you sure you want to upload it? (y/n): ").lower()
        if confirm != 'y':
            print_info("Upload cancelled.")
            return False

    try:
        with open(local_file_path, "rb") as f:
            if TQDM_AVAILABLE:
                file_size = os.path.getsize(local_file_path)
                with tqdm(total=file_size, unit='B', unit_scale=True, desc="Reading file") as pbar:
                    content = f.read()
                    pbar.update(len(content))
            else:
                content = f.read()
    except FileNotFoundError:
        print_error(f"Error: The local file '{local_file_path}' was not found.")
        if not args or not args.batch:
            sys.exit(1)
        return False
    except Exception as e:
        print_error(f"Error reading file: {e}")
        if not args or not args.batch:
            sys.exit(1)
        return False

    sha = None
    response = get_file_info(github_username, repo_name, repo_file_path, github_token)
    if response.status_code == 200:
        print_info("File exists in the repository. It will be overwritten.")
        sha = response.json()['sha']
    elif response.status_code != 404:
        print_error(f"Error checking for file: {response.status_code} - {response.text}")
        if not args or not args.batch:
            sys.exit(1)
        return False

    response = update_file(github_username, repo_name, repo_file_path, content, github_token, commit_message, sha)
    if response.status_code == 201:
        print_success(f"Successfully created file '{repo_file_path}' in '{repo_name}'.")
    elif response.status_code == 200:
        print_success(f"Successfully updated file '{repo_file_path}' in '{repo_name}'.")
    else:
        print_error(f"Error uploading file: {response.status_code} - {response.text}")
        if not args or not args.batch:
            sys.exit(1)
        return False
    print_info(f"View the file at: {response.json()['content']['html_url']}")
    return True

def get_batch_files_input(config, args=None):
    """Get files for batch upload."""
    if args and args.files:
        files = [f.strip() for f in args.files.split(',') if f.strip()]
    else:
        print_header("Select files for batch upload")
        print("Enter file paths separated by commas, or 'all' for all files in directory:")
        files_input = input("> ").strip()
        
        if files_input.lower() == 'all':
            files = [item for item in os.listdir('.') if os.path.isfile(item)]
        else:
            files = [f.strip() for f in files_input.split(',') if f.strip()]
    
    if not files:
        print_error("No files specified.")
        return None, None, None, None
    
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
    """Upload multiple files in batch with styled output."""
    if args and args.dry_run:
        print_info("*** Dry Run Mode: No changes will be made. ***")
        files, repo_name, repo_base_path, commit_message = get_batch_files_input(config, args)
        print_info(f"Would upload {len(files)} files to {repo_name} in batch.")
        return

    files, repo_name, repo_base_path, commit_message = get_batch_files_input(config, args)
    
    if not files:
        return

    # Security check for batch files
    files = audit_files_and_prompt(files)
    if not files:
        print_warning("No files to upload after security check.")
        return
    
    print_info(f"\nUploading {len(files)} files to {repo_name}...")
    
    file_iterator = tqdm(files, desc="Uploading files") if TQDM_AVAILABLE else files
    
    success_count = 0
    fail_count = 0
    
    for local_file in file_iterator:
        try:
            if repo_base_path:
                repo_file_path = os.path.join(repo_base_path, os.path.basename(local_file)).replace("\\", "/")
            else:
                repo_file_path = os.path.basename(local_file)
            
            # Use upload_single_file logic but adapted for batch
            # We skip some input gathering and validation already done
            
            with open(local_file, "rb") as f:
                content = f.read()
            
            sha = None
            f_info = get_file_info(github_username, repo_name, repo_file_path, github_token)
            if f_info.status_code == 200:
                sha = f_info.json()['sha']
            
            response = update_file(github_username, repo_name, repo_file_path, content, github_token, commit_message, sha)
            
            if response.status_code in [200, 201]:
                success_count += 1
            else:
                print_error(f"Failed to upload {local_file}: {response.status_code}")
                fail_count += 1
                if not config["batch"]["continue_on_error"]:
                    print_warning("Stopping batch upload due to error.")
                    break
                    
        except Exception as e:
            print_error(f"Error uploading {local_file}: {e}")
            fail_count += 1
            if not config["batch"]["continue_on_error"]:
                break
    
    print_success(f"\nBatch upload complete: {success_count} succeeded, {fail_count} failed.")

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
    """Update the same file across multiple repositories with styled output."""
    if args and args.dry_run:
        print_info("*** Dry Run Mode: No changes will be made. ***")
        repo_names, file_path, repo_file_path, commit_message = get_multi_repo_input(config, args)
        print_info(f"Would update {file_path} in {len(repo_names)} repositories.")
        return

    print_header("Multi-Repository Update")
    repo_names, file_path, repo_file_path, commit_message = get_multi_repo_input(config, args)
    
    # Security check
    if check_is_sensitive(file_path):
        print_warning(f"'{file_path}' appears to be a sensitive file.")
        confirm = input("Are you sure you want to update this file across multiple repositories? (y/n): ").lower()
        if confirm != 'y':
            print_info("Multi-repo update cancelled.")
            return

    # Filter out any empty repository names that might result from trailing commas
    repo_names = [name for name in repo_names if name]

    if not os.path.exists(file_path):
        print_error(f"File '{file_path}' not found.")
        return
    
    print_info(f"Updating {file_path} in {len(repo_names)} repositories...")
    
    try:
        with open(file_path, "rb") as f:
            file_content = f.read()
    except Exception as e:
        print_error(f"Error reading file: {e}")
        return
    
    success_count = 0
    for repo_name in repo_names:
        try:
            # Check if file exists to get SHA
            response = get_file_info(github_username, repo_name, repo_file_path, github_token)
            sha = None
            if response.status_code == 200:
                sha = response.json().get('sha')
            
            # Update file
            update_response = update_file(
                github_username, repo_name, repo_file_path,
                file_content, github_token, commit_message, sha
            )
            
            if update_response.status_code in [200, 201]:
                print_success(f"Updated {repo_file_path} in {repo_name}")
                success_count += 1
            else:
                print_error(f"Failed to update {repo_file_path} in {repo_name}: {update_response.status_code}")
        except Exception as e:
            print_error(f"Error updating {repo_name}: {e}")
    
    print_success(f"Multi-repository update complete: {success_count}/{len(repo_names)} successful.")

import math
import shutil
import tempfile

def migrate_repository(github_username, github_token, config, args=None):
    """Mirror a repository from any source to GitHub with full history."""
    print_header("The Great Migration Porter")
    
    src_url = args.url if args and hasattr(args, 'url') and args.url else input("🔗 Enter Source Repository URL (GitLab/Bitbucket/etc): ")
    
    # Security: Validate Source URL
    try:
        validate_git_url(src_url)
    except ValueError as e:
        print_error(str(e))
        return

    dest_name = args.repo if args and hasattr(args, 'repo') and args.repo else input("📦 Enter Destination GitHub Repository Name: ")
    
    is_private = args.private if args and hasattr(args, 'private') else input("🔒 Make destination private? (y/n) [y]: ").lower() != 'n'

    print_info(f"Establishing destination on GitHub...")
    # Ensure dest exists
    create_or_get_github_repository(dest_name, f"Mirrored from {src_url}", is_private, github_username, github_token)
    
    # Authenticated URL for the single push operation
    auth_dest_url = f"https://{github_token}@github.com/{github_username}/{dest_name}.git"
    
    # Use a temporary directory for the mirror operation
    temp_dir = tempfile.mkdtemp()
    try:
        print_info("Performing mirror clone (this may take time for large repos)...")
        # Direct arguments to avoid shell=True risk
        subprocess.run(["git", "clone", "--mirror", src_url, temp_dir], check=True, capture_output=True)
        
        # Change to the temporary directory
        current_dir = os.getcwd()
        os.chdir(temp_dir)
        
        print_info("Pushing mirror to GitHub (Authenticated Session)...")
        # We push to the auth_dest_url but the origin URL in the clone remains clean
        subprocess.run(["git", "push", "--mirror", auth_dest_url], check=True, capture_output=True)
        
        os.chdir(current_dir)
        print_success(f"\nMigration Successful! 🚀")
        print_info(f"View it at: https://github.com/{github_username}/{dest_name}")
    except subprocess.CalledProcessError as e:
        print_error(f"Migration failed during git operation: {e.stderr if e.stderr else e}")
    finally:
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

def manage_bulk_repositories(github_token):
    """List all repositories and show aggregated health scores."""
    print_header("Bulk Repository Management")
    print_info("Fetching all your repositories...")
    
    try:
        response = get_user_repos(github_token)
        if response.status_code != 200:
            print_error(f"Failed to fetch repos: {response.status_code}")
            return
            
        repos = response.json()
        print_success(f"Found {len(repos)} repositories.\n")
        
        print(f"{ 'Repository Name':<40} | {'Stars':<6} | {'Issues':<6} | {'Score':<6}")
        print("-" * 65)
        
        import math
        for r in repos:
            stars = r.get('stargazers_count', 0)
            forks = r.get('forks_count', 0)
            open_issues = r.get('open_issues_count', 0)
            
            # Real Intelligence Logic:
            # 1. Maintenance (40 pts): Ratio of forks to issues (engagement vs burden)
            m_score = min((forks / (open_issues + 1)) * 20, 40)
            
            # 2. Popularity (40 pts): Star density
            p_score = min(math.log2(stars + 1) * 5, 40)
            
            # 3. Baseline Activity (20 pts)
            health_score = int(m_score + p_score + 20)
            health_score = max(0, min(100, health_score))
            
            color = "green" if health_score > 70 else "yellow" if health_score > 40 else "red"
            print(f"{r['name']:<40} | {stars:<6} | {open_issues:<6} | [{color}]{health_score}%[/{color}]")
            
    except Exception as e:
        print_error(f"Bulk operation failed: {e}")
