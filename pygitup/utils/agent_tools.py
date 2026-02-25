import os
import subprocess
import json
import glob
import concurrent.futures
from .ui import print_info, print_success, print_error
from ..github.api import (
    create_repo, get_repo_info, create_issue, get_issues, 
    update_file, get_file_info, github_request, delete_repo_api,
    star_repo, follow_user
)
from ..core.config import load_config, get_github_username, get_github_token
from ..utils.validation import get_current_repo_context, is_safe_path

REFERENCE_CONTENT_END = "REFERENCE_CONTENT_END"

def read_file_tool(path):
    """Reads content from a local file."""
    if not is_safe_path(path):
        return {"error": "Security Violation: Access denied to path outside workspace."}
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            # Basic truncation logic for safety
            if len(content) > 100000: # 100KB limit
                return {"content": content[:100000], "is_truncated": True, "warning": "File truncated due to size."}
            return {"content": content}
    except Exception as e:
        return {"error": str(e)}

def _read_single_file_task(path):
    """Internal helper for parallel reading."""
    if not is_safe_path(path):
        return path, "Error: Security Violation"
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            if len(content) > 50000: # Smaller limit for batch read
                return path, content[:50000] + "\n[WARNING: File truncated in batch read]"
            return path, content
    except Exception as e:
        return path, f"Error: {e}"

def read_many_files_tool(include, exclude=None):
    """
    Reads multiple files using glob patterns.
    Optimized with parallel execution and structured formatting.
    """
    files_to_read = set()
    exclude = exclude or []
    
    # 1. Expand glob patterns
    for pattern in include:
        matches = glob.glob(pattern, recursive=True)
        for m in matches:
            if os.path.isfile(m):
                # Apply exclusions
                is_excluded = False
                for ex in exclude:
                    if glob.fnmatch.fnmatch(m, ex):
                        is_excluded = True
                        break
                if not is_excluded:
                    files_to_read.add(m)

    # 2. Parallel Reading
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_file = {executor.submit(_read_single_file_task, f): f for f in files_to_read}
        for future in concurrent.futures.as_completed(future_to_file):
            path, content = future.result()
            results[path] = content

    # 3. Structured Formatting for LLM
    llm_output = ""
    for path, content in sorted(results.items()):
        llm_output += f"--- {path} ---\n\n{content}\n\n"
    
    if llm_output:
        llm_output += f"\n{REFERENCE_CONTENT_END}"
    
    return {
        "content": llm_output,
        "files_processed": list(results.keys()),
        "status": "success" if results else "no_files_found"
    }

def create_git_checkpoint(message):
    """Creates a temporary git stash as a safety checkpoint."""
    try:
        # Check if it's a git repo
        if not os.path.isdir(".git"): return None
        
        # Create a stash with a specific message
        stash_msg = f"PyGitUp Checkpoint: {message}"
        # We use --include-untracked to ensure new files are also saved
        subprocess.run(["git", "stash", "push", "--include-untracked", "-m", stash_msg], 
                       capture_output=True, text=True, check=True)
        
        # Immediately re-apply it so the workspace doesn't change, 
        # but now we have a recovery point in 'git stash list'
        subprocess.run(["git", "stash", "apply", "stash@{0}"], 
                       capture_output=True, text=True, check=True)
        return "stash@{0}"
    except Exception as e:
        print_warning(f"Safety Checkpoint failed: {e}")
        return None

def write_file_tool(path, content):
    """
    Writes content to a local file using an atomic operation.
    Prevents file corruption by writing to a temp file first.
    """
    if not is_safe_path(path):
        return {"error": "Security Violation: Access denied to path outside workspace."}
    
    import tempfile
    import shutil
    
    abs_path = os.path.abspath(os.path.expanduser(path))
    dir_name = os.path.dirname(abs_path)
    os.makedirs(dir_name, exist_ok=True)
    
    # Safety Checkpoint before modification
    create_git_checkpoint(f"Before write to {path}")
    
    # Atomic write pattern
    fd, temp_path = tempfile.mkstemp(dir=dir_name, text=True)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(content)
        # Atomic replace
        shutil.move(temp_path, abs_path)
        return {"status": "success", "path": abs_path, "bytes": len(content)}
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return {"error": str(e)}

