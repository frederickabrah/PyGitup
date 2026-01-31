import os
import subprocess
import sys
import base64
from tqdm import tqdm

from ..github.api import update_file, get_file_info, create_repo, get_repo_info
from ..utils.security import scan_directory_for_sensitive_files, audit_files_and_prompt, check_is_sensitive

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
    response = get_repo_info(github_username, repo_name, github_token)
    if response.status_code == 200:
        print(f"Repository '{repo_name}' already exists on GitHub. Using existing repository.")
        return response.json()
    
    response = create_repo(github_username, repo_name, github_token, description=repo_description, private=is_private)
    if response.status_code == 201:
        print(f"Successfully created repository '{repo_name}' on GitHub.")
        return response.json()
    else:
        print(f"Error creating repository: {response.status_code} - {response.text}")
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
    if args and args.dry_run:
        print("*** Dry Run Mode: No changes will be made. ***")
        print("Would initialize git repository, create/get GitHub repository, and push to GitHub.")
        return

    project_path, repo_name, repo_description, is_private = get_project_directory_input(config, args)
    
    # Run security scan on the directory
    if not scan_directory_for_sensitive_files(project_path):
        print("Upload cancelled due to security check.")
        return

    initialize_git_repository(project_path)
    create_or_get_github_repository(repo_name, repo_description, is_private, github_username, github_token)
    push_to_github(repo_name, github_username, github_token)
    print(f"You can find your repository at: https://github.com/{github_username}/{repo_name}")

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
    if args and args.dry_run:
        print("*** Dry Run Mode: No changes will be made. ***")
        repo_name, local_file_path, repo_file_path, commit_message = get_single_file_input(config, args)
        print(f"Would upload {local_file_path} to {repo_name}/{repo_file_path} with message: {commit_message}")
        return

    repo_name, local_file_path, repo_file_path, commit_message = get_single_file_input(config, args)

    if check_is_sensitive(local_file_path):
        print(f"\nWARNING: '{local_file_path}' appears to be a sensitive file.")
        confirm = input("Are you sure you want to upload it? (y/n): ").lower()
        if confirm != 'y':
            print("Upload cancelled.")
            return False

    try:
        with open(local_file_path, "rb") as f:
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
    response = get_file_info(github_username, repo_name, repo_file_path, github_token)
    if response.status_code == 200:
        print("File exists in the repository. It will be overwritten.")
        sha = response.json()['sha']
    elif response.status_code != 404:
        print(f"Error checking for file: {response.status_code} - {response.text}")
        if not args or not args.batch:
            sys.exit(1)
        return False

    response = update_file(github_username, repo_name, repo_file_path, content, github_token, commit_message, sha)
    if response.status_code == 201:
        print(f"Successfully created file '{repo_file_path}' in '{repo_name}'.")
    elif response.status_code == 200:
        print(f"Successfully updated file '{repo_file_path}' in '{repo_name}'.")
    else:
        print(f"Error uploading file: {response.status_code} - {response.text}")
        if not args or not args.batch:
            sys.exit(1)
        return False
    print(f"View the file at: {response.json()['content']['html_url']}")
    return True

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
    if args and args.dry_run:
        print("*** Dry Run Mode: No changes will be made. ***")
        files, repo_name, repo_base_path, commit_message = get_batch_files_input(config, args)
        print(f"Would upload {len(files)} files to {repo_name} in batch.")
        return

    files, repo_name, repo_base_path, commit_message = get_batch_files_input(config, args)
    
    if not files:
        return

    # Security check for batch files
    files = audit_files_and_prompt(files)
    if not files:
        print("No files to upload after security check.")
        return
    
    print(f"\nUploading {len(files)} files to {repo_name}...")
    
    file_iterator = tqdm(files, desc="Uploading files") if TQDM_AVAILABLE else files
    
    success_count = 0
    fail_count = 0
    
    for local_file in file_iterator:
        try:
            if repo_base_path:
                repo_file_path = os.path.join(repo_base_path, os.path.basename(local_file)).replace("\\", "/")
            else:
                repo_file_path = os.path.basename(local_file)
            
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
    if args and args.dry_run:
        print("*** Dry Run Mode: No changes will be made. ***")
        repo_names, file_path, repo_file_path, commit_message = get_multi_repo_input(config, args)
        print(f"Would update {file_path} in {len(repo_names)} repositories.")
        return

    repo_names, file_path, repo_file_path, commit_message = get_multi_repo_input(config, args)
    
    # Security check
    if check_is_sensitive(file_path):
        print(f"\nWARNING: '{file_path}' appears to be a sensitive file.")
        confirm = input("Are you sure you want to update this file across multiple repositories? (y/n): ").lower()
        if confirm != 'y':
            print("Multi-repo update cancelled.")
            return

    # Filter out any empty repository names that might result from trailing commas
    repo_names = [name for name in repo_names if name]

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
                sha = response.json().get('sha')
            
            # Update file
            update_response = update_file(
                github_username, repo_name, repo_file_path,
                file_content, github_token, commit_message, sha
            )
            
            if update_response.status_code in [200, 201]:
                print(f"✓ Updated {repo_file_path} in {repo_name}")
                success_count += 1
            else:
                print(f"✗ Failed to update {repo_file_path} in {repo_name}: {update_response.status_code} - {update_response.text}")
        except Exception as e:
            print(f"✗ Error updating {repo_name}: {e}")
    
    print(f"Multi-repository update complete: {success_count}/{len(repo_names)} successful.")