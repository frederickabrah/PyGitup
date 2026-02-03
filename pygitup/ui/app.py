from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, Static, ListItem, ListView, Label, Markdown, ContentSwitcher, Button
from textual.binding import Binding
from .. import __version__
from ..core.config import load_config, get_github_username, get_github_token, get_active_profile_path, list_profiles, set_active_profile
from ..github.repo_info import get_repo_info, get_repo_health_metrics
from ..utils.ai import get_git_diff, generate_ai_commit_message
from ..utils.analytics import calculate_health_score, predict_growth_v2
import os
import subprocess

class FeatureItem(ListItem):
    def __init__(self, name: str, mode: str, category: str, description: str):
        super().__init__()
        self.feature_name = name
        self.mode = mode
        self.category = category
        self.description = description

    def compose(self) -> ComposeResult:
        yield Label(f" {self.feature_name} [dim]({self.category})[/dim]")

class PyGitUpTUI(App):
    """The complete immersive God Mode Dashboard."""
    
    TITLE = f"PyGitUp v{__version__}"
    CSS = """
    Screen { background: #0d1117; }
    #sidebar { width: 40; background: #161b22; border-right: tall #30363d; }
    #main-switcher { padding: 1 4; width: 100%; }
    .category-header { background: #21262d; color: #58a6ff; text-style: bold; padding: 0 1; margin: 1 0 0 0; text-align: center; }
    ListItem { padding: 1 1; border-bottom: hkey #30363d; }
    ListItem:hover { background: #1f6feb; }
    ListView:focus > ListItem.--highlight { background: #238636; color: white; }
    .title { color: #58a6ff; text-style: bold; margin-bottom: 1; font-size: 120%; }
    Markdown { height: 100%; border: solid #30363d; padding: 1; background: #0d1117; }
    .btn-row { margin-top: 1; }
    Button { margin-right: 2; }
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
                Label(f" PROFILE: {active_profile} ", classes="category-header", id="profile-label"),
                ListView(
                    FeatureItem("Intelligence Hub", "osint", "GitHub", "Live reconnaissance and repo health."),
                    FeatureItem("AI Commit Lab", "ai-lab", "Tools", "Native AI commit generator and stager."),
                    FeatureItem("Analytics Pro", "analytics", "Tools", "Predictive growth and impact scoring."),
                    FeatureItem("Identity Vault", "identity", "Tools", "Manage and swap stealth profiles."),
                    FeatureItem("Project Upload", "project", "Core", "Upload whole directories to GitHub."),
                    FeatureItem("Infrastructure (SSH)", "ssh", "Tools", "Automated SSH setup."),
                    id="feature-list"
                ),
                id="sidebar"
            ),
            ContentSwitcher(
                Vertical(
                    Static("Welcome to PyGitUp God Mode", classes="title"),
                    Static("Select a module from the left to explore the immersive dashboard.", id="home-desc"),
                    id="home-view"
                ),
                Vertical(
                    Static("📡 Real-Time Intelligence Report", classes="title"),
                    Markdown("", id="intel-report"),
                    id="osint-view"
                ),
                Vertical(
                    Static("🧠 AI Semantic Commit Lab", classes="title"),
                    Markdown("", id="ai-diff-view"),
                    Horizontal(
                        Button("Generate Message", variant="primary", id="btn-gen-ai"),
                        Button("Commit Changes", variant="success", id="btn-commit"),
                        classes="btn-row"
                    ),
                    id="ai-lab-view"
                ),
                Vertical(
                    Static("📊 Advanced Analytics Dashboard", classes="title"),
                    Markdown("", id="analytics-report"),
                    id="analytics-view"
                ),
                Vertical(
                    Static("🔐 Identity Vault", classes="title"),
                    Static("Select a profile to activate:", id="identity-desc"),
                    ListView(id="profile-list"),
                    id="identity-view"
                ),
                id="main-switcher",
                initial="home-view"
            )
        )
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#feature-list").focus()

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.item and self.query_one("#main-switcher").current == "home-view":
            self.query_one("#home-desc").update(f"{event.item.description}\n\n[bold white]Press ENTER to launch.[/bold white]")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        mode = event.item.mode
        if mode == "osint": self.run_osint_view()
        elif mode == "ai-lab": self.run_ai_lab()
        elif mode == "analytics": self.run_analytics_view()
        elif mode == "identity": self.run_identity_view()
        else: self.launch_cli_feature(mode)

    # --- NATIVE VIEWS ---

    def run_osint_view(self):
        self.query_one("#main-switcher").current = "osint-view"
        self.query_one("#intel-report").update("# 📡 Initializing Reconnaissance...")
        self.run_worker(self.fetch_intel_task())

    def run_ai_lab(self):
        self.query_one("#main-switcher").current = "ai-lab-view"
        diff = get_git_diff() or "No staged changes found. Use CLI to stage files."
        self.query_one("#ai-diff-view").update(f"### Staged Changes\n```diff\n{diff}\n```")

    def run_analytics_view(self):
        self.query_one("#main-switcher").current = "analytics-view"
        self.query_one("#analytics-report").update("# 📊 Crunching Projections...")
        self.run_worker(self.fetch_analytics_task())

    def run_identity_view(self):
        self.query_one("#main-switcher").current = "identity-view"
        p_list = self.query_one("#profile-list", ListView)
        p_list.clear()
        for p in list_profiles():
            p_list.append(ListItem(Label(p)))

    # --- WORKERS ---

    async def fetch_intel_task(self):
        config = load_config(); token = get_github_token(config)
        owner, repo = "frederickabrah", "PyGitup"
        try:
            resp = get_repo_info(owner, repo, token)
            if resp.status_code == 200:
                data = resp.json(); health = get_repo_health_metrics(owner, repo, token)
                md = f"# 🛰️ Intelligence: {owner}/{repo}\n\n| Metric | Value |\n| --- | --- |\n| ⭐ Stars | {data.get('stargazers_count')} |\n| 🍴 Forks | {data.get('forks_count')} |\n| 🌐 Language | {data.get('language')} |\n| 🚑 Health | {health.get('activity_status', 'N/A')} |"
                self.query_one("#intel-report").update(md)
        except Exception as e: self.query_one("#intel-report").update(f"Error: {e}")

    async def fetch_analytics_task(self):
        config = load_config(); token = get_github_token(config); owner = get_github_username(config)
        repo = "PyGitup"
        try:
            repo_resp = get_repo_info(owner, repo, token)
            data = repo_resp.json()
            proj = predict_growth_v2(data['stargazers_count'], data['created_at'], data['forks_count'])
            md = f"# 📈 Analytics: {repo}\n\n### Projections\n- **90-Day Star Goal:** {proj} 🌟\n- **Current Velocity:** Healthy\n\n### Impact\nMaintenance is active."
            self.query_one("#analytics-report").update(md)
        except Exception as e: self.query_one("#analytics-report").update(f"Error: {e}")

    def action_go_home(self): self.query_one("#main-switcher").current = "home-view"

    def launch_cli_feature(self, mode):
        config = load_config(); user = get_github_username(config); token = get_github_token(config)
        with self.suspend():
            os.system('cls' if os.name == 'nt' else 'clear')
            if mode == "project": upload_project_directory(user, token, config)
            elif mode == "ssh": setup_ssh_infrastructure(config, token)
            input("\nPress Enter to return to TUI Dashboard...")

def run_tui():
    PyGitUpTUI().run()