
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
        return True, "Git repository initialized and committed."
    except FileNotFoundError:
        return False, f"Error: The directory '{project_path}' does not exist."
    except subprocess.CalledProcessError as e:
        return False, f"Git operation failed: {e.stderr.strip() if e.stderr else str(e)}"

def create_or_get_github_repository(repo_name, repo_description, is_private, github_username, github_token):
    """Creates a new repository on GitHub or confirms an existing one."""
    response = get_repo_info(github_username, repo_name, github_token)
    if response.status_code == 200:
        print_info(f"Repository '{repo_name}' already exists on GitHub. Using existing repository.")
        return True, response.json()
    
    response = create_repo(github_username, repo_name, github_token, description=repo_description, private=is_private)
    if response.status_code == 201:
        print_success(f"Successfully created repository '{repo_name}' on GitHub.")
        return True, response.json()
    else:
        return False, f"Error creating repository: {response.status_code} - {response.text}"

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
        return True, "Pushed to GitHub successfully."
    except subprocess.CalledProcessError as e:
        return False, f"Push failed: {e.stderr.strip() if e.stderr else str(e)}"

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
        return False

    success, msg = initialize_git_repository(project_path)
    if not success:
        print_error(msg)
        return False
    
    # Technical Upgrade: Automated SBOM Generation
    print_info("📄 Generating Software Bill of Materials (SBOM)...")
    try:
        from ..utils.supply_chain import generate_sbom_spdx
        sbom_path = os.path.join(project_path, "sbom.spdx.json")
        generate_sbom_spdx(sbom_path)
        subprocess.run(["git", "add", "sbom.spdx.json"], capture_output=True)
        subprocess.run(["git", "commit", "-m", "docs: include automated SBOM manifest"], capture_output=True)
        print_success("SBOM manifest integrated into repository.")
    except Exception as e:
        print_warning(f"SBOM generation skipped: {e}")
        
    success, data_or_msg = create_or_get_github_repository(repo_name, repo_description, is_private, github_username, github_token)
    if not success:
        print_error(data_or_msg)
        return False
        
    success, msg = push_to_github(repo_name, github_username, github_token)
    if not success:
        print_error(msg)
        return False
        
    print_info(f"You can find your repository at: https://github.com/{github_username}/{repo_name}")
    return True

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
    if files is None:
        print_warning("Batch upload cancelled by user.")
        return
    if not files:
        print_info("No files selected for upload after security filtering.")
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
    """Update the same file across multiple repositories in parallel."""
    if args and args.dry_run:
        print_info("*** Dry Run Mode: No changes will be made. ***")
        repo_names, file_path, repo_file_path, commit_message = get_multi_repo_input(config, args)
        print_info(f"Would update {file_path} in {len(repo_names)} repositories.")
        return

    print_header("Multi-Repository Update")
    repo_names, file_path, repo_file_path, commit_message = get_multi_repo_input(config, args)
    
    # Filter empty repo names
    repo_names = [name for name in repo_names if name]

    if not os.path.exists(file_path):
        print_error(f"File '{file_path}' not found.")
        return
    
    try:
        with open(file_path, "rb") as f:
            file_content = f.read()
    except Exception as e:
        print_error(f"Error reading file: {e}")
        return

    print_info(f"Updating {len(repo_names)} repositories in parallel...")
    
    import concurrent.futures
    success_count = 0
    
    def update_single_repo(repo_name):
        try:
            # Check for SHA
            response = get_file_info(github_username, repo_name, repo_file_path, github_token)
            sha = response.json().get('sha') if response.status_code == 200 else None
            
            # Update
            up_resp = update_file(github_username, repo_name, repo_file_path, file_content, github_token, commit_message, sha)
            if up_resp.status_code in [200, 201]:
                return True, repo_name
            return False, f"{repo_name} (HTTP {up_resp.status_code})"
        except Exception as e:
            return False, f"{repo_name} ({e})"

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(update_single_repo, name): name for name in repo_names}
        for future in concurrent.futures.as_completed(futures):
            success, result = future.result()
            if success:
                print_success(f"Updated: {result}")
                success_count += 1
            else:
                print_error(f"Failed: {result}")
    
    print_info(f"\nMulti-repo update complete: {success_count}/{len(repo_names)} successful.")

import math
import shutil
import tempfile

