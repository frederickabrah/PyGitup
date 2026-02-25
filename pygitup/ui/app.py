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
import difflib
import asyncio

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
    
    TITLE = "PyGitUp Dashboard"
    SUB_TITLE = f"v{__version__}"
    chat_history = [] 
    target_dir = os.getcwd()
    pending_tool = None
    is_online = True
    agent_busy = False
    user_signal = asyncio.Event()
    user_response = None

    CSS = """
    Screen { background: #0d1117; color: #c9d1d9; }
    #sidebar { 
        width: 30%; 
        background: #161b22; 
        border-right: tall #30363d; 
        transition: width 300ms in_out_cubic;
    }
    #sidebar.collapsed {
        width: 0%;
        display: none;
    }
    #main-switcher { width: 100%; padding: 1 2; }
    .category-header { 
        background: #21262d; 
        color: #58a6ff; 
        text-style: bold; 
        width: 100%;
        text-align: center;
        margin-top: 1;
    }
    #status-bar { height: 1; background: #21262d; color: #8b949e; text-align: center; }
    .online { color: #3fb950; }
    .offline { color: #f85149; }
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
    #project-log, #release-log, #gist-log, #docs-log, #diag-log, #pr-log, #market-log { 
        height: 10; border: solid #30363d; background: #010409; color: #7d8590; padding: 0 1; overflow-y: scroll; 
    }
    .scroll-btn { min-width: 5; width: 10%; margin-left: 1; }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("escape", "go_home", "Home", show=True),
        Binding("r", "refresh", "Sync", show=True),
        Binding("b", "toggle_sidebar", "Sidebar", show=True),
        Binding("ctrl+l", "clear_chat", "Clear Chat", show=True),
        Binding("ctrl+up", "scroll_chat_up", "Scroll Up", show=False),
        Binding("ctrl+down", "scroll_chat_down", "Scroll Down", show=False),
        Binding("1", "switch_view('home')", "Home", show=False),
        Binding("2", "switch_view('mentor')", "AI", show=False),
        Binding("3", "switch_view('osint')", "Stats", show=False),
        Binding("4", "switch_view('security')", "Security", show=False),
        Binding("f1", "show_help", "Help", show=True),
    ]

    def action_switch_view(self, view: str) -> None:
        """Quick-switch views via hotkeys."""
        views = {
            "home": "home-view",
            "mentor": "mentor-view",
            "osint": "osint-view",
            "security": "security-view"
        }
        if view in views:
            self.query_one("#main-switcher").current = views[view]
            if view == "mentor": self.query_one("#chat-input").focus()

    def action_show_help(self) -> None:
        """Displays a technical help overlay."""
        self.notify("PyGitUp Dashboard: Use 1-4 for quick nav, B for sidebar, Ctrl+L to reset AI.", title="Technical Guide", severity="information")

    def compose(self) -> ComposeResult:
        active_profile = os.path.basename(get_active_profile_path()).replace(".yaml", "")
        yield Header(show_clock=True)
        yield Static("Checking connectivity...", id="status-bar")
        yield Horizontal(
            Vertical(
                Label(f" 👤 PROFILE: {active_profile.upper()} ", classes="category-header", id="profile-label"),
                ScrollableContainer(
                    ListView(
                        HeaderItem("AI ENGINEERING"),
                        FeatureItem("AI Assistant", "mentor", "AI", "Autonomous task execution and file management."),
                        FeatureItem("Diagnostic Tool", "ai-diagnostic", "AI", "Run commands and analyze failures."),
                        FeatureItem("Commit Assistant", "ai-lab", "AI", "Automated diff analysis and commit generation."),
                        HeaderItem("DATA ANALYSIS"),
                        FeatureItem("Repo Dashboard", "osint", "GitHub", "Repository metadata and statistics."),
                        FeatureItem("Analytics", "analytics", "Data", "Growth trends and health scoring."),
                        HeaderItem("SECURITY"),
                        FeatureItem("Static Scan (SAST)", "security", "Security", "Local vulnerability scanning."),
                        FeatureItem("Profile Manager", "identity", "Auth", "Manage account profiles."),
                        FeatureItem("SSH Manager", "ssh", "Auth", "Automated SSH configuration."),
                        HeaderItem("REPOSITORY OPS"),
                        FeatureItem("Project Upload", "project", "Core", "Repository initialization and push."),
                        FeatureItem("Marketplace", "marketplace", "Core", "Deploy project templates."),
                        HeaderItem("ADVANCED GIT OPS"),
                        FeatureItem("Universal Search", "search", "Tools", "Global code and text pattern search."),
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
                        Input(placeholder="my-repository", id="up-name", classes="form-input"),
                        Label("Description:", classes="form-label"),
                        Input(placeholder="Repository description...", id="up-desc", classes="form-input"),
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
                        Static("[bold cyan]Status: Idle[/bold cyan]", id="chat-mission-label"),
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
                    Static("🛠️ DIAGNOSTIC TOOL", classes="title-banner"),
                    Label("Command to Verify (e.g. pytest):", classes="form-label"),
                    Input(placeholder="python3 -m pytest", id="diag-cmd", classes="form-input"),
                    Button("RUN & ANALYZE", id="btn-diag-start", variant="primary"),
                    Static("", id="diag-log"),
                    id="diagnostic-view"
                ),
                Vertical(
                    Static("🧠 COMMIT ASSISTANT", classes="title-banner"),
                    RichLog(id="ai-diff-log", highlight=True, markup=True),
                    Horizontal(
                        Input(placeholder="Commit Message... (Click Generate)", id="ai-commit-msg", classes="form-input"),
                        Button("GENERATE", id="btn-ai-gen", variant="primary"),
                        Button("COMMIT", id="btn-ai-commit", variant="success"),
                        classes="btn-row"
                    ),
                    Static("", id="ai-lab-log"),
                    id="ai-lab-view"
                ),
                Vertical(
                    Static("📊 ANALYTICS", classes="title-banner"),
                    Markdown("", id="analytics-report"),
                    id="analytics-view"
                ),
                Vertical(
                    Static("🛡️ STATIC SCAN (SAST)", classes="title-banner"),
                    DataTable(id="security-table"),
                    Horizontal(Button("Run Security Scan", variant="primary", id="btn-scan"), classes="btn-row"),
                    id="security-view"
                ),
                Vertical(
                    Static("🏗️ PROJECT TEMPLATES", classes="title-banner"),
                    Grid(
                        Button("FastAPI Pro", id="tpl-fastapi"),
                        Button("Express Node", id="tpl-node"),
                        Button("Python CLI", id="tpl-cli"),
                        id="marketplace-grid"
                    ),
                    Static("", id="market-log"),
                    id="marketplace-view"
                ),
                Vertical(
                    Static("🔐 PROFILE MANAGER", classes="title-banner"),
                    ListView(id="profile-list"),
                    id="identity-view"
                ),
                Vertical(
                    Static("🚀 RELEASE MANAGER", classes="title-banner"),
                    ScrollableContainer(
                        Label("Version Tag (e.g. v1.0.0):", classes="form-label"),
                        Input(placeholder="v1.0.0", id="rel-tag", classes="form-input"),
                        Label("Release Title:", classes="form-label"),
                        Input(placeholder="Version 1.0.0 Release", id="rel-name", classes="form-input"),
                        Label("Release Notes (Markdown supported):", classes="form-label"),
                        Input(placeholder="- Change log entry", id="rel-notes", classes="form-input"),
                        Button("PUBLISH RELEASE", variant="primary", id="btn-release-start"),
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
                            Horizontal(Label("[bold]Public? [/bold]"), Switch(value=False, id="gist-public"), classes="btn-row"),
                            Button("CREATE GIST", variant="primary", id="btn-gist-create"),
                            Static("", id="gist-log"),
                            id="gist-create-view"
                        ),
                        Vertical(DataTable(id="gist-table"), id="gist-list-view"),
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
                        Static("", id="docs-log"),
                    ),
                    id="docs-view"
                ),
                Vertical(
                    Static("🔍 UNIVERSAL SEARCH", classes="title-banner"),
                    Label("Search Pattern (Code/Text):", classes="form-label"),
                    Input(placeholder="function_name or 'TODO'", id="search-query", classes="form-input"),
                    Button("EXECUTE GLOBAL SEARCH", id="btn-search-start", variant="primary"),
                    DataTable(id="search-results-table"),
                    id="search-view"
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
                            Input(placeholder="feat: implement feature description", id="pr-title", classes="form-input"),
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
        self.query_one("#search-results-table", DataTable).add_columns("File")
        
        # UX: Adaptive Sidebar (Collapse on small screens)
        if self.size.width < 80:
            self.query_one("#sidebar").add_class("collapsed")

        # UX: Restore previous session if exists
        self.load_chat_session()
        
        # Start connectivity monitor
        self.set_interval(30, self.update_status_bar)

    def action_toggle_sidebar(self) -> None:
        """Toggles the sidebar visibility."""
        sidebar = self.query_one("#sidebar")
        if sidebar.has_class("collapsed"):
            sidebar.remove_class("collapsed")
        else:
            sidebar.add_class("collapsed")

    def action_clear_chat(self) -> None:
        """Clears the chat history and log."""
        self.chat_history = []
        self.save_chat_session()
        log = self.query_one("#chat-log")
        log.clear()
        log.write(RichMarkdown("# Chat Cleared"))
        self.notify("Chat history cleared")

    def save_chat_session(self):
        """Persists the current chat history to disk with secret scrubbing."""
        try:
            config_dir = os.path.join(os.path.expanduser("~"), ".pygitup_config")
            session_file = os.path.join(config_dir, "last_session.json")
            
            # Scrub sensitive data before saving
            import copy
            scrubbed_history = copy.deepcopy(self.chat_history)
            token_pattern = r'(ghp_|github_pat_|gho_|ghu_|ghs_|ghr_)[a-zA-Z0-9_]{16,}'
            
            for msg in scrubbed_history:
                if msg.get('text'):
                    msg['text'] = re.sub(token_pattern, "[REDACTED TOKEN]", msg['text'])
            
            with open(session_file, 'w') as f:
                json.dump(scrubbed_history, f, indent=2)
        except Exception: pass

    def load_chat_session(self):
        """Loads the previous chat history from disk."""
        try:
            config_dir = os.path.join(os.path.expanduser("~"), ".pygitup_config")
            session_file = os.path.join(config_dir, "last_session.json")
            if os.path.exists(session_file):
                with open(session_file, 'r') as f:
                    self.chat_history = json.load(f)
                
                # Render history to log
                log = self.query_one("#chat-log")
                log.write(RichMarkdown("# ⏳ Session Restored"))
                for msg in self.chat_history:
                    role = "You" if msg['role'] == 'user' else "AI Assistant"
                    if msg.get('text'):
                        # Strip thought tags for history display to keep it clean
                        import re
                        display_text = re.sub(r'<thought>.*?</thought>', '', msg['text'], flags=re.DOTALL).strip()
                        if display_text:
                            log.write(RichMarkdown(f"---\n**{role}**\n{display_text}"))
        except Exception: pass

    async def update_status_bar(self):
        """Monitors connectivity in a non-blocking worker."""
        self.run_worker(self.check_connectivity())

    async def check_connectivity(self):
        import requests
        from ..github.api import check_rate_limit
        from ..core.config import get_github_token
        is_up = False
        rate_limit_str = ""
        
        # 1. Fetch Rate Limit (Internal data)
        config = load_config()
        token = get_github_token(config)
        if token:
            rl = check_rate_limit(token)
            if rl:
                rate_limit_str = f" | 🔑 {rl.remaining}/{rl.limit}"

        # 2. Check targets
        for target in ["https://github.com", "https://google.com"]:
            try:
                # Use a very short timeout for responsiveness
                resp = requests.get(target, timeout=3)
                if resp.status_code < 400:
                    is_up = True
                    break
            except Exception:
                continue
        
        if is_up:
            self.is_online = True
            self.query_one("#status-bar").update(f"[bold][@click=app.sync]📡 ONLINE[/] | System Operational{rate_limit_str}[/bold]")
            self.query_one("#status-bar").set_classes("online")
        else:
            self.is_online = False
            self.query_one("#status-bar").update("[bold]🔌 OFFLINE[/bold] | Actions will be queued")
            self.query_one("#status-bar").set_classes("offline")

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.list_view.id == "feature-list" and event.item and isinstance(event.item, FeatureItem):
            if self.query_one("#main-switcher").current == "home-view":
                self.query_one("#home-desc").update(f"{event.item.description}\n\n[bold white]Press ENTER to activate.[/bold white]")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.list_view.id == "feature-list":
            if not isinstance(event.item, FeatureItem):
                return
            mode = event.item.mode
            if mode == "mentor":
                self.run_mentor_view()
            elif mode == "ai-diagnostic":
                self.run_diagnostic_view()
            elif mode == "ai-lab":
                self.run_ai_lab_view()
            elif mode == "project":
                self.run_project_view()
            elif mode == "osint":
                self.run_osint_view()
            elif mode == "analytics":
                self.run_analytics_view()
            elif mode == "security":
                self.run_security_view()
            elif mode == "identity":
                self.run_identity_view()
            elif mode == "marketplace":
                self.run_marketplace_view()
            elif mode == "release":
                self.run_release_view()
            elif mode == "gist":
                self.run_gist_view()
            elif mode == "ssh":
                self.run_ssh_view()
            elif mode == "generate-docs":
                self.run_docs_view()
            elif mode == "pr":
                self.run_pr_view()
            elif mode == "search":
                self.run_search_view()
            else:
                self.launch_cli_fallback(mode)
        elif event.list_view.id == "profile-list":
            if not event.item:
                return
            profile_name = str(event.item.query_one(Label).renderable).replace("🔑 ", "")
            success, msg = set_active_profile(profile_name)
            if success:
                self.notify(f"Switched to: {profile_name.upper()}")
                self.query_one("#profile-label").update(f" 👤 PROFILE: {profile_name.upper()} ")
            else:
                self.notify(msg, severity="error")

    def run_mentor_view(self): 
        self.query_one("#main-switcher").current = "mentor-view"
        self.query_one("#chat-input").focus()
        if not self.chat_history:
            self.query_one("#chat-log").write(RichMarkdown("# AI Assistant Initialized"))

    def run_diagnostic_view(self):
        self.query_one("#main-switcher").current = "diagnostic-view"

    def run_project_view(self):
        self.query_one("#main-switcher").current = "project-view"

    def run_osint_view(self):
        self.query_one("#main-switcher").current = "osint-view"
        self.run_worker(self.fetch_intel_task())

    def run_analytics_view(self):
        self.query_one("#main-switcher").current = "analytics-view"
        self.run_worker(self.fetch_analytics_task())

    def run_security_view(self):
        self.query_one("#main-switcher").current = "security-view"
    
    def run_identity_view(self):
        self.query_one("#main-switcher").current = "identity-view"
        p_list = self.query_one("#profile-list", ListView)
        p_list.clear()
        for p in list_profiles():
            p_list.append(ListItem(Label(f"🔑 {p}")))
    
    def run_marketplace_view(self):
        self.query_one("#main-switcher").current = "marketplace-view"

    def run_release_view(self):
        self.query_one("#main-switcher").current = "release-view"

    def run_gist_view(self):
        self.query_one("#main-switcher").current = "gist-view"
    
    def run_ssh_view(self):
        self.query_one("#main-switcher").current = "ssh-view"
        key_path = os.path.expanduser("~/.ssh/pygitup_id_rsa.pub")
        if os.path.exists(key_path):
            self.query_one("#ssh-status-view").update(f"✅ **Key Found:** `{key_path}`")
        else:
            self.query_one("#ssh-status-view").update("❌ **No Key Found**")

    def run_docs_view(self):
        self.query_one("#main-switcher").current = "docs-view"

    def run_pr_view(self):
        self.query_one("#main-switcher").current = "pr-view"
        self.run_worker(self.list_prs_task())

    def run_search_view(self):
        self.query_one("#main-switcher").current = "search-view"

    def action_go_home(self):
        self.query_one("#main-switcher").current = "home-view"

    def run_ai_lab_view(self):
        self.query_one("#main-switcher").current = "ai-lab-view"
        log = self.query_one("#ai-diff-log")
        log.clear()
        try:
            diff = subprocess.run(["git", "diff", "--cached"], capture_output=True, text=True).stdout
            if not diff:
                log.write("[yellow]No staged changes. Use 'git add' first.[/yellow]")
            else:
                log.write(RichMarkdown(f"### Staged Diff\n```diff\n{diff}\n```"))
        except Exception as e:
            log.write(f"[red]Error: {e}[/red]")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "target-dir-input":
            self.switch_context()
            return

        if event.input.id == "chat-input":
            query = event.value
            event.input.value = ""
            
            if not query.strip():
                return

            if self.agent_busy and not self.pending_tool:
                self.notify("AI is thinking...", severity="warning")
                return

            if self.pending_tool:
                # User is responding to a tool confirmation prompt
                self.user_response = query
                self.user_signal.set()
                return
            
            # Context Injection Processor (@file)
            import re
            processed_query = query
            file_matches = re.findall(r'@(\S+)', query)
            
            injected_context = ""
            if file_matches:
                for filename in file_matches:
                    if os.path.exists(filename) and os.path.isfile(filename):
                        try:
                            with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                # Safety truncation for large files
                                if len(content) > 15000:
                                    content = content[:15000] + "\n... [TRUNCATED FOR SPEED] ..."
                                injected_context += f"\n--- CONTENT OF {filename} ---\n{content}\n--- END OF {filename} ---\n"
                        except Exception as e:
                            injected_context += f"\n[Error reading {filename}: {e}]\n"
            
            if injected_context:
                processed_query += f"\n\n[USER CONTEXT INJECTION]:\n{injected_context}"
                self.query_one("#chat-log").write(RichMarkdown(f"📎 **Injected {len(file_matches)} file(s) into context.**"))

            # Start a new interaction - DO NOT append to history here, mentor_task handles it
            self.query_one("#chat-log").write(RichMarkdown(f"---\n👤 **You**\n{query}"))
            self.query_one("#chat-loader").add_class("-loading")
            self.agent_busy = True
            self.run_worker(self.mentor_task(processed_query))

    async def mentor_task(self, initial_query):
        from ..utils.ai import code_mentor_chat
        from ..utils.agent_tools import execute_agent_tool
        import re
        
        turn_count = 0
        max_turns = 10
        query = initial_query
        
        try:
            while turn_count < max_turns:
                turn_count += 1
                
                # Add current query to history (Initial query or 'Proceed' message)
                self.chat_history.append({"role": "user", "text": query})
                
                ctx = await self.gather_context_async()
                config = load_config()
                ai_key = config["github"].get("ai_api_key")
                
                # UX: Prune history to prevent context overflow (keep last 20 messages)
                self.chat_history = self.chat_history[-20:]
                
                # Pass history WITHOUT a redundant query parameter to ensure strict alternation
                resp = code_mentor_chat(ai_key, None, ctx, history=self.chat_history)
                agent_msg = {"role": "model", "text": resp['text'], "tool_calls": resp['tool_calls']}
                self.chat_history.append(agent_msg)
                
                # UX: Parse and render thoughts separately
                full_text = resp['text']
                thought_match = re.search(r'<thought>(.*?)</thought>', full_text, re.DOTALL)
                
                if thought_match:
                    thought = thought_match.group(1).strip()
                    main_response = full_text.replace(thought_match.group(0), "").strip()
                    self.query_one("#chat-log").write(RichMarkdown(f"> 🧠 **Agent Thought:**\n> *{thought}*"))
                    if main_response:
                        self.query_one("#chat-log").write(RichMarkdown(f"---\n🤖 **AI Assistant**\n{main_response}"))
                elif full_text:
                    self.query_one("#chat-log").write(RichMarkdown(f"---\n🤖 **AI Assistant**\n{full_text}"))
                
                # Persist Session after every turn
                self.save_chat_session()

                if not resp['tool_calls']:
                    break
                
                # UX: Communicate tool usage
                self.query_one("#chat-log").write(RichMarkdown(f"⚙️ **Agent is executing {len(resp['tool_calls'])} tool(s)...**"))

                for tc in resp['tool_calls']:
                    if tc['name'] in ["write_file", "patch_file", "run_shell", "github_issue", "ask_user"]:
                        # This logic handles tools that require user confirmation or extra input
                        self.pending_tool = tc
                        
                        # Special handling for ask_user: present question directly
                        if tc['name'] == "ask_user":
                            self.query_one("#chat-log").write(RichMarkdown(f"❓ **QUESTION:** {tc['args'].get('question')}"))
                            self.query_one("#chat-input").placeholder = "Type your answer..."
                        # Special handling for comments: Ask for the text
                        elif tc['name'] == "github_issue" and tc['args'].get('action') == "comment":
                            self.query_one("#chat-log").write(RichMarkdown(f"📝 **Comment required for Issue #{tc['args'].get('number')}**"))
                            self.query_one("#chat-input").placeholder = "Type your comment and press Enter..."
                        else:
                            # Show diff if applicable
                            if tc['name'] in ["write_file", "patch_file"]:
                                path = tc['args'].get('path')
                                new_content = tc['args'].get('content') or tc['args'].get('replace_text', "")
                                try:
                                    old_content = ""
                                    if os.path.exists(path):
                                        with open(path, 'r') as f:
                                            old_content = f.read()
                                    if tc['name'] == "patch_file":
                                        search = tc['args'].get('search_text')
                                        new_content = old_content.replace(search, new_content)
                                    diff = difflib.unified_diff(
                                        old_content.splitlines(), 
                                        new_content.splitlines(), 
                                        fromfile=f"a/{path}", 
                                        tofile=f"b/{path}", 
                                        lineterm=""
                                    )
                                    diff_text = "\n".join(list(diff))
                                    if diff_text:
                                        self.query_one("#chat-log").write(RichMarkdown(f"### 🔍 Proposed Changes for `{path}`\n```diff\n{diff_text}\n```"))
                                except Exception: pass
                            
                            self.query_one("#chat-log").write(RichMarkdown(f"⚠️ **APPROVAL REQUIRED:** `{tc['name']}`"))
                            self.query_one("#chat-input").placeholder = "Type 'y' to confirm or anything else to deny..."

                        # PAUSE: Wait for user to submit input via on_input_submitted
                        self.query_one("#chat-loader").remove_class("-loading")
                        self.user_signal.clear()
                        await self.user_signal.wait()
                        
                        user_val = self.user_response
                        self.user_response = None
                        self.pending_tool = None
                        self.query_one("#chat-input").placeholder = "Ask a technical question..."
                        self.query_one("#chat-loader").add_class("-loading")

                        # Process the user's choice
                        if tc['name'] == "ask_user":
                            result = {"response": user_val}
                            self.query_one("#chat-log").write(RichMarkdown(f"💬 **You:** {user_val}"))
                        elif tc['name'] == "github_issue" and tc['args'].get('action') == "comment":
                            tc['args']['body'] = user_val
                            result = execute_agent_tool(tc['name'], tc['args'])
                            self.query_one("#chat-log").write(RichMarkdown(f"💬 **Comment Posted**"))
                        elif user_val.lower() in ['y', 'yes']:
                            # Inform user about the safety net
                            if os.path.isdir(".git"):
                                self.query_one("#chat-log").write(RichMarkdown("🛡️ **Safety Checkpoint Created** (Restore via `git stash list`)"))
                            
                            self.query_one("#chat-log").write(RichMarkdown(f"✅ **APPROVED:** `{tc['name']}`"))
                            result = execute_agent_tool(tc['name'], tc['args'])
                        else:
                            self.query_one("#chat-log").write(RichMarkdown(f"❌ **DENIED:** `{tc['name']}`"))
                            result = {"error": "User denied action."}
                    else:
                        # Non-privileged tools: Execute immediately
                        result = execute_agent_tool(tc['name'], tc['args'])
                    
                    self.chat_history.append({"role": "user", "text": "", "tool_results": [{"name": tc['name'], "content": result}]})
                
                query = "Proceed with results."
        except Exception as e:
            self.query_one("#chat-log").write(RichMarkdown(f"❌ **Task Error:** {e}"))
        finally:
            self.agent_busy = False
            self.query_one("#chat-loader").remove_class("-loading")

    async def fetch_intel_task(self):
        owner, repo = get_current_repo_context()
        if not owner or not repo:
            return
        config = load_config()
        token = get_github_token(config)
        try:
            resp = get_repo_info(owner, repo, token)
            if resp.status_code == 200:
                data = resp.json()
                health = get_repo_health_metrics(owner, repo, token)
                from ..utils.scraper import scrape_repo_info
                scraped = scrape_repo_info(f"https://github.com/{owner}/{repo}")
                md = f"# 🛰️ Intelligence: {owner}/{repo}\n\n| Metric | Value |\n| --- | --- |\n| ⭐ Stars | {data.get('stargazers_count')} |\n| 🚑 Health | {health.get('activity_status', 'N/A')} |"
                if scraped and scraped.get('social_links'):
                    md += "\n## 🌐 Digital Footprint\n"
                    for platform, url in scraped['social_links'].items():
                        md += f"- **{platform}:** {url}\n"
                self.query_one("#intel-report").update(md)
        except Exception as e:
            self.query_one("#intel-report").update(f"## ⚠️ Intel Gathering Limited\n{e}")

    async def fetch_analytics_task(self):
        owner, repo = get_current_repo_context()
        if not owner or not repo:
            return
        config = load_config()
        token = get_github_token(config)
        try:
            resp = get_repo_info(owner, repo, token)
            if resp.status_code == 200:
                data = resp.json()
                proj = predict_growth_v2(data['stargazers_count'], data['created_at'], data['forks_count'])
                self.query_one("#analytics-report").update(f"# 📈 Momentum: {repo}\n\n- Projected Goal: {proj} 🌟")
        except Exception as e:
            self.query_one("#analytics-report").update(f"## ⚠️ Analytics Unavailable\n{e}")

    async def diagnostic_task(self):
        cmd = self.query_one("#diag-cmd").value
        if not cmd:
            return
        self.query_one("#diag-log").update(f"[cyan]Executing: {cmd}...[/cyan]")
        config = load_config()
        from ..utils.ai import ai_diagnostics_workflow
        result = ai_diagnostics_workflow(config, cmd)
        if isinstance(result, str):
            self.query_one("#diag-log").update(f"[red]Healing Proposal:[/red]\n{result}")
        elif result is True:
            self.query_one("#diag-log").update("[green]Passed![/green]")

    async def upload_task(self):
        path, name, desc = self.query_one("#up-path").value, self.query_one("#up-name").value, self.query_one("#up-desc").value
        private = self.query_one("#up-private").value
        log_widget = self.query_one("#project-log")
        messages = ["[bold cyan]Deployment Sequence...[/bold cyan]"]
        def add_log(msg):
            messages.append(f"> {msg}")
            log_widget.update("\n".join(messages))
        
        original_cwd = os.getcwd()
        try:
            os.chdir(path)
            subprocess.run(["git", "init"], check=True, capture_output=True)
            subprocess.run(["git", "add", "."], check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", "Deployment via PyGitUp", "--allow-empty"], capture_output=True)
            config = load_config()
            user, token = get_github_username(config), get_github_token(config)
            from ..github.api import create_repo, get_repo_info
            if get_repo_info(user, name, token).status_code != 200:
                create_repo(user, name, token, description=desc, private=private)
            subprocess.run(["git", "push", "-u", "--force", f"https://{token}@github.com/{user}/{name}.git", "main"], check=True, capture_output=True)
            add_log("[green]SUCCESS! 🚀[/green]")
            self.notify("Project Uploaded")
        except Exception as e:
            add_log(f"[red]Error: {e}[/red]")
        finally:
            os.chdir(original_cwd)

    async def docs_task(self):
        config = load_config()
        user, token = get_github_username(config), get_github_token(config)
        owner, repo = get_current_repo_context()
        from ..project.docs import core_generate_docs
        generated = core_generate_docs(config, repo, "docs", user, token)
        self.query_one("#docs-log").update(f"[green]Success! Generated: {len(generated)} files.[/green]")
        self.notify("Docs Generated")

    async def marketplace_task(self, btn_id):
        log = self.query_one("#market-log")
        tpl_map = {"tpl-fastapi": "fastapi-pro", "tpl-node": "express-node", "tpl-cli": "cli-python"}
        tpl_name = tpl_map.get(btn_id)
        if not tpl_name:
            return
        config = load_config()
        user, token = get_github_username(config), get_github_token(config)
        from ..project.templates import core_deploy_template
        success, msg = core_deploy_template(tpl_name, f"my-{tpl_name}", "Boilerplate", False, user, token, config)
        if success:
            log.update(f"[green]SUCCESS! {msg}[/green]")
            self.notify("Template Deployed")
        else:
            log.update(f"[red]Failed: {msg}[/red]")

    async def ai_gen_task(self):
        log = self.query_one("#ai-lab-log")
        config = load_config()
        ai_key = config["github"].get("ai_api_key")
        from ..utils.ai import get_git_diff, generate_ai_commit_message
        diff = get_git_diff()
        if diff:
            msg = generate_ai_commit_message(ai_key, diff)
            if msg:
                self.query_one("#ai-commit-msg").value = msg
                log.update("[green]Generated![/green]")
        else:
            log.update("[yellow]Nothing staged.[/yellow]")

    async def ai_commit_task(self):
        msg = self.query_one("#ai-commit-msg").value
        if msg:
            try:
                subprocess.run(["git", "commit", "-m", msg], check=True, capture_output=True)
                self.notify("Committed")
                self.run_ai_lab_view()
            except Exception as e:
                self.query_one("#ai-lab-log").update(f"[red]Error: {e}[/red]")

    async def search_task(self):
        query = self.query_one("#search-query").value
        table = self.query_one("#search-results-table", DataTable)
        table.clear()
        if not query:
            return
        self.notify(f"Searching for: {query}")
        from ..utils.agent_tools import search_code_tool
        result = search_code_tool(query)
        
        if isinstance(result, dict) and "matches" in result:
            matches = result["matches"]
            if not matches:
                self.notify("No matches found.", severity="warning")
            else:
                for line in matches:
                    table.add_row(line)
                self.notify(f"Search Complete ({result.get('method', 'unknown')})")
        elif isinstance(result, dict) and "error" in result:
            self.notify(f"Search Error: {result['error']}", severity="error")
        else:
            self.notify("Search Complete")

    async def release_task(self):
        tag, name, notes = self.query_one("#rel-tag").value, self.query_one("#rel-name").value, self.query_one("#rel-notes").value
        config = load_config()
        user, token = get_github_username(config), get_github_token(config)
        owner, repo = get_current_repo_context()
        from ..github.api import create_release
        resp = create_release(owner, repo, token, tag, name, notes)
        if resp.status_code == 201:
            self.notify("Release Created")

    async def create_gist_task(self):
        fname, desc, content = self.query_one("#gist-file").value, self.query_one("#gist-desc").value, self.query_one("#gist-content").value
        from ..github.api import github_request
        config = load_config()
        token = get_github_token(config)
        data = {"description": desc, "public": self.query_one("#gist-public").value, "files": {fname: {"content": content}}}
        if github_request("POST", "https://api.github.com/gists", token, json=data).status_code == 201:
            self.notify("Gist Created")

    async def list_gists_task(self):
        table = self.query_one("#gist-table", DataTable)
        table.clear()
        config = load_config()
        token, user = get_github_token(config), get_github_username(config)
        from ..github.api import github_request
        resp = github_request("GET", f"https://api.github.com/users/{user}/gists", token)
        if resp.status_code == 200:
            for g in resp.json():
                table.add_row(list(g['files'].keys())[0], g['description'] or "", "Public" if g['public'] else "Secret", g['html_url'])

    async def ssh_task(self):
        from ..utils.security import generate_ssh_key
        from ..github.api import upload_ssh_key
        config = load_config()
        token = get_github_token(config)
        pub_key, path = generate_ssh_key(config["github"].get("email", "pygitup@user"))
        if pub_key and upload_ssh_key(token, f"PyGitUp - {os.uname().nodename}", pub_key).status_code == 201:
            self.notify("SSH Key Uploaded")

    async def list_prs_task(self):
        table = self.query_one("#pr-table", DataTable)
        table.clear()
        config = load_config()
        token = get_github_token(config)
        owner, repo = get_current_repo_context()
        from ..github.api import get_pull_requests
        resp = get_pull_requests(owner, repo, token)
        if resp.status_code == 200:
            for pr in resp.json():
                table.add_row(str(pr['number']), pr['title'], pr['head']['ref'], pr['base']['ref'])

    async def create_pr_task(self):
        title, head, base, body = self.query_one("#pr-title").value, self.query_one("#pr-head").value, self.query_one("#pr-base").value, self.query_one("#pr-body").value
        config = load_config()
        token = get_github_token(config)
        owner, repo = get_current_repo_context()
        from ..github.api import create_pull_request
        if create_pull_request(owner, repo, token, title, head, base, body).status_code == 201:
            self.notify("PR Created")

    async def manage_pr_task(self, btn_id):
        table = self.query_one("#pr-table", DataTable)
        try:
            pr_num = table.get_row_at(table.cursor_row)[0]
        except:
            return
        config = load_config()
        token = get_github_token(config)
        owner, repo = get_current_repo_context()
        from ..github.api import github_request
        if "merge" in btn_id:
            github_request("PUT", f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_num}/merge", token)
        elif "close" in btn_id:
            github_request("PATCH", f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_num}", token, json={"state": "closed"})
        elif "comment" in btn_id:
            self.pending_tool = {"name": "github_issue", "args": {"action": "comment", "repo": repo, "number": int(pr_num)}}
            self.query_one("#chat-input").placeholder = f"Type comment for PR #{pr_num}..."
            self.query_one("#chat-input").focus()
            self.notify("Enter comment in chat")
            return
        self.run_worker(self.list_prs_task())

    async def gather_context_async(self):
        cwd = os.getcwd()
        context = f"PATH: {cwd}\n"
        count = 0
        for root, dirs, files in os.walk("."):
            dirs[:] = [d for d in dirs if d not in [".git", "node_modules", "venv", "__pycache__", "dist", "build"]]
            for f in files:
                context += f"- {os.path.relpath(os.path.join(root, f), '.')}\n"
                count += 1
                if count > 300: # Safety cap
                    context += "... (truncated for speed)\n"
                    return context[:4000]
        return context[:4000]

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-upload-start":
            self.run_worker(self.upload_task())
        elif event.button.id == "btn-docs-gen":
            self.run_worker(self.docs_task())
        elif event.button.id == "btn-switch-context":
            self.switch_context()
        elif event.button.id == "btn-scroll-up":
            self.query_one("#chat-log").scroll_up()
        elif event.button.id == "btn-scroll-down":
            self.query_one("#chat-log").scroll_down()
        elif event.button.id == "btn-diag-start":
            self.run_worker(self.diagnostic_task())
        elif event.button.id == "btn-pr-mode-list":
            self.query_one("#pr-switcher").current = "pr-list-view"
            self.run_worker(self.list_prs_task())
        elif event.button.id == "btn-pr-mode-create":
            self.query_one("#pr-switcher").current = "pr-create-view"
        elif event.button.id == "btn-pr-create":
            self.run_worker(self.create_pr_task())
        elif event.button.id == "btn-gist-mode-list":
            self.query_one("#gist-switcher").current = "gist-list-view"
            self.run_worker(self.list_gists_task())
        elif event.button.id == "btn-gist-mode-create":
            self.query_one("#gist-switcher").current = "gist-create-view"
        elif event.button.id == "btn-gist-create":
            self.run_worker(self.create_gist_task())
        elif event.button.id == "btn-ssh-gen":
            self.run_worker(self.ssh_task())
        elif event.button.id == "btn-release-start":
            self.run_worker(self.release_task())
        elif "btn-pr-" in event.button.id:
            self.run_worker(self.manage_pr_task(event.button.id))
        elif event.button.id.startswith("tpl-"):
            self.run_worker(self.marketplace_task(event.button.id))
        elif event.button.id == "btn-ai-gen":
            self.run_worker(self.ai_gen_task())
        elif event.button.id == "btn-ai-commit":
            self.run_worker(self.ai_commit_task())
        elif event.button.id == "btn-search-start":
            self.run_worker(self.search_task())
        elif event.button.id == "btn-scan":
            self.run_sast_scan()

    def run_sast_scan(self):
        table = self.query_one("#security-table", DataTable)
        table.clear()
        results = run_local_sast_scan(".")
        for r in results:
            table.add_row(r['type'], os.path.basename(r['file']), r['code'])

    def switch_context(self):
        new_path = self.query_one("#target-dir-input").value
        if os.path.isdir(new_path):
            os.chdir(new_path)
            self.target_dir = new_path
            self.query_one("#lbl-current-target").update(f"Current: [green]{new_path}[/green]")
            self.notify("Context Switched")
        else:
            self.notify("Invalid Directory", severity="error")

    def launch_cli_fallback(self, mode):
        from ..github.ssh_ops import setup_ssh_infrastructure
        from ..utils.ai import ai_commit_workflow
        from ..project.templates import create_project_from_template
        config = load_config()
        user, token = get_github_username(config), get_github_token(config)
        with self.suspend():
            os.system('clear')
            try:
                if "ai-commit" in mode:
                    ai_commit_workflow(user, token, config)
                elif "ssh" in mode:
                    setup_ssh_infrastructure(config, token)
                elif "template" in mode:
                    create_project_from_template(user, token, config)
                else:
                    print(f"Feature '{mode}' migrated to TUI.")
                    input("\nPress Enter...")
            except Exception as e:
                print(f"Error: {e}")
                input("Press Enter...")

def run_tui():
    PyGitUpTUI().run()
