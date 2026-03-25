"""
AI-Powered Issue Labeling and Prioritization
=============================================
Automatically labels and prioritizes GitHub issues using AI analysis.
"""

import requests
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from ..utils.ui import print_info, print_success, print_error, print_warning, console
from ..utils.ai import call_gemini_api, validate_ai_key
from ..github.api import github_request


# Predefined label categories with descriptions
LABEL_CATEGORIES = {
    "bug": {
        "color": "d73a4a",
        "description": "Something isn't working correctly"
    },
    "enhancement": {
        "color": "a2eeef",
        "description": "New feature or request"
    },
    "documentation": {
        "color": "0075ca",
        "description": "Improvements or additions to documentation"
    },
    "good first issue": {
        "color": "7057ff",
        "description": "Good for newcomers"
    },
    "help wanted": {
        "color": "008672",
        "description": "Extra attention is needed"
    },
    "question": {
        "color": "d876e3",
        "description": "Further information is requested"
    },
    "wontfix": {
        "color": "ffffff",
        "description": "This will not be worked on"
    },
    "duplicate": {
        "color": "cfd3d7",
        "description": "This issue or pull request already exists"
    },
    "invalid": {
        "color": "e4e669",
        "description": "This doesn't seem right"
    },
    "priority:critical": {
        "color": "b60205",
        "description": "Critical priority - needs immediate attention"
    },
    "priority:high": {
        "color": "d93f0b",
        "description": "High priority"
    },
    "priority:medium": {
        "color": "fbca04",
        "description": "Medium priority"
    },
    "priority:low": {
        "color": "0e8a16",
        "description": "Low priority"
    },
    "security": {
        "color": "d93f0b",
        "description": "Security-related issue"
    },
    "performance": {
        "color": "006b75",
        "description": "Performance improvement"
    },
}


def get_or_create_labels(owner: str, repo: str, token: str, 
                          labels_to_ensure: List[str]) -> Dict[str, str]:
    """
    Ensure labels exist in the repository, create if missing.
    
    Returns:
        Dict mapping label names to their existence status
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/labels"
    existing_labels = {}
    
    # Fetch existing labels
    response = github_request("GET", url, token)
    if response.status_code == 200:
        for label in response.json():
            existing_labels[label["name"].lower()] = label["name"]
    
    # Create missing labels
    for label_name in labels_to_ensure:
        if label_name.lower() not in existing_labels:
            category = LABEL_CATEGORIES.get(label_name, {})
            data = {
                "name": label_name,
                "color": category.get("color", "ededed"),
                "description": category.get("description", "")
            }
            create_response = github_request("POST", url, token, json=data)
            if create_response.status_code in [200, 201]:
                existing_labels[label_name.lower()] = label_name
                print_info(f"Created label: {label_name}")
            else:
                print_warning(f"Could not create label: {label_name}")
    
    return existing_labels


def analyze_issue_with_ai(api_key: str, issue: Dict) -> Dict:
    """
    Analyze a single issue using AI to determine labels and priority.
    
    Args:
        api_key: Gemini API key
        issue: Issue dictionary from GitHub API
    
    Returns:
        Dict with suggested_labels, priority, and reasoning
    """
    title = issue.get("title", "")
    body = issue.get("body", "") or ""
    comments_count = issue.get("comments", 0)
    created_at = issue.get("created_at", "")
    
    # Prepare context for AI
    prompt = f"""
Analyze this GitHub issue and provide:
1. Suggested labels (from: bug, enhancement, documentation, good first issue, help wanted, question, security, performance)
2. Priority level (critical, high, medium, low)
3. Brief reasoning

ISSUE TITLE: {title}

ISSUE BODY:
{body[:2000]}

COMMENTS: {comments_count}
CREATED: {created_at}

