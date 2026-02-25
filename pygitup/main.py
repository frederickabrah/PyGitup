import sys
import os

from .core.args import create_parser
from .core.config import load_config, get_github_username, get_github_token, configuration_wizard, list_profiles, set_active_profile, get_active_profile_path, check_crypto_installed
from .project.project_ops import upload_project_directory, upload_single_file, upload_batch_files, update_multiple_repos, manage_bulk_repositories, migrate_repository
from .project.templates import create_project_from_template
from .github.releases import create_release_tag
from .project.issues import scan_todos, list_and_triage_issues
from .utils.offline import queue_offline_commit, process_offline_queue
from .github.pull_requests import manage_pull_requests, request_code_review
from .git.push import smart_push
from .project.docs import generate_documentation
from .utils.analytics import generate_analytics
from .utils.ai import ai_commit_workflow, list_available_ai_models
from .git.branch import manage_branches
from .git.stash import manage_stashes
from .git.tag import manage_tags
from .git.cherry_pick import cherry_pick_commit
from .github.gists import manage_gists
from .github.webhooks import manage_webhooks
from .github.actions import manage_actions
from .utils.security import run_audit
from .utils.security_enhanced import run_comprehensive_security_scan, get_security_report, AUDIT_LOGGER, AuditEventType
from .utils.token_manager import display_token_health_report, get_token_tracker, get_rotation_manager, check_token_health
from .utils.supply_chain import run_supply_chain_scan, generate_sbom_spdx, generate_sbom_cyclonedx
from .github.repo import manage_repo_visibility, delete_repository
from .github.repo_info import get_detailed_repo_info, get_fork_intelligence, parse_github_url
from .github.ssh_ops import setup_ssh_infrastructure
from .ui.app import run_tui
from .utils.banner import show_banner
from .utils.ui import display_menu, print_error, print_success, print_info, console, print_header
from .utils.update import check_for_updates
from .github.api import github_request, star_repo, follow_user, check_rate_limit

def auto_star_and_follow(token):
    """Automatic Star and Follow integration."""
    try:
        owner = "frederickabrah"
        repo = "PyGitUp"
        
        # 1. Check & Star the repo
        # GET returns 204 if starred, 404 if not
        check_star_url = f"https://api.github.com/user/starred/{owner}/{repo}"
        if github_request("GET", check_star_url, token).status_code == 404:
            star_repo(owner, repo, token)
        
        # 2. Check & Follow the user
        # GET returns 204 if following, 404 if not
        check_follow_url = f"https://api.github.com/user/following/{owner}"
        if github_request("GET", check_follow_url, token).status_code == 404:
            follow_user(owner, token)
    except Exception as e:
        if os.environ.get("PYGITUP_DEBUG"):
            print_warning(f"Community integration limited: {e}")

