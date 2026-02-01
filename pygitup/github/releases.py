from .api import create_release, get_commit_history
from ..utils.ui import print_success, print_error, print_info, print_header

def get_release_input(config, args, github_username, github_token):
    """Get release input from user or arguments."""
    if args and args.repo:
        repo_name = args.repo
    else:
        repo_name = input("Enter repository name: ")
    
    if args and args.version:
        version = args.version
    else:
        version = input("Enter version tag (e.g., v1.0.0): ")
    
    if args and args.name:
        name = args.name
    else:
        default_name = f"Release {version}"
        name_input = input(f"Enter release name (default: {default_name}): ")
        name = name_input if name_input else default_name
    
    # Generate changelog if requested
    changelog = ""
    if args and args.generate_changelog:
        changelog = generate_changelog(github_username, repo_name, github_token, version)
    elif not args or not args.message:
        changelog_input = input("Enter release notes (optional): ")
        changelog = changelog_input
    
    return repo_name, version, name, changelog

def generate_changelog(username, repo_name, token, version):
    """Generate a changelog from commit history."""
    try:
        response = get_commit_history(username, repo_name, token)
        if response.status_code == 200:
            commits = response.json()
            changelog = f"## Changelog for {version}\n\n"
            for commit in commits[:20]:  # Last 20 commits
                message = commit['commit']['message'].split('\n')[0]
                author = commit['commit']['author']['name']
                date = commit['commit']['author']['date'][:10]
                changelog += f"- {message} ({author} on {date})\n"
            return changelog
        else:
            return "Changelog generation failed."
    except Exception as e:
        return f"Changelog generation failed: {e}"

def create_release_tag(github_username, github_token, config, args=None):
    """Create a new GitHub release with styled output."""
    if args and args.dry_run:
        print_info("*** Dry Run Mode: No changes will be made. ***")
        repo_name, version, name, changelog = get_release_input(config, args, github_username, github_token)
        print_info(f"Would create release {version} for {repo_name}.")
        return

    print_header("Create GitHub Release")
    repo_name, version, name, changelog = get_release_input(config, args, github_username, github_token)
    
    print_info(f"Creating release {version} for {repo_name}...")
    
    response = create_release(github_username, repo_name, github_token, version, name, changelog)
    
    if response.status_code == 201:
        release_data = response.json()
        print_success(f"Release created successfully!")
        print_info(f"View release at: {release_data['html_url']}")
    else:
        print_error(f"Error creating release: {response.status_code} - {response.text}")