def migrate_repository(github_username, github_token, config, args=None):
    """Mirror a repository from any source to GitHub with full history."""
    print_header("Repository Migration Tool")
    
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
    print_header("Bulk Repository Management")
    
    # Core Upgrade: Reload config to ensures rotated tokens are active
    from ..core.config import load_config, get_github_token
    config = load_config()
    current_token = get_github_token(config) or github_token
    
    print_info("Fetching all your repositories...")

    try:
        from ..github.api import get_user_repos, get_repo_languages
        from datetime import datetime

        response = get_user_repos(current_token)
        if response.status_code != 200:
            print_error(f"Failed to fetch repos: {response.status_code}")
            return

        repos = response.json()
        print_success(f"Found {len(repos)} repositories.\n")

        total_stars = sum(r.get('stargazers_count', 0) for r in repos)
        total_forks = sum(r.get('forks_count', 0) for r in repos)
        total_issues = sum(r.get('open_issues_count', 0) for r in repos)
        total_size = sum(r.get('size', 0) for r in repos)
        
        public_repos = len([r for r in repos if not r.get('private', False)])
        private_repos = len([r for r in repos if r.get('private', False)])
        archived_repos = len([r for r in repos if r.get('archived', False)])
        forks_repos = len([r for r in repos if r.get('fork', False)])

        print("Portfolio Overview:")
        print(f"  Total Repositories:    {len(repos)}")
        print(f"  Public Repositories:   {public_repos}")
        print(f"  Private Repositories:  {private_repos}")
        print(f"  Archived Repositories: {archived_repos}")
        print(f"  Forked Repositories:   {forks_repos}")
        print(f"  Total Stars:           {total_stars}")
        print(f"  Total Forks:           {total_forks}")
        print(f"  Total Issues:          {total_issues}")
        print(f"  Total Size:            {total_size / 1024:.2f} MB\n")

        language_stats = {}
        for repo in repos[:20]:
            try:
                lang_resp = get_repo_languages(repo['owner']['login'], repo['name'], current_token)
                if lang_resp.status_code == 200:
                    langs = lang_resp.json()
                    for lang, bytes_count in langs.items():
                        language_stats[lang] = language_stats.get(lang, 0) + bytes_count
            except:
                pass
        
        if language_stats:
            total_bytes = sum(language_stats.values())
            print("Language Distribution (Top 20 Repos):")
            for lang, bytes_count in sorted(language_stats.items(), key=lambda x: -x[1])[:10]:
                percentage = (bytes_count / total_bytes * 100) if total_bytes > 0 else 0
                bar_length = int(percentage / 2)
                bar = "#" * bar_length + "-" * (50 - bar_length)
                print(f"  {lang:<20} {bar} {percentage:.1f}%")
            print()

        print("Detailed Repository Intelligence:\n")
        print(f"{'Repository':<40} | {'Vis':<4} | {'Stars':<6} | {'Forks':<6} | {'Issues':<6} | {'Updated':<12} | {'Health':<8} | {'Status':<15}")
        print("-" * 110)

        import math
        repo_scores = []
        
        for r in repos:
            name = f"{r['owner']['login']}/{r['name']}"
            visibility = "Pvt" if r.get('private') else "Pub"
            stars = r.get('stargazers_count', 0)
            forks = r.get('forks_count', 0)
            open_issues = r.get('open_issues_count', 0)
            updated_at = r.get('updated_at', '')[:10] if r.get('updated_at') else 'N/A'
            
            engagement = 0
            if stars > 0:
                engagement += min(math.log2(stars + 1) * 6, 15)
            if forks > 0:
                engagement += min(forks * 2, 15)
            
            maintenance = 0
            if open_issues > 0:
                maintenance += max(0, 30 - (open_issues * 2))
            else:
                maintenance = 30
            
            activity = 0
            try:
                updated_date = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                days_since_update = (datetime.utcnow() - updated_date.replace(tzinfo=None)).days
                if days_since_update < 7:
                    activity = 25
                elif days_since_update < 30:
                    activity = 20
                elif days_since_update < 90:
                    activity = 15
                elif days_since_update < 365:
                    activity = 10
                else:
                    activity = 5
            except:
                activity = 10
            
            doc_score = 0
            if r.get('has_wiki'):
                doc_score += 5
            if r.get('has_pages'):
                doc_score += 5
            if r.get('license'):
                doc_score += 5
            
            health_score = int(engagement + maintenance + activity + doc_score)
            health_score = max(0, min(100, health_score))
            
            if r.get('archived'):
                status = "Archived"
            elif r.get('fork'):
                status = "Fork"
            elif health_score >= 80:
                status = "Excellent"
            elif health_score >= 60:
                status = "Good"
            elif health_score >= 40:
                status = "Needs Work"
            else:
                status = "Critical"
            
            color = "green" if health_score >= 70 else "yellow" if health_score >= 40 else "red"

            # Use console.print to render Rich markup
            from ..utils.ui import console
            console.print(f"{name:<40} | {visibility:<4} | {stars:<6} | {forks:<6} | {open_issues:<6} | {updated_at:<12} | [{color}]{health_score}%[/{color}] | {status:<15}")
            
            repo_scores.append({
                'name': name,
                'health': health_score,
                'stars': stars,
                'forks': forks,
                'issues': open_issues,
                'visibility': 'private' if r.get('private') else 'public',
                'archived': r.get('archived', False),
                'updated_at': updated_at
            })

        print("-" * 110)
        
        excellent = len([r for r in repo_scores if r['health'] >= 80])
        good = len([r for r in repo_scores if 60 <= r['health'] < 80])
        needs_work = len([r for r in repo_scores if 40 <= r['health'] < 60])
        critical = len([r for r in repo_scores if r['health'] < 40])
        
        print("\nHealth Distribution:")
        print(f"  Excellent (80-100): {excellent}")
        print(f"  Good (60-79):       {good}")
        print(f"  Needs Work (40-59): {needs_work}")
        print(f"  Critical (0-39):    {critical}\n")

        if repo_scores:
            top_by_stars = sorted(repo_scores, key=lambda x: -x['stars'])[:5]
            top_by_health = sorted(repo_scores, key=lambda x: -x['health'])[:5]
            most_active = sorted([r for r in repo_scores if not r['archived']], key=lambda x: x['updated_at'], reverse=True)[:5]
            
            print("Top Performers:")
            print("  By Stars:")
            for i, repo in enumerate(top_by_stars, 1):
                print(f"    {i}. {repo['name']} ({repo['stars']} stars)")
            print("\n  By Health Score:")
            for i, repo in enumerate(top_by_health, 1):
                print(f"    {i}. {repo['name']} ({repo['health']}%)")
            print("\n  Most Recently Updated:")
            for i, repo in enumerate(most_active, 1):
                print(f"    {i}. {repo['name']} ({repo['updated_at']})")
            print()

        recommendations = []
        if critical > 0:
            recommendations.append(f"{critical} repos need immediate attention (health < 40%)")
        if needs_work > 0:
            recommendations.append(f"{needs_work} repos could use improvement (health 40-60%)")
        if archived_repos > 0:
            recommendations.append(f"Consider deleting {archived_repos} archived repos to clean up")
        low_star_repos = len([r for r in repo_scores if r['stars'] == 0 and not r['archived']])
        if low_star_repos > 5:
            recommendations.append(f"{low_star_repos} active repos have 0 stars - consider promotion")
        no_license = len([r for r in repos if not r.get('license')])
        if no_license > 0:
            recommendations.append(f"{no_license} repos missing LICENSE - add for clarity")
        
        if recommendations:
            print("Recommendations:")
            for rec in recommendations:
                print(f"  - {rec}")
            print()

        print("Export Options:")
        print("  1: JSON Format")
        print("  2: CSV Format")
        print("  3: Markdown Report")
        print("  4: Skip Export")
        export_choice = input("\nChoice [4]: ").strip() or "4"
        
        if export_choice in ['1', '2', '3']:
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            
            if export_choice == '1':
                import json
                filename = f"repo_report_{timestamp}.json"
                with open(filename, 'w') as f:
                    json.dump({
                        'generated_at': datetime.utcnow().isoformat(),
                        'total_repos': len(repos),
                        'summary': {
                            'total_stars': total_stars,
                            'total_forks': total_forks,
                            'total_issues': total_issues,
                            'public_repos': public_repos,
                            'private_repos': private_repos,
                        },
                        'repositories': repo_scores
                    }, f, indent=2)
                print_success(f"Exported to {filename}")
            
            elif export_choice == '2':
                import csv
                filename = f"repo_report_{timestamp}.csv"
                with open(filename, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Name', 'Health', 'Stars', 'Forks', 'Issues', 'Visibility', 'Archived', 'Updated'])
                    for repo in repo_scores:
                        writer.writerow([
                            repo['name'], repo['health'], repo['stars'],
                            repo['forks'], repo['issues'], repo['visibility'],
                            repo['archived'], repo['updated_at']
                        ])
                print_success(f"Exported to {filename}")
            
            elif export_choice == '3':
                filename = f"repo_report_{timestamp}.md"
                with open(filename, 'w') as f:
                    f.write("# Repository Health Report\n\n")
                    f.write(f"Generated: {datetime.utcnow().isoformat()}\n\n")
                    f.write("## Summary\n\n")
                    f.write(f"- Total Repos: {len(repos)}\n")
                    f.write(f"- Total Stars: {total_stars}\n")
                    f.write(f"- Total Forks: {total_forks}\n\n")
                    f.write("## Repository Details\n\n")
                    f.write("| Name | Health | Stars | Forks | Issues |\n")
                    f.write("|------|-------|-------|-------|--------|\n")
                    for repo in repo_scores:
                        f.write(f"| {repo['name']} | {repo['health']}% | {repo['stars']} | {repo['forks']} | {repo['issues']} |\n")
                print_success(f"Exported to {filename}")

    except Exception as e:
        print_error(f"Bulk operation failed: {e}")