Respond in this exact JSON format (no markdown, no extra text):
{{
    "labels": ["label1", "label2"],
    "priority": "critical|high|medium|low",
    "reasoning": "Brief explanation"
}}
"""
    
    response_text = call_gemini_api(api_key, prompt, timeout=30)
    
    if not response_text:
        return {
            "labels": [],
            "priority": "medium",
            "reasoning": "AI analysis failed"
        }
    
    # Parse JSON response
    try:
        import json
        # Clean up response - remove markdown code blocks if present
        response_text = response_text.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        response_text = response_text.strip()
        
        result = json.loads(response_text)
        return {
            "labels": result.get("labels", []),
            "priority": result.get("priority", "medium"),
            "reasoning": result.get("reasoning", "")
        }
    except Exception as e:
        print_warning(f"Failed to parse AI response: {e}")
        return {
            "labels": [],
            "priority": "medium",
            "reasoning": f"Parse error: {str(e)}"
        }


def ai_label_issues(owner: str, repo: str, token: str, api_key: str,
                    issue_numbers: List[int] = None,
                    state: str = "open",
                    dry_run: bool = False) -> List[Dict]:
    """
    Apply AI-generated labels to issues.
    
    Args:
        owner: Repository owner
        repo: Repository name
        token: GitHub token
        api_key: Gemini API key
        issue_numbers: Specific issues to label (None = all open)
        state: Issue state filter
        dry_run: If True, don't actually apply labels
    
    Returns:
        List of results for each processed issue
    """
    if not validate_ai_key(api_key, "AI issue labeling"):
        return []
    
    print_info(f"🏷️  Starting AI-powered issue labeling for {owner}/{repo}...")
    
    # Ensure labels exist
    labels_to_ensure = list(LABEL_CATEGORIES.keys())
    existing_labels = get_or_create_labels(owner, repo, token, labels_to_ensure)
    
    # Fetch issues
    url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    params = {"state": state, "per_page": 100}
    
    response = github_request("GET", url, token, params=params)
    
    if response.status_code != 200:
        print_error(f"Failed to fetch issues: {response.status_code}")
        return []
    
    issues = response.json()
    
    # Filter to specific issues if requested
    if issue_numbers:
        issues = [i for i in issues if i["number"] in issue_numbers]
    
    results = []
    
    for issue in issues:
        # Skip pull requests (they appear in issues endpoint)
        if "pull_request" in issue:
            continue
        
        issue_num = issue["number"]
        print_info(f"Analyzing issue #{issue_num}: {issue['title'][:50]}...")
        
        # Analyze with AI
        analysis = analyze_issue_with_ai(api_key, issue)
        
        # Filter to valid labels
        valid_labels = [
            existing_labels.get(label.lower(), label) 
            for label in analysis["labels"]
            if label.lower() in existing_labels or label.startswith("priority:")
        ]
        
        # Add priority label
        priority = analysis.get("priority", "medium")
        priority_label = f"priority:{priority}"
        if priority_label not in valid_labels:
            valid_labels.append(priority_label)
        
        result = {
            "number": issue_num,
            "title": issue["title"],
            "suggested_labels": valid_labels,
            "priority": priority,
            "reasoning": analysis["reasoning"],
            "applied": False
        }
        
        # Apply labels
        if not dry_run and valid_labels:
            labels_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_num}/labels"
            
            # Replace all labels with new ones (or use POST to add)
            label_response = github_request("PUT", labels_url, token, json={"labels": valid_labels})
            
            if label_response.status_code in [200, 201]:
                result["applied"] = True
                print_success(f"Applied labels to #{issue_num}")
            else:
                print_warning(f"Failed to apply labels to #{issue_num}")
        else:
            print_info(f"Would apply labels: {', '.join(valid_labels)}" if valid_labels else "No labels suggested")
        
        results.append(result)
    
    return results


def ai_prioritize_issues(owner: str, repo: str, token: str, api_key: str,
                         issue_numbers: List[int] = None,
                         dry_run: bool = False) -> List[Dict]:
    """
    Analyze and prioritize issues without necessarily applying labels.
    
    Args:
        owner: Repository owner
        repo: Repository name
        token: GitHub token
        api_key: Gemini API key
        issue_numbers: Specific issues to prioritize
        dry_run: If True, just report without changes
    
    Returns:
        List of prioritized issues with analysis
    """
    if not validate_ai_key(api_key, "AI issue prioritization"):
        return []
    
    print_info(f"📊 Starting AI-powered issue prioritization for {owner}/{repo}...")
    
    # Fetch issues
    url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    params = {"state": "open", "per_page": 100}
    
    response = github_request("GET", url, token, params=params)
    
    if response.status_code != 200:
        print_error(f"Failed to fetch issues: {response.status_code}")
        return []
    
    issues = response.json()
    
    # Filter to specific issues if requested
    if issue_numbers:
        issues = [i for i in issues if i["number"] in issue_numbers]
    
    # Filter out PRs
    issues = [i for i in issues if "pull_request" not in i]
    
    results = []
    
    for issue in issues:
        issue_num = issue["number"]
        print_info(f"Prioritizing issue #{issue_num}...")
        
        analysis = analyze_issue_with_ai(api_key, issue)
        
        result = {
            "number": issue_num,
            "title": issue["title"],
            "priority": analysis["priority"],
            "labels": analysis["labels"],
            "reasoning": analysis["reasoning"],
            "created_at": issue["created_at"],
            "comments": issue.get("comments", 0)
        }
        
        results.append(result)
    
    # Sort by priority
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    results.sort(key=lambda x: (priority_order.get(x["priority"], 2), x["number"]))
    
    # Print summary
    print_success(f"Prioritized {len(results)} issues")
    print("\n📋 Priority Summary:")
    for priority in ["critical", "high", "medium", "low"]:
        count = len([r for r in results if r["priority"] == priority])
        if count > 0:
            print(f"  {priority.upper()}: {count} issues")
    
    return results


def auto_label_and_triage(owner: str, repo: str, token: str, api_key: str,
                          new_issues_only: bool = True,
                          dry_run: bool = False) -> Dict:
    """
    Combined function to automatically label and triage new issues.
    
    Args:
        owner: Repository owner
        repo: Repository name
        token: GitHub token
        api_key: Gemini API key
        new_issues_only: Only process issues created in last 7 days
        dry_run: If True, report without applying changes
    
    Returns:
        Summary dictionary with statistics
    """
    from datetime import timedelta
    
    if not validate_ai_key(api_key, "Auto label and triage"):
        return {"processed": 0, "labeled": 0, "errors": 0}
    
    print_info("🤖 Starting automatic issue labeling and triage...")
    
    # Fetch issues
    url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    params = {"state": "open", "per_page": 100}
    
    response = github_request("GET", url, token, params=params)
    
    if response.status_code != 200:
        print_error(f"Failed to fetch issues: {response.status_code}")
        return {"processed": 0, "labeled": 0, "errors": 0}
    
    issues = [i for i in response.json() if "pull_request" not in i]
    
    # Filter to new issues only
    if new_issues_only:
        week_ago = datetime.utcnow() - timedelta(days=7)
        filtered_issues = []
        for issue in issues:
            created_at = issue.get("created_at", "")
            if created_at:
                try:
                    issue_date = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    if issue_date.replace(tzinfo=None) >= week_ago:
                        filtered_issues.append(issue)
                except:
                    pass
        issues = filtered_issues
        print_info(f"Found {len(issues)} issues from the last 7 days")
    
    # Ensure labels exist
    labels_to_ensure = list(LABEL_CATEGORIES.keys())
    existing_labels = get_or_create_labels(owner, repo, token, labels_to_ensure)
    
    stats = {"processed": 0, "labeled": 0, "errors": 0, "by_priority": {}}
    
    for issue in issues:
        issue_num = issue["number"]
        stats["processed"] += 1
        
        try:
            analysis = analyze_issue_with_ai(api_key, issue)
            
            # Build label list
            valid_labels = [
                existing_labels.get(label.lower(), label)
                for label in analysis["labels"]
                if label.lower() in existing_labels
            ]
            
            priority = analysis.get("priority", "medium")
            priority_label = f"priority:{priority}"
            valid_labels.append(priority_label)
            
            # Track by priority
            stats["by_priority"][priority] = stats["by_priority"].get(priority, 0) + 1
            
            # Apply labels
            if not dry_run and valid_labels:
                labels_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_num}/labels"
                label_response = github_request("PUT", labels_url, token, json={"labels": valid_labels})
                
                if label_response.status_code in [200, 201]:
                    stats["labeled"] += 1
                    print_success(f"✓ Issue #{issue_num} labeled: {', '.join(valid_labels)}")
                else:
                    stats["errors"] += 1
                    print_warning(f"Failed to label issue #{issue_num}")
            else:
                print_info(f"Issue #{issue_num}: priority={priority}, labels={valid_labels}")
                
        except Exception as e:
            stats["errors"] += 1
            print_error(f"Error processing issue #{issue_num}: {e}")
    
    # Print summary
    print("\n📊 Triage Summary:")
    print(f"  Processed: {stats['processed']} issues")
    print(f"  Labeled: {stats['labeled']} issues")
    print(f"  Errors: {stats['errors']}")
    
    if stats["by_priority"]:
        print("\n  By Priority:")
        for priority, count in sorted(stats["by_priority"].items()):
            print(f"    {priority}: {count}")
    
    return stats
