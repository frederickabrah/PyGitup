import requests
import base64
import time
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Any, List, Union
from dataclasses import dataclass
from collections import defaultdict

# Rate limit tracking
_rate_limit_cache: Dict[str, Dict] = {}
_abuse_detection_cache: Dict[str, list] = defaultdict(list)

@dataclass
class RateLimitInfo:
    """GitHub API rate limit information."""
    limit: int
    remaining: int
    reset_time: datetime
    used: int
    is_secondary: bool = False

class PaginatedResponse:
    """Wrapper for paginated API responses."""
    def __init__(self, data: Any, status_code: int, headers: Dict[str, str]):
        self.data = data
        self.status_code = status_code
        self.headers = headers
    
    def json(self) -> Any:
        return self.data
    
    def raise_for_status(self):
        """Raise HTTPError if status code indicates an error."""
        if 400 <= self.status_code < 600:
            raise requests.exceptions.HTTPError(f"HTTP Error: {self.status_code}")
    
    def __getitem__(self, key):
        return self.data[key] if isinstance(self.data, dict) else self.data
    
    def __iter__(self):
        if isinstance(self.data, list):
            return iter(self.data)
        raise TypeError("Response data is not iterable")


def get_github_headers(token):
    """Create standard GitHub API headers with security enhancements."""
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "PyGitUp/2.3.0 (Security-Enhanced)",
        "X-GitHub-Api-Version": "2022-11-28"
    }


def check_rate_limit(token: str) -> Optional[RateLimitInfo]:
    """
    Check current rate limit status without making an API call.
    
    Args:
        token: GitHub token
        
    Returns:
        RateLimitInfo or None if unavailable
    """
    try:
        # Check cache first
        if token in _rate_limit_cache:
            cache = _rate_limit_cache[token]
            if datetime.utcnow() < cache['expires']:
                return RateLimitInfo(**cache['data'])
        
        # Query rate limit endpoint
        response = github_request('GET', 'https://api.github.com/rate_limit', token)
        
        if response.status_code == 200:
            data = response.json()
            core = data.get('resources', {}).get('core', {})
            
            info = RateLimitInfo(
                limit=core.get('limit', 5000),
                remaining=core.get('remaining', 0),
                reset_time=datetime.utcfromtimestamp(core.get('reset', 0)),
                used=core.get('used', 0)
            )
            
            # Cache for 5 minutes
            _rate_limit_cache[token] = {
                'data': {
                    'limit': info.limit,
                    'remaining': info.remaining,
                    'reset_time': info.reset_time,
                    'used': info.used,
                    'is_secondary': False
                },
                'expires': datetime.utcnow() + timedelta(minutes=5)
            }
            
            return info
    except Exception as e:
        if os.environ.get('PYGITUP_DEBUG'):
            print(f"Could not check rate limit: {e}")
    
    return None


def detect_abuse_pattern(token: str, endpoint: str) -> bool:
    """
    Detect potential abuse patterns in API usage.
    
    Args:
        token: GitHub token
        endpoint: API endpoint being called
        
    Returns:
        True if abuse pattern detected
    """
    now = time.time()
    key = f"{token[:8]}:{endpoint}"
    
    # Add to request history
    _abuse_detection_cache[key].append(now)
    
    # Keep only last 60 seconds
    _abuse_detection_cache[key] = [t for t in _abuse_detection_cache[key] if now - t < 60]
    
    # Check for abuse patterns
    request_count = len(_abuse_detection_cache[key])
    
    # More than 30 requests per minute to same endpoint
    if request_count > 30:
        from ..utils.ui import print_warning
        print_warning(f"⚠️ Abuse detection: High request rate to {endpoint} ({request_count}/min)")
        return True
    
    return False


