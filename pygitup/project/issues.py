import glob
import re
import os
import subprocess
import hashlib
from ..github.api import create_issue, get_issues, search_user_by_email
from ..utils.ui import print_success, print_error, print_info, print_warning
from ..utils.ai import suggest_todo_fix

def get_git_author(file_path, line_num):
    """Extracts the author's email for a specific line using git blame."""
    try:
        # porcelain format is easier to parse programmatically
        cmd = ["git", "blame", "-L", f"{line_num},{line_num}", "--porcelain", file_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        for line in result.stdout.splitlines():
            if line.startswith("author-mail "):
                return line.replace("author-mail <", "").replace(">", "").strip()
    except Exception:
        return None
    return None

def get_code_context(file_path, line_num, window=3):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            start = max(0, line_num - window - 1)
            end = min(len(lines), line_num + window)
            snippet = "".join(lines[start:end])
            return f"```python\n{snippet}\n```"
    except Exception:
        return "Context unavailable."

def scan_todos(github_username, github_token, config, args=None):
    if args and args.dry_run:
        print_info("*** Dry Run Mode: Scanning but not creating issues. ***")

    if args and args.repo:
        repo_name = args.repo
    else:
        repo_name = input("Enter repository name: ")

    pattern_input = args.pattern if args and args.pattern else input("Enter file patterns (e.g., *.py,*.js) [*.py]: ")
    file_patterns = pattern_input.split(",") if pattern_input else ["*.py"]

    # Fetch existing issues to avoid duplicates
    print_info("Checking existing issues to prevent duplicates...")
    existing_titles = []
    try:
        issue_resp = get_issues(github_username, repo_name, github_token, state='all')
        if issue_resp.status_code == 401:
            print_error("Authentication failed (401). Please check your GitHub token.")
            print_info("Run Option 14 to reconfigure your credentials.")
            return
        elif issue_resp.status_code == 404:
            print_error(f"Repository '{repo_name}' not found or you don't have access.")
            return
        elif issue_resp.status_code == 200:
            existing_titles = [i['title'] for i in issue_resp.json()]
    except Exception as e:
        print_warning(f"Could not fetch existing issues: {e}")

    found_todos = []
    for pattern in file_patterns:
        # Clean pattern for glob
        clean_pattern = pattern.strip()
        for file_path in glob.glob(clean_pattern, recursive=True):
            if os.path.isfile(file_path) and ".git" not in file_path:
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        for line_num, line in enumerate(f, 1):
                                match = re.search(r'#\s*(?:TODO|FIXME|HACK):\s*(.*)', line, re.IGNORECASE)
                                if match:
                                    comment = match.group(1).strip()
                                    author = get_git_author(file_path, line_num)
                                    context = get_code_context(file_path, line_num)
                                    found_todos.append({
                                        "file": file_path,
                                        "line": line_num,
                                        "comment": comment,
                                        "author": author,
                                        "context": context
                                    })
                except Exception as e:
                    print_warning(f"Skipping {file_path}: {e}")

    if not found_todos:
        return

    
    created_count = 0
    for todo in found_todos:
        title = f"[{todo['file']}:{todo['line']}] {todo['comment'][:50]}"
        if len(todo['comment']) > 50: title += "..."
        
        if title in existing_titles:
            print_warning(f"Skipping duplicate issue: {title}")
            continue

        body = f"### Description\n{todo['comment']}\n\n"
        body += f"### Location\n- **File:** `{todo['file']}`\n- **Line:** {todo['line']}\n"
        if todo['author']:
            body += f"- **Blame:** {todo['author']}\n"
        
        body += f"\n### Context\n{todo['context']}\n\n"
        
        # AI: Suggest Fix
        ai_key = config["github"].get("ai_api_key")
        if ai_key:
            print_info(f"🤖 AI is suggesting a fix for: {title}")
            fix_suggestion = suggest_todo_fix(ai_key, todo['comment'], todo['context'])
            if fix_suggestion:
                body += f"### 💡 AI-Suggested Fix\n{fix_suggestion}\n\n"

        body += "_Generated automatically by PyGitUp Smart Issue engine._"

        if args and args.dry_run:
            print(f"[DRY-RUN] Would create issue: {title}")
            created_count += 1
            continue

        # Real-Time Identity Resolution: Map email to actual GitHub username
        resolved_assignees = [name.strip() for name in args.assign.split(",")] if args and args.assign else []
        if todo['author']:
            user_resp = search_user_by_email(todo['author'], github_token)
            if user_resp.status_code == 200:
                items = user_resp.json().get('items', [])
                if items:
                    gh_username = items[0]['login']
                    if gh_username not in resolved_assignees:
                        resolved_assignees.append(gh_username)
                        print_info(f"Resolved author email {todo['author']} to @{gh_username}")

        response = create_issue(github_username, repo_name, github_token, title, body, resolved_assignees)
        if response.status_code == 201:
            print_success(f"Created issue: {title}")
            created_count += 1
        elif response.status_code == 401:
            print_error("Authentication failed (401). Please check your GitHub token.")
            print_info("Run Option 14 to reconfigure your credentials.")
            return
        elif response.status_code == 404:
            print_error(f"Repository '{repo_name}' not found.")
        else:
            print_error(f"Failed to create issue '{title}': {response.status_code}")

    print_success(f"Operation complete. {created_count} new issues processed.")

def list_and_triage_issues(github_username, github_token, config, args=None):
    """Fetch remote issues and use AI to suggest fixes for triage."""
    from ..github.api import get_issues
    from ..utils.ui import console, Table, box, Panel
    from ..utils.ai import call_gemini_api
    
    if args and args.repo:
        repo_name = args.repo
    else:
        repo_name = input("Enter repository name: ")

    print_info(f"Fetching open issues for {repo_name}...")

    try:
        resp = get_issues(github_username, repo_name, github_token, state='open')
        if resp.status_code == 401:
            print_error("Authentication failed (401). Please check your GitHub token.")
            print_info("Run Option 14 to reconfigure your credentials.")
            return
        elif resp.status_code == 404:
            print_error(f"Repository '{repo_name}' not found or you don't have access.")
            return
        elif resp.status_code != 200:
            print_error(f"Failed to fetch issues: {resp.status_code}")
            return

        issues = resp.json()
        if not issues:
            print_info("No open issues found.")
            return
            
        table = Table(title=f"Open Issues: {repo_name}", box=box.ROUNDED)
        table.add_column("ID", style="cyan")
        table.add_column("Title", style="white")
        table.add_column("Author", style="dim")
        
        for i in issues[:10]: # Triage top 10
            table.add_row(str(i['number']), i['title'], i['user']['login'])
            
        console.print(table)
        
        target = input("\nEnter Issue ID to Triage (or 'q' to back): ")
        if target.lower() == 'q': return
        
        issue = next((i for i in issues if str(i['number']) == target), None)
        if not issue:
            print_error("Issue not found.")
            return
            
        print_info(f"Analyzing Issue #{target}...")

        ai_key = config["github"].get("ai_api_key")
        if ai_key:
            # Check if issue has body/content
            issue_body = issue.get('body', '') or 'No description provided.'
            issue_title = issue.get('title', 'Untitled')
            
            prompt = f"""Analyze this GitHub Issue and suggest a technical fix strategy.

TITLE: {issue_title}
BODY: {issue_body}

Provide a step-by-step resolution plan and example code if possible.
"""
            try:
                print_info("Sending to AI for analysis...")
                if os.environ.get('PYGITUP_DEBUG'):
                    print(f"[DEBUG] Prompt length: {len(prompt)}")
                    print(f"[DEBUG] Prompt preview: {prompt[:200]}...")
                
                analysis = call_gemini_api(ai_key, prompt)
                
                if os.environ.get('PYGITUP_DEBUG'):
                    print(f"[DEBUG] AI response length: {len(analysis) if analysis else 0}")
                    if analysis:
                        print(f"[DEBUG] AI response preview: {analysis[:200]}...")
                
                if analysis and len(analysis.strip()) > 0:
                    console.print(Panel(analysis, title=f"AI Triage Report: Issue #{target}", border_style="green"))
                else:
                    print_warning("AI returned empty response.")
                    print_info("This could be due to: 1) Rate limiting, 2) Invalid prompt, 3) API temporarily unavailable")
            except Exception as e:
                print_error(f"AI Analysis failed: {e}")
                if os.environ.get('PYGITUP_DEBUG'):
                    import traceback
                    traceback.print_exc()
        else:
            print_warning("AI API Key not configured for triage.")
            print_info("Configure it in Option 14 (Configuration Wizard)")
            
    except Exception as e:
        print_error(f"Triage failed: {e}")
