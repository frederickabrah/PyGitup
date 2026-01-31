import inquirer
from .api import github_request, toggle_workflow_api
from ..utils.ui import print_success, print_error, print_info, print_header

def manage_actions(args, github_username, github_token):
    """Advanced GitHub Actions Control Center."""
    action = args.action if hasattr(args, 'action') and args.action else None
    repo_name = args.repo if hasattr(args, 'repo') and args.repo else None

    if not action:
        print_header("CI/CD Control Center")
        questions = [
            inquirer.List(
                "action",
                message="Select an Actions operation",
                choices=["Trigger Workflow", "Monitor Status & Metrics", "Enable Workflow", "Disable Workflow"],
            )
        ]
        answers = inquirer.prompt(questions)
        action = answers["action"]

    if not repo_name:
        repo_name = inquirer.prompt([inquirer.Text("repo", message="Enter the repository name")])["repo"]

    base_url = f"https://api.github.com/repos/{github_username}/{repo_name}/actions"

    try:
        if action == "Trigger Workflow":
            # List workflows first to let user choose
            w_resp = github_request("GET", f"{base_url}/workflows", github_token)
            workflows = w_resp.json().get("workflows", [])
            if not workflows:
                print_error("No workflows found.")
                return
            
            choices = [(w['name'], w['id']) for w in workflows]
            w_choice = inquirer.prompt([inquirer.List("w", message="Select workflow to trigger", choices=choices)])["w"]
            ref = input("Enter ref (branch/tag) [main]: ") or "main"
            
            trigger_url = f"{base_url}/workflows/{w_choice}/dispatches"
            github_request("POST", trigger_url, github_token, json={"ref": ref})
            print_success(f"Successfully triggered workflow run on {ref}")

        elif action == "Monitor Status & Metrics":
            print_info(f"Fetching execution metrics for {repo_name}...")
            run_resp = github_request("GET", f"{base_url}/runs", github_token, params={"per_page": 10})
            runs = run_resp.json().get("workflow_runs", [])
            
            if not runs:
                print_info("No recent runs found.")
                return

            print("\n[bold]Recent Workflow Runs & Metrics:[/bold]")
            success_count = 0
            from datetime import datetime
            for run in runs:
                status_icon = "🟢" if run['conclusion'] == "success" else "🔴" if run['conclusion'] == "failure" else "⏳"
                if run['conclusion'] == "success": success_count += 1
                
                duration_str = "N/A"
                if run.get('updated_at') and run.get('run_started_at'):
                    start = datetime.fromisoformat(run['run_started_at'].replace('Z', '+00:00'))
                    end = datetime.fromisoformat(run['updated_at'].replace('Z', '+00:00'))
                    diff = end - start
                    minutes, seconds = divmod(diff.total_seconds(), 60)
                    duration_str = f"{int(minutes)}m {int(seconds)}s"

                print(f"{status_icon} ID: {run['id']} | {run['name']} | Time: {duration_str} | Result: {run['conclusion']}")
            
            success_rate = (success_count / len(runs)) * 100
            print(f"\n[bold cyan]Success Rate (Last 10): {success_rate:.0f}%[/bold cyan]")

        elif "Workflow" in action:
            enable = "Enable" in action
            w_resp = github_request("GET", f"{base_url}/workflows", github_token)
            workflows = w_resp.json().get("workflows", [])
            choices = [(w['name'], w['id']) for w in workflows]
            w_choice = inquirer.prompt([inquirer.List("w", message=f"Select workflow to {action.lower()}", choices=choices)])["w"]
            
            toggle_workflow_api(github_username, repo_name, github_token, w_choice, enable=enable)
            print_success(f"Workflow {action.lower()}d successfully.")

    except Exception as e:
        print_error(f"Actions operation failed: {e}")