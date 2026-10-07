"""Smoke installed entry points in an empty home, without Jira credentials."""
import json
import os
import subprocess
import tempfile


def main():
    with tempfile.TemporaryDirectory() as home:
        env = {key: value for key, value in os.environ.items()
               if not key.startswith(("JIRA_", "JSUP_"))}
        env.update(HOME=home, USERPROFILE=home, XDG_CONFIG_HOME=home)
        for executable in ("jira", "jira-cli-toolkit", "jsup"):
            for args in (["--version"], ["--help"], ["help", "issue", "create"]):
                result = subprocess.run([executable, *args], cwd=home, env=env,
                                        capture_output=True, text=True, timeout=30, check=True)
                assert result.stdout.strip(), (executable, args)
                if args == ["--version"]:
                    from jsup import __version__
                    assert result.stdout.strip() == f"{executable} {__version__}", result.stdout
        result = subprocess.run(["jira", "context", "show", "--json"],
                                cwd=home, env=env, capture_output=True, text=True,
                                timeout=30, check=True)
        data = json.loads(result.stdout)
        assert data["site"] is None and data["project"] is None, data
        for args in (["template", "show", "callback", "--json"], ["update", "--info", "--json"], ["completion", "bash"]):
            subprocess.run(["jira", *args], cwd=home, env=env,
                           capture_output=True, text=True, timeout=30, check=True)
    print("All three installed CLI entry points passed clean-home smoke checks.")


if __name__ == "__main__":
    main()
