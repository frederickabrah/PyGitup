import subprocess
import requests
import json
import time
import re
import os
from .ui import print_info, print_error, print_warning, print_success, console, Panel
from .agent_tools import AGENT_TOOLS_SPEC, execute_agent_tool

def validate_ai_key(api_key: str, feature_name: str = "This feature") -> bool:
    """Validate AI API key and show helpful error if missing."""
    if not api_key or len(api_key.strip()) < 10:
        error_message = f"""
╭─────────────────────────────────────────────────────────────╮
│  🤖 AI API Key Required                                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  The Gemini API key is not configured.                      │
│                                                             │
│  To use {feature_name}, you need to:                      │
│                                                             │
│  1. Get an API key from:                                    │
│     🔗 https://makersuite.google.com/app/apikey            │
│                                                             │
│  2. Configure it using one of these methods:                │
│                                                             │
│     a) Environment Variable:                                │
│        export GEMINI_API_KEY=your_api_key                   │
│                                                             │
│     b) PyGitUp Configuration:                               │
│        Run: pygitup → Option 14 (Configure)                 │
│        Add your Gemini API key                              │
│                                                             │
│  After configuration, run this command again.               │
│                                                             │
╰─────────────────────────────────────────────────────────────╯
"""
        print_error(error_message)
        return False
    return True

def get_git_diff():
    """Extract the staged git diff."""
    try:
        result = subprocess.run(["git", "diff", "--cached"], capture_output=True, text=True, check=True)
        return result.stdout if result.stdout.strip() else None
    except: return None

def list_available_ai_models(api_key):
    """Queries the API to list all models available for this key."""
    if not validate_ai_key(api_key, "AI Model Listing"):
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
    """Centralized simple caller with exhaustive model rotation."""
    if not validate_ai_key(api_key, "AI-powered features"):
        return None
        
    models = [
        ("gemini-3.1-pro", "v1beta"),
        ("gemini-3-flash", "v1beta"),
        ("gemini-2.5-pro", "v1beta"),
        ("gemini-2.5-flash", "v1beta"),
        ("gemini-2.0-flash", "v1beta"), 
        ("gemini-1.5-pro", "v1beta"),
        ("gemini-1.5-flash", "v1beta"),
        ("gemini-1.5-pro", "v1"),
        ("gemini-1.5-flash", "v1")
    ]
    
    for model, version in models:
        url = f"https://generativelanguage.googleapis.com/{version}/models/{model}:generateContent"
        headers = {
            "x-goog-api-key": api_key,
            "Content-Type": "application/json"
        }
        payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
        
        for attempt in range(2):
            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get('candidates'):
                        return data['candidates'][0]['content']['parts'][0]['text'].strip()
                elif resp.status_code == 429: # Rate limit
                    time.sleep(2 ** attempt)
                    continue
                else:
                    break # Try next model/version
            except (requests.exceptions.RequestException, KeyError, IndexError):
                time.sleep(1)
                continue
    return None

def generate_ai_commit_message(api_key, diff_text):
    prompt = f"Write a Conventional Commit for this diff:\n{diff_text[:5000]}"
    return call_gemini_api(api_key, prompt)

def generate_ai_release_notes(api_key, repo_name, commit_history):
    """Uses Gemini to summarize recent history into a professional release announcement."""
    if not api_key: return None
    history_text = "\n".join([f"- {c['commit']['message'].splitlines()[0]}" for c in commit_history[:30]])
    prompt = f"""Write a technical release announcement for '{repo_name}'.\nRECENT CHANGES:\n{history_text}\nNo placeholders."""
    return call_gemini_api(api_key, prompt)

def generate_ai_readme(api_key, project_name, file_list, code_context=""):
    """Uses Gemini to generate a professional README based on structure and code content."""
    prompt = f"Write a professional README.md for '{project_name}'. Structure: {file_list}. Context: {code_context[:5000]}"
    return call_gemini_api(api_key, prompt)

def generate_ai_workflow(api_key, project_name, file_list, code_context=""):
    """Uses Gemini to architect a custom CI/CD pipeline."""
    prompt = f"Architect a professional GitHub Actions YAML for '{project_name}'. Structure: {file_list}. Context: {code_context[:5000]}"
    msg = call_gemini_api(api_key, prompt)
    if msg and msg.startswith("```"):
        msg = "\n".join(msg.splitlines()[1:-1])
    return msg

