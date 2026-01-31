import sys

from .core.args import create_parser
from .core.config import load_config, get_github_username, get_github_token, configuration_wizard
from .project.project_ops import upload_project_directory, upload_single_file, upload_batch_files, update_multiple_repos
from .project.templates import create_project_from_template
from .github.releases import create_release_tag
from .project.issues import scan_todos
from .utils.offline import queue_offline_commit, process_offline_queue
from .github.pull_requests import manage_pull_requests, request_code_review
from .git.push import smart_push
from .project.docs import generate_documentation
from .utils.analytics import generate_analytics
from .git.branch import manage_branches
from .git.stash import manage_stashes
from .git.tag import manage_tags
from .git.cherry_pick import cherry_pick_commit
from .github.gists import manage_gists
from .github.webhooks import manage_webhooks
from .github.actions import manage_actions
from .utils.security import run_audit
from .github.repo import manage_repo_visibility, delete_repository
from .github.repo_info import get_detailed_repo_info
from .utils.banner import show_banner
from .utils.ui import display_menu, print_error, print_success

def main():
    """Main function to orchestrate the process."""
    show_banner()

    # Parse command line arguments
    parser = create_parser()
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Get credentials
    github_username = get_github_username(config)
    github_token = get_github_token(config)
    
    # Process offline queue if not in queue processing mode
    if args.mode != "process-queue":
        process_offline_queue(github_username, github_token, config)
    
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
            '23': ("Run security audit", "audit"),
            '24': ("Change repository visibility", "visibility"),
            '25': ("Get repository info from URL", "repo-info"),
            '26': ("Delete GitHub repository", "delete-repo")
        }

        display_menu(menu_options)
        choice = input("\n👉 Enter your choice (1-26): ")
        
        selected_option = menu_options.get(choice)
        mode = selected_option[1] if selected_option else ""

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
        run_audit()
    elif mode == "visibility":
        manage_repo_visibility(args, github_username, github_token)
    elif mode == "repo-info":
        get_detailed_repo_info(args, github_token)
    elif mode == "delete-repo":
        delete_repository(args, github_username, github_token)
    else:
        print_error("Invalid mode selected. Exiting.")
        sys.exit(1)

    print_success("Operation complete.")