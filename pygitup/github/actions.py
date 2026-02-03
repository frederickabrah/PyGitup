import inquirer
import os
import subprocess
import requests
from .api import github_request, toggle_workflow_api, get_repo_contents
from ..utils.ui import print_success, print_error, print_info, print_header, print_warning
from ..utils.ai import generate_ai_workflow

PYTHON_WORKFLOW = """name: Python CI

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
    - name: Lint with Ruff
      run: |
        pip install ruff
        ruff check .
    - name: Test with pytest
      run: |
        pip install pytest
        pytest
"""

NODE_WORKFLOW = """name: Node.js CI

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Use Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18.x'
    - run: npm install
    - run: npm run build --if-present
    - run: npm test
"""

def setup_cicd_workflow(github_username, github_token, repo_name, config):
    """Automated CI/CD Pipeline Generator with AI support."""
    print_header("CI/CD Pipeline Architect")
    
    workflow_path = ".github/workflows/main.yml"
    os.makedirs(".github/workflows", exist_ok=True)
    
    print("\n[bold]Pipeline Generation Mode:[/bold]")
    print("1: [green]Standard Template (Python/Node)[/green]")
    print("2: [cyan]AI DevOps Architect (Custom Tailored)[/cyan]")
    
    choice = input("\n👉 Choice (1/2) [1]: ")
    
    content = ""
    if choice == '2':
        ai_key = config["github"].get("ai_api_key")
        if not ai_key:
            print_error("Gemini API Key missing. Falling back to Standard.")
            choice = '1'
        else:
            print_info("🤖 AI is reading your code to architect a custom pipeline...")
            repo_resp = get_repo_contents(github_username, repo_name, github_token)
            if repo_resp.status_code == 200:
                contents_list = repo_resp.json()
                file_paths = [item['path'] for item in contents_list]
                
                # Context Gathering: Read entries & configs
                code_context = ""
                priority_files = ["main.py", "setup.py", "requirements.txt", "package.json", "Dockerfile"]
                for item in contents_list:
                    if item['name'] in priority_files and item['type'] == 'file':
                        print_info(f"   📄 Analyzing {item['name']}...")
                        f_resp = requests.get(item['download_url'])
                        if f_resp.status_code == 200:
                            snippet = "\n".join(f_resp.text.splitlines()[:150])
                            code_context += f"\n--- {item['name']} ---\n{snippet}\n"

                content = generate_ai_workflow(ai_key, repo_name, "\n".join(file_paths), code_context)
            
            if not content:
                print_error("AI generation failed. Falling back to standard.")
                choice = '1'

    if choice != '2':
        # Standard Detection
        if os.path.exists("requirements.txt") or os.path.exists("setup.py"):
            print_success("Standard: Python CI Selected")
            content = PYTHON_WORKFLOW
        elif os.path.exists("package.json"):
            print_success("Standard: Node.js CI Selected")
            content = NODE_WORKFLOW
        else:
            print_warning("No config files found. Defaulting to Python template.")
            content = PYTHON_WORKFLOW

    # Creation
    try:
        with open(workflow_path, 'w') as f:
            f.write(content)
        print_success(f"CI/CD Workflow generated at {workflow_path}")
    except Exception as e:
        print_error(f"Failed to write workflow file: {e}")
        return

    # Deployment
    if os.path.isdir(".git"):
        push = input("\nWould you like to push this pipeline to GitHub now? (y/n): ").lower()
        if push == 'y':
            try:
                subprocess.run(["git", "add", workflow_path], check=True)
                subprocess.run(["git", "commit", "-m", "ci: implement automated pipeline via PyGitUp AI"], check=True)
                subprocess.run(["git", "push"], check=True)
                print_success("Pipeline is live on GitHub! 🚀")
            except Exception as e:
                print_error(f"Failed to push pipeline: {e}")

def manage_actions(args, github_username, github_token, config):
    """Advanced GitHub Actions Control Center."""
    action = args.action if hasattr(args, 'action') and args.action else None
    repo_name = args.repo if hasattr(args, 'repo') and args.repo else None

    if not action:
        print_header("CI/CD Control Center")
        questions = [
            inquirer.List(
                "action",
                message="Select an Actions operation",
                choices=["Generate CI/CD Workflow", "Trigger Workflow", "Monitor Status & Metrics", "Enable Workflow", "Disable Workflow"],
            )
        ]
        answers = inquirer.prompt(questions)
        if not answers: return
        action = answers["action"]

    if not repo_name:
        repo_name = inquirer.prompt([inquirer.Text("repo", message="Enter the repository name")])["repo"]

    if action == "Generate CI/CD Workflow":
        setup_cicd_workflow(github_username, github_token, repo_name, config)
        return

    base_url = f"https://api.github.com/repos/{github_username}/{repo_name}/actions"

    try:
        if action == "Trigger Workflow":
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
