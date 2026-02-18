import os
import ast
import fnmatch
import subprocess
from ..github.api import get_dependabot_alerts, get_secret_scanning_alerts
from ..utils.ui import print_success, print_error, print_warning, print_info, print_header, Table, box, console

# --- Secure SSH Keygen ---
def generate_ssh_key(email):
    """
    Generates a new SSH key (RSA 4096 or Ed25519) and returns the public key.
    """
    home_dir = os.path.expanduser("~")
    ssh_dir = os.path.join(home_dir, ".ssh")
    os.makedirs(ssh_dir, exist_ok=True)

    print("\n[bold]Select Key Algorithm:[/bold]")
    print("1: [cyan]Ed25519[/cyan] (Modern, recommended)")
    print("2: [green]RSA 4096[/green] (Maximum compatibility)")
    choice = input("\n👉 Choice [1]: ") or "1"
    
    algo = "ed25519" if choice == "1" else "rsa"
    key_name = f"pygitup_id_{algo}"
    key_path = os.path.join(ssh_dir, key_name)
    pub_key_path = f"{key_path}.pub"

    if not os.path.exists(key_path):
        print_info(f"Generating new {algo.upper()} key...")
        try:
            command = ["ssh-keygen", "-t", algo]
            if algo == "rsa":
                command += ["-b", "4096"]
            command += ["-C", email, "-f", key_path, "-N", ""]
            
            subprocess.run(command, check=True, capture_output=True, text=True)
            print_success(f"Key generated at {key_path}")
        except Exception as e:
            print_error(f"Failed to generate key: {e}")
            return None, None
    else:
        print_info(f"Using existing key at {key_path}")

    try:
        with open(pub_key_path, "r") as f:
            return f.read().strip(), key_path
    except Exception:
        return None, None

# List of patterns that are usually sensitive or too heavy to upload
SENSITIVE_PATTERNS = [
    "*.env", ".env.*",
    "*.pem", "*.key", "id_rsa", "id_dsa",
    "token.json", "credentials.json", "secrets.json",
    "pygitup.yaml",
    "node_modules",
    "venv", ".venv", "env",
    "__pycache__", "*.pyc",
    "dist", "build", "*.egg-info",
    ".git", ".idea", ".vscode"
]

class SASTVisitor(ast.NodeVisitor):
    def __init__(self):
        self.vulnerabilities = []

    def visit_Call(self, node):
        # 1. Command Injection (subprocess, os.system)
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == 'system' and isinstance(node.func.value, ast.Name) and node.func.value.id == 'os':
                self.vulnerabilities.append({
                    "line": node.lineno,
                    "type": "Command Injection",
                    "code": "os.system(...)"
                })
            elif node.func.attr in ['run', 'call', 'Popen'] and isinstance(node.func.value, ast.Name) and node.func.value.id == 'subprocess':
                # Check for shell=True
                for keyword in node.keywords:
                    if keyword.arg == 'shell' and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                        self.vulnerabilities.append({
                            "line": node.lineno,
                            "type": "Command Injection",
                            "code": f"subprocess.{node.func.attr}(..., shell=True)"
                        })

        # 2. Insecure Deserialization (pickle.load)
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == 'load' and isinstance(node.func.value, ast.Name) and node.func.value.id == 'pickle':
                self.vulnerabilities.append({
                    "line": node.lineno,
                    "type": "Insecure Deserialization",
                    "code": "pickle.load(...)"
                })

        # 3. Dynamic Execution (eval, exec)
        if isinstance(node.func, ast.Name):
            if node.func.id in ['eval', 'exec']:
                self.vulnerabilities.append({
                    "line": node.lineno,
                    "type": "Arbitrary Code Execution",
                    "code": f"{node.func.id}(...)"
                })

        self.generic_visit(node)

    def visit_Assign(self, node):
        # 4. Hardcoded Secrets
        for target in node.targets:
            if isinstance(target, ast.Name):
                name = target.id.lower()
                if any(x in name for x in ['password', 'secret', 'token', 'api_key', 'auth']):
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        val = node.value.value
                        # Filter: Ignore empty, short, or obvious placeholders
                        placeholders = ['your_', 'enter_', 'placeholder', 'token_here']
                        if len(val) > 8 and not any(p in val.lower() for p in placeholders):
                            # Detection: Known high-entropy patterns (GitHub tokens, API keys)
                            is_suspicious = False
                            if re.match(r'^(ghp_|github_pat_|AIza)[a-zA-Z0-9_]{16,}$', val):
                                is_suspicious = True
                            elif len(set(val)) / len(val) > 0.4: # Simple entropy check
                                is_suspicious = True
                                
                            if is_suspicious:
                                self.vulnerabilities.append({
                                    "line": node.lineno,
                                    "type": "Hardcoded Secret",
                                    "code": f"{target.id} = '***'"
                                })
        self.generic_visit(node)

