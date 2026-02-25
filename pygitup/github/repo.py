
import inquirer
from .api import update_repo_visibility, delete_repo_api
from ..utils.ui import print_success, print_error, print_info, print_header, print_warning

def manage_repo_visibility(args, github_username, github_token):
    """Handle repository visibility changes with styled output."""
    repo_name = args.repo if hasattr(args, 'repo') and args.repo else None
    
    # Determine desired state from args
    target_private = None
    if hasattr(args, 'private') and args.private:
        target_private = True
    elif hasattr(args, 'public') and args.public:
        target_private = False

    # Interactive mode if info is missing
    if (not repo_name or target_private is None):
        print_header("Repository Visibility")
        questions = []
        if not repo_name:
            questions.append(inquirer.Text("repo", message="Enter the repository name"))
        
        if target_private is None:
            questions.append(inquirer.List(
                "visibility",
                message="Select new visibility",
                choices=["Private", "Public"],
            ))
            
        answers = inquirer.prompt(questions)
        if not answers:
            print_info("Operation cancelled.")
            return
        
        if not repo_name:
            repo_name = answers["repo"]
        
        if target_private is None:
            target_private = answers["visibility"] == "Private"

    if not repo_name:
        print_error("Repository name is required.")
        return

    if target_private is None:
        print_error("You must specify --private or --public, or select an option.")
        return

    visibility_str = "PRIVATE" if target_private else "PUBLIC"
    print_info(f"Changing visibility of '{repo_name}' to {visibility_str}...")

    try:
        response = update_repo_visibility(github_username, repo_name, github_token, target_private)
        
        if response.status_code == 200:
            print_success(f"Successfully changed '{repo_name}' to {visibility_str}.")
        else:
            print_error(f"Failed to change visibility: {response.status_code} - {response.text}")
            print_info("Note: You need admin access to the repository to change its visibility.")
            
    except Exception as e:
        print_error(f"An error occurred: {e}")

def delete_repository(args, github_username, github_token):
    """Delete a GitHub repository with safety confirmation and styled output."""
    repo_name = args.repo if hasattr(args, 'repo') and args.repo else None

    if not repo_name:
        print_header("Delete Repository")
        questions = [inquirer.Text("repo", message="Enter the name of the repository to DELETE")]
        answers = inquirer.prompt(questions)
        if not answers:
            print_info("Operation cancelled.")
            return
        repo_name = answers["repo"]

    if not repo_name:
        print_error("Repository name is required.")
        return

    print("\n" + "!" * 50)
    print_error(f"DANGER: You are about to PERMANENTLY DELETE '{repo_name}'")
    print("!" * 50 + "\n")
    
    confirmation = input(f"To confirm, type '{repo_name}': ")
    
    if confirmation != repo_name:
        print_warning("Verification failed. Repository deletion cancelled.")
        return

    print_info(f"Deleting repository '{repo_name}'...")
    
    try:
        response = delete_repo_api(github_username, repo_name, github_token)
        
        if response.status_code == 204:
            print_success(f"Successfully deleted repository '{repo_name}'.")
        else:
            print_error(f"Failed to delete repository: {response.status_code} - {response.text}")
            print_info("Note: You need 'delete_repo' scope in your token or admin access.")
            
    except Exception as e:
        print_error(f"An error occurred: {e}")
