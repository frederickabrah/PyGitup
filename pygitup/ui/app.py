
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, Static, ListItem, ListView, Label, Markdown, ContentSwitcher
from textual.binding import Binding
from .. import __version__
from ..core.config import load_config, get_github_username, get_github_token, get_active_profile_path
from ..github.repo_info import get_repo_info, get_repo_health_metrics
import os

class FeatureItem(ListItem):
    """A selectable feature item in the sidebar."""
    def __init__(self, name: str, mode: str, category: str, description: str):
        super().__init__()
        self.feature_name = name
        self.mode = mode
        self.category = category
        self.description = description

    def compose(self) -> ComposeResult:
        yield Label(f" {self.feature_name} [dim]({self.category})[/dim]")

class PyGitUpTUI(App):
    """The main immersive TUI Dashboard."""
    
    TITLE = f"PyGitUp v{__version__}"
    CSS = """
    Screen { background: #0d1117; }
    #sidebar { width: 40; background: #161b22; border-right: tall #30363d; }
    #main-switcher { padding: 1 4; width: 100%; }
    .category-header { background: #21262d; color: #58a6ff; text-style: bold; padding: 0 1; margin: 1 0 0 0; text-align: center; }
    ListItem { padding: 1 1; border-bottom: hkey #30363d; }
    ListItem:hover { background: #1f6feb; }
    ListView:focus > ListItem.--highlight { background: #238636; color: white; }
    .title { color: #58a6ff; text-style: bold; margin-bottom: 1; }
    #intel-report { height: 100%; border: solid #30363d; padding: 1; }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("escape", "go_home", "Home", show=True),
    ]

    def compose(self) -> ComposeResult:
        active_profile = os.path.basename(get_active_profile_path()).replace(".yaml", "")
        yield Header(show_clock=True)
        yield Horizontal(
            Vertical(
                Label(f" PROFILE: {active_profile} ", classes="category-header"),
                ListView(
                    FeatureItem("Intelligence Center", "osint", "GitHub", "Deep OSINT reconnaissance and health stats."),
                    FeatureItem("Project Upload", "project", "Core", "Upload whole directories to GitHub."),
                    FeatureItem("Template Marketplace", "template", "Core", "Pull 'God Tier' architectures instantly."),
                    FeatureItem("AI Semantic Commit", "ai-commit", "Tools", "Gemini-powered professional commits."),
                    FeatureItem("Security Sentinel", "audit", "Tools", "Local SAST and cloud leak scanning."),
                    FeatureItem("Analytics Dashboard", "analytics", "Tools", "Predictive growth and impact scoring."),
                    FeatureItem("Infrastructure (SSH)", "ssh", "Tools", "Automated SSH key management."),
                    id="feature-list"
                ),
                id="sidebar"
            ),
            ContentSwitcher(
                Vertical(
                    Static("Welcome to PyGitUp God Mode", classes="title"),
                    Static("Select a module from the left to explore the immersive dashboard.\n\n[bold cyan]PyGitUp[/bold cyan] is officially reactive.", id="home-desc"),
                    id="home-view"
                ),
                Vertical(
                    Static("📡 Real-Time Intelligence Report", classes="title"),
                    Markdown("", id="intel-report"),
                    id="osint-view"
                ),
                id="main-switcher",
                initial="home-view"
            )
        )
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#feature-list").focus()

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Updates the home view description when navigating."""
        if event.item and self.query_one("#main-switcher").current == "home-view":
            self.query_one("#home-desc").update(f"{event.item.description}\n\n[bold white]Press ENTER to launch.[/bold white]")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        mode = event.item.mode
        if mode == "osint":
            self.run_osint_view()
        else:
            self.launch_cli_feature(mode)

    def run_osint_view(self):
        """Switches to native TUI intelligence view."""
        self.query_one("#main-switcher").current = "osint-view"
        self.query_one("#intel-report").update("# 📡 Initializing Reconnaissance...")
        self.run_worker(self.fetch_intel_task())

    async def fetch_intel_task(self):
        """Background task to fetch data without freezing UI."""
        config = load_config()
        token = get_github_token(config)
        owner, repo = "frederickabrah", "PyGitup"
        
        try:
            resp = get_repo_info(owner, repo, token)
            if resp.status_code == 200:
                data = resp.json()
                health = get_repo_health_metrics(owner, repo, token)
                
                md = f"# 🛰️ Intelligence: {owner}/{repo}\n\n"
                md += f"| Metric | Value |\n| --- | --- |\n"
                md += f"| ⭐ Stars | {data.get('stargazers_count')} |\n"
                md += f"| 🍴 Forks | {data.get('forks_count')} |\n"
                md += f"| 🌐 Language | {data.get('language')} |\n"
                md += f"| 🚑 Health | {health.get('activity_status', 'N/A')} |\n"
                md += f"| 🏃 Velocity | {health.get('development_velocity_days', 'N/A')} days/commit |\n\n"
                md += "### Core Description\n"
                md += f"*{data.get('description')}*"
                
                self.query_one("#intel-report").update(md)
        except Exception as e:
            self.query_one("#intel-report").update(f"## ❌ Reconnaissance Failed\nError: {e}")

    def action_go_home(self):
        self.query_one("#main-switcher").current = "home-view"

    def action_refresh(self) -> None:
        if self.query_one("#main-switcher").current == "osint-view":
            self.run_osint_view()
        else:
            self.notify("System Status: Online 🟢")

    def launch_cli_feature(self, mode):
        """Handles legacy CLI features by suspending the TUI."""
        from ..project.project_ops import upload_project_directory
        from ..project.templates import create_project_from_template
        from ..utils.ai import ai_commit_workflow
        from ..github.ssh_ops import setup_ssh_infrastructure
        from ..utils.security import run_audit
        from ..utils.analytics import generate_analytics
        
        config = load_config()
        user = get_github_username(config)
        token = get_github_token(config)

        with self.suspend():
            os.system('cls' if os.name == 'nt' else 'clear')
            try:
                if mode == "project": upload_project_directory(user, token, config)
                elif mode == "template": create_project_from_template(user, token, config)
                elif mode == "ai-commit": ai_commit_workflow(user, token, config)
                elif mode == "ssh": setup_ssh_infrastructure(config, token)
                elif mode == "audit": run_audit(user, None, token)
                elif mode == "analytics": generate_analytics(user, token, config)
                
                input("\nPress Enter to return to TUI Dashboard...")
            except Exception as e:
                print(f"\nError: {e}")
                input("Press Enter to continue...")

def run_tui():
    app = PyGitUpTUI()
    app.run()
