
from rich.console import Console
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
        "Core": ["project", "file", "batch", "template"],
        "Git": ["branch", "stash", "tag", "cherry-pick", "smart-push"],
        "GitHub": ["release", "multi-repo", "request-review", "gist", "webhook", "actions", "pr", "visibility", "delete-repo", "repo-info"],
        "Tools": ["scan-todos", "offline-queue", "process-queue", "generate-docs", "analytics", "audit", "configure"]
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
    """Displays repository info in a rich panel."""
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

    panel = Panel(
        grid,
        title=f"[bold]{data.get('full_name')}[/bold]",
        border_style="green" if not data.get("private") else "red",
        subtitle=data.get("description") or "No description"
    )
    console.print(panel)
