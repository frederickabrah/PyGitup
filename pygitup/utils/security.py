import subprocess
import os
import fnmatch
import math
from ..github.api import get_dependabot_alerts, get_secret_scanning_alerts
from ..utils.ui import print_success, print_error, print_warning, print_info, print_header

# List of patterns that are usually sensitive or too heavy to upload
SENSITIVE_PATTERNS = [
    # Secrets and Configs
    "*.env", ".env.*",
    "*.pem", "*.key", "id_rsa", "id_dsa",
    "token.json", "credentials.json", "secrets.json",
    "pygitup.yaml",
    
    # Heavy / Build Artifacts
    "node_modules",
    "venv", ".venv", "env",
    "__pycache__", "*.pyc",
    "dist", "build", "*.egg-info",
    ".git", ".idea", ".vscode"
]

def calculate_entropy(data):
    """Calculates the Shannon entropy of a string."""
    if not data:
        return 0
    entropy = 0
    for x in range(256):
        p_x = float(data.count(chr(x))) / len(data)
        if p_x > 0:
            entropy += - p_x * math.log(p_x, 2)
    return entropy

def run_audit(github_username=None, repo_name=None, github_token=None):
    """Run a security audit on the project dependencies."""
    print_header("Security Audit")
    
    # Local pip-audit
    print_info("Running local pip-audit on current environment...")
    try:
        result = subprocess.run(["pip-audit"], capture_output=True, text=True)
        if result.returncode == 0:
            print_success("No known local vulnerabilities found via pip-audit.")
        else:
            print_warning("Local vulnerabilities detected:")
            print(result.stdout)
    except FileNotFoundError:
        print_warning("'pip-audit' not found. Skipping local scan.")

    # Remote GitHub Security scan if context provided
    if github_username and repo_name and github_token:
        run_advanced_security_scan(github_username, repo_name, github_token)

def run_advanced_security_scan(username, repo_name, token):
    """Deep vulnerability scanning using GitHub's security APIs."""
    print_info(f"Fetching GitHub Security Alerts for {repo_name}...")
    
    try:
        # Dependabot
        dep_resp = get_dependabot_alerts(username, repo_name, token)
        if dep_resp.status_code == 200:
            alerts = dep_resp.json()
            open_alerts = [a for a in alerts if a['state'] == 'open']
            if open_alerts:
                print_error(f"Found {len(open_alerts)} OPEN Dependabot vulnerabilities!")
                for a in open_alerts[:3]:
                    print(f" - {a['security_advisory']['summary']} ({a['security_advisory']['severity']})")
            else:
                print_success("No open Dependabot alerts found.")
        
        # Secret Scanning
        sec_resp = get_secret_scanning_alerts(username, repo_name, token)
        if sec_resp.status_code == 200:
            secrets = sec_resp.json()
            open_secrets = [s for s in secrets if s['state'] == 'open']
            if open_secrets:
                print_error(f"ALERT: {len(open_secrets)} LEAKED SECRETS detected in repo history!")
                for s in open_secrets:
                    print(f" - Type: {s['secret_type']} at {s['html_url']}")
            else:
                print_success("No leaked secrets detected.")
        elif sec_resp.status_code == 404:
            print_info("Secret scanning is not enabled or not supported for this repo.")

    except Exception as e:
        print_warning(f"Advanced security scan failed: {e}")

def check_is_sensitive(file_path):
    """Checks if a file path matches any sensitive patterns or has high entropy contents."""
    name = os.path.basename(file_path)
    
    # 1. Filename Pattern Check
    gitignore_patterns = []
    if os.path.exists(".gitignore"):
        with open(".gitignore", "r") as f:
            gitignore_patterns = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    all_patterns = SENSITIVE_PATTERNS + gitignore_patterns
    for pattern in all_patterns:
        if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(file_path, pattern):
            return True

    # 2. Sophisticated Content Analysis (High Entropy Detection)
    if os.path.isfile(file_path) and os.path.getsize(file_path) < 1024 * 500:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                for line in content.splitlines():
                    words = line.split()
                    for word in words:
                        if len(word) > 20 and calculate_entropy(word) > 4.5:
                            return True
        except Exception:
            pass

    return False

def audit_files_and_prompt(files):
    """Scans a list of files for sensitive content."""
    sensitive_matches = [f for f in files if check_is_sensitive(f)]
    if not sensitive_matches:
        return files

    print_warning(f"SECURITY WARNING: {len(sensitive_matches)} sensitive or heavy files detected!")
    for f in sensitive_matches[:5]:
        print(f" - {f}")
    
    choice = input("\nHow to proceed? (1: Skip them [Default], 2: Upload anyway, 3: Cancel): ") or "1"
    
    if choice == "1":
        return [f for f in files if f not in sensitive_matches]
    elif choice == "2":
        return files
    return []

def scan_directory_for_sensitive_files(directory):
    """Scans a directory for sensitive files before git add."""
    detected = []
    for root, dirs, files in os.walk(directory):
        for name in dirs + files:
            full_path = os.path.join(root, name)
            if check_is_sensitive(full_path):
                detected.append(full_path)

    if not detected:
        return True

    print_warning(f"Sensitive files found: {len(detected)}")
    choice = input("\nAction? (1: Add to .gitignore, 2: Ignore warning, 3: Cancel): ")
    
    if choice == "1":
        with open(".gitignore", "a") as f:
            f.write("\n# Added by PyGitUp Interceptor\n")
            for item in detected:
                f.write(f"{os.path.relpath(item, directory)}\n")
        return True
    return choice == "2"

def generate_ssh_key(email):
    """Generates a secure Ed25519 SSH key if one does not exist."""
    ssh_dir = os.path.expanduser("~/.ssh")
    key_path = os.path.join(ssh_dir, "id_ed25519")
    pub_key_path = f"{key_path}.pub"

    if os.path.exists(key_path):
        print_info("Existing Ed25519 key found.")
        try:
            with open(pub_key_path, 'r') as f:
                return f.read().strip(), key_path
        except FileNotFoundError:
            print_error("Private key exists but public key is missing.")
            return None, None

    print_info("Generating new secure Ed25519 SSH key...")
    os.makedirs(ssh_dir, exist_ok=True)
    
    try:
        # Generate key with no passphrase for automation convenience (standard for dev tools)
        subprocess.run(
            ["ssh-keygen", "-t", "ed25519", "-C", email, "-f", key_path, "-N", ""],
            check=True,
            capture_output=True
        )
        print_success(f"Key generated at {key_path}")
        
        with open(pub_key_path, 'r') as f:
            return f.read().strip(), key_path
            
    except subprocess.CalledProcessError as e:
        print_error(f"SSH Key generation failed: {e}")
        return None, None