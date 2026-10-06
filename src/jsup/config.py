"""Config: CLI flags > env vars > ~/.config/jsup/config.json (mode 600)."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from urllib.parse import urlsplit
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "jsup" / "config.json"
KEYS = ("JIRA_SITE", "JIRA_EMAIL", "JIRA_API_TOKEN", "JIRA_PROJECT")


def _read_file() -> dict:
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Configuration must be a JSON object.")
        return data
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        raise ValueError(f"Invalid configuration JSON in {CONFIG_PATH}; repair the file before continuing.") from None


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temp = tempfile.mkstemp(prefix=".jira-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temp, 0o600)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def validate_site(site):
    url = urlsplit(site)
    if url.scheme != "https" or not url.hostname or url.username or url.password or url.query or url.fragment or url.path not in ("", "/"):
        raise ValueError("Use an HTTPS Jira site URL without credentials, a path, query, or fragment.")
    return site.rstrip("/")


def resolve_config(args, *, read_secret=True) -> dict:
    """Resolve existing settings without requiring authentication or printing secrets."""
    file_cfg = _read_file()
    if file_cfg.get("schema_version") == 2:
        from . import credentials
        chosen = getattr(args, "profile", None) or os.getenv("JIRA_PROFILE")
        explicit = [getattr(args, key, None) for key in ("site", "email", "token")]
        env = [os.getenv(key) for key in ("JIRA_SITE", "JIRA_EMAIL", "JIRA_API_TOKEN")]
        if chosen and any(explicit):
            raise ValueError("--profile/JIRA_PROFILE cannot be combined with identity flags; select one identity source.")
        source, values = None, None
        if any(explicit):
            if not all(explicit):
                raise ValueError("Identity flags require --site, --email and --token together; saved credentials will not be mixed.")
            source, values = "flags", explicit
        elif not chosen and any(env):
            if not all(env):
                raise ValueError("Environment identity requires JIRA_SITE, JIRA_EMAIL and JIRA_API_TOKEN together.")
            source, values = "environment", env
        if values:
            return dict(site=validate_site(values[0]), email=values[1], token=values[2],
                        project=getattr(args, "project", None) or os.getenv("JIRA_PROJECT", ""),
                        source=source, profile=None)
        chosen = chosen or file_cfg.get("active_profile")
        settings = file_cfg.get("profiles", {}).get(chosen)
        if not settings:
            if chosen:
                raise ValueError(f"Unknown profile: {chosen}. Run profile list or auth login.")
            return dict(site="", email="", token="", project="", source="none", profile=None)
        site = validate_site(settings["site"])
        allow_ui = sys.stdin.isatty() and not getattr(args, "no_input", False) and not getattr(args, "json", False)
        result = dict(site=site, email=settings["email"], token=credentials.get(chosen, settings, CONFIG_PATH, allow_ui=allow_ui) if read_secret else "",
                      project=getattr(args, "project", None) or os.getenv("JIRA_PROJECT") or settings.get("project", ""),
                      board=settings.get("board"), profile=chosen, source=settings["storage"])
        if settings.get("cloud_id"):
            result["api_site"] = "https://api.atlassian.com/ex/jira/" + settings["cloud_id"]
        return result
    if getattr(args, "profile", None) or os.getenv("JIRA_PROFILE"):
        raise ValueError("No named profiles exist yet. Run auth login or config migrate.")
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
    cfg["source"] = ("flags" if any(getattr(args, key, None) for key in ("site", "email", "token"))
                     else "environment" if any(os.getenv(k) for k in KEYS[:3]) else "legacy-config")
    cfg["profile"] = None
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
    if cur.get("schema_version") == 2:
        raise ValueError("Named profiles are configured. Use auth login instead of legacy config init.")
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
    atomic_json(CONFIG_PATH, {
        "JIRA_SITE": site.rstrip("/"), "JIRA_EMAIL": email,
        "JIRA_API_TOKEN": token, "JIRA_PROJECT": project,
    })
    print(f"Saved to {CONFIG_PATH} (mode 600). Try: jsup me")


def show_config(as_json: bool = False) -> None:
    cfg = _read_file()
    if cfg.get("schema_version") == 2:
        safe = {"file": str(CONFIG_PATH), "schema_version": 2,
                "active_profile": cfg.get("active_profile"),
                "profiles": {name: {k: v for k, v in settings.items() if k != "credential_id"}
                             for name, settings in cfg.get("profiles", {}).items()}}
        print(json.dumps(safe, indent=2))
        return
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
