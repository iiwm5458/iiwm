"""Versioned, pinned mouse-button plugin interface for the full edition.

Plugins live under the host's installation directory. Official updates preserve
that directory, and separate installations manage their own plugins. The host
only handles discovery and connection; it knows no particular device.
"""

import hashlib
import json
import re
import sys
import types
from pathlib import Path


API_MAJOR = 1
PLUGIN_KIND = "mouse-buttons"
PLUGIN_STORAGE = "install-root-v1"
_PLUGIN_ID = re.compile(r"[a-z][a-z0-9_]{0,63}\Z")
_ENTRY_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]*\.py\Z")
# Only reviewed distributions may execute. Keep the original literal table in
# future official updates: older read-only MOD tools parse it without executing
# the host. New versions are separate complete manifest/backend hash pairs.
_APPROVED_PAYLOADS = {
    "logitech_click": {
        "manifest.json": "d4a216bce7f368f62210883ee817b3a324c88afa011e35cf874f92575cc1ffcf",
        "backend.py": "6813289379baec329a9f636d06deaefe9ded2d4a51a1f811cf0ecf72fb45a829",
    },
}
_APPROVED_PAYLOAD_VERSIONS = {
    "logitech_click": [
        {
            "manifest.json": "99224faf95c3331fe39c2c0c7b8779252c8dcff81b9435e04a9358525e98828d",
            "backend.py": "7e7cb4567628d399cdf95fea649f74c73a865aeb8c6ca54724fd6eb7f7ed108d",
        },
        {
            "manifest.json": "0644a658a93db7daec69fb5d4260f4a6a4e42af5e8dacd3e70d97c59f4f25677",
            "backend.py": "7312dabea06bc588d5bbf1086eaa6615e8e9feda46ec8b917c4c5225ff790a44",
        },
    ],
}


def _approved_payloads(plugin_id):
    """Return complete reviewed pairs, never independent per-file allowlists."""
    return (_APPROVED_PAYLOADS[plugin_id],) + tuple(
        _APPROVED_PAYLOAD_VERSIONS.get(plugin_id, ())
    )


class InputPluginError(RuntimeError):
    """An optional input plugin cannot safely be loaded or used."""


def plugin_root():
    install_root = Path(__file__).resolve().parent
    root = (install_root / "mods").resolve()
    if not _within(root, install_root):
        raise InputPluginError("Input plugin root is outside the installation directory")
    return root


def _validate_id(plugin_id):
    if not isinstance(plugin_id, str) or not _PLUGIN_ID.fullmatch(plugin_id):
        raise InputPluginError("Invalid input plugin ID")
    if plugin_id not in _APPROVED_PAYLOADS:
        raise InputPluginError(f"Input plugin is not approved: {plugin_id}")


def _within(path, parent):
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def read_manifest(plugin_id):
    """Return only exact reviewed payload bytes and versioned metadata."""
    _validate_id(plugin_id)
    root = plugin_root().resolve()
    directory = (root / plugin_id).resolve()
    if not _within(directory, root):
        raise InputPluginError("Input plugin directory is outside the plugin root")
    manifest_path = (directory / "manifest.json").resolve()
    if not _within(manifest_path, directory) or not manifest_path.is_file():
        raise InputPluginError(f"Input plugin manifest is missing: {plugin_id}")
    # The installed directory is data, not a source of arbitrary extra modules.
    if any(path.name != "backend.py" for path in directory.glob("*.py")):
        raise InputPluginError(f"Unapproved Python file in input plugin: {plugin_id}")
    try:
        manifest_bytes = manifest_path.read_bytes()
        manifest_digest = hashlib.sha256(manifest_bytes).hexdigest()
        matching_payloads = tuple(
            payload for payload in _approved_payloads(plugin_id)
            if manifest_digest == payload["manifest.json"]
        )
        if not matching_payloads:
            raise InputPluginError(f"Input plugin manifest integrity check failed: {plugin_id}")
        manifest = json.loads(manifest_bytes.decode("utf-8-sig"))
    except InputPluginError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise InputPluginError(f"Could not read input plugin manifest {plugin_id}: {exc}") from exc
    if not isinstance(manifest, dict):
        raise InputPluginError(f"Invalid input plugin manifest: {plugin_id}")
    if manifest.get("id") != plugin_id:
        raise InputPluginError(f"Input plugin ID mismatch: {plugin_id}")
    if manifest.get("kind") != PLUGIN_KIND:
        raise InputPluginError(f"Unsupported input plugin kind: {plugin_id}")
    if type(manifest.get("api_major")) is not int or manifest["api_major"] != API_MAJOR:
        raise InputPluginError(f"Incompatible input plugin API: {plugin_id}")
    if not isinstance(manifest.get("display_name"), str) or not manifest["display_name"].strip():
        raise InputPluginError(f"Input plugin display name is missing: {plugin_id}")
    if not isinstance(manifest.get("warning", ""), str):
        raise InputPluginError(f"Invalid input plugin warning: {plugin_id}")
    entry = manifest.get("entry")
    if not isinstance(entry, str) or not _ENTRY_NAME.fullmatch(entry):
        raise InputPluginError(f"Invalid input plugin entry: {plugin_id}")
    entry_path = (directory / entry).resolve()
    if entry != "backend.py" or not _within(entry_path, directory) or not entry_path.is_file():
        raise InputPluginError(f"Input plugin backend is missing: {plugin_id}")
    try:
        backend_bytes = entry_path.read_bytes()
    except OSError as exc:
        raise InputPluginError(f"Could not read input plugin backend {plugin_id}: {exc}") from exc
    backend_digest = hashlib.sha256(backend_bytes).hexdigest()
    if not any(backend_digest == payload[entry] for payload in matching_payloads):
        raise InputPluginError(f"Input plugin backend integrity check failed: {plugin_id}")
    return manifest, entry_path, backend_bytes


def list_input_plugins():
    """Expose only trusted display fields, without connecting to a device."""
    available = []
    for plugin_id in _APPROVED_PAYLOADS:
        try:
            manifest, _, _ = read_manifest(plugin_id)
        except InputPluginError:
            continue
        available.append({
            "id": manifest["id"],
            "display_name": manifest["display_name"],
            "warning": manifest.get("warning", ""),
        })
    return available


def connect_input_plugin(plugin_id):
    """Execute verified bytes, avoiding a hash/check-to-import file swap."""
    _, entry_path, backend_bytes = read_manifest(plugin_id)
    module_name = f"_nikke_input_plugin_{plugin_id}"
    module = types.ModuleType(module_name)
    module.__file__ = str(entry_path)
    module.__package__ = ""
    sys.modules[module_name] = module
    try:
        exec(compile(backend_bytes, str(entry_path), "exec"), module.__dict__)
        connector = getattr(module, "connect", None)
        if not callable(connector):
            raise InputPluginError(f"Input plugin connect() is missing: {plugin_id}")
        provider = connector()
        if provider is None or not all(
            callable(getattr(provider, name, None))
            for name in ("left_click", "release", "close")
        ):
            raise InputPluginError(f"Input plugin has an invalid mouse-button interface: {plugin_id}")
        return provider
    except InputPluginError:
        raise
    except Exception as exc:
        raise InputPluginError(f"Input plugin connection failed ({plugin_id}): {exc}") from exc