def suggest_todo_fix(api_key, todo_text, context_code):
    """Suggests code fix for a TODO using tiered fallback."""
    prompt = f"Suggest a fix for this TODO: \"{todo_text}\" in this context:\n{context_code}"
    return call_gemini_api(api_key, prompt, timeout=20)

def analyze_failed_log(api_key, log_text):
    prompt = f"Identify the bug in this log and provide a fix:\n{log_text[:5000]}"
    return call_gemini_api(api_key, prompt)

def compress_history(api_key, history):
    """Distills long history into a technical <state_snapshot> to preserve context."""
    if len(history) < 10: return history
    
    # Extract the last 2 turns to keep them 'fresh'
    recent_turns = history[-2:]
    history_to_compress = history[:-2]
    
    history_text = ""
    for msg in history_to_compress:
        role = "User" if msg['role'] == 'user' else "Agent"
        text = msg.get('text', '[Tool Action]')
        history_text += f"{role}: {text}\n"

    prompt = f"""
You are a Technical System Distiller. Summarize this chat history into a dense XML <state_snapshot>.
Include: 1. OVERALL_GOAL, 2. TECHNICAL_DISCOVERIES, 3. COMPLETED_TASKS, 4. PENDING_TASKS.
Be extremely technical and concise. No chitchat.

HISTORY:
{history_text}
"""
    summary = call_gemini_api(api_key, prompt)
    if summary:
        # Return a curated history starting with the snapshot
        return [{"role": "user", "text": f"[SYSTEM RECOVERY SNAPSHOT]:\n{summary}"}] + recent_turns
    return history

