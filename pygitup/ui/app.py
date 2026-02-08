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
    #project-log { height: 10; border: solid #30363d; background: #010409; color: #7d8590; padding: 0 1; overflow-y: scroll; }
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
                    Static(f"[dim italic]Context: {os.getcwd()}[/dim italic]", id="chat-context-label"),
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
                                Button("COMMENT", id="btn-pr-comment"),
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

    # --- CLASS METHODS ---
    def action_scroll_chat_up(self):
        self.query_one("#chat-log").scroll_up()
    
    def action_scroll_chat_down(self):
        self.query_one("#chat-log").scroll_down()

    def run_mentor_view(self):
        self.query_one("#main-switcher").current = "mentor-view"
        self.query_one("#chat-input").focus()
        if not self.chat_history:
             self.query_one("#chat-log").write(RichMarkdown("# Neural Code Mentor Initialized\nI am ready to analyze your code."))

    def run_project_view(self):
        self.query_one("#main-switcher").current = "project-view"
        self.query_one("#up-path").value = os.getcwd()
        self.query_one("#up-name").value = os.path.basename(os.getcwd())

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "chat-input":
            query = event.value; event.input.value = ""
            self.query_one("#chat-loader").add_class("-loading")
            self.chat_history.append({"role": "user", "text": query})
            self.query_one("#chat-log").write(RichMarkdown(f"---\n\n👤 **You**\n{query}"))
            self.run_worker(self.mentor_task(query))

    def update_chat_ui(self):
        # Fallback if needed, but RichLog handles incremental writes better.
        pass

    async def mentor_task(self, query):
        ctx = await self.gather_context_async()
        config = load_config(); ai_key = config["github"].get("ai_api_key")
        from ..utils.ai import code_mentor_chat
        from ..utils.agent_tools import execute_agent_tool
        
        while True:
            # 1. Call Agent
            resp = code_mentor_chat(ai_key, query, ctx, history=self.chat_history)
            
            # Update history with the agent's turn (text and/or tool calls)
            agent_msg = {"role": "model", "text": resp['text'], "tool_calls": resp['tool_calls']}
            self.chat_history.append(agent_msg)
            
            # Show response text if any
            if resp['text']:
                self.query_one("#chat-log").write(RichMarkdown(f"---\n\n🤖 **Sentinel Agent**\n{resp['text']}"))
            
            # 2. Check for Tool Calls
            if not resp['tool_calls']:
                break # Goal achieved or just chatting
            
            # Handle Tool Calls (Sequentially for safety)
            tool_results = []
            for tc in resp['tool_calls']:
                # UI Approval Prompt (Native TUI style)
                self.query_one("#chat-log").write(RichMarkdown(f"⚠️ **ACTION REQUESTED:** `{tc['name']}`\nArgs: `{tc['args']}`"))
                
                # For this iteration, we auto-approve for speed, 
                # but we'll add a 'PAUSE' mechanism in the next refinement.
                # Let's log execution:
                self.query_one("#chat-log").write(RichMarkdown(f"*⚙️ Executing {tc['name']}...*"))
                
                result = execute_agent_tool(tc['name'], tc['args'])
                tool_results.append({"name": tc['name'], "content": result})
                
                # Show snippet of result
                display_res = (result[:200] + '...') if len(result) > 200 else result
                self.query_one("#chat-log").write(RichMarkdown(f"✅ **Result:**\n```\n{display_res}\n```"))

            # Update history with results
            self.chat_history.append({"role": "user", "text": "", "tool_results": tool_results})
            
            # Loop back to let the agent process the tool results
            query = "Proceed based on tool results."

        self.query_one("#chat-loader").remove_class("-loading")

    async def gather_context_async(self):
        cwd = os.getcwd()
        context = f"CURRENT PROJECT PATH: {cwd}\n\nProject Structure:\n"
        for root, _, files in os.walk("."):
            if any(x in root for x in [".git", "node_modules", "venv", "dist"]): continue
            for f in files: context += f"{root}/{f}\n"
        priority = ["main.py", "setup.py", "requirements.txt", "pygitup/ui/app.py"]
        for p in priority:
            if os.path.exists(p):
                try:
                    with open(p, 'r', encoding='utf-8', errors='ignore') as f: 
                        context += f"\n\n--- MODULE ANALYSIS: {p} ---\n" + "".join(f.readlines()[:200])
                except Exception: continue
        return context

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-scan": self.run_sast_scan()
        elif event.button.id == "btn-upload-start": self.run_worker(self.upload_task())
        elif event.button.id == "btn-release-start": self.run_worker(self.release_task())
        elif event.button.id == "btn-gist-create": self.run_worker(self.create_gist_task())
        elif event.button.id == "btn-gist-mode-create": self.query_one("#gist-switcher").current = "gist-create-view"
        elif event.button.id == "btn-gist-mode-list": 
            self.query_one("#gist-switcher").current = "gist-list-view"
            self.run_worker(self.list_gists_task())
        elif event.button.id == "btn-ssh-gen": self.run_worker(self.ssh_task())
        elif event.button.id == "btn-docs-gen": self.run_worker(self.docs_task())
        elif event.button.id == "btn-diag-start": self.run_worker(self.diagnostic_task())
        elif event.button.id == "btn-pr-mode-list":
            self.query_one("#pr-switcher").current = "pr-list-view"
            self.run_worker(self.list_prs_task())
        elif event.button.id == "btn-pr-mode-create":
            self.query_one("#pr-switcher").current = "pr-create-view"
        elif event.button.id == "btn-pr-create": self.run_worker(self.create_pr_task())
        elif event.button.id in ["btn-pr-merge", "btn-pr-close", "btn-pr-comment"]:
            self.run_worker(self.manage_pr_task(event.button.id))
        elif event.button.id == "btn-switch-context": self.switch_context()
        elif event.button.id == "btn-analyze": self.launch_cli_fallback("ai-commit")
        elif event.button.id == "btn-scroll-up": self.action_scroll_chat_up()
        elif event.button.id == "btn-scroll-down": self.action_scroll_chat_down()
        elif event.button.id.startswith("tpl-"):
            tpl_map = {"tpl-fastapi": "fastapi-pro", "tpl-node": "express-node", "tpl-cli": "cli-python"}
            self.launch_cli_fallback(f"template --template {tpl_map[event.button.id]}")

    async def upload_task(self):
        path = self.query_one("#up-path").value
        name = self.query_one("#up-name").value
        desc = self.query_one("#up-desc").value
        private = self.query_one("#up-private").value
        log_widget = self.query_one("#project-log")
        messages = ["[bold cyan]Starting Deployment Sequence...[/bold cyan]"]
        log_widget.update("\n".join(messages))

        def add_log(msg):
            messages.append(f"> {msg}")
            log_widget.update("\n".join(messages))
        
        is_v, err = validate_file_path(path)
        if not is_v: add_log(f"[red]Error: {err}[/red]"); return
        add_log("Initiating Security Sentinel...")
        results = run_local_sast_scan(path)
        if results: add_log(f"[yellow]Warning: {len(results)} potential vulnerabilities detected.[/yellow]")
        else: add_log("[green]Security scan passed.[/green]")

        try:
            add_log("Synchronizing local Git state...")
            os.chdir(path)
            if not os.path.isdir(".git"):
                subprocess.run(["git", "init"], check=True, capture_output=True)
                add_log("Initialized Git repository.")
            subprocess.run(["git", "add", "."], check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", "Initial commit via PyGitUp TUI"], capture_output=True)
            add_log("Local changes committed.")
        except Exception as e: add_log(f"[red]Git Error: {e}[/red]"); return

        add_log("Contacting GitHub Command Center...")
        config = load_config(); user = get_github_username(config); token = get_github_token(config)
        from ..github.api import create_repo, get_repo_info
        repo_resp = get_repo_info(user, name, token)
        if repo_resp.status_code == 200: add_log("Repository exists. Connecting...")
        else:
            add_log(f"Creating {'private' if private else 'public'} repository...")
            create_repo(user, name, token, description=desc, private=private)
        
        try:
            add_log("Pushing to Cloud...")
            remote_url = f"https://{user}:{token}@github.com/{user}/{name}.git"
            subprocess.run(["git", "remote", "remove", "origin"], capture_output=True)
            subprocess.run(["git", "remote", "add", "origin", remote_url], check=True, capture_output=True)
            subprocess.run(["git", "branch", "-M", "main"], check=True, capture_output=True)
            subprocess.run(["git", "push", "-u", "--force", "origin", "main"], check=True, capture_output=True)
            add_log("[bold green]DEPLOYMENT SUCCESSFUL! 🚀[/bold green]")
            self.notify("Project Uploaded Successfully")
        except Exception as e: add_log(f"[red]Cloud Error: {e}[/red]")

    def switch_context(self):
        new_path = self.query_one("#target-dir-input").value
        lbl = self.query_one("#lbl-current-target")
        if os.path.isdir(new_path):
            try:
                os.chdir(new_path)
                self.target_dir = new_path
                lbl.update(f"Current: [bold green]{new_path}[/bold green]")
                self.notify(f"Context Switched to: {os.path.basename(new_path)}")
                
                # Update Mentor Context Label if visible
                try: self.query_one("#chat-context-label").update(f"[dim italic]Context: {new_path}[/dim italic]")
                except: pass
                
            except Exception as e:
                self.notify(f"Error: {e}", severity="error")
        else:
            self.notify("Invalid Directory", severity="error")

    def run_osint_view(self):
        self.query_one("#main-switcher").current = "osint-view"
        self.run_worker(self.fetch_intel_task())

        async def fetch_intel_task(self):

            owner, repo = get_current_repo_context()

            if not owner or not repo:

                self.query_one("#intel-report").update("## ❌ Context Error"); return

            config = load_config(); token = get_github_token(config)

            try:

                resp = get_repo_info(owner, repo, token)

                if resp.status_code == 200:

                    data = resp.json(); health = get_repo_health_metrics(owner, repo, token)

                    

                    # Scrape Deep Intel

                    from ..utils.scraper import scrape_repo_info

                    scraped = scrape_repo_info(f"https://github.com/{owner}/{repo}")

                    

                    md = f"# 🛰️ Intelligence: {owner}/{repo}\n\n"

                    md += f"| Metric | Value |\n| --- | --- |\n"

                    md += f"| ⭐ Stars | {data.get('stargazers_count')} |\n"

                    md += f"| 🚑 Health | {health.get('activity_status', 'N/A')} |\n"

                    

                    if scraped:

                        if scraped.get('social_links'):

                            md += "\n## 🌐 Digital Footprint\n"

                            for platform, url in scraped['social_links'].items():

                                md += f"- **{platform}:** {url}\n"

                        

                        if scraped.get('used_by'):

                            md += f"\n- **Used By:** {scraped['used_by']} repositories\n"

                    

                    self.query_one("#intel-report").update(md)

            except Exception: pass

    def run_analytics_view(self):
        self.query_one("#main-switcher").current = "analytics-view"
        self.run_worker(self.fetch_analytics_task())

    async def fetch_analytics_task(self):
        owner, repo = get_current_repo_context()
        if not owner or not repo: return
        config = load_config(); token = get_github_token(config)
        try:
            resp = get_repo_info(owner, repo, token)
            if resp.status_code == 200:
                data = resp.json(); proj = predict_growth_v2(data['stargazers_count'], data['created_at'], data['forks_count'])
                self.query_one("#analytics-report").update(f"# 📈 Momentum: {repo}\n\n- Projected Star Goal: {proj} 🌟")
        except Exception: pass

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

    def run_release_view(self):
        self.query_one("#main-switcher").current = "release-view"
        # Try to auto-suggest version
        try:
            latest = subprocess.run(["git", "describe", "--tags", "--abbrev=0"], capture_output=True, text=True).stdout.strip()
            if latest:
                self.query_one("#rel-notes").value = f"Changes since {latest}..."
        except: pass

    async def release_task(self):
        tag = self.query_one("#rel-tag").value
        name = self.query_one("#rel-name").value
        notes = self.query_one("#rel-notes").value
        log = self.query_one("#release-log")
        
        if not tag: log.update("[red]Error: Version Tag is required.[/red]"); return
        
        log.update("[cyan]Contacting GitHub...[/cyan]")
        
        config = load_config(); user = get_github_username(config); token = get_github_token(config)
        owner, repo = get_current_repo_context()
        
        if not owner or not repo: log.update("[red]Error: No active repository context.[/red]"); return
        
        from ..github.api import create_release
        resp = create_repo_release = create_release(owner, repo, token, tag, name, notes) # Using direct API import
        
        if resp.status_code == 201:
            log.update(f"[bold green]SUCCESS! Release {tag} published.[/bold green]\nURL: {resp.json()['html_url']}")
            self.notify(f"Release {tag} Created")
        else:
            log.update(f"[red]Failed: {resp.status_code} - {resp.text}[/red]")
    
    def run_gist_view(self):
        self.query_one("#main-switcher").current = "gist-view"

    async def create_gist_task(self):
        fname = self.query_one("#gist-file").value
        desc = self.query_one("#gist-desc").value
        content = self.query_one("#gist-content").value
        public = self.query_one("#gist-public").value
        log = self.query_one("#gist-log")
        
        if not fname or not content:
            log.update("[red]Error: Filename and Content are required.[/red]")
            return
            
        log.update("[cyan]Creating Gist...[/cyan]")
        config = load_config(); token = get_github_token(config)
        
        # Manually construct payload to avoid CLI wizard
        from ..github.api import github_request
        data = {
            "description": desc,
            "public": public,
            "files": { fname: { "content": content } }
        }
        
        try:
            resp = github_request("POST", "https://api.github.com/gists", token, json=data)
            if resp.status_code == 201:
                url = resp.json()['html_url']
                log.update(f"[bold green]Gist Created![/bold green]\n{url}")
                self.notify("Gist Created Successfully")
            else:
                log.update(f"[red]Failed: {resp.status_code}[/red]")
        except Exception as e:
            log.update(f"[red]Error: {e}[/red]")

    async def list_gists_task(self):
        table = self.query_one("#gist-table", DataTable)
        table.clear()
        config = load_config(); token = get_github_token(config); user = get_github_username(config)
        
        from ..github.api import github_request
        try:
            resp = github_request("GET", f"https://api.github.com/users/{user}/gists", token)
            if resp.status_code == 200:
                for g in resp.json():
                    fname = list(g['files'].keys())[0] if g['files'] else "N/A"
                    vis = "Public" if g['public'] else "Secret"
                    table.add_row(fname, g['description'] or "", vis, g['html_url'])
            else:
                self.notify(f"Failed to fetch gists: {resp.status_code}", severity="error")
        except: pass

    def run_ssh_view(self):
        self.query_one("#main-switcher").current = "ssh-view"
        # Check for key existence
        key_path = os.path.expanduser("~/.ssh/pygitup_id_rsa.pub")
        if os.path.exists(key_path):
            self.query_one("#ssh-status-view").update(f"✅ **Key Found:** `{key_path}`\n\nReady to upload.")
        else:
            self.query_one("#ssh-status-view").update("❌ **No Key Found**\n\nClick generate to create one.")

    async def ssh_task(self):
        log = self.query_one("#ssh-log")
        log.update("[cyan]Generating Key...[/cyan]")
        
        config = load_config(); token = get_github_token(config)
        email = config["github"].get("email") or "pygitup@user"
        
        from ..utils.security import generate_ssh_key
        from ..github.api import upload_ssh_key
        
        pub_key, path = generate_ssh_key(email)
        if not pub_key:
            log.update("[red]Key Generation Failed[/red]")
            return
            
        log.update("[cyan]Uploading to GitHub...[/cyan]")
        title = f"PyGitUp Key - {os.uname().nodename}"
        resp = upload_ssh_key(token, title, pub_key)
        
        if resp.status_code == 201:
            log.update("[bold green]SUCCESS! Key uploaded.[/bold green]")
            self.notify("SSH Key Uploaded")
            self.run_ssh_view() # Refresh status
        elif resp.status_code == 422:
            log.update("[yellow]Key already exists on GitHub.[/yellow]")
        else:
            log.update(f"[red]Upload Failed: {resp.status_code}[/red]")

    def run_docs_view(self):
        self.query_one("#main-switcher").current = "docs-view"

    def run_diagnostic_view(self):
        self.query_one("#main-switcher").current = "diagnostic-view"

    async def diagnostic_task(self):
        cmd = self.query_one("#diag-cmd").value
        log = self.query_one("#diag-log")
        if not cmd: return
        
        log.update(f"[cyan]Executing: {cmd}...[/cyan]")
        config = load_config()
        from ..utils.ai import ai_diagnostics_workflow
        # Pass the TUI log context if we want to stream, but for now we call the workflow
        result = ai_diagnostics_workflow(config, cmd)
        
        if isinstance(result, str):
             log.update(f"[bold red]Healing Proposal:[/bold red]\n{result}")
        elif result is True:
             log.update("[bold green]Verification Passed![/bold green]")
        else:
             log.update("[yellow]Diagnostic complete. No healing suggested.[/yellow]")

    async def docs_task(self):
        log = self.query_one("#docs-log")
        log.update("[cyan]Generating Documentation...[/cyan]")
        
        # Collect choices
        docs_map = {
            "README.md": self.query_one("#doc-readme").value,
            "CONTRIBUTING.md": self.query_one("#doc-contrib").value,
            "CODE_OF_CONDUCT.md": self.query_one("#doc-coc").value,
            "SECURITY.md": self.query_one("#doc-sec").value,
            "LICENSE": self.query_one("#doc-lic").value,
        }
        
        generated = []
        for name, active in docs_map.items():
            if active:
                # Basic generation logic (Mock for TUI - implies 'touch' or basic template)
                # Ideally this calls into project/docs.py logic
                if not os.path.exists(name):
                    with open(name, "w") as f: f.write(f"# {name}\n\nGenerated by PyGitUp.")
                    generated.append(name)
        
        if generated:
            log.update(f"[bold green]Created: {', '.join(generated)}[/bold green]")
            self.notify(f"{len(generated)} Files Generated")
        else:
            log.update("[yellow]No new files created (already exist or none selected).[/yellow]")

    def run_pr_view(self):
        self.query_one("#main-switcher").current = "pr-view"
        self.run_worker(self.list_prs_task())

    async def list_prs_task(self):
        table = self.query_one("#pr-table", DataTable)
        table.clear()
        config = load_config(); token = get_github_token(config)
        owner, repo = get_current_repo_context()
        if not owner or not repo: return
        
        from ..github.api import get_pull_requests
        try:
            resp = get_pull_requests(owner, repo, token)
            if resp.status_code == 200:
                for pr in resp.json():
                    table.add_row(str(pr['number']), pr['title'], pr['head']['ref'], pr['base']['ref'])
            else:
                self.notify("Failed to fetch PRs", severity="error")
        except: pass

    async def create_pr_task(self):
        title = self.query_one("#pr-title").value
        head = self.query_one("#pr-head").value
        base = self.query_one("#pr-base").value
        body = self.query_one("#pr-body").value
        log = self.query_one("#pr-log")
        
        if not title or not head or not base:
            log.update("[red]Error: Title, Head, and Base are required.[/red]")
            return
            
        log.update("[cyan]Submitting Pull Request...[/cyan]")
        config = load_config(); token = get_github_token(config)
        owner, repo = get_current_repo_context()
        
        from ..github.api import create_pull_request
        try:
            resp = create_pull_request(owner, repo, token, title, head, base, body)
            if resp.status_code == 201:
                log.update(f"[bold green]PR Created successfully![/bold green]\n{resp.json()['html_url']}")
                self.notify("Pull Request Created")
            else:
                log.update(f"[red]Failed: {resp.status_code} - {resp.text}[/red]")
        except Exception as e:
            log.update(f"[red]Error: {e}[/red]")

    async def manage_pr_task(self, btn_id):
        table = self.query_one("#pr-table", DataTable)
        # Get selected row number
        try:
            row_idx = table.cursor_row
            row_data = table.get_row_at(row_idx)
            pr_num = row_data[0]
        except:
            self.notify("No PR selected", severity="warning")
            return

        config = load_config(); token = get_github_token(config)
        owner, repo = get_current_repo_context()
        from ..github.api import github_request
        
        if btn_id == "btn-pr-merge":
            url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_num}/merge"
            resp = github_request("PUT", url, token)
            if resp.status_code == 200: self.notify(f"PR #{pr_num} Merged"); self.run_worker(self.list_prs_task())
            else: self.notify(f"Merge Failed: {resp.status_code}", severity="error")
            
        elif btn_id == "btn-pr-close":
            url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_num}"
            resp = github_request("PATCH", url, token, json={"state": "closed"})
            if resp.status_code == 200: self.notify(f"PR #{pr_num} Closed"); self.run_worker(self.list_prs_task())
            else: self.notify(f"Close Failed", severity="error")
            
        elif btn_id == "btn-pr-comment":
            # For simplicity, we use a prompt here or a dedicated modal later
            # For now, let's notify. Implementing a dynamic comment input in TUI is next.
            self.notify("Comment feature coming soon to TUI", severity="information")

    def action_go_home(self): self.query_one("#main-switcher").current = "home-view"

    def launch_cli_fallback(self, mode):
        from ..github.ssh_ops import setup_ssh_infrastructure
        from ..utils.ai import ai_commit_workflow
        from ..github.releases import create_release_tag
        from ..github.pull_requests import manage_pull_requests
        from ..github.gists import manage_gists
        from ..project.docs import generate_documentation
        
        config = load_config(); user = get_github_username(config); token = get_github_token(config)
        actual_mode = mode.split(" ")[0]
        
        with self.suspend():
            os.system('cls' if os.name == 'nt' else 'clear')
            try:
                if actual_mode == "ai-commit": ai_commit_workflow(user, token, config)
                elif actual_mode == "ssh": setup_ssh_infrastructure(config, token)
                elif actual_mode == "release": create_release_tag(user, token, config)
                elif actual_mode == "pr": manage_pull_requests(None, user, token) # Args handled inside or None
                elif actual_mode == "gist": manage_gists(None, user, token)
                elif actual_mode == "generate-docs": generate_documentation(user, token, config)
                
                input("\nPress Enter to return to TUI Dashboard...")
            except Exception as e: print(f"Error: {e}"); input("Press Enter...")

def run_tui():
    PyGitUpTUI().run()
