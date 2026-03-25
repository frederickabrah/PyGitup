import questionary
import subprocess
import time

from .api import github_request, create_pull_request
from ..utils.ui import print_success, print_error, print_info, print_header

def manage_pull_requests(args, github_username, github_token):
    """Handle pull request management operations with rate-limiting support."""
    action = args.action if hasattr(args, 'action') and args.action else None
    repo_name = args.repo if hasattr(args, 'repo') and args.repo else None
    pr_number = args.pr_number if hasattr(args, 'pr_number') and args.pr_number else None
    comment = args.comment if hasattr(args, 'comment') and args.comment else None

    if not action:
        print_header("Pull Request Management")
        action = questionary.select(
            "What pull request operation would you like to perform?",
            choices=["merge", "close", "comment"],
        ).ask()

        if not repo_name:
            repo_name = questionary.text("Enter the repository name").ask()

        pr_number = questionary.text("Enter the pull request number").ask()
        if pr_number:
            pr_number = int(pr_number)

        if action == "comment":
            comment = questionary.text("Enter your comment").ask()

    if not repo_name or not pr_number:
        print_error("Repository name and pull request number are required.")
        return

    base_url = f"https://api.github.com/repos/{github_username}/{repo_name}"

    try:
        if action == "merge":
            url = f"{base_url}/pulls/{pr_number}/merge"
            response = github_request("PUT", url, github_token)
            response.raise_for_status()
            print_success("Pull request merged successfully!")

        elif action == "close":
            url = f"{base_url}/pulls/{pr_number}"
            data = {"state": "closed"}
            response = github_request("PATCH", url, github_token, json=data)
            response.raise_for_status()
            print_success("Pull request closed successfully!")

        elif action == "comment":
            url = f"{base_url}/issues/{pr_number}/comments"
            data = {"body": comment}
            response = github_request("POST", url, github_token, json=data)
            response.raise_for_status()
            print_success("Comment added successfully!")

    except Exception as e:
        print_error(f"Pull request operation failed: {e}")

def request_code_review(github_username, github_token, config, args=None):
    """Request code reviews for specific files."""
    if args and args.dry_run:
        print_info("*** Dry Run Mode: No changes will be made. ***")
        print_info("Would request a code review.")
        return

    if args and args.repo:
        repo_name = args.repo
    else:
        repo_name = questionary.text("Enter the repository name").ask()

    # TECHNICAL VALIDATION: Ensure current directory matches the target repo
    try:
        remote_res = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True)
        if repo_name.lower() not in remote_res.stdout.lower():
            print_error(f"Context Mismatch: Current directory is not '{repo_name}'.")
            print_info("Please 'cd' into the correct repository before requesting a review.")
            return
    except Exception:
        print_error("Not a git repository.")
        return

    # Create a new branch for the review
    branch_name = f"review-{int(time.time())}"

    try:
        # Create and switch to the new branch
        subprocess.run(["git", "checkout", "-b", branch_name], check=True)
        print_info(f"Created and switched to new branch: {branch_name}")

        if args and args.files:
            files = args.files.split(",")
        else:
            files_input = input("Enter files to review (comma-separated): ")
            files = files_input.split(",") if files_input else []

        if files:
            # Add the specified files to the branch
            subprocess.run(["git", "add"] + files, check=True)
            print_info(f"Added files to the branch: {files}")

            # Check if there are changes to commit
            status_check = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.strip()
            if status_check:
                # Commit the changes
                commit_message = f"Code review request for: {', '.join(files)}"
                subprocess.run(["git", "commit", "-m", commit_message], check=True)
                print_info("Committed changes to the branch.")
            else:
                print_warning("No changes detected in the specified files relative to the current branch.")

        # TECHNICAL UPGRADE: Credentialed Push
        # We inject the token into the push URL to ensure success
        push_url = f"https://{github_token}@github.com/{github_username}/{repo_name}.git"
        print_info(f"Synchronizing review branch with GitHub...")
        subprocess.run(["git", "push", "-u", push_url, branch_name], check=True, capture_output=True)
        print_success("Pushed the new branch to GitHub.")

        reviewers = []
        if args and args.reviewers:
            reviewers = args.reviewers.split(",")
        else:
            reviewers_input = input("Enter reviewers (comma-separated GitHub usernames): ")
            reviewers = reviewers_input.split(",") if reviewers_input else []

        # Create a pull request
        pr_title = f"Code Review Request: {', '.join(files) if files else 'General Review'}"
        pr_body = f"This PR is requesting code review for the following files:\n"
        for file in files:
            pr_body += f"- {file}\n"

        if reviewers:
            pr_body += f"\nRequested reviewers: {', '.join(reviewers)}"

        response = create_pull_request(github_username, repo_name, github_token, pr_title, branch_name, "main", pr_body)

        if response.status_code == 201:
            pr_data = response.json()
            print_success("\nPull request created successfully!")
            print_info(f"View it here: {pr_data['html_url']}")
        else:
            print_error(f"\nError creating pull request: {response.status_code} - {response.text}")

    except subprocess.CalledProcessError as e:
        print_error(f"An error occurred while running a git command: {e}")
    except Exception as e:
        print_error(f"An error occurred: {e}")
    finally:
        # Switch back to the main branch
        subprocess.run(["git", "checkout", "main"], check=True)
        print_info("Switched back to the main branch.")