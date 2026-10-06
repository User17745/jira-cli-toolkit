"""Entry points for Jira CLI Toolkit and the compatible jsup executable."""
from __future__ import annotations

import sys

import requests

from . import ui
from .application import CommandError, run, show_context
from .client import JiraError, UncertainOutcome
from .commands import build_parser, help_parser


def main(argv=None, *, prog: str = "jsup", default_dashboard: bool = True) -> None:
    parser = build_parser(prog)
    args = parser.parse_args(argv)
    def fail(code, kind, message, **details):
        # Server errors can echo submitted credentials. Never print them.
        from .config import resolve_config
        secrets = [getattr(args, "token", None)]
        try:
            secrets.append(resolve_config(args).get("token"))
        except (ValueError, OSError):
            pass
        for secret in secrets:
            if secret:
                message = message.replace(secret, "[redacted]")
        if args.json and not args.legacy and prog != "jsup":
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
    except CommandError as error:
        fail(2, "invalid_input", str(error))
    except JiraError as error:
        hint = {401: " (authentication failed; check credentials with user me)",
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


if __name__ == "__main__":
    main(sys.argv[1:])
