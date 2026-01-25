
import subprocess

def smart_push(github_username, github_token, config, args=None):
    """Smart push that squashes meaningless commits."""
    if args and args.dry_run:
        print("*** Dry Run Mode: No changes will be made. ***")
        print("Would perform a smart push with commit squashing.")
        return

    if args and args.repo:
        repo_name = args.repo
    else:
        repo_name = input("Enter repository name: ")

    # Get squash patterns
    if args and args.squash_pattern:
        patterns = args.squash_pattern.split(",")
    else:
        patterns_input = input("Enter commit message patterns to squash (comma-separated): ")
        patterns = patterns_input.split(",") if patterns_input else ["typo", "fix", "update"]

    print(f"Smart pushing to {repo_name} with squash patterns: {patterns}")

    try:
        # Get the last 10 commits
        log_result = subprocess.run(["git", "log", "--oneline", "-n", "10"], capture_output=True, text=True, check=True)
        commits = log_result.stdout.strip().split("\n")

        # Identify commits to squash
        commits_to_squash = []
        for commit in commits:
            commit_hash, commit_message = commit.split(" ", 1)
            for pattern in patterns:
                if pattern.lower() in commit_message.lower():
                    commits_to_squash.append(commit_hash)
                    break

        if not commits_to_squash:
            print("No commits to squash. Pushing normally.")
            subprocess.run(["git", "push"], check=True)
            return

        print(f"Found {len(commits_to_squash)} commits to squash: {commits_to_squash}")

        # The parent of the oldest commit to be squashed
        squash_base = f"{commits_to_squash[-1]}~"

        # Get the messages of the commits being squashed for the new commit message
        squashed_messages = []
        for commit_hash in reversed(commits_to_squash):
            msg = subprocess.run(["git", "log", "--format=%B", "-n", "1", commit_hash], capture_output=True, text=True, check=True).stdout.strip()
            squashed_messages.append(msg)

        new_commit_message = f"Squashed {len(squashed_messages)} commits\n\n" + "\n".join(f"- {msg}" for msg in squashed_messages)

        print(f"\nResetting to {squash_base} and preparing to squash.")
        subprocess.run(["git", "reset", "--soft", squash_base], check=True)

        print("Creating new squashed commit.")
        subprocess.run(["git", "commit", "-m", new_commit_message], check=True)

        print("Force-pushing the new history. This will overwrite the remote history.")
        subprocess.run(["git", "push", "--force-with-lease"], check=True)

        print("\nSmart push complete.")

    except subprocess.CalledProcessError as e:
        print(f"An error occurred while running a git command: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
