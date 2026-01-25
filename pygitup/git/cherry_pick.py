
import subprocess
import inquirer

def cherry_pick_commit(args):
    """Cherry-pick a commit."""
    commit_hash = args.commit_hash
    if not commit_hash:
        questions = [
            inquirer.Text("commit_hash", message="Enter the hash of the commit to cherry-pick")
        ]
        answers = inquirer.prompt(questions)
        commit_hash = answers["commit_hash"]

    if not commit_hash:
        print("No commit hash provided. Exiting.")
        return

    try:
        print(f"Cherry-picking commit: {commit_hash}")
        subprocess.run(["git", "cherry-pick", commit_hash], check=True)
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while running a git command: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
