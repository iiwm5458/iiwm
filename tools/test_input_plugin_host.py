"""Checks the full-edition pinned input plugin boundary and click routing."""

import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
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


def load_file(name, directory=ROOT):
    spec = importlib.util.spec_from_file_location(name.removesuffix(".py") + "_test", directory / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class InputPluginHostTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.install_root = Path(self.temp.name) / "tool"
        self.plugin_dir = self.install_root / "mods" / "logitech_click"
        self.plugin_dir.mkdir(parents=True)
        shutil.copy2(ROOT / "nikke_input_plugins.py", self.install_root / "nikke_input_plugins.py")
        self.environment = patch.dict(os.environ, {"LOCALAPPDATA": str(Path(self.temp.name) / "appdata")})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.host = load_file("nikke_input_plugins.py", self.install_root)
        payload_files = [PAYLOAD / name for name in ("manifest.json", "backend.py")]
        self.private_payload_present = any(path.exists() for path in payload_files)
        if self.private_payload_present:
            # An incomplete or modified private distribution must fail, never
            # silently fall back to a test fixture or change production pins.
            digests = {}
            for path in payload_files:
                self.assertTrue(path.is_file(), f"Private payload is incomplete: {path}")
                digests[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
            matched = [
                pair for pair in self.host._approved_payloads("logitech_click")
                if pair == digests
            ]
            self.assertTrue(matched, "Private payload no longer matches a complete production hash pair")
            self.accepted_payload = matched[0]
            for path in payload_files:
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
            # file and other host instances stay pinned.
            fixture_pins = patch.dict(self.host._APPROVED_PAYLOADS, {
                "logitech_click": {
                    "manifest.json": hashlib.sha256(manifest_bytes).hexdigest(),
                    "backend.py": hashlib.sha256(MOCK_BACKEND).hexdigest(),
                },
            })
            fixture_pins.start()
            self.addCleanup(fixture_pins.stop)
            self.accepted_payload = self.host._APPROVED_PAYLOADS["logitech_click"]

    def create_worker_fixture(self, name, display_name):
        """Copy the real worker and a host with only generated test payload pins."""
        tool = Path(self.temp.name) / name
        directory = tool / "mods" / "logitech_click"
        directory.mkdir(parents=True)
        manifest = {
            "id": "logitech_click",
            "kind": "mouse-buttons",
            "api_major": 1,
            "entry": "backend.py",
            "display_name": display_name,
            "warning": "Generated fixture; no device access.",
        }
        manifest_bytes = json.dumps(manifest, ensure_ascii=True).encode("utf-8")
        (directory / "manifest.json").write_bytes(manifest_bytes)
        (directory / "backend.py").write_bytes(MOCK_BACKEND)
        fixture_pins = {
            "logitech_click": {
                "manifest.json": hashlib.sha256(manifest_bytes).hexdigest(),
                "backend.py": hashlib.sha256(MOCK_BACKEND).hexdigest(),
            },
        }
        # Overrides exist only in this temporary host copy, never public source.
        host_bytes = (ROOT / "nikke_input_plugins.py").read_bytes()
        host_bytes += (
            "\n# Generated subprocess fixture; no driver or device code.\n"
            f"_APPROVED_PAYLOADS = {fixture_pins!r}\n"
            "_APPROVED_PAYLOAD_VERSIONS = {}\n"
        ).encode("utf-8")
        (tool / "nikke_input_plugins.py").write_bytes(host_bytes)
        shutil.copy2(ROOT / "nikke_round_stitcher.py", tool / "nikke_round_stitcher.py")
        return tool, [{
            "id": manifest["id"],
            "display_name": manifest["display_name"],
            "warning": manifest["warning"],
        }]

    def worker_list(self, tool, cwd):
        python = ROOT / "runtime_core" / "python.exe"
        if not python.is_file():
            python = Path(sys.executable)
        result = subprocess.run(
            [str(python), str(tool / "nikke_round_stitcher.py"), "--list-input-plugins"],
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=dict(os.environ),
            check=False,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        return json.loads(result.stdout)

    def test_root_comes_from_host_file_without_localappdata(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(self.host.plugin_root(), self.install_root / "mods")
        self.assertEqual(self.host.PLUGIN_STORAGE, "install-root-v1")
        self.assertEqual(self.host.API_MAJOR, 1)

    def test_rejects_mods_directory_link_outside_installation(self):
        tool = Path(self.temp.name) / "linked_tool"
        tool.mkdir()
        shutil.copy2(ROOT / "nikke_input_plugins.py", tool / "nikke_input_plugins.py")
        external = Path(self.temp.name) / "external_mods"
        external.mkdir()
        link = tool / "mods"
        if os.name == "nt":
            linked = subprocess.run(
                ["cmd.exe", "/c", "mklink", "/J", str(link), str(external)],
                capture_output=True, check=False, timeout=10,
            )
            self.assertEqual(linked.returncode, 0, linked.stderr.decode(errors="replace"))
        else:
            link.symlink_to(external, target_is_directory=True)
        linked_host = load_file("nikke_input_plugins.py", tool)
        with self.assertRaisesRegex(linked_host.InputPluginError, "outside the installation"):
            linked_host.plugin_root()
        with self.assertRaises(linked_host.InputPluginError):
            linked_host.read_manifest("logitech_click")
        self.assertEqual(linked_host.list_input_plugins(), [])

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
            self.accepted_payload["backend.py"] = hashlib.sha256(fixture).hexdigest()
            provider = self.host.connect_input_plugin("logitech_click")
            execute.assert_called_once()
        provider.left_click(0.08)
        provider.release()
        provider.close()

    def test_production_pairs_are_retained_for_older_and_newer_mods(self):
        production = load_file("nikke_input_plugins.py")
        self.assertEqual(production._APPROVED_PAYLOADS["logitech_click"], {
            "manifest.json": "d4a216bce7f368f62210883ee817b3a324c88afa011e35cf874f92575cc1ffcf",
            "backend.py": "6813289379baec329a9f636d06deaefe9ded2d4a51a1f811cf0ecf72fb45a829",
        })
        self.assertIn(
            production._APPROVED_PAYLOADS["logitech_click"],
            production._approved_payloads("logitech_click"),
        )
        self.assertIn({
            "manifest.json": "99224faf95c3331fe39c2c0c7b8779252c8dcff81b9435e04a9358525e98828d",
            "backend.py": "7e7cb4567628d399cdf95fea649f74c73a865aeb8c6ca54724fd6eb7f7ed108d",
        }, production._APPROVED_PAYLOAD_VERSIONS["logitech_click"])
        self.assertEqual(len(production._approved_payloads("logitech_click")), 3)

    def test_accepts_each_complete_reviewed_pair_and_rejects_mixed_pairs(self):
        # Public fixtures contain no real driver implementation. Pins are only
        # replaced in this isolated in-memory host.
        versions = []
        for version in ("old", "new", "repair"):
            manifest = {
                "id": "logitech_click",
                "kind": "mouse-buttons",
                "api_major": 1,
                "entry": "backend.py",
                "version": version,
                "display_name": f"Generated {version} provider",
                "warning": "Generated fixture; no device access.",
            }
            manifest_bytes = json.dumps(manifest, ensure_ascii=True).encode("utf-8")
            backend_bytes = MOCK_BACKEND + f"# {version} fixture\n".encode("ascii")
            versions.append((manifest_bytes, backend_bytes, {
                "manifest.json": hashlib.sha256(manifest_bytes).hexdigest(),
                "backend.py": hashlib.sha256(backend_bytes).hexdigest(),
            }))
        with patch.dict(self.host._APPROVED_PAYLOADS, {"logitech_click": versions[0][2]}), \
             patch.dict(self.host._APPROVED_PAYLOAD_VERSIONS, {"logitech_click": [item[2] for item in versions[1:]]}):
            for index in range(len(versions)):
                with self.subTest(accepted=index):
                    (self.plugin_dir / "manifest.json").write_bytes(versions[index][0])
                    (self.plugin_dir / "backend.py").write_bytes(versions[index][1])
                    manifest, _, verified_bytes = self.host.read_manifest("logitech_click")
                    self.assertEqual(verified_bytes, versions[index][1])
                    self.assertEqual(self.host.list_input_plugins()[0]["display_name"], manifest["display_name"])
                    provider = self.host.connect_input_plugin("logitech_click")
                    provider.left_click(0.08)
                    provider.release()
                    provider.close()
            mixed_pairs = ((left, right) for left in range(len(versions))
                           for right in range(len(versions)) if left != right)
            for manifest_index, backend_index in mixed_pairs:
                with self.subTest(mixed=(manifest_index, backend_index)):
                    (self.plugin_dir / "manifest.json").write_bytes(versions[manifest_index][0])
                    (self.plugin_dir / "backend.py").write_bytes(versions[backend_index][1])
                    self.assertEqual(self.host.list_input_plugins(), [])
                    with patch.object(self.host, "exec", wraps=exec, create=True) as execute:
                        with self.assertRaisesRegex(self.host.InputPluginError, "backend integrity check failed"):
                            self.host.connect_input_plugin("logitech_click")
                        execute.assert_not_called()

    def test_worker_reads_own_install_root_from_unrelated_cwd(self):
        tool, expected = self.create_worker_fixture("worker_tool", "Worker fixture")
        unrelated = Path(self.temp.name) / "unrelated_cwd"
        unrelated.mkdir()
        self.assertEqual(self.worker_list(tool, unrelated), expected)
        # A changed backend must remain hidden even when discovery succeeds.
        with (tool / "mods" / "logitech_click" / "backend.py").open("ab") as backend:
            backend.write(b"\n# unapproved edit\n")
        self.assertEqual(self.worker_list(tool, unrelated), [])

    def test_workers_are_independent_and_never_fall_back_to_appdata(self):
        first, expected_first = self.create_worker_fixture("first_tool", "First tool")
        second, expected_second = self.create_worker_fixture("second_tool", "Second tool")
        legacy_dir = Path(os.environ["LOCALAPPDATA"]) / "NIKKE C ARENA Tool" / "mods" / "logitech_click"
        legacy_dir.mkdir(parents=True)
        for name in ("manifest.json", "backend.py"):
            shutil.copy2(first / "mods" / "logitech_click" / name, legacy_dir / name)
        self.assertEqual(self.worker_list(first, second), expected_first)
        self.assertEqual(self.worker_list(second, first), expected_second)
        (first / "mods" / "logitech_click" / "manifest.json").unlink()
        # The first fixture is still valid in AppData, and the second cwd also
        # has a valid MOD. Neither can replace the missing first tool payload.
        self.assertEqual(self.worker_list(first, second), [])
        self.assertEqual(self.worker_list(second, first), expected_second)

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
