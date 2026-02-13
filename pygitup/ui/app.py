from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, ScrollableContainer, Grid
from textual.widgets import Header, Footer, Static, ListItem, ListView, Label, Markdown, ContentSwitcher, Button, DataTable, Input, LoadingIndicator, Switch, RichLog
from textual.binding import Binding
from rich.markdown import Markdown as RichMarkdown
from .. import __version__
from ..core.config import load_config, get_github_username, get_github_token, get_active_profile_path, list_profiles, set_active_profile
from ..github.repo_info import get_repo_info, get_repo_health_metrics
from ..utils.ai import get_git_diff, generate_ai_commit_message, code_mentor_chat
from ..utils.analytics import calculate_health_score, predict_growth_v2
from ..utils.security import run_local_sast_scan
from ..utils.validation import get_current_repo_context, validate_file_path, validate_repo_name
import os
import subprocess
import shlex

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
    """The PyGitUp Developer Dashboard."""
    
    TITLE = f"PyGitUp v{__version__}"
    chat_history = [] 
    target_dir = os.getcwd()
    pending_tool = None
    tool_queue = []

    CSS = """
    Screen { background: #0d1117; color: #c9d1d9; }
    #sidebar { width: 30%; background: #161b22; border-right: tall #30363d; }
    #main-switcher { width: 70%; padding: 1 2; }
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
    Markdown, DataTable, #log-view { height: 100%; border: solid #30363d; padding: 1; background: #0d1117; }
    #chat-log { height: 1fr; border: solid #30363d; background: #090c10; margin-bottom: 0; overflow-y: scroll; }
    #chat-input { border: double #58a6ff; height: 3; width: 80%; }
    LoadingIndicator { color: #58a6ff; height: 3; display: none; }
    LoadingIndicator.-loading { display: block; }
    .btn-row { margin-top: 1; height: 3; }
    Button { margin-right: 1; }
    .form-label { margin-top: 1; color: #58a6ff; text-style: bold; }
    .form-input { margin-bottom: 1; }
    #project-log, #release-log, #gist-log, #docs-log, #diag-log, #pr-log { 
        height: 10; border: solid #30363d; background: #010409; color: #7d8590; padding: 0 1; overflow-y: scroll; 
    }
    .scroll-btn { min-width: 5; width: 10%; margin-left: 1; }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("escape", "go_home", "Home", show=True),
        Binding("r", "refresh", "Sync", show=True),
        Binding("ctrl+up", "scroll_chat_up", "Scroll Up", show=False),
        Binding("ctrl+down", "scroll_chat_down", "Scroll Down", show=False),
    ]

    def compose(self) -> ComposeResult:
        active_profile = os.path.basename(get_active_profile_path()).replace(".yaml", "")
        yield Header(show_clock=True)
        yield Horizontal(
            Vertical(
                Label(f" 👤 PROFILE: {active_profile.upper()} ", classes="category-header", id="profile-label"),
                ScrollableContainer(
                    ListView(
                        HeaderItem("AI ENGINEERING"),
                        FeatureItem("AI Assistant (Autonomous)", "mentor", "AI", "Autonomous task execution and file management."),
                        FeatureItem("AI Diagnostic Loop", "ai-diagnostic", "AI", "Run commands and auto-heal failures."),
                        FeatureItem("AI Commit Lab", "ai-lab", "AI", "Automated diff analysis and commit generation."),
                        
                        HeaderItem("DATA ANALYSIS"),
                        FeatureItem("Repo Dashboard", "osint", "GitHub", "Repository metadata and digital footprint."),
                        FeatureItem("Analytics Studio", "analytics", "Data", "Growth trends and health scoring."),
                        
                        HeaderItem("SECURITY"),
                        FeatureItem("Static Scan (SAST)", "security", "Security", "Local vulnerability scanning."),
                        FeatureItem("Identity Vault", "identity", "Auth", "Manage account profiles."),
                        FeatureItem("SSH Manager", "ssh", "Auth", "Automated SSH configuration."),
                        
                        HeaderItem("REPOSITORY OPS"),
                        FeatureItem("Project Upload", "project", "Core", "Repository initialization and push."),
                        FeatureItem("Marketplace", "marketplace", "Core", "Deploy boilerplate templates."),
                        
                        HeaderItem("ADVANCED GIT OPS"),
                        FeatureItem("Release Manager", "release", "DevOps", "Create GitHub releases."),
                        FeatureItem("Pull Requests", "pr", "Collab", "Manage open pull requests."),
                        FeatureItem("Gist Manager", "gist", "Share", "Manage GitHub Gists."),
                        FeatureItem("Docs Generator", "generate-docs", "Docs", "Generate project documentation."),
                        id="feature-list"
                    )
                ),
                id="sidebar"
            ),
            ContentSwitcher(
                Vertical(
                    Static("PYGITUP CONTROL CENTER", classes="title-banner"),
                    Static("Select a module from the sidebar to begin.\nManage your repositories and automate Git workflows.", id="home-desc"),
                    Label("🎯 ACTIVE TARGET PROJECT:", classes="form-label"),
                    Horizontal(
                        Input(id="target-dir-input", placeholder="Enter full path to project...", classes="form-input"),
                        Button("SWITCH CONTEXT", id="btn-switch-context", variant="primary"),
                        classes="btn-row"
                    ),
                    Static(f"[dim]Current: {os.getcwd()}[/dim]", id="lbl-current-target"),
                    id="home-view"
                ),
                Vertical(
                    Static("🛰️ PROJECT UPLOAD", classes="title-banner"),
                    ScrollableContainer(
                        Label("Local Project Path:", classes="form-label"),
                        Input(placeholder="/path/to/project", id="up-path", classes="form-input"),
                        Label("Repository Name:", classes="form-label"),
                        Input(placeholder="my-awesome-repo", id="up-name", classes="form-input"),
                        Label("Description:", classes="form-label"),
                        Input(placeholder="A brief summary...", id="up-desc", classes="form-input"),
                        Horizontal(
                            Label("[bold]Private Repository? [/bold]"),
                            Switch(value=True, id="up-private"),
                            classes="btn-row"
                        ),
                        Button("START UPLOAD", variant="primary", id="btn-upload-start"),
                        Label("Progress Log:", classes="form-label"),
                        Static("", id="project-log"),
                    ),
                    id="project-view"
                ),
                Vertical(
                    Static("📡 REPOSITORY DATA", classes="title-banner"),
                    Markdown("", id="intel-report"),
                    id="osint-view"
                ),
                Vertical(
                    Static("🧠 AI ASSISTANT", classes="title-banner"),
                    Horizontal(
                        Static(f"[dim italic]Context: {os.getcwd()}[/dim italic]", id="chat-context-label"),
                        Static("[bold cyan]Mission: Idle[/bold cyan]", id="chat-mission-label"),
                        classes="btn-row"
                    ),
                    RichLog(id="chat-log", highlight=True, markup=True, wrap=True),
                    LoadingIndicator(id="chat-loader"),
                    Horizontal(
                        Input(placeholder="Ask a technical question...", id="chat-input"),
                        Button("⬆️", id="btn-scroll-up", classes="scroll-btn"),
                        Button("⬇️", id="btn-scroll-down", classes="scroll-btn"),
                        classes="btn-row"
                    ),
                    id="mentor-view"
                ),
                Vertical(
                    Static("🛠️ AI DIAGNOSTIC LOOP", classes="title-banner"),
                    Label("Command to Verify (e.g. pytest):", classes="form-label"),
                    Input(placeholder="python3 -m pytest", id="diag-cmd", classes="form-input"),
                    Button("RUN & HEAL", id="btn-diag-start", variant="primary"),
                    Static("", id="diag-log"),
                    id="diagnostic-view"
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
                    Static("🛡️ STATIC SCAN (SAST)", classes="title-banner"),
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
                Vertical(
                    Static("🚀 RELEASE COMMANDER", classes="title-banner"),
                    ScrollableContainer(
                        Label("Version Tag (e.g. v1.0.0):", classes="form-label"),
                        Input(placeholder="v1.0.0", id="rel-tag", classes="form-input"),
                        Label("Release Title:", classes="form-label"),
                        Input(placeholder="The Big Update", id="rel-name", classes="form-input"),
                        Label("Release Notes (Markdown supported):", classes="form-label"),
                        Input(placeholder="- Fixed bugs\n- Added features", id="rel-notes", classes="form-input"),
                        Button("PUBLISH RELEASE", variant="primary", id="btn-release-start"),
                        Label("Status Log:", classes="form-label"),
                        Static("", id="release-log"),
                    ),
                    id="release-view"
                ),
                Vertical(
                    Static("📝 GIST MANAGER", classes="title-banner"),
                    Horizontal(
                        Button("Create New", id="btn-gist-mode-create", variant="primary"),
                        Button("List All", id="btn-gist-mode-list"),
                        classes="btn-row"
                    ),
                    ContentSwitcher(
                        ScrollableContainer(
                            Label("Filename:", classes="form-label"),
                            Input(placeholder="snippet.py", id="gist-file", classes="form-input"),
                            Label("Description:", classes="form-label"),
                            Input(placeholder="A useful script", id="gist-desc", classes="form-input"),
                            Label("Content:", classes="form-label"),
                            Input(placeholder="print('Hello World')", id="gist-content", classes="form-input"),
                            Horizontal(
                                Label("[bold]Public? [/bold]"),
                                Switch(value=False, id="gist-public"),
                                classes="btn-row"
                            ),
                            Button("CREATE GIST", variant="primary", id="btn-gist-create"),
                            Static("", id="gist-log"),
                            id="gist-create-view"
                        ),
                        Vertical(
                            DataTable(id="gist-table"),
                            id="gist-list-view"
                        ),
                        id="gist-switcher",
                        initial="gist-create-view"
                    ),
                    id="gist-view"
                ),
                Vertical(
                    Static("🔑 SSH INFRASTRUCTURE", classes="title-banner"),
                    Static("Current Status:", classes="form-label"),
                    Markdown("", id="ssh-status-view"),
                    Button("GENERATE & UPLOAD KEY", variant="primary", id="btn-ssh-gen"),
                    Static("", id="ssh-log"),
                    id="ssh-view"
                ),
                Vertical(
                    Static("📄 DOCS GENERATOR", classes="title-banner"),
                    ScrollableContainer(
                        Label("Select Documents to Generate:", classes="form-label"),
                        Horizontal(Label("README.md "), Switch(value=True, id="doc-readme"), classes="btn-row"),
                        Horizontal(Label("CONTRIBUTING.md "), Switch(value=True, id="doc-contrib"), classes="btn-row"),
                        Horizontal(Label("CODE_OF_CONDUCT.md "), Switch(value=True, id="doc-coc"), classes="btn-row"),
                        Horizontal(Label("SECURITY.md "), Switch(value=True, id="doc-sec"), classes="btn-row"),
                        Horizontal(Label("LICENSE "), Switch(value=True, id="doc-lic"), classes="btn-row"),
                        Button("GENERATE DOCS", variant="primary", id="btn-docs-gen"),
                        Label("Output Log:", classes="form-label"),
                        Static("", id="docs-log"),
                    ),
                    id="docs-view"
                ),
                Vertical(
                    Static("🤝 PULL REQUEST CENTER", classes="title-banner"),
                    Horizontal(
                        Button("Open PRs", id="btn-pr-mode-list", variant="primary"),
                        Button("Create New", id="btn-pr-mode-create"),
                        classes="btn-row"
                    ),
                    ContentSwitcher(
                        Vertical(
                            DataTable(id="pr-table"),
                            Horizontal(
                                Button("MERGE", id="btn-pr-merge", variant="success"),
                                Button("CLOSE", id="btn-pr-close", variant="error"),
                                classes="btn-row"
                            ),
                            id="pr-list-view"
                        ),
                        ScrollableContainer(
                            Label("PR Title:", classes="form-label"),
                            Input(placeholder="feat: add cool feature", id="pr-title", classes="form-input"),
                            Label("Head Branch (from):", classes="form-label"),
                            Input(placeholder="feature-branch", id="pr-head", classes="form-input"),
                            Label("Base Branch (into):", classes="form-label"),
                            Input(placeholder="main", id="pr-base", classes="form-input"),
                            Label("Body / Description:", classes="form-label"),
                            Input(placeholder="What does this PR do?", id="pr-body", classes="form-input"),
                            Button("SUBMIT PULL REQUEST", variant="primary", id="btn-pr-create"),
                            Static("", id="pr-log"),
                            id="pr-create-view"
                        ),
                        id="pr-switcher",
                        initial="pr-list-view"
                    ),
                    id="pr-view"
                ),
                id="main-switcher",
                initial="home-view"
            )
        )
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#feature-list").focus()
        self.query_one("#security-table", DataTable).add_columns("Type", "File", "Context")
        self.query_one("#gist-table", DataTable).add_columns("Filename", "Description", "Visibility", "URL")
        self.query_one("#pr-table", DataTable).add_columns("Number", "Title", "From", "Into")

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.item and isinstance(event.item, FeatureItem):
            if self.query_one("#main-switcher").current == "home-view":
                self.query_one("#home-desc").update(f"{event.item.description}\n\n[bold white]Press ENTER to activate.[/bold white]")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if not isinstance(event.item, FeatureItem): return
        mode = event.item.mode
        if mode == "mentor": self.run_mentor_view()
        elif mode == "ai-diagnostic": self.run_diagnostic_view()
        elif mode == "project": self.run_project_view()
        elif mode == "osint": self.run_osint_view()
        elif mode == "analytics": self.run_analytics_view()
        elif mode == "security": self.run_security_view()
        elif mode == "identity": self.run_identity_view()
        elif mode == "marketplace": self.run_marketplace_view()
        elif mode == "release": self.run_release_view()
        elif mode == "gist": self.run_gist_view()
        elif mode == "ssh": self.run_ssh_view()
        elif mode == "generate-docs": self.run_docs_view()
        elif mode == "pr": self.run_pr_view()
        else: self.launch_cli_fallback(mode)

    # --- CORE REPOSITORY LOGIC ---
    async def upload_task(self):
        path, name, desc = self.query_one("#up-path").value, self.query_one("#up-name").value, self.query_one("#up-desc").value
        private = self.query_one("#up-private").value
        log_widget = self.query_one("#project-log")
        messages = ["[bold cyan]Initiating Deployment Pipeline...[/bold cyan]"]
        def add_log(msg): messages.append(f"> {msg}"); log_widget.update("\n".join(messages))
        
        # 1. Verification
        if not os.path.exists(path): add_log("[red]Error: Path does not exist.[/red]"); return
        
        # 2. Local Git Ops (REAL Implementation)
        try:
            os.chdir(path)
            if not os.path.exists(".git"):
                subprocess.run(["git", "init"], check=True, capture_output=True)
                add_log("Initialized empty Git repository.")
            subprocess.run(["git", "add", "."], check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", "Initial push via PyGitUp TUI"], capture_output=True)
            add_log("Local changes staged and committed.")
        except Exception as e: add_log(f"[red]Git Error: {e}[/red]"); return

        # 3. GitHub Cloud Setup
        config = load_config(); user, token = get_github_username(config), get_github_token(config)
        from ..github.api import create_repo, get_repo_info
        
        add_log("Checking GitHub repository status...")
        if get_repo_info(user, name, token).status_code != 200:
            add_log(f"Creating remote repository: {name}")
            create_repo(user, name, token, description=desc, private=private)
        
        # 4. Push Session
        try:
            remote_url = f"https://{token}@github.com/{user}/{name}.git"
            subprocess.run(["git", "remote", "remove", "origin"], capture_output=True)
            subprocess.run(["git", "remote", "add", "origin", f"https://github.com/{user}/{name}.git"], check=True)
            add_log("Synchronizing with remote...")
            subprocess.run(["git", "push", "-u", "--force", remote_url, "main"], check=True, capture_output=True)
            add_log("[bold green]DEPLOYMENT COMPLETE! 🚀[/bold green]")
            self.notify("Project Uploaded Successfully")
        except Exception as e: add_log(f"[red]Cloud Push Error: {e}[/red]")

    async def docs_task(self):
        log = self.query_one("#docs-log")
        log.update("[cyan]Generating Documentation...[/cyan]")
        
        config = load_config(); user = get_github_username(config); token = get_github_token(config)
        owner, repo = get_current_repo_context()
        
        if not owner or not repo:
            log.update("[red]Error: No active repository context.[/red]")
            return

        from ..project.docs import core_generate_docs
        
        # We assume output dir is 'docs' for TUI simplicity
        generated = core_generate_docs(config, repo, "docs", user, token)
        
        if generated:
            log.update(f"[bold green]Success! Generated:[/bold green]\n" + "\n".join(generated))
            self.notify(f"{len(generated)} Docs Generated")
        else:
            log.update("[yellow]No documentation generated (empty repo or API error).[/yellow]")

    # --- AI ASSISTANT LOGIC ---
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "chat-input":
            query = event.value; event.input.value = ""
            if self.pending_tool:
                if query.lower() in ['y', 'yes']:
                    tc = self.pending_tool
                    self.query_one("#chat-log").write(RichMarkdown(f"✅ **APPROVED:** `{tc['name']}`"))
                    from ..utils.agent_tools import execute_agent_tool
                    result = execute_agent_tool(tc['name'], tc['args'])
                    self.run_worker(self.resume_agent_task(tc, result))
                else:
                    self.query_one("#chat-log").write(RichMarkdown("❌ **DENIED**"))
                    self.run_worker(self.resume_agent_task(self.pending_tool, "User denied action.", denied=True))
                self.pending_tool = None
                self.query_one("#chat-input").placeholder = "Ask a technical question..."
                return
            self.chat_history.append({"role": "user", "text": query})
            self.query_one("#chat-log").write(RichMarkdown(f"---\n👤 **You**\n{query}"))
            self.query_one("#chat-loader").add_class("-loading")
            self.run_worker(self.mentor_task(query))

    async def mentor_task(self, query):
        ctx = await self.gather_context_async()
        config = load_config(); ai_key = config["github"].get("ai_api_key")
        from ..utils.ai import code_mentor_chat
        from ..utils.agent_tools import execute_agent_tool
        while True:
            resp = code_mentor_chat(ai_key, query, ctx, history=self.chat_history)
            self.chat_history.append({"role": "model", "text": resp['text'], "tool_calls": resp['tool_calls']})
            if resp['text']: self.query_one("#chat-log").write(RichMarkdown(f"---\n🤖 **Assistant**\n{resp['text']}"))
            if not resp['tool_calls']: break
            for tc in resp['tool_calls']:
                if tc['name'] in ["write_file", "patch_file", "run_shell"]:
                    self.pending_tool = tc
                    self.query_one("#chat-log").write(RichMarkdown(f"⚠️ **APPROVAL REQUIRED:** `{tc['name']}`\nArgs: `{tc['args']}`"))
                    self.query_one("#chat-input").placeholder = "Type 'y' to confirm action..."
                    self.query_one("#chat-loader").remove_class("-loading")
                    return
                result = execute_agent_tool(tc['name'], tc['args'])
                self.chat_history.append({"role": "user", "text": "", "tool_results": [{"name": tc['name'], "content": result}]}
                query = "Proceed with tool results."
        self.query_one("#chat-loader").remove_class("-loading")

    async def resume_agent_task(self, tool_call, result, denied=False):
        self.chat_history.append({"role": "user", "text": "", "tool_results": [{"name": tool_call['name'], "content": result}]}
        await self.mentor_task("Proceed based on tool results.")

    # --- VIEW NAVIGATION ---
    def switch_context(self):
        new_path = self.query_one("#target-dir-input").value
        if os.path.isdir(new_path):
            os.chdir(new_path); self.target_dir = new_path
            self.query_one("#lbl-current-target").update(f"Current: [green]{new_path}[/green]")
            self.notify("Context Switched")
        else: self.notify("Invalid Directory", severity="error")

    def run_mentor_view(self): self.query_one("#main-switcher").current = "mentor-view"; self.query_one("#chat-input").focus()
    def run_diagnostic_view(self): self.query_one("#main-switcher").current = "diagnostic-view"
    def run_project_view(self): self.query_one("#main-switcher").current = "project-view"
    def run_osint_view(self): self.query_one("#main-switcher").current = "osint-view"; self.run_worker(self.fetch_intel_task())
    def run_analytics_view(self): self.query_one("#main-switcher").current = "analytics-view"; self.run_worker(self.fetch_analytics_task())
    def run_security_view(self): self.query_one("#main-switcher").current = "security-view"
    def run_identity_view(self):
        self.query_one("#main-switcher").current = "identity-view"
        p_list = self.query_one("#profile-list", ListView); p_list.clear()
        for p in list_profiles(): p_list.append(ListItem(Label(f"🔑 {p}")))
    def run_marketplace_view(self): self.query_one("#main-switcher").current = "marketplace-view"
    def run_release_view(self): self.query_one("#main-switcher").current = "release-view"
    def run_gist_view(self): self.query_one("#main-switcher").current = "gist-view"
    def run_ssh_view(self): self.query_one("#main-switcher").current = "ssh-view"
    def run_docs_view(self): self.query_one("#main-switcher").current = "docs-view"
    def run_pr_view(self): self.query_one("#main-switcher").current = "pr-view"; self.run_worker(self.list_prs_task())
    def action_go_home(self): self.query_one("#main-switcher").current = "home-view"

    # --- TASK DISPATCHERS ---
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-upload-start": self.run_worker(self.upload_task())
        elif event.button.id == "btn-docs-gen": self.run_worker(self.docs_task())
        elif event.button.id == "btn-switch-context": self.switch_context()
        elif event.button.id == "btn-scroll-up": self.query_one("#chat-log").scroll_up()
        elif event.button.id == "btn-scroll-down": self.query_one("#chat-log").scroll_down()
        elif event.button.id == "btn-diag-start": self.run_worker(self.diagnostic_task())
        # ... (Add remaining button handlers as needed)

    async def gather_context_async(self):
        return f"PATH: {os.getcwd()}\nFILES: {os.listdir('.')[:20]}"

    def launch_cli_fallback(self, mode):
        # Professional Suspend for remaining CLI-only advanced logic
        with self.suspend():
            os.system('clear')
            print(f"Launching Advanced {mode} Interface...")
            input("\nPress Enter to return...")

def run_tui():
    PyGitUpTUI().run()
