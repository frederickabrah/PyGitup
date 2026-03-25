import questionary
from .api import github_request
from ..utils.ui import print_success, print_error, print_info, print_header

def manage_webhooks(args, github_username, github_token):
    """Handle webhook management operations with rate-limiting support."""
    action = args.action if hasattr(args, 'action') and args.action else None
    repo_name = args.repo if hasattr(args, 'repo') and args.repo else None
    hook_id = args.hook_id if hasattr(args, 'hook_id') and args.hook_id else None
    url = args.url if hasattr(args, 'url') and args.url else None
    events = args.events if hasattr(args, 'events') and args.events else ['push']

    if not action:
        print_header("Webhook Management")
        action = questionary.select(
            "What webhook operation would you like to perform?",
            choices=["list", "create", "delete"]
        ).ask()
        
        if not action:
            print_info("Operation cancelled.")
            return

        if not repo_name:
            repo_name = questionary.text("Enter the repository name:").ask()
            if not repo_name:
                print_info("Operation cancelled.")
                return

        if action == "create":
            url = questionary.text("Enter the webhook URL:").ask()
            events_str = questionary.text("Enter events to subscribe to (comma-separated):", default="push").ask()
            if not url or not events_str:
                print_info("Operation cancelled.")
                return
            events = [e.strip() for e in events_str.split(",")]

        elif action == "delete":
            hook_id = questionary.text("Enter the ID of the webhook to delete:").ask()
            if not hook_id:
                print_info("Operation cancelled.")
                return

    if not repo_name:
        print_error("Repository name is required for webhook operations.")
        return

    base_url = f"https://api.github.com/repos/{github_username}/{repo_name}/hooks"

    try:
        if action == "list":
            response = github_request("GET", base_url, github_token)
            response.raise_for_status()
            hooks = response.json()
            if hooks:
                print_info(f"Webhooks for {repo_name}:")
                for hook in hooks:
                    print(f"- ID: {hook['id']}, URL: {hook['config']['url']}, Events: {hook['events']}")
            else:
                print_info(f"No webhooks found for {repo_name}.")

        elif action == "create":
            data = {
                "name": "web",
                "active": True,
                "events": events,
                "config": {
                    "url": url,
                    "content_type": "json"
                }
            }
            response = github_request("POST", base_url, github_token, json=data)
            response.raise_for_status()
            print_success("Webhook created successfully!")

        elif action == "delete":
            if not hook_id:
                print_error("Hook ID is required for deletion.")
                return
            delete_url = f"{base_url}/{hook_id}"
            response = github_request("DELETE", delete_url, github_token)
            response.raise_for_status()
            print_success("Webhook deleted successfully!")

    except Exception as e:
        print_error(f"Webhook operation failed: {e}")