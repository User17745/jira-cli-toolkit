"""`jira api`: authenticated requests to any Jira Cloud REST path, without a token in the command.

The selected identity, trusted site and scoped-token gateway come from the existing
resolver. Callers choose the method, path, query, headers and body; the CLI keeps control
of the destination, authentication, content framing and transport.
"""
from __future__ import annotations

import base64
import json
import os
import re
import sys
import tempfile
from contextlib import ExitStack
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote, urlsplit

from .client import Jira

METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS")
# Methods retried after transient failures. A POST is never retried, even for searches.
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
BODYLESS_METHODS = {"GET", "HEAD", "OPTIONS"}
MAX_DATA = 10 * 1024 * 1024
MAX_UPLOAD = 50 * 1024 * 1024
MAX_RESPONSE = 250 * 1024 * 1024
MAX_ERROR_BODY = 64 * 1024
# The CLI owns authentication, destination, framing and transport.
RESERVED_HEADERS = {
    "authorization", "proxy-authorization", "cookie", "host", "content-length", "content-type",
    "transfer-encoding", "connection", "keep-alive", "te", "trailer", "upgrade", "expect",
    "forwarded", "via",
}
RESERVED_PREFIXES = ("proxy-", "x-forwarded-", "sec-")
HEADER_NAME = re.compile(r"^[!#$%&'*+.^_`|~0-9A-Za-z-]+$")
TEXT_TYPES = re.compile(r"^(text/|application/([\w.+-]*\+)?(json|xml|javascript|x-www-form-urlencoded)\b)", re.I)


class ApiError(Exception):
    """A failed request, reported as a redacted JSON object on stderr."""

    def __init__(self, exit_code: int, code: str, message: str, **details):
        super().__init__(message)
        self.exit_code, self.code, self.details = exit_code, code, details


def invalid(message: str) -> ApiError:
    return ApiError(2, "invalid_input", message)


@dataclass
class Request:
    method: str
    path: str
    params: list[tuple[str, str]] = field(default_factory=list)
    headers: dict[str, str] = field(default_factory=dict)
    body: bytes | None = None
    content_type: str | None = None
    form: list[tuple[str, str | None, Path | None]] = field(default_factory=list)


def validate_path(path: str) -> str:
    if path == "spec" or not path.startswith("/"):
        raise invalid("PATH must be a Jira REST path such as /rest/api/3/myself. "
                      "Use jira api spec refresh or jira api spec status for discovery.")
    if any(ord(ch) < 0x21 or ord(ch) > 0x7E for ch in path):
        raise invalid("PATH must be printable ASCII without spaces; percent-encode other characters.")
    if "?" in path or "#" in path:
        raise invalid("PATH must not contain a query or fragment; pass query values with --query KEY=VALUE.")
    if "\\" in path or "//" in path:
        raise invalid("PATH must not contain backslashes or empty segments.")
    if not path.startswith("/rest/"):
        raise invalid("PATH must start with /rest/, for example /rest/api/3/myself or /rest/agile/1.0/board.")
    if re.search(r"%(?![0-9A-Fa-f]{2})", path):
        raise invalid("PATH contains an invalid percent-encoding.")
    # Encoded separators and dot segments could address a different resource than the one shown.
    if re.search(r"%(2[fF]|5[cC])", path):
        raise invalid("PATH must not contain encoded slashes or backslashes.")
    segments = re.sub(r"%2[eE]", ".", path).split("/")
    if any(segment in (".", "..") for segment in segments):
        raise invalid("PATH must not contain . or .. segments.")
    return path


def parse_query(values: list[str]) -> list[tuple[str, str]]:
    params = []
    for item in values:
        key, sep, value = item.partition("=")
        if not sep or not key:
            raise invalid(f"--query expects KEY=VALUE, got {item!r}.")
        params.append((key, value))
    return params


def parse_headers(values: list[str]) -> dict[str, str]:
    headers: dict[str, str] = {}
    for item in values:
        name, sep, value = item.partition(":")
        name, value = name.strip(), value.strip()
        if not sep or not HEADER_NAME.match(name):
            raise invalid(f"--header expects 'Name: value', got {item!r}.")
        if any(ch in value for ch in "\r\n\0"):
            raise invalid(f"Header {name} contains a line break or NUL character.")
        lower = name.lower()
        if lower in RESERVED_HEADERS or lower.startswith(RESERVED_PREFIXES):
            hint = " Use --content-type." if lower == "content-type" else ""
            raise invalid(f"Header {name} is managed by the CLI and cannot be set.{hint}")
        headers[name] = value
    return headers


