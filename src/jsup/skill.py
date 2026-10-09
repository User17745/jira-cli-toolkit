"""The agent skill bundled with the CLI, so its instructions match the installed commands."""
from __future__ import annotations

from importlib.resources import files
from pathlib import Path

DEFAULT_DIR = Path.home() / ".claude" / "skills" / "jira"


def text() -> str:
    return files("jsup").joinpath("data/skill/SKILL.md").read_text(encoding="utf-8")


def install(directory=None, force=False) -> dict:
    target = Path(directory).expanduser() / "SKILL.md" if directory else DEFAULT_DIR / "SKILL.md"
    content = text()
    if target.is_symlink():
        raise ValueError(f"Refusing to write through a symbolic link: {target}")
    if target.exists():
        if target.read_text(encoding="utf-8") == content:
            return {"path": str(target), "status": "unchanged"}
        if not force:
            raise ValueError(f"{target} exists and differs from this version's skill. "
                             "Compare it with `jira skill show`, then pass --force to replace it.")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {"path": str(target), "status": "written"}
