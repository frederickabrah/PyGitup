import glob
import re
import os
import subprocess
import hashlib
from ..github.api import create_issue, get_issues
from ..utils.ui import print_success, print_error, print_info, print_warning

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
    """Grabs a few lines of code around the TODO for better issue context."""
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
    """Advanced TODO scanner with Git Blame and Context support."""
    if args and args.dry_run:
        print_info("*** Dry Run Mode: Scanning but not creating issues. ***")

    if args and args.repo:
        repo_name = args.repo
    else:
        repo_name = input("Enter repository name: ")
    
    pattern_input = args.pattern if args and args.pattern else input("Enter file patterns (e.g., *.py,*.js) [*.py]: ")
    file_patterns = pattern_input.split(",") if pattern_input else ["*.py"]
    
    print_info(f"Scanning for TODOs in {repo_name} using patterns {file_patterns}...")

    # Fetch existing issues to avoid duplicates
    print_info("Checking existing issues to prevent duplicates...")
    existing_titles = []
    try:
        issue_resp = get_issues(github_username, repo_name, github_token, state='all')
        if issue_resp.status_code == 200:
            existing_titles = [i['title'] for i in issue_resp.json()]
    except Exception:
        print_warning("Could not fetch existing issues. Duplicate detection disabled.")

    found_todos = []
    for pattern in file_patterns:
        # Clean pattern for glob
        clean_pattern = pattern.strip()
        for file_path in glob.glob(clean_pattern, recursive=True):
            if os.path.isfile(file_path) and ".git" not in file_path:
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        for line_num, line in enumerate(f, 1):
                            if "TODO" in line:
                                match = re.search(r'TODO:(.*)', line, re.IGNORECASE)
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
        print_success("Clean sweep! No TODOs found.")
        return

    print_info(f"Found {len(found_todos)} TODOs. Processing...")
    
    created_count = 0
    for todo in found_todos:
        title = f"TODO: {todo['comment'][:50]}" # Cap title length
        if title in existing_titles:
            print_warning(f"Skipping duplicate issue: {title}")
            continue

        body = f"### Description\n{todo['comment']}\n\n"
        body += f"### Location\n- **File:** `{todo['file']}`\n- **Line:** {todo['line']}\n"
        if todo['author']:
            body += f"- **Blame:** {todo['author']}\n"
        
        body += f"\n### Context\n{todo['context']}\n\n"
        body += "_Generated automatically by PyGitUp Smart Issue engine._"

        if args and args.dry_run:
            print(f"[DRY-RUN] Would create issue: {title}")
            created_count += 1
            continue

        # In a real scenario, we might use the author's email to find their GH username,
        # but for now, we'll stick to provided assignees or none.
        assignees = [name.strip() for name in args.assign.split(",")] if args and args.assign else []
        
        response = create_issue(github_username, repo_name, github_token, title, body, assignees)
        if response.status_code == 201:
            print_success(f"Created issue: {title}")
            created_count += 1
        else:
            print_error(f"Failed to create issue '{title}': {response.status_code}")

    print_success(f"Operation complete. {created_count} new issues processed.")
