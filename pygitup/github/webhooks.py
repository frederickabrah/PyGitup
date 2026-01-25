
import requests
import inquirer

from .api import get_github_headers

def manage_webhooks(args, github_username, github_token):
    """Handle webhook management operations."""
    action = args.action if hasattr(args, 'action') and args.action else None
    repo_name = args.repo if hasattr(args, 'repo') and args.repo else None
    hook_id = args.hook_id if hasattr(args, 'hook_id') and args.hook_id else None
    url = args.url if hasattr(args, 'url') and args.url else None
    events = args.events if hasattr(args, 'events') and args.events else ['push']

    if not action:
        questions = [
            inquirer.List(
                "action",
                message="What webhook operation would you like to perform?",
                choices=["list", "create", "delete"],
            )
        ]
        answers = inquirer.prompt(questions)
        action = answers["action"]

        if not repo_name:
            repo_questions = [inquirer.Text("repo", message="Enter the repository name")]
            repo_answers = inquirer.prompt(repo_questions)
            repo_name = repo_answers["repo"]

        if action == "create":
            webhook_questions = [
                inquirer.Text("url", message="Enter the webhook URL"),
                inquirer.Text("events", message="Enter events to subscribe to (comma-separated)", default="push"),
            ]
            webhook_answers = inquirer.prompt(webhook_questions)
            url = webhook_answers["url"]
            events = [e.strip() for e in webhook_answers["events"].split(",")]

        elif action == "delete":
            hook_id_questions = [inquirer.Text("hook_id", message="Enter the ID of the webhook to delete")]
            hook_id_answers = inquirer.prompt(hook_id_questions)
            hook_id = hook_id_answers["hook_id"]

    if not repo_name:
        print("Repository name is required for webhook operations.")
        return

    headers = get_github_headers(github_token)
    base_url = f"https://api.github.com/repos/{github_username}/{repo_name}/hooks"

    try:
        if action == "list":
            response = requests.get(base_url, headers=headers)
            response.raise_for_status()
            hooks = response.json()
            if hooks:
                print(f"Webhooks for {repo_name}:")
                for hook in hooks:
                    print(f"- ID: {hook['id']}, URL: {hook['config']['url']}, Events: {hook['events']}")
            else:
                print(f"No webhooks found for {repo_name}.")

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
            response = requests.post(base_url, headers=headers, json=data)
            response.raise_for_status()
            print("Webhook created successfully!")

        elif action == "delete":
            delete_url = f"{base_url}/{hook_id}"
            response = requests.delete(delete_url, headers=headers)
            response.raise_for_status()
            print("Webhook deleted successfully!")

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while communicating with the GitHub API: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
