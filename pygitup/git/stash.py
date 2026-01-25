
import subprocess
import inquirer

def manage_stashes(args):
    """Handle stash management operations."""
    action = args.action if hasattr(args, 'action') and args.action else None
    message = args.message if hasattr(args, 'message') and args.message else None

    if not action:
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
            print("Saving current changes to a new stash.")
            subprocess.run(command, check=True)
        elif action == "list":
            print("Listing all stashes:")
            subprocess.run(["git", "stash", "list"], check=True)
        elif action == "apply":
            print("Applying the latest stash.")
            subprocess.run(["git", "stash", "apply"], check=True)
        elif action == "pop":
            print("Applying the latest stash and dropping it from the list.")
            subprocess.run(["git", "stash", "pop"], check=True)
        elif action == "drop":
            print("Dropping the latest stash.")
            subprocess.run(["git", "stash", "drop"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while running a git command: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