def handle_rate_limit(response: requests.Response, token: str) -> Tuple[bool, int]:
    """
    Handle rate limit responses.
    
    Args:
        response: GitHub API response
        token: GitHub token
        
    Returns:
        Tuple of (should_retry, sleep_duration)
    """
    if response.status_code == 403:
        # Check if it's rate limiting or abuse detection
        if 'X-RateLimit-Remaining' in response.headers:
            remaining = int(response.headers.get('X-RateLimit-Remaining', 1))
            if remaining == 0:
                reset_time = int(response.headers.get('X-RateLimit-Reset', time.time() + 60))
                sleep_duration = max(reset_time - time.time() + 1, 1)
                return True, sleep_duration
        
        # Abuse detection (no rate limit headers)
        if 'abuse' in response.text.lower() or 'too fast' in response.text.lower():
            from ..utils.ui import print_warning
            print_warning("⚠️ GitHub abuse detection triggered. Waiting 60 seconds...")
            return True, 60
    
    elif response.status_code == 429:
        # Too Many Requests
        retry_after = int(response.headers.get('Retry-After', 60))
        return True, retry_after
    
    return False, 0


def github_request(method, url, token, paginate=False, **kwargs):
    """Centralized GitHub API request handler with enhanced rate-limiting and abuse detection."""
    headers = get_github_headers(token)
    if 'headers' in kwargs:
        headers.update(kwargs.pop('headers'))

    results = []
    current_url = url
    max_retries = 5
    consecutive_failures = 0

    try:
        while current_url:
            retry_count = 0
            response = None

            while retry_count < max_retries:
                try:
                    # Check for abuse patterns before making request
                    if detect_abuse_pattern(token, current_url):
                        from ..utils.ui import print_warning
                        print_warning("⏸️ Pausing due to high request rate...")
                        time.sleep(5)
                    
                    response = requests.request(method, current_url, headers=headers, timeout=30, **kwargs)

                    # Handle rate limiting
                    should_retry, sleep_duration = handle_rate_limit(response, token)
                    
                    if should_retry:
                        from ..utils.ui import print_info
                        print_info(f"⏳ Rate limited. Waiting {sleep_duration:.0f} seconds...")
                        time.sleep(min(sleep_duration, 300))  # Cap at 5 minutes
                        continue

                    # Track rate limit info from response headers
                    if 'X-RateLimit-Remaining' in response.headers:
                        remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
                        if remaining < 100:
                            from ..utils.ui import print_warning
                            print_warning(f"⚠️ Rate limit warning: Only {remaining} requests remaining")
                        if remaining < 10:
                            from ..utils.ui import print_error
                            print_error(f"🚨 Critical: Only {remaining} requests remaining!")

                    # Success or non-retryable error
                    consecutive_failures = 0
                    break

                except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                    retry_count += 1
                    consecutive_failures += 1
                    
                    if retry_count == max_retries:
                        raise
                    
                    # Exponential backoff
                    backoff_time = retry_count * 2
                    from ..utils.ui import print_warning
                    print_warning(f"⚠️ Request failed, retrying in {backoff_time}s... ({consecutive_failures} failures)")
                    time.sleep(backoff_time)
                    
                    # If too many consecutive failures, add extra delay
                    if consecutive_failures >= 3:
                        from ..utils.ui import print_info
                        print_info("⏸️ Multiple failures detected. Adding extra delay...")
                        time.sleep(10)

            if not paginate:
                return response

            # Pagination logic
            data = response.json()
            if isinstance(data, list):
                results.extend(data)
            else:
                # If non-list data is returned with paginate=True, return it wrapped
                return PaginatedResponse(data, response.status_code, response.headers)

            # Check for next page
            current_url = None
            if 'Link' in response.headers:
                links = response.headers['Link'].split(',')
                for link in links:
                    if 'rel="next"' in link:
                        current_url = link.split(';')[0].strip('< >')
                        break

        # Return accumulated results as a PaginatedResponse object
        if paginate:
            return PaginatedResponse(results, 200, response.headers)

    except requests.exceptions.RequestException as e:
        # Log the error for debugging
        if os.environ.get('PYGITUP_DEBUG'):
            from ..utils.ui import print_error
            print_error(f"API request failed: {e}")
        raise e

