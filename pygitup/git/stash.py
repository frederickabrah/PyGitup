import subprocess
import inquirer
from ..utils.ui import print_success, print_error, print_info, print_header

def manage_stashes(args):
    """Handle stash management operations with styled output."""
    action = args.action if hasattr(args, 'action') and args.action else None
    message = args.message if hasattr(args, 'message') and args.message else None

    if not action:
        print_header("Stash Management")
        questions = [
            inquirer.List(
                "action",
                message="What stash operation would you like to perform?",
                choices=["save", "list", "apply", "pop", "drop"],
            )
        ]
        answers = inquirer.prompt(questions)
        action = answers["action"]

        if action == "save":
            stash_questions = [
                inquirer.Text("message", message="Enter an optional message for the stash")
            ]
            stash_answers = inquirer.prompt(stash_questions)
            message = stash_answers["message"]

    try:
        if action == "save":
            command = ["git", "stash", "save"]
            if message:
                command.append(message)
            print_info("Saving current changes to a new stash.")
            subprocess.run(command, check=True)
            print_success("Changes stashed.")
        elif action == "list":
            print_info("Listing all stashes:")
            subprocess.run(["git", "stash", "list"], check=True)
        elif action == "apply":
            print_info("Applying the latest stash.")
            subprocess.run(["git", "stash", "apply"], check=True)
            print_success("Stash applied.")
        elif action == "pop":
            print_info("Applying the latest stash and dropping it from the list.")
            subprocess.run(["git", "stash", "pop"], check=True)
            print_success("Stash popped.")
        elif action == "drop":
            print_info("Dropping the latest stash.")
            subprocess.run(["git", "stash", "drop"], check=True)
            print_success("Stash dropped.")
    except subprocess.CalledProcessError as e:
        print_error(f"Git command failed: {e}")
    except Exception as e:
        print_error(f"An unexpected error occurred: {e}")