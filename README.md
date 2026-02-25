# PyGitUp 🚀

```
  _____       _____ _ _   _   _
 |  __ \     / ____(_) | | | | |
 | |__) |   | |  __ _| |_| | | |_ __
 |  ___/    | | |_ | | __| | | | '_ \
 | |     _  | |__| | | |_| |_| | |_) |
 |_|    (_)  \_____|_|\__|_|\___/| .__/
                               | |
                               |_|
```

**PyGitUp** is a professional CLI & TUI command center for **comprehensive GitHub automation**. It combines Git operations, GitHub API integration, security scanning, AI-powered assistance, and intelligence analytics into a single unified platform.

**Version:** 2.4.0 (Security-Enhanced)  
**Total Features:** 40+ across 8 categories

---

## 🎯 Quick Start

```bash
# Install
git clone https://github.com/frederickabrah/PyGitUp.git
cd PyGitUp
pip install -r requirements.txt
pip install -e .

# Launch interactive mode
python pygitup.py

# Or use CLI directly
python pygitup.py --mode repo-info --url https://github.com/frederickabrah/PyGitUp
```

---

## 📋 Core Capabilities

### 🔧 **Git & Repository Operations**
- **Project Upload** - Initialize & upload entire directories
- **File Management** - Single/batch file uploads
- **Template Projects** - Scaffold from templates (React, Django, etc.)
- **Smart Push** - Squash meaningless commits automatically
- **Branch/Stash/Tag Management** - Full Git operation automation
- **Cherry-Pick** - Apply specific commits across branches
- **Repository Migration** - Mirror from GitLab/Bitbucket

### 🐙 **GitHub API Integration**
- **Release Management** - Create releases with auto-changelogs
- **Issue Automation** - Scan TODOs → create issues
- **Pull Requests** - Create/manage PRs, request reviews
- **Gists** - Create/edit GitHub Gists
- **Webhooks** - Configure repository webhooks
- **Actions** - Enable/disable/manage workflows
- **Repository Control** - Visibility, deletion, bulk operations

### 🔒 **Security & Compliance** (NEW)
- **Enhanced Security Scan** - SAST + 60+ secret pattern detection
- **Secret Detection** - GitHub tokens, AWS keys, API keys, private keys
- **Dependency Scanning** - Vulnerability detection via pip-audit & OSV
- **SBOM Generation** - SPDX & CycloneDX formats for compliance
- **Token Management** - Encrypted storage, rotation, health monitoring
- **Audit Logging** - JSON-structured security event tracking
- **Fork Intelligence** - Analyze fork networks for community contributions

### 🤖 **Autonomous AI Agent** (ADVANCED)
- **Chain-of-Thought Reasoning** - Multi-step problem solving
- **Tool-Use Capabilities** - Executes system tasks natively
- **Persistent Assistant** - Remembers context across sessions
- **AI Diagnostic Loop** - Self-healing system that analyzes failures and proposes code repairs
- **Code Reading & Writing** - Full-stack AI engineer capabilities
- **Automated Debugging** - Executes commands, analyzes errors, suggests fixes

### 🤖 **AI-Powered Features**
- **AI Commit Messages** - Semantic commits from diffs
- **AI Issue Triage** - Analyze issues & suggest fixes
- **AI Release Notes** - Auto-generate from commit history
- **AI README Generation** - From project structure
- **AI Workflow Generation** - Custom CI/CD pipelines
- **Code Mentorship** - Real-time coding assistance

### 📊 **Intelligence & Analytics**
- **Repository Health Scoring** - 0-100% health metrics
- **Portfolio Management** - Multi-repo dashboard with recommendations
- **Predictive Analytics** - Growth forecasting from engagement data
- **OSINT Reconnaissance** - Social metadata, digital footprints
- **Traffic Analytics** - Clone/view trends (requires admin access)
- **Language Distribution** - Codebase composition analysis

### 🖥️ **Immersive TUI Dashboard**
- **Engineering Hub** - Manage profiles, contexts, AI tasks
- **Intelligence Center** - Real-time repository visualization
- **Native Operations** - Dedicated views for PRs, Gists, SSH keys
- **Interactive Menus** - 40+ features accessible via keyboard

---

## 🎛️ Usage Examples

### **Interactive Mode**
```bash
python pygitup.py
# Select from 40+ options in the menu
```

### **CLI Commands**

```bash
# Upload project
python pygitup.py --mode project --path ./myproject --private

# Security scan
python pygitup.py --mode security-scan

# Repository intelligence
python pygitup.py --mode repo-info --url https://github.com/user/repo

# Bulk repository management
python pygitup.py --mode bulk-mgmt

# Generate SBOM
python pygitup.py --mode generate-sbom

# Token health check
python pygitup.py --mode token-health

# AI-powered commit
python pygitup.py --mode ai-commit

# Launch TUI
python pygitup.py --mode tui
```

