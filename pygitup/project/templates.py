from ..github.api import create_repo, update_file
from ..core.config import get_github_username

# Template definitions
DEFAULT_TEMPLATES = {
    "web-app": {
        "files": {
            "index.html": """<!DOCTYPE html>
<html>
<head>
    <title>{{PROJECT_NAME}}</title>
</head>
<body>
    <h1>Welcome to {{PROJECT_NAME}}</h1>
    <p>Created with PyGitUp</p>
</body>
</html>""",
            "style.css": """body {
    font-family: Arial, sans-serif;
    margin: 40px;
}""",
            "README.md": """# {{PROJECT_NAME}}

{{DESCRIPTION}}

## Setup

1. Clone this repository
2. Open `index.html` in your browser

Generated with PyGitUp"""
        }
    },
    "python-package": {
        "files": {
            "__init__.py": "",
            "main.py": """#!/usr/bin/env python3

'''{{PROJECT_NAME}} - {{DESCRIPTION}}'''

def main():
    print("Hello from {{PROJECT_NAME}}!")

if __name__ == "__main__":
    main()""",
            "setup.py": """from setuptools import setup, find_packages

setup(
    name=\"{{PROJECT_NAME}}\",
    version=\"0.1.0\",
    packages=find_packages(),
    install_requires=[],
    entry_points={
        'console_scripts': [
            '{{PROJECT_NAME}}=main:main'
        ]
    }
)""",
            "README.md": """# {{PROJECT_NAME}}

{{DESCRIPTION}}

## Installation

```bash
pip install . 
```

## Usage

```bash
{{PROJECT_NAME}}
```"""
        }
    }
}

def get_template_input(config, args=None):
    """Get template input from user or arguments."""
    if args and args.template:
        template_name = args.template
    else:
        print("\n--- Available Templates ---")
        for template in DEFAULT_TEMPLATES.keys():
            print(f"- {template}")
        template_name = input("Enter template name: ")
    
    if template_name not in DEFAULT_TEMPLATES:
        print(f"Template '{template_name}' not found.")
        return None, None, None, None
    
    if args and args.repo:
        repo_name = args.repo
    else:
        repo_name = input("Enter repository name: ")
    
    # Get variables
    variables = {}
    if args and args.variables:
        # Parse variables from command line
        var_pairs = args.variables.split(",")
        for pair in var_pairs:
            if "=" in pair:
                key, value = pair.split("=", 1)
                variables[key.strip()] = value.strip()
    
    # Default variables
    if "PROJECT_NAME" not in variables:
        variables["PROJECT_NAME"] = repo_name
    if "DESCRIPTION" not in variables:
        variables["DESCRIPTION"] = "Project created with PyGitUp template"
    if "AUTHOR" not in variables:
        variables["AUTHOR"] = get_github_username(config)
    
    return template_name, repo_name, variables, DEFAULT_TEMPLATES[template_name]

def create_project_from_template(github_username, github_token, config, args=None):
    """Create a new project from a template."""
    if args and args.dry_run:
        print("*** Dry Run Mode: No changes will be made. ***")
        template_name, repo_name, variables, template = get_template_input(config, args)
        print(f"Would create project '{repo_name}' from template '{template_name}'.")
        return

    template_name, repo_name, variables, template = get_template_input(config, args)
    
    if not template_name:
        return
    
    print(f"Creating project '{repo_name}' from template '{template_name}'...")
    
    # Create repository first
    response = create_repo(
        github_username, repo_name, github_token,
        description=variables.get("DESCRIPTION", ""),
        private=args.private if args and hasattr(args, 'private') else False
    )
    
    if response.status_code not in [201, 200]:
        print(f"Error creating repository: {response.status_code} - {response.text}")
        return
    
    print(f"Repository '{repo_name}' created successfully.")
    
    # Create files from template
    success_count = 0
    for file_name, file_content in template["files"].items():
        # Replace variables in file content
        for var_name, var_value in variables.items():
            file_content = file_content.replace(f"{{{{{var_name}}}}}", var_value)
        
        # Upload file
        file_response = update_file(
            github_username, repo_name, file_name,
            file_content.encode('utf-8'), github_token,
            f"Initial commit: {file_name}"
        )
        
        if file_response.status_code in [201, 200]:
            print(f"Created file: {file_name}")
            success_count += 1
        else:
            print(f"Error creating file {file_name}: {file_response.status_code}")
    
    print(f"Template project created with {success_count} files.")
    print(f"View your repository at: https://github.com/{github_username}/{repo_name}")