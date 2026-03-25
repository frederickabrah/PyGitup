
import questionary
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
            repo_name = questionary.text("Enter the repository name").ask()
            if not repo_name: # Handle cancellation
                print_info("Operation cancelled.")
                return
        
        if target_private is None:
            visibility = questionary.select(
                "Select new visibility",
                choices=["Private", "Public"],
            ).ask()
            if visibility is None: # Handle cancellation
                print_info("Operation cancelled.")
                return
            target_private = visibility == "Private"

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
        repo_name = questionary.text("Enter the name of the repository to DELETE:").ask()
        if not repo_name: # Handle cancellation
            print_info("Operation cancelled.")
            return

    if not repo_name:
        print_error("Repository name is required.")
        return

    # Professional Danger Warning
    from rich.panel import Panel
    from rich.text import Text
    from ..utils.ui import console
    
    warning_text = Text.assemble(
        ("DANGER: ", "bold red"),
        (f"You are about to PERMANENTLY DELETE repository '", "white"),
        (f"{repo_name}", "bold yellow"),
        ("'", "white")
    )
    console.print(Panel(warning_text, border_style="red", title="⚠️  CRITICAL ACTION"))
    print_warning("This operation is irreversible and will remove all code, issues, and history.")
    
    print("\nStep 1: Security Verification")
    confirm_name = input(f"Type the repository name to confirm ('{repo_name}'): ").strip()
    
    if confirm_name != repo_name:
        print_info("Verification failed. Deletion cancelled.")
        return
    
    print("\nStep 2: Final Authorization")
    final = input("Type 'CONFIRM DELETE' to finalize: ").strip()
    if final != 'CONFIRM DELETE':
        print_info("Authorization aborted. Repository remains safe.")
        return

    print_info(f"Initiating technical deletion of '{repo_name}'...")
    
    try:
        response = delete_repo_api(github_username, repo_name, github_token)
        
        if response.status_code == 204:
            print_success(f"Successfully deleted repository '{repo_name}'.")
        else:
            print_error(f"Failed to delete repository: {response.status_code} - {response.text}")
            print_info("Note: You need 'delete_repo' scope in your token or admin access.")
            
    except Exception as e:
        print_error(f"An error occurred: {e}")

