import os
import subprocess
import json
from .ui import print_info, print_success, print_error
from ..github.api import (
    create_repo, get_repo_info, create_issue, get_issues, 
    update_file, get_file_info, github_request, delete_repo_api,
    star_repo, follow_user
)
from ..core.config import load_config, get_github_username, get_github_token

def read_file_tool(path):
    """Reads content from a local file."""
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"

def write_file_tool(path, content):
    """Writes content to a local file."""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote to {path}"
    except Exception as e:
        return f"Error writing file: {e}"

def list_files_tool(directory="."):
    """Lists files in a directory recursively."""
    files_list = []
    try:
        for root, _, files in os.walk(directory):
            if any(x in root for x in [".git", "node_modules", "venv", "__pycache__", "dist"]):
                continue
            for f in files:
                files_list.append(os.path.join(root, f))
        return "\n".join(files_list)
    except Exception as e:
        return f"Error listing files: {e}"

import shlex

def run_shell_tool(command):
    """Executes a shell command safely."""
    try:
        # Prevent subshell execution by using list-based arguments
        args = shlex.split(command)
        # Block dangerous commands explicitly
        forbidden = ['rm', 'mv', 'mkfs', 'dd', 'sudo']
        if args[0] in forbidden:
            return f"Error: Command '{args[0]}' is restricted for security."
            
        result = subprocess.run(args, shell=False, capture_output=True, text=True, timeout=30)
        return f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}\nEXIT CODE: {result.returncode}"
    except Exception as e:
        return f"Execution Error: {e}"

# --- GITHUB TOOLS ---

def github_repo_tool(action, name, description="", private=True):
    """Manages GitHub repositories (create, delete, info)."""
    config = load_config(); user = get_github_username(config); token = get_github_token(config)
    if action == "create":
        resp = create_repo(user, name, token, description, private)
        return f"Create Repo Result: {resp.status_code} - {resp.text}"
    elif action == "delete":
        resp = delete_repo_api(user, name, token)
        return f"Delete Repo Result: {resp.status_code}"
    elif action == "info":
        resp = get_repo_info(user, name, token)
        return f"Repo Info: {resp.json() if resp.status_code == 200 else resp.text}"
    return "Invalid Repo Action"

def github_issue_tool(action, repo, title="", body="", number=None, state="open"):
    """Manages GitHub issues (list, create, comment, close)."""
    config = load_config(); user = get_github_username(config); token = get_github_token(config)
    if action == "list":
        resp = get_issues(user, repo, token, state=state)
        return json.dumps(resp.json() if resp.status_code == 200 else {"error": resp.text})
    elif action == "create":
        resp = create_issue(user, repo, token, title, body)
        return f"Create Issue Result: {resp.status_code}"
    elif action == "comment" and number:
        url = f"https://api.github.com/repos/{user}/{repo}/issues/{number}/comments"
        resp = github_request("POST", url, token, json={"body": body})
        return f"Comment Result: {resp.status_code}"
    elif action == "close" and number:
        url = f"https://api.github.com/repos/{user}/{repo}/issues/{number}"
        resp = github_request("PATCH", url, token, json={"state": "closed"})
        return f"Close Result: {resp.status_code}"
    return "Invalid Issue Action"

def github_social_tool(action, target):
    """Handles social automation (starring, following)."""
    config = load_config(); token = get_github_token(config)
    if action == "star":
        # Target format: "owner/repo"
        if "/" in target:
            owner, repo = target.split("/")
            resp = star_repo(owner, repo, token)
            return f"Star Result: {resp.status_code}"
        return "Error: Target must be 'owner/repo'"
    elif action == "follow":
        resp = follow_user(target, token)
        return f"Follow Result: {resp.status_code}"
    return "Invalid Social Action"

def search_code_tool(query, path="."):
    """Recursively searches for a string within the project files."""
    matches = []
    try:
        for root, _, files in os.walk(path):
            if any(x in root for x in [".git", "node_modules", "venv", "__pycache__", "dist"]):
                continue
            for f in files:
                fpath = os.path.join(root, f)
                try:
                    with open(fpath, 'r', encoding='utf-8', errors='ignore') as file:
                        if query in file.read():
                            matches.append(fpath)
                except: continue
        return "\n".join(matches) if matches else "No matches found."
    except Exception as e:
        return f"Search Error: {e}"

