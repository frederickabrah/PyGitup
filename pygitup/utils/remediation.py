"""
PyGitUp Secret Remediation & History Management
================================================
Industrial tools for fixing accidental secret exposures:
- Safe Undo (Soft reset)
- Deep History Purge (File/String scrubbing)
- Force-push coordination
- Backup creation before destructive operations

WARNING: These tools rewrite git history. Use with extreme caution.
"""

import os
import subprocess
import shutil
import re
from datetime import datetime
from .ui import print_success, print_error, print_info, print_warning, print_header, Table, box, console


def remediate_secrets_workflow(config=None):
    """Workflow to scan for secrets and automatically offer remediation for each."""
    print_header("🛡️ Automatic Secret Remediation")
    
    from .security_enhanced import run_comprehensive_security_scan
    
    print_info("Scanning codebase for secrets and vulnerabilities...")
    findings = run_comprehensive_security_scan(".", include_deps=False)
    
    if not findings:
        print_success("No security issues found. Everything looks clean!")
        return True
    
    # Filter for remediable findings (secrets)
    remediable = [f for f in findings if f.category == 'credential_leak']
    
    if not remediable:
        print_info("Found vulnerabilities, but none are direct secret leaks that can be auto-purged.")
        print_info("Please review the scan report for manual remediation.")
        return True
    
    print_warning(f"Found {len(remediable)} staged or committed secrets!")
    
    for i, finding in enumerate(remediable, 1):
        print_header(f"Remediation Task {i}/{len(remediable)}")
        console.print(f"[bold red]Detected:[/bold red] {finding.title}")
        console.print(f"[bold cyan]Location:[/bold cyan] {finding.file}:{finding.line}")
        console.print(f"[bold yellow]Value:[/bold yellow] {finding.code}")
        
        print("\nChoose remediation method:")
        print("1: Purge STRING from entire history (Recommended for multi-file/multi-commit)")
        print("2: Purge FILE from entire history (Use if the whole file is sensitive)")
        print("3: Undo last commit (Use if you JUST committed this)")
        print("4: Skip this finding")
        print("5: Abort all")
        
        choice = input("\n👉 Action [1]: ") or "1"
        
        if choice == '1':
            # Extract the secret string if possible, or ask user to confirm
            secret_to_purge = input(f"Confirm exact string to redact (Default: {finding.code}): ") or finding.code
            if len(secret_to_purge) < 8:
                print_error("String too short to safely purge automatically. Please enter it manually.")
                secret_to_purge = input("Enter exact secret string: ")
            
            if secret_to_purge:
                purge_string_from_history(secret_to_purge)
        
        elif choice == '2':
            purge_file_from_history(finding.file)
            
        elif choice == '3':
            undo_last_commit()
            
        elif choice == '4':
            continue
            
        elif choice == '5':
            print_info("Remediation workflow aborted.")
            break
            
    print_success("Secret remediation workflow complete.")
    return True


def check_git_installed():
    """Verify git is installed and accessible."""
    try:
        subprocess.run(["git", "--version"], capture_output=True, check=True)
        return True
    except Exception:
        return False


def check_repo_state():
    """Check current repository state and return warnings."""
    warnings = []
    
    # Check if in git repo
    res = subprocess.run(["git", "rev-parse", "--git-dir"], capture_output=True)
    if res.returncode != 0:
        raise Exception("Not a git repository")
    
    # Check for uncommitted changes
    res = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    if res.stdout.strip():
        warnings.append("You have uncommitted changes (PyGitUp will attempt to auto-stash them).")
    
    # Check for remote
    res = subprocess.run(["git", "remote", "-v"], capture_output=True, text=True)
    if not res.stdout.strip():
        warnings.append("No remote configured - changes will be local only")
    
    # Check current branch
    res = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True)
    branch = res.stdout.strip() if res.stdout else "unknown"
    
    return warnings, branch


