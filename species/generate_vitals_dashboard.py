"""generate_vitals_dashboard — Intelligence Dashboard Evolution.

Scaffolds a Sovereign-themed Next.js 14 + Tailwind dashboard (vitals_ui/)
that visualises progress.txt and registry.json via a local SSE stream.

Panels:
  Live Feed       — tails progress.txt via /api/feed (SSE, 2 s poll)
  DNA Map         — reads registry.json via /api/dna (JSON, 15 s refresh)
  Manual Override — POSTs to Brain /evolve via /api/evolve (proxy)
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Dashboard file tree — every key is a relative path, value is file content.
# Substitution tokens:  {brain_root}  {brain_port}
# ---------------------------------------------------------------------------

_DASHBOARD_FILES: dict[str, str] = {
    # ── package.json ────────────────────────────────────────────────────────
    "package.json": """{
  "name": "vitals-ui",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start"
  },
  "dependencies": {
    "next": "14.2.3",
    "react": "^18.3.0",
    "react-dom": "^18.3.0"
  },
  "devDependencies": {
    "typescript": "^5.4.5",
    "@types/node": "^20.12.0",
    "@types/react": "^18.3.0",
    "tailwindcss": "^3.4.3",
    "postcss": "^8.4.38",
    "autoprefixer": "^10.4.19"
  }
}
""",

    # ── tailwind.config.js ──────────────────────────────────────────────────
    "tailwind.config.js": """/** @type {import("tailwindcss").Config} */
module.exports = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        sovereign: {
          bg:     "#0a0a0a",
          panel:  "#111111",
          border: "#1a1a1a",
          accent: "#00ff41",
          muted:  "#4a4a4a",
          text:   "#e0e0e0",
        },
      },
      fontFamily: {
        mono: ["JetBrains Mono", "Fira Code", "Consolas", "monospace"],
      },
    },
  },
  plugins: [],
};
""",

    # ── postcss.config.js ───────────────────────────────────────────────────
    "postcss.config.js": "module.exports = { plugins: { tailwindcss: {}, autoprefixer: {} } };\n",

    # ── next.config.js ──────────────────────────────────────────────────────
    "next.config.js": "/** @type {import('next').NextConfig} */\nmodule.exports = { reactStrictMode: true };\n",

    # ── tsconfig.json ───────────────────────────────────────────────────────
    "tsconfig.json": """{
  "compilerOptions": {
    "target": "es5",
    "lib": ["dom", "esnext"],
    "jsx": "preserve",
    "strict": true,
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "paths": { "@/*": ["./*"] }
  }
}
""",

    # ── .env.local ──────────────────────────────────────────────────────────
    ".env.local": "NEXT_PUBLIC_BRAIN_URL=http://localhost:{brain_port}\nMCP_BEARER_TOKEN=\n",

    # ── app/globals.css ─────────────────────────────────────────────────────
    "app/globals.css": """@import url("https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap");

@tailwind base;
@tailwind components;
@tailwind utilities;

:root { --color-accent: #00ff41; }

body {
  background-color: #0a0a0a;
  color: #e0e0e0;
  font-family: "JetBrains Mono", "Fira Code", monospace;
}

::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: #0a0a0a; }
::-webkit-scrollbar-thumb { background: #00ff41; border-radius: 2px; }
""",

    # ── app/layout.tsx ──────────────────────────────────────────────────────
    "app/layout.tsx": """import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Darwin-MCP Intelligence Dashboard",
  description: "Sovereign vitals interface for the Darwin-MCP organism",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-sovereign-bg font-mono text-sovereign-text">
        {children}
      </body>
    </html>
  );
}
""",

    # ── app/page.tsx ────────────────────────────────────────────────────────
    "app/page.tsx": """import LiveFeed from "@/components/LiveFeed";
import DnaMap from "@/components/DnaMap";
import ManualOverride from "@/components/ManualOverride";

export default function Home() {
  return (
    <main className="max-w-7xl mx-auto p-6 space-y-6">
      <header className="border-b border-sovereign-border pb-4">
        <h1 className="text-2xl font-bold text-sovereign-accent tracking-widest uppercase">
          ◈ Darwin-MCP Intelligence Dashboard
        </h1>
        <p className="text-sovereign-muted text-sm mt-1">
          Organism vitals · DNA registry · Manual evolution trigger
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-6">
          <LiveFeed />
          <ManualOverride />
        </div>
        <DnaMap />
      </div>
    </main>
  );
}
""",

    # ── app/api/dna/route.ts ────────────────────────────────────────────────
    "app/api/dna/route.ts": """import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

