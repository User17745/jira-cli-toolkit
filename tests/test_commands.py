import contextlib
import io
import unittest

from jsup.commands import build_parser


class CommandTests(unittest.TestCase):
    def test_global_flags_survive_each_nesting_level(self):
        paths = [
            ["--project", "ENG", "--json", "issue", "view", "ENG-1"],
            ["issue", "--project", "ENG", "--json", "view", "ENG-1"],
            ["issue", "view", "ENG-1", "--project", "ENG", "--json"],
            ["--project", "ENG", "issue", "comment", "--json", "list", "ENG-1"],
            ["issue", "--json", "comment", "list", "ENG-1", "--project", "ENG"],
            ["--project", "ENG", "--json", "open"],
        ]
        for argv in paths:
            with self.subTest(argv=argv):
                args = build_parser().parse_args(argv)
                self.assertEqual(args.project, "ENG")
                self.assertTrue(args.json)

    def test_credential_flags_and_no_input_survive_subcommands(self):
        args = build_parser().parse_args([
            "--site", "https://example.invalid", "--email", "tester", "--token", "secret",
            "--no-input", "issue", "comment", "list", "ENG-1",
        ])
        self.assertEqual((args.site, args.email, args.token),
                         ("https://example.invalid", "tester", "secret"))
        self.assertTrue(args.no_input)

    def test_last_explicit_global_flag_wins(self):
        args = build_parser().parse_args([
            "-p", "OLD", "issue", "-p", "MID", "view", "ENG-1", "-p", "NEW",
        ])
        self.assertEqual(args.project, "NEW")

    def test_grouped_and_legacy_spellings_select_same_operation(self):
        pairs = [
            (["me"], ["user", "me"]),
            (["project-list"], ["project", "list"]),
            (["project-show", "ENG"], ["project", "view", "ENG"]),
            (["issue-create", "-s", "Example"], ["issue", "create", "-s", "Example"]),
            (["issue-show", "ENG-1"], ["issue", "view", "ENG-1"]),
            (["issue-move", "ENG-1", "--to", "Done"], ["issue", "transition", "ENG-1", "--to", "Done"]),
            (["transitions", "ENG-1"], ["issue", "transitions", "ENG-1"]),
            (["issue-delete", "ENG-1", "--yes"], ["issue", "delete", "ENG-1", "--yes"]),
            (["comment-add", "ENG-1", "-m", "Example"], ["issue", "comment", "add", "ENG-1", "-m", "Example"]),
            (["comment-list", "ENG-1"], ["issue", "comment", "list", "ENG-1"]),
            (["board-list"], ["board", "list"]),
            (["board-create", "--name", "Example"], ["board", "create", "--name", "Example"]),
            (["board-issues", "12"], ["board", "issues", "12"]),
            (["board-feature", "12", "--feature", "reports", "--enable"],
             ["board", "feature", "enable", "12", "--feature", "reports"]),
            (["sprint-list", "--board", "12"], ["sprint", "list", "--board", "12"]),
            (["sprint-create", "--board", "12", "--name", "Example"],
             ["sprint", "create", "--board", "12", "--name", "Example"]),
            (["sprint-state", "4", "active"], ["sprint", "start", "4"]),
            (["sprint-state", "4", "closed"], ["sprint", "close", "4"]),
            (["sprint-state", "4", "future"], ["sprint", "edit", "4", "--state", "future"]),
            (["sprint-add", "4", "ENG-1"], ["sprint", "add-issues", "4", "ENG-1"]),
            (["component-list"], ["component", "list"]),
            (["component-create", "--name", "Example"], ["component", "create", "--name", "Example"]),
        ]
        parser = build_parser()
        for legacy, grouped in pairs:
            with self.subTest(legacy=legacy):
                left, right = parser.parse_args(legacy), parser.parse_args(grouped)
                self.assertEqual(left.cmd, right.cmd)
                self.assertTrue(left.legacy)
                self.assertFalse(right.legacy)
                for name in ("key", "summary", "message", "board_id", "state", "enable", "keys"):
                    if hasattr(left, name):
                        self.assertEqual(getattr(left, name), getattr(right, name))

    def test_invalid_limits_and_ids_are_rejected(self):
        for argv in (["issue", "list", "--limit", "0"], ["board", "view", "-1"],
                     ["sprint", "start", "0"]):
            with self.subTest(argv=argv), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    build_parser().parse_args(argv)
                self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
