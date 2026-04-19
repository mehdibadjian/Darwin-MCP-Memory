"""Scaffold Generator species — Project Architect Evolution.

Accepts a project_type and name, creates a full-stack folder structure
with boilerplate files, and returns a manifest of everything created.

Supported project types: FastAPI, React, Tailwind, NextJS
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Boilerplate templates per project type
# ---------------------------------------------------------------------------

_FASTAPI_FILES = {
    "main.py": '''\
from fastapi import FastAPI

app = FastAPI(title="{name}", version="0.1.0")


@app.get("/health")
def health():
    return {{"status": "ok"}}
''',
    "requirements.txt": '''\
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
pydantic>=2.0
''',
    ".env.example": '''\
DATABASE_URL=sqlite:///./app.db
SECRET_KEY=change_me
''',
    "routers/__init__.py": "",
    "routers/health.py": '''\
from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
def health_check():
    return {{"status": "ok"}}
''',
    "models/__init__.py": "",
    "schemas/__init__.py": "",
    "tests/__init__.py": "",
    "tests/test_main.py": '''\
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
''',
    "README.md": '''\
# {name}

A FastAPI project scaffolded by Darwin-MCP scaffold_generator.

## Run

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```
''',
}

_REACT_FILES = {
    "package.json": '''\
{{
  "name": "{name_slug}",
  "version": "0.1.0",
  "private": true,
  "scripts": {{
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test"
  }},
  "dependencies": {{
    "react": "^18.0.0",
    "react-dom": "^18.0.0",
    "react-scripts": "5.0.1"
  }}
}}
''',
    "public/index.html": '''\
<!DOCTYPE html>
<html lang="en">
  <head><meta charset="UTF-8" /><title>{name}</title></head>
  <body><div id="root"></div></body>
</html>
''',
    "src/index.tsx": '''\
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";

const root = ReactDOM.createRoot(document.getElementById("root") as HTMLElement);
root.render(<React.StrictMode><App /></React.StrictMode>);
''',
    "src/App.tsx": '''\
import React from "react";

export default function App() {{
  return <h1>{name}</h1>;
}}
''',
    "src/components/.gitkeep": "",
    "src/hooks/.gitkeep": "",
    "src/pages/.gitkeep": "",
    "README.md": '''\
# {name}

A React project scaffolded by Darwin-MCP scaffold_generator.

## Run

```bash
npm install
npm start
```
''',
}

_TAILWIND_FILES = {
    **_REACT_FILES,
    "tailwind.config.js": '''\
/** @type {{import("tailwindcss").Config}} */
module.exports = {{
  content: ["./src/**/*.{{js,jsx,ts,tsx}}"],
  theme: {{ extend: {{}} }},
  plugins: [],
}};
''',
    "postcss.config.js": '''\
module.exports = {{
  plugins: {{ tailwindcss: {{}}, autoprefixer: {{}} }},
}};
''',
    "src/index.css": '''\
@tailwind base;
@tailwind components;
@tailwind utilities;
''',
}

_NEXTJS_FILES = {
    "package.json": '''\
{{
  "name": "{name_slug}",
  "version": "0.1.0",
  "private": true,
  "scripts": {{
    "dev": "next dev",
    "build": "next build",
    "start": "next start"
  }},
  "dependencies": {{
    "next": "14.0.0",
    "react": "^18.0.0",
    "react-dom": "^18.0.0"
  }},
  "devDependencies": {{
    "typescript": "^5.0.0",
    "@types/node": "^20.0.0",
    "@types/react": "^18.0.0"
  }}
}}
''',
    "next.config.js": 'module.exports = {{ reactStrictMode: true }};\n',
    "tsconfig.json": '''\
{{
  "compilerOptions": {{
    "target": "es5", "lib": ["dom", "esnext"],
    "jsx": "preserve", "strict": true,
    "moduleResolution": "bundler", "resolveJsonModule": true
  }}
}}
''',
    "app/layout.tsx": '''\
export const metadata = {{ title: "{name}" }};

export default function RootLayout({{ children }}: {{ children: React.ReactNode }}) {{
  return (
    <html lang="en"><body>{{children}}</body></html>
  );
}}
''',
    "app/page.tsx": '''\
export default function Home() {{
  return <main><h1>{name}</h1></main>;
}}
''',
    "app/globals.css": "* { box-sizing: border-box; margin: 0; }\n",
    "components/.gitkeep": "",
    "lib/.gitkeep": "",
    "public/.gitkeep": "",
    "README.md": '''\
# {name}

A Next.js project scaffolded by Darwin-MCP scaffold_generator.

## Run

```bash
npm install
npm run dev
```
''',
}

_TEMPLATES: dict[str, dict] = {
    "fastapi": _FASTAPI_FILES,
    "react": _REACT_FILES,
    "tailwind": _TAILWIND_FILES,
    "nextjs": _NEXTJS_FILES,
}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def scaffold_generator(
    project_type: str,
    name: str,
    output_dir: Optional[str] = None,
    dry_run: bool = False,
) -> dict:
    """Generate a full-stack project scaffold from a single sentence.

    Args:
        project_type: One of ``FastAPI``, ``React``, ``Tailwind``, ``NextJS``
                      (case-insensitive).
        name:         Human-readable project name (e.g. ``Personal Finance Dashboard``).
        output_dir:   Absolute or relative path where the scaffold is created.
                      Defaults to ``<cwd>/<name-slug>``.
        dry_run:      When True, return the full file manifest without writing
                      anything to disk — the Lysosome mode for safe validation
                      and CI checks that would otherwise clog the Droplet.

    Returns:
        dict with keys:
            status        — "ok" or "error"
            dry_run       — echoed flag
            project_type  — normalised type used
            name          — original name
            root          — absolute path the scaffold *would* be created at
            files_created — list of relative paths (written or would-be-written)
            message       — human-readable summary
    """
    norm = project_type.strip().lower().replace(" ", "").replace("-", "").replace("_", "")
    # Map aliases
    if norm in ("nextjs", "next"):
        norm = "nextjs"
    elif norm in ("fastapi",):
        norm = "fastapi"
    elif norm in ("react",):
        norm = "react"
    elif norm in ("tailwind", "tailwindcss"):
        norm = "tailwind"

    if norm not in _TEMPLATES:
        return {
            "status": "error",
            "error": f"Unknown project_type '{project_type}'. Supported: FastAPI, React, Tailwind, NextJS",
            "supported": list(_TEMPLATES.keys()),
        }

    name_slug = name.strip().lower().replace(" ", "-").replace("_", "-")

    if output_dir:
        root = Path(output_dir).expanduser().resolve()
    else:
        root = Path.cwd() / name_slug

    template = _TEMPLATES[norm]
    files_manifest: list[str] = sorted(template.keys())

    # --- Lysosome mode: return manifest, touch nothing on disk ---
    if dry_run:
        return {
            "status": "ok",
            "dry_run": True,
            "project_type": norm,
            "name": name,
            "root": str(root),
            "files_created": files_manifest,
            "message": (
                f"🔬 dry_run: '{name}' ({norm}) would create "
                f"{len(files_manifest)} files at {root}"
            ),
        }

    if root.exists():
        return {
            "status": "error",
            "error": f"Output directory already exists: {root}",
            "root": str(root),
        }

    files_created: list[str] = []

    for rel_path, content in template.items():
        abs_path = root / rel_path
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        filled = content.replace("{name_slug}", name_slug).replace("{name}", name)
        abs_path.write_text(filled, encoding="utf-8")
        files_created.append(rel_path)

    return {
        "status": "ok",
        "dry_run": False,
        "project_type": norm,
        "name": name,
        "root": str(root),
        "files_created": sorted(files_created),
        "message": (
            f"✅ Scaffolded '{name}' ({norm}) → {root} "
            f"({len(files_created)} files created)"
        ),
    }


# Allow direct invocation for quick testing
def run(project_type: str = "fastapi", name: str = "my-project", output_dir: Optional[str] = None) -> dict:
    return scaffold_generator(project_type, name, output_dir)