def code_mentor_chat(api_key, query, code_context, history=None):
    """Autonomous AI Agent with Sovereign mandates and history curation."""
    if not api_key: return {"text": "API Key missing.", "tool_calls": []}
    history = history or []
    
    sys_instr = (
        "You are an interactive CLI agent specializing in software engineering tasks. "
        "Your primary goal is to help users safely and efficiently, adhering strictly to the following instructions.\n\n"
        "# Core Mandates\n"
        "- **Conventions:** Rigorously adhere to existing project conventions. Analyze code, tests, and config first.\n"
        "- **Libraries:** NEVER assume a library is available. Verify usage in 'package.json', 'requirements.txt', etc.\n"
        "- **Comments:** Add sparingly. Focus on *why*, not *what*. NEVER talk to the user in comments.\n"
        "- **Proactiveness:** Fulfill requests thoroughly. Adding features/fixing bugs includes adding tests.\n"
        "- **Explain Before Acting:** Provide a concise, one-sentence explanation of your intent before tool calls.\n"
        "- **No Chitchat:** Avoid conversational filler. Get straight to the action.\n\n"
        "# Primary Workflow\n"
        "1. **Understand:** Use 'list_files' and 'read_file' extensively to understand context and conventions.\n"
        "2. **Plan:** Build a coherent plan. If a change is implied but not stated, ASK for confirmation.\n"
        "3. **Implement:** Use 'patch_file' for precision or 'write_file' for new modules.\n"
        "4. **Verify:** Use 'run_shell' to execute tests and check standards (linting, types).\n\n"
        "# Operational Guidelines\n"
        "- **Concise & Direct:** Aim for fewer than 3 lines of text output per response.\n"
        "- **Tools vs. Text:** Use tools for actions, text output *only* for communication.\n"
        "- **Security:** Never introduce code that exposes secrets or API keys.\n\n"
        f"Current Project Context:\n{code_context[:1500]}"
    )
    
    # 1. Build and clean history turns with sequence protection
    contents = []
    
    # COMPRESSION: If history is too long, distill it
    if len(history) > 20:
        history = compress_history(api_key, history)
    
    # We take the last 15 turns and verify structure.
    raw_history = history[-15:]
    
    for msg in raw_history:
        # CURATION: Skip empty or malformed turns
        if not msg.get('text') and not msg.get('tool_calls') and not msg.get('tool_results'):
            continue
            
        role = "model" if msg['role'] == 'model' else "user"
        parts = []
        
        if msg.get('text'):
            parts.append({"text": msg['text']})
            
        if msg.get('tool_calls'):
            role = "model"
            for tc in msg['tool_calls']:
                parts.append({"function_call": {"name": tc['name'], "args": tc['args']}})
                
        if msg.get('tool_results'):
            role = "user"
            for tr in msg['tool_results']:
                # The 'response' field must be an object
                parts.append({"function_response": {"name": tr['name'], "response": tr['content']}})
        
        if not parts: continue
        
        # Merge consecutive roles to satisfy API constraints
        if contents and contents[-1]['role'] == role:
            contents[-1]['parts'].extend(parts)
        else:
            contents.append({"role": role, "parts": parts})

    # 2. Add current query (must be a user turn)
    if query:
        if contents and contents[-1]['role'] == "user":
            contents[-1]['parts'].append({"text": query})
        else:
            contents.append({"role": "user", "parts": [{"text": query}]})

    # 3. Validation: If the last turn is model but has tool_calls, API will fail if no user response follows.
    # Our logic ensures 'query' or 'tool_results' always follows a model turn in the final payload.

    # 4. Call API with rotation and fallback support
    models = [
        ("gemini-3.1-pro", "v1beta"),
        ("gemini-3-flash", "v1beta"),
        ("gemini-2.5-pro", "v1beta"),
        ("gemini-2.5-flash", "v1beta"),
        ("gemini-2.0-flash", "v1beta"),
        ("gemini-1.5-pro", "v1beta"),
        ("gemini-1.5-flash", "v1beta"),
        ("gemini-1.5-pro", "v1"),
        ("gemini-1.5-flash", "v1")
    ]
    last_err = "No successful model connection."
    
    for model, version in models:
        url = f"https://generativelanguage.googleapis.com/{version}/models/{model}:generateContent"
        headers = {
            "x-goog-api-key": api_key,
            "Content-Type": "application/json"
        }
        try:
            payload = {
                "contents": contents,
                "system_instruction": {"parts": [{"text": sys_instr}]},
                "tools": [{"function_declarations": AGENT_TOOLS_SPEC}]
            }
            # v1 doesn't support system_instruction in standard generateContent
            if version == "v1":
                payload.pop("system_instruction", None)
                # Some v1 models might not support tools either, or might require different schema
                # We'll try with tools first, and fallback if it returns 400
                
            resp = requests.post(url, json=payload, headers=headers, timeout=15)
            
            if resp.status_code == 400 and version == "v1":
                # Fallback: Try without tools on v1 if it failed
                payload.pop("tools", None)
                resp = requests.post(url, json=payload, headers=headers, timeout=15)

            if resp.status_code == 200:
                data = resp.json()
                if not data.get('candidates'):
                    last_err = f"[{model}] No candidates returned."
                    continue
                cand = data['candidates'][0].get('content', {})
                if not cand.get('parts'):
                    last_err = f"[{model}] Empty response body."
                    continue
                    
                out_text = ""; calls = []
                for p in cand['parts']:
                    if 'text' in p: out_text += p['text']
                    if 'function_call' in p:
                        calls.append({"name": p['function_call']['name'], "args": p['function_call']['args']})
                return {"text": out_text.strip(), "tool_calls": calls}
            
            elif resp.status_code == 403:
                last_err = "API Key lacks required permissions (403)."
                continue
            elif resp.status_code == 429:
                time.sleep(2)
                continue
            elif resp.status_code == 404:
                last_err = f"Model {model} ({version}) not found."
                continue 
            else:
                last_err = f"[{model} {version}] HTTP {resp.status_code}"
        except Exception as e:
            last_err = f"Connection error: {str(e)}"
            
    # Final Fallback Error Reporting
    return {"text": f"AI Engine Error: {last_err}", "tool_calls": []}

def ai_diagnostics_workflow(config, command, tui_app=None):
    print_info(f"Running: {command}")
    from .agent_tools import run_shell_tool
    res = run_shell_tool(command)
    if res.get('exit_code') == 0: return True
    api_key = config["github"].get("ai_api_key")
    return analyze_failed_log(api_key, str(res))

def ai_commit_workflow(github_username, github_token, config):
    api_key = config["github"].get("ai_api_key")
    diff = get_git_diff()
    if not diff: return False
    msg = generate_ai_commit_message(api_key, diff)
    if msg:
        print(f"Proposed: {msg}")
        if input("Commit? (y/n) ").lower() == 'y':
            subprocess.run(["git", "commit", "-m", msg])
            return True
    return False
