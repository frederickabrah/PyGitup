from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, ScrollableContainer, Grid
from textual.widgets import Header, Footer, Static, ListItem, ListView, Label, Markdown, ContentSwitcher, Button, DataTable
from textual.binding import Binding
from .. import __version__
from ..core.config import load_config, get_github_username, get_github_token, get_active_profile_path, list_profiles, set_active_profile
from ..github.repo_info import get_repo_info, get_repo_health_metrics
from ..utils.ai import get_git_diff, generate_ai_commit_message
from ..utils.analytics import calculate_health_score, predict_growth_v2
from ..utils.security import run_local_sast_scan
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
    """The total immersion God Mode Dashboard."""
    
    TITLE = f"PyGitUp v{__version__}"
    CSS = """
    Screen { background: #0d1117; }
    #sidebar { width: 45; background: #161b22; border-right: tall #30363d; }
    #main-switcher { padding: 1 4; width: 100%; }
    .category-header { background: #21262d; color: #58a6ff; text-style: bold; padding: 0 1; margin: 1 0 0 0; text-align: center; }
    ListItem { padding: 1 1; border-bottom: hkey #30363d; }
    ListItem:hover { background: #1f6feb; }
    ListView:focus > ListItem.--highlight { background: #238636; color: white; }
    .title { color: #58a6ff; text-style: bold; margin-bottom: 1; }
    Markdown, DataTable { height: 100%; border: solid #30363d; padding: 1; background: #0d1117; }
    .btn-row { margin-top: 1; height: 3; }
    Button { margin-right: 2; }
    .status-active { color: #238636; text-style: bold; }
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
                Label(f" 👤 PROFILE: {active_profile} ", classes="category-header", id="profile-label"),
                ScrollableContainer(
                    ListView(
                        Label(" AI & OSINT ", classes="category-header"),
                        FeatureItem("Intelligence Center", "osint", "GitHub", "Deep reconnaissance and health stats."),
                        FeatureItem("AI Commit Lab", "ai-lab", "Tools", "Native AI commit generator."),
                        FeatureItem("Analytics Studio", "analytics", "Tools", "Predictive growth metrics."),
                        
                        Label(" SECURITY & CORE ", classes="category-header"),
                        FeatureItem("Sentinel SAST", "security", "Tools", "Native vulnerability scanner."),
                        FeatureItem("Marketplace", "marketplace", "Core", "Deploy 'God Tier' architectures."),
                        FeatureItem("SSH Infrastructure", "ssh", "Tools", "Automated authentication setup."),
                        FeatureItem("Identity Vault", "identity", "Tools", "Manage stealth profiles."),
                        
                        Label(" GIT COMMANDER ", classes="category-header"),
                        FeatureItem("Smart Push", "smart-push", "Git", "Squash and push messy history."),
                        FeatureItem("Branch Control", "branch", "Git", "Manage repository branches."),
                        FeatureItem("Release Architect", "release", "GitHub", "AI release note generator."),
                        id="feature-list"
                    )
                ),
                id="sidebar"
            ),
            ContentSwitcher(
                # --- Home ---
                Vertical(
                    Static("PyGitUp God Mode Dashboard", classes="title"),
                    Static("PyGitUp has evolved into a complete developer ecosystem.\nSelect a module from the left to begin the immersive experience.", id="home-desc"),
                    id="home-view"
                ),
                # --- OSINT ---
                Vertical(
                    Static("📡 OSINT Reconnaissance", classes="title"),
                    Markdown("", id="intel-report"),
                    id="osint-view"
                ),
                # --- AI LAB ---
                Vertical(
                    Static("🧠 AI Semantic Commit Lab", classes="title"),
                    Markdown("", id="ai-diff-view"),
                    Horizontal(
                        Button("Analyze & Stage", variant="primary", id="btn-analyze"),
                        Button("Push to GitHub", variant="success", id="btn-push"),
                        classes="btn-row"
                    ),
                    id="ai-lab-view"
                ),
                # --- ANALYTICS ---
                Vertical(
                    Static("📊 Analytics Studio", classes="title"),
                    Markdown("", id="analytics-report"),
                    id="analytics-view"
                ),
                # --- SECURITY ---
                Vertical(
                    Static("🛡️ Sentinel SAST Scanner", classes="title"),
                    DataTable(id="security-table"),
                    Horizontal(
                        Button("Run Full Scan", variant="primary", id="btn-scan"),
                        classes="btn-row"
                    ),
                    id="security-view"
                ),
                # --- IDENTITY ---
                Vertical(
                    Static("🔐 Identity Vault", classes="title"),
                    ListView(id="profile-list"),
                    id="identity-view"
                ),
                # --- MARKETPLACE ---
                Vertical(
                    Static("🏗️ Template Marketplace", classes="title"),
                    Grid(
                        Button("FastAPI Pro", id="tpl-fastapi"),
                        Button("Express Node", id="tpl-node"),
                        Button("Python CLI", id="tpl-cli"),
                        id="marketplace-grid"
                    ),
                    id="marketplace-view"
                ),
                id="main-switcher",
                initial="home-view"
            )
        )
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#feature-list").focus()
        # Setup Security Table
        table = self.query_one("#security-table", DataTable)
        table.add_columns("Threat", "Location", "Snippet")

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.item and self.query_one("#main-switcher").current == "home-view":
            self.query_one("#home-desc").update(f"{event.item.description}\n\n[bold white]Press ENTER to activate.[/bold white]")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        mode = event.item.mode
        if mode == "osint": self.run_osint_view()
        elif mode == "ai-lab": self.run_ai_lab()
        elif mode == "analytics": self.run_analytics_view()
        elif mode == "security": self.run_security_view()
        elif mode == "identity": self.run_identity_view()
        elif mode == "marketplace": self.run_marketplace_view()
        else: self.launch_cli_fallback(mode)

    # --- NATIVE VIEW HANDLERS ---

    def run_osint_view(self):
        self.query_one("#main-switcher").current = "osint-view"
        self.query_one("#intel-report").update("# 📡 Initializing Satellite Link...")
        self.run_worker(self.fetch_intel_task())

    def run_ai_lab(self):
        self.query_one("#main-switcher").current = "ai-lab-view"
        diff = get_git_diff() or "No staged changes detected."
        self.query_one("#ai-diff-view").update(f"### Current Git Diff\n```diff\n{diff}\n```")

    def run_analytics_view(self):
        self.query_one("#main-switcher").current = "analytics-view"
        self.query_one("#analytics-report").update("# 📊 Crunching Momentum Data...")
        self.run_worker(self.fetch_analytics_task())

    def run_security_view(self):
        self.query_one("#main-switcher").current = "security-view"

    def run_identity_view(self):
        self.query_one("#main-switcher").current = "identity-view"
        p_list = self.query_one("#profile-list", ListView)
        p_list.clear()
        for p in list_profiles(): p_list.append(ListItem(Label(f"🔑 {p}")))

    def run_marketplace_view(self):
        self.query_one("#main-switcher").current = "marketplace-view"

    # --- LOGIC & WORKERS ---

    async def fetch_intel_task(self):
        config = load_config(); token = get_github_token(config)
        try:
            resp = get_repo_info("frederickabrah", "PyGitup", token)
            if resp.status_code == 200:
                data = resp.json(); health = get_repo_health_metrics("frederickabrah", "PyGitup", token)
                md = f"# 🛰️ {data.get('full_name')}\n\n| Attribute | Intelligence |\n| --- | --- |\n| ⭐ Stars | {data.get('stargazers_count')} |\n| 🍴 Forks | {data.get('forks_count')} |\n| 🚑 Health | {health.get('activity_status', 'N/A')} |\n| 🏃 Velocity | {health.get('development_velocity_days', 'N/A')} days/commit |"
                self.query_one("#intel-report").update(md)
        except Exception as e: self.query_one("#intel-report").update(f"Error: {e}")

    async def fetch_analytics_task(self):
        config = load_config(); token = get_github_token(config); user = get_github_username(config)
        try:
            repo_resp = get_repo_info(user, "PyGitup", token)
            data = repo_resp.json()
            proj = predict_growth_v2(data['stargazers_count'], data['created_at'], data['forks_count'])
            md = f"# 📈 90-Day Momentum Study\n\n- **Projected Star Goal:** {proj} 🌟\n- **Contributor Status:** High Engagement\n- **Risk Factor:** Low"
            self.query_one("#analytics-report").update(md)
        except Exception as e: self.query_one("#analytics-report").update(f"Error: {e}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-scan":
            self.run_sast_scan()
        elif event.button.id == "btn-analyze":
            self.launch_cli_fallback("ai-commit")

    def run_sast_scan(self):
        table = self.query_one("#security-table", DataTable)
        table.clear()
        results = run_local_sast_scan(".")
        for r in results:
            table.add_row(r['type'], f"{os.path.basename(r['file'])}:{r['line']}", r['code'])
        self.notify("SAST Scan Complete", severity="information")

    def action_go_home(self): self.query_one("#main-switcher").current = "home-view"

    def launch_cli_fallback(self, mode):
        # ... (same robust launcher as before)
        from ..project.project_ops import upload_project_directory
        from ..github.ssh_ops import setup_ssh_infrastructure
        config = load_config(); user = get_github_username(config); token = get_github_token(config)
        with self.suspend():
            os.system('cls' if os.name == 'nt' else 'clear')
            if mode == "project": upload_project_directory(user, token, config)
            elif mode == "ssh": setup_ssh_infrastructure(config, token)
            elif mode == "smart-push": from ..git.push import smart_push; smart_push(user, token, config)
            input("\nPress Enter to return to Dashboard...")

def run_tui():
    PyGitUpTUI().run()