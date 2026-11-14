"""Regression coverage for round-robin batch PNG and JPEG-78 output."""

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
STITCHER_PATH = ROOT / "nikke_round_stitcher.py"


def load_stitcher():
    spec = importlib.util.spec_from_file_location("nikke_round_stitcher_output_format_test", STITCHER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class RoundRobinOutputFormatTest(unittest.TestCase):
    def setUp(self):
        self.worker = load_stitcher()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output_root = Path(self.temp.name)

    def test_legacy_or_invalid_config_uses_jpeg78(self):
        legacy_config = self.output_root / "legacy.json"
        legacy_config.write_text(json.dumps({"round_robin_background": "#FFFFFF"}), encoding="utf-8")
        loaded = self.worker.load_config(legacy_config)
        self.assertEqual(loaded["round_robin_output_format"], "jpg78")
        self.assertEqual(self.worker.normalize_round_robin_output_format("invalid"), "jpg78")
        self.assertEqual(self.worker.normalize_round_robin_output_format(None), "jpg78")

    def test_batch_output_paths_follow_selected_format_and_never_overwrite(self):
        base = self.output_root / "batch.jpg"
        png_path = self.worker.round_robin_group_output_path(base, 1, "png")
        jpg_path = self.worker.round_robin_group_output_path(base, 1, "jpg78")
        self.assertEqual(png_path.name, "Group01-batch.png")
        self.assertEqual(jpg_path.name, "Group01-batch.jpg")
        png_path.write_bytes(b"existing")
        self.assertEqual(
            self.worker.round_robin_group_output_path(base, 1, "png").name,
            "Group01-batch-2.png",
        )

    def test_png_output_is_lossless(self):
        image = Image.new("RGB", (3, 2))
        image.putdata([
            (0, 1, 2), (3, 4, 5), (6, 7, 8),
            (9, 10, 11), (12, 13, 14), (15, 16, 17),
        ])
        path = self.output_root / "group.png"
        self.worker.save_round_robin_group_output(image, path, "png", {})
        with Image.open(path) as saved:
            self.assertEqual(saved.format, "PNG")
            saved_rgb = saved.convert("RGB")
            self.assertEqual(
                [saved_rgb.getpixel((x, y)) for y in range(2) for x in range(3)],
                [image.getpixel((x, y)) for y in range(2) for x in range(3)],
            )

    def test_jpeg78_keeps_the_existing_encoder_settings(self):
        image = Image.new("RGB", (3, 2), "red")
        path = self.output_root / "group.jpg"
        with patch.object(Image.Image, "save", autospec=True) as save:
            self.worker.save_round_robin_group_output(image, path, "jpg78", {})
        _, args, kwargs = save.mock_calls[0]
        self.assertEqual(args[1], path)
        self.assertEqual(kwargs["format"], "JPEG")
        self.assertEqual(kwargs["quality"], 78)
        self.assertEqual(kwargs["subsampling"], 2)
        self.assertTrue(kwargs["optimize"])

    def test_cli_accepts_only_supported_batch_formats(self):
        with patch.object(sys, "argv", [str(STITCHER_PATH), "--round-robin-output-format", "png"]):
            self.assertEqual(self.worker.parse_args().round_robin_output_format, "png")
        with patch.object(sys, "argv", [str(STITCHER_PATH)]):
            self.assertIsNone(self.worker.parse_args().round_robin_output_format)


if __name__ == "__main__":
    unittest.main()
