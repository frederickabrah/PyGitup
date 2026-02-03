import inquirer
import os
import subprocess
import requests
import time
import zipfile
import io
from .api import github_request, toggle_workflow_api, get_repo_contents, get_workflow_run_logs
from ..utils.ui import print_success, print_error, print_info, print_header, print_warning, console, Panel
from ..utils.ai import generate_ai_workflow, analyze_failed_log

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
                
                # Context Gathering
                code_context = ""
                priority_files = ["main.py", "setup.py", "requirements.txt", "package.json", "Dockerfile"]
                for item in contents_list:
                    if item['name'] in priority_files and item['type'] == 'file':
                        f_resp = requests.get(item['download_url'])
                        if f_resp.status_code == 200:
                            snippet = "\n".join(f_resp.text.splitlines()[:150])
                            code_context += f"\n--- {item['name']} ---\n{snippet}\n"

                content = generate_ai_workflow(ai_key, repo_name, "\n".join(file_paths), code_context)
            
            if not content:
                print_error("AI generation failed. Falling back to standard.")
                choice = '1'

    if choice != '2':
        if os.path.exists("requirements.txt") or os.path.exists("setup.py"):
            content = PYTHON_WORKFLOW
        elif os.path.exists("package.json"):
            content = NODE_WORKFLOW
        else:
            content = PYTHON_WORKFLOW

    try:
        with open(workflow_path, 'w') as f:
            f.write(content)
        print_success(f"CI/CD Workflow generated at {workflow_path}")
    except Exception as e:
        print_error(f"Failed to write workflow file: {e}")
        return

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

def monitor_live_build(github_username, repo_name, github_token, config):
    """Refreshes build status every 10 seconds until completion."""
    print_header(f"Live Build Monitor: {repo_name}")
    ai_key = config["github"].get("ai_api_key")
    
    try:
        while True:
            url = f"https://api.github.com/repos/{github_username}/{repo_name}/actions/runs"
            run_resp = github_request("GET", url, github_token, params={"per_page": 1})
            runs = run_resp.json().get("workflow_runs", [])
            
            if not runs:
                print_info("No runs found. Waiting...")
                time.sleep(10)
                continue
                
            run = runs[0]
            status = run['status']
            conclusion = run['conclusion']
            
            icon = "⏳" if status != "completed" else "🟢" if conclusion == "success" else "🔴"
            
            # Use os.system directly for cleaner refresh
            import os
            os.system('cls' if os.name == 'nt' else 'clear')
            print_header(f"Live Monitor: {repo_name}")
            print(f"\n[bold]Current Run:[/bold] {run['name']}")
            print(f"ID: {run['id']} | Branch: {run['head_branch']}")
            print(f"Status: {icon} [bold]{status.upper()}[/bold]")
            
            if status == "completed":
                print_success(f"Build finished with conclusion: {conclusion}")
                if conclusion == "failure" and ai_key:
                    choice = input("\nWould you like AI to debug this failure? (y/n): ").lower()
                    if choice == 'y':
                        debug_build_failure(github_username, repo_name, run['id'], github_token, ai_key)
                break
                
            print_info("\nRefreshing in 10s... (Ctrl+C to stop)")
            time.sleep(10)
    except KeyboardInterrupt:
        print_info("\nMonitoring stopped.")

def debug_build_failure(username, repo, run_id, token, ai_key):
    """Downloads failed build logs and uses AI to explain the error."""
    print_info("📡 Downloading build logs...")
    log_resp = get_workflow_run_logs(username, repo, token, run_id)
    
    if log_resp.status_code == 200:
        try:
            with zipfile.ZipFile(io.BytesIO(log_resp.content)) as z:
                combined_logs = ""
                for filename in z.namelist():
                    with z.open(filename) as f:
                        combined_logs += f.read().decode('utf-8', errors='ignore')
                
                print_info("🤖 AI is analyzing logs for the root cause...")
                analysis = analyze_failed_log(ai_key, combined_logs)
                if analysis:
                    console.print(Panel(analysis, title="AI Debugging Report", border_style="red"))
                else:
                    print_error("AI could not analyze the logs.")
        except Exception as e:
            print_error(f"Failed to process log zip: {e}")
    else:
        print_error(f"Failed to download logs: {log_resp.status_code}")

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
                choices=["Generate CI/CD Workflow", "Watch Live Build", "Monitor Status & Metrics", "Trigger Workflow", "Enable Workflow", "Disable Workflow"],
            )
        ]
        answers = inquirer.prompt(questions)
        if not answers: return
        action = answers["action"]

    if not repo_name:
        repo_name = inquirer.prompt([inquirer.Text("repo", message="Enter the repository name")])["repo"]

    if action == "Generate CI/CD Workflow":
        setup_cicd_workflow(github_username, github_token, repo_name, config)
    elif action == "Watch Live Build":
        monitor_live_build(github_username, repo_name, github_token, config)
    elif action == "Monitor Status & Metrics":
        print_info(f"Fetching execution metrics for {repo_name}...")
        url = f"https://api.github.com/repos/{github_username}/{repo_name}/actions/runs"
        run_resp = github_request("GET", url, github_token, params={"per_page": 10})
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

    elif action == "Trigger Workflow":
        base_url = f"https://api.github.com/repos/{github_username}/{repo_name}/actions"
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

    elif "Workflow" in action:
        enable = "Enable" in action
        base_url = f"https://api.github.com/repos/{github_username}/{repo_name}/actions"
        w_resp = github_request("GET", f"{base_url}/workflows", github_token)
        workflows = w_resp.json().get("workflows", [])
        choices = [(w['name'], w['id']) for w in workflows]
        w_choice = inquirer.prompt([inquirer.List("w", message=f"Select workflow to {action.lower()}", choices=choices)])["w"]
        toggle_workflow_api(github_username, repo_name, github_token, w_choice, enable=enable)
        print_success(f"Workflow {action.lower()}d successfully.")