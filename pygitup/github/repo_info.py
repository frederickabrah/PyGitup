import inquirer
from urllib.parse import urlparse
from .api import get_repo_info, github_request, get_commit_history, get_issues, get_contributors, get_repo_languages, get_community_profile, get_latest_release, get_repo_forks, compare_commits
from ..utils.ui import display_repo_info, display_traffic_trends, print_error, print_warning, print_info, print_header, print_success

def get_fork_intelligence(owner, repo, token):
    """Deep scan of the Forks Network to find hidden community improvements."""
    print_header("Network & Fork Intelligence")
    print_info(f"Scanning community forks for {owner}/{repo}...")
    
    try:
        forks_resp = get_repo_forks(owner, repo, token)
        if forks_resp.status_code != 200:
            print_error("Failed to fetch forks list.")
            return
            
        forks = forks_resp.json()
        if not forks:
            print_info("No forks found for this repository.")
            return
            
        print_info(f"Analyzing {len(forks)} forks for unique activity...")
        
        found_unique = False
        for fork in forks:
            f_owner = fork['owner']['login']
            f_name = fork['name']
            f_default_branch = fork['default_branch']
            
            print(f"  🔍 Checking @{f_owner}/{f_name} [{f_default_branch}]...")
            
            # Compare the fork's default branch against the upstream's default branch
            compare_url = f"https://api.github.com/repos/{owner}/{repo}/compare/{owner}:{f_default_branch}...{f_owner}:{f_default_branch}"
            compare_resp = github_request("GET", compare_url, token)
            
            if compare_resp.status_code == 200:
                data = compare_resp.json()
                ahead = data.get('ahead_by', 0)
                behind = data.get('behind_by', 0)
                
                status = "Synced"
                if ahead > 0 and behind > 0: status = "Diverged"
                elif ahead > 0: status = "Ahead"
                elif behind > 0: status = "Behind"
                
                print(f"     └─ Status: {status} | Ahead: {ahead} | Behind: {behind}")
                
                if ahead > 0:
                    found_unique = True
                    print_success(f"     🌟 Discovery: Unique code found in @{f_owner}!")
                    print(f"        View Diff: {data.get('html_url')}")
            else:
                print_warning(f"     ⚠️  Could not compare: {compare_resp.status_code}")
        
        if not found_unique:
            print_info("No unique community work detected in forks (all forks are in-sync or behind).")
            
    except Exception as e:
        print_error(f"Fork intelligence scan failed: {e}")

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

def get_repo_health_metrics(username, repo_name, token):
    """Calculate repository health metrics."""
    metrics = {}

    # Get recent commits
    try:
        commits_response = get_commit_history(username, repo_name, token)
        if commits_response.status_code == 200:
            commits = commits_response.json()
            metrics['recent_commits'] = len(commits)
            if commits:
                # Calculate median time between commits (Sophisticated Velocity Math)
                from datetime import datetime
                dates = [datetime.fromisoformat(c['commit']['author']['date'].replace('Z', '+00:00')) 
                         for c in commits[:20]] # Last 20 commits
                if len(dates) > 1:
                    time_diffs = sorted([(dates[i] - dates[i+1]).total_seconds() / 86400 for i in range(len(dates)-1)])
                    # Use median to avoid outlier skew
                    median_days = time_diffs[len(time_diffs)//2]
                    metrics['development_velocity_days'] = round(median_days, 2)
                    
                    # Burst detection: comparing last 3 to last 20
                    recent_burst = sum(time_diffs[:3]) / 3
                    metrics['activity_status'] = "Active/Bursting" if recent_burst < median_days else "Stable"
    except Exception:
        pass

    # Get closed issues
    try:
        issues_response = get_issues(username, repo_name, token, state='closed')
        if issues_response.status_code == 200:
            closed_issues = issues_response.json()
            metrics['closed_issues'] = len(closed_issues)
    except Exception:
        pass

    # Get contributors
    try:
        contrib_response = get_contributors(username, repo_name, token)
        if contrib_response.status_code == 200:
            contributors = contrib_response.json()
            metrics['contributors_count'] = len(contributors)
    except Exception:
        pass

    return metrics

def get_detailed_repo_info(args, github_token):
    """Fetch and display comprehensive repository information with insights."""
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

    print(f"\nFetching comprehensive report for '{owner}/{repo_name}'...")
    
    try:
        # Get basic repo info
        repo_response = get_repo_info(owner, repo_name, github_token)
        if repo_response.status_code != 200:
            print_warning(f"API Error: {repo_response.status_code} - {repo_response.text}")
            print_warning("Attempting to fallback to HTML scraping...")
            
            scraped_data = scrape_repo_info(url)
            if scraped_data:
                display_repo_info(scraped_data)
                return
            else:
                print_error("Failed to fetch repository data via API and Scraping.")
                return

        repo_data = repo_response.json()

        # OSINT Upgrade: Fetch deep metadata
        try:
            # Languages
            lang_resp = get_repo_languages(owner, repo_name, github_token)
            if lang_resp.status_code == 200:
                repo_data['osint_languages'] = lang_resp.json()
            
            # Community Profile
            comm_resp = get_community_profile(owner, repo_name, github_token)
            if comm_resp.status_code == 200:
                repo_data['osint_community'] = comm_resp.json()
            
            # Latest Release
            rel_resp = get_latest_release(owner, repo_name, github_token)
            if rel_resp.status_code == 200:
                repo_data['osint_release'] = rel_resp.json()
        except Exception:
            pass

        # Add traffic analytics (requires push access)
        traffic_data = {}
        try:
            # Clones data
            clones_response = github_request("GET", f"https://api.github.com/repos/{owner}/{repo_name}/traffic/clones", github_token)
            if clones_response.status_code == 200:
                traffic_data['clones'] = clones_response.json()

            # Views data
            views_response = github_request("GET", f"https://api.github.com/repos/{owner}/{repo_name}/traffic/views", github_token)
            if views_response.status_code == 200:
                traffic_data['views'] = views_response.json()

            # Referrers data
            referrers_response = github_request("GET", f"https://api.github.com/repos/{owner}/{repo_name}/traffic/popular/referrers", github_token)
            if referrers_response.status_code == 200:
                traffic_data['referrers'] = referrers_response.json()

            if traffic_data:
                repo_data['traffic'] = traffic_data
        except Exception as e:
            # Silently fail for traffic data if permissions are missing, or log warning
            pass

        # Add health metrics
        health_metrics = get_repo_health_metrics(owner, repo_name, github_token)
        repo_data['health'] = health_metrics
        
        # Display comprehensive report
        display_repo_info(repo_data)
        
        if 'traffic' in repo_data and repo_data['traffic']:
            display_traffic_trends(repo_data['traffic'])

    except Exception as e:
        print_error(f"An unexpected error occurred: {e}")