def main():
    """Main function to orchestrate the process."""
    try:
        show_banner()
        check_for_updates()

        # Smart Start: Check if we are in a git repo
        if not os.path.isdir(".git") and not any(arg in sys.argv for arg in ["--help", "init", "clone", "migrate", "template"]):
            print_info("You are not currently in a Git repository.")
            target_path = input("📂 Enter the path to your project (or Enter to stay here): ").strip()
            if target_path:
                # Security Patch: Normalize and validate path to prevent injection
                target_path = os.path.abspath(os.path.expanduser(target_path))
                
                if os.path.isdir(target_path):
                    try:
                        os.chdir(target_path)
                        print_success(f"Switched context to: {os.getcwd()}")
                    except Exception as e:
                        print_error(f"Could not switch directory: {e}")
                else:
                    print_error(f"Invalid or inaccessible directory: {target_path}")

        # Parse command line arguments
        parser = create_parser()
        args = parser.parse_args()
        
        # Load configuration
        config = load_config(args.config)

        # Security: Check for encryption library
        check_crypto_installed()

        # Prompt for master password if encrypted data exists
        from pygitup.core import config as config_module
        salt = config.get("security", {}).get("salt", "")
        if salt and config_module._SESSION_KEY is None:
            token_value = config["github"].get("token", "")
            # Check if token looks encrypted (starts with gAAAA) OR is empty (failed decryption)
            if (token_value and token_value.startswith("gAAAA")) or (not token_value and salt):
                # Token is encrypted or decryption failed, need password
                try:
                    from pygitup.core.config import get_master_key
                    get_master_key(bytes.fromhex(salt))
                    # Reload config now that we have the decryption key
                    config = load_config(args.config)
                except Exception as e:
                    print_error(f"Failed to decrypt credentials: {e}")
                    print_info("Run Option 14 to reconfigure")

        # Auto-Setup Wizard if credentials missing
        if not config["github"].get("username") or not config["github"].get("token"):
            print_info("No existing credentials found. Starting initial setup...")
            configuration_wizard()
            # Reload after setup
            config = load_config(args.config)

        # Get credentials
        github_username = get_github_username(config)
        github_token = get_github_token(config)

        # Security Upgrade: Proactive Token Validation
        if github_token:
            from .utils.token_manager import get_token_tracker
            tracker = get_token_tracker()
            if not tracker._validate_token(github_token):
                print_error("🚨 AUTHENTICATION FAILURE: Your stored GitHub token appears to be REVOKED or INVALID.")
                print_info("Please run Option 39 (Rotate GitHub Token) to restore access.")
            else:
                # --- COMMUNITY INTEGRATION ---
                auto_star_and_follow(github_token)
        
        # Process offline queue if not in queue processing mode
        if args.mode != "process-queue":
            process_offline_queue(github_username, github_token, config)
        
        # Persistent loop for interactive mode
        is_interactive = not args.mode
        
        while True:
            # Determine mode
            mode = args.mode
            if not mode:
                menu_options = {
                    '1': ("Upload/update a whole project directory", "project"),
                    '2': ("Upload/update a single file", "file"),
                    '3': ("Batch upload multiple files", "batch"),
                    '4': ("Create project from template", "template"),
                    '5': ("Create GitHub release", "release"),
                    '6': ("Update file in multiple repositories", "multi-repo"),
                    '7': ("Scan for TODOs and create issues", "scan-todos"),
                    '8': ("Queue commit for offline", "offline-queue"),
                    '9': ("Process offline commit queue", "process-queue"),
                    '10': ("Request code review", "request-review"),
                    '11': ("Smart push with commit squashing", "smart-push"),
                    '12': ("Generate documentation", "generate-docs"),
                    '13': ("Generate collaboration analytics", "analytics"),
                    '14': ("Run the configuration wizard", "configure"),
                    '15': ("Manage branches", "branch"),
                    '16': ("Manage stashes", "stash"),
                    '17': ("Manage tags", "tag"),
                    '18': ("Cherry-pick a commit", "cherry-pick"),
                    '19': ("Manage Gists", "gist"),
                    '20': ("Manage Webhooks", "webhook"),
                    '21': ("Manage GitHub Actions", "actions"),
                    '22': ("Manage Pull Requests", "pr"),
                    '23': ("Run security audit (Local + GitHub)", "audit"),
                    '24': ("Change repository visibility", "visibility"),
                    '25': ("Get repository info from URL", "repo-info"),
                    '26': ("Delete GitHub repository", "delete-repo"),
                    '27': ("Bulk Repository Management & Health", "bulk-mgmt"),
                    '28': ("Migrate/Mirror Repository from any source", "migrate"),
                    '29': ("Network & Fork Intelligence (OSINT)", "fork-intel"),
                    '30': ("AI-Powered Semantic Commit", "ai-commit"),
                    '31': ("Manage Accounts (Switch/Add/List)", "accounts"),
                    '32': ("AI Diagnostic (List Available Models)", "ai-diagnostic"),
                    '33': ("SSH Key Infrastructure Manager", "ssh-setup"),
                    '34': ("Launch TUI Dashboard", "tui"),
                    '35': ("🔒 Enhanced Security Scan (SAST + Secrets)", "security-scan"),
                    '36': ("🔐 Token Health & Rotation", "token-health"),
                    '37': ("📦 Supply Chain Security Scan", "supply-chain"),
                    '38': ("📄 Generate SBOM (Software Bill of Materials)", "generate-sbom"),
                    '39': ("🔄 Rotate GitHub Token", "rotate-token"),
                    '40': ("📋 Interactive Issue Triage & AI Analysis", "issue-triage"),
                    '41': ("↩️  Undo Last Commit (Soft Reset)", "undo-commit"),
                    '42': ("🧹 Purge File from Git History", "purge-file"),
                    '43': ("✂️  Purge Sensitive String from History", "purge-string"),
                    '44': ("📝 Interactive History Editor (Edit/Delete Commits)", "edit-history"),
                    '45': ("📖 Remediation Help & Guide", "remediation-help"),
                    '0': ("Exit PyGitUp", "exit")
                }

                display_menu(menu_options)
                max_choice = max([int(k) for k in menu_options.keys() if k.isdigit()])
                choice = input(f"\n👉 Enter your choice (0-{max_choice}): ")
                
                if choice == '0':
                    print_info("Goodbye! 🚀")
                    break

                selected_option = menu_options.get(choice)
                if not selected_option:
                    print_error("Invalid choice. Try again.")
                    continue
                mode = selected_option[1]

            # Execute the corresponding function based on the mode
            if mode == "project":
                upload_project_directory(github_username, github_token, config, args)
            elif mode == "file":
                upload_single_file(github_username, github_token, config, args)
            elif mode == "batch":
                upload_batch_files(github_username, github_token, config, args)
            elif mode == "template":
                create_project_from_template(github_username, github_token, config, args)
            elif mode == "release":
                create_release_tag(github_username, github_token, config, args)
            elif mode == "multi-repo":
                update_multiple_repos(github_username, github_token, config, args)
            elif mode == "scan-todos":
                scan_todos(github_username, github_token, config, args)
            elif mode == "offline-queue":
                queue_offline_commit(config, args)
            elif mode == "process-queue":
                process_offline_queue(github_username, github_token, config, args)
            elif mode == "request-review":
                request_code_review(github_username, github_token, config, args)
            elif mode == "smart-push":
                smart_push(github_username, github_token, config, args)
            elif mode == "generate-docs":
                generate_documentation(github_username, github_token, config, args)
            elif mode == "analytics":
                generate_analytics(github_username, github_token, config, args)
            elif mode == "configure":
                configuration_wizard()
                config = load_config(args.config)
                github_username = get_github_username(config)
                github_token = get_github_token(config)
            elif mode == "branch":
                manage_branches(args)
            elif mode == "stash":
                manage_stashes(args)
            elif mode == "tag":
                manage_tags(args)
            elif mode == "cherry-pick":
                cherry_pick_commit(args)
            elif mode == "gist":
                manage_gists(args, github_username, github_token)
            elif mode == "webhook":
                manage_webhooks(args, github_username, github_token)
            elif mode == "actions":
                manage_actions(args, github_username, github_token, config)
            elif mode == "pr":
                manage_pull_requests(args, github_username, github_token)
            elif mode == "audit":
                repo_to_audit = args.repo if args and hasattr(args, 'repo') and args.repo else input("Enter repo name for GitHub security scan: ")
                run_audit(github_username, repo_to_audit, github_token)
            elif mode == "visibility":
                manage_repo_visibility(args, github_username, github_token)
            elif mode == "repo-info":
                get_detailed_repo_info(args, github_token)
            elif mode == "delete-repo":
                delete_repository(args, github_username, github_token)
            elif mode == "bulk-mgmt":
                manage_bulk_repositories(github_token)
            elif mode == "migrate":
                migrate_repository(github_username, github_token, config, args)
            elif mode == "fork-intel":
                url = args.url if args and hasattr(args, 'url') and args.url else input("Enter repository URL: ")
                owner, repo_name = parse_github_url(url)
                if owner and repo_name:
                    get_fork_intelligence(owner, repo_name, github_token)
                else:
                    print_error("Invalid repository URL.")
            elif mode == "ai-commit":
                ai_commit_workflow(github_username, github_token, config)
            elif mode == "ai-diagnostic":
                ai_key = config["github"].get("ai_api_key")
                list_available_ai_models(ai_key)
            elif mode == "ssh-setup":
                setup_ssh_infrastructure(config, github_token)
            elif mode == "tui":
                run_tui()
            elif mode == "accounts":
                print_header("Account & Profile Manager")
                profiles = list_profiles()
                active_path = get_active_profile_path()
                active_name = os.path.basename(active_path).replace(".yaml", "")
                console.print(f"Current Active Profile: [bold green]{active_name}[/bold green]")
                print("\nAvailable Profiles:")
                for p in profiles:
                    marker = "➜ " if p == active_name else "  "
                    print(f"{marker}{p}")
                print("\n[bold]Options:[/bold]")
                print("1: Switch Profile")
                print("2: Add New Account")
                print("3: Force Update Token (if old token is revoked)")
                print("4: Back")
                acc_choice = input("\n👉 Choice: ")
                if acc_choice == '1':
                    target = input("Enter profile name to switch to: ")
                    success, msg = set_active_profile(target)
                    if success:
                        print_success(msg)
                        config = load_config(args.config)
                        github_username = get_github_username(config)
                        github_token = get_github_token(config)
                    else:
                        print_error(msg)
                elif acc_choice == '2':
                    configuration_wizard()
                    config = load_config(args.config)
                    github_username = get_github_username(config)
                    github_token = get_github_token(config)
                elif acc_choice == '3':
                    print_info("\nForce Token Update - Use when old token is revoked")
                    new_token = input("Enter your new GitHub token: ").strip()
                    if new_token:
                        try:
                            import getpass
                            import yaml
                            import base64
                            from cryptography.hazmat.primitives import hashes
                            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
                            from cryptography.fernet import Fernet
                            
                            profile_path = get_active_profile_path()
                            profile_name = os.path.basename(profile_path).replace('.yaml', '')
                            
                            print_info(f"Updating profile: {profile_name}")
                            
                            # Load existing config
                            with open(profile_path, 'r') as f:
                                existing_config = yaml.safe_load(f)
                            
                            # Get salt
                            salt_hex = existing_config.get('security', {}).get('salt', '')
                            if not salt_hex:
                                print_error("Could not find salt in config. Profile may not be encrypted.")
                            else:
                                # Prompt for master password
                                password = getpass.getpass("Enter Master Password: ")
                                
                                # Derive key
                                salt = bytes.fromhex(salt_hex)
                                kdf = PBKDF2HMAC(
                                    algorithm=hashes.SHA256(),
                                    length=32,
                                    salt=salt,
                                    iterations=100000,
                                )
                                key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
                                f = Fernet(key)
                                
                                # Encrypt new token
                                encrypted_token = f.encrypt(new_token.encode()).decode()
                                
                                # Update config
                                existing_config['github']['token'] = encrypted_token
                                
                                with open(profile_path, 'w') as f:
                                    yaml.dump(existing_config, f, default_flow_style=False)
                                
                                if os.name != 'nt':
                                    os.chmod(profile_path, 0o600)
                                
                                print_success("Token updated successfully!")
                                print_info("Restarting PyGitUp...")
                                os.execl(sys.executable, sys.executable, *sys.argv)
                                
                        except Exception as e:
                            print_error(f"Failed to update token: {e}")
                    else:
                        print_error("No token provided.")
                elif acc_choice == '4':
                    pass  # Back to menu
            # === SECURITY FEATURES ===
            elif mode == "security-scan":
                print_info("🔒 Running Enhanced Security Scan...")
                
                # Prompt for AI enhancement
                use_ai = False
                ai_key = config["github"].get("ai_api_key")
                
                if not ai_key:
                    print_info("\n🤖 AI Enhancement Available")
                    print("AI can provide:")
                    print("  • Smarter vulnerability analysis")
                    print("  • Reduced false positives")
                    print("  • Custom remediation code")
                    print("\n⚠️  Requires Gemini API key")
                    
                    choice = input("\nWould you like to configure AI now? (y/n): ").strip().lower()
                    if choice in ['y', 'yes']:
                        print_info("\nTo get a Gemini API key:")
                        print("  1. Visit: https://makersuite.google.com/app/apikey")
                        print("  2. Copy your API key")
                        print("  3. Run Option 14 (Configure) to add it")
                        print("\nContinuing with rule-based scan only...")
                else:
                    ai_choice = input("\n🤖 Use AI to enhance findings? (y/n): ").strip().lower()
                    use_ai = ai_choice in ['y', 'yes']
                
                findings = run_comprehensive_security_scan(".", use_ai=use_ai, config=config)
                
                if findings:
                    report = get_security_report(findings)
                    print("\n" + report)
                    # Log the scan
                    AUDIT_LOGGER.log_event(
                        AuditEventType.SECURITY_SCAN,
                        user=github_username,
                        details={
                            "findings_count": len(findings),
                            "critical_count": len([f for f in findings if f.severity == 'critical']),
                            "ai_enhanced": use_ai
                        },
                        severity="high" if any(f.severity == 'critical' for f in findings) else "info"
                    )
            elif mode == "token-health":
                print_info("🔐 Checking Token Health...")
                if github_token:
                    display_token_health_report(github_token, github_username)
                else:
                    print_error("No GitHub token found. Please configure your credentials.")
            elif mode == "supply-chain":
                print_info("📦 Running Supply Chain Security Scan...")
                results = run_supply_chain_scan(output_sbom=False)
            elif mode == "generate-sbom":
                print_info("📄 Generating Software Bill of Materials...")
                print("\nSelect format:")
                print("1: SPDX (JSON)")
                print("2: CycloneDX (JSON)")
                print("3: Both")
                sbom_choice = input("\n👉 Choice [1]: ") or "1"
                
                if sbom_choice in ['1', '3']:
                    generate_sbom_spdx("sbom.spdx.json")
                if sbom_choice in ['2', '3']:
                    generate_sbom_cyclonedx("sbom.cyclonedx.json")
            elif mode == "rotate-token":
                from .utils.token_manager import get_rotation_manager
                manager = get_rotation_manager()
                if github_token:
                    manager.rotate_token(github_token, github_username)
                else:
                    print_error("No current token found to rotate.")
            elif mode == "issue-triage":
                list_and_triage_issues(github_username, github_token, config, args)
            elif mode == "undo-commit":
                from .utils.remediation import undo_last_commit
                undo_last_commit()
            elif mode == "purge-file":
                from .utils.remediation import purge_file_from_history
                file_to_purge = args.file if args and args.file else input("Enter filename to purge from history: ")
                purge_file_from_history(file_to_purge)
            elif mode == "purge-string":
                from .utils.remediation import purge_string_from_history
                secret_str = args.string if args and args.string else input("Enter exact string to redact from history: ")
                purge_string_from_history(secret_str)
            elif mode == "edit-history":
                from .utils.remediation import interactive_commit_manager
                interactive_commit_manager()
            elif mode == "remediation-help":
                from .utils.remediation import show_remediation_help
                show_remediation_help()
            # === END SECURITY FEATURES ===
            else:
                print_error("Invalid mode selected.")
                if not is_interactive: sys.exit(1)

            print_success("Operation complete.")
            if not is_interactive:
                break
            input("\n⌨️  Press Enter to return to the menu...")
            os.system('cls' if os.name == 'nt' else 'clear')
            show_banner()

    except KeyboardInterrupt:
        print("\n")
        print_info("PyGitUp interrupted by user. Exiting...")
        sys.exit(0)
    except Exception as e:
        print_error(f"A critical error occurred: {e}")
        print_info("Please report this bug at: https://github.com/frederickabrah/PyGitUp/issues")
        sys.exit(1)

if __name__ == "__main__":
    main()