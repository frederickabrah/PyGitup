import os
import re
import ast
import requests

from ..github.api import get_repo_contents

def extract_python_docs(content, filename):
    """Extract documentation from Python code using AST."""
    docs = {
        'module_docstring': '',
        'functions': [],
        'classes': [],
        'constants': []
    }
    
    try:
        tree = ast.parse(content)
        
        # Module docstring
        docs['module_docstring'] = ast.get_docstring(tree) or ''
        
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                func_doc = ast.get_docstring(node) or ''
                args = [arg.arg for arg in node.args.args]
                docs['functions'].append({
                    'name': node.name,
                    'params': ', '.join(args),
                    'docstring': func_doc
                })
            elif isinstance(node, ast.ClassDef):
                class_doc = ast.get_docstring(node) or ''
                bases = [base.id for base in node.bases if isinstance(base, ast.Name)]
                class_info = {
                    'name': node.name,
                    'parent': ', '.join(bases) if bases else 'object',
                    'docstring': class_doc,
                    'methods': []
                }
                
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        method_doc = ast.get_docstring(item) or ''
                        method_args = [arg.arg for arg in item.args.args]
                        class_info['methods'].append({
                            'name': item.name,
                            'params': ', '.join(method_args),
                            'docstring': method_doc
                        })
                
                docs['classes'].append(class_info)
                
    except SyntaxError:
        print(f"Warning: Could not parse {filename} (SyntaxError). Skipping.")
    except Exception as e:
        print(f"Warning: Error parsing {filename}: {e}")
    
    return docs

def extract_javascript_docs(content, filename):
    """Extract documentation from JavaScript code."""
    docs = {
        'module_description': '',
        'functions': [],
        'classes': []
    }
    
    # Extract JSDoc comments
    jsdoc_pattern = r'/\*\*\s*\n(\s*\*\s*[^\n]*\n)*\s*\*/\s*\n\s*(?:function\s+(\w+)|class\s+(\w+))'
    for match in re.finditer(jsdoc_pattern, content, re.DOTALL):
        jsdoc, func_name, class_name = match.groups()
        if func_name:
            # Extract the function
            docs['functions'].append({
                'name': func_name,
                'jsdoc': jsdoc.strip()
            })
        elif class_name:
            # Extract the class
            docs['classes'].append({
                'name': class_name,
                'jsdoc': jsdoc.strip()
            })
    
    return docs

def extract_go_docs(content, filename):
    """Extract documentation from Go code."""
    docs = {
        'functions': []
    }

    # Extract Go-style comments for functions
    func_pattern = r'//\s*(\w+)\s*.*\nfunc\s+(\w+)\s*\([^)]*\)'
    for match in re.finditer(func_pattern, content, re.DOTALL):
        go_doc, func_name = match.groups()
        docs['functions'].append({
            'name': func_name,
            'go_doc': go_doc.strip()
        })

    return docs

def extract_cpp_docs(content, filename):
    """Extract documentation from C++ code."""
    docs = {
        'functions': [],
        'classes': []
    }

    # Extract Doxygen-style comments for functions
    func_pattern = r'/\*!\s*\n(\s*\*\s*[^\n]*\n)*\s*\*/\s*\n\s*(?:[\w\s]+)\s+(\w+)\s*\([^)]*\)'
    for match in re.finditer(func_pattern, content, re.DOTALL):
        doxygen, func_name = match.groups()
        docs['functions'].append({
            'name': func_name,
            'doxygen': doxygen.strip()
        })

    # Extract Doxygen-style comments for classes
    class_pattern = r'/\*!\s*\n(\s*\*\s*[^\n]*\n)*\s*\*/\s*\n\s*class\s+(\w+)'
    for match in re.finditer(class_pattern, content, re.DOTALL):
        doxygen, class_name = match.groups()
        docs['classes'].append({
            'name': class_name,
            'doxygen': doxygen.strip()
        })

    return docs

def extract_java_docs(content, filename):
    """Extract documentation from Java code."""
    docs = {
        'classes': []
    }

    # Extract Javadoc comments
    javadoc_pattern = r'/\*\*\s*\n(\s*\*\s*[^\n]*\n)*\s*\*/\s*\n\s*(?:public|private|protected)?\s*(?:static\s+)?(?:final\s+)?class\s+(\w+)'
    for match in re.finditer(javadoc_pattern, content, re.DOTALL):
        javadoc, class_name = match.groups()
        docs['classes'].append({
            'name': class_name,
            'javadoc': javadoc.strip()
        })

    return docs

