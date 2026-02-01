import requests
import base64
import time

def get_github_headers(token):
    """Create standard GitHub API headers."""
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

def github_request(method, url, token, **kwargs):
    """Centralized GitHub API request handler with rate-limiting support."""
    headers = get_github_headers(token)
    if 'headers' in kwargs:
        headers.update(kwargs.pop('headers'))
    
    while True:
        try:
            response = requests.request(method, url, headers=headers, **kwargs)
            
            # Handle rate limiting
            if response.status_code == 403 and 'X-RateLimit-Remaining' in response.headers:
                remaining = int(response.headers.get('X-RateLimit-Remaining', 1))
                if remaining == 0:
                    reset_time = int(response.headers.get('X-RateLimit-Reset', time.time() + 60))
                    sleep_duration = max(reset_time - time.time() + 1, 1)
                    print(f"\n[!] Rate limit reached. Sleeping for {sleep_duration:.0f}s until reset...")
                    time.sleep(sleep_duration)
                    continue
            
            return response
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            raise

def graphql_request(query, variables, token):
    """Execute a GitHub GraphQL (v4) API request with rate-limiting support."""
    url = "https://api.github.com/graphql"
    payload = {"query": query, "variables": variables}
    # GraphQL always uses POST
    return github_request("POST", url, token, json=payload)

def get_repo_info(username, repo_name, token):
    """Get repository information."""
    url = f"https://api.github.com/repos/{username}/{repo_name}"
    return github_request("GET", url, token)

def create_repo(username, repo_name, token, description="", private=False):
    """Create a new GitHub repository."""
    url = "https://api.github.com/user/repos"
    data = {
        "name": repo_name,
        "description": description,
        "private": private
    }
    return github_request("POST", url, token, json=data)

def get_file_info(username, repo_name, file_path, token):
    """Get information about a file in a repository."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{file_path}"
    return github_request("GET", url, token)

def update_file(username, repo_name, file_path, content, token, message, sha=None):
    """Update or create a file in a repository."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{file_path}"
    encoded_content = base64.b64encode(content).decode('utf-8')
    data = {
        "message": message,
        "content": encoded_content
    }
    if sha:
        data["sha"] = sha
    return github_request("PUT", url, token, json=data)

def get_commit_history(username, repo_name, token, path=None):
    """Get commit history for a repository or specific file."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/commits"
    params = {}
    if path:
        params["path"] = path
    return github_request("GET", url, token, params=params)

def create_release(username, repo_name, token, tag_name, name, body=""):
    """Create a new GitHub release."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/releases"
    data = {
        "tag_name": tag_name,
        "name": name,
        "body": body,
        "draft": False,
        "prerelease": False
    }
    return github_request("POST", url, token, json=data)

def create_issue(username, repo_name, token, title, body="", assignees=None):
    """Create a new GitHub issue."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/issues"
    data = {
        "title": title,
        "body": body
    }
    if assignees:
        data["assignees"] = assignees
    return github_request("POST", url, token, json=data)

def get_pull_requests(username, repo_name, token, state="open"):
    """Get pull requests for a repository."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/pulls"
    params = {"state": state}
    return github_request("GET", url, token, params=params)

def create_pull_request(username, repo_name, token, title, head, base, body=""):
    """Create a new pull request."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/pulls"
    data = {
        "title": title,
        "head": head,
        "base": base,
        "body": body
    }
    return github_request("POST", url, token, json=data)

def get_contributors(username, repo_name, token):
    """Get contributors for a repository."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/contributors"
    return github_request("GET", url, token)

def get_issues(username, repo_name, token, state="all"):
    """Get issues for a repository."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/issues"
    params = {"state": state}
    return github_request("GET", url, token, params=params)

def get_repo_languages(username, repo_name, token):
    """Get detailed language breakdown for a repository."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/languages"
    return github_request("GET", url, token)

def get_community_profile(username, repo_name, token):
    """Get community health metrics (presence of README, LICENSE, etc)."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/community/profile"
    # This endpoint uses a different preview header for some data
    return github_request("GET", url, token)

def get_latest_release(username, repo_name, token):
    """Get the latest release for a repository."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/releases/latest"
    return github_request("GET", url, token)

def get_repo_contents(username, repo_name, token, path=""):
    """Get repository contents recursively."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{path}"
    return github_request("GET", url, token)

def search_user_by_email(email, token):
    """Find a GitHub user by their email address."""
    url = f"https://api.github.com/search/users"
    return github_request("GET", url, token, params={"q": f"{email} in:email"})

def get_user_repos(token):
    """List all repositories for the authenticated user."""
    url = "https://api.github.com/user/repos"
    return github_request("GET", url, token, params={"per_page": 100})

def update_repo_visibility(username, repo_name, token, private):
    """Update the visibility of a repository."""
    url = f"https://api.github.com/repos/{username}/{repo_name}"
    data = {"private": private}
    return github_request("PATCH", url, token, json=data)

def delete_repo_api(username, repo_name, token):
    """Delete a GitHub repository."""
    url = f"https://api.github.com/repos/{username}/{repo_name}"
    return github_request("DELETE", url, token)

# --- ADVANCED ENHANCEMENT ENDPOINTS ---

def get_workflow_run_logs(username, repo_name, token, run_id):
    """Download logs for a specific workflow run."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/actions/runs/{run_id}/logs"
    return github_request("GET", url, token)

def toggle_workflow_api(username, repo_name, token, workflow_id, enable=True):
    """Enable or disable a specific workflow."""
    status = "enable" if enable else "disable"
    url = f"https://api.github.com/repos/{username}/{repo_name}/actions/workflows/{workflow_id}/{status}"
    return github_request("PUT", url, token)

def get_dependabot_alerts(username, repo_name, token):
    """Fetch Dependabot alerts for a repository."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/dependabot/alerts"
    return github_request("GET", url, token)

def get_secret_scanning_alerts(username, repo_name, token):
    """Fetch Secret Scanning alerts for a repository."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/secret-scanning/alerts"
    return github_request("GET", url, token)