"""Checks the full-edition pinned input plugin boundary and click routing."""

import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = Path(os.environ.get(
    "NIKKE_TEST_INPUT_PLUGIN_PAYLOAD", str(ROOT / "mods" / "logitech_click")
))
# This fixture exercises the host contract without any device or driver code.
MOCK_BACKEND = (
    "class Provider:\n"
    "    def left_click(self, hold_seconds): pass\n"
    "    def release(self): pass\n"
    "    def close(self): pass\n"
    "def connect(): return Provider()\n"
).encode("utf-8")


def load_file(name):
    spec = importlib.util.spec_from_file_location(name.removesuffix(".py") + "_test", ROOT / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class InputPluginHostTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.plugin_dir = Path(self.temp.name) / "NIKKE C ARENA Tool" / "mods" / "logitech_click"
        self.plugin_dir.mkdir(parents=True)
        self.environment = patch.dict(os.environ, {"LOCALAPPDATA": self.temp.name})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.host = load_file("nikke_input_plugins.py")
        payload_files = [PAYLOAD / name for name in ("manifest.json", "backend.py")]
        self.private_payload_present = any(path.exists() for path in payload_files)
        if self.private_payload_present:
            # An incomplete or modified private distribution must fail, never
            # silently fall back to a test fixture or change production pins.
            for path in payload_files:
                self.assertTrue(path.is_file(), f"Private payload is incomplete: {path}")
                self.assertEqual(
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                    self.host._APPROVED_PAYLOADS["logitech_click"][path.name],
                    f"Private payload no longer matches production pin: {path.name}",
                )
                shutil.copy2(path, self.plugin_dir / path.name)
        else:
            manifest = {
                "id": "logitech_click",
                "kind": "mouse-buttons",
                "api_major": 1,
                "entry": "backend.py",
                "display_name": "Test input provider",
                "warning": "Generated fixture; no device access.",
            }
            manifest_bytes = json.dumps(manifest, ensure_ascii=True).encode("utf-8")
            (self.plugin_dir / "manifest.json").write_bytes(manifest_bytes)
            (self.plugin_dir / "backend.py").write_bytes(MOCK_BACKEND)
            # Approve only this freshly loaded test module. The production host
            # file and hosts loaded by isolated worker processes stay pinned.
            fixture_pins = patch.dict(self.host._APPROVED_PAYLOADS, {
                "logitech_click": {
                    "manifest.json": hashlib.sha256(manifest_bytes).hexdigest(),
                    "backend.py": hashlib.sha256(MOCK_BACKEND).hexdigest(),
                },
            })
            fixture_pins.start()
            self.addCleanup(fixture_pins.stop)

    def test_optional_private_payload_matches_production_pins(self):
        if not self.private_payload_present:
            self.skipTest("Optional private MOD payload is not distributed in the public source")
        manifest, entry, backend_bytes = self.host.read_manifest("logitech_click")
        self.assertEqual(manifest["id"], "logitech_click")
        self.assertEqual(entry, self.plugin_dir / "backend.py")
        self.assertEqual(backend_bytes, (PAYLOAD / "backend.py").read_bytes())

    def test_only_pinned_distribution_is_listed(self):
        manifest = json.loads((self.plugin_dir / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(self.host.list_input_plugins(), [{
            "id": "logitech_click",
            "display_name": manifest["display_name"],
            "warning": manifest["warning"],
        }])
        for name in ("manifest.json", "backend.py"):
            with self.subTest(tampered=name):
                target = self.plugin_dir / name
                original = target.read_bytes()
                try:
                    target.write_bytes(original + b"\n")
                    self.assertEqual(self.host.list_input_plugins(), [])
                    with self.assertRaises(self.host.InputPluginError):
                        self.host.connect_input_plugin("logitech_click")
                finally:
                    target.write_bytes(original)

    def test_rejects_other_ids_and_extra_python_file(self):
        with self.assertRaises(self.host.InputPluginError):
            self.host.read_manifest("../logitech_click")
        with self.assertRaises(self.host.InputPluginError):
            self.host.read_manifest("unreviewed")
        (self.plugin_dir / "helper.py").write_text("raise RuntimeError('must not execute')\n")
        self.assertEqual(self.host.list_input_plugins(), [])

    def test_executes_only_verified_bytes(self):
        fixture = MOCK_BACKEND + b"# verified execution test\n"
        (self.plugin_dir / "backend.py").write_bytes(fixture)
        with patch.object(self.host, "exec", wraps=exec, create=True) as execute:
            with self.assertRaises(self.host.InputPluginError):
                self.host.connect_input_plugin("logitech_click")
            execute.assert_not_called()
            self.host._APPROVED_PAYLOADS["logitech_click"]["backend.py"] = hashlib.sha256(fixture).hexdigest()
            provider = self.host.connect_input_plugin("logitech_click")
            execute.assert_called_once()
        provider.left_click(0.08)
        provider.release()
        provider.close()

    def test_bundled_isolated_worker_lists_only_verified_plugin(self):
        python = ROOT / "runtime_core" / "python.exe"
        if not python.is_file():
            self.skipTest("Bundled Python runtime is unavailable")
        result = subprocess.run(
            [str(python), str(ROOT / "nikke_round_stitcher.py"), "--list-input-plugins"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=dict(os.environ),
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        expected = self.host.list_input_plugins() if self.private_payload_present else []
        self.assertEqual(json.loads(result.stdout), expected)

    def test_worker_routes_position_then_button_click_and_releases_after_failure(self):
        worker = load_file("nikke_round_stitcher.py")
        provider = Mock()
        with patch.object(worker, "ACTIVE_INPUT_PLUGIN", provider), \
             patch.object(worker, "MANUAL_LEFT_CLICK", True), \
             patch.object(worker, "user32", Mock()) as user32, \
             patch.object(worker, "send_mouse") as send_mouse, \
             patch.object(worker, "wait_for_manual_left_click") as manual, \
             patch.object(worker.time, "sleep"):
            worker.click_screen_point(123, 456, 0.04)
        user32.SetCursorPos.assert_called_once_with(123, 456)
        provider.left_click.assert_called_once_with(0.08)
        send_mouse.assert_not_called()
        manual.assert_not_called()

        provider.left_click.side_effect = RuntimeError("device disconnected")
        with patch.object(worker, "ACTIVE_INPUT_PLUGIN", provider), \
             patch.object(worker, "user32", Mock()), \
             patch.object(worker.time, "sleep"):
            with self.assertRaisesRegex(RuntimeError, "device disconnected"):
                worker.click_screen_point(123, 456)
        provider.release.assert_called_once()

    def test_lite_worker_does_not_offer_extension_cli(self):
        worker = load_file("nikke_round_stitcher.py")
        lite_file = str(Path(self.temp.name) / "lite" / "nikke_round_stitcher.py")
        help_output = io.StringIO()
        with patch.object(worker, "__file__", lite_file), \
             patch("sys.argv", [lite_file, "--help"]), \
             redirect_stdout(help_output):
            with self.assertRaises(SystemExit) as exited:
                worker.parse_args()
        self.assertEqual(exited.exception.code, 0)
        self.assertNotIn("--input-plugin", help_output.getvalue())

        error_output = io.StringIO()
        with patch.object(worker, "__file__", lite_file), \
             patch("sys.argv", [lite_file, "--input-plugin", "logitech_click"]), \
             redirect_stderr(error_output):
            with self.assertRaises(SystemExit) as exited:
                worker.parse_args()
        self.assertEqual(exited.exception.code, 2)
        self.assertIn("unrecognized arguments", error_output.getvalue())


if __name__ == "__main__":
    unittest.main()
