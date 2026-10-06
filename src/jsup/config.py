"""Config: CLI flags > env vars > ~/.config/jsup/config.json (mode 600)."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "jsup" / "config.json"
KEYS = ("JIRA_SITE", "JIRA_EMAIL", "JIRA_API_TOKEN", "JIRA_PROJECT")


def _read_file() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def resolve_config(args) -> dict:
    """Resolve existing settings without requiring authentication or printing secrets."""
    file_cfg = _read_file()
    cfg = {
        "site": (getattr(args, "site", None) or os.getenv("JIRA_SITE")
                 or file_cfg.get("JIRA_SITE", "")).rstrip("/"),
        "email": (getattr(args, "email", None) or os.getenv("JIRA_EMAIL")
                  or file_cfg.get("JIRA_EMAIL", "")),
        "token": (getattr(args, "token", None) or os.getenv("JIRA_API_TOKEN")
                  or file_cfg.get("JIRA_API_TOKEN", "")),
        "project": (getattr(args, "project", None) or os.getenv("JIRA_PROJECT")
                    or file_cfg.get("JIRA_PROJECT", "")),
    }
    return cfg


def get_config(args) -> dict:
    cfg = resolve_config(args)
    if not (cfg["site"] and cfg["email"] and cfg["token"]):
        print("Not configured yet. Run: jsup config init", file=sys.stderr)
        sys.exit(2)
    return cfg


def init_config() -> None:
    import getpass
    cur = _read_file()
    site = input(f"Jira site [{cur.get('JIRA_SITE') or os.getenv('JIRA_SITE', '')}]: ").strip() \
        or cur.get("JIRA_SITE") or os.getenv("JIRA_SITE", "")
    email = input(f"Email [{cur.get('JIRA_EMAIL') or os.getenv('JIRA_EMAIL', '')}]: ").strip() \
        or cur.get("JIRA_EMAIL") or os.getenv("JIRA_EMAIL", "")
    default_token = "*****" if (cur.get("JIRA_API_TOKEN") or os.getenv("JIRA_API_TOKEN")) else ""
    token_in = getpass.getpass(f"API token [{default_token}]: ").strip()
    token = token_in or cur.get("JIRA_API_TOKEN") or os.getenv("JIRA_API_TOKEN", "")
    project = input(f"Default project [{cur.get('JIRA_PROJECT') or os.getenv('JIRA_PROJECT', '')}]: ").strip() \
        or cur.get("JIRA_PROJECT") or os.getenv("JIRA_PROJECT", "")
    if not (site and email and token):
        print("site, email and token are required.", file=sys.stderr)
        sys.exit(2)
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps({
        "JIRA_SITE": site.rstrip("/"), "JIRA_EMAIL": email,
        "JIRA_API_TOKEN": token, "JIRA_PROJECT": project,
    }, indent=2) + "\n")
    CONFIG_PATH.chmod(0o600)
    print(f"Saved to {CONFIG_PATH} (mode 600). Try: jsup me")


def show_config(as_json: bool = False) -> None:
    cfg = _read_file()
    if as_json:
        print(json.dumps({"file": str(CONFIG_PATH), "site": cfg.get("JIRA_SITE") or None,
                          "email": cfg.get("JIRA_EMAIL") or None,
                          "project": cfg.get("JIRA_PROJECT") or None,
                          "token_configured": bool(cfg.get("JIRA_API_TOKEN"))}, indent=2))
        return
    if not cfg:
        print("No config file. Run: jsup config init")
        return
    tok = cfg.get("JIRA_API_TOKEN", "")
    print(f"file:    {CONFIG_PATH}")
    print(f"site:    {cfg.get('JIRA_SITE', '')}")
    print(f"email:   {cfg.get('JIRA_EMAIL', '')}")
    print(f"token:   {'*' * 8 + tok[-4:] if len(tok) > 4 else '(missing)'}")
    print(f"project: {cfg.get('JIRA_PROJECT', '')}")
