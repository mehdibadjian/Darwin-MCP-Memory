# Darwin MCP Memory

This repository stores the stateful memory layer for Darwin MCP.

## Purpose

- Keep long-lived skill metadata and species definitions outside the stateless brain service.
- Provide a single source of truth for what species exist and how they are registered.

## Structure

- `dna/registry.json`: canonical registry of registered species.
- `species/`: Python species implementations loaded by the brain.
- `requirements.txt`: Python dependencies needed by species.

## Typical Workflow

1. Update species code in `species/`.
2. Update `dna/registry.json` if species registration metadata changes.
3. Commit and push changes in this memory repository.
4. In the parent repository, commit the updated submodule pointer.

## Notes

- Treat `dna/registry.json` as authoritative state.
- Keep species files focused and testable.