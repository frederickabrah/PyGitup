from ..github.api import get_contributors, get_issues
from .ui import print_success, print_error, print_info, print_header, Table, box, console

def generate_analytics(github_username, github_token, config, args=None):
    """Generate team contribution reports with sophisticated UI."""
    if args and args.dry_run:
        print_info("*** Dry Run Mode: No changes will be made. ***")
        print_info("Would generate team contribution analytics.")
        return

    print_header("Collaboration Analytics")
    if args and args.repo:
        repo_name = args.repo
    else:
        repo_name = input("Enter repository name: ")
    
    period = config["analytics"]["period"]
    if args and args.period:
        period = args.period
    else:
        period_input = input(f"Enter period (e.g., last-month, all-time) [default: {period}]: ")
        period = period_input if period_input else period
    
    print_info(f"Generating analytics for {repo_name}...")
    
    # Contributors Table
    try:
        response = get_contributors(github_username, repo_name, github_token)
        if response.status_code == 200:
            contributors = response.json()
            
            table = Table(title=f"Contribution Report: {repo_name}", box=box.ROUNDED, show_header=True, header_style="bold magenta")
            table.add_column("Rank", justify="center", style="cyan")
            table.add_column("User", style="white")
            table.add_column("Contributions", justify="right", style="green")
            
            for i, contributor in enumerate(contributors[:10], 1):
                table.add_row(str(i), contributor['login'], str(contributor['contributions']))
            
            console.print(table)
            print_info(f"Total contributors detected: {len(contributors)}")
        else:
            print_error(f"Error fetching contributors: {response.status_code}")
    except Exception as e:
        print_error(f"Error generating contributor analytics: {e}")
    
    # Issue Statistics
    try:
        response = get_issues(github_username, repo_name, github_token)
        if response.status_code == 200:
            issues = response.json()
            open_issues = [issue for issue in issues if issue['state'] == 'open']
            closed_issues = [issue for issue in issues if issue['state'] == 'closed']
            
            issue_table = Table(title="Issue Lifecycle Statistics", box=box.SIMPLE, show_header=True)
            issue_table.add_column("Metric", style="cyan")
            issue_table.add_column("Value", justify="right", style="yellow")
            
            issue_table.add_row("Total Issues", str(len(issues)))
            issue_table.add_row("Open Issues", str(len(open_issues)))
            issue_table.add_row("Closed Issues", str(len(closed_issues)))
            
            if len(issues) > 0:
                closure_rate = (len(closed_issues) / len(issues)) * 100
                issue_table.add_row("Closure Rate", f"{closure_rate:.1f}%")
            
            console.print(issue_table)
        else:
            print_error(f"Error fetching issues: {response.status_code}")
    except Exception as e:
        print_error(f"Error generating issue analytics: {e}")