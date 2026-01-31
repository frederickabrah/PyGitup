
import re
import os

def validate_repo_name(name):
    """
    Validates a GitHub repository name.
    Rules: Only alphanumeric characters, hyphens, and underscores.
    """
    if not name:
        return False, "Repository name cannot be empty."
    
    if not re.match(r'^[a-zA-Z0-9\-_.]+$', name):
        return False, "Invalid repository name. Use only letters, numbers, hyphens, dots, and underscores."
    
    if len(name) > 100:
        return False, "Repository name is too long (max 100 characters)."
        
    return True, ""

def validate_file_path(path, must_exist=True):
    """
    Validates a local file path.
    """
    if not path:
        return False, "File path cannot be empty."
    
    if must_exist and not os.path.exists(path):
        return False, f"File or directory does not exist: {path}"
        
    return True, ""

def sanitize_input(text):
    """
    Basic sanitization for string inputs.
    Removes leading/trailing whitespace.
    """
    if text is None:
        return ""
    return str(text).strip()
