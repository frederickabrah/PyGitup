
import os
import json
from datetime import datetime

from ..github.api import update_file
from .security import check_is_sensitive
from .ui import print_success, print_error, print_info, print_header, print_warning

def queue_offline_commit(config, args=None):
    """Queue a commit for when online with styled output."""
    if args and args.dry_run:
        print_info("*** Dry Run Mode: No changes will be made. ***")
        print_info("Would queue a commit for the next online session.")
        return

    print_header("Offline Commit Queue")
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
    
    # Security check
    if check_is_sensitive(file_path):
        print_warning(f"'{file_path}' appears to be a sensitive file.")
        confirm = input("Are you sure you want to queue this file for upload? (y/n): ").lower()
        if confirm != 'y':
            print_info("Queuing cancelled.")
            return
    
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
            print_warning(f"Could not load queue file: {e}")
    
    # Add new entry
    queue.append(queue_entry)
    
    # Save queue
    try:
        with open(queue_file, 'w') as f:
            json.dump(queue, f, indent=2)
        print_success("Commit queued for next online session.")
        print_info(f"Queue file: {queue_file}")
    except Exception as e:
        print_error(f"Error saving queue: {e}")

def process_offline_queue(github_username, github_token, config, args=None):
    """Process queued commits when online with styled output."""
    if args and args.dry_run:
        print_info("*** Dry Run Mode: No changes will be made. ***")
        print_info("Would process the offline commit queue.")
        return

    queue_file = config["scheduling"]["offline_queue_file"]
    
    if not os.path.exists(queue_file):
        # Silently return if no queue file exists, unless manually triggered
        if args and args.mode == "process-queue":
            print_info("No offline queue found.")
        return
    
    try:
        with open(queue_file, 'r') as f:
            queue = json.load(f)
    except Exception as e:
        print_error(f"Error loading queue: {e}")
        return
    
    if not queue:
        if args and args.mode == "process-queue":
            print_info("Offline queue is empty.")
        return
    
    # Filter for queued entries
    queued_entries = [e for e in queue if e["status"] == "queued"]
    if not queued_entries:
        return

    print_header("Processing Offline Queue")
    print_info(f"Processing {len(queued_entries)} queued commits...")
    
    processed = 0
    for entry in queue:
        if entry["status"] == "queued":
            try:
                # Read file content
                if not os.path.exists(entry["file"]):
                    print_error(f"File not found: {entry['file']}. Skipping.")
                    entry["status"] = "failed"
                    entry["error"] = "File not found"
                    continue

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
                    print_success(f"Processed: {entry['message']}")
                    processed += 1
                else:
                    print_error(f"Failed: {entry['message']} - {response.status_code}")
                    entry["error"] = response.text
            except Exception as e:
                print_error(f"Error processing: {entry['message']} - {e}")
                entry["error"] = str(e)
    
    # Save updated queue
    try:
        with open(queue_file, 'w') as f:
            json.dump(queue, f, indent=2)
        print_success(f"Processed {processed} commits from queue.")
    except Exception as e:
        print_error(f"Error saving updated queue: {e}")
