
import subprocess
import inquirer

def manage_tags(args):
    """Handle tag management operations."""
    action = args.action if hasattr(args, 'action') and args.action else None
    tag_name = args.tag_name if hasattr(args, 'tag_name') and args.tag_name else None
    message = args.message if hasattr(args, 'message') and args.message else None

    if not action:
        questions = [
            inquirer.List(
                "action",
                message="What tag operation would you like to perform?",
                choices=["list", "create", "delete"],
            )
        ]
        answers = inquirer.prompt(questions)
        action = answers["action"]

        if action in ["create", "delete"]:
            tag_questions = [
                inquirer.Text("tag_name", message=f"Enter the name of the tag to {action}")
            ]
            tag_answers = inquirer.prompt(tag_questions)
            tag_name = tag_answers["tag_name"]

        if action == "create":
            message_questions = [
                inquirer.Text("message", message="Enter an optional annotation message for the tag")
            ]
            message_answers = inquirer.prompt(message_questions)
            message = message_answers["message"]

    try:
        if action == "list":
            print("Listing all tags:")
            subprocess.run(["git", "tag"], check=True)
        elif action == "create":
            command = ["git", "tag"]
            if message:
                command.extend(["-a", tag_name, "-m", message])
            else:
                command.append(tag_name)
            print(f"Creating new tag: {tag_name}")
            subprocess.run(command, check=True)
        elif action == "delete":
            print(f"Deleting tag: {tag_name}")
            subprocess.run(["git", "tag", "-d", tag_name], check=True)
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while running a git command: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
