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

# Schema definitions for Gemini Function Calling
AGENT_TOOLS_SPEC = [
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
    elif name == "write_file":
        return write_file_tool(arguments.get("path"), arguments.get("content"))
    elif name == "list_files":
        return list_files_tool(arguments.get("directory", "."))
    elif name == "run_shell":
        return run_shell_tool(arguments.get("command"))
    elif name == "github_repo":
        return github_repo_tool(arguments.get("action"), arguments.get("name"), arguments.get("description", ""), arguments.get("private", True))
    elif name == "github_issue":
        return github_issue_tool(arguments.get("action"), arguments.get("repo"), arguments.get("title", ""), arguments.get("body", ""), arguments.get("number"), arguments.get("state", "open"))
    elif name == "github_social":
        return github_social_tool(arguments.get("action"), arguments.get("target"))
    else:
        return f"Error: Tool '{name}' not found."