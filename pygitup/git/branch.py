
import subprocess
import inquirer

def manage_branches(args):
    """Handle branch management operations."""
    action = args.action if hasattr(args, 'action') and args.action else None
    branch_name = args.branch_name if hasattr(args, 'branch_name') and args.branch_name else None

    if not action:
        questions = [
            inquirer.List(
                "action",
                message="What branch operation would you like to perform?",
                choices=["list", "create", "delete", "switch"],
            )
        ]
        answers = inquirer.prompt(questions)
        action = answers["action"]

        if action in ["create", "delete", "switch"]:
            branch_questions = [
                inquirer.Text("branch_name", message=f"Enter the name of the branch to {action}")
            ]
            branch_answers = inquirer.prompt(branch_questions)
            branch_name = branch_answers["branch_name"]

    try:
        if action == "list":
            print("Listing all local branches:")
            subprocess.run(["git", "branch"], check=True)
        elif action == "create":
            print(f"Creating new branch: {branch_name}")
            subprocess.run(["git", "branch", branch_name], check=True)
        elif action == "delete":
            print(f"Deleting branch: {branch_name}")
            subprocess.run(["git", "branch", "-d", branch_name], check=True)
        elif action == "switch":
            print(f"Switching to branch: {branch_name}")
            subprocess.run(["git", "checkout", branch_name], check=True)
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while running a git command: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
