import os
import subprocess
import requests
import base64
import getpass

# ==============================================================================
# SECTION 1: UPLOAD/UPDATE A SINGLE FILE
# ==============================================================================

def get_single_file_input():
    """Gets user input for the file upload details interactively."""
    repo_name = input("Enter the name of the target GitHub repository: ")

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

    repo_file_path = input("Enter the path for the file in the repository (e.g., folder/file.txt): ")
    commit_message = input("Enter the commit message: ")
    return repo_name, local_file_path, repo_file_path, commit_message

def upload_single_file(github_username, github_token):
    """Handles the entire process of uploading/updating a single file."""
    repo_name, local_file_path, repo_file_path, commit_message = get_single_file_input()

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
        exit()

    sha = None
    try:
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            print("File exists in the repository. It will be overwritten.")
            sha = response.json()['sha']
        elif response.status_code != 404:
            print(f"Error checking for file: {response.status_code} - {response.text}")
            exit()
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to GitHub: {e}")
        exit()

    data = {"message": commit_message, "content": encoded_content}
    if sha:
        data["sha"] = sha

    try:
        response = requests.put(api_url, headers=headers, json=data)
        response.raise_for_status()
        if response.status_code == 201:
            print(f"Successfully created file '{repo_file_path}' in '{repo_name}'.")
        elif response.status_code == 200:
            print(f"Successfully updated file '{repo_file_path}' in '{repo_name}'.")
        print(f"View the file at: {response.json()['content']['html_url']}")
    except requests.exceptions.HTTPError as e:
        print(f"Error uploading file: {e.response.status_code} - {e.response.text}")
        exit()
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to GitHub: {e}")
        exit()

# ==============================================================================
# SECTION 2: UPLOAD/UPDATE A PROJECT DIRECTORY
# ==============================================================================

def get_project_directory_input():
    """Gets user input for the project upload details."""
    project_path = input("Enter the full path to your project directory: ")
    repo_name = input("Enter the desired name for your GitHub repository: ")
    repo_description = input("Enter a description for your repository: ")
    is_private = input("Make the repository private? (y/n): ").lower() == 'y'
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
        exit()
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while running a git command: {e}")
        exit()

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
        exit()
    create_url = "https://api.github.com/user/repos"
    data = {"name": repo_name, "description": repo_description, "private": is_private}
    try:
        response = requests.post(create_url, headers=headers, json=data)
        response.raise_for_status()
        print(f"Successfully created repository '{repo_name}' on GitHub.")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to GitHub: {e}")
        exit()
    except requests.exceptions.HTTPError as e:
        print(f"Error creating repository: {e.response.status_code} - {e.response.text}")
        exit()

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
        exit()

def upload_project_directory(github_username, github_token):
    """Handles the entire process of uploading/updating a project directory."""
    project_path, repo_name, repo_description, is_private = get_project_directory_input()
    initialize_git_repository(project_path)
    create_or_get_github_repository(repo_name, repo_description, is_private, github_username, github_token)
    push_to_github(repo_name, github_username, github_token)
    print(f"You can find your repository at: https://github.com/{github_username}/{repo_name}")

# ==============================================================================
# MAIN FUNCTION
# ==============================================================================

def main():
    """Main function to orchestrate the process."""
    print("GitHub Uploader Tool")
    print("--------------------")

    github_username = os.environ.get("GITHUB_USERNAME")
    if not github_username:
        github_username = input("Enter your GitHub username: ")
    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        github_token = getpass.getpass("Enter your GitHub Personal Access Token: ")

    print("\nWhat would you like to do?")
    print("1: Upload/update a whole project directory")
    print("2: Upload/update a single file")
    choice = input("Enter your choice (1 or 2): ")

    if choice == '1':
        upload_project_directory(github_username, github_token)
    elif choice == '2':
        upload_single_file(github_username, github_token)
    else:
        print("Invalid choice. Exiting.")
        exit()

    print("--------------------")
    print("Operation complete.")

if __name__ == "__main__":
    main()
