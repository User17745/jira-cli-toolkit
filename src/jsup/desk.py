"""Jira Service Management: service desks, queues and customer requests.

JSON output keeps the Service Management API's own shapes; tables and CSV use flattened rows.
"""
from __future__ import annotations

from rich.panel import Panel

from . import ui
from .client import Jira, identifier

BASE = "/rest/servicedeskapi"
LIST_COMMANDS = {"desk-list", "desk-queues", "desk-queue", "request-list", "request-transitions"}
STATUS_FILTER = {"open": "OPEN_REQUESTS", "closed": "CLOSED_REQUESTS", "all": "ALL_REQUESTS"}


def _pages(j: Jira, path, params=None, limit=50, all_results=False):
    """Collect Service Management pages (start / limit / isLastPage) up to a total limit."""
    values, start, last = [], 0, {}
    for _ in range(1000):
        size = 50 if all_results else min(50, limit - len(values))
        page = j._req("GET", BASE + path, params={**(params or {}), "start": start, "limit": size})
        if not isinstance(page, dict) or not isinstance(page.get("values"), list):
            raise ValueError("Jira returned an unexpected Service Management page.")
        batch = page["values"]
        values.extend(batch if all_results else batch[:size])
        last = page
        start += len(batch)
        if page.get("isLastPage") is not False or not batch or (not all_results and len(values) >= limit):
            break
    return {**last, "values": values, "start": 0, "size": len(values), "fetched": len(values),
            "isLastPage": last.get("isLastPage") is not False and len(values) == start}


def _pick(items, value, label, names):
    """Match an ID exactly, otherwise a unique case-insensitive name from `names`."""
    exact = [i for i in items if str(i.get("id")) == str(value)]
    if exact:
        return exact[0]
    wanted = str(value).casefold()
    matches = [i for i in items if any(str(i.get(n, "")).casefold() == wanted for n in names)]
    if len(matches) == 1:
        return matches[0]
    choices = ", ".join(f"{' / '.join(str(i.get(n)) for n in names if i.get(n))} [id:{i.get('id')}]" for i in items)
    reason = "matches more than one" if matches else "matches none"
    raise ValueError(f"{label} {value!r} {reason}. Available: {choices or 'none'}.")


def _desk(j: Jira, value):
    desks = _pages(j, "/servicedesk", all_results=True)["values"]
    return _pick(desks, value, "Service desk", ("projectKey", "projectName"))


def handle(j: Jira, args, cfg):
    cmd = args.cmd
    paging = dict(limit=args.max, all_results=args.all) if cmd in LIST_COMMANDS - {"request-transitions"} else {}
    if cmd == "desk-list":
        return _pages(j, "/servicedesk", **paging)
    if cmd in ("desk-queues", "desk-queue"):
        desk = _desk(j, args.desk)
        queues = _pages(j, f"/servicedesk/{desk['id']}/queue", {"includeCount": "true"},
                        **(paging if cmd == "desk-queues" else {"all_results": True}))
        if cmd == "desk-queues":
            return queues
        queue = _pick(queues["values"], args.queue, "Queue", ("name",))
        result = _pages(j, f"/servicedesk/{desk['id']}/queue/{queue['id']}/issue", **paging)
        return {**result, "serviceDeskId": str(desk["id"]), "queueId": str(queue["id"]), "queueName": queue.get("name")}
    if cmd == "request-list":
        params = {"requestStatus": STATUS_FILTER[args.status]}
        if args.desk:
            params["serviceDeskId"] = str(_desk(j, args.desk)["id"])
        return _pages(j, "/request", params, **paging)
    key = identifier(args.key)
    if cmd == "request-view":
        return j._req("GET", f"{BASE}/request/{key}", params={"expand": "participant,status,sla"})
    if cmd == "request-transitions":
        return _pages(j, f"/request/{key}/transition", all_results=True)
    if cmd == "request-comment":
        comment = j._req("POST", f"{BASE}/request/{key}/comment", json={"body": args.message, "public": not args.internal})
        return {"request": args.key, "comment_id": comment.get("id"), "public": comment.get("public", not args.internal)}
    if cmd == "request-transition":
        from .fields import choose
        transitions = _pages(j, f"/request/{key}/transition", all_results=True)["values"]
        selected = choose(transitions, args.to, "--to")
        body = {"id": str(selected["id"])}
        if args.message:
            body["additionalComment"] = {"body": args.message}
        j._req("POST", f"{BASE}/request/{key}/transition", json=body)
        return {"moved": args.key, "to": selected["name"], "transition_id": str(selected["id"])}
    raise ValueError(f"Unknown service desk command: {cmd}")


