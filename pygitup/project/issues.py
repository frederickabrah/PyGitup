import glob
import re
import os

from ..github.api import create_issue

def scan_todos(github_username, github_token, config, args=None):
    """Scan code for TODO comments and create GitHub issues."""
    if args and args.dry_run:
        print("*** Dry Run Mode: No changes will be made. ***")
        if args and args.repo:
            repo_name = args.repo
        else:
            repo_name = input("Enter repository name: ")
        print(f"Would scan for TODOs in {repo_name} and create issues.")
        return

    if args and args.repo:
        repo_name = args.repo
    else:
        repo_name = input("Enter repository name: ")
    
    if args and args.pattern:
        file_patterns = args.pattern.split(",")
    else:
        pattern_input = input("Enter file patterns (comma-separated, e.g., *.py,*.js): ")
        file_patterns = pattern_input.split(",") if pattern_input else ["*.py"]
    
    assignees = []
    if args and args.assign:
        assignees = [name.strip() for name in args.assign.split(",")]
    elif not args or not args.no_assign:
        assign_input = input("Assign issues to (comma-separated usernames, optional): ")
        assignees = [name.strip() for name in assign_input.split(",")] if assign_input else []
    
    print(f"Scanning for TODOs in {repo_name}...")

    todos = []
    for pattern in file_patterns:
        for file_path in glob.glob(pattern, recursive=True):
            if os.path.isfile(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        for line_num, line in enumerate(f, 1):
                            if "TODO" in line:
                                match = re.search(r'#.*TODO:(.*)', line, re.IGNORECASE)
                                if match:
                                    comment = match.group(0).strip()
                                    todos.append({
                                        "file": file_path,
                                        "line": line_num,
                                        "comment": comment
                                    })
                except Exception as e:
                    print(f"Warning: Could not read file {file_path}: {e}")

    if not todos:
        print("No TODO comments found.")
        return
    
    created_issues = 0
    for todo in todos:
        title = f"TODO: {todo['comment'][6:]}"  # Remove "TODO: " prefix
        body = f"Found in {todo['file']} at line {todo['line']}\n\n{todo['comment']}"
        
        response = create_issue(github_username, repo_name, github_token, title, body, assignees)
        
        if response.status_code == 201:
            issue_data = response.json()
            print(f"✓ Created issue: {title}")
            print(f"  View at: {issue_data['html_url']}")
            created_issues += 1
        else:
            print(f"✗ Failed to create issue '{title}': {response.status_code}")
    
    print(f"TODO scan complete: {created_issues} issues created.")