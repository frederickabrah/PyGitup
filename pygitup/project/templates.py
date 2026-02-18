
import os
import subprocess
from ..github.api import create_repo, update_file
from ..core.config import get_github_username
from ..utils.ui import print_success, print_error, print_info, print_header, console, Table, box

# --- GOD TIER TEMPLATE DEFINITIONS ---

FASTAPI_PRO = {
    "description": "Production-ready FastAPI backend with Docker & Tests",
    "files": {
        "main.py": """from fastapi import FastAPI
app = FastAPI(title="{{PROJECT_NAME}}")

@app.get("/")
def read_root():
    return {"message": "Welcome to {{PROJECT_NAME}} API"}
""",
        "requirements.txt": "fastapi\\nuvicorn\\npytest\\nhttpx",
        "Dockerfile": """FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]""",
        "tests/test_main.py": """from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to {{PROJECT_NAME}} API"}
""",
        "README.md": """# {{PROJECT_NAME}}
{{DESCRIPTION}}

## Setup
1. `pip install -r requirements.txt`
2. `uvicorn main:app --reload`

## Docker
`docker build -t {{PROJECT_NAME}} .`
"""
    }
}

NODE_EXPRESS = {
    "description": "Clean Express.js starter with environment config",
    "files": {
        "index.js": """const express = require('express');
const app = express();
const port = process.env.PORT || 3000;

app.get('/', (req, res) => {
  res.send('Hello from {{PROJECT_NAME}}!');
});

app.listen(port, () => {
  console.log(`{{PROJECT_NAME}} listening at http://localhost:${port}`);
});""",
        "package.json": """{
  "name": "{{PROJECT_NAME}}",
  "version": "1.0.0",
  "description": "{{DESCRIPTION}}",
  "main": "index.js",
  "dependencies": {
    "express": "^4.18.2"
  }
}""",
        ".gitignore": """node_modules
.env""",
        "README.md": """# {{PROJECT_NAME}}
{{DESCRIPTION}}

## Start
`npm install && node index.js`
"""
    }
}

CLI_TOOL_PYTHON = {
    "description": "Professional CLI tool template using Typer",
    "files": {
        "app.py": """import typer
app = typer.Typer()

@app.command()
def hello(name: str = "World"):
    print(f"Hello {name}")

if __name__ == "__main__":
    app()""",
        "requirements.txt": "typer[all]",
        "setup.py": """from setuptools import setup
setup(
    name='{{PROJECT_NAME}}',
    version='0.1.0',
    py_modules=['app'],
    install_requires=['typer'],
    entry_points={'console_scripts': ['{{PROJECT_NAME}}=app:app']}
)""",
        "README.md": """# {{PROJECT_NAME}}
{{DESCRIPTION}}
"""
    }
}

GOD_TEMPLATES = {
    "fastapi-pro": FASTAPI_PRO,
    "express-node": NODE_EXPRESS,
    "cli-python": CLI_TOOL_PYTHON
}

def get_template_input(config, args=None):
    """Interactive template selector with rich UI."""
    print_header("God Mode Template Marketplace")
    
    table = Table(title="Available Architectures", box=box.ROUNDED)
    table.add_column("ID", style="cyan")
    table.add_column("Template Name", style="bold white")
    table.add_column("Description", style="dim")
    
    for i, (name, details) in enumerate(GOD_TEMPLATES.items(), 1):
        table.add_row(str(i), name, details["description"])
    
    console.print(table)
    
    choice = input("\n👉 Enter Template ID or Name: ").strip()
    
    # Resolve choice
    selected_name = None
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(GOD_TEMPLATES):
            selected_name = list(GOD_TEMPLATES.keys())[idx]
    elif choice in GOD_TEMPLATES:
        selected_name = choice
        
    if not selected_name:
        print_error("Invalid selection.")
        return None, None, None, None

    repo_name = input("📦 Target Repository Name: ").strip()
    description = input("📝 Short Description: ").strip() or GOD_TEMPLATES[selected_name]["description"]
    is_private = input("🔒 Make Private? (y/n) [y]: ").lower() != 'n'
    
    variables = {
        "PROJECT_NAME": repo_name,
        "DESCRIPTION": description,
        "AUTHOR": get_github_username(config)
    }
    
    return selected_name, repo_name, variables, is_private

def core_deploy_template(template_name, repo_name, description, is_private, github_username, github_token, config):
    """Core logic for deploying a template to GitHub, decoupled from CLI input."""
    if template_name not in GOD_TEMPLATES:
        return False, "Template not found."

    variables = {
        "PROJECT_NAME": repo_name,
        "DESCRIPTION": description,
        "AUTHOR": get_github_username(config)
    }
    
    # 1. Create GitHub Repo
    resp = create_repo(github_username, repo_name, github_token, description=description, private=is_private)
    if resp.status_code not in [200, 201]:
        return False, f"Cloud initialization failed: {resp.text}"

    # 2. Deploy Template Files
    template = GOD_TEMPLATES[template_name]
    success_count = 0
    for path, content in template["files"].items():
        # Render variables
        final_content = content
        for k, v in variables.items():
            final_content = final_content.replace(f"{{{{{k}}}}}", v)
            
        f_resp = update_file(github_username, repo_name, path, final_content.encode('utf-8'), github_token, f"chore: initialize {path} from template")
        if f_resp.status_code in [200, 201]:
            success_count += 1
            
    return True, f"Deployed {success_count} files to {github_username}/{repo_name}."

def create_project_from_template(github_username, github_token, config, args=None):
    """CLI Wrapper for template orchestration."""
    template_name, repo_name, variables, is_private = get_template_input(config, args)
    if not template_name: return
    
    print_info(f"Building {template_name} architecture...")
    success, msg = core_deploy_template(template_name, repo_name, variables["DESCRIPTION"], is_private, github_username, github_token, config)
    
    if success:
        print_success(msg)
        print_info(f"URL: https://github.com/{github_username}/{repo_name}")
    else:
        print_error(msg)
