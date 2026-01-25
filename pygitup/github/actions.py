
import requests
import inquirer

from .api import get_github_headers

def manage_actions(args, github_username, github_token):
    """Handle GitHub Actions management operations."""
    action = args.action if hasattr(args, 'action') and args.action else None
    repo_name = args.repo if hasattr(args, 'repo') and args.repo else None
    workflow_id = args.workflow_id if hasattr(args, 'workflow_id') and args.workflow_id else None
    ref = args.ref if hasattr(args, 'ref') and args.ref else 'main'

    if not action:
        questions = [
            inquirer.List(
                "action",
                message="What Actions operation would you like to perform?",
                choices=["trigger", "monitor"],
            )
        ]
        answers = inquirer.prompt(questions)
        action = answers["action"]

        if not repo_name:
            repo_questions = [inquirer.Text("repo", message="Enter the repository name")]
            repo_answers = inquirer.prompt(repo_questions)
            repo_name = repo_answers["repo"]

        if action == "trigger":
            trigger_questions = [
                inquirer.Text("workflow_id", message="Enter the workflow ID (e.g., main.yml)"),
                inquirer.Text("ref", message="Enter the ref to trigger the workflow on", default="main"),
            ]
            trigger_answers = inquirer.prompt(trigger_questions)
            workflow_id = trigger_answers["workflow_id"]
            ref = trigger_answers["ref"]

    if not repo_name:
        print("Repository name is required for Actions operations.")
        return

    headers = get_github_headers(github_token)
    base_url = f"https://api.github.com/repos/{github_username}/{repo_name}/actions"

    try:
        if action == "trigger":
            url = f"{base_url}/workflows/{workflow_id}/dispatches"
            data = {"ref": ref}
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            print("Workflow triggered successfully!")

        elif action == "monitor":
            url = f"{base_url}/runs"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            runs = response.json()["workflow_runs"]
            if runs:
                print(f"Workflow runs for {repo_name}:")
                for run in runs:
                    print(f"- ID: {run['id']}, Status: {run['status']}, Conclusion: {run['conclusion']}")
            else:
                print(f"No workflow runs found for {repo_name}.")

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while communicating with the GitHub API: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
