
import json
from pathlib import Path


def dna_validator(registry_path=None):
    """Scan memory/dna/registry.json and report any skills whose path no longer exists.

    Returns:
        dict with keys:
            ok      – True if every registered path exists on disk
            valid   – list of skill names whose path exists
            broken  – list of {skill, path} dicts for missing files
    """
    if registry_path is None:
        registry_path = Path(__file__).resolve().parent.parent / "dna" / "registry.json"

    registry_path = Path(registry_path)
    if not registry_path.exists():
        raise FileNotFoundError(f"Registry not found: {registry_path}")

    with open(registry_path, encoding="utf-8") as fh:
        registry = json.load(fh)

    valid, broken = [], []
    for name, entry in registry.get("skills", {}).items():
        path = entry.get("path", "")
        if Path(path).exists():
            valid.append(name)
        else:
            broken.append({"skill": name, "path": path})

    return {"ok": len(broken) == 0, "valid": valid, "broken": broken}