const BRAIN_ROOT = "{brain_root}";
const REGISTRY_PATH = path.join(BRAIN_ROOT, "memory", "dna", "registry.json");

export async function GET() {
  try {
    const raw = fs.readFileSync(REGISTRY_PATH, "utf-8");
    const registry = JSON.parse(raw);

    const skills = Object.entries(registry.skills || {}).map(
      ([name, entry]: [string, any]) => {
        const success = entry.success_count ?? 0;
        const failure = entry.failure_count ?? 0;
        const total = success + failure;
        const successRate = total === 0 ? 1.0 : success / total;
        return {
          name,
          status: entry.status ?? "unknown",
          version: entry.version ?? 1,
          evolved_at: entry.evolved_at ?? null,
          last_used_at: entry.last_used_at ?? null,
          total_calls: entry.total_calls ?? 0,
          success_rate: Math.round(successRate * 100),
          dependencies: entry.dependencies ?? [],
          short_description: entry.short_description ?? entry.description ?? "",
        };
      }
    );

    return NextResponse.json({
      organism_version: registry.organism_version,
      last_mutation: registry.last_mutation,
      total_species: skills.length,
      skills,
    });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
""",

    # ── app/api/feed/route.ts ───────────────────────────────────────────────
    "app/api/feed/route.ts": """import fs from "fs";
import path from "path";

const BRAIN_ROOT = "{brain_root}";
const PROGRESS_PATH = path.join(BRAIN_ROOT, "progress.txt");
const POLL_MS = 2000;

export async function GET() {
  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    start(controller) {
      let lastSize = 0;

      // Seed with last 20 lines immediately
      try {
        const content = fs.readFileSync(PROGRESS_PATH, "utf-8");
        const lines = content.trim().split("\\n").slice(-20);
        for (const line of lines) {
          if (line) controller.enqueue(encoder.encode(`data: ${JSON.stringify(line)}\\n\\n`));
        }
        lastSize = fs.statSync(PROGRESS_PATH).size;
      } catch { /* file may not exist yet */ }

      function poll() {
        try {
          const stat = fs.statSync(PROGRESS_PATH);
          if (stat.size > lastSize) {
            const len = stat.size - lastSize;
            const buf = Buffer.alloc(len);
            const fd = fs.openSync(PROGRESS_PATH, "r");
            fs.readSync(fd, buf, 0, len, lastSize);
            fs.closeSync(fd);
            lastSize = stat.size;
            for (const line of buf.toString("utf-8").trim().split("\\n")) {
              if (line) controller.enqueue(encoder.encode(`data: ${JSON.stringify(line)}\\n\\n`));
            }
          } else {
            controller.enqueue(encoder.encode(": keepalive\\n\\n"));
          }
        } catch {
          controller.enqueue(encoder.encode(": keepalive\\n\\n"));
        }
      }

      const interval = setInterval(poll, POLL_MS);
      return () => clearInterval(interval);
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
""",

    # ── app/api/evolve/route.ts ─────────────────────────────────────────────
    "app/api/evolve/route.ts": """import { NextRequest, NextResponse } from "next/server";

const BRAIN_URL = process.env.NEXT_PUBLIC_BRAIN_URL ?? "http://localhost:{brain_port}";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const res = await fetch(`${BRAIN_URL}/evolve`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${process.env.MCP_BEARER_TOKEN ?? ""}`,
      },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
""",

    # ── components/LiveFeed.tsx ─────────────────────────────────────────────
    "components/LiveFeed.tsx": """"use client";

import { useEffect, useRef, useState } from "react";

export default function LiveFeed() {
  const [lines, setLines] = useState<string[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const es = new EventSource("/api/feed");
    es.onmessage = (e) => {
      try {
        const line: string = JSON.parse(e.data);
        setLines((prev) => [...prev.slice(-200), line]);
      } catch { /* ignore malformed */ }
    };
    return () => es.close();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines]);

  return (
    <section className="bg-sovereign-panel border border-sovereign-border rounded p-4">
      <h2 className="text-sovereign-accent text-sm font-bold uppercase tracking-widest mb-3">
        ▸ Metabolism Record — progress.txt
      </h2>
      <div className="h-64 overflow-y-auto text-xs leading-relaxed space-y-0.5">
        {lines.length === 0 ? (
          <p className="text-sovereign-muted italic">Awaiting signal…</p>
        ) : (
          lines.map((l, i) => (
            <p key={i} className="font-mono text-sovereign-text hover:text-sovereign-accent transition-colors">
              {l}
            </p>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </section>
  );
}
""",

    # ── components/DnaMap.tsx ───────────────────────────────────────────────
    "components/DnaMap.tsx": """"use client";

import { useEffect, useState } from "react";

interface Species {
  name: string;
  status: string;
  version: number;
  evolved_at: string | null;
  last_used_at: string | null;
  total_calls: number;
  success_rate: number;
  dependencies: string[];
  short_description: string;
}

interface DnaData {
  organism_version: string;
  last_mutation: string | null;
  total_species: number;
  skills: Species[];
}

function SuccessBar({ rate }: { rate: number }) {
  const color =
    rate >= 80 ? "bg-sovereign-accent" : rate >= 50 ? "bg-yellow-500" : "bg-red-600";
  return (
    <div className="flex items-center gap-2 mt-1">
      <div className="flex-1 h-1 bg-sovereign-border rounded">
        <div className={`h-1 rounded ${color}`} style={{ width: `${rate}%` }} />
      </div>
      <span className="text-xs text-sovereign-muted w-10 text-right">{rate}%</span>
    </div>
  );
}

export default function DnaMap() {
  const [data, setData] = useState<DnaData | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = () => {
    fetch("/api/dna")
      .then((r) => r.json())
      .then(setData)
      .catch((e) => setError(e.message));
  };

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 15000);
    return () => clearInterval(id);
  }, []);

  if (error) return <p className="text-red-500 text-xs p-4">{error}</p>;
  if (!data) return <p className="text-sovereign-muted text-xs p-4 italic">Loading DNA Map…</p>;

  return (
    <section className="bg-sovereign-panel border border-sovereign-border rounded p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sovereign-accent text-sm font-bold uppercase tracking-widest">
          🧬 DNA Map — {data.total_species} Species
        </h2>
        <span className="text-sovereign-muted text-xs">v{data.organism_version}</span>
      </div>

      <div className="space-y-3 max-h-[32rem] overflow-y-auto pr-1">
        {data.skills.map((s) => (
          <div
            key={s.name}
            className="border border-sovereign-border rounded p-3 hover:border-sovereign-accent transition-colors"
          >
            <div className="flex items-start justify-between">
              <span className="font-mono font-bold text-sovereign-accent text-sm">{s.name}</span>
              <span
                className={`text-xs px-1.5 py-0.5 rounded font-mono ${
                  s.status === "active"
                    ? "bg-green-900 text-green-400"
                    : s.status === "Toxic"
                    ? "bg-red-900 text-red-400"
                    : "bg-yellow-900 text-yellow-400"
                }`}
              >
                {s.status} v{s.version}
              </span>
            </div>
            {s.short_description && (
              <p className="text-sovereign-muted text-xs mt-1 truncate">{s.short_description}</p>
            )}
            <SuccessBar rate={s.success_rate} />
            <div className="flex flex-wrap gap-4 mt-1 text-sovereign-muted text-xs">
              <span>calls: {s.total_calls}</span>
              {s.evolved_at && (
                <span>evolved: {new Date(s.evolved_at).toLocaleDateString()}</span>
              )}
              {s.dependencies.length > 0 && (
                <span>deps: {s.dependencies.join(", ")}</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
""",

    # ── components/ManualOverride.tsx ───────────────────────────────────────
    "components/ManualOverride.tsx": """"use client";

import { useState } from "react";

export default function ManualOverride() {
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [tests, setTests] = useState("");
  const [requirements, setRequirements] = useState("");
  const [status, setStatus] = useState<{
    type: "idle" | "loading" | "ok" | "error";
    message?: string;
  }>({ type: "idle" });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus({ type: "loading" });
    try {
      const res = await fetch("/api/evolve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          code,
          tests,
          requirements: requirements
            .split("\\n")
            .map((r) => r.trim())
            .filter(Boolean),
        }),
      });
      const data = await res.json();
      if (res.ok && data.status === "success") {
        setStatus({ type: "ok", message: `✅ ${data.message}` });
      } else {
        setStatus({ type: "error", message: `⚠ ${data.message ?? data.error}` });
      }
    } catch (err: any) {
      setStatus({ type: "error", message: `⚠ ${err.message}` });
    }
  };

  const inputCls =
    "w-full bg-sovereign-bg border border-sovereign-border rounded px-3 py-2 text-sm font-mono text-sovereign-text focus:outline-none focus:border-sovereign-accent";

  return (
    <section className="bg-sovereign-panel border border-sovereign-border rounded p-4">
      <h2 className="text-sovereign-accent text-sm font-bold uppercase tracking-widest mb-3">
        ⚡ Manual Override — request_evolution
      </h2>
      <form onSubmit={handleSubmit} className="space-y-3">
        <input
          className={inputCls}
          placeholder="skill_name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
        <textarea
          className={`${inputCls} h-28 resize-y`}
          placeholder="# Python code…"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          required
        />
        <textarea
          className={`${inputCls} h-20 resize-y`}
          placeholder="# pytest tests…"
          value={tests}
          onChange={(e) => setTests(e.target.value)}
          required
        />
        <textarea
          className={`${inputCls} h-12 resize-y`}
          placeholder="requirements (one per line)"
          value={requirements}
          onChange={(e) => setRequirements(e.target.value)}
        />
        <button
          type="submit"
          disabled={status.type === "loading"}
          className="w-full py-2 bg-sovereign-accent text-sovereign-bg font-bold text-sm rounded hover:opacity-90 disabled:opacity-50 transition-opacity uppercase tracking-widest font-mono"
        >
          {status.type === "loading" ? "Evolving…" : "▸ Trigger Evolution"}
        </button>
        {status.message && (
          <p
            className={`text-xs font-mono ${
              status.type === "ok" ? "text-sovereign-accent" : "text-red-400"
            }`}
          >
            {status.message}
          </p>
        )}
      </form>
    </section>
  );
}
""",

    # ── README.md ───────────────────────────────────────────────────────────
    "README.md": """# Darwin-MCP Intelligence Dashboard

Sovereign-themed vitals interface for the Darwin-MCP organism.

## Panels

| Panel | Source | Update cadence |
|-------|--------|----------------|
| **Metabolism Record** | `progress.txt` (SSE tail) | Real-time (2 s poll) |
| **DNA Map** | `registry.json` (direct read) | Every 15 s |
| **Manual Override** | Brain `/evolve` API | On submit |

## Run

```bash
npm install
npm run dev    # http://localhost:3000
```

## Environment

Edit `.env.local`:

```
NEXT_PUBLIC_BRAIN_URL=http://localhost:8000
MCP_BEARER_TOKEN=your-token-here
```

> Scaffolded by Darwin-MCP `generate_vitals_dashboard` species.
""",
}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def generate_vitals_dashboard(
    output_dir: Optional[str] = None,
    brain_root: Optional[str] = None,
    brain_port: int = 8000,
    dry_run: bool = False,
) -> dict:
    """Scaffold the Intelligence Dashboard Next.js project.

    Args:
        output_dir:  Target directory. Defaults to <cwd>/vitals_ui.
        brain_root:  Absolute path to the mcp-evolution-core repo root.
                     Defaults to parent³ of __file__ — same resolution used
                     throughout the Brain codebase.
        brain_port:  Brain SSE server port written to .env.local. Default: 8000.
        dry_run:     When True, return the manifest without writing any files.

    Returns:
        dict with keys:
            status        — "ok" or "error"
            dry_run       — echoed flag
            name          — "vitals_ui"
            root          — absolute path the project would be/was created at
            files_created — sorted list of relative paths
            message       — human-readable summary
    """
    if brain_root is None:
        brain_root = str(Path(__file__).resolve().parent.parent.parent)

    root = (
        Path(output_dir).expanduser().resolve()
        if output_dir
        else Path.cwd() / "vitals_ui"
    )

    files_manifest: list[str] = sorted(_DASHBOARD_FILES.keys())

    if dry_run:
        return {
            "status": "ok",
            "dry_run": True,
            "name": "vitals_ui",
            "root": str(root),
            "files_created": files_manifest,
            "message": (
                f"🔬 dry_run: Intelligence Dashboard would create "
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
    for rel_path, content in _DASHBOARD_FILES.items():
        abs_path = root / rel_path
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        filled = content.replace("{brain_root}", brain_root).replace(
            "{brain_port}", str(brain_port)
        )
        abs_path.write_text(filled, encoding="utf-8")
        files_created.append(rel_path)

    return {
        "status": "ok",
        "dry_run": False,
        "name": "vitals_ui",
        "root": str(root),
        "files_created": sorted(files_created),
        "message": (
            f"✅ Intelligence Dashboard scaffolded → {root} "
            f"({len(files_created)} files created)"
        ),
    }


def run(output_dir: Optional[str] = None, brain_root: Optional[str] = None) -> dict:
    return generate_vitals_dashboard(output_dir=output_dir, brain_root=brain_root)
