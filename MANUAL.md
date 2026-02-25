# PyGitUp User Manual

**Version:** 2.4.0 (Security-Enhanced)  
**Last Updated:** February 22, 2026

---

## 📖 Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Configuration](#configuration)
5. [Interactive Mode](#interactive-mode)
6. [Command-Line Interface](#command-line-interface)
7. [Feature Reference](#feature-reference)
8. [Security Features](#security-features)
9. [AI Capabilities](#ai-capabilities)
10. [TUI Dashboard](#tui-dashboard)
11. [Workflows & Examples](#workflows--examples)
12. [Troubleshooting](#troubleshooting)
13. [Best Practices](#best-practices)
14. [FAQ](#faq)

---

## 🎯 Introduction

### What is PyGitUp?

PyGitUp is a **comprehensive GitHub automation platform** that combines:
- 🔧 Git operations management
- 🐙 GitHub API integration  
- 🔒 Security scanning & compliance
- 🤖 AI-powered assistance
- 📊 Intelligence & analytics

### Who Should Use PyGitUp?

- **Solo Developers** - Automate repetitive Git tasks
- **Development Teams** - Streamline collaboration workflows
- **Security Teams** - SAST scanning, SBOM generation
- **DevOps Engineers** - CI/CD, webhook, actions management
- **Open Source Maintainers** - Issue triage, release management
- **Consultants** - Multi-repo management, migrations

### Key Features

- **40+ Features** across 8 categories
- **CLI, Interactive Menu, and TUI** interfaces
- **Encrypted credential storage** with master password
- **AI-powered assistance** (optional, opt-in)
- **Security scanning** with 60+ secret patterns
- **Multi-profile support** for multiple accounts

---

## 📥 Installation

### Prerequisites

- Python 3.6 or higher
- pip (Python package manager)
- Git installed and configured
- GitHub account (for most features)

### Step-by-Step Installation

#### 1. Clone the Repository

```bash
git clone https://github.com/frederickabrah/PyGitUp.git
cd PyGitUp
```

#### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

**Required packages:**
- `requests` - HTTP library for API calls
- `PyYAML` - Configuration file parsing
- `tqdm` - Progress bars
- `pip-audit` - Dependency vulnerability scanning
- `inquirer` - Interactive prompts
- `rich` - Terminal formatting
- `textual` - TUI framework
- `beautifulsoup4` - HTML scraping
- `pytest` - Testing framework
- `cryptography` - Encrypted storage

#### 3. Install PyGitUp

```bash
# Development mode (recommended)
pip install -e .

# Or system-wide installation
pip install .
```

#### 4. Verify Installation

```bash
python pygitup.py --help
```

You should see the help message with all available options.

---

## 🚀 Quick Start

### First-Time Setup

1. **Launch PyGitUp:**
   ```bash
   python pygitup.py
   ```

2. **Configure Credentials:**
   - Select **Option 14** (Configuration Wizard)
   - Enter your GitHub username
   - Enter your GitHub token (create at: https://github.com/settings/tokens)
   - Set a master password for encryption

3. **Required Token Scopes:**
   - ✅ `repo` - Full control of private repositories
   - ✅ `workflow` - Update GitHub Action workflows
   - ✅ `admin:org` - Organization features (optional)
   - ✅ `gist` - Gist management (optional)

4. **Test Configuration:**
   - Select **Option 36** (Token Health)
   - Verify token is valid

### Your First Operations

#### Upload a Project

```bash
python pygitup.py
# Select Option 1: Upload/update a whole project directory
# Follow prompts to select path and repository
```

#### Get Repository Info

```bash
python pygitup.py --mode repo-info --url https://github.com/frederickabrah/PyGitUp
```

#### Run Security Scan

```bash
python pygitup.py
# Select Option 35: Enhanced Security Scan
```

---

## ⚙️ Configuration

### Configuration Files

PyGitUp stores configuration in:
```
~/.pygitup_config/
├── settings.json          # Active profile settings
├── profiles/
│   ├── default.yaml       # Default profile
│   └── yourname.yaml      # Custom profiles
└── token_tracking.json    # Token expiration tracking
```

### Multi-Profile Management

#### Create New Profile

```bash
python pygitup.py
# Option 14: Configure
# Enter new profile name
```

#### Switch Profiles

```bash
python pygitup.py
# Option 31: Manage Accounts
# Option 1: Switch Profile
# Enter profile name
```

#### List Profiles

```bash
python pygitup.py
# Option 31: Manage Accounts
# View available profiles
```

### Environment Variables

```bash
# GitHub token (alternative to config file)
export GITHUB_TOKEN=your_token_here

# AI API key
export GEMINI_API_KEY=your_ai_key_here

# Debug mode
export PYGITUP_DEBUG=1

# Custom config directory
export PYGITUP_CONFIG_DIR=/path/to/config
```

### Configuration File Structure

```yaml
# ~/.pygitup_config/profiles/default.yaml

security:
  salt: <encryption_salt>

github:
  username: your_username
  token: <encrypted_token>
  ai_api_key: <encrypted_ai_key>
  default_description: "Repository created with PyGitUp"
  default_private: false

defaults:
  commit_message: "Update from PyGitUp"
  branch: main

performance:
  max_parallel_uploads: 5
  timeout: 30

logging:
  enabled: false
  file: pygitup.log
  level: INFO
```

---

## 🎮 Interactive Mode

### Launching Interactive Mode

```bash
python pygitup.py
```

### Menu Structure

```
╭────┬────────────────────────────────────┬──────────╮
│ ID │ Feature                            │ Category │
├────┼────────────────────────────────────┼──────────┤
│ 1  │ Upload/update a whole project      │ Core     │
│ 2  │ Upload/update a single file        │ Core     │
│ 3  │ Batch upload multiple files        │ Core     │
│ 4  │ Create project from template       │ Core     │
│ 5  │ Create GitHub release              │ GitHub   │
│ ...│ ...                                │ ...      │
│ 0  │ Exit PyGitUp                       │ Exit     │
╰────┴────────────────────────────────────┴──────────╯
```

### Navigation

- **Enter number** - Select option (e.g., `1`, `35`)
- **0** - Exit PyGitUp
- **Enter** - Return to menu after operation

### Categories

- **Core** - Project & file operations
- **GitHub** - GitHub API features
- **Git** - Git operations
- **Tools** - Utilities & automation
- **Security** - Security scanning & compliance
- **AI** - AI-powered features
- **Misc** - Additional features

---

## 💻 Command-Line Interface

### Basic Syntax

```bash
python pygitup.py [OPTIONS] [SUBCOMMAND]
```

### Global Options

| Option | Description | Example |
|--------|-------------|---------|
| `--mode` | Operation mode | `--mode repo-info` |
| `--repo` | Repository name | `--repo myproject` |
| `--config` | Custom config file | `--config /path/to/config` |
| `--dry-run` | Simulate without changes | `--dry-run` |
| `--batch` | Batch mode (no prompts) | `--batch` |
| `-h, --help` | Show help | `--help` |

### Common CLI Patterns

#### File Operations
```bash
# Upload single file
python pygitup.py --mode file --repo myrepo --file myfile.py

# Upload project
python pygitup.py --mode project --path ./myproject --private

# Batch upload
python pygitup.py --mode batch --repo myrepo --files file1.py,file2.py
```

#### Repository Management
```bash
# Create release
python pygitup.py --mode release --repo myrepo --version v1.0.0

# Change visibility
python pygitup.py --mode visibility --repo myrepo --private

# Delete repository
python pygitup.py --mode delete-repo --repo myrepo
```

#### Security Operations
```bash
# Security scan
python pygitup.py --mode security-scan

# Token health
python pygitup.py --mode token-health

# Generate SBOM
python pygitup.py --mode generate-sbom
```

#### Information & Analytics
```bash
# Repository info
python pygitup.py --mode repo-info --url https://github.com/user/repo

# Analytics
python pygitup.py --mode analytics --period last-month

# Bulk management
python pygitup.py --mode bulk-mgmt
```

---

## 📚 Feature Reference (The Full 40)

PyGitUp's interactive menu provides access to 40 industrial-grade automation tools. Below is the technical breakdown of each mode.

---

### 🔧 CORE OPERATIONS (1-4)

#### 1. Upload Project Directory
- **Goal:** Transform a local folder into a GitHub repository.
- **Input:** Local path, repo name, visibility (Public/Private).
- **Impact:** Initializes Git, generates `.gitignore`, creates remote repo, and performs initial push.

#### 2. Upload Single File
- **Goal:** Atomic file injection into a remote repository.
- **Input:** Local file path, target repo, commit message.
- **Impact:** Pushes a single blob to GitHub without cloning the full repo.

#### 3. Batch Upload
- **Goal:** Bulk synchronization of specific files.
- **Input:** Comma-separated list of paths.
- **Impact:** Identifies changed files and pushes them in a single multi-file commit.

#### 4. Create from Template
- **Goal:** Standardized scaffolding for new projects.
- **Input:** Template name (e.g., `react-app`), repo name.
- **Impact:** Deploys a pre-configured architecture with best-practice folder structures.

---

### 📦 RELEASE & VERSIONING (5-9)

#### 5. Create GitHub Release
- **Goal:** Official versioning and artifact tagging.
- **Input:** Tag name (v1.0.0), release title, description.
- **Impact:** Creates a Git tag and a GitHub Release entry with auto-generated changelogs.

#### 6. Multi-Repo Update
- **Goal:** Global synchronization across a portfolio.
- **Input:** List of repos, file to sync (e.g., `LICENSE` or `.github/workflows/ci.yml`).
- **Impact:** Executes parallel updates across all targets.

#### 7. Scan TODOs
- **Goal:** Technical debt conversion.
- **Input:** File pattern (*.py).
- **Impact:** Parses code for `# TODO` or `# FIXME`, extracts context via `git blame`, and creates GitHub Issues.

#### 8. Offline Queue Commit
- **Goal:** Asynchronous Git operations.
- **Input:** Commit message, changed files.
- **Impact:** Stores operations in a local `.pygitup_offline_queue` for later sync.

#### 9. Process Offline Queue
- **Goal:** Synchronization of deferred tasks.
- **Input:** None.
- **Impact:** Replays all queued commits to GitHub sequentially once connectivity is restored.

---

### 🤝 COLLABORATION & DOCS (10-13)

#### 10. Request Code Review
- **Goal:** Automated peer review triggering.
- **Input:** PR number, list of reviewers.
- **Impact:** Assigns specific GitHub users to an open Pull Request.

#### 11. Smart Push
- **Goal:** Git history hygiene.
- **Input:** Branch name.
- **Impact:** Automatically squashes "fixup!" or "wip" commits into a single semantic commit before pushing.

#### 12. Generate Documentation
- **Goal:** Automated project visibility.
- **Input:** Repo name.
- **Impact:** Analyzes code structure and generates `README.md`, `CONTRIBUTING.md`, and `LICENSE`.

#### 13. Generate Analytics
- **Goal:** Productivity and growth metrics.
- **Input:** Time period.
- **Impact:** Generates reports on star growth, fork velocity, and contributor impact.

---

### 🛠️ SYSTEM & GIT CONFIG (14-18)

#### 14. Configuration Wizard
- **Goal:** Credential management.
- **Input:** GitHub Token, AI API Key, Master Password.
- **Impact:** Encrypts and stores profile data in `~/.pygitup_config/`.

#### 15. Manage Branches
- **Goal:** Remote-first branch control.
- **Input:** Branch name, action (create/delete/switch).
- **Impact:** Manipulates the Git tree directly via API calls.

#### 16. Manage Stashes
- **Goal:** Work-in-progress persistence.
- **Impact:** Saves or retrieves local modifications without affecting the commit history.

#### 17. Manage Tags
- **Goal:** Milestone marking.
- **Impact:** Creates or deletes immutable tags in the Git history.

#### 18. Cherry-Pick Commit
- **Goal:** Selective code porting.
- **Input:** Commit hash.
- **Impact:** Applies specific changes from one branch to another using the Git engine.

---

### 🐙 GITHUB INTEGRATION (19-22)

#### 19. Manage Gists
- **Goal:** Snippet sharing.
- **Impact:** Creates, edits, or lists GitHub Gists for quick code sharing.

#### 20. Manage Webhooks
- **Goal:** CI/CD event integration.
- **Impact:** Configures URL endpoints to receive GitHub events (push, pull_request).

#### 21. Manage Actions
- **Goal:** Workflow automation control.
- **Impact:** Enables, disables, or triggers GitHub Action workflows via API.

#### 22. Manage Pull Requests
- **Goal:** Collaborative merge management.
- **Impact:** Lists, creates, merges, or closes PRs with terminal-based interaction.

---

### 🔒 SECURITY & REPO MGMT (23-29)

#### 23. Security Audit
- **Goal:** Comprehensive vulnerability assessment.
- **Impact:** Runs SAST, dependency scans, and fetches GitHub security alerts.

#### 24. Change Visibility
- **Goal:** Access control management.
- **Impact:** Toggles repository status between Public and Private.

#### 25. Repository Info (OSINT)
- **Goal:** Deep metadata reconnaissance.
- **Impact:** Extracts social links, dependency health, and digital footprints of a repo.

#### 26. Delete Repository
- **Goal:** Permanent cleanup.
- **Impact:** Removes a repository from GitHub (Requires manual confirmation).

#### 27. Bulk Management
- **Goal:** Portfolio oversight.
- **Impact:** Displays a dashboard of all owned repos with aggregated health scores.

#### 28. Migrate Repository
- **Goal:** Platform transition.
- **Input:** Source URL (GitLab/Bitbucket).
- **Impact:** Performs a high-fidelity mirror of external repos to GitHub.

#### 29. Fork Intelligence
- **Goal:** Community impact analysis.
- **Impact:** Analyzes the fork network to identify influential contributors.

---

### 🤖 AI-POWERED ENGINEERING (30-34)

#### 30. AI Commit Workflow
- **Goal:** Semantic history generation.
- **Impact:** Analyzes staged diffs and generates Conventional Commit messages.

#### 31. AI Diagnostic Tool
- **Goal:** Self-healing engineering.
- **Impact:** Executes failing commands, captures logs, and generates code fixes.

#### 32. SSH Infrastructure Setup
- **Goal:** Secure authentication.
- **Impact:** Generates RSA/Ed25519 keys and uploads them to GitHub automatically.

#### 33. AI Model Listing
- **Goal:** Capability assessment.
- **Impact:** Queries the AI engine to verify available models and API latency.

#### 34. TUI Dashboard
- **Goal:** Full-stack engineering workstation.
- **Impact:** Launches the immersive, multi-pane graphical dashboard.

---

### 🛡️ ENHANCED SECURITY (35-40)

#### 35. Enhanced Security Scan
- **Goal:** Industrial-grade SAST.
- **Impact:** Scans for 60+ secret patterns and 7 vulnerability classes (Injection, etc.).

#### 36. Token Health Check
- **Goal:** Credential hygiene.
- **Impact:** Detects revoked, expired, or over-privileged GitHub tokens.

#### 37. Supply Chain Scan
- **Goal:** Dependency auditing.
- **Impact:** Checks all packages against the OSV database for known vulnerabilities.

#### 38. Generate SBOM
- **Goal:** Compliance reporting.
- **Impact:** Exports project manifests in SPDX 2.3 or CycloneDX 1.4 JSON formats.

#### 39. Rotate GitHub Token
- **Goal:** Automated credential refresh.
- **Impact:** Guides the user through a secure 4-step rotation and re-encryption protocol.

#### 40. Interactive Issue Triage
- **Goal:** Proactive project management.
- **Impact:** Fetches remote issues and uses AI to generate step-by-step resolution plans.

---

## 🛡️ Technical Sovereignty

### Secret Detection

**Patterns Detected:**
- GitHub tokens (ghp_*, github_pat_*, gho_*, etc.)
- AWS credentials (Access Keys, Secret Keys)
- GCP/Azure keys
- Database connection strings
- API keys (Stripe, Twilio, SendGrid, Slack)
- Private keys (RSA, EC, SSH, PGP)
- JWT tokens

### SAST Scanning

**Vulnerability Categories:**
1. Command Injection (CWE-78)
2. SQL Injection (CWE-89)
3. Insecure Deserialization (CWE-502)
4. Arbitrary Code Execution (CWE-95)
5. Hardcoded Secrets (CWE-798)
6. Security Misconfiguration (CWE-295)

### Token Security

**Encryption:**
- Algorithm: Fernet (symmetric)
- Key Derivation: PBKDF2 (100,000 iterations)
- Storage: Encrypted YAML files
- Permissions: 0600 (owner read/write only)

**Best Practices:**
- Rotate tokens every 90-180 days
- Use fine-grained PATs when possible
- Enable master password protection
- Monitor token health regularly

---

## 🤖 AI Capabilities

### The Cortex Engine (History Compression)
Unlike standard AI chats that lose context over time, PyGitUp uses **History Compression**. When a session grows too long, the agent automatically distills the past into a structured technical `<state_snapshot>`. This ensures the agent never loses sight of your **Overall Goal**.

### 📎 Context Injection (@-mentions)
You can inject the content of any local file directly into the AI's "working memory" by using the `@` symbol followed by the filename in the chat.
*Example: "Analyze @pygitup/main.py for potential logic errors."*

### Autonomous Agent Capabilities
- **Chain-of-Thought reasoning**
- **Tool-Use** (executes system tasks natively)
- **Persistent memory** across sessions
- **Self-healing diagnostic loop**
- **Secret Scrubbing:** Sensitive tokens are automatically redacted before session saving.

---

## 🛡️ Technical Sovereignty

PyGitUp is built for industrial-grade reliability with several "Elite" features:

### 1. Atomic File Operations
All file writes by the AI agent are performed **atomically**. The system writes to a temporary file first and only replaces the original upon successful completion, preventing file corruption during crashes.

### 2. Safety Checkpoints (Git Stash)
Before any destructive file edit (write/patch), PyGitUp creates a temporary **Git Stash checkpoint**. You can restore your previous state at any time using `git stash list`.

### 3. Fuzzy Indentation-Aware Patching
The `patch_file` tool uses advanced regex normalization to match code blocks even if the AI model makes minor spacing or indentation errors, ensuring high-fidelity code modifications.

---

## 🖥️ TUI Dashboard

### Launch TUI

```bash
python pygitup.py --mode tui
# Or Option 34 in interactive mode
```

### TUI Interface Overview

```
╔══════════════════════════════════════════════════════════╗
║  Header (Clock, Status)                                  ║
╠══════════════════════════════════════════════════════════╣
║  ┌─────────────┐  ┌──────────────────────────────────┐  ║
║  │             │  │                                  │  ║
║  │   Sidebar   │  │        Main Content Area         │  ║
║  │   (30%)     │  │           (70%)                  │  ║
║  │             │  │                                  │  ║
║  │  Features   │  │  - Repository Info               │  ║
║  │  - Core     │  │  - Security Scans                │  ║
║  │  - GitHub   │  │  - Analytics Charts              │  ║
║  │  - Git      │  │  - AI Chat                       │  ║
║  │  - Security │  │                                  │  ║
║  │  - AI       │  │                                  │  ║
║  │             │  │                                  │  ║
║  └─────────────┘  └──────────────────────────────────┘  ║
╠══════════════════════════════════════════════════════════╣
║  Status Bar: ● Online | Profile: default | v2.4.0       ║
║  Footer: [q] Quit [←/→] Navigate [Enter] Select         ║
╚══════════════════════════════════════════════════════════╝
```

### Complete Keyboard Controls

#### **Global Navigation**

| Key | Action | Description |
|-----|--------|-------------|
| `q` | Quit | Exit TUI immediately |
| `Escape` | Go Home | Return to main dashboard |
| `Tab` | Switch Panel | Toggle between sidebar and main content |
| `F1` | Help | Show keyboard shortcuts help |
| `F5` | Refresh | Refresh all data from GitHub |
| `Ctrl+R` | Reload | Force reload current view |

#### **Sidebar Navigation**

| Key | Action | Description |
|-----|--------|-------------|
| `↑` or `k` | Move Up | Select previous feature |
| `↓` or `j` | Move Down | Select next feature |
| `Home` | First Item | Jump to first feature |
| `End` | Last Item | Jump to last feature |
| `Enter` or `l` | Select | Open selected feature |
| `→` | Expand | Expand category (if collapsed) |
| `←` | Collapse | Collapse category |

#### **Main Content Navigation**

| Key | Action | Description |
|-----|--------|-------------|
| `↑` or `k` | Scroll Up | Scroll content up |
| `↓` or `j` | Scroll Down | Scroll content down |
| `Page Up` | Page Up | Scroll one page up |
| `Page Down` | Page Down | Scroll one page down |
| `Ctrl+U` | Half Page Up | Scroll half page up |
| `Ctrl+D` | Half Page Down | Scroll half page down |
| `g` or `Home` | Go to Top | Jump to content top |
| `G` or `End` | Go to Bottom | Jump to content bottom |

#### **Chat Interface** (AI Assistant)

| Key | Action | Description |
|-----|--------|-------------|
| `Ctrl+Up` | Scroll Chat Up | Scroll chat history up |
| `Ctrl+Down` | Scroll Chat Down | Scroll chat history down |
| `Enter` | Send Message | Send chat message |
| `Escape` | Cancel Input | Cancel current input |
| `Ctrl+L` | Clear Chat | Clear chat history |

#### **Data Tables**

| Key | Action | Description |
|-----|--------|-------------|
| `↑`/`↓` | Navigate Rows | Move between rows |
| `←`/`→` | Navigate Columns | Move between columns |
| `Enter` | View Details | Open detailed view |
| `/` | Search | Search table content |
| `s` | Sort | Toggle sort order |
| `f` | Filter | Open filter dialog |

#### **Forms & Inputs**

| Key | Action | Description |
|-----|--------|-------------|
| `Tab` | Next Field | Move to next input field |
| `Shift+Tab` | Previous Field | Move to previous field |
| `Enter` | Submit | Submit form |
| `Escape` | Cancel | Cancel and go back |
| `Ctrl+A` | Select All | Select all text |
| `Ctrl+X` | Cut | Cut selected text |
| `Ctrl+C` | Copy | Copy selected text |
| `Ctrl+V` | Paste | Paste text |

#### **Views & Panels**

| Key | Action | Description |
|-----|--------|-------------|
| `1` | View 1 | Switch to view 1 |
| `2` | View 2 | Switch to view 2 |
| `3` | View 3 | Switch to view 3 |
| `+` | Zoom In | Increase font size |
| `-` | Zoom Out | Decrease font size |
| `0` | Reset Zoom | Reset to default size |
| `b` | Back | Go back to previous view |
| `r` | Refresh | Refresh current view |

#### **Quick Actions**

| Key | Action | Description |
|-----|--------|-------------|
| `n` | New | Create new item |
| `d` | Delete | Delete selected item |
| `e` | Edit | Edit selected item |
| `c` | Copy | Copy selected item |
| `p` | Paste | Paste item |
| `s` | Save | Save current state |
| `x` | Execute | Execute selected action |
| `?` | Help | Show help for current view |

### TUI Views

#### **1. Repository Dashboard**
- **Access:** Select any repository from list
- **Shows:**
  - Repository name and description
  - Stars, forks, issues count
  - Primary language
  - Last updated timestamp
  - Health score badge
- **Actions:**
  - `Enter` - Open detailed view
  - `o` - Open in browser
  - `c` - Clone repository

#### **2. Security Scan View**
- **Access:** Option 35 → Security Scan
- **Shows:**
  - Vulnerability table
  - Severity distribution chart
  - File locations
  - Remediation suggestions
- **Actions:**
  - `Enter` - View vulnerability details
  - `f` - Filter by severity
  - `e` - Export report
  - `a` - Run AI analysis

#### **3. Analytics View**
- **Access:** Option 13 → Analytics
- **Shows:**
  - Star/fork trends
  - Contributor activity
  - Language distribution
  - Traffic analytics (if admin)
- **Actions:**
  - `←`/`→` - Change time period
  - `t` - Toggle chart type
  - `d` - Download data

#### **4. AI Chat View**
- **Access:** Available in most views
- **Shows:**
  - Chat history
  - Input field
  - Status indicator
- **Actions:**
  - Type message and press `Enter`
  - `Ctrl+L` - Clear history
  - `Ctrl+Up/Down` - Scroll history

#### **5. Profile Manager**
- **Access:** Option 31 → Accounts
- **Shows:**
  - Active profile indicator
  - List of available profiles
  - Account details
- **Actions:**
  - `Enter` - Switch profile
  - `n` - New profile
  - `d` - Delete profile

### Status Indicators

#### **Connection Status**
- `● Online` (green) - Connected to GitHub
- `● Offline` (red) - No connection
- `● Rate Limited` (yellow) - API limit reached

#### **Profile Status**
- `Profile: default` - Using default profile
- `Profile: work` - Using work profile
- `Profile: client` - Using client profile

#### **Activity Indicators**
- `⏳ Loading...` - Fetching data
- `✓ Success` - Operation completed
- `✗ Error` - Operation failed
- `⚠ Warning` - Warning message

### Customization

#### **Themes**
Edit `~/.pygitup_config/settings.json`:
```json
{
  "theme": "dark",
  "colors": {
    "primary": "#1f6feb",
    "success": "#238636",
    "warning": "#d29922",
    "error": "#da3633"
  }
}
```

#### **Layout**
```json
{
  "sidebar_width": 30,
  "show_status_bar": true,
  "show_footer": true,
  "auto_refresh": 300
}
```

### Troubleshooting TUI

#### **Display Issues**
- **Problem:** Garbled characters  
  **Solution:** Ensure terminal supports UTF-8

- **Problem:** Colors not showing  
  **Solution:** Use terminal with 256 color support

- **Problem:** Layout broken  
  **Solution:** Resize terminal window (min 80x24)

#### **Input Issues**
- **Problem:** Keys not responding  
  **Solution:** Click on terminal window to focus

- **Problem:** Can't type in chat  
  **Solution:** Press `Tab` to focus input field

#### **Performance Issues**
- **Problem:** Slow rendering  
  **Solution:** Reduce terminal font size or disable animations

- **Problem:** High CPU usage  
  **Solution:** Disable auto-refresh in settings

### Best Practices

1. **Use keyboard shortcuts** - Much faster than mouse
2. **Learn vim-style keys** (`h/j/k/l`) - Universal navigation
3. **Use `?` for context help** - Shows relevant shortcuts
4. **Pin frequently used views** - Quick access via number keys
5. **Customize theme** - Reduce eye strain during long sessions

---

## 🔧 Workflows & Examples

### Daily Development Workflow

```bash
# 1. Create feature branch
python pygitup.py branch create feature/new-feature

# 2. Make changes, then smart push
python pygitup.py --mode smart-push --repo myapp

# 3. Stash WIP if needed
python pygitup.py stash save "WIP: new feature"

# 4. Switch back to main
python pygitup.py branch switch main
```

### Release Process

```bash
# 1. Create tag
python pygitup.py tag create v2.0.0

# 2. Generate changelog and release
python pygitup.py --mode release --repo myapp --version v2.0.0 --generate-changelog

# 3. Update documentation
python pygitup.py --mode generate-docs --repo myapp
```

### Security Compliance

```bash
# 1. Run security scan
python pygitup.py --mode security-scan

# 2. Scan dependencies
python pygitup.py --mode supply-chain

# 3. Generate SBOM
python pygitup.py --mode generate-sbom

# 4. Check token health
python pygitup.py --mode token-health
```

### Multi-Repo Management

```bash
# 1. Portfolio health check
python pygitup.py --mode bulk-mgmt

# 2. Update LICENSE across repos
python pygitup.py --mode multi-repo --multi-repo repo1,repo2,repo3 --file LICENSE

# 3. Get repo intelligence
python pygitup.py --mode repo-info --url https://github.com/user/repo
```

---

## 🐛 Troubleshooting

### Common Issues

#### "Authentication failed (401)"

**Cause:** Invalid or expired token

**Solution:**
```bash
python pygitup.py --mode token-health
# If invalid, rotate token
python pygitup.py --mode rotate-token
```

#### "Token is still encrypted"

**Cause:** Master password not entered

**Solution:**
- Restart PyGitUp
- Enter master password when prompted

#### "AI returned empty response"

**Causes:**
1. Rate limiting
2. Invalid prompt
3. API temporarily unavailable

**Solutions:**
- Wait and retry
- Check AI API key validity
- Verify internet connection

#### "Module not found: cryptography"

**Solution:**
```bash
pip install cryptography
```

#### "pip-audit not found"

**Solution:**
```bash
pip install pip-audit
```

### Debug Mode

Enable debug output:
```bash
export PYGITUP_DEBUG=1
python pygitup.py
```

### Log Files

Location: `~/.pygitup_config/pygitup.log`

Enable logging in config:
```yaml
logging:
  enabled: true
  file: pygitup.log
  level: INFO
```

---

## ✅ Best Practices

### Security

1. **Rotate tokens regularly** (every 90-180 days)
2. **Use fine-grained PATs** when possible
3. **Enable master password** protection
4. **Run security scans** before pushing
5. **Review SBOM** for compliance

### Workflow

1. **Use smart push** to squash fixup commits
2. **Scan TODOs** regularly to track technical debt
3. **Generate documentation** automatically
4. **Use templates** for new projects
5. **Monitor token health** monthly

### Multi-Profile

1. **Separate profiles** for different accounts
2. **Use descriptive names** (work, personal, client)
3. **Switch profiles** before operations
4. **Keep profiles updated** with current tokens

---

## ❓ FAQ

### General

**Q: Is PyGitUp free?**  
A: Yes, completely free and open-source (MIT license).

**Q: Does PyGitUp work with GitHub Enterprise?**  
A: Currently supports GitHub.com only. Enterprise support planned.

**Q: Can I use PyGitUp without AI features?**  
A: Yes! All core features work without AI. AI is opt-in only.

### Security

**Q: How are tokens stored?**  
A: Encrypted using Fernet with PBKDF2 key derivation. Master password required.

**Q: Is my code sent to AI providers?**  
A: Only small snippets for analysis. Full files are not transmitted.

**Q: Does PyGitUp collect telemetry?**  
A: No. All data stays local. Only GitHub API calls are made.

### Features

**Q: Can I create custom templates?**  
A: Currently using built-in templates. Custom template support planned.

**Q: Does PyGitUp support GitLab or Bitbucket?**  
A: Currently GitHub only. Migration feature supports importing from other platforms.

**Q: Can I use PyGitUp in CI/CD pipelines?**  
A: Yes! Use `--batch` mode for non-interactive execution.

---

## 📞 Support

- **GitHub:** https://github.com/frederickabrah/PyGitUp
- **Issues:** https://github.com/frederickabrah/PyGitUp/issues
- **Documentation:** See README.md and CAPABILITIES_GUIDE.md

---

**PyGitUp v2.4.0** - Professional GitHub Automation & Security Platform  
**License:** MIT | **Author:** Frederick Abraham
