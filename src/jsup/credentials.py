"""Credential storage with no implicit plaintext fallback."""
from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from threading import RLock

SERVICE = "jira-cli-toolkit"
_STORE_LOCK = RLock()


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


@contextmanager
def _store(allow_ui):
    """Keep OS unlock dialogs out of scripted commands.

    keyring 25 targets the macOS file-based Keychain, whose process-wide
    interaction flag must be restored even if an operation fails.
    """
    backend = _keyring()
    module = type(backend).__module__
    if allow_ui or module == "keyring.backends.Windows":
        yield backend
        return
    if module == "keyring.backends.macOS":
        import ctypes
        from keyring.backends.macOS import api
        get_ui = api._sec.SecKeychainGetUserInteractionAllowed
        set_ui = api._sec.SecKeychainSetUserInteractionAllowed
        get_ui.argtypes = [ctypes.POINTER(ctypes.c_ubyte)]
        set_ui.argtypes = [ctypes.c_ubyte]
        get_ui.restype = set_ui.restype = ctypes.c_int32
        with _STORE_LOCK:
            previous = ctypes.c_ubyte()
            api.Error.raise_for_status(get_ui(ctypes.byref(previous)))
            api.Error.raise_for_status(set_ui(False))
            try:
                yield backend
            finally:
                api.Error.raise_for_status(set_ui(previous.value))
        return
    # Linux backends can create/unlock a wallet through an unbounded D-Bus
    # prompt. Scripted use must choose an explicit noninteractive source.
    raise CredentialError("This OS store can request an unlock dialog. Use environment authentication or explicitly choose --storage file for headless use; run auth login in a terminal for native storage.")


def get(profile, settings, config_path, *, allow_ui=False):
    storage = settings.get("storage", "keyring")
    if storage == "keyring":
        try:
            with _store(allow_ui) as backend:
                return backend.get_password(SERVICE, settings["credential_id"]) or ""
        except CredentialError:
            raise
        except Exception:
            raise CredentialError("Could not read the OS credential store without approved access. Run auth login interactively or use environment authentication.") from None
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


def put(settings, token, config_path, *, allow_ui=False):
    if settings["storage"] == "keyring":
        try:
            with _store(allow_ui) as backend:
                backend.set_password(SERVICE, settings["credential_id"], token)
            return
        except CredentialError:
            raise
        except Exception:
            raise CredentialError("Could not save to the OS credential store. Run auth login interactively to approve access, use environment authentication, or explicitly choose --storage file (POSIX only). No plaintext fallback was written.") from None
    import os
    if os.name == "nt":
        raise CredentialError("File storage on Windows is unsupported until ACL protection is implemented; use the Windows credential store or environment variables.")
    from .config import atomic_json
    path = Path(config_path).with_name("credentials.json")
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    data[settings["credential_id"]] = token
    atomic_json(path, data)


def delete(settings, config_path, *, allow_ui=False):
    if settings["storage"] == "keyring":
        try:
            with _store(allow_ui) as backend:
                backend.delete_password(SERVICE, settings["credential_id"])
        except Exception:
            raise CredentialError("Could not remove the OS credential. Unlock the store and retry logout.") from None
    else:
        from .config import atomic_json
        path = Path(config_path).with_name("credentials.json")
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            data.pop(settings["credential_id"], None)
            atomic_json(path, data)
