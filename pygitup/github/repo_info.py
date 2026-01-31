
import inquirer
import json
from urllib.parse import urlparse
from .api import get_repo_info
from ..utils.ui import display_repo_info, print_header, print_error

def parse_github_url(url):
    """Extract owner and repo name from a GitHub URL."""
    try:
        parsed = urlparse(url)
        # Handle cases like https://github.com/owner/repo or github.com/owner/repo
        path = parsed.path
             
        parts = path.strip("/").split("/")
        if len(parts) >= 2:
            return parts[0], parts[1]
    except Exception:
        pass
    return None, None

def get_detailed_repo_info(args, github_token):
    """Fetch and display verbose information about a repository."""
    url = args.url if hasattr(args, 'url') and args.url else None

    if not url:
        questions = [
            inquirer.Text("url", message="Enter the GitHub repository URL")
        ]
        answers = inquirer.prompt(questions)
        url = answers["url"]

    owner, repo_name = parse_github_url(url)
    
    if not owner or not repo_name:
        print_error("Error: Could not parse repository owner and name from the URL.")
        print("Please ensure the URL is in the format: https://github.com/owner/repo")
        return

    print(f"\nFetching full details for '{owner}/{repo_name}'...")
    
    try:
        # We reuse the existing API function but might need to ensure it doesn't just get my repos
        # The existing get_repo_info takes (username, repo_name, token). 
        # API logic: f"https://api.github.com/repos/{username}/{repo_name}"
        # This works for any public repo or private repo the token has access to.
        
        response = get_repo_info(owner, repo_name, github_token)
        
        if response.status_code == 200:
            data = response.json()
            display_repo_info(data)
        else:
            print_error(f"Error: Failed to fetch data (Status Code: {response.status_code})")
            print(f"Response: {response.text}")
            if response.status_code == 404:
                print("Hint: The repository might not exist or is private (and your token lacks access).")

    except Exception as e:
        print_error(f"An unexpected error occurred: {e}")