class _Inputs:
    """Reads @file and @- sources with size limits; stdin may be consumed only once."""

    def __init__(self, stdin=None):
        self.stdin = stdin if stdin is not None else sys.stdin.buffer
        self.used_stdin = False

    def read(self, value: str, option: str, limit: int) -> bytes:
        if value == "@-":
            if self.used_stdin:
                raise invalid("Only one option can read from stdin (@-).")
            self.used_stdin = True
            data = self.stdin.read(limit + 1)
        elif value.startswith("@"):
            path = Path(value[1:])
            if not path.is_file():
                raise invalid(f"{option}: file not found: {path}")
            if path.stat().st_size > limit:
                raise invalid(f"{option}: {path} is larger than {limit} bytes.")
            data = path.read_bytes()
        else:
            data = value.encode("utf-8")
        if len(data) > limit:
            raise invalid(f"{option} is larger than {limit} bytes.")
        return data


def build_request(args, stdin=None) -> Request:
    method = args.method.upper()
    request = Request(method=method, path=validate_path(args.path),
                      params=parse_query(args.query), headers=parse_headers(args.header))
    bodies = [name for name, value in (("--data", args.data), ("--raw-data", args.raw_data), ("--form", args.form)) if value]
    if len(bodies) > 1:
        raise invalid(f"Choose one body option; got {' and '.join(bodies)}.")
    # A body never silently changes the method.
    if bodies and method in BODYLESS_METHODS:
        raise invalid(f"{bodies[0]} needs an explicit method that accepts a body, such as -X POST.")
    if args.content_type and not (args.data or args.raw_data):
        raise invalid("--content-type applies only to --data or --raw-data.")
    if args.content_type and any(ch in args.content_type for ch in "\r\n\0"):
        raise invalid("--content-type contains a line break or NUL character.")
    inputs = _Inputs(stdin)
    if args.data:
        body = inputs.read(args.data, "--data", MAX_DATA)
        try:
            json.loads(body)
        except (ValueError, UnicodeDecodeError):
            raise invalid("--data must be valid JSON; use --raw-data with --content-type for other formats.") from None
        # Send the caller's bytes unchanged so no endpoint field is added, reordered or dropped.
        request.body, request.content_type = body, args.content_type or "application/json"
    elif args.raw_data:
        if not args.content_type:
            raise invalid("--raw-data needs --content-type.")
        request.body = inputs.read(args.raw_data, "--raw-data", MAX_DATA)
        request.content_type = args.content_type
    total = 0
    for item in args.form:
        name, sep, value = item.partition("=")
        if not sep or not name:
            raise invalid(f"--form expects NAME=VALUE or NAME=@FILE, got {item!r}.")
        if value.startswith("@"):
            path = Path(value[1:])
            if value == "@-" or not path.is_file():
                raise invalid(f"--form {name}: expected an existing file, got {value!r}.")
            total += path.stat().st_size
            if total > MAX_UPLOAD:
                raise invalid(f"Uploads are limited to {MAX_UPLOAD} bytes per request.")
            request.form.append((name, None, path))
        else:
            request.form.append((name, value, None))
    return request


def secret_values(email, token) -> list[str]:
    """The token and every form derived from it that could appear in output."""
    if not token:
        return []
    values = [token, quote(token, safe="")]
    if email:
        basic = base64.b64encode(f"{email}:{token}".encode()).decode()
        values += [basic, basic.rstrip("=")]
    return sorted({v for v in values if v}, key=len, reverse=True)


def _redactor(cfg: dict):
    secrets = secret_values(cfg.get("email"), cfg.get("token"))

    def redact(text: str) -> str:
        for secret in secrets:
            text = text.replace(secret, "[redacted]")
        return text
    return redact


def _read(response, limit: int) -> tuple[bytes, bool]:
    """Read at most limit bytes; report whether more remained."""
    data = bytearray()
    for chunk in response.iter_content(64 * 1024):
        data += chunk
        if len(data) > limit:
            return bytes(data[:limit]), True
    return bytes(data), False


def _error_body(response, redact):
    raw, _ = _read(response, MAX_ERROR_BODY)
    text = redact(raw.decode(response.encoding or "utf-8", errors="replace"))
    try:
        return json.loads(text)
    except ValueError:
        return text


def check_output(destination: str) -> Path:
    output = Path(destination)
    if output.exists():
        raise invalid(f"Destination already exists: {output}")
    if not output.parent.is_dir():
        raise invalid(f"Destination folder does not exist: {output.parent}")
    return output


def _write_file(response, destination: str) -> int:
    # Checked again here in case the destination appeared during the request.
    output = check_output(destination)
    fd, temporary = tempfile.mkstemp(prefix=".jira-api-", dir=output.parent)
    received = 0
    try:
        with os.fdopen(fd, "wb") as stream:
            for chunk in response.iter_content(1024 * 1024):
                received += len(chunk)
                if received > MAX_RESPONSE:
                    raise ApiError(1, "response_too_large", f"Response exceeds {MAX_RESPONSE} bytes; nothing was saved.")
                stream.write(chunk)
        # Hard-link creation fails atomically if the destination appeared meanwhile.
        os.link(temporary, output)
    finally:
        os.unlink(temporary)
    return received