def list_files_tool(directory="."):
    """
    Lists files with metadata (size, modified time).
    Respects common ignore patterns automatically.
    """
    if not is_safe_path(directory):
        return {"error": "Security Violation: Access denied."}
        
    files_list = []
    ignore_list = [".git", "node_modules", "venv", "__pycache__", "dist", "build", ".pytest_cache"]
    
    try:
        for root, dirs, files in os.walk(directory):
            # Prune ignored directories
            dirs[:] = [d for d in dirs if d not in ignore_list]
            
            for f in files:
                fpath = os.path.join(root, f)
                try:
                    stats = os.stat(fpath)
                    files_list.append({
                        "path": os.path.relpath(fpath, directory),
                        "size_bytes": stats.st_size,
                        "modified": stats.st_mtime,
                        "type": "file" if os.path.isfile(fpath) else "dir"
                    })
                except: continue
                
                if len(files_list) > 1000: # Limit for safety
                    return {"files": files_list, "warning": "Truncated: too many files."}
                    
        return {"files": files_list, "total_count": len(files_list)}
    except Exception as e:
        return {"error": str(e)}

import shlex

def run_shell_tool(command, is_background=False):
    """Executes a shell command safely with background support."""
    try:
        args = shlex.split(command)
        forbidden = ['rm', 'mv', 'mkfs', 'dd', 'sudo']
        if args[0] in forbidden:
            return {"error": f"Command '{args[0]}' is restricted."}
            
        if is_background:
            # Run in background and return PID
            process = subprocess.Popen(args, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            return {"status": "started", "pid": process.pid, "message": "Command running in background."}
        
        result = subprocess.run(args, shell=False, capture_output=True, text=True, timeout=60)
        
        stdout = result.stdout
        stderr = result.stderr
        
        # Optimization: Truncate massive outputs to prevent UI/API hangs
        limit = 10000 # 10KB limit
        if len(stdout) > limit:
            stdout = stdout[:limit] + "\n... [TRUNCATED: Output too large] ..."
        if len(stderr) > limit:
            stderr = stderr[:limit] + "\n... [TRUNCATED: Error too large] ..."
            
        return {"stdout": stdout, "stderr": stderr, "exit_code": result.returncode}
    except Exception as e:
        return {"error": str(e)}

# --- GITHUB TOOLS ---

def github_repo_tool(action, name, description="", private=True):
    """Manages GitHub repositories (create, delete, info)."""
    config = load_config()
    user = get_github_username(config)
    token = get_github_token(config)
    if action == "create":
        resp = create_repo(user, name, token, description, private)
        return {"status": resp.status_code, "data": resp.json() if resp.status_code in [200, 201] else resp.text}
    elif action == "delete":
        resp = delete_repo_api(user, name, token)
        return {"status": resp.status_code}
    elif action == "info":
        resp = get_repo_info(user, name, token)
        return {"status": resp.status_code, "data": resp.json() if resp.status_code == 200 else resp.text}
    return {"error": "Invalid action"}

def github_issue_tool(action, repo, title="", body="", number=None, state="open"):
    """Manages GitHub issues (list, create, comment, close)."""
    config = load_config()
    user = get_github_username(config)
    token = get_github_token(config)
    if action == "list":
        resp = get_issues(user, repo, token, state=state)
        return {"status": resp.status_code, "data": resp.json() if resp.status_code == 200 else resp.text}
    elif action == "create":
        resp = create_issue(user, repo, token, title, body)
        return {"status": resp.status_code}
    elif action == "comment" and number:
        url = f"https://api.github.com/repos/{user}/{repo}/issues/{number}/comments"
        resp = github_request("POST", url, token, json={"body": body})
        return {"status": resp.status_code}
    elif action == "close" and number:
        url = f"https://api.github.com/repos/{user}/{repo}/issues/{number}"
        resp = github_request("PATCH", url, token, json={"state": "closed"})
        return {"status": resp.status_code}
    return {"error": "Invalid action"}

def github_social_tool(action, target):
    """Handles social automation (starring, following)."""
    config = load_config()
    token = get_github_token(config)
    if action == "star":
        if "/" in target:
            owner, repo = target.split("/")
            resp = star_repo(owner, repo, token)
            return {"status": resp.status_code}
        return {"error": "Target must be owner/repo"}
    elif action == "follow":
        resp = follow_user(target, token)
        return {"status": resp.status_code}
    return {"error": "Invalid action"}

def ask_user_tool(question):
    """Pauses the agent mission to ask the user for clarification or data."""
    # The TUI implementation of mentor_task will catch this tool name specifically
    return {"status": "pending_user_response", "question": question}

def search_code_tool(query, path="."):
    """Recursively searches for a string using git grep (optimized) or manual fallback."""
    # Try git grep first (faster, respects .gitignore)
    try:
        cmd = ["git", "grep", "-n", "--ignore-case", query]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            return {"matches": result.stdout.splitlines()[:50], "method": "git_grep"}
    except: pass

    # Manual fallback
    matches = []
    try:
        for root, _, files in os.walk(path):
            if any(x in root for x in [".git", "node_modules", "venv", "__pycache__", "dist"]):
                continue
            for f in files:
                fpath = os.path.join(root, f)
                try:
                    with open(fpath, 'r', encoding='utf-8', errors='ignore') as file:
                        for i, line in enumerate(file, 1):
                            if query.lower() in line.lower():
                                matches.append(f"{fpath}:{i}:{line.strip()}")
                                if len(matches) > 50: break
                except: continue
            if len(matches) > 50: break
        return {"matches": matches, "method": "manual_scan"}
    except Exception as e:
        return {"error": str(e)}

def git_manager_tool(action, params=""):
    """Handles complex Git operations."""
    cmd = ["git", action]
    if params:
        cmd += shlex.split(params)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return {"stdout": result.stdout, "stderr": result.stderr, "exit_code": result.returncode}
    except Exception as e:
        return {"error": str(e)}

def patch_file_tool(path, search_text, replace_text):
    """
    Performs a targeted edit with robust whitespace handling.
    Normalizes indentation to ensure matching even if the model has minor spacing errors.
    """
    if not is_safe_path(path):
        return {"error": "Security Violation: Access denied."}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 1. Try exact match first
        if search_text in content:
            new_content = content.replace(search_text, replace_text)
        else:
            # 2. Try normalized whitespace match (Fuzzy)
            import re
            
            # Escape the search text for regex but then make whitespace flexible
            pattern = re.escape(search_text)
            # Replace escaped spaces with a regex that matches any whitespace
            pattern = re.sub(r'\\ ', r'\\s+', pattern)
            # Also handle escaped newlines/tabs if they exist in the escape
            pattern = re.sub(r'\\n', r'\\s+', pattern)
            pattern = re.sub(r'\\t', r'\\s+', pattern)
            
            matches = list(re.finditer(pattern, content))
            if len(matches) == 1:
                match = matches[0]
                new_content = content[:match.start()] + replace_text + content[match.end():]
            elif len(matches) > 1:
                return {"error": "Multiple matches found for fuzzy search. Be more specific."}
            else:
                return {"error": "Search block not found. Ensure the code snippet is accurate."}

        # Safety Checkpoint
        create_git_checkpoint(f"Before patch to {path}")

        # Atomic Write
        return write_file_tool(path, new_content)
    except Exception as e:
        return {"error": str(e)}

def get_code_summary_tool(path="."):
    """Uses AST to map all classes and functions."""
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
                            summary.append({"file": fpath, "classes": classes, "functions": funcs})
                    except: continue
        return {"summary": summary}
    except Exception as e:
        return {"error": str(e)}

def persistence_tool(action, key, value=None, scope="session"):
    """
    Stores or retrieves state data across turns and sessions.
    Scopes: 'session' (ephemeral), 'fact' (long-term memory).
    """
    import time
    config_dir = os.path.join(os.path.expanduser("~"), ".pygitup_config")
    os.makedirs(config_dir, exist_ok=True)
    
    state_file = os.path.join(config_dir, "agent_memory.json")
    memory = {"session": {}, "facts": {}, "last_updated": time.time()}
    
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r') as f:
                memory.update(json.load(f))
        except: pass

    target = memory["facts"] if scope == "fact" else memory["session"]

    if action == "set":
        target[key] = value
        memory["last_updated"] = time.time()
        with open(state_file, 'w') as f:
            json.dump(memory, f, indent=4)
        return {"status": "memory_updated", "scope": scope, "key": key}
    elif action == "get":
        return {"key": key, "value": target.get(key, "Not found"), "scope": scope}
    return {"error": "Invalid action"}

def read_file_range_tool(path, start_line, end_line):
    """Reads a specific range of lines from a file."""
    if not is_safe_path(path):
        return {"error": "Security Violation: Access denied."}
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            return {"content": "".join(lines[start_line-1:end_line]), "range": [start_line, end_line]}
    except Exception as e:
        return {"error": str(e)}

def repo_audit_tool():
    """Provides a high-level summary of the repository status."""
    config = load_config()
    user = get_github_username(config)
    token = get_github_token(config)
    owner, repo = get_current_repo_context()
    if not owner or not repo: return {"error": "Not in a repository"}
    from ..github.api import get_issues, get_commit_history
    try:
        issues = get_issues(owner, repo, token, state="open").json()[:5]
        commits = get_commit_history(owner, repo, token).json()[:5]
        return {
            "repo": f"{owner}/{repo}",
            "open_issues_count": len(issues),
            "recent_issues": [{"number": i['number'], "title": i['title']} for i in issues],
            "recent_commits": [c['commit']['message'][:50] for c in commits]
        }
    except Exception as e:
        return {"error": str(e)}

def fetch_web_content_tool(url):
    """Fetches and cleans text content from a URL."""
    try:
        import requests
        from bs4 import BeautifulSoup
        resp = requests.get(url, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')
        for s in soup(["script", "style"]): s.extract()
        return {"url": url, "content": soup.get_text(separator=' ', strip=True)[:10000]}
    except Exception as e:
        return {"error": str(e)}

def get_environment_info_tool():
    """Returns details about the local dev environment."""
    import sys
    import platform
    return {
        "os": platform.system(),
        "os_release": platform.release(),
        "python_version": sys.version,
        "cwd": os.getcwd()
    }

# Schema definitions for Gemini Function Calling
AGENT_TOOLS_SPEC = [
    {
        "name": "fetch_web_content",
        "description": "Examine the technical content of a webpage or documentation URL. Use this to research libraries or API usage.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The full HTTP/HTTPS URL to fetch."}
            },
            "required": ["url"]
        }
    },
    {
        "name": "get_environment_info",
        "description": "Retrieve the current system state, including OS type and current working directory. Essential for understanding where you are executing.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "repo_audit",
        "description": "Perform a high-level reconnaissance of the current repository. Returns recent commits and open issues to help plan your next steps.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "read_file_range",
        "description": "Read a specific window of lines from a file. Useful for large files where you only need to examine a specific function or class.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path to the file."},
                "start_line": {"type": "integer", "description": "First line to read (1-indexed)."},
                "end_line": {"type": "integer", "description": "Last line to read."}
            },
            "required": ["path", "start_line", "end_line"]
        }
    },
    {
        "name": "persistence",
        "description": "Save or load task-specific state variables. Use this to 'remember' complex multi-step plans across several turns or store permanent facts.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["get", "set"], "description": "Whether to retrieve or store a value."},
                "key": {"type": "string", "description": "The unique identifier for the state data."},
                "value": {"type": "string", "description": "The data to store (only for 'set' action)."},
                "scope": {"type": "string", "enum": ["session", "fact"], "description": "Scope of memory. 'session' is turn-based, 'fact' is permanent across all sessions."}
            },
            "required": ["action", "key"]
        }
    },
    {
        "name": "ask_user",
        "description": "Stop the current automated process to ask the user a specific question. Use this for clarifying requirements or requesting missing data.",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "The question to present to the user."}
            },
            "required": ["question"]
        }
    },
    {
        "name": "read_many_files",
        "description": "Read the content of multiple files using glob patterns. Highly efficient for gathering context across several modules in one turn. Supports inclusions and exclusions.",
        "parameters": {
            "type": "object",
            "properties": {
                "include": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "An array of glob patterns or paths to include. Examples: ['src/**/*.py', 'README.md']"
                },
                "exclude": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional array of glob patterns to exclude. Example: ['**/test_*.py']"
                }
            },
            "required": ["include"]
        }
    },
    {
        "name": "read_file",
        "description": "Read the complete source code of a file. Use this after list_files to understand implementation details.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path to the file."}
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "Create a new file or completely overwrite an existing one with new content. Use for new modules or complete refactors.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path where the file should be saved."},
                "content": {"type": "string", "description": "The full text content of the file."}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "patch_file",
        "description": "Apply a precision edit to a file by replacing a specific text block. This is safer and more efficient than write_file for small changes.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path to the file."},
                "search_text": {"type": "string", "description": "The exact block of text currently in the file that you want to change."},
                "replace_text": {"type": "string", "description": "The new text that should replace search_text."}
            },
            "required": ["path", "search_text", "replace_text"]
        }
    },
    {
        "name": "get_code_summary",
        "description": "Generate an AST-based map of the project structure. Identify all classes and functions defined in the directory tree.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory to summarize (defaults to current)."}
            }
        }
    },
    {
        "name": "list_files",
        "description": "Explore the project structure by listing all files in a directory. Essential first step for any task.",
        "parameters": {
            "type": "object",
            "properties": {
                "directory": {"type": "string", "description": "The directory to list (defaults to current)."}
            }
        }
    },
    {
        "name": "run_shell",
        "description": "Execute a shell command. Use this for running tests, installing dependencies, or complex git commands not covered by git_manager.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The full bash command to execute."},
                "is_background": {"type": "boolean", "description": "If true, the command will run in the background and return a PID."}
            },
            "required": ["command"]
        }
    },
    {
        "name": "search_code",
        "description": "Search for a specific string or pattern across the entire codebase. Use this to find where a function is called or a variable is defined.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The text pattern to search for."}
            },
            "required": ["query"]
        }
    },
    {
        "name": "git_manager",
        "description": "Perform standard Git operations. Use for branch management, status checks, and stashing.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "The git subcommand (status, branch, stash, checkout)."},
                "params": {"type": "string", "description": "Arguments for the git subcommand."}
            },
            "required": ["action"]
        }
    },
    {
        "name": "github_repo",
        "description": "Interact with GitHub repositories. Create new repos, delete existing ones, or fetch remote metadata.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["create", "delete", "info"], "description": "The repository operation to perform."},
                "name": {"type": "string", "description": "Name of the repository."},
                "description": {"type": "string", "description": "Description for the repository."},
                "private": {"type": "boolean", "description": "Whether the repo should be private."}
            },
            "required": ["action", "name"]
        }
    },
    {
        "name": "github_issue",
        "description": "Manage GitHub issues and comments. Use this to track bugs, suggest features, or communicate within a repo.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["list", "create", "comment", "close"], "description": "The issue operation."},
                "repo": {"type": "string", "description": "Repository name (full or just the name if owned by user)."},
                "title": {"type": "string", "description": "Issue title."},
                "body": {"type": "string", "description": "Description or comment body."},
                "number": {"type": "integer", "description": "Issue number (required for comment/close)."},
                "state": {"type": "string", "description": "Filter state (open/closed/all)."}
            },
            "required": ["action", "repo"]
        }
    },
    {
        "name": "github_social",
        "description": "Perform social interactions on GitHub. Use this to star important repositories or follow relevant users.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["star", "follow"], "description": "Social action to take."},
                "target": {"type": "string", "description": "owner/repo for starring, or username for following."}
            },
            "required": ["action", "target"]
        }
    }
]