def create_backup():
    """Create a backup of the repository before destructive operations."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Technical Fix: Branch names cannot start with a dot
    backup_name = f"remediation_backup_{timestamp}"
    
    print_info(f"Creating backup branch: {backup_name}")
    
    try:
        # Create backup branch
        subprocess.run(["git", "branch", backup_name], check=True)
        print_success(f"Backup branch created: {backup_name}")
        print_info(f"Restore via: git reset --hard {backup_name}")
        return True
    except Exception as e:
        print_error(f"Backup creation failed: {e}")
        return False


def check_filter_repo_available():
    """Check if git-filter-repo is available and offer installation."""
    try:
        subprocess.run(["git-filter-repo", "--version"], capture_output=True)
        return True
    except Exception:
        print_info("💡 Performance Tip: 'git-filter-repo' is not installed.")
        print("   This tool is much faster and safer for history purging.")
        choice = input("   Would you like PyGitUp to install it for you? (y/n) [n]: ").lower()
        if choice == 'y':
            try:
                print_info("Installing git-filter-repo via pip...")
                subprocess.run(["pip", "install", "git-filter-repo"], check=True)
                print_success("Installation complete!")
                return True
            except Exception as e:
                print_error(f"Installation failed: {e}")
        return False


def check_bfg_available():
    """Check if BFG Repo-Cleaner is available."""
    try:
        subprocess.run(["bfg", "--version"], capture_output=True)
        return True
    except Exception:
        return False


def undo_last_commit():
    """Unstages the last commit while keeping all changes in the working directory."""
    print_header("Atomic Undo: Last Commit")
    
    # Check for dry-run mode
    import sys
    if '--dry-run' in sys.argv:
        print_info("*** DRY RUN MODE - No changes will be made ***")
        print_info("Would undo the last commit")
        result = subprocess.run(["git", "log", "-1", "--oneline"], capture_output=True, text=True)
        if result.stdout:
            print_info(f"Commit to undo: {result.stdout.strip()}")
        print_info("Your changes would remain staged")
        return True
    
    try:
        # Check if git is installed
        if not check_git_installed():
            print_error("Git is not installed or not in PATH")
            return False

        # Check repo state
        warnings, branch = check_repo_state()
        print_info(f"Current branch: {branch}")

        for w in warnings:
            print_warning(w)

        # Check if we have any commits
        res = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True)
        if res.returncode != 0:
            print_error("No commits found in this repository.")
            return False

        # Show what will be undone
        res = subprocess.run(["git", "log", "-1", "--oneline"], capture_output=True, text=True)
        if res.stdout:
            print_info(f"Will undo: {res.stdout.strip()}")

        confirm = input("\nProceed with undo? (yes/NO): ").strip().lower()
        if confirm != 'yes':
            print_info("Operation cancelled.")
            return False

        print_info("Performing soft reset to HEAD~1...")
        subprocess.run(["git", "reset", "--soft", "HEAD~1"], check=True)

        print_success("Successfully undid last commit.")
        print_info("Your changes are still staged. You can now remove secrets and re-commit.")
        print_info("\nNext steps:")
        print("  1. Remove secrets from staged files")
        print("  2. Commit again: git commit -m 'new message'")
        print("  3. If already pushed, you may need to force push: git push --force-with-lease")
        return True
    except Exception as e:
        print_error(f"Undo failed: {e}")
        return False


def purge_file_from_history(file_path):
    """Removes a file from every commit in the repository history."""
    print_header(f"Deep Purge: {file_path}")
    
    # Check for dry-run mode
    import sys
    if '--dry-run' in sys.argv:
        print_info("*** DRY RUN MODE - No changes will be made ***")
        print_warning("CRITICAL: This would rewrite your entire repository history!")
        print_info("All other contributors would need to re-clone or rebase")
        
        # Check if file exists in history
        res = subprocess.run(["git", "log", "--all", "--full-history", "--", file_path], 
                           capture_output=True, text=True)
        if not res.stdout.strip():
            print_error(f"File '{file_path}' not found in repository history.")
            return False
        
        # Show commits containing the file
        res = subprocess.run(["git", "log", "--oneline", "--", file_path], 
                           capture_output=True, text=True)
        if res.stdout:
            commit_count = len(res.stdout.strip().split('\n'))
            print_info(f"File found in {commit_count} commits:")
            for line in res.stdout.strip().split('\n')[:5]:
                print(f"  {line}")
            if commit_count > 5:
                print(f"  ... and {commit_count - 5} more")
        
        print_info("\nWould purge this file from ALL commits")
        print_info("Would create backup branch before proceeding")
        return True
    
    print_warning("CRITICAL: This will rewrite your entire repository history!")
    print_warning("All other contributors will need to re-clone or rebase.")
    
    try:
        # Check if git is installed
        if not check_git_installed():
            print_error("Git is not installed or not in PATH")
            return False
        
        # Check repo state
        warnings, branch = check_repo_state()
        for w in warnings:
            print_warning(f"⚠️  {w}")
        
        # Check if file exists in history
        res = subprocess.run(["git", "log", "--all", "--full-history", "--", file_path], 
                           capture_output=True, text=True)
        if not res.stdout.strip():
            print_error(f"File '{file_path}' not found in repository history.")
            return False
        
        # Show commits containing the file
        res = subprocess.run(["git", "log", "--oneline", "--", file_path], 
                           capture_output=True, text=True)
        if res.stdout:
            print_info(f"File found in {len(res.stdout.strip().split(chr(10)))} commits:")
            for line in res.stdout.strip().split('\n')[:5]:
                print(f"  {line}")
            if len(res.stdout.strip().split('\n')) > 5:
                print(f"  ... and {len(res.stdout.strip().split(chr(10))) - 5} more")
        
        # Create backup
        print("\nCreating backup branch...")
        if not create_backup():
            print_error("Backup creation failed. Aborting operation.")
            return False
        
        confirm = input(f"\nAre you absolutely sure you want to delete '{file_path}' from ALL commits? (yes/NO): ").strip().lower()
        if confirm != 'yes':
            print_info("Operation cancelled.")
            return False
        
        # Check for better tools
        use_filter_repo = check_filter_repo_available()
        use_bfg = check_bfg_available()
        
        if use_bfg:
            print_info("\n🚀 Executing BFG Repo-Cleaner...")
            try:
                subprocess.run(["bfg", "--delete-files", file_path], check=True, capture_output=True)
                print_success(f"Successfully purged '{file_path}' using BFG.")
                return True # Success
            except Exception as e:
                print_warning(f"BFG engine encountered a problem: {e}")
                print_info("Falling back to alternative engines...")
                use_bfg = False
        
        if use_filter_repo and not use_bfg:
            print_info("\n🚀 Executing git-filter-repo...")
            try:
                subprocess.run(["git-filter-repo", "--invert-path", "--path", file_path, "--force"], check=True, capture_output=True)
                print_success(f"Successfully purged '{file_path}' using git-filter-repo.")
                return True # Success
            except Exception as e:
                print_warning(f"git-filter-repo engine encountered a problem: {e}")
                print_info("Falling back to reliable internal sequence...")
                use_filter_repo = False
        
        # Fallback to filter-branch
        if not use_bfg and not use_filter_repo:
            print_info("\nUsing git filter-branch (slower but reliable)...")
            cmd = [
                "git", "filter-branch", "--force", "--index-filter",
                f"git rm --cached --ignore-unmatch {file_path}",
                "--prune-empty", "--tag-name-filter", "cat", "--", "--all"
            ]

            env = os.environ.copy()
            env["FILTER_BRANCH_SQUELCH_WARNING"] = "1"

            subprocess.run(cmd, check=True, env=env)
            print_success(f"Successfully purged '{file_path}' from all history.")
        
        print_info("\n✅ Purge complete!")
        print_info("\nNext steps:")
        print("  1. Verify the file is removed: git log --all --full-history -- " + file_path)
        print("  2. Force push to update remote: git push origin --force --all")
        print("  3. Delete backup branch when verified: git branch -D .git_backup_*")
        print("\n⚠️  CRITICAL REMINDERS:")
        print("  • Any secrets in that file are COMPROMISED - ROTATE THEM NOW")
        print("  • All collaborators must re-clone: git clone <repo-url>")
        print("  • Or fetch and reset: git fetch --all && git reset --hard origin/" + branch)
        return True
    except Exception as e:
        print_error(f"Purge failed: {e}")
        return False


def escape_sed_string(s):
    """Escape special characters for sed replacement."""
    # Escape special sed characters
    s = s.replace('\\', '\\\\')
    s = s.replace('/', '\\/')
    s = s.replace('&', '\\&')
    s = s.replace('$', '\\$')
    s = s.replace('.', '\\.')
    s = s.replace('*', '\\*')
    s = s.replace('[', '\\[')
    s = s.replace(']', '\\]')
    return s


def purge_string_from_history(secret_string):
    """Uses a specialized pattern to replace a string across all history."""
    print_header("Deep Purge: Sensitive String")
    
    if len(secret_string) < 8:
        print_error("Secret string too short for safe purging (min 8 chars).")
        print_info("Short strings may cause false positives.")
        return False
    
    if len(secret_string) > 100:
        print_warning("Very long string detected - this may take a while.")
    
    try:
        # Check if git is installed
        if not check_git_installed():
            print_error("Git is not installed or not in PATH")
            return False
        
        # Check repo state
        warnings, branch = check_repo_state()
        for w in warnings:
            print_warning(f"⚠️  {w}")
        
        # Create backup
        print("\nCreating backup branch...")
        if not create_backup():
            print_error("Backup creation failed. Aborting operation.")
            return False
        
        print_warning("This will replace the specified string with '***REDACTED***' in all commits.")
        print_warning("⚠️  WARNING: This may break binary files or cause merge conflicts.")
        
        confirm = input("\nProceed with history rewrite? (yes/NO): ").strip().lower()
        if confirm != 'yes':
            print_info("Operation cancelled.")
            return False
        
        # Escape the secret string for sed
        escaped_secret = escape_sed_string(secret_string)
        
        # Check for better tools
        use_filter_repo = check_filter_repo_available()
        
        if use_filter_repo:
            print_info("\n✅ git-filter-repo detected - using for better results...")
            try:
                # Create a blob callback for filter-repo
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f:
                    f.write(f"""#!/usr/bin/env python3
