"""Regression coverage for the November 2026 Global/HMT player-lineup layout."""

import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "nikke_round_config.json"
STITCHER_PATH = PROJECT_ROOT / "nikke_round_stitcher.py"


def load_stitcher():
    spec = importlib.util.spec_from_file_location(
        "nikke_round_stitcher_global_hmt_lineup_test", STITCHER_PATH
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class GlobalHmtLineupLayoutTest(unittest.TestCase):
    def setUp(self):
        self.worker = load_stitcher()

    def config_for(self, server):
        config = self.worker.load_config(CONFIG_PATH)
        config["runtime_server"] = server
        return config

    def test_resolver_keeps_cn_legacy_and_moves_global_hmt(self):
        expected_legacy = {
            "avatar": [1477, 579],
            "round_lineup": [1393, 756, 660, 274],
            "header_probe": [1380, 405, 680, 105],
            "tabs_probe": [1395, 670, 665, 74],
            "cards_probe": [1393, 756, 660, 274],
        }
        expected_regional = {
            "avatar": [1477, 549],
            "round_lineup": [1393, 786, 660, 274],
            "header_probe": [1380, 375, 680, 105],
            "tabs_probe": [1395, 700, 665, 74],
            "cards_probe": [1393, 786, 660, 274],
        }

        for server in ("cn", "global", "hmt"):
            with self.subTest(server=server):
                layout = self.worker.get_player_lineup_layout(self.config_for(server))
                expected = expected_legacy if server == "cn" else expected_regional
                for name, value in expected.items():
                    self.assertEqual(layout[name], value)
                self.assertEqual(
                    layout["round_tabs"],
                    {
                        "1": [1462, 707 if server == "cn" else 737],
                        "2": [1604, 707 if server == "cn" else 737],
                        "3": [1754, 707 if server == "cn" else 737],
                        "4": [1848, 707 if server == "cn" else 737],
                        "5": [2001, 707 if server == "cn" else 737],
                    },
                )

    def test_missing_regional_keys_fall_back_to_legacy_layout(self):
        config = copy.deepcopy(self.config_for("global"))
        for key in ("avatar_global_hmt", "round_tabs_global_hmt"):
            config["clicks"].pop(key)
        for key in (
            "round_lineup_global_hmt",
            "player_lineup_header_probe_global_hmt",
            "player_lineup_tabs_probe_global_hmt",
            "player_lineup_cards_probe_global_hmt",
        ):
            config["crops"].pop(key)

        layout = self.worker.get_player_lineup_layout(config)
        self.assertEqual(layout["avatar"], [1477, 579])
        self.assertEqual(layout["round_tabs"]["1"], [1462, 707])
        self.assertEqual(layout["round_lineup"], [1393, 756, 660, 274])
        self.assertEqual(layout["header_probe"], [1380, 405, 680, 105])
        self.assertEqual(layout["tabs_probe"], [1395, 670, 665, 74])
        self.assertEqual(layout["cards_probe"], [1393, 756, 660, 274])

    def test_round_lineup_crop_uses_resolved_origin_without_size_change(self):
        source = Image.new("RGB", (3440, 1440), "black")
        source.putpixel((1393, 756), (10, 20, 30))
        source.putpixel((1393, 786), (40, 50, 60))

        for server, expected_pixel in (
            ("cn", (10, 20, 30)),
            ("global", (40, 50, 60)),
            ("hmt", (40, 50, 60)),
        ):
            with self.subTest(server=server):
                crop = self.worker.crop_from_image(
                    self.config_for(server), source, "round_lineup"
                )
                self.assertEqual(crop.size, (660, 274))
                self.assertEqual(crop.getpixel((0, 0)), expected_pixel)

    def test_capture_uses_resolved_round_tabs_and_avatar(self):
        blank = Image.new("RGB", (3440, 1440), "black")

        for server in ("cn", "global", "hmt"):
            with self.subTest(server=server):
                config = self.config_for(server)
                layout = self.worker.get_player_lineup_layout(config)
                clicks = []

                def crop_current(_config, crop_name):
                    if crop_name == "round_lineup":
                        return Image.new("RGB", (660, 274), "white")
                    if crop_name == "team_summary":
                        return Image.new("RGB", (656, 122), "white")
                    raise AssertionError(f"unexpected crop: {crop_name}")

                with patch.object(self.worker, "screenshot", return_value=blank), \
                     patch.object(
                         self.worker,
                         "click",
                         side_effect=lambda point, _transform: clicks.append(list(point)),
                     ), \
                     patch.object(self.worker, "crop_current", side_effect=crop_current), \
                     patch.object(
                         self.worker,
                         "wait_for_profile_basic_page",
                         return_value=Image.new("RGB", (684, 514), "white"),
                     ), \
                     patch.object(
                         self.worker,
                         "crop_rects_from_image",
                         return_value=[Image.new("RGB", (638, 64), "white")],
                     ), \
                     patch.object(
                         self.worker,
                         "make_research_row",
                         return_value=Image.new("RGB", (638, 64), "white"),
                     ), \
                     patch.object(self.worker, "stitch", side_effect=lambda parts, _config: parts[0]), \
                     patch.object(self.worker.time, "sleep"):
                    result = self.worker.capture_player_image(
                        config, PROJECT_ROOT / "_unused", close_profile=False
                    )

                self.assertEqual(result.size, (684, 514))
                self.assertEqual(
                    clicks,
                    [layout["round_tabs"][str(index)] for index in range(1, 6)]
                    + [layout["avatar"], config["clicks"]["outpost_tab"]],
                )

    def test_lineup_poll_probes_come_from_resolved_layout(self):
        blank = Image.new("RGB", (3440, 1440), "black")
        original_scale_rect = self.worker.scale_rect

        for server in ("cn", "global", "hmt"):
            with self.subTest(server=server):
                config = self.config_for(server)
                layout = self.worker.get_player_lineup_layout(config)
                observed = []

                def recording_scale_rect(rect, transform, image_size):
                    observed.append(list(rect))
                    return original_scale_rect(rect, transform, image_size)

                with patch.object(self.worker, "scale_rect", side_effect=recording_scale_rect):
                    ready, _metrics = self.worker.inspect_player_lineup_page(config, blank)

                self.assertFalse(ready)
                self.assertEqual(
                    observed,
                    [layout["header_probe"], layout["tabs_probe"], layout["cards_probe"]],
                )

    def test_preview_marks_resolved_layout(self):
        blank = Image.new("RGB", (3440, 1440), "black")

        def has_color(image, center, rgb, radius=12):
            left = max(0, center[0] - radius)
            top = max(0, center[1] - radius)
            right = min(image.width, center[0] + radius + 1)
            bottom = min(image.height, center[1] + radius + 1)
            return any(
                image.getpixel((x, y))[:3] == rgb
                for y in range(top, bottom)
                for x in range(left, right)
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            for server in ("cn", "global", "hmt"):
                with self.subTest(server=server):
                    config = self.config_for(server)
                    layout = self.worker.get_player_lineup_layout(config)
                    output = Path(temp_dir) / f"preview_{server}.png"
                    with patch.object(self.worker, "screenshot", return_value=blank.copy()):
                        self.worker.preview_regions(config, output)
                    with Image.open(output) as preview:
                        preview = preview.convert("RGB")
                        crop = layout["round_lineup"]
                        self.assertTrue(
                            has_color(preview, (crop[0], crop[1]), (0, 255, 255), 4)
                        )
                        tab = layout["round_tabs"]["1"]
                        self.assertTrue(
                            has_color(preview, (tab[0], tab[1] - 8), (255, 255, 0))
                        )
                        avatar = layout["avatar"]
                        self.assertTrue(
                            has_color(preview, (avatar[0], avatar[1] - 10), (0, 255, 0))
                        )

    def test_centered_height_transform_scales_regional_layout(self):
        config = self.config_for("global")
        layout = self.worker.get_player_lineup_layout(config)

        expected = {
            (3440, 1440): {
                "tab": (1462, 737),
                "avatar": (1477, 549),
                "crop": (1393, 786, 2053, 1060),
            },
            (2560, 1080): {
                "tab": (1086, 553),
                "avatar": (1098, 412),
                "crop": (1035, 590, 1530, 795),
            },
            (1920, 1080): {
                "tab": (766, 553),
                "avatar": (778, 412),
                "crop": (715, 590, 1210, 795),
            },
        }
        for image_size, values in expected.items():
            with self.subTest(image_size=image_size):
                transform = self.worker.get_transform(config, image_size)
                self.assertEqual(
                    self.worker.scale_point(layout["round_tabs"]["1"], transform),
                    values["tab"],
                )
                self.assertEqual(
                    self.worker.scale_point(layout["avatar"], transform),
                    values["avatar"],
                )
                self.assertEqual(
                    self.worker.scale_rect(
                        layout["round_lineup"], transform, image_size
                    ),
                    values["crop"],
                )


if __name__ == "__main__":
    unittest.main()
