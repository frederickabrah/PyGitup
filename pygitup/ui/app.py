
from textual.app import App, ComposeResult

from textual.containers import Container, Horizontal, Vertical, ScrollableContainer

from textual.widgets import Header, Footer, Static, ListItem, ListView, Label

from textual.binding import Binding

from .. import __version__

from ..core.config import load_config, get_github_username, get_github_token, get_active_profile_path

from ..project.project_ops import upload_project_directory

from ..utils.ai import ai_commit_workflow

from ..github.repo_info import get_detailed_repo_info, get_fork_intelligence

from ..github.ssh_ops import setup_ssh_infrastructure

from ..github.actions import manage_actions, setup_cicd_workflow

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

    """The main TUI Dashboard for PyGitUp."""

    

    TITLE = f"PyGitUp v{__version__}"

    CSS = """

    Screen {

        background: #0d1117;

    }

    

    #sidebar {

        width: 40;

        background: #161b22;

        border-right: tall #30363d;

    }

    

    #main-content {

        padding: 1 4;

    }

    

    .category-header {

        background: #21262d;

        color: #58a6ff;

        text-style: bold;

        padding: 0 1;

        margin: 1 0 0 0;

        text-align: center;

    }

    

    ListItem {

        padding: 1 1;

        border-bottom: hkey #30363d;

    }

    

    ListItem:hover {

        background: #1f6feb;

    }

    

    ListView:focus > ListItem.--highlight {

        background: #238636;

    }



    #feature-title {

        color: #58a6ff;

        text-style: bold;

        margin-bottom: 1;

    }



    #feature-desc {

        color: #8b949e;

    }

    """



    BINDINGS = [

        Binding("q", "quit", "Quit", show=True),

        Binding("r", "refresh", "Refresh", show=True),

        Binding("enter", "select", "Launch Feature", show=True),

    ]



    def compose(self) -> ComposeResult:

        active_profile = os.path.basename(get_active_profile_path()).replace(".yaml", "")

        yield Header(show_clock=True)

        yield Horizontal(

            Vertical(

                Label(f" PROFILE: {active_profile} ", classes="category-header"),

                ListView(

                    FeatureItem("Project Upload", "project", "Core", "Upload whole directories to GitHub with security pre-scans."),

                    FeatureItem("AI Semantic Commit", "ai-commit", "Tools", "Uses Gemini to write professional conventional commits based on your diff."),

                    FeatureItem("OSINT Intelligence", "repo-info", "GitHub", "Deep reconnaissance of repository stats, health, and social metadata."),

                    FeatureItem("Fork Network Recon", "fork-intel", "GitHub", "Analyze community forks for unique code and hidden improvements."),

                    FeatureItem("CI/CD Architect", "cicd", "GitHub", "Automated GitHub Actions generation and live build monitoring."),

                    FeatureItem("SSH Infrastructure", "ssh-setup", "GitHub", "Auto-generate and sync secure Ed25519 keys with GitHub."),

                    id="feature-list"

                ),

                id="sidebar"

            ),

            Vertical(

                Static("Welcome to PyGitUp God Mode", id="feature-title"),

                Static("Select a module from the left to explore advanced GitHub automation features.", id="feature-desc"),

                id="main-content"

            )

        )

        yield Footer()



    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:

        if event.item:

            item = event.item

            self.query_one("#feature-title").update(f"🚀 {item.feature_name}")

            self.query_one("#feature-desc").update(f"{item.description}\n\n[bold white]Press ENTER to launch.[/bold white]")



    def action_refresh(self) -> None:

        self.notify("System Status: Online 🟢")



    def action_select(self) -> None:

        list_view = self.query_one("#feature-list", ListView)

        if list_view.highlighted_child:

            item = list_view.highlighted_child

            self.launch_feature(item.mode)



    def launch_feature(self, mode: str):

        """Suspends the TUI to run the selected CLI feature."""

        # Load config fresh

        config = load_config()

        user = get_github_username(config)

        token = get_github_token(config)

        

        # Suspend app to allow terminal output

        with self.suspend():

            try:

                if mode == "project":

                    upload_project_directory(user, token, config)

                elif mode == "ai-commit":

                    ai_commit_workflow(user, token, config)

                elif mode == "repo-info":

                    # Mock args for compatibility

                    class MockArgs: url = None

                    get_detailed_repo_info(MockArgs(), token)

                elif mode == "fork-intel":

                    url = input("Enter repository URL: ")

                    from ..github.repo_info import parse_github_url

                    owner, repo = parse_github_url(url)

                    if owner and repo:

                        get_fork_intelligence(owner, repo, token)

                elif mode == "ssh-setup":

                    setup_ssh_infrastructure(config, token)

                elif mode == "cicd":

                    setup_cicd_workflow(user, token, None, config)

                

                input("\nPress Enter to return to dashboard...")

            except Exception as e:

                print(f"\nError running feature: {e}")

                input("Press Enter to continue...")



def run_tui():

    app = PyGitUpTUI()

    app.run()


