# 🤖 PyGitUp Autonomous Agent Guide

The PyGitUp Technical Agent is a sovereign autonomous engineer integrated directly into your dashboard. It uses a **Chain-of-Thought** reasoning model to solve complex engineering tasks.

---

## 🛠️ Advanced Interaction

### 📎 Context Injection (@-mentions)
You can inject the content of any local file directly into the AI's "working memory" by using the `@` symbol followed by the filename.

**Example:**
> "Analyze the logic in @pygitup/utils/ai.py and suggest improvements."

*Note: PyGitUp automatically truncates massive files to ensure system responsiveness and prevent token overflow.*

### 🧠 The Cortex (History Compression)
Unlike standard AI chats that "forget" the beginning of a conversation, PyGitUp uses **History Compression**. When a session grows too long, the agent automatically distills the past into a structured technical `<state_snapshot>`. This ensures the agent never loses sight of your **Overall Goal**.

### 🛡️ Safety & Privacy
- **Secret Scrubbing:** Any GitHub tokens or AWS keys detected in the chat are automatically redacted before the session is saved to your disk.
- **Visual Diff Gatekeeper:** For privileged actions (like `write_file` or `patch_file`), the agent generates a visual diff. You must explicitly approve the changes before they are applied.
- **Safety Checkpoints:** Before any destructive file edit, PyGitUp creates a temporary Git Stash checkpoint. You can restore your code at any time using `git stash list`.

---

## ⚙️ Core Directives

The agent is governed by strict **Core Mandates**:
1. **Explain Before Acting:** The agent provides a concise explanation of its intent before calling any tool.
2. **Proactive Exploration:** It will automatically use `list_files` and `repo_audit` to understand your project structure before asking questions.
3. **No Chitchat:** The agent is designed for high-performance engineering; it avoids generic AI greetings and stays focused on technical execution.

---

## ⌨️ TUI Chat Hotkeys

| Key | Action |
|-----|--------|
| **Enter** | Send message / Approve tool |
| **Ctrl+L** | Clear chat history and memory |
| **Ctrl+Up** | Scroll chat log up |
| **Ctrl+Down** | Scroll chat log down |
| **Esc** | Return to Dashboard Home |

---

**PyGitUp Agent Engine** - *Technical Sovereignty in Engineering.*
