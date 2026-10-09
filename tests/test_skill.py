import argparse
import re
import tempfile
import unittest
from pathlib import Path

from jsup import skill
from jsup.commands import build_parser


def subparsers(parser):
    return next((a for a in parser._actions if isinstance(a, argparse._SubParsersAction)), None)


class SkillTests(unittest.TestCase):
    def test_every_command_the_skill_mentions_exists(self):
        parser = build_parser("jira")
        spans = re.findall(r"`(jira [^`]+)`", skill.text())
        self.assertGreater(len(spans), 20)
        for span in spans:
            current, path = parser, []
            for word in span.split()[1:]:
                choices = subparsers(current)
                if choices is None or word.startswith(("-", "<")) or word.isupper():
                    break
                self.assertIn(word, choices.choices, f"{span!r}: unknown command {' '.join(path + [word])}")
                current, path = choices.choices[word], path + [word]
            with self.subTest(span=span):
                self.assertIsNone(subparsers(current), f"{span!r} stops at a command group: {' '.join(path)}")
                flags = {name for action in current._actions for name in action.option_strings}
                for flag in re.findall(r"(?<![\w-])(--?[a-z][\w-]*)", span):
                    self.assertIn(flag, flags, f"{span!r}: {flag} is not an option of jira {' '.join(path)}")

    def test_frontmatter_names_the_skill(self):
        head = skill.text().split("---")[1]
        self.assertIn("name: jira", head)
        self.assertIn("description:", head)

    def test_install_writes_skips_and_refuses_changed_files(self):
        with tempfile.TemporaryDirectory() as folder:
            first = skill.install(folder)
            target = Path(folder, "SKILL.md")
            self.assertEqual((first["status"], target.read_text()), ("written", skill.text()))
            self.assertEqual(skill.install(folder)["status"], "unchanged")
            target.write_text("my edits")
            with self.assertRaisesRegex(ValueError, "--force"):
                skill.install(folder)
            self.assertEqual(target.read_text(), "my edits")
            self.assertEqual(skill.install(folder, force=True)["status"], "written")

    def test_install_refuses_symlinks(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, "elsewhere").write_text("x")
            Path(folder, "SKILL.md").symlink_to(Path(folder, "elsewhere"))
            with self.assertRaisesRegex(ValueError, "symbolic link"):
                skill.install(folder, force=True)


if __name__ == "__main__":
    unittest.main()
