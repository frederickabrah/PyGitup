
import re
import os
import urllib.parse

def validate_repo_name(name):
    """Validates GitHub repository names."""
    if not name:
        return False, "Repository name cannot be empty."
    if not re.match(r'^[a-zA-Z0-9._-]+$', name):
        return False, "Invalid repository name. Use only alphanumeric characters, dots, underscores, and hyphens."
    return True, ""

def is_safe_path(path):
    """
    Ensures the path is within the user's home directory or current working directory.
    Prevents access to sensitive system areas.
    """
    home = os.path.expanduser("~")
    cwd = os.getcwd()
    abs_path = os.path.abspath(os.path.expanduser(path))
    
    # Allow home directory or current workspace
    if abs_path.startswith(home) or abs_path.startswith(cwd):
        return True
    return False

def validate_file_path(path):
    """Validates local file paths with safety checks."""
    if not path:
        return False, "File path cannot be empty."
    
    if not is_safe_path(path):
        return False, "Security Violation: Path is outside authorized workspace."
        
    if not os.path.exists(path):
        return False, f"File or directory does not exist: {path}"
    return True, ""

def normalize_repo_path(path):
    """
    Sanitizes repository paths to prevent traversal.
    Returns a safe, relative path or raises ValueError.
    """
    if not path:
        return "."
    
    # Remove leading slashes and drive letters
    path = os.path.normpath(path).lstrip(os.sep).lstrip("/")
    
    # Block any attempt to go 'up'
    if ".." in path.split(os.sep) or ".." in path.split("/"):
        raise ValueError("Security Violation: Path traversal attempt detected.")
    
    return path

def validate_git_url(url):
    """
    Strict validation for Git URLs to prevent command injection.
    """
    if not url:
        raise ValueError("URL cannot be empty.")
        
    # Block Git Argument Injection (CVE-2017-1000117 style patterns)
    if url.startswith("-"):
        raise ValueError("Security Violation: URL cannot start with a dash.")
        
    # Block dangerous SSH options in the URL
    # Examples: ssh://-oProxyCommand=...
    if "ProxyCommand" in url or "upload-pack" in url or "receive-pack" in url:
        raise ValueError("Security Violation: Dangerous SSH options detected.")

    # Basic structure check
    if not (url.startswith(('http://', 'https://', 'git@', 'ssh://'))):
        raise ValueError("Invalid Git URL format. Must be HTTP, HTTPS, or SSH.")
    
    # Block shell metacharacters
    forbidden = [';', '|', '&', '`', '$(', '${', '>', '<', '\\']
    for char in forbidden:
        if char in url:
            raise ValueError(f"Security Violation: Dangerous character '{char}' detected in URL.")
            
    return True

def get_current_repo_context():
    """Extracts owner and repo name from local git remotes."""
    try:
        import subprocess
        result = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True)
        if result.returncode == 0:
            url = result.stdout.strip()
            # Handle both HTTPS and SSH formats
            if "github.com" in url:
                path = url.split("github.com")[-1].replace(":", "/").strip("/")
                parts = path.replace(".git", "").split("/")
                if len(parts) >= 2:
                    return parts[0], parts[1]
    except Exception:
        pass
    return None, None

def sanitize_input(text):
    """Removes potentially dangerous characters from general text input."""
    if not text:
        return ""
    # Remove everything except standard alpha-numeric and basic punctuation
    return re.sub(r'[^a-zA-Z0-9\s._\-()\[\]]', '', text)