def _status(request):
    return (request.get("currentStatus") or {}).get("status", "")


def rows(data, cmd):
    """Flat rows for tables and CSV."""
    values = data.get("values", [])
    if cmd == "desk-list":
        return [{"id": d.get("id"), "key": d.get("projectKey"), "name": d.get("projectName")} for d in values]
    if cmd == "desk-queues":
        return [{"id": q.get("id"), "name": q.get("name"), "issues": q.get("issueCount", "")} for q in values]
    if cmd == "desk-queue":
        out = []
        for issue in values:
            fields = issue.get("fields") or {}
            out.append({"key": issue.get("key"), "status": (fields.get("status") or {}).get("name", ""),
                        "summary": fields.get("summary", ""),
                        "assignee": (fields.get("assignee") or {}).get("displayName", "-"),
                        "updated": str(fields.get("updated", ""))[:10]})
        return out
    if cmd == "request-list":
        return [{"key": r.get("issueKey"), "status": _status(r), "summary": r.get("summary", ""),
                 "reporter": (r.get("reporter") or {}).get("displayName", ""),
                 "created": ((r.get("createdDate") or {}).get("iso8601") or "")[:10], "desk": r.get("serviceDeskId", "")}
                for r in values]
    if cmd == "request-transitions":
        return [{"id": t.get("id"), "name": t.get("name")} for t in values]
    return []


COLUMNS = {
    "desk-list": ["id", "key", "name"],
    "desk-queues": ["id", "name", "issues"],
    "desk-queue": ["key", "status", "summary", "assignee", "updated"],
    "request-list": ["key", "status", "summary", "reporter", "created", "desk"],
    "request-transitions": ["id", "name"],
}
TITLES = {"desk-list": "Service desks", "desk-queues": "Queues", "request-list": "Requests",
          "request-transitions": "Available transitions"}


def render(data, args) -> None:
    cmd = args.cmd
    if args.csv:
        ui.csv_data(rows(data, cmd), args.columns or ",".join(COLUMNS[cmd]))
        return
    if args.json:
        ui.dump_json(data)
        return
    if cmd == "request-transitions" and not data.get("values"):
        ui.console.print("No transitions are available to you on this request.", markup=False)
        return
    if cmd in COLUMNS:
        title = TITLES.get(cmd) or f"Queue {data.get('queueName')}"
        if cmd != "request-transitions":
            title += f" ({data.get('fetched', 0)} fetched{'' if data.get('isLastPage', True) else ' · more available'})"
        ui.simple_table(title, rows(data, cmd), args.columns.split(",") if args.columns else COLUMNS[cmd])
        return
    if cmd == "request-view":
        lines = [f"[bold]{data.get('issueKey')}[/]: {data.get('summary', '')}",
                 f"status={_status(data)}  desk={data.get('serviceDeskId', '')}  "
                 f"reporter={(data.get('reporter') or {}).get('displayName', '-')}  "
                 f"created={((data.get('createdDate') or {}).get('friendly') or '')}"]
        participants = [p.get("displayName", "") for p in (data.get("participants") or {}).get("values", [])]
        if participants:
            lines.append("participants=" + ", ".join(participants))
        for sla in (data.get("sla") or {}).get("values", []):
            cycle = sla.get("ongoingCycle") or {}
            remaining = (cycle.get("remainingTime") or {}).get("friendly")
            state = "breached" if cycle.get("breached") else (f"{remaining} left" if remaining else "completed")
            lines.append(f"SLA {sla.get('name')}: {state}")
        for field in data.get("requestFieldValues", []):
            value = field.get("value")
            text = value if isinstance(value, str) else (value or {}).get("name") if isinstance(value, dict) else None
            if text:
                lines.append(f"\n{field.get('label')}:\n{text[:1500]}")
        ui.console.print(Panel("\n".join(lines), title="Request"))
        return
    if cmd == "request-comment":
        kind = "customer-visible" if data.get("public") else "internal"
        ui.console.print(f"Added a {kind} comment to {data['request']} (id {data.get('comment_id')})", markup=False)
        return
    if cmd == "request-transition":
        ui.console.print(f"Moved {data['moved']} → {data['to']}", markup=False)
