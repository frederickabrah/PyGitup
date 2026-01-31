# PyGitUp 🚀

```
  _____       _____ _ _   _   _       
 |  __ \     / ____(_) | | | | |      
 | |__) |   | |  __ _| |_| | | |_ __  
 |  ___/    | | |_ | | __| | | | '_ \ 
 | |     _  | |__| | | |_| |_| | |_) |
 |_|    (_)  \_____|_|\__|\___/| .__/ 
                               | |    
                               |_|    
```

I got tired of typing the same 10 Git commands every time I started a new project or wanted to push a quick fix. So, I built **PyGitUp**. It's a CLI tool that actually makes sense—it handles the repetitive stuff, keeps your history clean, and makes sure you don't do anything stupid (like pushing your `.env` file).

---

## What does it actually do?

PyGitUp is basically a dashboard for your terminal. It’s got 26 modes, but here are the ones you'll actually use:

*   **Project Upload:** Forget `git init`, `git add`, `git commit`... this does it all in one go and creates the GitHub repo for you.
*   **Smart Push:** If you're like me and have 50 "fix typo" commits, this squashes them into one clean commit before pushing. Your history stays pretty.
*   **The Security Lock:** It actively scans your files before uploading. If it sees a `.env`, `node_modules`, or `venv`, it stops and asks you what you're doing. 
*   **Auto-Docs:** It literally reads your Python/JS/Java code and builds a documentation site for you. It uses AST parsing, so it's actually smart about it.
*   **Traffic Stats:** Want to see who's cloning your repo or where they're coming from? Option 25 gives you a full breakdown of views and referrers.
*   **Offline Mode:** If your internet is trash, queue your commits locally. The second you're back online, run the sync and they're gone.

---

## How to get it running

```bash
# Clone it
git clone https://github.com/frederickabrqh/PyGitUp.git
cd PyGitUp

# Grab the dependencies
pip install -r requirements.txt

# Run the interactive menu
python pygitup.py
```

---

## Let's be real (The Truth)

I'm not trying to sell you a miracle. Here’s what you should know:
1.  **It’s a Wrapper:** This tool needs Git installed on your system. It’s just running the commands for you so you don't have to remember the flags.
2.  **No Magic Docs:** If your code has zero docstrings, the "Auto-Docs" feature is going to generate a very empty folder. You still have to document your code.
3.  **Local Tokens:** Your GitHub token is stored in a local `.yaml` file. I don't see it, nobody else sees it. It stays on your machine.

---

## ❤️ Sponsor the Project: Fuel the Machine!

Let's be honest, `PyGitUp` is the digital equivalent of a Swiss Army knife for your GitHub workflow. It slices, it dices, it saves you from the existential dread of a `git push --force` gone wrong on a Friday afternoon. We've all been there.

This tool is, and always will be, **free**.

However, it is not fueled by good intentions alone. The `PyGitUp` development engine runs on a delicate, high-performance mixture of caffeine, sleep deprivation, and the sheer terror of disappointing its users. It's a miracle of engineering, really.

**If `PyGitUp` has saved you time, sanity, or even just a few frantic Google searches, consider becoming a sponsor.**

Think of it less as a donation and more as a strategic investment in your own future productivity. Your sponsorship directly translates into:

*   **More Features:** I have a roadmap longer than a `git log` on a decade-old project.
*   **Fewer Bugs:** Every bug squashed is a victory for developer sanity.
*   **The Ultimate Fuel:** Coffee. Lots and lots of coffee. You provide the caffeine, I provide the code that makes your life easier.

**[➡️ Become a GitHub Sponsor!](https://github.com/sponsors/frederickabrqh)**

**[☕ Buy Me a Coffee](https://www.buymeacoffee.com/frederickabrqh)**

---

**License:** MIT  
**Author:** Frederick Abraham