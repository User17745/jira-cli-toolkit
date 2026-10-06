"""Rich terminal UI: tables, panels, pickers. Plain output when piped."""
from __future__ import annotations

import json
import sys
import csv

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .client import adf_to_text

console = Console()
err_console = Console(stderr=True)

STATUS_STYLE = {"new": "cyan", "indeterminate": "yellow", "done": "green"}


def status_text(status: dict) -> Text:
    name = (status or {}).get("name", "?")
    cat = ((status or {}).get("statusCategory") or {}).get("key", "")
    return Text(name, style=STATUS_STYLE.get(cat, ""))


def emit(data, render) -> None:
    """JSON to stdout for scripts is handled by callers; this is human output."""
    render(data)


def dump_json(data) -> None:
    print(json.dumps(data, indent=2))


def list_rows(data):
    items = data if isinstance(data, list) else next((data[k] for k in ("issues", "values", "comments", "projects") if isinstance(data.get(k), list)), [])
    rows = []
    for item in items:
        if not isinstance(item, dict):
            rows.append({"value": str(item)})
            continue
        row = {**item, **item.get("fields", {})}
        row.pop("fields", None)
        for key, value in row.items():
            if isinstance(value, dict):
                row[key] = value.get("displayName", value.get("name", value.get("value", json.dumps(value))))
            elif isinstance(value, list):
                row[key] = json.dumps(value, ensure_ascii=False)
        rows.append(row)
    return rows


def csv_data(data, columns=None):
    rows = list_rows(data)
    names = columns.split(",") if columns else list(dict.fromkeys(k for row in rows for k in row))
    writer = csv.DictWriter(sys.stdout, fieldnames=names, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)


def issues_table(data, title="Issues", columns=None) -> None:
    issues = data.get("issues", [])
    if columns:
        simple_table(f"{title} ({len(issues)} fetched)", list_rows(data), columns.split(","))
        return
    remaining = " · more available" if data.get("isLast") is False or data.get("nextPageToken") else ""
    total = f", total={data['total']}" if "total" in data else ""
    t = Table(title=f"{title} ({len(issues)} fetched{total}{remaining})",
              show_lines=False)
    t.add_column("Key", style="bold", no_wrap=True)
    t.add_column("Status")
    t.add_column("Summary")
    t.add_column("Assignee")
    t.add_column("Updated", no_wrap=True)
    for i in issues:
        f = i.get("fields", {})
        t.add_row(
            i.get("key", "?"),
            status_text(f.get("status", {})),
            (f.get("summary") or "")[:90],
            (f.get("assignee") or {}).get("displayName", "-") if f.get("assignee") else "-",
            str(f.get("updated", ""))[:10],
        )
    console.print(t)


def issue_panel(d) -> None:
    f = d.get("fields", {})
    desc = adf_to_text(f.get("description"))
    body = (
        f"[bold]{d.get('key')}[/]: {f.get('summary', '')}\n"
        f"status={(f.get('status') or {}).get('name')}  "
        f"type={(f.get('issuetype') or {}).get('name')}  "
        f"priority={(f.get('priority') or {}).get('name')}\n"
        f"assignee={((f.get('assignee') or {}).get('displayName')) or '-'}  "
        f"labels={', '.join(f.get('labels', [])) or '-'}  "
        f"components={', '.join(c.get('name','') for c in f.get('components', [])) or '-'}"
    )
    if desc:
        body += f"\n\n{desc[:1500]}"
    n_comments = (d.get("fields", {}).get("comment") or {}).get("total", "?")
    console.print(Panel(body, title="Issue", subtitle=f"comments: {n_comments}"))


def comments_table(d) -> None:
    t = Table(title="Comments", show_lines=True)
    t.add_column("ID", no_wrap=True)
    t.add_column("Author")
    t.add_column("Body")
    for c in d.get("comments", []):
        t.add_row(str(c.get("id")),
                  (c.get("author") or {}).get("displayName", "?"),
                  adf_to_text(c.get("body"))[:400])
    console.print(t)


def boards_table(d) -> None:
    t = Table(title="Boards")
    t.add_column("ID", no_wrap=True)
    t.add_column("Type")
    t.add_column("Name")
    for b in d.get("values", []):
        t.add_row(str(b["id"]), b.get("type", ""), b.get("name", ""))
    console.print(t)


def sprints_table(d) -> None:
    t = Table(title="Sprints")
    t.add_column("ID", no_wrap=True)
    t.add_column("State")
    t.add_column("Name")
    t.add_column("Goal")
    for s in d.get("values", []):
        state = s.get("state", "")
        style = {"active": "green", "future": "cyan", "closed": "dim"}.get(state, "")
        t.add_row(str(s["id"]), f"[{style}]{state}[/]" if style else state,
                  s.get("name", ""), (s.get("goal") or "")[:60])
    console.print(t)


def simple_table(title, rows, cols) -> None:
    t = Table(title=title)
    for c in cols:
        t.add_column(c)
    for r in rows:
        t.add_row(*[str(r.get(c, "")) for c in cols])
    console.print(t)


def pick(prompt_text: str, options: list[str]) -> int:
    """Numbered picker; returns chosen index. Aborts cleanly on Ctrl-C/empty."""
    for n, label in enumerate(options, 1):
        console.print(f"  [bold]{n}[/]. {label}")
    try:
        raw = input(f"{prompt_text} [1-{len(options)}]: ").strip()
    except (KeyboardInterrupt, EOFError):
        err_console.print("\nAborted.")
        sys.exit(130)
    if not raw.isdigit() or not 1 <= int(raw) <= len(options):
        err_console.print("Aborted: pick a number from the list.")
        sys.exit(2)
    return int(raw) - 1


def confirm(prompt_text: str) -> bool:
    try:
        return input(f"{prompt_text} [y/N]: ").strip().lower() in ("y", "yes")
    except (KeyboardInterrupt, EOFError):
        return False
