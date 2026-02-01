import os
import subprocess
import tempfile
from .api import create_release, get_commit_history
from ..utils.ui import print_success, print_error, print_info, print_header, print_warning
from ..utils.ai import generate_ai_release_notes

def open_editor(initial_content=""):
    """Opens the system default editor to edit release notes."""
    editor = os.environ.get('EDITOR', 'nano')
    with tempfile.NamedTemporaryFile(suffix=".md", mode='w+', delete=False) as tf:
        tf.write(initial_content)
        temp_path = tf.name
    
    try:
        subprocess.run([editor, temp_path], check=True)
        with open(temp_path, 'r') as f:
            content = f.read()
        return content.strip()
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

def get_release_input(config, args, github_username, github_token):
    """Get release input from user or arguments with AI support."""
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
    
    # Release Notes Logic
    changelog = ""
    print("\n[bold]Release Notes Options:[/bold]")
    print("1: [cyan]AI-Generated Summary[/cyan]")
    print("2: [green]Auto-Changelog (Commit list)[/green]")
    print("3: [yellow]Manual Editor (Nano/Vim)[/yellow]")
    print("4: [white]Skip / Basic prompt[/white]")
    
    note_choice = input("\n👉 Choice: ")
    
    if note_choice == '1':
        print_info("🤖 AI is analyzing your project history...")
        resp = get_commit_history(github_username, repo_name, github_token)
        if resp.status_code == 200:
            ai_key = config["github"].get("ai_api_key")
            changelog = generate_ai_release_notes(ai_key, repo_name, resp.json())
            # Let user tweak the AI's output
            if changelog:
                confirm = input("AI notes generated. Edit them before publishing? (y/n): ").lower()
                if confirm == 'y':
                    changelog = open_editor(changelog)
        else:
            print_error("Failed to fetch history for AI.")
            
    elif note_choice == '2':
        changelog = generate_changelog(github_username, repo_name, github_token, version)
    elif note_choice == '3':
        changelog = open_editor("# Release Notes for " + version + "\n\n")
    else:
        if args and args.message:
            changelog = args.message
        else:
            changelog = input("Enter release notes: ")
    
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
    
    # 1. Automated Local Tagging
    try:
        # Check if we are in the target repo
        if os.path.isdir(".git"):
            print_info("Local Git repository detected. Synchronizing tags...")
            # Create tag
            subprocess.run(["git", "tag", "-a", version, "-m", name], capture_output=True)
            # Push tag
            subprocess.run(["git", "push", "origin", version], capture_output=True)
            print_success(f"Local tag '{version}' pushed to origin.")
    except Exception as e:
        print_warning(f"Local tagging skipped/failed: {e}")

    # 2. GitHub API Release
    response = create_release(github_username, repo_name, github_token, version, name, changelog)
    
    if response.status_code == 201:
        release_data = response.json()
        print_success(f"Release created successfully!")
        print_info(f"View release at: {release_data['html_url']}")
    else:
        print_error(f"Error creating release: {response.status_code} - {response.text}")