def generate_documentation(github_username, github_token, config, args=None):
    """Generate documentation from code comments."""
    if args and args.dry_run:
        print("*** Dry Run Mode: No changes will be made. ***")
        print("Would generate documentation from code comments.")
        return

    if args and args.repo:
        repo_name = args.repo
    else:
        repo_name = input("Enter repository name: ")
    
    output_dir = "docs"
    if args and args.output:
        output_dir = args.output
    else:
        output_dir_input = input(f"Enter output directory (default: {output_dir}): ")
        output_dir = output_dir_input if output_dir_input else output_dir
    
    print(f"Generating documentation for {repo_name}...")
    print(f"Output directory: {output_dir}")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Get repository contents
    try:
        response = get_repo_contents(github_username, repo_name, github_token)
        if response.status_code != 200:
            print(f"Error accessing repository: {response.status_code}")
            return
        
        contents = response.json()
        doc_content = f"# Documentation for {repo_name}\n\n"
        doc_content += '''<input type="text" id="search-bar" onkeyup="search()" placeholder="Search for names..">

'''
        doc_content += "## Table of Contents\n\n"
        doc_content += "- [Overview](#overview)\n"
        doc_content += "- [API Reference](#api-reference)\n"
        doc_content += "- [Usage Examples](#usage-examples)\n"
        doc_content += "- [Contributing](#contributing)\n\n"
        doc_content += "## Overview\n\n"
        doc_content += f"This documentation was automatically generated by PyGitUp for the {repo_name} repository.\n\n"
        
        # Process files
        api_reference = "## API Reference\n\n"
        modules_doc = ""
        examples_doc = "## Usage Examples\n\n"
        
        # Add sections for each language
        python_api = "### Python\n\n"
        javascript_api = "### JavaScript\n\n"
        java_api = "### Java\n\n"
        cpp_api = "### C++\n\n"
        go_api = "### Go\n\n"
        
        for item in contents:
            if item['type'] == 'file':
                # Process Python files
                if item['name'].endswith('.py'):
                    print(f"Processing {item['name']}...")
                    file_response = requests.get(item['download_url'])
                    if file_response.status_code == 200:
                        content = file_response.text
                        docs = extract_python_docs(content, item['name'])
                        
                        # Add to API reference
                        if docs['module_docstring'] or docs['functions'] or docs['classes']:
                            python_api += f"#### Module: {item['name']}\n\n"
                            if docs['module_docstring']:
                                python_api += f"{docs['module_docstring']}\n\n"
                            
                            # Functions
                            if docs['functions']:
                                python_api += "##### Functions\n\n"
                                for func in docs['functions']:
                                    python_api += f"**`{func['name']}({func['params']})`**\n\n"
                                    python_api += f"{func['docstring']}\n\n"
                            
                            # Classes
                            if docs['classes']:
                                python_api += "##### Classes\n\n"
                                for cls in docs['classes']:
                                    python_api += f"**`class {cls['name']}({cls['parent']})`**\n\n"
                                    python_api += f"{cls['docstring']}\n\n"
                                    
                                    # Methods
                                    if cls['methods']:
                                        python_api += "###### Methods\n\n"
                                        for method in cls['methods']:
                                             python_api += f"- **`{method['name']}({method['params']})`**: {method['docstring']}\n"
                                        python_api += "\n"
                
                # Process JavaScript files
                elif item['name'].endswith(('.js', '.jsx', '.ts', '.tsx')):
                    print(f"Processing {item['name']}...")
                    file_response = requests.get(item['download_url'])
                    if file_response.status_code == 200:
                        content = file_response.text
                        docs = extract_javascript_docs(content, item['name'])
                        
                        # Add to API reference
                        if docs['functions'] or docs['classes']:
                            javascript_api += f"#### Module: {item['name']}\n\n"
                            
                            # Functions
                            if docs['functions']:
                                javascript_api += "##### Functions\n\n"
                                for func in docs['functions']:
                                    javascript_api += f"**`{func['name']}`**\n\n"
                                    javascript_api += f"{func['jsdoc']}\n\n"
                            
                            # Classes
                            if docs['classes']:
                                javascript_api += "##### Classes\n\n"
                                for cls in docs['classes']:
                                    javascript_api += f"**`class {cls['name']}`**\n\n"
                                    javascript_api += f"{cls['jsdoc']}\n\n"
                
                # Process Java files
                elif item['name'].endswith('.java'):
                    print(f"Processing {item['name']}...")
                    file_response = requests.get(item['download_url'])
                    if file_response.status_code == 200:
                        content = file_response.text
                        docs = extract_java_docs(content, item['name'])
                        
                        # Add to API reference
                        if docs['classes']:
                            java_api += f"#### Module: {item['name']}\n\n"
                            
                            # Classes
                            if docs['classes']:
                                java_api += "##### Classes\n\n"
                                for cls in docs['classes']:
                                    java_api += f"**`class {cls['name']}`**\n\n"
                                    java_api += f"{cls['javadoc']}\n\n"
                
                # Process C++ files
                elif item['name'].endswith(('.cpp', '.hpp', '.h')):
                    print(f"Processing {item['name']}...")
                    file_response = requests.get(item['download_url'])
                    if file_response.status_code == 200:
                        content = file_response.text
                        docs = extract_cpp_docs(content, item['name'])
                        
                        # Add to API reference
                        if docs['functions'] or docs['classes']:
                            cpp_api += f"#### Module: {item['name']}\n\n"
                            
                            # Functions
                            if docs['functions']:
                                cpp_api += "##### Functions\n\n"
                                for func in docs['functions']:
                                    cpp_api += f"**`{func['name']}`**\n\n"
                                    cpp_api += f"{func['doxygen']}\n\n"
                            
                            # Classes
                            if docs['classes']:
                                cpp_api += "##### Classes\n\n"
                                for cls in docs['classes']:
                                    cpp_api += f"**`class {cls['name']}`**\n\n"
                                    cpp_api += f"{cls['doxygen']}\n\n"
                
                # Process Go files
                elif item['name'].endswith('.go'):
                    print(f"Processing {item['name']}...")
                    file_response = requests.get(item['download_url'])
                    if file_response.status_code == 200:
                        content = file_response.text
                        docs = extract_go_docs(content, item['name'])
                        
                        # Add to API reference
                        if docs['functions']:
                            go_api += f"#### Module: {item['name']}\n\n"
                            
                            # Functions
                            if docs['functions']:
                                go_api += "##### Functions\n\n"
                                for func in docs['functions']:
                                    go_api += f"**`{func['name']}`**\n\n"
                                    go_api += f"{func['go_doc']}\n\n"
        
        # Combine all documentation
        api_reference += python_api
        api_reference += javascript_api
        api_reference += java_api
        api_reference += cpp_api
        api_reference += go_api
        
        doc_content += api_reference
        doc_content += examples_doc
        doc_content += "## Contributing\n\n"
        doc_content += "Guidelines for contributing to this project.\n"
        
        # Add search script
        doc_content += r"\n<script>\nfunction search() {\n  var input, filter, ul, li, a, i, txtValue;\n  input = document.getElementById('search-bar');\n  filter = input.value.toUpperCase();\n  ul = document.getElementsByTagName('ul')[0];\n  li = ul.getElementsByTagName('li');\n  for (i = 0; i < li.length; i++) {\n    a = li[i].getElementsByTagName('a')[0];\n    txtValue = a.textContent || a.innerText;\n    if (txtValue.toUpperCase().indexOf(filter) > -1) {\n      li[i].style.display = \"\";\n    } else {\n      li[i].style.display = \"none\";\n    }\n  }\n}\n</script>\n"
        
        # Save main documentation
        doc_path = os.path.join(output_dir, "README.md")
        with open(doc_path, 'w') as f:
            f.write(doc_content)
        print(f"Main documentation generated successfully at {doc_path}")
        
        # Create API reference file
        api_path = os.path.join(output_dir, "API_REFERENCE.md")
        with open(api_path, 'w') as f:
            f.write(api_reference)
        print(f"API reference generated successfully at {api_path}")
        
        # Create simple index
        index_content = f"# {repo_name} Documentation\n\n"
        index_content += "- [Overview](README.md)\n"
        index_content += "- [API Reference](API_REFERENCE.md)\n"
        
        index_path = os.path.join(output_dir, "index.md")
        with open(index_path, 'w') as f:
            f.write(index_content)
        print(f"Documentation index generated successfully at {index_path}")
        
        print(f"\nDocumentation generation complete!")
        print(f"Documentation saved to: {output_dir}")
        
    except Exception as e:
        print(f"Error generating documentation: {e}")