
import requests
import inquirer
import subprocess
import time

from .api import get_github_headers, create_pull_request

def manage_pull_requests(args, github_username, github_token):
    """Handle pull request management operations."""
    action = args.action if hasattr(args, 'action') and args.action else None
    repo_name = args.repo if hasattr(args, 'repo') and args.repo else None
    pr_number = args.pr_number if hasattr(args, 'pr_number') and args.pr_number else None
    comment = args.comment if hasattr(args, 'comment') and args.comment else None

    if not action:
        questions = [
            inquirer.List(
                "action",
                message="What pull request operation would you like to perform?",
                choices=["merge", "close", "comment"],
            )
        ]
        answers = inquirer.prompt(questions)
        action = answers["action"]

        if not repo_name:
            repo_questions = [inquirer.Text("repo", message="Enter the repository name")]
            repo_answers = inquirer.prompt(repo_questions)
            repo_name = repo_answers["repo"]

        pr_number_questions = [inquirer.Text("pr_number", message="Enter the pull request number")]
        pr_number_answers = inquirer.prompt(pr_number_questions)
        pr_number = int(pr_number_answers["pr_number"])

        if action == "comment":
            comment_questions = [inquirer.Text("comment", message="Enter your comment")]
            comment_answers = inquirer.prompt(comment_questions)
            comment = comment_answers["comment"]

    if not repo_name or not pr_number:
        print("Repository name and pull request number are required.")
        return

    headers = get_github_headers(github_token)
    base_url = f"https://api.github.com/repos/{github_username}/{repo_name}"

    try:
        if action == "merge":
            url = f"{base_url}/pulls/{pr_number}/merge"
            response = requests.put(url, headers=headers)
            response.raise_for_status()
            print("Pull request merged successfully!")

        elif action == "close":
            url = f"{base_url}/pulls/{pr_number}"
            data = {"state": "closed"}
            response = requests.patch(url, headers=headers, json=data)
            response.raise_for_status()
            print("Pull request closed successfully!")

        elif action == "comment":
            url = f"{base_url}/issues/{pr_number}/comments"
            data = {"body": comment}
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            print("Comment added successfully!")

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while communicating with the GitHub API: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

def request_code_review(github_username, github_token, config, args=None):
    """Request code reviews for specific files."""
    if args and args.dry_run:
        print("*** Dry Run Mode: No changes will be made. ***")
        print("Would request a code review.")
        return

    if args and args.repo:
        repo_name = args.repo
    else:
        repo_name = input("Enter repository name: ")

    # Create a new branch for the review
    branch_name = f"review-{int(time.time())}"

    try:
        # Create and switch to the new branch
        subprocess.run(["git", "checkout", "-b", branch_name], check=True)
        print(f"Created and switched to new branch: {branch_name}")

        if args and args.files:
            files = args.files.split(",")
        else:
            files_input = input("Enter files to review (comma-separated): ")
            files = files_input.split(",") if files_input else []

        if files:
            # Add the specified files to the branch
            subprocess.run(["git", "add"] + files, check=True)
            print(f"Added files to the branch: {files}")

            # Commit the changes
            commit_message = f"Code review request for: {', '.join(files)}"
            subprocess.run(["git", "commit", "-m", commit_message], check=True)
            print("Committed changes to the branch.")

        # Push the new branch to GitHub
        subprocess.run(["git", "push", "-u", "origin", branch_name], check=True)
        print("Pushed the new branch to GitHub.")

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
            print("\nPull request created successfully!")
            print(f"View it here: {pr_data['html_url']}")
        else:
            print(f"\nError creating pull request: {response.status_code} - {response.text}")

    except subprocess.CalledProcessError as e:
        print(f"An error occurred while running a git command: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Switch back to the main branch
        subprocess.run(["git", "checkout", "main"], check=True)
        print("Switched back to the main branch.")
