"""
AI-Powered Release Note Generation
===================================
Generates comprehensive release notes from commits and PRs using AI.
"""

import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from ..utils.ui import print_info, print_success, print_error, print_warning, console
from ..utils.ai import call_gemini_api, validate_ai_key
from ..github.api import github_request, get_commit_history, get_pull_requests


def fetch_commits_between_tags(owner: str, repo: str, token: str, 
                                from_tag: str = None, to_tag: str = None,
                                since_date: str = None) -> List[Dict]:
    """
    Fetch commits between two tags or since a specific date.
    
    Args:
        owner: Repository owner
        repo: Repository name
        token: GitHub token
        from_tag: Starting tag (optional)
        to_tag: Ending tag (optional, defaults to latest)
        since_date: ISO format date string (optional)
    
    Returns:
        List of commit dictionaries
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/commits"
    params = {"per_page": 100}
    
    if from_tag:
        params["base"] = from_tag
    if to_tag:
        params["head"] = to_tag
    if since_date:
        params["since"] = since_date
    
    response = github_request("GET", url, token, params=params, paginate=True)
    
    if response.status_code == 200:
        return response.data if isinstance(response.data, list) else []
    
    print_error(f"Failed to fetch commits: {response.status_code}")
    return []


def fetch_prs_between_tags(owner: str, repo: str, token: str,
                           from_tag: str = None, to_tag: str = None,
                           state: str = "closed") -> List[Dict]:
    """
    Fetch pull requests between tags or in a date range.
    
    Args:
        owner: Repository owner
        repo: Repository name
        token: GitHub token
        from_tag: Starting tag (optional)
        to_tag: Ending tag (optional)
        state: PR state filter (default: closed)
    
    Returns:
        List of PR dictionaries
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
    params = {"state": state, "per_page": 100}
    
    response = github_request("GET", url, token, params=params, paginate=True)
    
    if response.status_code == 200:
        prs = response.data if isinstance(response.data, list) else []
        
        # Filter PRs by merge date if tags specified
        if from_tag or to_tag:
            filtered_prs = []
            for pr in prs:
                if pr.get("merged_at"):
                    filtered_prs.append(pr)
            return filtered_prs
        return prs
    
    print_error(f"Failed to fetch PRs: {response.status_code}")
    return []


def format_commits_for_ai(commits: List[Dict], max_commits: int = 50) -> str:
    """Format commit history into a readable string for AI processing."""
    formatted = []
    
    for commit in commits[:max_commits]:
        sha = commit.get("sha", "")[:7]
        message = commit.get("commit", {}).get("message", "").split("\n")[0]
        author = commit.get("commit", {}).get("author", {}).get("name", "Unknown")
        date = commit.get("commit", {}).get("author", {}).get("date", "")
        
        if date:
            date_obj = datetime.fromisoformat(date.replace("Z", "+00:00"))
            date_str = date_obj.strftime("%Y-%m-%d")
        else:
            date_str = "Unknown"
        
        formatted.append(f"- [{sha}] {message} by {author} ({date_str})")
    
    return "\n".join(formatted)


def format_prs_for_ai(prs: List[Dict], max_prs: int = 30) -> str:
    """Format pull requests into a readable string for AI processing."""
    formatted = []
    
    for pr in prs[:max_prs]:
        number = pr.get("number", "")
        title = pr.get("title", "Untitled")
        author = pr.get("user", {}).get("login", "Unknown")
        merged_at = pr.get("merged_at", "")
        labels = [label.get("name", "") for label in pr.get("labels", [])]
        
        if merged_at:
            date_obj = datetime.fromisoformat(merged_at.replace("Z", "+00:00"))
            date_str = date_obj.strftime("%Y-%m-%d")
        else:
            date_str = "Not merged"
        
        label_str = f" [{', '.join(labels)}]" if labels else ""
        formatted.append(f"- #{number}: {title} by @{author}{label_str} ({date_str})")
    
    return "\n".join(formatted)


def generate_ai_release_notes(api_key: str, repo_name: str, 
                               commits: List[Dict], prs: List[Dict],
                               version: str = None,
                               include_sections: List[str] = None) -> str:
    """
    Generate AI-powered release notes from commits and PRs.
    
    Args:
        api_key: Gemini API key
        repo_name: Repository name (e.g., "owner/repo")
        commits: List of commit dictionaries
        prs: List of PR dictionaries
        version: Version string for the release
        include_sections: Sections to include (default: all)
    
    Returns:
        Formatted release notes as markdown
    """
    if not validate_ai_key(api_key, "AI release note generation"):
        return None
    
    commits_text = format_commits_for_ai(commits)
    prs_text = format_prs_for_ai(prs)
    
    sections_hint = ""
    if include_sections:
        sections_hint = f"Include these sections: {', '.join(include_sections)}"
    
    version_hint = f"Version: {version}" if version else ""
    
    prompt = f"""
Generate professional release notes for the GitHub repository "{repo_name}".

{version_hint}

RECENT COMMITS:
{commits_text}

MERGED PULL REQUESTS:
{prs_text}

{sections_hint}

Create comprehensive release notes with:
1. A brief introduction summarizing the release
2. Categorized changes (Features, Bug Fixes, Improvements, Documentation, etc.)
3. Breaking changes section (if any)
4. Contributor acknowledgments
5. Installation/upgrade instructions

Use markdown formatting. Be specific about what changed. No placeholders like [TODO].
Make it professional and ready to publish.
"""
    
    return call_gemini_api(api_key, prompt, timeout=60)


