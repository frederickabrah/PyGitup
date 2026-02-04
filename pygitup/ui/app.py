from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, ScrollableContainer, Grid
from textual.widgets import Header, Footer, Static, ListItem, ListView, Label, Markdown, ContentSwitcher, Button, DataTable, Input
from textual.binding import Binding
from .. import __version__
from ..core.config import load_config, get_github_username, get_github_token, get_active_profile_path, list_profiles, set_active_profile
from ..github.repo_info import get_repo_info, get_repo_health_metrics
from ..utils.ai import get_git_diff, generate_ai_commit_message, code_mentor_chat
from ..utils.analytics import calculate_health_score, predict_growth_v2
from ..utils.security import run_local_sast_scan
import os
import requests

class FeatureItem(ListItem):
    def __init__(self, name: str, mode: str, category: str, description: str):
        super().__init__()
        self.feature_name = name
        self.mode = mode
        self.category = category
        self.description = description

    def compose(self) -> ComposeResult:
        yield Label(f" {self.feature_name} [dim]({self.category})[/dim]")

class HeaderItem(ListItem):
    def __init__(self, text: str):
        super().__init__(disabled=True)
        self.text = text
    def compose(self) -> ComposeResult:
        yield Label(f" {self.text} ", classes="category-header")

class PyGitUpTUI(App):
    """The immersive God Mode Dashboard with AI Code Mentor."""
    
    TITLE = f"PyGitUp v{__version__}"
    CSS = """
    Screen { background: #0d1117; }
    #sidebar { width: 45; background: #161b22; border-right: tall #30363d; }
    #main-switcher { padding: 1 4; width: 100%; }
    .category-header { background: #21262d; color: #58a6ff; text-style: bold; width: 100%; text-align: center; }
    ListItem { padding: 1 1; border-bottom: hkey #30363d; }
    ListItem:hover { background: #1f6feb; }
    ListView:focus > ListItem.--highlight { background: #238636; color: white; }
    .title { color: #58a6ff; text-style: bold; margin-bottom: 1; }
    Markdown, DataTable { height: 100%; border: solid #30363d; padding: 1; background: #0d1117; }
    #chat-input { margin-top: 1; border: solid #30363d; }
    .btn-row { margin-top: 1; height: 3; }
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
                Label(f" 👤 PROFILE: {active_profile} ", classes="category-header"),
                ScrollableContainer(
                    ListView(
                        HeaderItem("AI CO-PILOT"),
                        FeatureItem("Code Mentor Chat", "mentor", "AI", "Chat with your codebase live."),
                        FeatureItem("AI Commit Lab", "ai-lab", "Tools", "Native AI commit generator."),
                        
                        HeaderItem("INTELLIGENCE"),
                        FeatureItem("Intelligence Hub", "osint", "GitHub", "Live reconnaissance and health."),
                        FeatureItem("Analytics Studio", "analytics", "Tools", "Predictive growth metrics."),
                        
                        HeaderItem("SYSTEM"),
                        FeatureItem("Sentinel SAST", "security", "Tools", "Vulnerability scanner."),
                        FeatureItem("Identity Vault", "identity", "Tools", "Manage profiles."),
                        FeatureItem("SSH Infrastructure", "ssh", "GitHub", "Automated SSH setup."),
                        id="feature-list"
                    )
                ),
                id="sidebar"
            ),
            ContentSwitcher(
                Vertical(
                    Static("Welcome to PyGitUp God Mode", classes="title"),
                    Static("PyGitUp is now a complete AI-driven development ecosystem.\nSelect 'Code Mentor Chat' to begin talking to your code.", id="home-desc"),
                    id="home-view"
                ),
                Vertical(
                    Static("📡 OSINT Reconnaissance", classes="title"),
                    Markdown("", id="intel-report"),
                    id="osint-view"
                ),
                Vertical(
                    Static("🧠 AI Code Mentor", classes="title"),
                    Markdown("Hello! I am your PyGitUp Mentor. Ask me anything about your project architecture or staged changes.", id="mentor-chat-view"),
                    Input(placeholder="Type your question (e.g. How can I optimize main.py?)...", id="chat-input"),
                    id="mentor-view"
                ),
                Vertical(
                    Static("🧠 AI Semantic Commit Lab", classes="title"),
                    Markdown("", id="ai-diff-view"),
                    Horizontal(
                        Button("Analyze & Stage", variant="primary", id="btn-analyze"),
                        classes="btn-row"
                    ),
                    id="ai-lab-view"
                ),
                Vertical(
                    Static("📊 Analytics Studio", classes="title"),
                    Markdown("", id="analytics-report"),
                    id="analytics-view"
                ),
                Vertical(
                    Static("🛡️ Sentinel SAST Scanner", classes="title"),
                    DataTable(id="security-table"),
                    Horizontal(Button("Run Full Scan", variant="primary", id="btn-scan"), classes="btn-row"),
                    id="security-view"
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
        table = self.query_one("#security-table", DataTable)
        table.add_columns("Threat", "Location", "Snippet")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if not isinstance(event.item, FeatureItem): return
        mode = event.item.mode
        if mode == "osint": self.run_osint_view()
        elif mode == "mentor": self.run_mentor_view()
        elif mode == "ai-lab": self.run_ai_lab()
        elif mode == "analytics": self.run_analytics_view()
        elif mode == "security": self.run_security_view()
        elif mode == "identity": self.run_identity_view()
        else: self.launch_cli_fallback(mode)

    def run_mentor_view(self):
        self.query_one("#main-switcher").current = "mentor-view"
        self.query_one("#chat-input").focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "chat-input":
            query = event.value
            event.input.value = ""
            chat_view = self.query_one("#mentor-chat-view", Markdown)
            chat_view.update(f"### 👤 You\n{query}\n\n---\n### 🤖 Mentor\nThinking...")
            
            # Gathers local context
            context = self.gather_local_context()
            self.run_worker(self.mentor_task(query, context))

    def gather_local_context(self):
        """Builds a technical context blob of the local codebase."""
        context = "FILE STRUCTURE:\n"
        for root, dirs, files in os.walk("."):
            if ".git" in root or "node_modules" in root: continue
            level = root.replace(".", "").count(os.sep)
            indent = " " * 4 * level
            context += f"{indent}{os.path.basename(root)}/\n"
            for f in files:
                context += f"{indent}    {f}\n"
        
        # Read snippets of main entry files
        priority = ["main.py", "setup.py", "requirements.txt", "README.md", "pygitup/ui/app.py"]
        for p in priority:
            if os.path.exists(p):
                try:
                    with open(p, 'r') as f:
                        snippet = "".join(f.readlines()[:100])
                        context += f"\nFILE: {p}\n{snippet}\n"
                except: pass
        return context

    async def mentor_task(self, query, context):
        config = load_config()
        ai_key = config["github"].get("ai_api_key")
        response = code_mentor_chat(ai_key, query, context)
        self.query_one("#mentor-chat-view").update(response or "I encountered an error processing your query.")

    # --- OTHER VIEW HANDLERS ---
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
        self.query_one("#analytics-report").update("# 📊 Crunching Projections...")
        self.run_worker(self.fetch_analytics_task())

    def run_security_view(self): self.query_one("#main-switcher").current = "security-view"

    def run_identity_view(self):
        self.query_one("#main-switcher").current = "identity-view"
        p_list = self.query_one("#profile-list", ListView)
        p_list.clear()
        for p in list_profiles(): p_list.append(ListItem(Label(f"🔑 {p}")))

    async def fetch_intel_task(self):
        config = load_config(); token = get_github_token(config)
        try:
            resp = get_repo_info("frederickabrah", "PyGitup", token)
            if resp.status_code == 200:
                data = resp.json(); health = get_repo_health_metrics("frederickabrah", "PyGitup", token)
                md = f"# 🛰️ {data.get('full_name')}\n\n- **Stars:** {data.get('stargazers_count')} | **Health:** {health.get('activity_status', 'N/A')}\n- **Sponsors:** {'Active 💖' if data.get('is_sponsored') else 'None'}"
                self.query_one("#intel-report").update(md)
        except Exception as e: self.query_one("#intel-report").update(f"Error: {e}")

    async def fetch_analytics_task(self):
        config = load_config(); token = get_github_token(config); user = get_github_username(config)
        try:
            repo_resp = get_repo_info(user, "PyGitup", token)
            data = repo_resp.json()
            proj = predict_growth_v2(data['stargazers_count'], data['created_at'], data['forks_count'])
            self.query_one("#analytics-report").update(f"# 📈 Analytics\n\n- **90-Day Projection:** {proj} 🌟")
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
        for r in results: table.add_row(r['type'], f"{os.path.basename(r['file'])}:{r['line']}", r['code'])
        self.notify("SAST Scan Complete")

    def action_go_home(self): self.query_one("#main-switcher").current = "home-view"

    def launch_cli_fallback(self, mode):
        from ..project.project_ops import upload_project_directory
        from ..github.ssh_ops import setup_ssh_infrastructure
        config = load_config(); user = get_github_username(config); token = get_github_token(config)
        with self.suspend():
            os.system('cls' if os.name == 'nt' else 'clear')
            if mode == "project": upload_project_directory(user, token, config)
            elif mode == "ssh": setup_ssh_infrastructure(config, token)
            input("\nPress Enter to return to Dashboard...")

def run_tui():
    PyGitUpTUI().run()