def _write_stdout(response, stdout) -> None:
    content_type = response.headers.get("Content-Type", "")
    terminal = getattr(stdout, "isatty", lambda: False)()
    if terminal and content_type and not TEXT_TYPES.match(content_type):
        length = response.headers.get("Content-Length", "unknown")
        print(f"Binary response ({content_type}, {length} bytes) not printed to the terminal; rerun with --output FILE.",
              file=sys.stderr)
        return
    buffer = stdout.buffer if hasattr(stdout, "buffer") else stdout
    if terminal and "json" in content_type.lower():
        # Humans get indented JSON; pipes always get the upstream bytes.
        body, truncated = _read(response, MAX_RESPONSE)
        if truncated:
            raise ApiError(1, "response_too_large", f"Response exceeds {MAX_RESPONSE} bytes.")
        try:
            body = (json.dumps(json.loads(body), indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        except ValueError:
            pass
        buffer.write(body)
        buffer.flush()
        return
    received = 0
    for chunk in response.iter_content(64 * 1024):
        received += len(chunk)
        if received > MAX_RESPONSE:
            raise ApiError(1, "response_too_large", f"Response exceeds {MAX_RESPONSE} bytes; output is incomplete.")
        buffer.write(chunk)
    buffer.flush()


def _print_metadata(response, redact) -> None:
    print(f"HTTP {response.status_code} {response.reason or ''}".rstrip(), file=sys.stderr)
    for name, value in response.headers.items():
        # Session cookies from the gateway are credentials too.
        shown = "[redacted]" if name.lower() == "set-cookie" else redact(value)
        print(f"{name}: {shown}", file=sys.stderr)
    print(file=sys.stderr)


def execute(jira: Jira, request: Request, args, cfg: dict, stdout=None) -> None:
    stdout = stdout or sys.stdout
    redact = _redactor(cfg)
    headers = dict(request.headers)
    headers.setdefault("Accept", "application/json")
    kw = dict(params=request.params, headers=headers, stream=True)
    with ExitStack() as stack:
        if request.form:
            # requests writes the multipart boundary itself.
            headers["Content-Type"] = None
            kw["files"] = [(name, (path.name, stack.enter_context(path.open("rb")), "application/octet-stream")) if path
                           else (name, (None, value)) for name, value, path in request.form]
        elif request.body is not None:
            headers["Content-Type"] = request.content_type
            kw["data"] = request.body
        else:
            headers["Content-Type"] = None
        response = jira._send(request.method, request.path, safe=request.method in SAFE_METHODS, **kw)
    with response:
        # The prepared URL must still point at the trusted base after encoding.
        sent, base = urlsplit(response.request.url if response.request else jira.site + request.path), urlsplit(jira.site)
        if (sent.scheme, sent.netloc) != (base.scheme, base.netloc):
            raise ApiError(2, "invalid_input", "The request did not resolve to the selected Jira site.")
        if args.include:
            _print_metadata(response, redact)
        status = response.status_code
        if 300 <= status < 400:
            # Signed download URLs carry access tokens in the query, so only the address is shown.
            target = urlsplit(response.headers.get("Location", ""))
            raise ApiError(1, "jira_error", "Jira answered with a redirect, which is not followed so credentials stay "
                           "on the selected site. For endpoints that support it, such as attachment content, "
                           "pass --query redirect=false.", status=status, method=request.method, path=request.path,
                           location=redact(f"{target.scheme}://{target.netloc}{target.path}" if target.netloc else target.path))
        if status >= 400:
            raise ApiError(1, "jira_error", f"{request.method} {request.path} -> {status}", status=status,
                           method=request.method, path=request.path, body=_error_body(response, redact))
        if request.method == "HEAD" or status == 204:
            return
        if args.output:
            received = _write_file(response, args.output)
            print(f"Saved {received} bytes to {Path(args.output).absolute()}", file=sys.stderr)
        else:
            _write_stdout(response, stdout)


def run(args, cfg: dict) -> None:
    if args.csv or args.columns:
        raise invalid("--csv and --columns do not apply to api; the response is written as Jira returns it.")
    request = build_request(args)
    if args.output:
        # Fail before sending, so nothing is downloaded or changed for an unusable destination.
        check_output(args.output)
    if not (cfg["site"] and cfg["email"] and cfg["token"]):
        raise invalid("No Jira identity is configured. Run: jira auth login")
    jira = Jira(cfg.get("api_site", cfg["site"]), cfg["email"], cfg["token"])
    try:
        execute(jira, request, args, cfg)
    finally:
        jira.close()
