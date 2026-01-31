
import requests
import inquirer

from .api import get_github_headers
from ..utils.security import check_is_sensitive

def manage_gists(args, github_username, github_token):
    """Handle Gist management operations."""
    action = args.action if hasattr(args, 'action') and args.action else None
    filename = args.filename if hasattr(args, 'filename') and args.filename else None
    content = args.content if hasattr(args, 'content') and args.content else None
    description = args.description if hasattr(args, 'description') and args.description else None
    public = args.public if hasattr(args, 'public') and args.public else False

    if not action:
        questions = [
            inquirer.List(
                "action",
                message="What Gist operation would you like to perform?",
                choices=["create", "list"],
            )
        ]
        answers = inquirer.prompt(questions)
        action = answers["action"]

        if action == "create":
            gist_questions = [
                inquirer.Text("filename", message="Enter the filename for the Gist"),
                inquirer.Text("content", message="Enter the content of the Gist"),
                inquirer.Text("description", message="Enter an optional description for the Gist"),
                inquirer.Confirm("public", message="Make the Gist public?", default=False),
            ]
            gist_answers = inquirer.prompt(gist_questions)
            filename = gist_answers["filename"]
            content = gist_answers["content"]
            description = gist_answers["description"]
            public = gist_answers["public"]

    if action == "create":
        # Security check for Gist filename
        if check_is_sensitive(filename):
            print(f"\nWARNING: '{filename}' appears to be a sensitive filename pattern.")
            confirm = input("Are you sure you want to create this Gist? (y/n): ").lower()
            if confirm != 'y':
                print("Gist creation cancelled.")
                return

    headers = get_github_headers(github_token)

    try:
        if action == "create":
            data = {
                "description": description or "",
                "public": public,
                "files": {
                    filename: {
                        "content": content
                    }
                }
            }
            response = requests.post("https://api.github.com/gists", headers=headers, json=data)
            response.raise_for_status()
            gist_data = response.json()
            print("Gist created successfully!")
            print(f"View it here: {gist_data['html_url']}")

        elif action == "list":
            response = requests.get(f"https://api.github.com/users/{github_username}/gists", headers=headers)
            response.raise_for_status()
            gists = response.json()
            if gists:
                print("Your Gists:")
                for gist in gists:
                    gist_desc = gist['description'] or "No description"
                    print(f"- {gist['html_url']} ({gist_desc})")
            else:
                print("You don't have any Gists.")

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while communicating with the GitHub API: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
