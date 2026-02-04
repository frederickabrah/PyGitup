from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, ScrollableContainer, Grid
from textual.widgets import Header, Footer, Static, ListItem, ListView, Label, Markdown, ContentSwitcher, Button, DataTable, Input, LoadingIndicator
from textual.binding import Binding
from .. import __version__
from ..core.config import load_config, get_github_username, get_github_token, get_active_profile_path, list_profiles, set_active_profile
from ..github.repo_info import get_repo_info, get_repo_health_metrics
from ..utils.ai import get_git_diff, generate_ai_commit_message, code_mentor_chat
from ..utils.analytics import calculate_health_score, predict_growth_v2
from ..utils.security import run_local_sast_scan
from ..utils.validation import get_current_repo_context
import os
import subprocess

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

class HeaderItem(ListItem):
    """A non-selectable header item for the list."""
    def __init__(self, text: str):
        super().__init__(disabled=True)
        self.text = text

    def compose(self) -> ComposeResult:
        yield Label(f" {self.text} ", classes="category-header")

class PyGitUpTUI(App):
    """The total immersion God Mode Dashboard."""
    
    TITLE = f"PyGitUp v{__version__}"
    chat_history = [] 

    CSS = """
    Screen { background: #0d1117; color: #c9d1d9; }
    #sidebar { width: 35%; background: #161b22; border-right: tall #30363d; }
    #main-switcher { width: 65%; padding: 1 4; }
    .category-header { 
        background: #21262d; 
        color: #58a6ff; 
        text-style: bold; 
        width: 100%;
        text-align: center;
        margin-top: 1;
    }
    ListItem { padding: 1 1; border-bottom: hkey #30363d; }
    ListItem:hover { background: #1f6feb; }
    ListView:focus > ListItem.--highlight { background: #238636; color: white; }
    .title-banner { background: #1f6feb; color: white; text-style: bold; padding: 0 2; margin-bottom: 1; width: 100%; }
    Markdown, DataTable { height: 100%; border: solid #30363d; padding: 1; background: #0d1117; }
    #chat-scroll { height: 1fr; border: solid #30363d; background: #090c10; margin-bottom: 1; }
    #chat-input { border: double #58a6ff; }
    LoadingIndicator { color: #58a6ff; height: 3; display: none; }
    LoadingIndicator.-loading { display: block; }
    .btn-row { margin-top: 1; height: 3; }
    Button { margin-right: 2; }
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
                Label(f" 👤 PROFILE: {active_profile.upper()} ", classes="category-header", id="profile-label"),
                ScrollableContainer(
                    ListView(
                        HeaderItem("AI COMMAND CENTER"),
                        FeatureItem("Neural Code Mentor", "mentor", "AI", "Immersive chat with your local codebase."),
                        FeatureItem("AI Commit Lab", "ai-lab", "AI", "Native diff analysis and semantic commits."),
                        
                        HeaderItem("INTELLIGENCE"),
                        FeatureItem("OSINT Dashboard", "osint", "GitHub", "Live repository reconnaissance."),
                        FeatureItem("Analytics Studio", "analytics", "Data", "Predictive growth and impact scoring."),
                        
                        HeaderItem("FORTRESS"),
                        FeatureItem("Sentinel SAST", "security", "Security", "Local vulnerability and secret scanning."),
                        FeatureItem("Identity Vault", "identity", "Auth", "Manage stealth profiles."),
                        FeatureItem("SSH Manager", "ssh", "Auth", "Automated SSH setup."),
                        
                        HeaderItem("CORE OPERATIONS"),
                        FeatureItem("Project Upload", "project", "Core", "Cloud initialization & security pre-scan."),
                        FeatureItem("Marketplace", "marketplace", "Core", "Deploy 'God Tier' architectures."),
                        id="feature-list"
                    )
                ),
                id="sidebar"
            ),
            ContentSwitcher(
                Vertical(
                    Static("PYGITUP GLOBAL COMMAND CENTER", classes="title-banner"),
                    Static("Welcome to God Mode.\nPyGitUp is officially immersive and reactive.\n\nSelect a neural module to begin.", id="home-desc"),
                    id="home-view"
                ),
                Vertical(
                    Static("📡 OSINT RECONNAISSANCE", classes="title-banner"),
                    Markdown("", id="intel-report"),
                    id="osint-view"
                ),
                Vertical(
                    Static("🧠 NEURAL CODE MENTOR", classes="title-banner"),
                    ScrollableContainer(Markdown("System initialized. Ask me about your code...", id="mentor-chat-view"), id="chat-scroll"),
                    LoadingIndicator(id="chat-loader"),
                    Input(placeholder="Ask a technical question...", id="chat-input"),
                    id="mentor-view"
                ),
                Vertical(
                    Static("🧠 AI COMMIT LAB", classes="title-banner"),
                    Markdown("", id="ai-diff-view"),
                    Horizontal(
                        Button("Generate & Stage", variant="primary", id="btn-analyze"),
                        classes="btn-row"
                    ),
                    id="ai-lab-view"
                ),
                Vertical(
                    Static("📊 ANALYTICS STUDIO", classes="title-banner"),
                    Markdown("", id="analytics-report"),
                    id="analytics-view"
                ),
                Vertical(
                    Static("🛡️ SENTINEL SAST", classes="title-banner"),
                    DataTable(id="security-table"),
                    Horizontal(Button("Run Sentinel Scan", variant="primary", id="btn-scan"), classes="btn-row"),
                    id="security-view"
                ),
                Vertical(
                    Static("🏗️ TEMPLATE MARKETPLACE", classes="title-banner"),
                    Grid(
                        Button("FastAPI Pro", id="tpl-fastapi"),
                        Button("Express Node", id="tpl-node"),
                        Button("Python CLI", id="tpl-cli"),
                        id="marketplace-grid"
                    ),
                    id="marketplace-view"
                ),
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

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.item and isinstance(event.item, FeatureItem):
            if self.query_one("#main-switcher").current == "home-view":
                self.query_one("#home-desc").update(f"{event.item.description}\n\n[bold white]Press ENTER to activate.[/bold white]")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if not isinstance(event.item, FeatureItem): return
        mode = event.item.mode
        if mode == "mentor": self.run_mentor_view()
        elif mode == "osint": self.run_osint_view()
        elif mode == "analytics": self.run_analytics_view()
        elif mode == "security": self.run_security_view()
        elif mode == "identity": self.run_identity_view()
        elif mode == "marketplace": self.run_marketplace_view()
        else: self.launch_cli_fallback(mode)

    # --- NATIVE VIEWS ---
    def run_mentor_view(self):
        self.query_one("#main-switcher").current = "mentor-view"
        self.query_one("#chat-input").focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "chat-input":
            query = event.value; event.input.value = ""
            self.query_one("#chat-loader").add_class("-loading")
            self.run_worker(self.mentor_task(query))

    async def mentor_task(self, query):
        ctx = self.gather_smart_context()
        config = load_config(); ai_key = config["github"].get("ai_api_key")
        from ..utils.ai import code_mentor_chat
        resp = code_mentor_chat(ai_key, query, ctx, history=self.chat_history)
        self.chat_history.append({"role": "user", "text": query})
        self.chat_history.append({"role": "model", "text": resp})
        self.query_one("#chat-loader").remove_class("-loading")
        full_conversation = "# Neural Conversation History\n"
        for turn in self.chat_history:
            icon = "👤 **You**" if turn['role'] == "user" else "🤖 **Mentor**"
            full_conversation += f"\n---\n{icon}\n{turn['text']}\n"
        self.query_one("#mentor-chat-view").update(full_conversation)
        self.query_one("#chat-scroll").scroll_end(animate=False)

    def gather_smart_context(self):
        context = "Structure:\n"
        for root, _, files in os.walk("."):
            if any(x in root for x in [".git", "node_modules"]): continue
            for f in files: context += f"{root}/{f}\n"
        priority = ["main.py", "setup.py", "requirements.txt", "pygitup/ui/app.py"]
        for p in priority:
            if os.path.exists(p):
                with open(p, 'r', errors='ignore') as f: context += f"\n\n--- {p} ---\n" + "".join(f.readlines()[:150])
        return context

    def run_osint_view(self):
        self.query_one("#main-switcher").current = "osint-view"
        self.run_worker(self.fetch_intel_task())

    async def fetch_intel_task(self):
        owner, repo = get_current_repo_context()
        if not owner or not repo:
            self.query_one("#intel-report").update("## ❌ Context Error\nCould not find Git 'origin' remote.")
            return
        config = load_config(); token = get_github_token(config)
        try:
            resp = get_repo_info(owner, repo, token)
            if resp.status_code == 200:
                data = resp.json(); health = get_repo_health_metrics(owner, repo, token)
                md = f"# 🛰️ {data.get('full_name')}\n\n| Attribute | Intelligence |\n| --- | --- |\n| ⭐ Stars | {data.get('stargazers_count')} |\n| 🍴 Forks | {data.get('forks_count')} |\n| 🚑 Health | {health.get('activity_status', 'N/A')} |"
                self.query_one("#intel-report").update(md)
        except: pass

    def run_analytics_view(self):
        self.query_one("#main-switcher").current = "analytics-view"
        self.run_worker(self.fetch_analytics_task())

    async def fetch_analytics_task(self):
        owner, repo = get_current_repo_context()
        if not owner or not repo:
            self.query_one("#analytics-report").update("## ❌ Context Error\nCould not identify repository.")
            return
        config = load_config(); token = get_github_token(config); user = get_github_username(config)
        try:
            repo_resp = get_repo_info(owner, repo, token)
            if repo_resp.status_code == 200:
                data = repo_resp.json()
                proj = predict_growth_v2(data['stargazers_count'], data['created_at'], data['forks_count'])
                self.query_one("#analytics-report").update(f"# 📈 Momentum: {repo}\n\n- **Projected Star Goal:** {proj} 🌟")
        except: pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-scan": self.run_sast_scan()
        elif event.button.id == "btn-analyze": self.launch_cli_fallback("ai-commit")
        elif event.button.id.startswith("tpl-"):
            tpl_map = {"tpl-fastapi": "fastapi-pro", "tpl-node": "express-node", "tpl-cli": "cli-python"}
            self.launch_cli_fallback(f"template --template {tpl_map[event.button.id]}")

    def run_sast_scan(self):
        table = self.query_one("#security-table", DataTable); table.clear()
        results = run_local_sast_scan(".")
        if results:
            for r in results: table.add_row(r['type'], os.path.basename(r['file']), r['code'])
            self.notify("Scan Complete: Issues Found", severity="warning")
        else: self.notify("Scan Complete: System Secure")

    def run_security_view(self): self.query_one("#main-switcher").current = "security-view"
    def run_identity_view(self):
        self.query_one("#main-switcher").current = "identity-view"
        p_list = self.query_one("#profile-list", ListView); p_list.clear()
        for p in list_profiles(): p_list.append(ListItem(Label(f"🔑 {p}")))
    def run_marketplace_view(self): self.query_one("#main-switcher").current = "marketplace-view"
    def action_go_home(self): self.query_one("#main-switcher").current = "home-view"

    def launch_cli_fallback(self, mode):
        from ..project.project_ops import upload_project_directory, migrate_repository
        from ..github.ssh_ops import setup_ssh_infrastructure
        from ..utils.ai import ai_commit_workflow
        from ..project.templates import create_project_from_template
        config = load_config(); user = get_github_username(config); token = get_github_token(config)
        actual_mode = mode.split(" ")[0]
        with self.suspend():
            os.system('cls' if os.name == 'nt' else 'clear')
            try:
                if actual_mode == "project": upload_project_directory(user, token, config)
                elif actual_mode == "template":
                    if "--template" in mode:
                        t_name = mode.split("--template ")[1]
                        class MockArgs: template = t_name; repo = None; variables = None; private = True; dry_run = False
                        create_project_from_template(user, token, config, MockArgs())
                    else: create_project_from_template(user, token, config)
                elif actual_mode == "ai-commit": ai_commit_workflow(user, token, config)
                elif actual_mode == "ssh": setup_ssh_infrastructure(config, token)
                input("\nPress Enter to return to TUI...")
            except: input("\nFailed. Press Enter...")

def run_tui():
    PyGitUpTUI().run()