import sys
import re

secret = r'{escaped_secret}'
replacement = b'***REDACTED***'

for line in sys.stdin:
    line = line.encode() if isinstance(line, str) else line
    sys.stdout.buffer.write(line.replace(secret.encode(), replacement))
""")
                    script_path = f.name
                
                subprocess.run(["git-filter-repo", "--blob-callback", f"""
import re
secret = r'{escaped_secret}'.encode()
replacement = b'***REDACTED***'
if secret in blob.data:
    blob.data = blob.data.replace(secret, replacement)
""", "--force"], check=True)
                
                os.unlink(script_path)
                print_success("String redaction complete using git-filter-repo.")
            except Exception as e:
                print_warning(f"git-filter-repo failed: {e}")
                use_filter_repo = False
        
        # Fallback to filter-branch with sed
        if not use_filter_repo:
            print_info("\nUsing git filter-branch with sed...")
            print_warning("Note: This may not work perfectly with binary files.")
            
            # Create a safer sed command
            sed_cmd = f"sed -i 's/{escaped_secret}/***REDACTED***/g'"
            
            cmd = [
                "git", "filter-branch", "--force", "--tree-filter",
                f"find . -type f -name '*.py' -o -name '*.js' -o -name '*.ts' -o -name '*.java' -o -name '*.go' -o -name '*.rb' -o -name '*.php' -o -name '*.env' -o -name '*.json' -o -name '*.yaml' -o -name '*.yml' -o -name '*.txt' -o -name '*.md' -o -name '*.sh' -o -name '*.bash' | xargs -I {{}} {sed_cmd} {{}} || true",
                "--tag-name-filter", "cat", "--", "--all"
            ]

            env = os.environ.copy()
            env["FILTER_BRANCH_SQUELCH_WARNING"] = "1"

            print_info("Scanning text files and redacting string...")
            subprocess.run(cmd, check=True, env=env)
            print_success("Redaction complete across all branches.")
        
        print_info("\n✅ Redaction complete!")
        print_info("\nNext steps:")
        print("  1. Verify redaction: git log -p --all | grep -i REDACTED")
        print("  2. Force push to update remote: git push origin --force --all")
        print("  3. Delete backup branch when verified: git branch -D .git_backup_*")
        print("\n⚠️  CRITICAL REMINDERS:")
        print("  • The secret is still visible in the backup branch")
        print("  • ROTATE the compromised secret immediately")
        print("  • All collaborators must re-clone the repository")
        return True
    except Exception as e:
        print_error(f"Redaction failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def show_remediation_help():
    """Show comprehensive remediation guidance."""
    print_header("Secret Remediation Guide")
    
    print("""
