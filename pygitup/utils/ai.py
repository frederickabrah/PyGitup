import subprocess
import requests
import json
import time
import re
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

def list_available_ai_models(api_key):
    """Queries the API to list all models available for this key."""
    if not api_key:
        print_error("API Key missing.")
        return
    
    print_info("🔍 Querying Google for available models...")
    for version in ["v1beta", "v1"]:
        url = f"https://generativelanguage.googleapis.com/{version}/models?key={api_key}"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                models = response.json().get('models', [])
                print_success(f"Found {len(models)} models via {version}:")
                for m in models:
                    if 'generateContent' in m.get('supportedGenerationMethods', []):
                        name = m.get('name', '').replace('models/', '')
                        print(f"  - {name} ({m.get('displayName')})")
            else:
                print_warning(f"Could not list models via {version}: {response.status_code}")
        except Exception as e:
            print_error(f"Diagnostic failed for {version}: {e}")

def call_gemini_api(api_key, prompt, timeout=30):
    """Centralized caller with multi-model fallback, auto-retry, and verbose debugging."""
    if not api_key:
        print_error("Gemini API Key missing. Run Option 14.")
        return None

    # Optimized 'Flash-First' fallback chain based on diagnostic results
    models = [
        "gemini-2.5-flash",
        "gemini-2.0-flash", 
        "gemini-1.5-flash",
        "gemini-2.5-pro",
        "gemini-1.5-pro"
    ]
    # v1beta is prioritized due to high availability in diagnostics
    api_versions = ["v1beta", "v1"]
    
    last_error = ""
    for model in models:
        for version in api_versions:
            url = f"https://generativelanguage.googleapis.com/{version}/models/{model}:generateContent?key={api_key}"
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            
            print_info(f"🤖 AI Request: {model} ({version})...")
            
            try:
                response = requests.post(url, json=payload, timeout=timeout)
                
                if response.status_code == 200:
                    data = response.json()
                    try:
                        return data['candidates'][0]['content']['parts'][0]['text'].strip()
                    except (KeyError, IndexError):
                        last_error = f"[{model}] Malformed response body."
                        continue

                elif response.status_code == 429:
                    print_warning(f"   ⏳ Rate limit hit (429). Cooling down for 3s...")
                    time.sleep(3)
                    continue 
                
                else:
                    last_error = f"[{model}/{version}] HTTP {response.status_code}: {response.text}"
                    print_warning(f"   ⚠️  Failed ({response.status_code}).")
                    continue 

            except Exception as e:
                last_error = f"[{model}/{version}] Connection error: {e}"
                print_warning(f"   ⚠️  Connection failed.")
                continue

    print_error(f"❌ AI Engine exhausted all fallback combinations.")
    console.print(Panel(last_error, title="Final Raw Error", border_style="red"))
    return None

def generate_ai_commit_message(api_key, diff_text):
    """Generates professional commit message using tiered fallback."""
    prompt = f"Analyze this git diff and write a Conventional Commit message with a summary and bullets:\n{diff_text[:10000]}"
    msg = call_gemini_api(api_key, prompt)
    if msg and msg.startswith("```"):
        msg = "\n".join(msg.splitlines()[1:-1])
    return msg

def generate_ai_release_notes(api_key, repo_name, commit_history):
    """Uses Gemini to summarize recent history into a professional release announcement."""
    if not api_key: return None

    # Format history for the AI
    history_text = "\n".join([f"- {c['commit']['message'].splitlines()[0]}" for c in commit_history[:30]])
    
    prompt = f"""
    You are a Lead Software Architect. 
    Write a technical release announcement for the project '{repo_name}'.
    
    RECENT CHANGES:
    {history_text}
    
    CRITICAL CONSTRAINTS:
    1. DO NOT use placeholders like "[City, State]", "[Date]", or "[Name]".
    2. DO NOT use bracketed text or generic fill-in-the-blanks.
    3. Use real data from the provided changes.
    4. Sections: '🚀 Highlights', '🛠️ Technical Changes', '🛡️ Security & Stability'.
    5. Professional, technical, and concise tone.
    """
    return call_gemini_api(api_key, prompt)

def suggest_todo_fix(api_key, todo_text, context_code):
    """Suggests code fix for a TODO using tiered fallback."""
    prompt = f"Suggest a fix for this TODO: \"{todo_text}\" in this context:\n{context_code}"
    return call_gemini_api(api_key, prompt, timeout=20)

def generate_ai_readme(api_key, project_name, file_list, code_context=""):
    """Uses Gemini to generate a professional README based on structure and code content."""
    files = file_list[:3000] if len(file_list) > 3000 else file_list
    context = code_context[:7000] if len(code_context) > 7000 else code_context

    prompt = f"""
    Write a professional README.md for the project '{project_name}'.
    STRUCTURE: {files}
    CODE CONTEXT: {context}
    
    INSTRUCTIONS:
    1. Determine what the project actually DOES.
    2. Write a professional introduction and feature list.
    3. Include REAL installation steps based on the code.
    4. Format in beautiful Markdown. No placeholders.
    """
    return call_gemini_api(api_key, prompt)

def generate_ai_workflow(api_key, project_name, file_list, code_context=""):
    """Uses Gemini to architect a custom CI/CD pipeline."""
    prompt = f"Architect a professional GitHub Actions YAML for '{project_name}'. Structure: {file_list}. Context: {code_context[:5000]}"
    msg = call_gemini_api(api_key, prompt)
    if msg and msg.startswith("```"):
        msg = "\n".join(msg.splitlines()[1:-1])
    return msg

def analyze_failed_log(api_key, log_text):
    # ... (existing code)
    return call_gemini_api(api_key, prompt)

def code_mentor_chat(api_key, query, code_context):
    """Uses Gemini as a Code Mentor to answer questions about the local codebase."""
    if not api_key: return "API Key missing."
    
    prompt = f"""
    You are 'PyGitUp Mentor', an elite Software Architect.
    
    CONTEXT OF THE CURRENT PROJECT:
    {code_context[:8000]} # Limit context for speed
    
    USER QUERY:
    {query}
    
    INSTRUCTIONS:
    1. Answer based on the provided project context.
    2. Be technical, accurate, and direct.
    3. If providing code, use clean, production-ready syntax.
    4. Help the user optimize, debug, or understand their architecture.
    """
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

    print_info("🤖 AI is analyzing your changes...")
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