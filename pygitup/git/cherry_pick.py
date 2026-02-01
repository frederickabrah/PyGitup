import subprocess
import inquirer
from ..utils.ui import print_success, print_error, print_info, print_header

def cherry_pick_commit(args):
    """Cherry-pick a commit with styled output."""
    commit_hash = args.commit_hash
    if not commit_hash:
        print_header("Cherry-Pick Commit")
        questions = [
            inquirer.Text("commit_hash", message="Enter the hash of the commit to cherry-pick")
        ]
        answers = inquirer.prompt(questions)
        commit_hash = answers["commit_hash"]

    if not commit_hash:
        print_error("No commit hash provided. Exiting.")
        return

    try:
        print_info(f"Cherry-picking commit: {commit_hash}")
        subprocess.run(["git", "cherry-pick", commit_hash], check=True)
        print_success(f"Successfully cherry-picked {commit_hash}")
    except subprocess.CalledProcessError as e:
        print_error(f"Git command failed: {e}")
    except Exception as e:
        print_error(f"An unexpected error occurred: {e}")