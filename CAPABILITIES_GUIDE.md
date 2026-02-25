# 🚀 PyGitUp Complete Capabilities Guide

**Version:** 2.4.0 (Security-Enhanced)  
**Last Updated:** February 22, 2026  
**Total Features:** 40+ across 8 categories

---

## 📖 Table of Contents

1. [Overview](#overview)
2. [Core Operations](#core-operations)
3. [Sub-Commands](#sub-commands)
4. [Command-Line Reference](#command-line-reference)
5. [Workflow Examples](#workflow-examples)
6. [Security Features](#security-features)
7. [AI Capabilities](#ai-capabilities)
8. [Use Cases by User Type](#use-cases-by-user-type)

---

## 🎯 Overview

PyGitUp is a **comprehensive GitHub automation platform** that combines:
- 🔧 Git operations management
- 🐙 GitHub API integration
- 🔒 Security scanning & compliance
- 🤖 AI-powered assistance
- 📊 Intelligence & analytics

**40+ features** accessible via CLI, interactive menu, or TUI dashboard.

---

## 📋 Core Operations

### **1-4: Project & File Management**

| # | Feature | CLI Command | Description |
|---|---------|-------------|-------------|
| 1 | **Upload Project** | `--mode project` | Upload entire directory to GitHub |
| 2 | **Upload Single File** | `--mode file` | Upload one file to repository |
| 3 | **Batch Upload** | `--mode batch` | Upload multiple files at once |
| 4 | **Create from Template** | `--mode template` | Scaffold project from template |

**Use Cases:**
- Initialize new repositories from local projects
- Quick file updates without Git commands
- Bulk file management across repositories
- Quick project setup with pre-configured templates

---

### **5-9: Release & Version Management**

| # | Feature | CLI Command | Description |
|---|---------|-------------|-------------|
| 5 | **Create Release** | `--mode release` | Create GitHub release with tag |
| 6 | **Multi-Repo Update** | `--mode multi-repo` | Update file across repositories |
| 7 | **Scan TODOs** | `--mode scan-todos` | Convert code comments to issues |
| 8 | **Offline Queue** | `--mode offline-queue` | Queue commits for later |
| 9 | **Process Queue** | `--mode process-queue` | Upload queued commits |

**Use Cases:**
- Version releases with changelogs
- Monorepo file synchronization
- Automated task tracking from code
- Work without internet connectivity

---

### **10-14: Code Review & Documentation**

| # | Feature | CLI Command | Description |
|---|---------|-------------|-------------|
| 10 | **Request Review** | `--mode request-review` | Auto-request code reviews |
| 11 | **Smart Push** | `--mode smart-push` | Squash meaningless commits |
| 12 | **Generate Docs** | `--mode generate-docs` | Auto-create documentation |
| 13 | **Generate Analytics** | `--mode analytics` | Collaboration metrics report |
| 14 | **Configure** | `--mode configure` | Setup credentials & profiles |

**Use Cases:**
- Team collaboration automation
- Clean commit history
- Documentation from code comments
- Team productivity insights

---

### **15-18: Git Operations**

| # | Feature | CLI Command | Description |
|---|---------|-------------|-------------|
| 15 | **Manage Branches** | `branch` subcommand | Create/delete/switch branches |
| 16 | **Manage Stashes** | `stash` subcommand | Save/apply/pop stashes |
| 17 | **Manage Tags** | `tag` subcommand | Create/manage version tags |
| 18 | **Cherry-Pick** | `--mode cherry-pick` | Apply specific commits |

**Use Cases:**
- Branch management without Git commands
- Work-in-progress storage
- Release tagging
- Selective commit merging

---

### **19-22: GitHub Features**

| # | Feature | CLI Command | Description |
|---|---------|-------------|-------------|
| 19 | **Manage Gists** | `gist` subcommand | Create/edit GitHub Gists |
| 20 | **Manage Webhooks** | `webhook` subcommand | Configure repository webhooks |
| 21 | **Manage Actions** | `actions` subcommand | Enable/disable workflows |
| 22 | **Manage PRs** | `pr` subcommand | Create/manage Pull Requests |

**Use Cases:**
- Code snippet sharing
- CI/CD integration
- Automation workflow control
- Code review management

---

### **23-26: Security & Repository Management**

| # | Feature | CLI Command | Description |
|---|---------|-------------|-------------|
| 23 | **Security Audit** | `--mode audit` | SAST + dependency scanning |
| 24 | **Change Visibility** | `--mode visibility` | Toggle public/private |
| 25 | **Repo Info** | `--mode repo-info` | Repository intelligence |
| 26 | **Delete Repository** | `--mode delete-repo` | Remove GitHub repositories |

**Use Cases:**
- Security compliance auditing
- Access control management
- Due diligence on repositories
- Repository cleanup

---

### **27-29: Advanced Intelligence**

| # | Feature | CLI Command | Description |
|---|---------|-------------|-------------|
| 27 | **Bulk Management** | `--mode bulk-mgmt` | Portfolio health dashboard |
| 28 | **Migrate Repository** | `--mode migrate` | Mirror from other platforms |
| 29 | **Fork Intelligence** | `--mode fork-intel` | Analyze fork networks |

**Use Cases:**
- Multi-repo portfolio oversight
- Platform migration (GitLab → GitHub)
- Community contribution tracking

---

### **30-32: AI-Powered Features**

| # | Feature | CLI Command | Description |
|---|---------|-------------|-------------|
| 30 | **AI Commit** | `--mode ai-commit` | Auto-generate commit messages |
| 31 | **AI Diagnostic** | `--mode ai-diagnostic` | List available AI models |
| 32 | **AI Issue Triage** | `--mode 40` | Analyze issues & suggest fixes |

**Use Cases:**
- Commit message automation
- AI capability assessment
- Smart issue debugging

---

### **33-34: Infrastructure & UI**

| # | Feature | CLI Command | Description |
|---|---------|-------------|-------------|
| 33 | **SSH Manager** | `--mode ssh-setup` | Setup SSH infrastructure |
| 34 | **TUI Dashboard** | `--mode tui` | Text-based graphical interface |

**Use Cases:**
- Secure authentication setup
- Visual repository management

---

### **35-40: Enhanced Security (NEW)**

| # | Feature | CLI Command | Description |
|---|---------|-------------|-------------|
| 35 | **Security Scan** | `--mode security-scan` | SAST + 60+ secret patterns |
| 36 | **Token Health** | `--mode token-health` | Validate & rotate tokens |
| 37 | **Supply Chain Scan** | `--mode supply-chain` | Dependency vulnerability scan |
| 38 | **Generate SBOM** | `--mode generate-sbom` | Software Bill of Materials |
| 39 | **Rotate Token** | `--mode rotate-token` | Guided token rotation |
| 40 | **Issue Triage** | `--mode 40` | Interactive AI issue analysis |

**Use Cases:**
- Comprehensive security auditing
- Credential lifecycle management
- Compliance reporting (SBOM)
- Security maintenance

---

## 🔧 Sub-Commands

### **Branch Management**
```bash
python pygitup.py branch list              # List all branches
python pygitup.py branch create <name>     # Create new branch
python pygitup.py branch delete <name>     # Delete branch
python pygitup.py branch switch <name>     # Switch to branch
```

### **Stash Management**
```bash
python pygitup.py stash save [message]     # Save stash
python pygitup.py stash list               # List all stashes
python pygitup.py stash apply              # Apply latest stash
python pygitup.py stash pop                # Apply and remove
python pygitup.py stash drop               # Delete latest stash
```

### **Tag Management**
```bash
python pygitup.py tag list                 # List all tags
python pygitup.py tag create <name>        # Create tag
python pygitup.py tag delete <name>        # Delete tag
```

### **Gist Management**
```bash
python pygitup.py gist create              # Create new gist
python pygitup.py gist list                # List all gists
python pygitup.py gist edit                  # Edit existing gist
python pygitup.py gist delete                # Delete gist
```

### **Webhook Management**
```bash
python pygitup.py webhook add              # Add webhook
python pygitup.py webhook list             # List webhooks
python pygitup.py webhook delete           # Delete webhook
python pygitup.py webhook test             # Test webhook
```

### **Actions Management**
```bash
python pygitup.py actions list             # List workflows
python pygitup.py actions enable           # Enable workflow
python pygitup.py actions disable          # Disable workflow
python pygitup.py actions run              # Trigger workflow
```

### **Pull Request Management**
```bash
python pygitup.py pr create                # Create PR
python pygitup.py pr list                  # List PRs
python pygitup.py pr merge                 # Merge PR
python pygitup.py pr review                # Request review
```

---

## 💻 Command-Line Reference

### **Global Options**
```bash
--mode <mode>          # Operation mode (40 options)
--repo <name>          # Target repository name
--config <path>        # Custom configuration file
--dry-run              # Simulate without making changes
--batch                # Batch mode (no interactive prompts)
-h, --help             # Show help message
```

### **File Operations**
```bash
--file <path>          # Single file to upload
--path <path>          # Directory path for upload
--files <list>         # Comma-separated file list
--message <msg>        # Commit message
```

### **Project Operations**
```bash
--template <name>      # Project template name
--variables <k=v>      # Template variables (key=value)
--private              # Make repository private
--public               # Make repository public
--description <text>   # Repository description
```

### **Release Operations**
```bash
--version <tag>        # Release version tag
--name <name>          # Release name
--generate-changelog   # Auto-generate from commits
```

### **Issue Operations**
```bash
--assign <users>       # Assign issues to users (comma-separated)
--no-assign            # Disable automatic assignment
--reviewers <users>    # Request code reviews
```

### **Analytics & Reports**
```bash
--period <period>      # Analytics period (e.g., last-month)
--output <dir>         # Output directory for reports
--url <url>            # Repository URL for info
```

### **Advanced Options**
```bash
--squash-pattern <pat> # Commit message patterns to squash
--commit-hash <hash>   # Specific commit hash
--multi-repo <list>    # Multiple repositories (comma-separated)
```

---

## 🚀 Workflow Examples

### **1. Initialize New Project**

```bash
# Create from template
python pygitup.py --mode template --template react-app --repo myapp

# Or upload existing project
python pygitup.py --mode project --path ./myproject --private

# Interactive mode
python pygitup.py
# Select Option 1 or 4
```

### **2. Daily Development Workflow**

```bash
# Create feature branch
python pygitup.py branch create feature/new-feature

# Make changes, then smart push
python pygitup.py --mode smart-push --repo myapp

# Stash WIP if needed
python pygitup.py stash save "WIP: new feature"

# Switch back to main
python pygitup.py branch switch main
```

### **3. Release Process**

```bash
# Create tag
python pygitup.py tag create v2.0.0

# Generate changelog and create release
python pygitup.py --mode release --repo myapp --version v2.0.0 --generate-changelog

# Update documentation
python pygitup.py --mode generate-docs --repo myapp
```

### **4. Security & Compliance**

```bash
# Run comprehensive security audit
python pygitup.py --mode audit --repo myapp

# Enhanced security scan
python pygitup.py --mode security-scan

# Check token health
python pygitup.py --mode token-health

# Scan dependencies
python pygitup.py --mode supply-chain

# Generate SBOM for compliance
python pygitup.py --mode generate-sbom --format spdx
```

### **5. Multi-Repository Management**

```bash
# Portfolio health dashboard
python pygitup.py --mode bulk-mgmt

# Update LICENSE across all repos
python pygitup.py --mode multi-repo --multi-repo repo1,repo2,repo3 --file LICENSE

# Get detailed repo intelligence
python pygitup.py --mode repo-info --url https://github.com/user/repo

# Analyze fork network
python pygitup.py --mode fork-intel --url https://github.com/user/repo
```

### **6. AI-Powered Workflow**

```bash
# Generate commit message from diff
python pygitup.py --mode ai-commit

# Analyze and triage issues
python pygitup.py --mode 40  # Interactive issue analysis

# List available AI models
python pygitup.py --mode ai-diagnostic
```

### **7. TUI Dashboard**

```bash
# Launch graphical interface
python pygitup.py --mode tui

# Or in interactive mode, select Option 34
```

---

## 🔒 Security Features Deep Dive

### **Secret Detection (60+ Patterns)**
- GitHub tokens (all types)
- AWS credentials
- GCP/Azure keys
- Database connection strings
- API keys (Stripe, Twilio, SendGrid, Slack)
- Private keys (RSA, EC, SSH, PGP)
- JWT tokens

### **Static Analysis (SAST)**
- Command injection (CWE-78)
- SQL injection (CWE-89)
- Insecure deserialization (CWE-502)
- Arbitrary code execution (CWE-95)
- Hardcoded secrets (CWE-798)
- Security misconfiguration (CWE-295)

### **Supply Chain Security**
- Dependency vulnerability scanning
- Integration with pip-audit & OSV.dev
- SBOM generation (SPDX 2.3, CycloneDX 1.4)
- Dependency health scoring

### **Token Management**
- Encrypted credential storage (Fernet + PBKDF2)
- Token rotation workflows
- Expiration tracking
- Health monitoring

### **Audit Logging**
- 9 event types tracked
- JSON-structured logs
- Security event notifications
- Compliance ready

---

## 🤖 AI Capabilities

### **AI-Powered Features**
1. **Commit Message Generation** - Semantic commits from diffs
2. **Release Notes** - Automated from commit history
3. **README Generation** - From project structure
4. **Workflow Generation** - Custom CI/CD pipelines
5. **Issue Triage** - Analysis and fix suggestions
6. **Code Mentorship** - Real-time coding assistance
7. **Security Analysis** - Enhanced vulnerability assessment

**Advanced Guide:** See **[AGENT_GUIDE.md](AGENT_GUIDE.md)** for technical details on @-file injection and Cortex history compression.

---

## 🖥️ TUI Navigation

| Key | Action |
|-----|--------|
| **B** | Toggle Sidebar visibility |
| **R** | Sync/Refresh data |
| **Q** | Quit PyGitUp |
| **Esc** | Return to Home View |
| **Ctrl+L** | Clear AI Assistant memory |

---

## 📊 Intelligence & Analytics

### **Repository Intelligence**
- Health scoring (0-100%)
- Activity metrics
- Contributor analysis
- Language breakdown
- Community profile assessment

### **Portfolio Management**
- Multi-repo dashboard
- Aggregate statistics
- Health distribution
- Top performers ranking
- Actionable recommendations

### **OSINT Capabilities**
- Repository metadata extraction
- Social media link detection
- Dependency health analysis
- CI/CD status detection
- Used-by tracking
- Sponsorship detection

### **Predictive Analytics**
- Growth forecasting
- Star trajectory projection
- Maintenance health trends
- Contributor impact analysis

---

## 👥 Use Cases by User Type

### **Solo Developers**
- Automate repository initialization
- Smart commit management
- Quick file uploads
- Personal project templates
- Token rotation reminders

### **Development Teams**
- Code review automation
- Branch management
- Stash sharing
- Team analytics
- Documentation generation

### **Security Teams**
- SAST scanning
- Dependency auditing
- SBOM generation
- Secret detection
- Compliance reporting

### **DevOps Engineers**
- Workflow automation
- Webhook management
- Actions control
- Multi-repo deployments
- Migration assistance

### **Open Source Maintainers**
- Issue triage automation
- Fork network analysis
- Community metrics
- Release management
- Template repositories

### **Consultants & Agencies**
- Multi-client repo management
- Template-based scaffolding
- Bulk operations
- Migration tools
- Portfolio reporting

### **Researchers & Analysts**
- Repository OSINT
- Dependency health tracking
- Community contribution analysis
- Growth trend analysis
- Digital footprint mapping

---

## 🎓 Quick Reference Card

### **Most Used Commands**
```bash
# Upload project
python pygitup.py --mode project --path ./myproject

# Smart push
python pygitup.py --mode smart-push --repo myrepo

# Security scan
python pygitup.py --mode security-scan

# Repo info
python pygitup.py --mode repo-info --url https://github.com/user/repo

# Launch TUI
python pygitup.py --mode tui
```

### **Interactive Mode**
```bash
python pygitup.py
# Then select from 40 options
```

### **Help**
```bash
python pygitup.py --help
python pygitup.py --mode <mode> --help
```

---

## 📞 Support & Resources

- **GitHub:** https://github.com/frederickabrah/PyGitUp
- **Issues:** https://github.com/frederickabrah/PyGitUp/issues
- **Security:** https://github.com/frederickabrah/PyGitUp/security
- **Documentation:** See README.md for complete guide

---

**PyGitUp v2.4.0** - Professional GitHub Automation & Security Platform  
**License:** MIT  
**Author:** Frederick Abraham
