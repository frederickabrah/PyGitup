
from textual.app import App, ComposeResult

from textual.containers import Container, Horizontal, Vertical, ScrollableContainer

from textual.widgets import Header, Footer, Static, ListItem, ListView, Label

from textual.binding import Binding

from .. import __version__



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

        Binding("s", "switch_profile", "Switch Profile", show=True),

        Binding("enter", "select", "Launch Feature", show=True),

    ]



    def compose(self) -> ComposeResult:

        yield Header(show_clock=True)

        yield Horizontal(

            Vertical(

                Label(" 🛰️ INTELLIGENCE HUB ", classes="category-header"),

                ListView(

                    FeatureItem("Project Upload", "project", "Core", "Upload whole directories to GitHub with security pre-scans."),

                    FeatureItem("AI Semantic Commit", "ai-commit", "Tools", "Uses Gemini to write professional conventional commits based on your diff."),

                    FeatureItem("OSINT Intelligence", "repo-info", "GitHub", "Deep reconnaissance of repository stats, health, and social metadata."),

                    FeatureItem("Fork Network Recon", "fork-intel", "GitHub", "Analyze community forks for unique code and hidden improvements."),

                    FeatureItem("CI/CD Architect", "ssh-setup", "GitHub", "Automated GitHub Actions generation and live build monitoring."),

                    FeatureItem("Identity Switcher", "accounts", "Tools", "Swap between Work and Personal GitHub profiles instantly."),

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

            self.query_one("#feature-desc").update(f"{item.description}\n\n[dim]Press ENTER to launch this module.[/dim]")



    def action_refresh(self) -> None:

        self.notify("Refreshing all intelligence feeds...", title="System")



    def action_select(self) -> None:

        self.notify("Launching module... please wait.", title="Executive Order")



def run_tui():

    app = PyGitUpTUI()

    app.run()


