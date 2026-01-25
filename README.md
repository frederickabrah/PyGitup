# PyGitUp

## Effortless GitHub Workflows from Your Terminal

PyGitUp is a powerful command-line interface (CLI) tool written in Python designed to streamline and automate common GitHub workflows. Say goodbye to remembering complex `git` commands and repetitive tasks – PyGitUp makes managing your repositories intuitive and efficient.

## Features

PyGitUp offers a wide array of functionalities to simplify your development process:

### Core Operations

*   **Project Upload/Update:** Easily upload entire project directories or update existing ones on GitHub.
*   **Single File Upload/Update:** Quickly push changes to individual files in your repositories.
*   **Batch File Upload:** Upload multiple files to a repository in a single operation.
*   **Template-Based Project Initialization:** Create new GitHub repositories from predefined templates (e.g., web-app, Python package) with customizable variables.

### Git Management

*   **Branch Management:** Create, list, delete, and switch between local Git branches with simple commands.
*   **Stash Management:** Save, list, apply, pop, and drop stashed changes to keep your working directory clean.
*   **Tag Management:** Create, list, and delete Git tags for versioning and release management.
*   **Cherry-Picking:** Apply specific commits from one branch to another.
*   **Smart Push:** Automatically squash trivial commits (e.g., "fix typo") before pushing, leading to a cleaner commit history.

### GitHub Integration

*   **Automated Release Management:** Create GitHub releases with automated changelog generation from commit history.
*   **Multi-Repository Operations:** Update the same file or apply changes across multiple GitHub repositories simultaneously.
*   **Automated Issue Creation from TODOs:** Scan your codebase for `TODO` comments and automatically create GitHub issues for them, optionally assigning them to users.
*   **Code Review Automation:** Request code reviews by creating new branches, committing changes, pushing, and opening pull requests with specified reviewers.
*   **Gist Management:** Create, list, and manage your GitHub Gists directly from the command line.
*   **Webhook Management:** List, create, and delete webhooks for your repositories, enabling powerful integrations.
*   **GitHub Actions Integration:** Trigger and monitor GitHub Actions workflows.
*   **Pull Request Management:** Merge, close, and comment on pull requests.
*   **Change Repository Visibility:** Easily switch an existing repository between public and private.

### Utility & Analytics

*   **Offline Commit Queue:** Queue commits when offline and process them automatically once an internet connection is restored.
*   **Automated Documentation Generation:** Generate comprehensive documentation from code comments (now with robust AST-based parsing for Python, plus support for JavaScript, Java, C++, Go).
*   **Collaboration Analytics:** Generate reports on team contributions, issue statistics, and more.
*   **Security Auditing:** Scan project dependencies for known security vulnerabilities using `pip-audit`.
*   **Get Repository Info from URL:** Retrieve comprehensive, verbose information about any GitHub repository using its URL.

## Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/frederickabrah/PyGitUp.git
    cd PyGitUp
    ```

2.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

## Configuration

PyGitUp can be configured via a `pygitup.yaml` file in your project root or home directory, command-line arguments, or environment variables. To get started with a configuration file, run the interactive wizard:

```bash
python pygitup.py --mode configure
```

Alternatively, you can set environment variables:

*   `GITHUB_USERNAME`: Your GitHub username.
*   `GITHUB_TOKEN`: Your GitHub Personal Access Token (PAT) with appropriate `repo` scopes.

## Usage

PyGitUp offers both an interactive menu-driven mode and a command-line argument mode for automation.

### Interactive Mode

Simply run the tool without any arguments to access the interactive menu:

```bash
python pygitup.py
```

### Command-Line Mode

Use the `--mode` argument followed by the desired operation. Many modes also support subcommands and additional arguments.

**Examples:**

*   **Upload a single file:**

    ```bash
    python pygitup.py --mode file --repo My-Awesome-Project --file main.py --path src/main.py --message "Update main module"
    ```

*   **Upload an entire project:**

    ```bash
    python pygitup.py --mode project --path ./myproject --repo My-Awesome-Project --private
    ```

*   **Create a new project from a template:**

    ```bash
    python pygitup.py --mode template --template web-app --repo MyWebsite --variables "PROJECT_NAME=MyWebsite,DESCRIPTION=My awesome website"
    ```

*   **List branches:**

    ```bash
    python pygitup.py --mode branch --action list
    ```

*   **Create a Gist:**

    ```bash
    python pygitup.py --mode gist --action create --filename my_script.py --content "print('Hello, Gist!')" --public --description "A simple Python script"
    ```

*   **Run a security audit:**

    ```bash
    python pygitup.py --mode audit
    ```

*   **Change repository visibility to private:**

    ```bash
    python pygitup.py --mode visibility --repo MyPrivateRepo --private
    ```

*   **Change repository visibility to public:**

    ```bash
    python pygitup.py --mode visibility --repo MyPublicRepo --public
    ```

*   **Get detailed repository information:**

    ```bash
    python pygitup.py --mode repo-info --url https://github.com/owner/repository_name
    ```

For a full list of commands and arguments, use the `--help` flag:

```bash
python pygitup.py --help
```

## ❤️ Sponsor the Project: Fuel the Machine!

Let's be honest, `PyGitUp` is the digital equivalent of a Swiss Army knife for your GitHub workflow. It slices, it dices, it saves you from the existential dread of a `git push --force` gone wrong on a Friday afternoon. We've all been there.

This tool is, and always will be, **free**.

However, it is not fueled by good intentions alone. The `PyGitUp` development engine runs on a delicate, high-performance mixture of caffeine, sleep deprivation, and the sheer terror of disappointing its users. It's a miracle of engineering, really.

**If `PyGitUp` has saved you time, sanity, or even just a few frantic Google searches, consider becoming a sponsor.**

Think of it less as a donation and more as a strategic investment in your own future productivity. Your sponsorship directly translates into:

*   **More Features:** We have a roadmap longer than a `git log` on a decade-old project. Your support helps us build the features you want, faster.
*   **Fewer Bugs:** Every bug squashed is a victory for developer sanity everywhere.
*   **The Ultimate Fuel:** Coffee. Lots and lots of coffee. You're not just sponsoring a project; you're participating in a revolutionary **Caffeine-as-a-Service (CaaS)** model. You provide the caffeine, we provide the code that makes your life easier.

Your contribution, no matter the size, is a loud and clear message that you value this work. It's the ultimate "thank you" and the motivation to keep building.

**[➡️ Become a GitHub Sponsor!](https://github.com/sponsors/frederickabrah)**

**[☕ Buy Me a Coffee](https://www.buymeacoffee.com/frederickabrah)**

Help us turn caffeine into code. Be the hero this world needs.

## Contributing

We welcome contributions to PyGitUp! Please see `CONTRIBUTING.md` for guidelines.

## License

This project is licensed under the MIT License - see the `LICENSE` file for details.