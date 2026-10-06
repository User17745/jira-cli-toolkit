"""Entry points for Jira CLI Toolkit and the compatible jsup executable."""
from __future__ import annotations

import sys

import requests

from . import ui
from .application import CommandError, run, show_context
from .client import JiraError
from .commands import build_parser, help_parser


def main(argv=None, *, prog: str = "jsup", default_dashboard: bool = True) -> None:
    parser = build_parser(prog)
    args = parser.parse_args(argv)
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
        ui.err_console.print(str(error), markup=False)
        raise SystemExit(2) from None
    except JiraError as error:
        hint = {401: " (authentication failed; check credentials with user me)",
                403: " (permission denied for this operation)",
                404: " (not found; check the key or ID)"}.get(error.status, "")
        ui.err_console.print(f"Error: {error}{hint}", markup=False)
        raise SystemExit(1) from None
    except requests.RequestException:
        ui.err_console.print("Could not reach Jira. Check the site URL and network connection.")
        raise SystemExit(1) from None
    except OSError as error:
        ui.err_console.print(f"File operation failed: {error}", markup=False)
        raise SystemExit(2) from None
    except (KeyboardInterrupt, EOFError):
        ui.err_console.print("Aborted.")
        raise SystemExit(130) from None


def toolkit_main(argv=None) -> None:
    main(argv, prog="jira-cli-toolkit", default_dashboard=False)


if __name__ == "__main__":
    main(sys.argv[1:])
