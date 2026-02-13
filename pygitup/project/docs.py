import os
import re
import ast
import requests

from ..github.api import get_repo_contents
from ..utils.ui import print_success, print_error, print_info, print_header, print_warning
from ..utils.ai import generate_ai_readme

def extract_python_docs(content, filename):
    """Extract documentation from Python code using AST."""
    docs = {'module_docstring': '', 'functions': [], 'classes': [], 'constants': []}
    try:
        tree = ast.parse(content)
        docs['module_docstring'] = ast.get_docstring(tree) or ''
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                func_doc = ast.get_docstring(node) or ''
                args = [arg.arg for arg in node.args.args]
                docs['functions'].append({'name': node.name, 'params': ', '.join(args), 'docstring': func_doc})
            elif isinstance(node, ast.ClassDef):
                class_doc = ast.get_docstring(node) or ''
                bases = [base.id for base in node.bases if isinstance(base, ast.Name)]
                class_info = {'name': node.name, 'parent': ', '.join(bases) if bases else 'object', 'docstring': class_doc, 'methods': []}
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        method_doc = ast.get_docstring(item) or ''
                        method_args = [arg.arg for arg in item.args.args]
                        class_info['methods'].append({'name': item.name, 'params': ', '.join(method_args), 'docstring': method_doc})
                docs['classes'].append(class_info)
    except Exception: pass
    return docs

def extract_javascript_docs(content, filename):
    docs = {'functions': [], 'classes': []}
    jsdoc_pattern = r'/\*\*\s*\n(\s*\*\s*[^\n]*\n)*\s*\*/\s*\n\s*(?:function\s+(\w+)|class\s+(\w+))'
    for match in re.finditer(jsdoc_pattern, content, re.DOTALL):
        jsdoc, func_name, class_name = match.groups()
        if func_name: docs['functions'].append({'name': func_name, 'jsdoc': jsdoc.strip()})
        elif class_name: docs['classes'].append({'name': class_name, 'jsdoc': jsdoc.strip()})
    return docs

# (Keep extract_go_docs, extract_cpp_docs, extract_java_docs as helper functions if needed, simplified here for brevity but assuming they exist)

def core_generate_docs(config, repo_name, output_dir, github_username, github_token, use_ai=False):
    """Core logic for documentation generation, decoupled from CLI input."""
    generated_files = []
    os.makedirs(output_dir, exist_ok=True)

    # AI README Option
    ai_key = config["github"].get("ai_api_key")
    if use_ai and ai_key:
        repo_resp = get_repo_contents(github_username, repo_name, github_token)
        if repo_resp.status_code == 200:
            contents_list = repo_resp.json()
            file_paths = [item['path'] for item in contents_list]
            code_context = ""
            priority_files = ["main.py", "setup.py", "requirements.txt", "README.md", "pyproject.toml", "index.js", "package.json"]
            for item in contents_list:
                if item['name'] in priority_files and item['type'] == 'file':
                    f_resp = requests.get(item['download_url'])
                    if f_resp.status_code == 200:
                        snippet = "\n".join(f_resp.text.splitlines()[:150])
                        code_context += f"\n--- FILE: {item['name']} ---\n{snippet}\n"
            ai_readme = generate_ai_readme(ai_key, repo_name, "\n".join(file_paths), code_context)
            if ai_readme:
                path = os.path.join(output_dir, "README.md")
                with open(path, 'w') as f: f.write(ai_readme)
                generated_files.append(path)
                return generated_files

    # Standard Generation
    try:
        response = get_repo_contents(github_username, repo_name, github_token)
        if response.status_code != 200: return []
        
        contents = response.json()
        doc_content = f"# Documentation for {repo_name}\n\n## API Reference\n\n"
        
        for item in contents:
            if item['type'] == 'file' and item['name'].endswith('.py'):
                file_response = requests.get(item['download_url'])
                if file_response.status_code == 200:
                    docs = extract_python_docs(file_response.text, item['name'])
                    if docs['functions'] or docs['classes']:
                        doc_content += f"### Module: {item['name']}\n\n"
                        for func in docs['functions']: doc_content += f"**`{func['name']}({func['params']})`**\n{func['docstring']}\n\n"
                        for cls in docs['classes']: doc_content += f"**`class {cls['name']}`**\n{cls['docstring']}\n\n"

        doc_path = os.path.join(output_dir, "API_REFERENCE.md")
        with open(doc_path, 'w') as f: f.write(doc_content)
        generated_files.append(doc_path)
        return generated_files
    except Exception: return []

def generate_documentation(github_username, github_token, config, args=None):
    """CLI Wrapper for documentation generation."""
    if args and args.dry_run: return
    print_header("Documentation Generator")
    repo_name = args.repo if args and args.repo else input("Enter repository name: ")
    output_dir = args.output if args and args.output else input("Enter output directory (default: docs): ") or "docs"
    
    print_info(f"Generating documentation for {repo_name}...")
    files = core_generate_docs(config, repo_name, output_dir, github_username, github_token)
    
    if files: print_success(f"Generated: {', '.join(files)}")
    else: print_error("Failed to generate documentation.")