📋 REMEDIATION WORKFLOW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. IMMEDIATE ACTIONS (Do these FIRST):
   ✓ Rotate the exposed secret immediately
   ✓ Revoke the compromised credential
   ✓ Check for unauthorized access

2. CHOOSE REMEDIATION METHOD:
   
   Method A: Undo Last Commit (Option 41)
   - Use if: Secret was just committed, not pushed
   - Safe: Preserves all changes
   - Result: Commit undone, changes staged
   
   Method B: Purge File from History (Option 42)
   - Use if: File with secrets in multiple commits
   - Destructive: Rewrites entire history
   - Result: File removed from all commits
   
   Method C: Purge String from History (Option 43)
   - Use if: Secret string in multiple files/commits
   - Very Destructive: May break binary files
   - Result: String replaced with ***REDACTED***

   Ghost Editing (Integrated in Option 44):
   - Use if: Target repository is not on your system
   - Process: Ephemeral clone → Edit → Force Push → Vanish
   - Result: Cloud repository updated without local clutter

3. POST-REMEDIATION:
   ✓ Force push: git push origin --force --all
   ✓ Notify collaborators to re-clone
   ✓ Delete backup branches when verified
   ✓ Update CI/CD secrets if compromised

4. PREVENTION:
   ✓ Add file to .gitignore
   ✓ Use pre-commit hooks (e.g., detect-secrets)
   ✓ Use environment variables for secrets
   ✓ Enable GitHub secret scanning

