import subprocess
import os
import fnmatch

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

def run_audit():
    """Run a security audit on the project dependencies."""
    print("Running security audit on project dependencies...")
    try:
        result = subprocess.run(["pip-audit"], capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("Audit Warnings/Errors:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("\nAudit complete: No known vulnerabilities found.")
        elif result.returncode == 1:
            print("\nAudit complete: Vulnerabilities were found (listed above).")
        else:
            print(f"\nAn unexpected error occurred during the audit. Exit code: {result.returncode}")

    except FileNotFoundError:
        print("Error: 'pip-audit' is not installed. Please install it by running 'pip install pip-audit'")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def check_is_sensitive(file_path):
    """Checks if a file path matches any sensitive patterns."""
    name = os.path.basename(file_path)
    for pattern in SENSITIVE_PATTERNS:
        if fnmatch.fnmatch(name, pattern):
            return True
        # Check for directory matches (e.g. node_modules/)
        if pattern in file_path.split(os.sep):
            return True
    return False

def audit_files_and_prompt(files):
    """
    Scans a list of files for sensitive content.
    Returns: The list of files to proceed with (filtered or original).
    """
    sensitive_matches = [f for f in files if check_is_sensitive(f)]
    
    if not sensitive_matches:
        return files

    print("\n" + "!" * 50)
    print("SECURITY WARNING: Sensitive or heavy files detected!")
    print("!" * 50)
    print("The following files look like they shouldn't be uploaded:")
    for f in sensitive_matches[:10]:
        print(f" - {f}")
    if len(sensitive_matches) > 10:
        print(f" ... and {len(sensitive_matches) - 10} more.")
    
    while True:
        print("\nHow do you want to proceed?")
        print("1. Skip these files (Recommended)")
        print("2. Upload them anyway (I know what I'm doing)")
        print("3. Cancel operation")
        
        choice = input("Enter choice (1-3): ").strip()
        
        if choice == "1":
            safe_files = [f for f in files if f not in sensitive_matches]
            print(f"Skipped {len(sensitive_matches)} sensitive files.")
            return safe_files
        elif choice == "2":
            print("Proceeding with all files.")
            return files
        elif choice == "3":
            print("Operation cancelled by user.")
            return []
        else:
            print("Invalid choice. Please try again.")

def scan_directory_for_sensitive_files(directory):
    """
    Scans a directory for sensitive files before git add.
    Returns: True if safe to proceed, False if cancelled.
    If 'Skip' is selected, it appends to .gitignore.
    """
    detected = []
    for root, dirs, files in os.walk(directory):
        # Check dirs to prune checking inside node_modules etc
        sensitive_dirs = [d for d in dirs if check_is_sensitive(d)]
        for d in sensitive_dirs:
            detected.append(os.path.join(root, d) + "/")
        
        # Check files
        for f in files:
            full_path = os.path.join(root, f)
            if check_is_sensitive(full_path):
                detected.append(full_path)

    if not detected:
        return True

    print("\n" + "!" * 50)
    print("SECURITY WARNING: Sensitive files detected in this directory!")
    print("!" * 50)
    print("Found potential issues:")
    for f in detected[:10]:
        print(f" - {f}")
    if len(detected) > 10:
        print(f" ... and {len(detected) - 10} more.")

    while True:
        print("\nHow do you want to proceed?")
        print("1. Add them to .gitignore (Recommended)")
        print("2. Upload them anyway (Risky)")
        print("3. Cancel operation")
        
        choice = input("Enter choice (1-3): ").strip()
        
        if choice == "1":
            gitignore_path = os.path.join(directory, ".gitignore")
            try:
                with open(gitignore_path, "a") as f:
                    f.write("\n# Added by PyGitUp Security Check\n")
                    for item in detected:
                        # Convert to relative path for gitignore
                        rel_path = os.path.relpath(item, directory)
                        f.write(f"{rel_path}\n")
                print("Updated .gitignore with sensitive files.")
                return True
            except Exception as e:
                print(f"Error writing to .gitignore: {e}")
                return False
        elif choice == "2":
            return True
        elif choice == "3":
            return False
        else:
            print("Invalid choice.")