def git_manager_tool(action, params=""):
    """Handles complex Git operations like branching, merging, and status."""
    # List-based args for safety
    cmd = ["git", action]
    if params:
        import shlex
        cmd += shlex.split(params)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}\nCODE: {result.returncode}"
    except Exception as e:
        return f"Git Manager Error: {e}"

def patch_file_tool(path, search_text, replace_text):
    """Performs a targeted search-and-replace edit on a file."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        if search_text not in content:
            return f"Error: Could not find the exact text to replace in {path}."
        new_content = content.replace(search_text, replace_text)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return f"Successfully patched {path}."
    except Exception as e:
        return f"Patch Error: {e}"

def get_code_summary_tool(path="."):
    """Uses AST to map all classes and functions without reading full code."""
    import ast
    summary = []
    try:
        for root, _, files in os.walk(path):
            if any(x in root for x in [".git", "node_modules", "venv", "__pycache__"]): continue
            for f in files:
                if f.endswith(".py"):
                    fpath = os.path.join(root, f)
                    try:
                        with open(fpath, 'r', encoding='utf-8') as file:
                            tree = ast.parse(file.read())
                            funcs = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
                            classes = [n.name for n in tree.body if isinstance(n, ast.ClassDef)]
                            summary.append(f"FILE: {fpath}\n  Classes: {classes}\n  Functions: {funcs}")
                    except: continue
        return "\n".join(summary)
    except Exception as e:
        return f"Summary Error: {e}"

def persistence_tool(action, key, value=None):
    """Stores or retrieves simple state data for long-term task tracking."""
    state_file = ".pygitup_agent_state.json"
    state = {}
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r') as f: state = json.load(f)
        except Exception as e:
            print_error(f"Failed to load mission state: {e}")
    
    if action == "set":
        state[key] = value
        with open(state_file, 'w') as f: json.dump(state, f)
        return f"State '{key}' updated."
    elif action == "get":
        return str(state.get(key, "Not found."))
    return "Invalid Persistence Action"

def read_file_range_tool(path, start_line, end_line):
    """Reads a specific range of lines from a file."""
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            return "".join(lines[start_line-1:end_line])
    except Exception as e:
        return f"Error reading range: {e}"

def repo_audit_tool():
    """Provides a high-level summary of the repository status for Agent awareness."""
    config = load_config(); user = get_github_username(config); token = get_github_token(config)
    owner, repo = get_current_repo_context()
    if not owner or not repo: return "Not in a Git repository."
    
    from ..github.api import get_issues, get_commit_history
    try:
        issues = get_issues(owner, repo, token, state="open").json()[:5]
        commits = get_commit_history(owner, repo, token).json()[:5]
        
        summary = f"RECON REPORT: {owner}/{repo}\n"
        summary += f"- Open Issues: {len(issues)}\n"
        for i in issues: summary += f"  #{i['number']}: {i['title']}\n"
        summary += "- Recent Commits:\n"
        for c in commits: summary += f"  - {c['commit']['message'][:50]}\n"
        return summary
    except Exception as e:
        return f"Audit Error: {e}"

def fetch_web_content_tool(url):
    """Fetches and cleans text content from a URL (e.g., documentation)."""
    try:
        import requests
        from bs4 import BeautifulSoup
        resp = requests.get(url, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')
        # Remove scripts and styles
        for s in soup(["script", "style"]): s.extract()
        return soup.get_text(separator=' ', strip=True)[:10000]
    except Exception as e:
        return f"Web Fetch Error: {e}"

def get_environment_info_tool():
    """Returns details about the local dev environment."""
    import sys
    import platform
    info = {
        "os": platform.system(),
        "os_release": platform.release(),
        "python_version": sys.version,
        "cwd": os.getcwd()
    }
    return json.dumps(info, indent=2)

# Schema definitions for Gemini Function Calling
AGENT_TOOLS_SPEC = [
    {
        "name": "fetch_web_content",
        "description": "Read documentation or technical articles from a URL.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string"}
            },
            "required": ["url"]
        }
    },
    {
        "name": "get_environment_info",
        "description": "Get system-level details (OS, Python version, CWD).",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "repo_audit",
        "description": "Get a summary of the project status (issues, recent commits) to begin a task.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "read_file_range",
        "description": "Read a specific range of lines from a file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "start_line": {"type": "integer"},
                "end_line": {"type": "integer"}
            },
            "required": ["path", "start_line", "end_line"]
        }
    },
    {
        "name": "persistence",
        "description": "Store or retrieve task state to track long-term goals across sessions.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["get", "set"]},
                "key": {"type": "string"},
                "value": {"type": "string", "description": "Required for 'set' action."}
            },
            "required": ["action", "key"]
        }
    },
    {
        "name": "read_file",
        "description": "Read content from a local file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "Write content to a local file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "patch_file",
        "description": "Edit a specific part of a file using search and replace. Preferred over write_file for large files.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "search_text": {"type": "string", "description": "The exact text block to find."},
                "replace_text": {"type": "string", "description": "The new text to insert."}
            },
            "required": ["path", "search_text", "replace_text"]
        }
    },
    {
        "name": "get_code_summary",
        "description": "Get a high-level map of all classes and functions in the project.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory to map."}
            }
        }
    },
    {
        "name": "list_files",
        "description": "List project files.",
        "parameters": {
            "type": "object",
            "properties": {
                "directory": {"type": "string"}
            }
        }
    },
    {
        "name": "run_shell",
        "description": "Run a shell command (git, tests, etc).",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string"}
            },
            "required": ["command"]
        }
    },
    {
        "name": "search_code",
        "description": "Search for a string or pattern across the entire project.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The text to search for."}
            },
            "required": ["query"]
        }
    },
    {
        "name": "git_manager",
        "description": "Perform advanced Git tasks (branch, merge, checkout, status).",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "The git subcommand."},
                "params": {"type": "string", "description": "Arguments for the subcommand."}
            },
            "required": ["action"]
        }
    },
    {
        "name": "github_repo",
        "description": "Manage GitHub repositories.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["create", "delete", "info"]},
                "name": {"type": "string"},
                "description": {"type": "string"},
                "private": {"type": "boolean"}
            },
            "required": ["action", "name"]
        }
    },
    {
        "name": "github_issue",
        "description": "Manage GitHub issues.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["list", "create", "comment", "close"]},
                "repo": {"type": "string"},
                "title": {"type": "string"},
                "body": {"type": "string"},
                "number": {"type": "integer"},
                "state": {"type": "string"}
            },
            "required": ["action", "repo"]
        }
    },
    {
        "name": "github_social",
        "description": "Perform social actions like starring a repo or following a user.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["star", "follow"]},
                "target": {"type": "string", "description": "Repo name (owner/repo) for star, or username for follow."}
            },
            "required": ["action", "target"]
        }
    }
]

def execute_agent_tool(name, arguments):
    """Dispatcher for tool execution."""
    if name == "read_file":
        return read_file_tool(arguments.get("path"))
    elif name == "read_file_range":
        return read_file_range_tool(arguments.get("path"), arguments.get("start_line"), arguments.get("end_line"))
    elif name == "fetch_web_content":
        return fetch_web_content_tool(arguments.get("url"))
    elif name == "get_environment_info":
        return get_environment_info_tool()
    elif name == "repo_audit":
        return repo_audit_tool()
    elif name == "write_file":
        return write_file_tool(arguments.get("path"), arguments.get("content"))
    elif name == "patch_file":
        return patch_file_tool(arguments.get("path"), arguments.get("search_text"), arguments.get("replace_text"))
    elif name == "get_code_summary":
        return get_code_summary_tool(arguments.get("path", "."))
    elif name == "list_files":
        return list_files_tool(arguments.get("directory", "."))
    elif name == "run_shell":
        return run_shell_tool(arguments.get("command"))
    elif name == "search_code":
        return search_code_tool(arguments.get("query"), arguments.get("path", "."))
    elif name == "git_manager":
        return git_manager_tool(arguments.get("action"), arguments.get("params", ""))
    elif name == "github_repo":
        return github_repo_tool(arguments.get("action"), arguments.get("name"), arguments.get("description", ""), arguments.get("private", True))
    elif name == "github_issue":
        return github_issue_tool(arguments.get("action"), arguments.get("repo"), arguments.get("title", ""), arguments.get("body", ""), arguments.get("number"), arguments.get("state", "open"))
    elif name == "github_social":
        return github_social_tool(arguments.get("action"), arguments.get("target"))
    else:
        return f"Error: Tool '{name}' not found."