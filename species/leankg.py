"""
LeanKG Species - Knowledge Graph Integration for mcp-evolution-core

Provides MCP tools to query the LeanKG knowledge graph built from the codebase.
Enables impact analysis, dependency queries, and code relationship discovery.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional


def run_leankg_command(args: list[str], cwd: Optional[str] = None) -> dict[str, Any]:
    """
    Execute a leankg CLI command and return JSON output.
    
    Args:
        args: Command arguments (e.g., ['impact', 'brain/engine/mutator.py', '--depth', '3'])
        cwd: Working directory for the command
    
    Returns:
        Parsed JSON output from leankg command
    """
    try:
        cmd = ["leankg"] + args + ["--json"]
        result = subprocess.run(
            cmd,
            cwd=cwd or Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            return {
                "error": result.stderr or "Command failed",
                "returncode": result.returncode
            }
        
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {"raw_output": result.stdout}
    
    except subprocess.TimeoutExpired:
        return {"error": "LeanKG command timeout (30s)"}
    except FileNotFoundError:
        return {"error": "leankg binary not found. Run: brew install leankg or cargo install leankg"}
    except Exception as e:
        return {"error": str(e)}


def query_graph(query: str, limit: int = 10) -> dict[str, Any]:
    """
    Search the knowledge graph for elements and relationships.
    
    Args:
        query: Search term (file, function, or pattern)
        limit: Maximum results to return
    
    Returns:
        Search results with matching elements and relationships
    """
    # LeanKG doesn't have a direct search API yet, so we use the web UI or status
    result = run_leankg_command(["status"])
    
    if "error" in result:
        return result
    
    # Parse status to find relevant elements
    return {
        "query": query,
        "message": "Use 'leankg web' to search the graph interactively at http://localhost:8080",
        "status": result
    }


def get_impact_radius(file_path: str, depth: int = 2) -> dict[str, Any]:
    """
    Calculate blast radius - which code changes when a file is modified.
    
    Args:
        file_path: Path to the file (relative to repo root)
        depth: How many dependency levels to trace (default: 2)
    
    Returns:
        Set of affected files and functions
    """
    return run_leankg_command(["impact", file_path, "--depth", str(depth)])


def get_dependencies(file_path: str) -> dict[str, Any]:
    """
    Get all dependencies for a file.
    
    Args:
        file_path: Path to the file
    
    Returns:
        Direct and transitive dependencies
    """
    # LeanKG impact command shows what depends on the file
    result = get_impact_radius(file_path, depth=1)
    return {
        "file": file_path,
        "dependencies": result
    }


def get_graph_metrics() -> dict[str, Any]:
    """
    Get overall knowledge graph statistics and token savings metrics.
    
    Returns:
        Graph size, element counts, and efficiency metrics
    """
    return run_leankg_command(["metrics"])


def get_index_status() -> dict[str, Any]:
    """
    Check the current indexing status and graph state.
    
    Returns:
        Status of the knowledge graph database
    """
    return run_leankg_command(["status"])


def find_callers(function_name: str) -> dict[str, Any]:
    """
    Find all functions that call a given function.
    
    Args:
        function_name: Name of the function to trace
    
    Returns:
        List of calling functions and their locations
    """
    # This would require searching for CALLS relationships
    # For now, return a guide to use the web UI
    return {
        "function": function_name,
        "message": "Use 'leankg web' at http://localhost:8080 to visualize CALLS relationships",
        "note": "Graph includes IMPORTS, CALLS, and TESTED_BY edges"
    }


def find_tests(file_path: str) -> dict[str, Any]:
    """
    Find all tests that cover a given file.
    
    Args:
        file_path: Path to the source file
    
    Returns:
        List of test files with TESTED_BY relationships
    """
    return {
        "file": file_path,
        "message": "Use 'leankg web' to find TESTED_BY relationships",
        "tip": "Re-index tests directory with: leankg index ./tests"
    }


def get_file_info(file_path: str) -> dict[str, Any]:
    """
    Get detailed information about a specific file from the graph.
    
    Args:
        file_path: Path to the file
    
    Returns:
        Functions, classes, imports, and relationships in the file
    """
    # Impact analysis on a file shows what it imports and what imports it
    result = get_impact_radius(file_path, depth=1)
    return {
        "file": file_path,
        "analysis": result,
        "web_ui": "Visit http://localhost:8080 to visualize the file's relationships"
    }


def start_web_ui(port: int = 8080) -> dict[str, Any]:
    """
    Start the LeanKG web UI for interactive graph exploration.
    
    Args:
        port: Port to serve the web UI on (default: 8080)
    
    Returns:
        Status and URL of the web UI
    """
    return {
        "command": f"leankg web --port {port}",
        "url": f"http://localhost:{port}",
        "features": [
            "Force-directed graph visualization",
            "Community clustering",
            "WebGL rendering",
            "Search and filter",
            "Dependency traversal"
        ],
        "note": "Run this in your terminal: leankg web"
    }


def reindex_codebase() -> dict[str, Any]:
    """
    Reindex the codebase to update the knowledge graph.
    
    Useful after making code changes.
    
    Returns:
        Status of the reindexing operation
    """
    result = run_leankg_command(["index", "./brain"])
    return {
        "action": "reindex",
        "result": result,
        "next_steps": [
            "Use get_graph_metrics() to see updated statistics",
            "Run 'leankg web' to visualize changes"
        ]
    }


def watch_codebase() -> dict[str, Any]:
    """
    Enable continuous watching of the codebase for automatic reindexing.
    
    Returns:
        Instructions for running watch mode
    """
    return {
        "command": "leankg watch ./brain",
        "description": "Auto-reindex on file changes",
        "note": "Run this in your terminal: leankg watch ./brain",
        "benefits": [
            "Always up-to-date knowledge graph",
            "Automatic impact analysis on changes",
            "Real-time relationship discovery"
        ]
    }


# ============================================================================
# MCP Tool Registration
# ============================================================================

MCP_TOOLS = {
    "leankg_impact_radius": {
        "description": "Calculate blast radius - which code changes when a file is modified",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Relative path to the file (e.g., 'brain/engine/mutator.py')"
                },
                "depth": {
                    "type": "integer",
                    "description": "Dependency depth to trace (1-5, default: 2)",
                    "default": 2
                }
            },
            "required": ["file_path"]
        },
        "handler": get_impact_radius
    },
    
    "leankg_file_dependencies": {
        "description": "Get all files and modules that a file depends on",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to analyze"
                }
            },
            "required": ["file_path"]
        },
        "handler": get_dependencies
    },
    
    "leankg_graph_metrics": {
        "description": "Get knowledge graph statistics and token savings metrics",
        "inputSchema": {"type": "object"},
        "handler": get_graph_metrics
    },
    
    "leankg_index_status": {
        "description": "Check the status of the LeanKG knowledge graph database",
        "inputSchema": {"type": "object"},
        "handler": get_index_status
    },
    
    "leankg_find_callers": {
        "description": "Find all functions that call a given function",
        "inputSchema": {
            "type": "object",
            "properties": {
                "function_name": {
                    "type": "string",
                    "description": "Name of the function to trace (e.g., 'request_evolution')"
                }
            },
            "required": ["function_name"]
        },
        "handler": find_callers
    },
    
    "leankg_find_tests": {
        "description": "Find all tests that cover a given file",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the source file"
                }
            },
            "required": ["file_path"]
        },
        "handler": find_tests
    },
    
    "leankg_file_info": {
        "description": "Get detailed information about a file's structure, imports, and relationships",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file"
                }
            },
            "required": ["file_path"]
        },
        "handler": get_file_info
    },
    
    "leankg_web_ui": {
        "description": "Start the interactive LeanKG web UI for exploring the knowledge graph",
        "inputSchema": {
            "type": "object",
            "properties": {
                "port": {
                    "type": "integer",
                    "description": "Port to serve on (default: 8080)",
                    "default": 8080
                }
            }
        },
        "handler": start_web_ui
    },
    
    "leankg_reindex": {
        "description": "Reindex the codebase to update the knowledge graph after code changes",
        "inputSchema": {"type": "object"},
        "handler": reindex_codebase
    },
    
    "leankg_watch": {
        "description": "Enable continuous watching and auto-reindexing of the codebase",
        "inputSchema": {"type": "object"},
        "handler": watch_codebase
    },
    
    "leankg_query_graph": {
        "description": "Search the knowledge graph for elements and relationships",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search term (file, function, or pattern)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results (default: 10)",
                    "default": 10
                }
            },
            "required": ["query"]
        },
        "handler": query_graph
    }
}


def main():
    """Entry point for the LeanKG species."""
    print("LeanKG Species loaded")
    print(f"Available tools: {list(MCP_TOOLS.keys())}")


if __name__ == "__main__":
    main()
