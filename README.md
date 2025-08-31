# PyGitUp 🚀

**Your All-in-One Command-Line Tool for Effortless GitHub Uploads.**

[![Python Version](https://img.shields.io/badge/python-3.6%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

Tired of the repetitive `git` commands just to get your project on GitHub? Wish you could update a single file without a full `clone`, `commit`, and `push` cycle? **`PyGitUp` is the solution.**

This tool streamlines your entire GitHub workflow, whether you're pushing a brand-new project or updating a single file in an existing repository.

## ✨ Key Features

-   ✅ **Multiple Operation Modes:**
    -   **Project Mode:** Upload an entire project directory. `PyGitUp` initializes a git repo, creates the remote on GitHub, and pushes your code in one go.
    -   **File Mode:** Upload or overwrite a single file directly using the GitHub API. Perfect for quick updates.
    -   **Batch Mode:** Upload multiple files at once with a single command.
    -   **Template Mode:** Create new projects from templates with variable substitution.
    -   **Release Mode:** Create GitHub releases with auto-generated changelogs.
    -   **Multi-Repo Mode:** Update the same file across multiple repositories.
    -   **TODO Scan Mode:** Automatically create GitHub issues from TODO comments in your code.
    -   **Offline Queue Mode:** Queue commits when offline and automatically push when online.
-   ✅ **Flexible Configuration:**
    -   Command-line arguments for automated usage
    -   Configuration file support (`pygitup.yaml`) for default settings
    -   Environment variable support for credentials
-   ✅ **Enhanced User Experience:**
    -   A clean, interactive menu to choose your workflow.
    -   A file selector that lists files in your current directory for easy selection.
    -   Progress bars for long operations
    -   Detailed logging capabilities
-   ✅ **Unique Value Propositions:**
    -   **Direct File Updates Without Cloning:** Update remote files without downloading the entire repository.
    -   **Template-Based Project Creation:** Start new projects from customizable templates.
    -   **Automated Release Management:** Create releases with auto-generated changelogs.
    -   **Multi-Repository Operations:** Update files across multiple repositories simultaneously.
    -   **Automated Issue Creation:** Convert TODO comments to GitHub issues.
    -   **Offline Commit Queue:** Work offline and sync when you're back online.

## 🎬 Demonstration

Here's a glimpse of how easy it is to upload a single file with `PyGitUp`:

```
$ python pygitup.py
Enter your GitHub username: frederickabrah
Enter your GitHub Personal Access Token:

What would you like to do?
1: Upload/update a whole project directory
2: Upload/update a single file
3: Batch upload multiple files
4: Create project from template
5: Create GitHub release
6: Update file in multiple repositories
7: Scan for TODOs and create issues
8: Queue commit for offline
9: Process offline commit queue
Enter your choice (1-9): 2

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

### Interactive Mode
Simply run the script and follow the prompts:
```bash
python pygitup.py
```

### Command-Line Mode
For automated usage, use command-line arguments:

#### Basic Operations
```bash
# Upload a single file
python pygitup.py --mode file --repo My-Awesome-Project --file main.py --path src/main.py --message "Update main module"

# Upload an entire project
python pygitup.py --mode project --path ./myproject --repo My-Awesome-Project --private

# Batch upload multiple files
python pygitup.py --mode batch --repo My-Awesome-Project --files "file1.py,file2.py,file3.py" --path src/
```

#### Advanced Features
```bash
# Create project from template
python pygitup.py --mode template --template web-app --repo MyWebsite --variables "PROJECT_NAME=MyWebsite,DESCRIPTION=My awesome website"

# Create GitHub release with changelog
python pygitup.py --mode release --repo MyProject --version v1.2.0 --name "Version 1.2.0" --generate-changelog

# Update file in multiple repositories
python pygitup.py --mode multi-repo --multi-repo "repo1,repo2,repo3" --file config.json --path configs/config.json --message "Update configuration"

# Scan for TODOs and create issues
python pygitup.py --mode scan-todos --repo MyProject --pattern "*.py,*.js" --assign "maintainer"

# Queue commit for offline work
python pygitup.py --mode offline-queue --repo MyProject --file important.py --message "Important update"

# Process offline queue when back online
python pygitup.py --mode process-queue
```

### Configuration File
Create a `pygitup.yaml` file in your project directory or home directory:
```yaml
defaults:
  commit_message: "Update from PyGitUp"
  branch: "main"
  
github:
  username: "your-username"  # Optional, can use GITHUB_USERNAME env var
  token_file: "~/.github-token"  # More secure than environment variables
  default_description: "Repository created with PyGitUp"
  default_private: false

batch:
  continue_on_error: false

logging:
  enabled: true
  file: "pygitup.log"
  level: "INFO"

templates:
  directory: "./templates"

scheduling:
  offline_queue_file: ".pygitup_offline_queue"
```

### Environment Variables
For even faster use, set your credentials as environment variables:
```bash
export GITHUB_USERNAME="frederickabrah"
export GITHUB_TOKEN="your-pat"
```

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://github.com/frederickabrah/PyGitUp/issues). (You would update this link after you create the repository).