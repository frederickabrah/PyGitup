import subprocess
import requests
import json
from .ui import print_info, print_error, print_warning, print_success, console, Panel

def get_git_diff():
    """Extract the staged git diff."""
    try:
        result = subprocess.run(["git", "diff", "--cached"], capture_output=True, text=True, check=True)
        if not result.stdout.strip():
            return None
        return result.stdout
    except subprocess.CalledProcessError:
        return None

def call_gemini_api(api_key, prompt, timeout=30):
    """Centralized caller with 2.0 Flash -> 1.5 Flash fallback logic."""
    if not api_key:
        print_error("Gemini API Key missing. Run Option 14.")
        return None

    # Models to try in order
    models = ["gemini-2.0-flash", "gemini-1.5-flash"]
    
    last_error = ""
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        
        try:
            response = requests.post(url, json=payload, timeout=timeout)
            if response.status_code == 200:
                data = response.json()
                return data['candidates'][0]['content']['parts'][0]['text'].strip()
            else:
                last_error = f"Model {model} failed: {response.status_code} - {response.text}"
                continue # Try next model
        except Exception as e:
            last_error = f"Connection to {model} failed: {e}"
            continue

    print_error(f"AI Engine failure after all attempts. Last error: {last_error}")
    return None

def generate_ai_commit_message(api_key, diff_text):
    """Generates professional commit message using tiered fallback."""
    prompt = f"Analyze this git diff and write a Conventional Commit message with a summary and bullets:\n{diff_text[:10000]}"
    msg = call_gemini_api(api_key, prompt)
    if msg and msg.startswith("```"):
        msg = "\n".join(msg.splitlines()[1:-1])
    return msg

def generate_ai_release_notes(api_key, repo_name, commit_history):
    """Generates professional release notes using tiered fallback."""
    history_text = "\n".join([f"- {c['commit']['message'].splitlines()[0]}" for c in commit_history[:30]])
    prompt = f"Write a professional Release Announcement for '{repo_name}' based on these commits:\n{history_text}"
    return call_gemini_api(api_key, prompt)

def suggest_todo_fix(api_key, todo_text, context_code):
    """Suggests code fix for a TODO using tiered fallback."""
    prompt = f"Suggest a fix for this TODO: \"{todo_text}\" in this context:\n{context_code}"
    return call_gemini_api(api_key, prompt, timeout=20)

def generate_ai_readme(api_key, project_name, file_list):
    """Generates professional README using tiered fallback."""
    prompt = f"Write a professional README.md for '{project_name}' given this file structure:\n{file_list}"
    return call_gemini_api(api_key, prompt)

def ai_commit_workflow(github_username, github_token, config):
    """Orchestrates the AI commit process with auto-staging support."""
    api_key = config["github"].get("ai_api_key")
    
    diff = get_git_diff()
    if not diff:
        unstaged = subprocess.run(["git", "diff"], capture_output=True, text=True).stdout.strip()
        if unstaged:
            print_warning("No changes staged, but modified files detected.")
            confirm = input("Would you like me to stage all changes for you? (y/n): ").lower()
            if confirm == 'y':
                subprocess.run(["git", "add", "."], check=True)
                print_success("Staged all changes.")
                diff = get_git_diff()
            else:
                return False
        else:
            print_warning("No changes detected.")
            return False

    print_info("🤖 AI is analyzing your changes (Priority: 2.0 Flash)...")
    message = generate_ai_commit_message(api_key, diff)
    if not message: return False

    console.print(Panel(message, title="[bold cyan]Generated Commit Message[/bold cyan]", border_style="cyan"))
    print("\n1: Accept | 2: Edit | 3: Cancel")
    choice = input("\n👉 Choice: ")
    
    if choice == '1':
        subprocess.run(["git", "commit", "-m", message], check=True)
        print_success("Committed successfully!")
        return True
    elif choice == '2':
        manual_msg = input("Enter new message: ")
        if manual_msg:
            subprocess.run(["git", "commit", "-m", manual_msg], check=True)
            print_success("Committed successfully!")
            return True
    return False