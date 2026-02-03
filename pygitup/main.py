import sys
import os

from .core.args import create_parser
from .core.config import load_config, get_github_username, get_github_token, configuration_wizard, list_profiles, set_active_profile, get_active_profile_path
from .project.project_ops import upload_project_directory, upload_single_file, upload_batch_files, update_multiple_repos, manage_bulk_repositories, migrate_repository
from .project.templates import create_project_from_template
from .github.releases import create_release_tag
from .project.issues import scan_todos
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
from .github.repo import manage_repo_visibility, delete_repository
from .github.repo_info import get_detailed_repo_info, get_fork_intelligence, parse_github_url
from .github.ssh_ops import setup_ssh_infrastructure
from .utils.banner import show_banner
from .utils.ui import display_menu, print_error, print_success, print_info, console
from .utils.update import check_for_updates

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
                if os.path.isdir(target_path):
                    try:
                        os.chdir(target_path)
                        print_success(f"Switched context to: {os.getcwd()}")
                    except Exception as e:
                        print_error(f"Could not switch directory: {e}")
                else:
                    print_error(f"Directory not found: {target_path}")

        # Parse command line arguments
        parser = create_parser()
        args = parser.parse_args()
        
        # Load configuration
        config = load_config(args.config)
        
        # Auto-Setup Wizard if credentials missing
        if not config["github"].get("username") or not config["github"].get("token"):
            print_info("No existing credentials found. Starting stealth setup...")
            configuration_wizard()
            # Reload after setup
            config = load_config(args.config)

        # Get credentials
        github_username = get_github_username(config)
        github_token = get_github_token(config)
        
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
                manage_actions(args, github_username, github_token)
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
                print("3: Back")
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
        print_info("Please report this bug at: https://github.com/frederickabrah/PyGitup/issues")
        sys.exit(1)