# PyGitUp 🚀

**Your All-in-One Command-Line Tool for Effortless GitHub Uploads.**

[![Python Version](https://img.shields.io/badge/python-3.6%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

Tired of the repetitive `git` commands just to get your project on GitHub? Wish you could update a single file without a full `clone`, `commit`, and `push` cycle? **`PyGitUp` is the solution.**

This tool streamlines your entire GitHub workflow, whether you're pushing a brand-new project or updating a single file in an existing repository.

## ✨ Key Features

-   ✅ **Dual-Mode Operation:**
    -   **Project Mode:** Upload an entire project directory. `PyGitUp` initializes a git repo, creates the remote on GitHub, and pushes your code in one go.
    -   **File Mode:** Upload or overwrite a single file directly using the GitHub API. Perfect for quick updates.
-   ✅ **Interactive & Smart:**
    -   A clean, interactive menu to choose your workflow.
    -   A file selector that lists files in your current directory for easy selection.
    -   Remembers your credentials for the session and can use environment variables for convenience.
-   ✅ **User-Friendly:**
    -   Securely prompts for your GitHub Personal Access Token.
    -   Handles existing repositories and non-empty remotes gracefully with a force-push option.
    -   Clear, step-by-step prompts guide you through the process.

## 🎬 Demonstration

Here's a glimpse of how easy it is to upload a single file with `PyGitUp`:

```
$ python pygitup.py
Enter your GitHub username: frederickabrah
Enter your GitHub Personal Access Token:

What would you like to do?
1: Upload/update a whole project directory
2: Upload/update a single file
Enter your choice (1 or 2): 2

Enter the name of the target GitHub repository: My-Awesome-Project

--- Select a file to upload ---
Listing files in: /path/to/your/project
1: README.md
2: main.py
3: utils.py

Enter the number of the file you want to upload, or type a different path manually.
> 2
You selected: main.py
Enter the path for the file in the repository (e.g., folder/file.txt): src/main.py
Enter the commit message: ✨ Add new core feature

File exists in the repository. It will be overwritten.
Successfully updated file 'src/main.py' in 'My-Awesome-Project'.
View the file at: https://github.com/frederickabrah/My-Awesome-Project/blob/main/src/main.py
--------------------
Operation complete.
```

## 🛠️ Installation

1.  **Prerequisites:** Make sure you have Python 3 and Git installed.
2.  **Clone or download** this repository.
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## 🚀 Usage

1.  **Generate a GitHub Personal Access Token (PAT):**
    -   Go to [github.com/settings/tokens](https://github.com/settings/tokens).
    -   Generate a new token with the full `repo` scope.
    -   **Copy this token!** You'll need it to run the script.
2.  **Run the script:**
    ```bash
    python pygitup.py
    ```
3.  **Follow the on-screen prompts!**
    -   **Pro Tip:** For even faster use, set your credentials as environment variables:
        ```bash
        export GITHUB_USERNAME="frederickabrah"
        export GITHUB_TOKEN="your-pat"
        ```

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://github.com/frederickabrah/PyGitUp/issues). (You would update this link after you create the repository).
