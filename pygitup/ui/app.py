from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, ScrollableContainer, Container
from textual.widgets import Header, Footer, Static, ListItem, ListView, Label, Markdown, ContentSwitcher, Button, DataTable, Input, LoadingIndicator
from textual.binding import Binding
from .. import __version__
from ..core.config import load_config, get_github_username, get_github_token, get_active_profile_path, list_profiles, set_active_profile
from ..github.repo_info import get_repo_info, get_repo_health_metrics
from ..utils.ai import get_git_diff, generate_ai_commit_message, code_mentor_chat
from ..utils.analytics import calculate_health_score, predict_growth_v2
from ..utils.security import run_local_sast_scan
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

class HeaderItem(ListItem):
    def __init__(self, text: str):
        super().__init__(disabled=True)
        self.text = text
    def compose(self) -> ComposeResult:
        yield Label(f" {self.text} ", classes="category-header")

class PyGitUpTUI(App):
    """The High-Performance, Immersive God Mode Dashboard."""
    
    TITLE = f"PyGitUp v{__version__}"
    CSS = """
    Screen { background: #0d1117; color: #c9d1d9; }
    #sidebar { width: 30%; background: #161b22; border-right: tall #30363d; }
    #main-switcher { width: 70%; padding: 1 2; }
    .category-header { background: #21262d; color: #58a6ff; text-style: bold; width: 100%; text-align: center; margin-top: 1; }
    ListItem { padding: 1 1; border-bottom: hkey #30363d; }
    ListItem:hover { background: #1f6feb; }
    ListView:focus > ListItem.--highlight { background: #238636; color: white; }
    .title-banner { background: #1f6feb; color: white; text-style: bold; padding: 0 2; margin-bottom: 1; width: 100%; }
    Markdown { background: #0d1117; border: solid #30363d; padding: 1; height: auto; }
    #chat-scroll { height: 1fr; border: solid #30363d; background: #090c10; margin-bottom: 1; }
    #chat-input { border: double #58a6ff; }
    LoadingIndicator { color: #58a6ff; height: 3; }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("escape", "go_home", "Home", show=True),
        Binding("r", "refresh", "Sync", show=True),
    ]

    def compose(self) -> ComposeResult:
        active_profile = os.path.basename(get_active_profile_path()).replace(".yaml", "")
        yield Header(show_clock=True)
        yield Horizontal(
            Vertical(
                Label(f" 👤 {active_profile.upper()} ", classes="category-header"),
                ScrollableContainer(
                    ListView(
                        HeaderItem("AI COMMANDER"),
                        FeatureItem("Code Mentor Chat", "mentor", "AI", "Talk to your local codebase."),
                        FeatureItem("Commit Architect", "ai-lab", "AI", "Generate semantic commits."),
                        HeaderItem("INTELLIGENCE"),
                        FeatureItem("OSINT Intelligence", "osint", "GitHub", "Deep repo reconnaissance."),
                        FeatureItem("Analytics Studio", "analytics", "Data", "Growth and impact metrics."),
                        HeaderItem("FORTRESS"),
                        FeatureItem("Sentinel SAST", "security", "Security", "Vulnerability scanning."),
                        FeatureItem("Identity Vault", "identity", "Auth", "Switch stealth profiles."),
                        FeatureItem("SSH Manager", "ssh", "Auth", "Auto-SSH setup."),
                        id="feature-list"
                    )
                ),
                id="sidebar"
            ),
            ContentSwitcher(
                # --- HOME ---
                Vertical(
                    Static("PYGITUP GLOBAL COMMAND CENTER", classes="title-banner"),
                    Static("Status: [bold green]ONLINE[/bold green]\n\nSelect a neural module from the sidebar to begin.\nYour workspace is synced and secured.", id="home-desc"),
                    id="home-view"
                ),
                # --- MENTOR ---
                Vertical(
                    Static("🧠 NEURAL CODE MENTOR", classes="title-banner"),
                    ScrollableContainer(Markdown("System initialized. Ask me about your code...", id="mentor-chat-view"), id="chat-scroll"),
                    LoadingIndicator(id="chat-loader", show=False),
                    Input(placeholder="Ask a technical question...", id="chat-input"),
                    id="mentor-view"
                ),
                # --- OSINT ---
                Vertical(
                    Static("📡 SATELLITE RECONNAISSANCE", classes="title-banner"),
                    Markdown("", id="intel-report"),
                    id="osint-view"
                ),
                # --- AI LAB ---
                Vertical(
                    Static("🛠️ COMMIT ARCHITECT", classes="title-banner"),
                    Markdown("", id="ai-diff-view"),
                    Horizontal(Button("Generate Message", variant="primary", id="btn-analyze"), classes="btn-row"),
                    id="ai-lab-view"
                ),
                # --- ANALYTICS ---
                Vertical(
                    Static("📈 ANALYTICS STUDIO", classes="title-banner"),
                    Markdown("", id="analytics-report"),
                    id="analytics-view"
                ),
                # --- SECURITY ---
                Vertical(
                    Static("🛡️ SENTINEL SAST", classes="title-banner"),
                    DataTable(id="security-table"),
                    Horizontal(Button("Run Sentinel Scan", variant="primary", id="btn-scan"), classes="btn-row"),
                    id="security-view"
                ),
                # --- IDENTITY ---
                Vertical(
                    Static("🔐 IDENTITY VAULT", classes="title-banner"),
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
        self.query_one("#security-table", DataTable).add_columns("Type", "File", "Context")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        mode = event.item.mode
        if mode == "osint": self.run_osint_view()
        elif mode == "mentor": self.run_mentor_view()
        elif mode == "ai-lab": self.run_ai_lab()
        elif mode == "analytics": self.run_analytics_view()
        elif mode == "security": self.run_security_view()
        elif mode == "identity": self.run_identity_view()
        else: self.launch_cli_fallback(mode)

    # --- NATIVE HANDLERS ---
    def run_mentor_view(self):
        self.query_one("#main-switcher").current = "mentor-view"
        self.query_one("#chat-input").focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "chat-input":
            query = event.value
            event.input.value = ""
            self.query_one("#chat-loader").show = True
            self.query_one("#mentor-chat-view").update(f"### 👤 You\n{query}\n\n---\n### 🤖 Mentor\nThinking...")
            self.run_worker(self.mentor_task(query))

    def gather_smart_context(self):
        """High-fidelity project context engine."""
        files = []
        for root, _, filenames in os.walk("."):
            if any(x in root for x in [".git", "node_modules", "venv", "dist"]): continue
            for f in filenames: files.append(os.path.join(root, f))
        
        context = f"Project: {os.getcwd()}\nStructure:\n" + "\n".join(files[:50])
        priority = ["main.py", "setup.py", "requirements.txt", "README.md", "pygitup/ui/app.py", "pygitup/utils/ai.py"]
        for p in priority:
            if os.path.exists(p):
                with open(p, 'r', errors='ignore') as f:
                    context += f"\n\n--- FILE CONTENT: {p} ---\n" + "".join(f.readlines()[:200])
        return context

    async def mentor_task(self, query):
        ctx = self.gather_smart_context()
        config = load_config(); ai_key = config["github"].get("ai_api_key")
        from ..utils.ai import code_mentor_chat
        resp = code_mentor_chat(ai_key, query, ctx)
        self.query_one("#chat-loader").show = False
        self.query_one("#mentor-chat-view").update(resp or "Connection error.")

    def run_osint_view(self):
        self.query_one("#main-switcher").current = "osint-view"
        self.run_worker(self.fetch_intel_task())

    def run_ai_lab(self):
        self.query_one("#main-switcher").current = "ai-lab-view"
        diff = get_git_diff() or "Clean working tree."
        self.query_one("#ai-diff-view").update(f"### Git Diff\n```diff\n{diff}\n```")

    def run_analytics_view(self):
        self.query_one("#main-switcher").current = "analytics-view"
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
                md = f"# 🛰️ {data.get('full_name')}\n\n- **Stars:** {data.get('stargazers_count')} | **Forks:** {data.get('forks_count')}\n- **Status:** {health.get('activity_status', 'N/A')}\n- **Velocity:** {health.get('development_velocity_days', 'N/A')} d/c"
                self.query_one("#intel-report").update(md)
        except: pass

    async def fetch_analytics_task(self):
        config = load_config(); token = get_github_token(config); user = get_github_username(config)
        try:
            repo_resp = get_repo_info(user, "PyGitup", token)
            data = repo_resp.json()
            proj = predict_growth_v2(data['stargazers_count'], data['created_at'], data['forks_count'])
            self.query_one("#analytics-report").update(f"# 📈 Momentum Study\n\n- **90-Day Projection:** {proj} 🌟")
        except: pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-scan": self.run_sast_scan()
        elif event.button.id == "btn-analyze": self.launch_cli_fallback("ai-commit")

    def run_sast_scan(self):
        table = self.query_one("#security-table", DataTable); table.clear()
        results = run_local_sast_scan(".")
        for r in results: table.add_row(r['type'], os.path.basename(r['file']), r['code'])
        self.notify("Scan Complete")

    def action_go_home(self): self.query_one("#main-switcher").current = "home-view"

    def launch_cli_fallback(self, mode):
        from ..project.project_ops import upload_project_directory
        from ..github.ssh_ops import setup_ssh_infrastructure
        config = load_config(); user = get_github_username(config); token = get_github_token(config)
        with self.suspend():
            os.system('cls' if os.name == 'nt' else 'clear')
            try:
                if mode == "project": upload_project_directory(user, token, config)
                elif mode == "ssh": setup_ssh_infrastructure(config, token)
                elif mode == "smart-push": from ..git.push import smart_push; smart_push(user, token, config)
                input("\nPress Enter to return to Dashboard...")
            except Exception as e:
                print(f"Error: {e}"); input("Press Enter...")

def run_tui():
    PyGitUpTUI().run()