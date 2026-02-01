
import subprocess
import requests
import json
from .ui import print_info, print_error, print_warning, print_success, console, Panel

def get_git_diff():
    """Extract the staged git diff."""
    try:
        # Check if there are staged changes
        result = subprocess.run(["git", "diff", "--cached"], capture_output=True, text=True, check=True)
        if not result.stdout.strip():
            return None
        return result.stdout
    except subprocess.CalledProcessError:
        return None

def generate_ai_commit_message(api_key, diff_text):
    """Uses Gemini API to generate a professional commit message from a diff."""
    if not api_key:
        print_error("Gemini API Key missing. Please run the configuration wizard (Option 14).")
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    prompt = f"""
    You are an expert software engineer and git specialist. 
    Analyze the following git diff and generate a professional commit message. 
    
    CRITICAL RULES:
    1. Follow the Conventional Commits standard (feat:, fix:, refactor:, chore:, docs:, style:, test:).
    2. Start with a high-level summary line (max 50 chars).
    3. Add a blank line, then a bulleted list of specific, meaningful changes.
    4. Focus on the WHY and the IMPACT, not just the technical details.
    5. Do not include any other text, only the commit message itself. 
    
    DIFF DATA:
    {diff_text[:10000]} # Truncate to 10k chars for safety
    """

    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            try:
                msg = data['candidates'][0]['content']['parts'][0]['text'].strip()
                # Clean up markdown if the AI includes it
                if msg.startswith("```"):
                    msg = "\n".join(msg.splitlines()[1:-1])
                return msg
            except (KeyError, IndexError):
                print_error("Could not parse AI response.")
                return None
        else:
            print_error(f"Gemini API Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return None

def ai_commit_workflow(github_username, github_token, config):
    """Orchestrates the AI commit process."""
    api_key = config["github"].get("ai_api_key")
    
    diff = get_git_diff()
    if not diff:
        print_warning("No staged changes found. Use 'git add' to stage files before AI commit.")
        return False

    print_info("🤖 AI is analyzing your changes...")
    
    message = generate_ai_commit_message(api_key, diff)
    if not message:
        return False

    console.print(Panel(message, title="[bold cyan]Generated Commit Message[/bold cyan]", border_style="cyan"))
    
    print("\n[bold]Options:[/bold]")
    print("1: [green]Accept & Commit[/green]")
    print("2: [yellow]Edit manually[/yellow]")
    print("3: [red]Cancel[/red]")
    
    choice = input("\n👉 Choose an action (1-3): ")
    
    if choice == '1':
        try:
            subprocess.run(["git", "commit", "-m", message], check=True)
            print_success("Changes committed successfully!")
            return True
        except Exception as e:
            print_error(f"Commit failed: {e}")
            return False
    elif choice == '2':
        # Simple manual edit fallback
        manual_msg = input("Enter new commit message: ")
        if manual_msg:
            subprocess.run(["git", "commit", "-m", manual_msg], check=True)
            print_success("Changes committed successfully!")
            return True
    
    print_info("Commit cancelled.")
    return False
