from ..github.api import get_contributors, get_issues

def generate_analytics(github_username, github_token, config, args=None):
    """Generate team contribution reports."""
    if args and args.dry_run:
        print("*** Dry Run Mode: No changes will be made. ***")
        print("Would generate team contribution analytics.")
        return

    if args and args.repo:
        repo_name = args.repo
    else:
        repo_name = input("Enter repository name: ")
    
    period = config["analytics"]["period"]
    if args and args.period:
        period = args.period
    else:
        period_input = input(f"Enter period (default: {period}): ")
        period = period_input if period_input else period
    
    print(f"Generating analytics for {repo_name} for period: {period}")
    
    # Get contributors
    try:
        response = get_contributors(github_username, repo_name, github_token)
        if response.status_code == 200:
            contributors = response.json()
            print(f"\n=== Contribution Report for {repo_name} ===")
            print(f"Period: {period}")
            print(f"Total contributors: {len(contributors)}")
            print("\nTop contributors:")
            for i, contributor in enumerate(contributors[:10], 1):
                print(f"{i}. {contributor['login']}: {contributor['contributions']} contributions")
        else:
            print(f"Error fetching contributors: {response.status_code}")
    except Exception as e:
        print(f"Error generating analytics: {e}")
    
    # Get issues
    try:
        response = get_issues(github_username, repo_name, github_token)
        if response.status_code == 200:
            issues = response.json()
            open_issues = [issue for issue in issues if issue['state'] == 'open']
            closed_issues = [issue for issue in issues if issue['state'] == 'closed']
            print(f"\nIssue Statistics:")
            print(f"Total issues: {len(issues)}")
            print(f"Open issues: {len(open_issues)}")
            print(f"Closed issues: {len(closed_issues)}")
        else:
            print(f"Error fetching issues: {response.status_code}")
    except Exception as e:
        print(f"Error fetching issues: {e}")