### **Sub-Commands**
```bash
# Branch management
python pygitup.py branch list
python pygitup.py branch create feature-x
python pygitup.py branch switch main

# Stash operations
python pygitup.py stash save "WIP"
python pygitup.py stash list
python pygitup.py stash pop

# Tag management
python pygitup.py tag create v1.0.0
python pygitup.py tag list

# Gist management
python pygitup.py gist create
python pygitup.py gist list

# Pull requests
python pygitup.py pr create --title "Fix bug" --base main
python pygitup.py pr list
```

---

## 🔐 Security Features

### **What PyGitUp Scans For:**
- ✅ 60+ secret patterns (GitHub tokens, AWS keys, API keys, private keys)
- ✅ Command injection vulnerabilities (CWE-78)
- ✅ SQL injection (CWE-89)
- ✅ Insecure deserialization (CWE-502)
- ✅ Arbitrary code execution (CWE-95)
- ✅ Hardcoded credentials (CWE-798)
- ✅ Security misconfigurations (CWE-295)

### **Compliance Ready:**
- ✅ SBOM generation (SPDX 2.3, CycloneDX 1.4)
- ✅ Encrypted credential storage (Fernet + PBKDF2)
- ✅ Audit logging (9 event types)
- ✅ Token rotation workflows
- ✅ Dependency vulnerability tracking

---

## 📊 Repository Health Scoring

PyGitUp calculates health scores (0-100%) based on:
- **Engagement (30 pts)** - Stars & forks
- **Maintenance (30 pts)** - Issue management
- **Activity (25 pts)** - Recent updates
- **Documentation (15 pts)** - Wiki, pages, license

**Example Output:**
```
Repository                               | Health | Status
-----------------------------------------|--------|------------
frederickabrah/PyGitUp                   |  78%   | Good
frederickabrah/TCM                       |  75%   | Good
frederickabrah/awesome-gemini-cli        |  51%   | Needs Work
```

---

## 🤖 AI Integration

### **Supported Providers:**
- Google Gemini (default)
- OpenAI GPT (configurable)
- Anthropic Claude (configurable)

### **AI Features:**
- Commit message generation
- Issue analysis & triage
- Release notes automation
- README generation
- CI/CD workflow architecture
- Code remediation suggestions

**Privacy:** AI features are **opt-in only**. All core features work without AI.

---

## 📁 Configuration

### **Multi-Profile Support**
```bash
# Configure profiles
python pygitup.py --mode configure

# Switch profiles
python pygitup.py --mode accounts
```

### **Encrypted Storage**
- Credentials stored in `~/.pygitup_config/profiles/`
- Master password protection (PBKDF2 + Fernet encryption)
- File permissions: 0600 (owner read/write only)

### **Environment Variables**
```bash
export GITHUB_TOKEN=your_token
export GEMINI_API_KEY=your_ai_key
export PYGITUP_DEBUG=1  # Enable debug mode
```

---

## 🎯 Use Cases

### **Solo Developers**
- Automate repository initialization
- Smart commit management
- Quick file uploads
- Personal project templates

### **Development Teams**
- Code review automation
- Branch/stash management
- Team analytics
- Documentation generation

### **Security Teams**
- SAST scanning
- Dependency auditing
- SBOM generation
- Secret detection

### **Open Source Maintainers**
- Issue triage automation
- Fork network analysis
- Release management
- Community metrics

### **DevOps Engineers**
- Workflow automation
- Webhook management
- Multi-repo deployments
- Platform migrations

---

## 📚 Documentation

- **[MANUAL.md](MANUAL.md)** - Complete user guide with tutorials
- **[CAPABILITIES_GUIDE.md](CAPABILITIES_GUIDE.md)** - Feature reference
- **[README.md](README.md)** - Quick start and overview
- **[SECURITY.md](SECURITY.md)** - Security policy
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** - Community guidelines
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Contribution guide

---

## 🚀 Installation

### **From Source**
```bash
git clone https://github.com/frederickabrah/PyGitUp.git
cd PyGitUp
pip install -r requirements.txt
pip install -e .
```

### **Requirements**
- Python 3.6+
- See `requirements.txt` for dependencies
- `cryptography` library for encryption
- `pip-audit` for dependency scanning

---

## ❤️ Support the Project

PyGitUp is an open-source project maintained for the developer community. If this tool enhances your productivity, consider supporting its development.

**[➡️ Support on GitHub](https://github.com/sponsors/frederickabrah)**

**Ways to contribute:**
- ⭐ Star the repository
- 🐛 Report bugs
- 💡 Suggest features
- 📝 Improve documentation
- 🔧 Submit PRs

---

## 🔗 Quick Links

- **GitHub:** https://github.com/frederickabrah/PyGitUp
- **Issues:** https://github.com/frederickabrah/PyGitUp/issues
- **Security:** https://github.com/frederickabrah/PyGitUp/security
- **Full Capabilities:** [CAPABILITIES_GUIDE.md](CAPABILITIES_GUIDE.md)

---

## 📄 License & Author

**License:** MIT  
**Author:** Frederick Abraham  
**Version:** 2.4.0 (Security-Enhanced)  
**Last Updated:** February 22, 2026

---

**PyGitUp** - Professional GitHub Automation & Security Platform 🚀
