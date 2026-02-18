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
    except Exception as e:
        print_warning(f"Technical extraction failed for {filename}: {e}")
    return docs

def extract_javascript_docs(content, filename):
    docs = {'functions': [], 'classes': []}
    jsdoc_pattern = r'/\*\*\s*\n(\s*\*\s*[^\n]*\n)*\s*\*/\s*\n\s*(?:function\s+(\w+)|class\s+(\w+))'
    for match in re.finditer(jsdoc_pattern, content, re.DOTALL):
        jsdoc, func_name, class_name = match.groups()
        if func_name: docs['functions'].append({'name': func_name, 'jsdoc': jsdoc.strip()})
        elif class_name: docs['classes'].append({'name': class_name, 'jsdoc': jsdoc.strip()})
    return docs

def extract_go_docs(content, filename):
    docs = {'functions': []}
    func_pattern = r'//\s*(\w+)\s*.*\nfunc\s+(\w+)\s*\([^)]*\)'
    for match in re.finditer(func_pattern, content, re.DOTALL):
        go_doc, func_name = match.groups()
        docs['functions'].append({'name': func_name, 'go_doc': go_doc.strip()})
    return docs

def extract_cpp_docs(content, filename):
    docs = {'functions': [], 'classes': []}
    func_pattern = r'/\*!\s*\n(\s*\*\s*[^\n]*\n)*\s*\*/\s*\n\s*(?:[\w\s]+)\s+(\w+)\s*\([^)]*\)'
    for match in re.finditer(func_pattern, content, re.DOTALL):
        doxygen, func_name = match.groups()
        docs['functions'].append({'name': func_name, 'doxygen': doxygen.strip()})
    return docs

def extract_java_docs(content, filename):
    docs = {'classes': []}
    javadoc_pattern = r'/\*\*\s*\n(\s*\*\s*[^\n]*\n)*\s*\*/\s*\n\s*(?:public|private|protected)?\s*(?:static\s+)?(?:final\s+)?class\s+(\w+)'
    for match in re.finditer(javadoc_pattern, content, re.DOTALL):
        javadoc, class_name = match.groups()
        docs['classes'].append({'name': class_name, 'javadoc': javadoc.strip()})
    return docs

def core_generate_docs(config, repo_name, output_dir, github_username, github_token, use_ai=False):
    """Core logic for documentation generation, decoupled from CLI input."""
    generated_files = []
    os.makedirs(output_dir, exist_ok=True)

    # Standard Generation
    try:
        response = get_repo_contents(github_username, repo_name, github_token)
        if response.status_code != 200: return []
        
        contents = response.json()
        doc_content = f"# Documentation for {repo_name}\n\n## API Reference\n\n"
        
        for item in contents:
            if item['type'] != 'file': continue
            ext = os.path.splitext(item['name'])[1]
            file_response = requests.get(item['download_url'])
            if file_response.status_code != 200: continue
            
            content = file_response.text
            if ext == '.py':
                docs = extract_python_docs(content, item['name'])
                if docs['functions'] or docs['classes']:
                    doc_content += f"### Python Module: {item['name']}\n\n"
                    for func in docs['functions']: doc_content += f"**`{func['name']}({func['params']})`**\n{func['docstring']}\n\n"
                    for cls in docs['classes']: doc_content += f"**`class {cls['name']}`**\n{cls['docstring']}\n\n"
            elif ext in ['.js', '.ts', '.tsx']:
                docs = extract_javascript_docs(content, item['name'])
                if docs['functions'] or docs['classes']:
                    doc_content += f"### JS/TS Module: {item['name']}\n\n"
                    for func in docs['functions']: doc_content += f"**`{func['name']}`**\n{func['jsdoc']}\n\n"
            elif ext == '.go':
                docs = extract_go_docs(content, item['name'])
                if docs['functions']:
                    doc_content += f"### Go Module: {item['name']}\n\n"
                    for func in docs['functions']: doc_content += f"**`{func['name']}`**\n{func['go_doc']}\n\n"

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
