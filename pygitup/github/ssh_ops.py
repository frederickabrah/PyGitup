
import subprocess
import os
from .api import upload_ssh_key
from ..utils.security import generate_ssh_key
from ..utils.ui import print_success, print_error, print_info, print_header, print_warning

def setup_ssh_infrastructure(config, github_token):
    """
    Complete automation of SSH Key setup:
    1. Generate Key -> 2. Start Agent -> 3. Upload to GitHub -> 4. Test Connection -> 5. Update Remote
    """
    print_header("SSH Key Infrastructure Manager")
    
    email = config["github"].get("email") or input("Enter email for SSH Key label: ")
    
    # 1. Generate or Get Key
    public_key, key_path = generate_ssh_key(email)
    if not public_key:
        return

    # 2. Add to SSH Agent
    try:
        print_info("Adding key to SSH Agent...")
        subprocess.run(["eval $(ssh-agent -s) && ssh-add " + key_path], shell=True, check=True, capture_output=True)
    except subprocess.CalledProcessError:
        print_warning("Could not add to ssh-agent automatically. You may need to run 'ssh-add' manually.")

    # 3. Upload to GitHub
    title = f"PyGitUp Key - {os.uname().nodename}"
    print_info(f"Uploading key to GitHub as '{title}'...")
    
    response = upload_ssh_key(github_token, title, public_key)
    
    if response.status_code == 201:
        print_success("SSH Public Key uploaded to GitHub successfully!")
    elif response.status_code == 422:
        print_info("Key already exists on GitHub. Proceeding...")
    else:
        print_error(f"Failed to upload key: {response.status_code} - {response.text}")
        return

    # 4. Test Connection
    print_info("Testing connection to GitHub...")
    try:
        # ssh -T returns exit code 1 on success (weird GitHub thing), so we catch it
        result = subprocess.run(["ssh", "-T", "-o", "StrictHostKeyChecking=no", "git@github.com"], 
                              capture_output=True, text=True)
        
        if "successfully authenticated" in result.stderr:
            print_success("Connection verified! You are authenticated via SSH.")
        else:
            print_warning("Connection test outcome uncertain. Please check manual ssh output.")
    except Exception as e:
        print_warning(f"Could not run SSH test: {e}")

    # 5. Update Local Repo Remote
    if os.path.isdir(".git"):
        update = input("\nUpdate local repository to use SSH remote? (y/n): ").lower()
        if update == 'y':
            try:
                # Get current remote
                current_remote = subprocess.run(["git", "remote", "get-url", "origin"], 
                                              capture_output=True, text=True).stdout.strip()
                
                # Convert HTTPS to SSH
                if "https://github.com/" in current_remote:
                    ssh_remote = current_remote.replace("https://github.com/", "git@github.com:")
                    subprocess.run(["git", "remote", "set-url", "origin", ssh_remote], check=True)
                    print_success(f"Remote updated to: {ssh_remote}")
                else:
                    print_info("Remote is not standard HTTPS or already SSH.")
            except Exception as e:
                print_error(f"Failed to update remote: {e}")
