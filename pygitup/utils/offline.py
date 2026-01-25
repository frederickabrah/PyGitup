import os
import json
from datetime import datetime

from ..github.api import update_file

def queue_offline_commit(config, args=None):
    """Queue a commit for when online."""
    if args and args.dry_run:
        print("*** Dry Run Mode: No changes will be made. ***")
        print("Would queue a commit for the next online session.")
        return

    if args and args.repo:
        repo_name = args.repo
    else:
        repo_name = input("Enter repository name: ")
    
    if args and args.message:
        commit_message = args.message
    else:
        commit_message = input("Enter commit message: ")
    
    if args and args.file:
        file_path = args.file
    else:
        file_path = input("Enter file to commit: ")
    
    # Create queue entry
    queue_entry = {
        "timestamp": datetime.now().isoformat(),
        "repo": repo_name,
        "message": commit_message,
        "file": file_path,
        "status": "queued"
    }
    
    # Load existing queue
    queue_file = config["scheduling"]["offline_queue_file"]
    queue = []
    if os.path.exists(queue_file):
        try:
            with open(queue_file, 'r') as f:
                queue = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load queue file: {e}")
    
    # Add new entry
    queue.append(queue_entry)
    
    # Save queue
    try:
        with open(queue_file, 'w') as f:
            json.dump(queue, f, indent=2)
        print(f"Commit queued for next online session.")
        print(f"Queue file: {queue_file}")
    except Exception as e:
        print(f"Error saving queue: {e}")

def process_offline_queue(github_username, github_token, config, args=None):
    """Process queued commits when online."""
    if args and args.dry_run:
        print("*** Dry Run Mode: No changes will be made. ***")
        print("Would process the offline commit queue.")
        return

    queue_file = config["scheduling"]["offline_queue_file"]
    
    if not os.path.exists(queue_file):
        print("No offline queue found.")
        return
    
    try:
        with open(queue_file, 'r') as f:
            queue = json.load(f)
    except Exception as e:
        print(f"Error loading queue: {e}")
        return
    
    if not queue:
        print("Offline queue is empty.")
        return
    
    print(f"Processing {len(queue)} queued commits...")
    
    processed = 0
    for entry in queue:
        if entry["status"] == "queued":
            try:
                # Read file content
                with open(entry["file"], "rb") as f:
                    file_content = f.read()
                
                # Upload file
                response = update_file(
                    github_username, entry["repo"], entry["file"],
                    file_content, github_token, entry["message"]
                )
                
                if response.status_code in [200, 201]:
                    entry["status"] = "completed"
                    entry["processed_at"] = datetime.now().isoformat()
                    print(f"✓ Processed: {entry['message']}")
                    processed += 1
                else:
                    print(f"✗ Failed: {entry['message']} - {response.status_code}")
            except Exception as e:
                print(f"✗ Error processing: {entry['message']} - {e}")
    
    # Save updated queue
    try:
        with open(queue_file, 'w') as f:
            json.dump(queue, f, indent=2)
        print(f"Processed {processed} commits from queue.")
    except Exception as e:
        print(f"Error saving updated queue: {e}")