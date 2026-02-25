import json
import csv
import os
import math
from datetime import datetime, timedelta
from ..github.api import get_contributors, get_issues, github_request, get_pull_requests
from .ui import print_success, print_error, print_info, print_header, Table, box, console

def calculate_health_score(stars, forks, open_issues, closed_issues):
    """Calculates a 0-100 health score based on engagement and maintenance."""
    if stars == 0: return 50 # Baseline
    
    # 1. Maintenance Ratio (Issues closed vs total)
    total_issues = open_issues + closed_issues
    maintenance_factor = (closed_issues / total_issues * 40) if total_issues > 0 else 20
    
    # 2. Engagement Factor (Forks to Stars ratio)
    # Higher fork-to-star ratio usually means a more 'useful' tool
    engagement_factor = min((forks / (stars + 1)) * 100, 40)
    
    # 3. Popularity Bonus
    popularity_factor = min(math.log10(stars + 1) * 10, 20)
    
    score = int(maintenance_factor + engagement_factor + popularity_factor + 10)
    return max(0, min(100, score))

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

def predict_growth_v2(current_stars, created_at_str, forks, health_score=None):
    """
    Growth prediction factoring in velocity, maintenance health, and momentum.
    """
    try:
        created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
        days_old = (datetime.now(created_at.tzinfo) - created_at).days
        if days_old <= 0: return current_stars
        
        # 1. Historical Velocity (Stars per day)
        base_rate = current_stars / days_old
        
        # 2. Viral/Utility Factor (Fork density)
        # High forks usually correlate with future star growth
        fork_momentum = 1 + (forks / (current_stars + 1))
        
        # 3. Maintenance Multiplier (Health drag)
        # If health_score is low, growth is often stifled by bugs/unresponsiveness
        health_multiplier = 1.0
        if health_score:
            health_multiplier = 0.5 + (health_score / 100) # Range 0.5 - 1.5
        
        # 4. Acceleration (The 'Network Effect')
        # We assume growth accelerates if the project is already gaining traction
        acceleration = 1.2 if base_rate > 0.5 else 1.05
        
        # Calculation: Current + (Anticipated Daily Rate * 90 Days)
        projected_daily = base_rate * fork_momentum * health_multiplier * acceleration
        prediction_90_days = int(current_stars + (projected_daily * 90))
        
        return max(current_stars, prediction_90_days)
    except Exception:
        return current_stars

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
    """Repository Intelligence & Predictive Analytics."""
    print_header("Analytics & Reporting")
    
    if args and args.repo:
        repo_name = args.repo
    else:
        repo_name = input("Enter repository name: ")

    print_info(f"Analyzing data for {repo_name}...")
    report_data = {"repo_name": repo_name, "timestamp": datetime.now().isoformat()}

    try:
        # 1. Fetch Comprehensive Data
        repo_resp = github_request("GET", f"https://api.github.com/repos/{github_username}/{repo_name}", github_token)
        if repo_resp.status_code != 200:
            print_error(f"Access denied: {repo_resp.status_code}")
            return
        
        repo_data = repo_resp.json()
        stars = repo_data.get('stargazers_count', 0)
        forks = repo_data.get('forks_count', 0)
        open_issues_count = repo_data.get('open_issues_count', 0)

        # 2. Issue Lifecycle Analysis
        issue_resp = get_issues(github_username, repo_name, github_token, state='all')
        issues = issue_resp.json() if issue_resp.status_code == 200 else []
        closed_issues_count = len([i for i in issues if i['state'] == 'closed'])
        avg_res_hours = calculate_resolution_time(issues)

        # 3. Intelligence Modeling (v2)
        health_score = calculate_health_score(stars, forks, open_issues_count, closed_issues_count)
        predicted_stars = predict_growth_v2(stars, repo_data['created_at'], forks, health_score=health_score)
        
        # 4. Contributor Impact Analysis
        contrib_resp = get_contributors(github_username, repo_name, github_token)
        contributors = contrib_resp.json() if contrib_resp.status_code == 200 else []
        
        # UI Display: Contributor Metrics
        table = Table(title="Contributor Impact Index", box=box.HEAVY_EDGE, header_style="bold magenta")
        table.add_column("Engineer", style="cyan")
        table.add_column("Impact Score", justify="right", style="green")
        table.add_column("Status", justify="center")

        for c in contributors[:5]:
            # Impact = Contributions + (Weighted activity)
            impact = int(c['contributions'] * 1.8)
            status = "🏆 Lead" if impact > 100 else "🛠️ Active" if impact > 50 else "🌱 Contrib"
            table.add_row(c['login'], str(impact), status)
        
        console.print(table)

        # UI Display: Predictive Maintenance
        res_table = Table(title="Intelligence & Projections", box=box.ROUNDED)
        res_table.add_column("Metric", style="white")
        res_table.add_column("Value", style="bold yellow")
        
        res_table.add_row("Repository Health Score", f"{health_score}/100")
        res_table.add_row("Avg Issue Resolution", f"{avg_res_hours} hrs")
        res_table.add_row("90-Day Star Projection", f"{predicted_stars} 🌟")
        res_table.add_row("Open/Closed Issue Ratio", f"{open_issues_count}/{closed_issues_count}")
        
        console.print(res_table)

        # Final Summary Intelligence
        health_color = "green" if health_score > 70 else "yellow" if health_score > 40 else "red"
        print_info(f"\n[bold]Intelligence Summary:[/bold]")
        console.print(f"Overall Health: [{health_color}]{health_score}%[/{health_color}]")
        console.print(f"Projected Growth: {stars} ➜ {predicted_stars} Stars")

        # Update Report Data
        report_data.update({
            "health_score": health_score,
            "avg_resolution_hours": avg_res_hours,
            "predicted_stars": predicted_stars,
            "stars": stars,
            "forks": forks
        })

        # Export Prompt
        export = input("\n💾 Export detailed report? (json/csv/n): ").lower()
        if export in ['json', 'csv']:
            export_report(repo_name, report_data, export)

    except Exception as e:
        print_error(f"Intelligence Engine failure: {e}")