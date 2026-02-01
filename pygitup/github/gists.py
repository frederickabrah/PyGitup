import inquirer
from .api import github_request
from ..utils.security import check_is_sensitive
from ..utils.ui import print_success, print_error, print_info, print_header, print_warning

def manage_gists(args, github_username, github_token):
    """Handle Gist management operations with rate-limiting support."""
    action = args.action if hasattr(args, 'action') and args.action else None
    filename = args.filename if hasattr(args, 'filename') and args.filename else None
    content = args.content if hasattr(args, 'content') and args.content else None
    description = args.description if hasattr(args, 'description') and args.description else None
    public = args.public if hasattr(args, 'public') and args.public else False

    if not action:
        print_header("Gist Management")
        questions = [
            inquirer.List(
                "action",
                message="What Gist operation would you like to perform?",
                choices=["create", "list"],
            )
        ]
        answers = inquirer.prompt(questions)
        if not answers:
            print_info("Operation cancelled.")
            return
        action = answers["action"]

        if action == "create":
            gist_questions = [
                inquirer.Text("filename", message="Enter the filename for the Gist"),
                inquirer.Text("content", message="Enter the content of the Gist"),
                inquirer.Text("description", message="Enter an optional description for the Gist"),
                inquirer.Confirm("public", message="Make the Gist public?", default=False),
            ]
            gist_answers = inquirer.prompt(gist_questions)
            if not gist_answers:
                print_info("Operation cancelled.")
                return
            filename = gist_answers["filename"]
            content = gist_answers["content"]
            description = gist_answers["description"]
            public = gist_answers["public"]

    try:
        if action == "create":
            # Security check for Gist content/filename
            if check_is_sensitive(filename):
                print_warning(f"'{filename}' appears to be a sensitive filename pattern.")
                confirm = input("Are you sure you want to create this Gist? (y/n): ").lower()
                if confirm != 'y':
                    print_info("Gist creation cancelled.")
                    return

            data = {
                "description": description or "",
                "public": public,
                "files": {
                    filename: {
                        "content": content
                    }
                }
            }
            response = github_request("POST", "https://api.github.com/gists", github_token, json=data)
            response.raise_for_status()
            gist_data = response.json()
            print_success("Gist created successfully!")
            print_info(f"View it here: {gist_data['html_url']}")

        elif action == "list":
            url = f"https://api.github.com/users/{github_username}/gists"
            response = github_request("GET", url, github_token)
            response.raise_for_status()
            gists = response.json()
            if gists:
                print_info("Your Gists:")
                for gist in gists:
                    gist_desc = gist['description'] or "No description"
                    print(f"- {gist['html_url']} ({gist_desc})")
            else:
                print_info("You don't have any Gists.")

    except Exception as e:
        print_error(f"Gist operation failed: {e}")