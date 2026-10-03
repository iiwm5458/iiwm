"""Versioned, pinned mouse-button plugin interface for the full edition.

Plugins live in the user's application data rather than the installation tree,
so replacing application files does not replace installed plugins. The host only
handles discovery and connection; it has no knowledge of any particular device.
"""

import hashlib
import json
import os
import re
import sys
import types
from pathlib import Path


API_MAJOR = 1
PLUGIN_KIND = "mouse-buttons"
_PLUGIN_ID = re.compile(r"[a-z][a-z0-9_]{0,63}\Z")
_ENTRY_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]*\.py\Z")
# Only this reviewed distribution may execute. Keep these digests in future
# official updates so already-installed copies remain compatible with API v1.
_APPROVED_PAYLOADS = {
    "logitech_click": {
        "manifest.json": "d4a216bce7f368f62210883ee817b3a324c88afa011e35cf874f92575cc1ffcf",
        "backend.py": "6813289379baec329a9f636d06deaefe9ded2d4a51a1f811cf0ecf72fb45a829",
    },
}


class InputPluginError(RuntimeError):
    """An optional input plugin cannot safely be loaded or used."""


def plugin_root():
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise InputPluginError("LOCALAPPDATA is unavailable; cannot locate input plugins")
    return Path(local_app_data).resolve() / "NIKKE C ARENA Tool" / "mods"


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
        if hashlib.sha256(manifest_bytes).hexdigest() != _APPROVED_PAYLOADS[plugin_id]["manifest.json"]:
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
    if hashlib.sha256(backend_bytes).hexdigest() != _APPROVED_PAYLOADS[plugin_id][entry]:
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