def run_local_sast_scan(directory):
    """Scans Python code using AST analysis for semantic security flaws."""
    print_info(f"Initiating AST-based SAST scan in {directory}...")
    vulnerabilities = []
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        tree = ast.parse(f.read(), filename=path)
                        visitor = SASTVisitor()
                        visitor.visit(tree)
                        for v in visitor.vulnerabilities:
                            v['file'] = path
                            vulnerabilities.append(v)
                except Exception:
                    pass # Skip unparsable files
    
    if vulnerabilities:
        print_error(f"ALERT: {len(vulnerabilities)} CONFIRMED vulnerabilities found via AST Analysis!")
        table = Table(title="AST Security Findings", box=box.ROUNDED)
        table.add_column("Location", style="cyan")
        table.add_column("Threat", style="bold red")
        table.add_column("Snippet", style="dim")
        
        for v in vulnerabilities[:15]:
            table.add_row(f"{os.path.basename(v['file'])}:{v['line']}", v['type'], v['code'])
        console.print(table)
        return vulnerabilities
    
    print_success("Local AST scan passed. No structural vulnerabilities detected.")
    return []

def run_audit(github_username=None, repo_name=None, github_token=None):
    """Run a comprehensive security audit (Local AST + Remote Scan)."""
    print_header("Global Security Intelligence Audit")
    
    # 1. Local SAST
    run_local_sast_scan(".")
    
    # 2. Local pip-audit
    print_info("\nChecking dependencies for known vulnerabilities...")
    try:
        result = subprocess.run(["pip-audit"], capture_output=True, text=True)
        if result.returncode == 0:
            print_success("No known local vulnerabilities found via pip-audit.")
        else:
            print_warning("Local vulnerabilities detected:")
            print(result.stdout)
    except FileNotFoundError:
        print_warning("'pip-audit' not found. Skipping local dependency scan.")

    # 3. Remote GitHub Security scan
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
            else:
                print_success("No open Dependabot alerts found.")
        
        # Secret Scanning
        sec_resp = get_secret_scanning_alerts(username, repo_name, token)
        if sec_resp.status_code == 200:
            secrets = sec_resp.json()
            if secrets:
                print_error(f"ALERT: {len(secrets)} LEAKED SECRETS detected!")
            else:
                print_success("No leaked secrets detected.")
    except Exception as e:
        print_warning(f"Advanced security scan failed: {e}")

def check_is_sensitive(file_path):
    """Checks if a file path matches any sensitive patterns."""
    name = os.path.basename(file_path)
    # ... (Keep existing simple pattern matching for files)
    gitignore_patterns = []
    if os.path.exists(".gitignore"):
        with open(".gitignore", "r") as f:
            gitignore_patterns = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    all_patterns = SENSITIVE_PATTERNS + gitignore_patterns
    for pattern in all_patterns:
        if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(file_path, pattern):
            return True
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
    # ... (Keep existing implementation)
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