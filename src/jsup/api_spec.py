"""`jira api --spec`: look up endpoint requirements in cached official OpenAPI documents.

Discovery is public and advisory. It never resolves a Jira identity or sends credentials,
fetches only the fixed official spec URLs, resolves references only inside the fetched
document, and never blocks a raw request when a spec is missing or stale.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from .api import ApiError, invalid, validate_path

SOURCES = {
    "platform": ("Jira Cloud platform REST API", "https://developer.atlassian.com/cloud/jira/platform/swagger-v3.v3.json"),
    "software": ("Jira Software Cloud API", "https://developer.atlassian.com/cloud/jira/software/swagger.v3.json"),
    "service-management": ("Jira Service Management REST API", "https://developer.atlassian.com/cloud/jira/service-desk/swagger.v3.json"),
}
# Path prefixes served by each document; anything else under /rest/ belongs to Jira Software.
PLATFORM_PREFIXES = ("/rest/api/", "/rest/atlassian-connect/", "/rest/forge/", "/rest/internal/")
SERVICE_MANAGEMENT_PREFIXES = ("/rest/servicedeskapi/",)
MAX_SPEC = 20 * 1024 * 1024
STALE_AFTER = 30 * 24 * 3600
MAX_DEPTH = 6
MAX_NODES = 4000
RUNTIME_NOTE = ("Specs describe the API, not your site. Required fields, allowed values, transitions, screens and "
                "permissions vary by project and account; discover them at runtime, for example with "
                "jira project fields KEY --type TYPE or jira issue transitions KEY.")


def cache_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
    return base / "jira-cli-toolkit" / "api-specs"


def family_for(path: str) -> str:
    if path.startswith(PLATFORM_PREFIXES):
        return "platform"
    if path.startswith(SERVICE_MANAGEMENT_PREFIXES):
        return "service-management"
    return "software"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _index(folder: Path) -> dict:
    try:
        data = json.loads((folder / "index.json").read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (FileNotFoundError, ValueError):
        return {}


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_bytes(data)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _validate(raw: bytes, family: str) -> dict:
    try:
        document = json.loads(raw)
    except ValueError:
        raise ApiError(1, "spec_invalid", f"The {family} spec is not valid JSON; the cached copy was kept.") from None
    if not (isinstance(document, dict) and str(document.get("openapi", "")).startswith("3.")
            and isinstance(document.get("paths"), dict) and isinstance(document.get("info"), dict)):
        raise ApiError(1, "spec_invalid", f"The {family} spec is not an OpenAPI 3 document; the cached copy was kept.")
    return document


def refresh(families=None, folder: Path | None = None, session=None) -> list[dict]:
    """Fetch official specs without credentials, using conditional requests when cached."""
    folder = folder or cache_dir()
    index = _index(folder)
    session = session or requests.Session()
    results = []
    for family in families or SOURCES:
        title, url = SOURCES[family]
        entry = index.get(family, {})
        cached = (folder / f"{family}.json").exists()
        # The CDN sends an ETag only for uncompressed responses, and conditional refresh needs it.
        headers = {"Accept": "application/json", "Accept-Encoding": "identity"}
        if cached and entry.get("etag"):
            headers["If-None-Match"] = entry["etag"]
        try:
            # No auth, no redirects: only the fixed official address is trusted.
            response = session.get(url, headers=headers, timeout=(10, 60), stream=True, allow_redirects=False)
        except requests.RequestException:
            raise ApiError(1, "network_error", f"Could not download the {family} spec from {url}. "
                           + ("The cached copy is unchanged." if cached else "No cached copy exists yet.")) from None
        with response:
            if response.status_code == 304 and cached:
                entry["checked_at"] = _now()
                index[family] = entry
                results.append({"family": family, "status": "unchanged", **_summary(entry)})
                continue
            if response.status_code != 200:
                raise ApiError(1, "spec_unavailable", f"{url} answered HTTP {response.status_code}; "
                               + ("the cached copy is unchanged." if cached else "no cached copy exists yet."))
            raw = bytearray()
            for chunk in response.iter_content(1024 * 1024):
                raw += chunk
                if len(raw) > MAX_SPEC:
                    raise ApiError(1, "spec_invalid", f"The {family} spec exceeds {MAX_SPEC} bytes; the cached copy was kept.")
            document = _validate(bytes(raw), family)
            _atomic_write(folder / f"{family}.json", bytes(raw))
            entry = {"title": title, "url": url, "etag": response.headers.get("ETag"),
                     "last_modified": response.headers.get("Last-Modified"), "fetched_at": _now(), "checked_at": _now(),
                     "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
                     "version": document["info"].get("version"), "paths": len(document["paths"])}
            index[family] = entry
            results.append({"family": family, "status": "updated", **_summary(entry)})
    _atomic_write(folder / "index.json", (json.dumps(index, indent=2) + "\n").encode("utf-8"))
    return results


def _summary(entry: dict) -> dict:
    return {k: entry.get(k) for k in ("title", "url", "version", "paths", "fetched_at", "checked_at", "sha256")}


def _age(entry: dict) -> float | None:
    try:
        checked = datetime.fromisoformat(entry.get("checked_at") or entry["fetched_at"])
    except (KeyError, TypeError, ValueError):
        return None
    return time.time() - checked.timestamp()


def status(folder: Path | None = None) -> list[dict]:
    folder = folder or cache_dir()
    index = _index(folder)
    rows = []
    for family, (title, url) in SOURCES.items():
        entry = index.get(family)
        if not entry or not (folder / f"{family}.json").exists():
            rows.append({"family": family, "title": title, "url": url, "cached": False})
            continue
        age = _age(entry)
        rows.append({"family": family, "cached": True, "stale": age is None or age > STALE_AFTER, **_summary(entry)})
    return rows


def load(family: str, folder: Path | None = None, session=None) -> tuple[dict, dict]:
    """Return (document, cache entry); download once if nothing is cached."""
    folder = folder or cache_dir()
    if not (folder / f"{family}.json").exists() or family not in _index(folder):
        refresh([family], folder, session)
    entry = _index(folder)[family]
    raw = (folder / f"{family}.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != entry.get("sha256"):
        raise ApiError(1, "spec_invalid", f"The cached {family} spec does not match its recorded hash. "
                       "Run: jira api spec refresh")
    return _validate(raw, family), entry


def _segments(path: str) -> list[str]:
    return path.strip("/").split("/")


def match(document: dict, path: str, method: str) -> tuple[str, dict, dict]:
    """Find the operation for a concrete path, preferring literal segments over templates."""
    wanted = _segments(path)
    candidates = []
    for template, item in document["paths"].items():
        parts = _segments(template)
        if len(parts) != len(wanted):
            continue
        params, score = {}, []
        for part, value in zip(parts, wanted):
            name = re.fullmatch(r"\{([^{}]+)\}", part)
            if name:
                params[name.group(1)] = value
                score.append(0)
            elif part == value:
                score.append(1)
            else:
                break
        else:
            candidates.append((score, template, item, params))
    candidates.sort(key=lambda c: c[0], reverse=True)
    for _, template, item, params in candidates:
        if isinstance(item.get(method.lower()), dict):
            return template, item, params
    if candidates:
        methods = sorted({m.upper() for _, _, item, _ in candidates for m, op in item.items() if isinstance(op, dict)})
        raise ApiError(1, "spec_not_found", f"{path} is documented, but not for {method}. Documented methods: "
                       f"{', '.join(methods)}. Pass one with -X.", methods=methods)
    raise ApiError(1, "spec_not_found", f"No documented operation matches {method} {path}. The cached spec may be "
                   "older than the endpoint; run jira api spec refresh. The request itself can still be sent "
                   "with jira api.")


class _Resolver:
    """Inline local #/components references with depth, size and cycle limits."""

    def __init__(self, document: dict):
        self.document, self.nodes = document, 0

    def target(self, ref: str):
        if not ref.startswith("#/"):
            return None
        node = self.document
        for part in ref[2:].split("/"):
            part = part.replace("~1", "/").replace("~0", "~")
            if not isinstance(node, dict) or part not in node:
                return None
            node = node[part]
        return node

    def __call__(self, node, depth=0, seen=()):
        self.nodes += 1
        if isinstance(node, list):
            return [self(item, depth, seen) for item in node]
        if not isinstance(node, dict):
            return node
        ref = node.get("$ref")
        if isinstance(ref, str):
            name = ref.rsplit("/", 1)[-1]
            if ref in seen:
                return {"$ref": ref, "x-note": f"{name} repeats here (recursive); see its first expansion."}
            if depth >= MAX_DEPTH or self.nodes > MAX_NODES:
                return {"$ref": ref, "x-note": f"{name} not expanded to keep the output bounded."}
            target = self.target(ref)
            if target is None:
                # Only references inside the official document are followed; nothing is fetched.
                return {"$ref": ref, "x-note": "Reference outside this document; not followed."}
            return {"x-schema": name, **self(target, depth + 1, seen + (ref,))}
        return {key: self(value, depth, seen) for key, value in node.items()}


