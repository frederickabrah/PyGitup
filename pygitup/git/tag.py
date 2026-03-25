import subprocess
import questionary
from ..utils.ui import print_success, print_error, print_info, print_header

def manage_tags(args):
    """Handle tag management operations with styled output."""
    action = args.action if hasattr(args, 'action') and args.action else None
    tag_name = args.tag_name if hasattr(args, 'tag_name') and args.tag_name else None
    message = args.message if hasattr(args, 'message') and args.message else None

    if not action:
        print_header("Tag Management")
        action = questionary.select(
            "What tag operation would you like to perform?",
            choices=["list", "create", "delete"],
        ).ask()

        if action in ["create", "delete"]:
            tag_name = questionary.text(f"Enter the name of the tag to {action}").ask()

        if action == "create":
            message = questionary.text("Enter an optional annotation message for the tag").ask()

    try:
        if action == "list":
            print_info("Listing all tags:")
            subprocess.run(["git", "tag"], check=True)
        elif action == "create":
            if not tag_name:
                print_error("Tag name is required.")
                return
            command = ["git", "tag"]
            if message:
                command.extend(["-a", tag_name, "-m", message])
            else:
                command.append(tag_name)
            print_info(f"Creating new tag: {tag_name}")
            subprocess.run(command, check=True)
            print_success(f"Tag '{tag_name}' created.")
        elif action == "delete":
            if not tag_name:
                print_error("Tag name is required.")
                return
            print_info(f"Deleting tag: {tag_name}")
            subprocess.run(["git", "tag", "-d", tag_name], check=True)
            print_success(f"Tag '{tag_name}' deleted.")
    except subprocess.CalledProcessError as e:
        print_error(f"Git command failed: {e}")
    except Exception as e:
        print_error(f"An unexpected error occurred: {e}")