def graphql_request(query, variables, token):
    """Execute a GitHub GraphQL (v4) API request with rate-limiting support."""
    url = "https://api.github.com/graphql"
    payload = {"query": query, "variables": variables}
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
    data = {"message": message, "content": encoded_content}
    if sha: data["sha"] = sha
    return github_request("PUT", url, token, json=data)

def get_commit_history(username, repo_name, token, path=None):
    """Get commit history for a repository or specific file."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/commits"
    params = {}
    if path: params["path"] = path
    return github_request("GET", url, token, params=params)

def create_release(username, repo_name, token, tag_name, name, body=""):
    """Create a new GitHub release."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/releases"
    data = {"tag_name": tag_name, "name": name, "body": body, "draft": False, "prerelease": False}
    return github_request("POST", url, token, json=data)

def create_issue(username, repo_name, token, title, body="", assignees=None):
    """Create a new GitHub issue."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/issues"
    data = {"title": title, "body": body}
    if assignees: data["assignees"] = assignees
    return github_request("POST", url, token, json=data)

def get_pull_requests(username, repo_name, token, state="open"):
    """Get pull requests for a repository."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/pulls"
    params = {"state": state}
    return github_request("GET", url, token, params=params)

def create_pull_request(username, repo_name, token, title, head, base, body=""):
    """Create a new pull request."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/pulls"
    data = {"title": title, "head": head, "base": base, "body": body}
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

def get_repo_forks(owner, repo, token):
    """Fetch all forks of a repository."""
    url = f"https://api.github.com/repos/{owner}/{repo}/forks"
    return github_request("GET", url, token, params={"per_page": 100})

def compare_commits(owner, repo, base, head, token):
    """Compare two commits/branches/refs."""
    url = f"https://api.github.com/repos/{owner}/{repo}/compare/{base}...{head}"
    return github_request("GET", url, token)

def get_repo_languages(username, repo_name, token):
    """Get detailed language breakdown for a repository."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/languages"
    return github_request("GET", url, token)

def get_community_profile(username, repo_name, token):
    """Get community health metrics (presence of README, LICENSE, etc)."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/community/profile"
    return github_request("GET", url, token)

def get_latest_release(username, repo_name, token):
    """Get the latest release for a repository."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/releases/latest"
    return github_request("GET", url, token)

def get_repo_contents(username, repo_name, token, path=""):
    """Get repository contents (shallow)."""
    url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{path}"
    return github_request("GET", url, token)

def get_repo_tree_recursive(username, repo_name, token, branch="main"):
    """Fetch the entire repository tree recursively using the Git Trees API."""
    ref_url = f"https://api.github.com/repos/{username}/{repo_name}/git/ref/heads/{branch}"
    ref_resp = github_request("GET", ref_url, token)
    if ref_resp.status_code != 200: return ref_resp
    sha = ref_resp.json()['object']['sha']
    tree_url = f"https://api.github.com/repos/{username}/{repo_name}/git/trees/{sha}?recursive=1"
    return github_request("GET", tree_url, token)

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

def upload_ssh_key(token, title, key):
    """Upload a new SSH public key to the user's GitHub account."""
    url = "https://api.github.com/user/keys"
    data = {"title": title, "key": key}
    return github_request("POST", url, token, json=data)

def delete_repo_api(username, repo_name, token):
    """Delete a GitHub repository."""
    url = f"https://api.github.com/repos/{username}/{repo_name}"
    return github_request("DELETE", url, token)

# --- SOCIAL AUTOMATION ENDPOINTS ---

def star_repo(owner, repo, token):
    """Star a GitHub repository."""
    url = f"https://api.github.com/user/starred/{owner}/{repo}"
    return github_request("PUT", url, token)

def follow_user(target_username, token):
    """Follow a GitHub user."""
    url = f"https://api.github.com/user/following/{target_username}"
    return github_request("PUT", url, token)

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
