
import requests
import base64

def get_github_headers(token):
    """Create standard GitHub API headers."""
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

def get_repo_info(username, repo_name, token):
    """Get repository information."""
    url = f"https://api.github.com/repos/{username}/{repo_name}"
    headers = get_github_headers(token)
    response = requests.get(url, headers=headers)
    return response

def create_repo(username, repo_name, token, description="", private=False):
    """Create a new GitHub repository."""
    url = "https://api.github.com/user/repos"
    headers = get_github_headers(token)
    data = {
        "name": repo_name,
        "description": description,
        "private": private
    }
    response = requests.post(url, headers=headers, json=data)
    return response

def get_file_info(username, repo_name, file_path, token):
    """Get information about a file in a repository."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{file_path}"
    headers = get_github_headers(token)
    response = requests.get(url, headers=headers)
    return response

def update_file(username, repo_name, file_path, content, token, message, sha=None):
    """Update or create a file in a repository."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{file_path}"
    headers = get_github_headers(token)
    encoded_content = base64.b64encode(content).decode('utf-8')
    data = {
        "message": message,
        "content": encoded_content
    }
    if sha:
        data["sha"] = sha
    response = requests.put(url, headers=headers, json=data)
    return response

def get_commit_history(username, repo_name, token, path=None):
    """Get commit history for a repository or specific file."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/commits"
    headers = get_github_headers(token)
    params = {}
    if path:
        params["path"] = path
    response = requests.get(url, headers=headers, params=params)
    return response

def create_release(username, repo_name, token, tag_name, name, body=""):
    """Create a new GitHub release."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/releases"
    headers = get_github_headers(token)
    data = {
        "tag_name": tag_name,
        "name": name,
        "body": body,
        "draft": False,
        "prerelease": False
    }
    response = requests.post(url, headers=headers, json=data)
    return response

def create_issue(username, repo_name, token, title, body="", assignees=None):
    """Create a new GitHub issue."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/issues"
    headers = get_github_headers(token)
    data = {
        "title": title,
        "body": body
    }
    if assignees:
        data["assignees"] = assignees
    response = requests.post(url, headers=headers, json=data)
    return response

def get_pull_requests(username, repo_name, token, state="open"):
    """Get pull requests for a repository."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/pulls"
    headers = get_github_headers(token)
    params = {"state": state}
    response = requests.get(url, headers=headers, params=params)
    return response

def create_pull_request(username, repo_name, token, title, head, base, body=""):
    """Create a new pull request."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/pulls"
    headers = get_github_headers(token)
    data = {
        "title": title,
        "head": head,
        "base": base,
        "body": body
    }
    response = requests.post(url, headers=headers, json=data)
    return response

def get_contributors(username, repo_name, token):
    """Get contributors for a repository."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/contributors"
    headers = get_github_headers(token)
    response = requests.get(url, headers=headers)
    return response

def get_issues(username, repo_name, token, state="all"):
    """Get issues for a repository."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/issues"
    headers = get_github_headers(token)
    params = {"state": state}
    response = requests.get(url, headers=headers, params=params)
    return response

def get_repo_contents(username, repo_name, token, path=""):
    """Get repository contents recursively."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{path}"
    headers = get_github_headers(token)
    response = requests.get(url, headers=headers)
    return response

def update_repo_visibility(username, repo_name, token, private):
    """Update the visibility of a repository."""
    url = f"https://api.github.com/repos/{username}/{repo_name}"
    headers = get_github_headers(token)
    data = {"private": private}
    response = requests.patch(url, headers=headers, json=data)
    return response
