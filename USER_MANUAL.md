# 📘 PyGitUp Complete User Manual

**Version:** 2.4.6  
**Last Updated:** March 2026

---

## 📋 TABLE OF CONTENTS

1. [Getting Started](#getting-started)
2. [Core Operations (Options 1-4)](#core-operations)
3. [GitHub Operations (Options 5-9, 19-22, 24-29)](#github-operations)
4. [Git Operations (Options 15-18)](#git-operations)
5. [Security Features (Options 23, 35-39, 41-45)](#security-features)
6. [AI Features (Options 30-32, 40)](#ai-features)
7. [Tools & Utilities (Options 10-14, 31, 33-34)](#tools--utilities)
8. [Command-Line Reference](#command-line-reference)
9. [Troubleshooting](#troubleshooting)

---

## 🚀 GETTING STARTED

### **Installation**

```bash
# Clone the repository
git clone https://github.com/frederickabrah/PyGitUp.git
cd PyGitUp

# Install dependencies
pip install -r requirements.txt

# Install PyGitUp
pip install -e .

# Launch PyGitUp
python pygitup.py
```

### **First-Time Setup**

1. **Run PyGitUp:**
   ```bash
   python pygitup.py
   ```

2. **Configure Credentials (Option 14):**
   - Enter your GitHub username
   - Generate a Personal Access Token at: https://github.com/settings/tokens
   - Required scopes: `repo`, `workflow`, `admin:org` (optional), `gist` (optional)
   - Set a master password for encryption

3. **Verify Setup (Option 36):**
   - Check token health
   - Verify connection to GitHub

---

## 📦 CORE OPERATIONS (Options 1-4)

### **Option 1: Upload/Update Project Directory**

**WHAT IT DOES:**  
Uploads your entire project folder to GitHub as a new repository (or updates existing one).

**WHEN TO USE:**
- ✅ Starting a new project
- ✅ Moving local code to GitHub
- ✅ Syncing entire project structure

**HOW TO USE:**
1. Select Option 1
2. Enter project path (or use current directory)
3. Enter repository name
4. Add description (optional)
5. Choose public/private
6. PyGitUp will:
   - Initialize git repository
   - Create GitHub repository
   - Add all files
   - Commit and push

**EXAMPLE:**
```
📂 Enter project path: /home/user/myproject
📝 Repository name: myproject
📄 Description: My awesome project
🔒 Make private? (y/n): y
```

**TIPS:**
- Excludes: `node_modules`, `venv`, `.git`, `__pycache__`
- Warns about sensitive files (`.env`, `*.key`)
- Creates `.gitignore` automatically

---

### **Option 2: Upload/Update Single File**

**WHAT IT DOES:**  
Uploads a single file to an existing GitHub repository.

**WHEN TO USE:**
- ✅ Quick file update
- ✅ Adding a new file
- ✅ Fixing a typo in documentation

**HOW TO USE:**
1. Select Option 2
2. Enter repository name
3. Choose file from list or enter path
4. Enter commit message

**EXAMPLE:**
```
📝 Repository name: myproject
1: README.md
2: main.py
3: config.json
> 1
📄 Commit message: Update README
```

**TIPS:**
- Shows numbered list of files in current directory
- Can enter custom path: `/path/to/file.txt`
- Updates file if it exists, creates if new

---

### **Option 3: Batch Upload Multiple Files**

**WHAT IT DOES:**  
Uploads multiple files in one operation.

**WHEN TO USE:**
- ✅ Uploading several related files
- ✅ Syncing a folder's contents
- ✅ Bulk file updates

**HOW TO USE:**
1. Select Option 3
2. Enter repository name
3. Enter file paths (comma-separated)
4. Enter commit message

**EXAMPLE:**
```
📝 Repository name: myproject
📁 Files: README.md,main.py,config.json
📄 Commit message: Add project files
```

**TIPS:**
- Use wildcards: `*.py`, `src/*`
- Relative or absolute paths work
- Shows progress bar during upload

---

### **Option 4: Create Project from Template**

**WHAT IT DOES:**  
Creates a new project from a pre-configured template.

**AVAILABLE TEMPLATES:**
- `fastapi` - FastAPI backend
- `react` - React frontend
- `django` - Django web app
- `flask` - Flask microframework
- `rust-cli` - Rust command-line tool

**WHEN TO USE:**
- ✅ Starting a new project quickly
- ✅ Using best-practice structure
- ✅ Boilerplate code setup

**HOW TO USE:**
1. Select Option 4
2. Choose template
3. Enter project name
4. PyGitUp creates structure and pushes to GitHub

**EXAMPLE:**
```
📋 Available templates: fastapi, react, django, flask, rust-cli
📝 Template: fastapi
📁 Project name: myapi
```

**TIPS:**
- Templates include `.gitignore`, `README.md`, basic structure
- Custom templates can be added to `./templates/` folder

---

## 🔐 SECURITY FEATURES (Options 23, 35-39, 41-45)

### **Option 23: Run Security Audit**

**WHAT IT DOES:**  
Comprehensive security scan including:
- Local SAST (Static Application Security Testing)
- Dependency vulnerability check
- GitHub security alerts (Dependabot, Secret Scanning)

**WHEN TO USE:**
- ✅ Before deploying to production
- ✅ After adding new dependencies
- ✅ Regular security maintenance

**HOW TO USE:**
1. Select Option 23
2. Enter repository name (for remote scan)
3. Review findings

**OUTPUT:**
```
🛡️ Security Audit
├─ Local SAST: 3 vulnerabilities found
├─ Dependencies: 2 vulnerabilities found
└─ GitHub Alerts: 0 issues
```

**TIPS:**
- Run monthly for best security
- Fix CRITICAL issues immediately
- Review HIGH issues within a week

---

### **Option 35: Enhanced Security Scan**

**WHAT IT DOES:**  
Advanced security scanning with:
- 60+ secret pattern detection
- AST-based vulnerability analysis
- Entropy analysis for unknown secrets
- Optional AI enhancement

**DETECTS:**
- GitHub tokens (`ghp_*`, `github_pat_*`)
- AWS credentials
- Database passwords
- API keys (Stripe, Twilio, SendGrid)
- Private keys (RSA, EC, SSH)
- Command injection vulnerabilities
- SQL injection vulnerabilities
- Hardcoded secrets

**WHEN TO USE:**
- ✅ Before committing code
- ✅ After cloning a repository
- ✅ Security compliance requirements

**HOW TO USE:**
1. Select Option 35
2. Choose AI enhancement (y/n)
3. Review findings

**EXAMPLE OUTPUT:**
```
🛡️ Enhanced Security Scan
Scanning 234 files...
Estimated time: 117-234 seconds

⚠️  ALERT: 12 potential vulnerabilities found!
Summary: 2 CRITICAL, 10 HIGH

┌──────────┬─────────────┬────────────┬─────────────┐
│ Severity │ Type        │ Location   │ Description │
├──────────┼─────────────┼────────────┼─────────────┤
│ CRITICAL │ Injection   │ main.py:42 │ Command     │
│          │             │            │ Injection   │
│ HIGH     │ Secret      │ config.py:5│ AWS Key     │
└──────────┴─────────────┴────────────┴─────────────┘
```

**TIPS:**
- AI enhancement provides custom remediation code
- False positives possible - review each finding
- Run in CI/CD pipeline for automated security

---

### **Option 41: Undo Last Commit**

**WHAT IT DOES:**  
Undoes the last commit while keeping your changes staged.

**WHEN TO USE:**
- ✅ Committed wrong files
- ✅ Wrong commit message
- ✅ Need to reorganize commits

**HOW TO USE:**
1. Select Option 41
2. Confirm with "yes"
3. Make corrections
4. Commit again

**EXAMPLE:**
```
↩️  Undo Last Commit
Will undo: abc1234 Fix typo

Proceed with undo? (yes/NO): yes
✅ Successfully undid last commit.

Next steps:
  1. Remove secrets from staged files
  2. Commit again: git commit -m 'new message'
```

**TIPS:**
- Changes remain staged - use `git reset` to unstage
- Use `--dry-run` to test first
- Doesn't affect remote - use `git push --force` carefully

---

### **Option 42: Purge File from Git History**

**WHAT IT DOES:**  
Completely removes a file from ALL commits in history.

**⚠️ WARNING:** This rewrites history! All collaborators must re-clone.

**WHEN TO USE:**
- ✅ Accidentally committed secrets
- ✅ Sensitive file in history
- ✅ Large file that shouldn't be tracked

**HOW TO USE:**
1. Select Option 42
2. Enter file path
3. Confirm deletion
4. Force push: `git push --force`

**EXAMPLE:**
```
🧹 Purge File from Git History
File: .env

⚠️  CRITICAL: This will rewrite history!
File found in 5 commits:
  abc1234 Add config
  def5678 Update settings
  ...

Confirm? (yes/NO): yes
✅ File purged from all history
```

**TIPS:**
- Creates backup branch automatically
- Tell team to re-clone after
- Use `--dry-run` to see what would happen
- Safer than `git filter-branch` manually

---

### **Option 43: Purge Sensitive String from History**

**WHAT IT DOES:**  
Replaces a specific string (like a password) with `***REDACTED***` in all commits.

**⚠️ WARNING:** Rewrites history!

**WHEN TO USE:**
- ✅ Committed API key
- ✅ Password in code
- ✅ Any sensitive string

**HOW TO USE:**
1. Select Option 43
2. Enter the exact string to remove
3. Confirm
4. Force push

**EXAMPLE:**
```
✂️  Purge Sensitive String
String: sk_live_abc123xyz

⚠️  This will replace with ***REDACTED***
Found in 3 commits

Proceed? (yes/NO): yes
✅ String redacted from history
```

**TIPS:**
- Must be EXACT string match
- ROTATE the secret immediately after!
- Old commits still have it in backup branch

---

### **Option 44: Interactive History Editor**

**WHAT IT DOES:**  
Interactive UI to edit, delete, or reorganize commits.

**FEATURES:**
- View last 15 commits
- Edit commit messages
- Delete commits
- Reorder commits

**WHEN TO USE:**
- ✅ Cleaning up commit history
- ✅ Before merging feature branch
- ✅ Preparing for code review

**HOW TO USE:**
1. Select Option 44
2. Choose commit number
3. Select action (Edit/Delete/Cancel)
4. Confirm changes

**TIPS:**
- Creates backup before changes
- Use `--dry-run` to preview
- Don't edit public/pushed commits

---

### **Option 45: Remediation Help & Guide**

**WHAT IT DOES:**  
Shows help and best practices for remediation operations.

**WHEN TO USE:**
- ✅ Before using purge features
- ✅ Learning security best practices
- ✅ Incident response

---

## 🤖 AI FEATURES (Options 30-32, 40)

### **Option 30: AI-Powered Semantic Commit**

**WHAT IT DOES:**  
Uses AI to analyze your changes and generate a professional commit message.

**WHEN TO USE:**
- ✅ Large commits with many changes
- ✅ Want conventional commits
- ✅ Non-native English speaker

**HOW TO USE:**
1. Stage your changes: `git add .`
2. Select Option 30
3. Review AI-generated message
4. Accept or edit

**EXAMPLE:**
```
🤖 AI is analyzing staged changes...
✅ Generated commit message:

feat(auth): implement OAuth2 authentication

- Add OAuth2 client credentials flow
- Implement token refresh mechanism
- Add unit tests for auth module

Accept? (y/n): y
✅ Commit created successfully
```

**TIPS:**
- Requires AI API key configured
- Works best with clear, focused changes
- Edit message if needed before committing

---

### **Option 32: AI Diagnostic (List Models)**

**WHAT IT DOES:**  
Shows available AI models for code assistance.

**WHEN TO USE:**
- ✅ Checking AI capabilities
- ✅ Choosing best model for task

---

### **Option 40: Interactive Issue Triage & AI Analysis**

**WHAT IT DOES:**  
Uses AI to analyze and prioritize issues.

**FEATURES:**
- Auto-categorize issues (bug, feature, question)
- Suggest priority (critical, high, medium, low)
- Recommend assignee based on code ownership
- Generate response templates

**WHEN TO USE:**
- ✅ Many issues to triage
- ✅ New project with no process
- ✅ Community management

---

## 🛠️ TOOLS & UTILITIES

### **Option 14: Configuration Wizard**

**WHAT IT DOES:**  
Sets up or updates PyGitUp credentials.

**WHEN TO USE:**
- ✅ First-time setup
- ✅ Token expired/revoked
- ✅ Adding AI API key
- ✅ Switching GitHub accounts

**HOW TO USE:**
1. Select Option 14
2. Enter profile name
3. Enter GitHub username
4. Enter GitHub token
5. Enter AI API key (optional)
6. Set master password

**TIPS:**
- Multiple profiles supported
- Master password encrypts credentials
- Use different profiles for work/personal

---

### **Option 36: Token Health & Rotation**

**WHAT IT DOES:**  
Checks GitHub token status and helps rotate if needed.

**SHOWS:**
- Token type (Classic vs Fine-Grained)
- Creation date
- Expiration date
- Scopes/permissions
- Health recommendations

**WHEN TO USE:**
- ✅ Authentication errors
- ✅ Regular security check
- ✅ Token nearing expiration

**EXAMPLE:**
```
🔐 Token Health Report
┌────────────────────────────┐
│ ✅ VALID                   │
│ Type: Personal Classic     │
│ Created: 2023-11-13        │
│ Scopes: repo, workflow     │
└────────────────────────────┘

💡 Recommendations:
  • Token is 832 days old - consider rotation
  • Has full repo access - use fine-grained token

🔄 Rotation Recommended
```

---

### **Option 38: Generate SBOM**

**WHAT IT DOES:**  
Creates Software Bill of Materials (dependency list).

**FORMATS:**
- SPDX (industry standard)
- CycloneDX (security-focused)

**WHEN TO USE:**
- ✅ Security compliance
- ✅ Supply chain audit
- ✅ License compliance

**EXAMPLE:**
```
📄 Generating SBOM...
📊 Project: myproject v1.0.0
🔍 Detected languages: Python, Node.js
📦 Found 45 Python dependencies

✅ SBOM generated: sbom.spdx.json
```

**TIPS:**
- Works with Python projects
- Shows warning for multi-language projects
- Use CycloneDX for security audits

---

## 💻 COMMAND-LINE REFERENCE

### **Basic Usage**

```bash
# Interactive mode
python pygitup.py

# Direct mode
python pygitup.py --mode <mode> [options]
```

### **Common Commands**

```bash
# Upload project
python pygitup.py --mode project --path ./myproject --repo myproject

# Security scan
python pygitup.py --mode security-scan

# Generate SBOM
python pygitup.py --mode generate-sbom --format spdx

# Dry run (test without changes)
python pygitup.py --mode delete-repo --dry-run

# Get help
python pygitup.py --mode help
```

### **All Options**

| Option | Mode | Description |
|--------|------|-------------|
| 1 | `project` | Upload project directory |
| 2 | `file` | Upload single file |
| 3 | `batch` | Batch upload files |
| 4 | `template` | Create from template |
| 5 | `release` | Create GitHub release |
| ... | ... | ... |

---

## 🔧 TROUBLESHOOTING

### **Authentication Errors**

**Problem:** `401 Unauthorized`

**Solution:**
1. Check token is valid: Option 36
2. Regenerate token at: https://github.com/settings/tokens
3. Update credentials: Option 14

---

### **Git Conflicts**

**Problem:** Cherry-pick or merge conflicts

**Solution:**
```bash
# See conflicts
git status

# Edit files to fix
nano <file>

# Mark resolved
git add <file>

# Continue operation
git cherry-pick --continue
```

---

### **Rate Limiting**

**Problem:** `403 Rate limit exceeded`

**Solution:**
- Wait 1 hour for limit to reset
- Use authenticated requests (configured token)
- Upgrade to GitHub Pro for higher limits

---

### **SBOM Shows Wrong Project**

**Problem:** SBOM shows PyGitUp instead of your project

**Solution:**
- Fixed in v2.4.3+
- Update: `pip install --upgrade pygitup`

---

## 📞 SUPPORT

- **GitHub Issues:** https://github.com/frederickabrah/PyGitUp/issues
- **Documentation:** https://github.com/frederickabrah/PyGitUp/wiki
- **Security:** https://github.com/frederickabrah/PyGitUp/security

---

**Happy Coding! 🚀**
