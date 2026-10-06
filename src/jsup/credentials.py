"""Credential storage with no implicit plaintext fallback."""
from __future__ import annotations

import json
from pathlib import Path

SERVICE = "jira-cli-toolkit"


class CredentialError(ValueError):
    pass


def _keyring():
    try:
        import keyring
        backend = keyring.get_keyring()
        module = type(backend).__module__
        # Accept only native OS stores; chained/plaintext third-party stores
        # are not an implicit downgrade from secure storage.
        trusted={"keyring.backends.macOS", "keyring.backends.Windows",
                 "keyring.backends.SecretService", "keyring.backends.kwallet"}
        if module in trusted:
            return backend
        for candidate in getattr(backend, "backends", []):
            if type(candidate).__module__ in trusted and candidate.priority > 0:
                return candidate
        raise CredentialError("No native credential store available. Use JIRA_API_TOKEN for headless use, or explicitly choose --storage file.")
    except ImportError:
        raise CredentialError("Credential-store support is missing; reinstall the package or use environment authentication.") from None


def get(profile, settings, config_path):
    storage = settings.get("storage", "keyring")
    if storage == "keyring":
        try:
            return _keyring().get_password(SERVICE, settings["credential_id"]) or ""
        except CredentialError:
            raise
        except Exception:
            raise CredentialError("Could not read the OS credential store. Unlock it or use environment authentication.") from None
    path = Path(config_path).with_name("credentials.json")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise CredentialError("Invalid credential file.")
        return data.get(settings["credential_id"], "")
    except FileNotFoundError:
        return ""
    except json.JSONDecodeError:
        raise CredentialError("Invalid credential file.") from None


def put(settings, token, config_path):
    if settings["storage"] == "keyring":
        try:
            _keyring().set_password(SERVICE, settings["credential_id"], token)
            return
        except CredentialError:
            raise
        except Exception:
            raise CredentialError("Could not save to the OS credential store. No plaintext fallback was written.") from None
    import os
    if os.name == "nt":
        raise CredentialError("File storage on Windows is unsupported until ACL protection is implemented; use the Windows credential store or environment variables.")
    from .config import atomic_json
    path = Path(config_path).with_name("credentials.json")
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    data[settings["credential_id"]] = token
    atomic_json(path, data)


def delete(settings, config_path):
    if settings["storage"] == "keyring":
        try:
            _keyring().delete_password(SERVICE, settings["credential_id"])
        except Exception:
            raise CredentialError("Could not remove the OS credential. Unlock the store and retry logout.") from None
    else:
        from .config import atomic_json
        path = Path(config_path).with_name("credentials.json")
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            data.pop(settings["credential_id"], None)
            atomic_json(path, data)