def generate_release_notes_from_commits(owner: str, repo: str, token: str,
                                         api_key: str = None,
                                         version: str = None,
                                         from_tag: str = None,
                                         to_tag: str = None,
                                         since_days: int = 30) -> Optional[str]:
    """
    Main function to generate release notes from commit history.
    
    Args:
        owner: Repository owner
        repo: Repository name
        token: GitHub token
        api_key: Gemini API key (optional, falls back to template)
        version: Version string
        from_tag: Starting tag
        to_tag: Ending tag
        since_days: Days to look back if no tags specified
    
    Returns:
        Release notes as markdown string
    """
    print_info(f"📝 Generating release notes for {owner}/{repo}...")
    
    # Fetch commits
    since_date = None
    if not from_tag and not to_tag:
        since_date = (datetime.utcnow() - timedelta(days=since_days)).isoformat() + "Z"
        print_info(f"Fetching commits since {since_date[:10]}...")
    
    commits = fetch_commits_between_tags(owner, repo, token, from_tag, to_tag, since_date)
    
    if not commits:
        print_warning("No commits found in the specified range.")
        return None
    
    print_success(f"Found {len(commits)} commits")
    
    # Fetch PRs
    print_info("Fetching pull requests...")
    prs = fetch_prs_between_tags(owner, repo, token, from_tag, to_tag)
    print_success(f"Found {len(prs)} merged PRs")
    
    # Generate with AI if key available
    if api_key:
        print_info("🤖 Generating AI-powered release notes...")
        release_notes = generate_ai_release_notes(
            api_key, f"{owner}/{repo}", commits, prs, version
        )
        
        if release_notes:
            print_success("Release notes generated successfully!")
            return release_notes
    
    # Fallback to template-based generation
    print_info("Generating template-based release notes...")
    return generate_template_release_notes(owner, repo, commits, prs, version)


def generate_template_release_notes(owner: str, repo: str, 
                                     commits: List[Dict], 
                                     prs: List[Dict],
                                     version: str = None) -> str:
    """
    Generate release notes using a template (fallback when AI not available).
    
    Args:
        owner: Repository owner
        repo: Repository name
        commits: List of commits
        prs: List of PRs
        version: Version string
    
    Returns:
        Formatted release notes
    """
    version_str = f"## Release {version}\n\n" if version else "## Latest Release\n\n"
    
    # Categorize commits by conventional commit type
    features = []
    fixes = []
    improvements = []
    docs = []
    other = []
    
    for commit in commits[:30]:
        message = commit.get("commit", {}).get("message", "").split("\n")[0].lower()
        full_message = commit.get("commit", {}).get("message", "")
        sha = commit.get("sha", "")[:7]
        
        if message.startswith("feat") or "add" in message or "new" in message:
            features.append(f"- {full_message.split(chr(10))[0]} ({sha})")
        elif message.startswith("fix") or "bug" in message or "issue" in message:
            fixes.append(f"- {full_message.split(chr(10))[0]} ({sha})")
        elif message.startswith("improve") or "perf" in message or "optimize" in message:
            improvements.append(f"- {full_message.split(chr(10))[0]} ({sha})")
        elif message.startswith("doc") or "readme" in message:
            docs.append(f"- {full_message.split(chr(10))[0]} ({sha})")
        else:
            other.append(f"- {full_message.split(chr(10))[0]} ({sha})")
    
    # Build release notes
    notes = [version_str]
    notes.append(f"**Repository:** [{owner}/{repo}](https://github.com/{owner}/{repo})\n")
    notes.append(f"**Date:** {datetime.utcnow().strftime('%Y-%m-%d')}\n")
    
    if features:
        notes.append("\n### 🚀 Features\n")
        notes.extend(features[:10])
    
    if fixes:
        notes.append("\n### 🐛 Bug Fixes\n")
        notes.extend(fixes[:10])
    
    if improvements:
        notes.append("\n### ⚡ Improvements\n")
        notes.extend(improvements[:10])
    
    if docs:
        notes.append("\n### 📚 Documentation\n")
        notes.extend(docs[:10])
    
    if other:
        notes.append("\n### 📦 Other Changes\n")
        notes.extend(other[:5])
    
    # Add PR summary
    if prs:
        notes.append("\n### 🔀 Merged Pull Requests\n")
        for pr in prs[:15]:
            number = pr.get("number", "")
            title = pr.get("title", "Untitled")
            author = pr.get("user", {}).get("login", "Unknown")
            notes.append(f"- #{number}: {title} by @{author}")
    
    # Contributors
    contributors = set()
    for commit in commits:
        author = commit.get("commit", {}).get("author", {}).get("name", "")
        if author:
            contributors.add(author)
    
    if contributors:
        notes.append("\n### 👏 Contributors\n")
        notes.append("Thanks to: " + ", ".join(sorted(contributors)))
    
    return "\n".join(notes)


def save_release_notes(notes: str, filename: str = "RELEASE_NOTES.md") -> bool:
    """Save release notes to a file."""
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(notes)
        print_success(f"Release notes saved to {filename}")
        return True
    except Exception as e:
        print_error(f"Failed to save release notes: {e}")
        return False