def execute_agent_tool(name, arguments):
    """Dispatcher for tool execution."""
    if name == "read_file":
        return read_file_tool(arguments.get("path"))
    elif name == "read_many_files":
        return read_many_files_tool(arguments.get("include", []), arguments.get("exclude"))
    elif name == "read_file_range":
        return read_file_range_tool(arguments.get("path"), arguments.get("start_line"), arguments.get("end_line"))
    elif name == "fetch_web_content":
        return fetch_web_content_tool(arguments.get("url"))
    elif name == "get_environment_info":
        return get_environment_info_tool()
    elif name == "repo_audit":
        return repo_audit_tool()
    elif name == "persistence":
        return persistence_tool(arguments.get("action"), arguments.get("key"), arguments.get("value"), arguments.get("scope", "session"))
    elif name == "write_file":
        return write_file_tool(arguments.get("path"), arguments.get("content"))
    elif name == "patch_file":
        return patch_file_tool(arguments.get("path"), arguments.get("search_text"), arguments.get("replace_text"))
    elif name == "get_code_summary":
        return get_code_summary_tool(arguments.get("path", "."))
    elif name == "list_files":
        return list_files_tool(arguments.get("directory", "."))
    elif name == "run_shell":
        return run_shell_tool(arguments.get("command"), arguments.get("is_background", False))
    elif name == "ask_user":
        return ask_user_tool(arguments.get("question"))
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
        return {"error": f"Tool '{name}' not found."}
