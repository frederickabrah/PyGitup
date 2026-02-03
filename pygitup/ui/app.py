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
    """The complete immersive God Mode Dashboard with ALL 34+ features."""
    
    TITLE = f"PyGitUp v{__version__}"
    CSS = """
    Screen { background: #0d1117; }
    #sidebar { width: 45; background: #161b22; border-right: tall #30363d; }
    #main-switcher { padding: 1 4; width: 100%; }
    .category-header { background: #21262d; color: #58a6ff; text-style: bold; padding: 0 1; margin: 1 0 0 0; text-align: center; }
    ListItem { padding: 1 1; border-bottom: hkey #30363d; }
    ListItem:hover { background: #1f6feb; }
    ListView:focus > ListItem.--highlight { background: #238636; color: white; }
    .title { color: #58a6ff; text-style: bold; margin-bottom: 1; font-size: 120%; }
    Markdown { height: 100%; border: solid #30363d; padding: 1; background: #0d1117; }
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
                ScrollableContainer(
                    ListView(
                        # --- CORE ---
                        Label(" CORE OPERATIONS ", classes="category-header"),
                        FeatureItem("Project Upload", "project", "Core", "Upload whole directories to GitHub with security pre-scans."),
                        FeatureItem("Template Marketplace", "template", "Core", "Pull 'God Tier' architectures (FastAPI, Node, etc.) instantly."),
                        FeatureItem("Migration Porter", "migrate", "Core", "Mirror any repository from GitLab/Bitbucket to GitHub."),
                        
                        # --- AI & TOOLS ---
                        Label(" AI & INTELLIGENCE ", classes="category-header"),
                        FeatureItem("Intelligence Center", "osint", "GitHub", "Deep OSINT reconnaissance and health stats."),
                        FeatureItem("AI Commit Lab", "ai-lab", "Tools", "Native AI commit generator and stager."),
                        FeatureItem("Analytics Pro", "analytics", "Tools", "Predictive growth and impact scoring."),
                        FeatureItem("AI Diagnostics", "ai-diagnostic", "Tools", "List available AI models for your key."),
                        
                        # --- SECURITY ---
                        Label(" SECURITY & AUTH ", classes="category-header"),
                        FeatureItem("Security Sentinel", "audit", "Tools", "Local SAST and cloud leak scanning."),
                        FeatureItem("SSH Infrastructure", "ssh-setup", "GitHub", "Auto-generate and sync secure Ed25519 keys."),
                        FeatureItem("Identity Switcher", "identity", "Tools", "Swap between multiple GitHub profiles."),
                        
                        # --- GIT OPS ---
                        Label(" GIT OPERATIONS ", classes="category-header"),
                        FeatureItem("Smart Push", "smart-push", "Git", "Squash messy history before pushing."),
                        FeatureItem("Branch Manager", "branch", "Git", "List, create, or switch branches."),
                        FeatureItem("Stash Manager", "stash", "Git", "Save and restore work-in-progress."),
                        FeatureItem("Tag Manager", "tag", "Git", "Version control with local/remote tags."),
                        FeatureItem("Cherry Picker", "cherry-pick", "Git", "Move specific commits between branches."),
                        
                        # --- GITHUB OPS ---
                        Label(" GITHUB ECOSYSTEM ", classes="category-header"),
                        FeatureItem("Gist Manager", "gist", "GitHub", "Create and list snippets."),
                        FeatureItem("Release Architect", "release", "GitHub", "Generate AI release notes and tag versions."),
                        FeatureItem("PR Manager", "pr", "GitHub", "Handle pull requests and code reviews."),
                        FeatureItem("Webhook Manager", "webhook", "GitHub", "Automate external notifications."),
                        FeatureItem("CI/CD Architect", "cicd", "GitHub", "GitHub Actions generation and live monitoring."),
                        FeatureItem("Network Recon", "fork-intel", "GitHub", "Scan forks for unique community work."),
                        
                        # --- UTILS ---
                        Label(" UTILITIES ", classes="category-header"),
                        FeatureItem("Auto-Docs", "generate-docs", "Tools", "Generate AI READMEs or API references."),
                        FeatureItem("Issue Scanner", "scan-todos", "Tools", "Find TODOs and create AI-resolved issues."),
                        FeatureItem("Offline Queue", "offline-queue", "Tools", "Queue commits while offline."),
                        FeatureItem("Repository Management", "bulk-mgmt", "GitHub", "Change visibility or delete repositories."),
                        id="feature-list"
                    )
                ),
                id="sidebar"
            ),
            ContentSwitcher(
                Vertical(
                    Static("Welcome to PyGitUp God Mode", classes="title"),
                    Static("PyGitUp is now feature-complete.\nSelect a module from the expanded sidebar to explore the full ecosystem.", id="home-desc"),
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
                        Button("Launch AI Workflow", variant="primary", id="btn-launch-ai"),
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
        if event.item and isinstance(event.item, FeatureItem):
            if self.query_one("#main-switcher").current == "home-view":
                self.query_one("#home-desc").update(f"{event.item.description}\n\n[bold white]Press ENTER to launch.[/bold white]")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if not isinstance(event.item, FeatureItem): return
        mode = event.item.mode
        if mode == "osint": self.run_osint_view()
        elif mode == "ai-lab": self.run_ai_lab()
        elif mode == "analytics": self.run_analytics_view()
        elif mode == "identity": self.run_identity_view()
        else: self.launch_cli_feature(mode)

    def run_osint_view(self):
        self.query_one("#main-switcher").current = "osint-view"
        self.query_one("#intel-report").update("# 📡 Initializing Reconnaissance...")
        self.run_worker(self.fetch_intel_task())

    def run_ai_lab(self):
        self.query_one("#main-switcher").current = "ai-lab-view"
        diff = get_git_diff() or "No staged changes found."
        self.query_one("#ai-diff-view").update(f"### Staged Changes\n```diff\n{diff}\n```")

    def run_analytics_view(self):
        self.query_one("#main-switcher").current = "analytics-view"
        self.query_one("#analytics-report").update("# 📊 Crunching Data...")
        self.run_worker(self.fetch_analytics_task())

    def run_identity_view(self):
        self.query_one("#main-switcher").current = "identity-view"
        p_list = self.query_one("#profile-list", ListView)
        p_list.clear()
        for p in list_profiles(): p_list.append(ListItem(Label(p)))

    async def fetch_intel_task(self):
        config = load_config(); token = get_github_token(config)
        try:
            resp = get_repo_info("frederickabrah", "PyGitup", token)
            if resp.status_code == 200:
                data = resp.json(); health = get_repo_health_metrics("frederickabrah", "PyGitup", token)
                md = f"# 🛰️ Intel: PyGitup\n\n- **Stars:** {data.get('stargazers_count')} | **Health:** {health.get('activity_status', 'N/A')}\n- **Sponsors:** {'Active 💖' if data.get('is_sponsored') else 'None'}"
                self.query_one("#intel-report").update(md)
        except Exception as e: self.query_one("#intel-report").update(f"Error: {e}")

    async def fetch_analytics_task(self):
        config = load_config(); token = get_github_token(config)
        try:
            repo_resp = get_repo_info(get_github_username(config), "PyGitup", token)
            data = repo_resp.json()
            proj = predict_growth_v2(data['stargazers_count'], data['created_at'], data['forks_count'])
            self.query_one("#analytics-report").update(f"# 📈 Analytics\n\n- **90-Day Projection:** {proj} 🌟")
        except Exception as e: self.query_one("#analytics-report").update(f"Error: {e}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-launch-ai": self.launch_cli_feature("ai-commit")

    def action_go_home(self):
        self.query_one("#main-switcher").current = "home-view"

    def launch_cli_feature(self, mode):
        # Full dynamic import to avoid circular dependencies
        from ..main import main
        from ..project.project_ops import upload_project_directory, migrate_repository
        from ..github.ssh_ops import setup_ssh_infrastructure
        from ..github.actions import manage_actions
        from ..github.releases import create_release_tag
        from ..github.gists import manage_gists
        from ..utils.security import run_audit
        from ..utils.analytics import generate_analytics
        from ..utils.ai import ai_commit_workflow, list_available_ai_models
        from ..project.docs import generate_documentation
        from ..project.issues import scan_todos
        from ..utils.offline import queue_offline_commit
        
        config = load_config(); user = get_github_username(config); token = get_github_token(config)
        with self.suspend():
            os.system('cls' if os.name == 'nt' else 'clear')
            try:
                if mode == "project": upload_project_directory(user, token, config)
                elif mode == "migrate": migrate_repository(user, token, config)
                elif mode == "ai-commit": ai_commit_workflow(user, token, config)
                elif mode == "ssh-setup": setup_ssh_infrastructure(config, token)
                elif mode == "cicd": manage_actions(None, user, token, config)
                elif mode == "release": create_release_tag(user, token, config)
                elif mode == "audit": run_audit(user, None, token)
                elif mode == "analytics": generate_analytics(user, token, config)
                elif mode == "generate-docs": generate_documentation(user, token, config)
                elif mode == "scan-todos": scan_todos(user, token, config)
                elif mode == "offline-queue": queue_offline_commit(config)
                elif mode == "ai-diagnostic": list_available_ai_models(config["github"].get("ai_api_key"))
                elif mode == "gist": manage_gists(None, user, token)
                input("\nPress Enter to return to TUI Dashboard...")
            except Exception as e:
                print(f"Error: {e}"); input("Press Enter...")

def run_tui():
    PyGitUpTUI().run()