def _permissions(description: str) -> str | None:
    found = re.search(r"\*\*\[?Permissions\]?(?:\([^)]*\))? required:?\*\*:?\s*(.+?)(?:\n\n|$)", description or "", re.S)
    return re.sub(r"\s+", " ", found.group(1)).strip() if found else None


def describe(path: str, method: str, folder: Path | None = None, session=None) -> dict:
    family = family_for(path)
    document, entry = load(family, folder, session)
    template, item, params = match(document, path, method)
    operation = item[method.lower()]
    resolve = _Resolver(document)
    parameters = resolve([*item.get("parameters", []), *operation.get("parameters", [])])
    for parameter in parameters:
        if parameter.get("in") == "path" and parameter.get("name") in params:
            parameter["x-value"] = params[parameter["name"]]
    responses = {}
    for code, body in operation.get("responses", {}).items():
        body = resolve(body)
        responses[code] = body if str(code).startswith("2") else {"description": body.get("description")}
    age = _age(entry)
    return {
        "method": method, "path": path, "template": template, "pathParameters": params,
        "operationId": operation.get("operationId"), "summary": operation.get("summary"),
        "deprecated": bool(operation.get("deprecated")), "experimental": bool(operation.get("x-experimental")),
        "permissions": _permissions(operation.get("description", "")),
        "scopes": {"oauth2": operation.get("x-atlassian-oauth2-scopes", []), "connect": operation.get("x-atlassian-connect-scope")},
        "description": operation.get("description"),
        "parameters": parameters,
        "requestBody": resolve(operation["requestBody"]) if "requestBody" in operation else None,
        "responses": responses,
        "source": {"family": family, **_summary(entry), "stale": age is None or age > STALE_AFTER},
        "note": RUNTIME_NOTE,
    }


def _emit(data) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def run(args) -> None:
    """Handle --spec and the spec subcommands. Never resolves a Jira identity."""
    if args.path == "spec":
        action = args.spec_action
        if action == "refresh":
            _emit(refresh())
        elif action in (None, "status"):
            _emit(status())
        else:
            raise invalid(f"Unknown spec action {action!r}; use jira api spec refresh or jira api spec status.")
        return
    if args.spec_action:
        raise invalid(f"Unexpected argument {args.spec_action!r}; pass query values with --query KEY=VALUE.")
    used = [flag for flag, value in (("--query", args.query), ("--header", args.header), ("--data", args.data),
                                      ("--raw-data", args.raw_data), ("--form", args.form), ("--include", args.include),
                                      ("--output", args.output), ("--content-type", args.content_type)) if value]
    if used:
        raise invalid(f"--spec describes an operation and sends nothing; remove {', '.join(used)}.")
    result = describe(validate_path(args.path), args.method.upper())
    if result["source"]["stale"]:
        print("The cached spec is more than 30 days old; run jira api spec refresh for current details.", file=sys.stderr)
    _emit(result)
