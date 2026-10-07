import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("command_tree", ROOT / "scripts" / "command_tree.py")
command_tree = importlib.util.module_from_spec(spec)
spec.loader.exec_module(command_tree)


class WebsiteCommandTreeTests(unittest.TestCase):
    def test_website_command_data_matches_parser(self):
        published = json.loads((ROOT / "web" / "src" / "data" / "commands.json").read_text(encoding="utf-8"))
        self.assertEqual(published, command_tree.tree(),
                         "Regenerate: python scripts/command_tree.py > web/src/data/commands.json")

    def test_tree_has_grouped_commands_without_root_legacy_aliases(self):
        names = [c["name"] for c in command_tree.tree()["commands"]]
        self.assertIn("issue", names)
        self.assertNotIn("issue-show", names)
        issue = next(c for c in command_tree.tree()["commands"] if c["name"] == "issue")
        self.assertIn("transitions", [c["name"] for c in issue["commands"]])


if __name__ == "__main__":
    unittest.main()
