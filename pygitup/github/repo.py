
import inquirer
from .api import update_repo_visibility

def manage_repo_visibility(args, github_username, github_token):
    """Handle repository visibility changes."""
    repo_name = args.repo if hasattr(args, 'repo') and args.repo else None
    
    # Determine desired state from args
    target_private = None
    if hasattr(args, 'private') and args.private:
        target_private = True
    elif hasattr(args, 'public') and args.public:
        target_private = False

    # Interactive mode if info is missing
    if (not repo_name or target_private is None):
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
        
        if not repo_name:
            repo_name = answers["repo"]
        
        if target_private is None:
            target_private = answers["visibility"] == "Private"

    if not repo_name:
        print("Repository name is required.")
        return

    if target_private is None:
        print("You must specify --private or --public, or select an option.")
        return

    visibility_str = "PRIVATE" if target_private else "PUBLIC"
    print(f"Changing visibility of '{repo_name}' to {visibility_str}...")

    try:
        response = update_repo_visibility(github_username, repo_name, github_token, target_private)
        
        if response.status_code == 200:
            print(f"Successfully changed '{repo_name}' to {visibility_str}.")
        else:
            print(f"Failed to change visibility: {response.status_code} - {response.text}")
            print("Note: You need admin access to the repository to change its visibility.")
            
    except Exception as e:
        print(f"An error occurred: {e}")
