import subprocess
import questionary
from ..utils.ui import print_success, print_error, print_info, print_header

def manage_branches(args):
    """Handle branch management operations with styled output."""
    action = args.action if hasattr(args, 'action') and args.action else None
    branch_name = args.branch_name if hasattr(args, 'branch_name') and args.branch_name else None

    if not action:
        print_header("Branch Management")
        action = questionary.select(
            "What branch operation would you like to perform?",
            choices=["list", "create", "delete", "switch"],
        ).ask()
        if not action:
            print_info("Operation cancelled.")
            return

        if action in ["create", "delete", "switch"]:
            branch_name = questionary.text(f"Enter the name of the branch to {action}").ask()
            if not branch_name:
                print_info("Operation cancelled.")
                return

    try:
        if action == "list":
            print_info("Listing all local branches:")
            subprocess.run(["git", "branch"], check=True)
        elif action == "create":
            if not branch_name:
                print_error("Branch name is required.")
                return
            print_info(f"Creating new branch: {branch_name}")
            subprocess.run(["git", "branch", branch_name], check=True)
            print_success(f"Branch '{branch_name}' created.")
        elif action == "delete":
            if not branch_name:
                print_error("Branch name is required.")
                return
            print_info(f"Deleting branch: {branch_name}")
            subprocess.run(["git", "branch", "-d", branch_name], check=True)
            print_success(f"Branch '{branch_name}' deleted.")
        elif action == "switch":
            if not branch_name:
                print_error("Branch name is required.")
                return
            print_info(f"Switching to branch: {branch_name}")
            subprocess.run(["git", "checkout", branch_name], check=True)
            print_success(f"Switched to branch '{branch_name}'.")
    except subprocess.CalledProcessError as e:
        print_error(f"Git command failed: {e}")
    except Exception as e:
        print_error(f"An unexpected error occurred: {e}")