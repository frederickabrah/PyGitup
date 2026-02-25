
import os
import subprocess
from ..github.api import create_repo, update_file
from ..core.config import get_github_username
from ..utils.ui import print_success, print_error, print_info, print_header, console, Table, box

# --- CORE PROJECT TEMPLATES ---

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

NEXTJS_TAILWIND = {
    "description": "Modern Next.js 14+ with Tailwind CSS & TypeScript",
    "files": {
        "package.json": """{
  "name": "{{PROJECT_NAME}}",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "react": "^18",
    "react-dom": "^18",
    "next": "14.1.0"
  },
  "devDependencies": {
    "typescript": "^5",
    "@types/node": "^20",
    "@types/react": "^18",
    "@types/react-dom": "^18",
    "autoprefixer": "^10.0.1",
    "postcss": "^8",
    "tailwindcss": "^3.3.0",
    "eslint": "^8",
    "eslint-config-next": "14.1.0"
  }
}""",
        "tsconfig.json": """{
  "compilerOptions": {
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [
      {
        "name": "next"
      }
    ],
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}""",
        "src/app/page.tsx": """export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-between p-24">
      <div className="z-10 max-w-5xl w-full items-center justify-between font-monospace text-sm flex">
        <p className="fixed left-0 top-0 flex w-full justify-center border-b border-gray-300 bg-gradient-to-b from-zinc-200 pb-6 pt-8 backdrop-blur-2xl dark:border-neutral-800 dark:bg-zinc-800/30 dark:from-inherit lg:static lg:w-auto  lg:rounded-xl lg:border lg:bg-gray-200 lg:p-4 lg:dark:bg-zinc-800/30">
          Get started by editing&nbsp;
          <code className="font-bold">src/app/page.tsx</code>
        </p>
      </div>

      <div className="relative flex place-items-center">
        <h1 className="text-6xl font-bold text-center">
          {{PROJECT_NAME}}
        </h1>
      </div>

      <div className="mb-32 grid text-center lg:max-w-5xl lg:w-full lg:mb-0 lg:grid-cols-4 lg:text-left">
        <p className="text-sm opacity-50">
          {{DESCRIPTION}}
        </p>
      </div>
    </main>
  )
}
""",
        "src/app/layout.tsx": """import './globals.css'
import type { Metadata } from 'next'
import { Inter } from 'next/font/google'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: '{{PROJECT_NAME}}',
  description: '{{DESCRIPTION}}',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>{children}</body>
    </html>
  )
}
""",
        "src/app/globals.css": """@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --foreground-rgb: 0, 0, 0;
  --background-start-rgb: 214, 219, 220;
  --background-end-rgb: 255, 255, 255;
}

@media (prefers-color-scheme: dark) {
  :root {
    --foreground-rgb: 255, 255, 255;
    --background-start-rgb: 0, 0, 0;
    --background-end-rgb: 0, 0, 0;
  }
}

body {
  color: rgb(var(--foreground-rgb));
  background: linear-gradient(
      to bottom,
      transparent,
      rgb(var(--background-end-rgb))
    )
    rgb(var(--background-start-rgb));
}
""",
        "README.md": """# {{PROJECT_NAME}}
{{DESCRIPTION}}

## Getting Started
`npm install && npm run dev`
"""
    }
}

RUST_MICROSERVICE = {
    "description": "High-performance Rust service using Axum & Tokio",
    "files": {
        "Cargo.toml": """[package]
name = "{{PROJECT_NAME}}"
version = "0.1.0"
edition = "2021"

[dependencies]
axum = "0.7"
tokio = { version = "1.0", features = ["full"] }
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
tower-http = { version = "0.5", features = ["cors"] }
""",
        "src/main.rs": """use axum::{
    routing::get,
    Json, Router,
};
use serde::Serialize;
use std::net::SocketAddr;

#[derive(Serialize)]
struct Status {
    message: String,
    service: String,
}

#[tokio::main]
async fn main() {
    let app = Router::new()
        .route("/", get(handler));

    let addr = SocketAddr::from(([127, 0, 0, 1], 3000));
    println!("🚀 {{PROJECT_NAME}} listening on {}", addr);
    
    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}

async fn handler() -> Json<Status> {
    Json(Status {
        message: "Hello from Rust!".to_string(),
        service: "{{PROJECT_NAME}}".to_string(),
    })
}
""",
        ".gitignore": """target/
Cargo.lock
""",
        "README.md": """# {{PROJECT_NAME}}
{{DESCRIPTION}}

## Build & Run
`cargo run`
"""
    }
}

PROJECT_TEMPLATES = {
    "fastapi-pro": FASTAPI_PRO,
    "express-node": NODE_EXPRESS,
    "cli-python": CLI_TOOL_PYTHON,
    "nextjs-tailwind": NEXTJS_TAILWIND,
    "rust-microservice": RUST_MICROSERVICE
}

def get_template_input(config, args=None):
    """Interactive template selector with rich UI."""
    print_header("Project Architecture Marketplace")
    
    table = Table(title="Available Architectures", box=box.ROUNDED)
    table.add_column("ID", style="cyan")
    table.add_column("Template Name", style="bold white")
    table.add_column("Description", style="dim")
    
    for i, (name, details) in enumerate(PROJECT_TEMPLATES.items(), 1):
        table.add_row(str(i), name, details["description"])
    
    console.print(table)
    
    choice = input("\n👉 Enter Template ID or Name: ").strip()
    
    # Resolve choice
    selected_name = None
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(PROJECT_TEMPLATES):
            selected_name = list(PROJECT_TEMPLATES.keys())[idx]
    elif choice in PROJECT_TEMPLATES:
        selected_name = choice
        
    if not selected_name:
        print_error("Invalid selection.")
        return None, None, None, None

    repo_name = input("📦 Target Repository Name: ").strip()
    description = input("📝 Short Description: ").strip() or PROJECT_TEMPLATES[selected_name]["description"]
    is_private = input("🔒 Make Private? (y/n) [y]: ").lower() != 'n'
    
    variables = {
        "PROJECT_NAME": repo_name,
        "DESCRIPTION": description,
        "AUTHOR": get_github_username(config)
    }
    
    return selected_name, repo_name, variables, is_private

def core_deploy_template(template_name, repo_name, description, is_private, github_username, github_token, config):
    """Core logic for deploying a template to GitHub with rollback support."""
    if template_name not in PROJECT_TEMPLATES:
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
    template = PROJECT_TEMPLATES[template_name]
    deployed_files = []
    
    try:
        for path, content in template["files"].items():
            # Render variables
            final_content = content
            for k, v in variables.items():
                final_content = final_content.replace(f"{{{{{k}}}}}", v)
                
            f_resp = update_file(github_username, repo_name, path, final_content.encode('utf-8'), github_token, f"chore: initialize {path} from template")
            if f_resp.status_code in [200, 201]:
                deployed_files.append(path)
            else:
                raise RuntimeError(f"Failed to deploy {path}: {f_resp.text}")
                
        return True, f"Deployed {len(deployed_files)} files to {github_username}/{repo_name}."
        
    except Exception as e:
        print_error(f"Deployment failed: {e}. Initiating rollback...")
        # Rollback: Delete the failed repository to prevent broken state
        from ..github.api import delete_repo_api
        delete_repo_api(github_username, repo_name, github_token)
        return False, f"Deployment failed and repository was removed: {e}"

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
