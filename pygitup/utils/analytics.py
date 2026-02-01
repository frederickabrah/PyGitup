
import json
import csv
import os
from datetime import datetime, timedelta
from ..github.api import get_contributors, get_issues, github_request
from .ui import print_success, print_error, print_info, print_header, Table, box, console

def calculate_resolution_time(issues):
    """Calculates average time to close an issue in hours."""
    closed_issues = [i for i in issues if i['state'] == 'closed' and i.get('closed_at')]
    if not closed_issues:
        return 0
    
    total_hours = 0
    for issue in closed_issues:
        created = datetime.fromisoformat(issue['created_at'].replace('Z', '+00:00'))
        closed = datetime.fromisoformat(issue['closed_at'].replace('Z', '+00:00'))
        duration = closed - created
        total_hours += duration.total_seconds() / 3600
        
    return round(total_hours / len(closed_issues), 1)

def predict_growth(current_count, created_at_str):
    """Simple linear projection for repository growth."""
    try:
        created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
        days_old = (datetime.now(created_at.tzinfo) - created_at).days
        if days_old <= 0: return current_count
        
        growth_rate = current_count / days_old
        prediction_90_days = int(current_count + (growth_rate * 90))
        return prediction_90_days
    except Exception:
        return current_count

def export_report(repo_name, data, format='json'):
    """Exports analytics data to a file."""
    filename = f"{repo_name}_analytics_{datetime.now().strftime('%Y%m%d')}.{format}"
    try:
        if format == 'json':
            with open(filename, 'w') as f:
                json.dump(data, f, indent=4)
        elif format == 'csv':
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Metric", "Value"])
                for k, v in data.items():
                    writer.writerow([k, v])
        print_success(f"Report exported to {filename}")
    except Exception as e:
        print_error(f"Export failed: {e}")

def generate_analytics(github_username, github_token, config, args=None):
    """Advanced Repository Intelligence & Predictive Analytics."""
    print_header("Advanced Analytics & Reporting")
    
    if args and args.repo:
        repo_name = args.repo
    else:
        repo_name = input("Enter repository name: ")

    print_info(f"Analyzing {repo_name}...")
    report_data = {"repo_name": repo_name, "timestamp": datetime.now().isoformat()}

    try:
        # 1. Fetch Core Data
        repo_resp = github_request("GET", f"https://api.github.com/repos/{github_username}/{repo_name}", github_token)
        if repo_resp.status_code != 200:
            print_error(f"Failed to fetch repo data: {repo_resp.status_code}")
            return
        
        repo_data = repo_resp.json()
        stars = repo_data.get('stargazers_count', 0)
        
        # 2. Predictive Growth
        predicted_stars = predict_growth(stars, repo_data['created_at'])
        report_data["current_stars"] = stars
        report_data["predicted_stars_90d"] = predicted_stars

        # 3. Contributor Metrics
        contrib_resp = get_contributors(github_username, repo_name, github_token)
        if contrib_resp.status_code == 200:
            contributors = contrib_resp.json()
            report_data["contributor_count"] = len(contributors)
            
            # Weighted Impact Table
            table = Table(title="Contributor Performance Metrics", box=box.DOUBLE_EDGE)
            table.add_column("User", style="cyan")
            table.add_column("Impact Score", justify="right", style="green")
            
            for c in contributors[:5]:
                # Impact = Contributions * 1.5 (Advanced weighting logic)
                impact_score = int(c['contributions'] * 1.5)
                table.add_row(c['login'], str(impact_score))
            console.print(table)

        # 4. Issue Resolution Analytics
        issue_resp = get_issues(github_username, repo_name, github_token, state='all')
        if issue_resp.status_code == 200:
            issues = issue_resp.json()
            avg_res_hours = calculate_resolution_time(issues)
            report_data["avg_resolution_hours"] = avg_res_hours
            
            res_table = Table(title="Predictive Maintenance", box=box.SIMPLE)
            res_table.add_row("Avg Resolution Time", f"{avg_res_hours} Hours")
            res_table.add_row("Growth Projection (90d)", f"{predicted_stars} Stars")
            console.print(res_table)

        # 5. Dashboard Summary
        print_info(f"\n[bold]Summary for {repo_name}:[/bold]")
        print(f"🌟 Stars: {stars} -> Predicted: {predicted_stars}")
        print(f"⏱️  Avg Fix Time: {avg_res_hours} hrs")

        # 6. Export Prompt
        export = input("\n💾 Export report? (json/csv/n): ").lower()
        if export in ['json', 'csv']:
            export_report(repo_name, report_data, export)

    except Exception as e:
        print_error(f"Analytics engine failure: {e}")
