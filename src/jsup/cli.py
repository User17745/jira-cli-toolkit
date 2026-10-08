"""Entry points for Jira CLI Toolkit and the compatible jsup executable."""
from __future__ import annotations

import json
import sys

import requests

from . import ui
from .api import ApiError, secret_values
from .application import CommandError, run, show_context
from .client import JiraError, UncertainOutcome
from .commands import build_parser, help_parser


def main(argv=None, *, prog: str = "jsup", default_dashboard: bool = True) -> None:
    raw = sys.argv[1:] if argv is None else argv
    if raw and raw[0] == "--_complete":
        from .completion import candidates
        print("\n".join(candidates(raw[1:], prog)))
        return
    if raw and raw[0] == "--_apply-update":
        from .update import apply_windows_update
        apply_windows_update(raw[1:])
        return
    if prog in {"jsup", "jira-cli-toolkit"}:
        ui.err_console.print(
            f"Warning: the tool has moved to the 'jira' command. '{prog}' is running "
            "under legacy support (supported throughout v2.x) and may be deprecated "
            "in a future major release. Update your commands to use 'jira'.",
            style="yellow", markup=False,
        )
    parser = build_parser(prog)
    args = parser.parse_args(argv)
    def fail(code, kind, message, **details):
        # Server errors can echo submitted credentials. Never print them.
        from .config import resolve_config
        secrets = secret_values(getattr(args, "email", None), getattr(args, "token", None))
        # Spec discovery never resolves an identity, not even to redact an error.
        discovery = args.cmd == "api" and (getattr(args, "spec", False) or getattr(args, "path", None) == "spec")
        try:
            if not discovery:
                cfg = resolve_config(args)
                secrets += secret_values(cfg.get("email"), cfg.get("token"))
        except (ValueError, OSError):
            pass

        def redact(text):
            for secret in secrets:
                text = text.replace(secret, "[redacted]")
            return text
        message = redact(message)
        if args.cmd == "api":
            # stdout carries only response bodies, so api errors always go to stderr as JSON.
            payload = json.dumps({"error": {"code": kind, "message": message, **details}}, indent=2, ensure_ascii=False)
            print(redact(payload), file=sys.stderr)
        elif args.json and not args.legacy and prog != "jsup":
            ui.dump_json({"error": {"code": kind, "message": message, **details}})
        else:
            ui.err_console.print(message, markup=False)
        raise SystemExit(code) from None
    if args.cmd == "help":
        help_parser(parser, args.path).print_help()
        return
    try:
        if not args.cmd:
            if args.command:
                args.selected_parser.print_help()
                return
            if not default_dashboard:
                show_context(args, prog, include_help=True)
                return
            args.cmd, args.projects = "dashboard", None
        run(args, prog)
    except ApiError as error:
        fail(error.exit_code, error.code, str(error), **error.details)
    except (CommandError, ValueError) as error:
        fail(2, "invalid_input", str(error))
    except JiraError as error:
        hint = {401: " (authentication failed; replace the token with auth login, or migrate legacy credentials with config migrate)",
                403: " (permission denied for this operation)",
                404: " (not found; check the key or ID)"}.get(error.status, "")
        fail(1, "jira_error", f"Error: {error}{hint}", status=error.status)
    except UncertainOutcome as error:
        fail(1, "uncertain_outcome", str(error))
    except requests.RequestException:
        fail(1, "network_error", "Could not reach Jira. Check the site URL and network connection.")
    except OSError as error:
        fail(2, "file_error", f"File operation failed: {error}")
    except (KeyboardInterrupt, EOFError):
        fail(130, "aborted", "Aborted.")


def toolkit_main(argv=None) -> None:
    main(argv, prog="jira-cli-toolkit", default_dashboard=False)


def jira_main(argv=None) -> None:
    main(argv, prog="jira", default_dashboard=False)


if __name__ == "__main__":
    main(sys.argv[1:])