🛠️  INTEGRATED ENGINES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PyGitUp automatically leverages the following industrial tools if 
they are installed on your system, providing elite performance:

• git-filter-repo: (Recommended) Faster and safer than filter-branch.
  - Install: pip install git-filter-repo

• BFG Repo-Cleaner: 10-720x faster than standard git tools.
  - Great for massive repositories.

• Internal Fallback: If no external tools are found, PyGitUp uses 
  a secure 'git filter-branch' sequence to ensure remediation.

⚠️  WARNINGS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• History rewriting is DESTRUCTIVE
• Always create backups before proceeding
• All collaborators must re-clone after history rewrite
• Secrets in backup branches are still visible
• GitHub may cache commits for a short period

📞 ADDITIONAL RESOURCES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• GitHub Secret Scanning: https://docs.github.com/en/code-security/secret-scanning
• Git Filter Repo: https://htmlpreview.github.io/?https://github.com/newren/git-filter-repo/blob/docs/html/git-filter-repo.html
• BFG Repo-Cleaner: https://rtyley.github.io/bfg-repo-cleaner/
""")

def interactive_commit_manager():
    """Industrial UI for managing recent commits with Context and Ghost Editing."""
    print_header("Interactive History Manager")

    current_dir = os.getcwd()
    console.print(f"\n[cyan]Current Context:[/cyan] {current_dir}")

    # Check for uncommitted changes BEFORE proceeding
    res = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    if res.stdout.strip():
        print_warning("⚠️  You have uncommitted changes!")
        print_warning("These changes may be lost during history editing.")
        print_info("Recommended actions:")
        print("  1. Commit changes: git add . && git commit -m 'WIP'")
        print("  2. Stash changes: git stash")
        print("  3. Discard changes: git checkout -- .")
        choice = input("\nProceed anyway? (y/n): ").strip().lower()
        if choice != 'y':
            print_info("Operation cancelled. Please save or stash your changes first.")
            return

    console.print("\n[bold]Select Context:[/bold]")
    console.print("  [1] Manage Current Directory")
    console.print("  [2] Manage Other Local Repository (Path)")
    console.print("  [3] Ghost Edit Remote Repository (GitHub Name)")

    choice = input("\n👉 Choice [1]: ") or "1"

    temp_mode = False
    temp_dir = ""

    if choice == '2':
        target_path = input("Enter path to target repository: ").strip()
        if os.path.isdir(target_path):
            os.chdir(target_path)
            print_success(f"Switched context to: {target_path}")
        else:
            print_error(f"Invalid directory: {target_path}")
            return
    elif choice == '3':
        # FIX BUG #5: Add repository name validation
        import re
        repo_name = input("Enter GitHub repository (e.g., user/repo): ").strip()
        if not repo_name:
            print_error("Repository name required")
            return
        
        # Validate format: user/repo
        if not re.match(r'^[a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+$', repo_name):
            print_error("Invalid repository format. Use: user/repo")
            return
        
        # FIX BUG #6: Make clone depth configurable
        print_info("How many commits to fetch? (default: 100, 0 for full history)")
        try:
            depth = int(input("👉 Depth [100]: ") or "100")
            if depth <= 0:
                depth = None  # Full history
        except ValueError:
            depth = 100

        # Ghost Editing Logic
        import tempfile
        temp_dir = tempfile.mkdtemp(prefix="pygitup_ghost_")
        temp_mode = True

        from ..core.config import load_config, get_github_token
        config = load_config()
        token = get_github_token(config)

        print_info(f"Initiating Ghost Clone into {temp_dir}...")
        try:
            # FIX BUG #2: Use credential helper instead of exposing token in URL
            # Write token to a temporary credential helper script
            import stat
            
            # Create a temporary credential helper
            helper_script = os.path.join(temp_dir, ".git_helper.sh")
            with open(helper_script, 'w') as f:
                f.write(f"#!/bin/bash\necho '{token}'\n")
            os.chmod(helper_script, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)  # 700 permissions
            
            # Configure git to use the helper
            env = os.environ.copy()
            env['GIT_ASKPASS'] = helper_script
            
            # Clone using the credential helper (token not visible in ps)
            clone_url = f"https://github.com/{repo_name}.git"
            clone_cmd = ["git", "clone"]
            if depth:
                clone_cmd.extend(["--depth", str(depth)])
            clone_cmd.extend([clone_url, temp_dir])
            
            subprocess.run(clone_cmd, check=True, capture_output=True, env=env)
            
            # Clean up helper script
            os.remove(helper_script)
            
            os.chdir(temp_dir)
            print_success("Ghost Context Active.")
        except Exception as e:
            print_error(f"Ghost Clone failed: {e}")
            # FIX BUG #4: Ensure cleanup even on clone failure
            shutil.rmtree(temp_dir, ignore_errors=True)
            return

    try:
        # Check if git is installed
        if not check_git_installed():
            print_error("Git is not installed or not in PATH")
            return

        # 1. Fetch recent commits
        cmd = ["git", "log", "-n", "15", "--pretty=format:%h|%ar|%s"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print_error("Failed to fetch Git history. Are you in a repository?")
            return

        lines = result.stdout.splitlines()
        if not lines:
            print_info("No commits found.")
            return

        # 2. Display organized table
        table = Table(title="Recent Commits", box=box.ROUNDED)
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Time", style="green")
        table.add_column("Message", style="white")

        commits = []
        for i, line in enumerate(lines):
            parts = line.split('|')
            if len(parts) >= 3:
                commits.append({"hash": parts[0], "msg": parts[2]})
                table.add_row(f"{i+1}: {parts[0]}", parts[1], parts[2])

        console.print(table)

        # 3. User Selection
        choice = input("\n👉 Enter Commit Number to manage (or 'q' to quit): ")
        if choice.lower() == 'q' or not choice: return

        try:
            idx = int(choice) - 1
        except ValueError:
            print_error("Invalid input. Please enter a number.")
            return

        if not (0 <= idx < len(commits)):
            print_error("Selection out of range.")
            return

        selected = commits[idx]
        console.print(f"\n[bold cyan]Managing Commit:[/bold cyan] {selected['hash']} ('{selected['msg']}')")
        
        # Technical Warning: Deep Rebase Risk
        if idx > 5:
            console.print("\n[bold yellow]⚠️  TECHNICAL WARNING:[/bold yellow] Deep history modification detected.")
            console.print("   Modifying older commits (5+ back) often causes merge conflicts.")
            console.print("   PyGitUp will create a backup, but proceed with caution.")

        console.print("\n  1: [yellow]Edit Message[/yellow]")
        console.print("  2: [red]Delete (Drop) Commit[/red]")
        console.print("  3: [white]Cancel[/white]")
        
        action = input("\n👉 Action: ")
        
        if action == '1':
            # Edit Message logic
            if idx == 0:
                # Easiest case: last commit
                subprocess.run(["git", "commit", "--amend"], check=True)
                print_success("Commit message updated.")
            else:
                print_warning("Technical Note: This requires an interactive rebase.")
                print_info(f"Running: git rebase -i {selected['hash']}^")
                # We launch the standard rebase tool for maximum reliability
                subprocess.run(["git", "rebase", "-i", f"{selected['hash']}^"], check=True)
        
        elif action == '2':
            # Delete Commit logic
            console.print(f"\n[bold red]CRITICAL:[/bold red] This will remove commit {selected['hash']} permanently!")
            confirm = input("Confirm deletion? (y/n): ")
            if confirm.lower() != 'y':
                print_info("Deletion cancelled.")
                return
            
            # FIX BUG #1: Import create_backup from agent_tools
            from .agent_tools import create_git_checkpoint
            
            # 1. Create backup FIRST
            checkpoint_id = create_git_checkpoint(f"Before deleting {selected['hash']}")
            if checkpoint_id:
                print_success(f"Backup created: {checkpoint_id}")
            else:
                print_warning("Could not create backup. Proceed with extreme caution.")

            # 2. Handle dirty worktree
            res = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
            stashed = False
            if res.stdout.strip():
                print_info("Unstaged changes detected. Stashing for safety...")
                subprocess.run(["git", "stash", "push", "-m", "PyGitUp Remediation Auto-Stash"], check=True)
                stashed = True

            # 3. FIX BUG #3: Use safe rebase with sequence editor
            print_info(f"Dropping commit {selected['hash']}...")
            try:
                # Create a safe rebase sequence editor script
                import tempfile
                import stat
                
                # Create editor script that replaces 'pick' with 'drop' for our commit
                editor_script = tempfile.mktemp(suffix='.sh')
                with open(editor_script, 'w') as f:
                    f.write(f"#!/bin/bash\n")
                    f.write(f"# Auto-drop commit {selected['hash']}\n")
                    f.write(f"sed -i.bak 's/^pick {selected['hash']}/drop {selected['hash']}/' \"$1\"\n")
                
                os.chmod(editor_script, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)  # 700 permissions
                
                # Run interactive rebase with our custom sequence editor
                env = os.environ.copy()
                env['GIT_SEQUENCE_EDITOR'] = editor_script
                
                # Start from the parent of the commit to delete
                parent_commit = f"{selected['hash']}^"
                subprocess.run(["git", "rebase", "-i", parent_commit], check=True, env=env)
                
                # Clean up editor script and backup
                try:
                    os.remove(editor_script)
                    os.remove(editor_script + '.bak')
                except:
                    pass
                
                print_success("Commit deleted from history.")
                print_info("Use 'git push --force-with-lease' to update remote.")
                
            except Exception as rebase_err:
                print_error(f"Rebase failed: {rebase_err}")
                print_info("Attempting to abort rebase...")
                subprocess.run(["git", "rebase", "--abort"], capture_output=True)
            finally:
                if stashed:
                    print_info("Restoring your stashed changes...")
                    subprocess.run(["git", "stash", "pop"], capture_output=True)

    except Exception as e:
        print_error(f"History management failed: {e}")
    finally:
        # Restoration logic
        os.chdir(current_dir)
        if temp_mode and temp_dir:
            print_info("Cleaning up Ghost environment...")
            shutil.rmtree(temp_dir, ignore_errors=True)
