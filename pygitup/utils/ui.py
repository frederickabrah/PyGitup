
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box
from contextlib import contextmanager

console = Console()

def print_success(message):
    """Prints a success message in green."""
    console.print(f"[bold green]✔ {message}[/bold green]")

def print_error(message):
    """Prints an error message in red."""
    console.print(f"[bold red]✖ {message}[/bold red]")

def print_warning(message):
    """Prints a warning message in yellow."""
    console.print(f"[bold yellow]⚠ {message}[/bold yellow]")

def print_info(message):
    """Prints an info message in blue."""
    console.print(f"[bold blue]ℹ {message}[/bold blue]")

def print_header(text):
    """Prints a styled header."""
    console.print(Panel(Text(text, justify="center", style="bold white"), border_style="blue", expand=False))

@contextmanager
def show_spinner(text="Processing..."):
    """Context manager for a loading spinner."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description=text, total=None)
        yield

def display_menu(options):
    """Displays the main menu options in a grid."""
    table = Table(title="[bold blue]PyGitUp Main Menu[/bold blue]", box=box.ROUNDED, show_header=True, header_style="bold cyan")
    table.add_column("ID", justify="center", style="green", no_wrap=True)
    table.add_column("Feature", style="white")
    table.add_column("Category", style="dim")

    categories = {
        "Core": ["project", "file", "batch", "template", "migrate"],
        "Git": ["branch", "stash", "tag", "cherry-pick", "smart-push"],
        "GitHub": ["release", "multi-repo", "request-review", "gist", "webhook", "actions", "pr", "visibility", "delete-repo", "repo-info", "bulk-mgmt", "fork-intel"],
        "Tools": ["scan-todos", "offline-queue", "process-queue", "generate-docs", "analytics", "audit", "configure", "ai-commit"]
    }

    for key, value in options.items():
        # Determine category (naive approach, could be passed in)
        cat = "Misc"
        mode_guess = value[1] # Assuming value is tuple (desc, mode)
        
        for c_name, c_items in categories.items():
            if mode_guess in c_items:
                cat = c_name
                break
        
        table.add_row(key, value[0], cat)

    console.print(table)

def display_repo_info(data):
    """Displays repository info in a rich panel with traffic analytics."""
    grid = Table.grid(expand=True)
    grid.add_column(justify="left", style="cyan", no_wrap=True)
    grid.add_column(justify="left", style="white")

    fields = {
        "Name": data.get("name"),
        "Owner": data.get("owner", {}).get("login"),
        "Visibility": "Private" if data.get("private") else "Public",
        "Language": data.get("language"),
        "Stars": str(data.get("stargazers_count")),
        "Forks": str(data.get("forks_count")),
        "Issues": f"{data.get('open_issues_count')} open",
        "Created": data.get("created_at"),
        "Clone URL": data.get("clone_url")
    }

    for label, value in fields.items():
        grid.add_row(f"{label}:", str(value))

    # OSINT: Languages Section
    if 'osint_languages' in data and data['osint_languages']:
        langs = data['osint_languages']
        total_bytes = sum(langs.values())
        lang_str = ""
        for name, bytes_count in sorted(langs.items(), key=lambda x: x[1], reverse=True)[:5]:
            percentage = (bytes_count / total_bytes) * 100
            lang_str += f"{name} ({percentage:.1f}%) "
        grid.add_row("Languages:", lang_str.strip())

    # OSINT: Community Profile
    if 'osint_community' in data and data['osint_community']:
        comm = data['osint_community']
        grid.add_row("", "")
        grid.add_row("[bold]Community Intelligence[/bold]", f"Health Score: [bold green]{comm.get('health_percentage')}%[/bold green]")
        
        files = comm.get('files', {})
        readme = "✅" if files.get('readme') else "❌"
        license = "✅" if files.get('license') else "❌"
        coc = "✅" if files.get('code_of_conduct') else "❌"
        grid.add_row("Documentation:", f"README: {readme} | LICENSE: {license} | CoC: {coc}")

    # OSINT: Release Summary
    if 'osint_release' in data and data['osint_release']:
        rel = data['osint_release']
        grid.add_row("", "")
        grid.add_row("[bold]Latest Intelligence[/bold]", "")
        grid.add_row("Version:", f"{rel.get('tag_name')} ({rel.get('name')})")
        grid.add_row("Released:", rel.get('published_at', '')[:10])

    # Health & Activity Section
    if 'health' in data and data['health']:
        health = data['health']
        grid.add_row("", "")
        grid.add_row("[bold]Health & Activity[/bold]", "")
        
        if 'development_velocity_days' in health:
            grid.add_row("Dev Velocity (Median):", f"{health['development_velocity_days']} days/commit")
        
        if 'activity_status' in health:
            status_color = "green" if health['activity_status'] == "Active/Bursting" else "white"
            grid.add_row("Activity Status:", f"[{status_color}]{health['activity_status']}[/{status_color}]")
            
        if 'closed_issues' in health:
            grid.add_row("Closed Issues:", str(health['closed_issues']))
            
        if 'contributors_count' in health:
            grid.add_row("Total Contributors:", str(health['contributors_count']))

    # Traffic analytics section if available
    if 'traffic' in data and data['traffic']:
        traffic = data['traffic']
        grid.add_row("", "") # Spacer
        grid.add_row("[bold]Traffic Analytics (Admin Only)[/bold]", "")

        if 'clones' in traffic and traffic['clones'].get('clones'):
            # Safely get the last element or use defaults
            clones_list = traffic['clones']['clones']
            if clones_list:
                latest_clones = clones_list[-1]
                grid.add_row("Clones (Last recorded):", f"{latest_clones['count']} ({latest_clones['uniques']} unique)")

        if 'views' in traffic and traffic['views'].get('views'):
            views_list = traffic['views']['views']
            if views_list:
                latest_views = views_list[-1]
                grid.add_row("Views (Last recorded):", f"{latest_views['count']} ({latest_views['uniques']} unique)")

        if 'referrers' in traffic and traffic['referrers']:
            referrer_table = Table(title="Top Referrers", box=box.SIMPLE)
            referrer_table.add_column("Referrer", style="cyan")
            referrer_table.add_column("Visits", style="green")
            referrer_table.add_column("Unique", style="yellow")

            for referrer in traffic['referrers'][:5]:
                referrer_table.add_row(
                    referrer['referrer'],
                    str(referrer['count']),
                    str(referrer['uniques'])
                )
            
            grid.add_row("", "")
            grid.add_row("Traffic Sources:", referrer_table)

    panel = Panel(
        grid,
        title=f"[bold]{data.get('full_name')}[/bold]",
        border_style="green" if not data.get("private") else "red",
        subtitle=data.get("description") or "No description"
    )
    console.print(panel)

def display_traffic_trends(traffic_data):
    """Display traffic trends in a tabular format."""
    if not traffic_data:
        return

    groups = []

    if 'clones' in traffic_data and traffic_data['clones'].get('clones'):
        clones_table = Table(title="Clone Trends (Last 14 Days)", box=box.MINIMAL)
        clones_table.add_column("Date", style="cyan")
        clones_table.add_column("Clones", style="green")
        clones_table.add_column("Unique", style="yellow")

        for clone_data in traffic_data['clones']['clones']:
            clones_table.add_row(
                clone_data['timestamp'][:10],
                str(clone_data['count']),
                str(clone_data['uniques'])
            )
        groups.append(clones_table)

    if 'views' in traffic_data and traffic_data['views'].get('views'):
        views_table = Table(title="View Trends (Last 14 Days)", box=box.MINIMAL)
        views_table.add_column("Date", style="cyan")
        views_table.add_column("Views", style="green")
        views_table.add_column("Unique", style="yellow")

        for view_data in traffic_data['views']['views']:
            views_table.add_row(
                view_data['timestamp'][:10],
                str(view_data['count']),
                str(view_data['uniques'])
            )
        groups.append(views_table)

    if groups:
        console.print(Group(*groups))
