"""Regression coverage for the November 2026 Global/HMT result-dialog layout."""

import copy
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "nikke_round_config.json"
STITCHER_PATH = PROJECT_ROOT / "nikke_round_stitcher.py"


LEGACY_SIMPLE_RESULT = [1555, 793, 243, 301]
REGIONAL_SIMPLE_RESULT = [1555, 844, 243, 301]
LEGACY_STAGE_TABS_PROBE = [1450, 1110, 650, 120]
REGIONAL_STAGE_TABS_PROBE = [1450, 1161, 650, 120]
LEGACY_DETAIL_BUTTONS = [
    [1891, 826],
    [1891, 887],
    [1891, 948],
    [1891, 1008],
    [1891, 1070],
]
REGIONAL_DETAIL_BUTTONS = [
    [1848, 877],
    [1848, 938],
    [1848, 999],
    [1848, 1059],
    [1848, 1121],
]


def load_stitcher():
    spec = importlib.util.spec_from_file_location(
        "nikke_round_stitcher_global_hmt_result_test", STITCHER_PATH
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class GlobalHmtResultLayoutTest(unittest.TestCase):
    def setUp(self):
        self.worker = load_stitcher()

    def config_for(self, server):
        config = self.worker.load_config(CONFIG_PATH)
        config["runtime_server"] = server
        return config

    def test_resolver_keeps_cn_legacy_and_moves_global_hmt_result_dialog(self):
        expected_by_server = {
            "cn": {
                "simple": LEGACY_SIMPLE_RESULT,
                "tabs_probe": LEGACY_STAGE_TABS_PROBE,
                "avatars": [[1455, 727], [1899, 727]],
                "detail_buttons": LEGACY_DETAIL_BUTTONS,
                "stage_16": [1533, 1158],
                "stage_32": [1903, 1158],
            },
            "global": {
                "simple": REGIONAL_SIMPLE_RESULT,
                "tabs_probe": REGIONAL_STAGE_TABS_PROBE,
                "avatars": [[1455, 778], [1899, 778]],
                "detail_buttons": REGIONAL_DETAIL_BUTTONS,
                "stage_16": [1533, 1209],
                "stage_32": [1903, 1209],
            },
            "hmt": {
                "simple": REGIONAL_SIMPLE_RESULT,
                "tabs_probe": REGIONAL_STAGE_TABS_PROBE,
                "avatars": [[1455, 778], [1899, 778]],
                "detail_buttons": REGIONAL_DETAIL_BUTTONS,
                "stage_16": [1533, 1209],
                "stage_32": [1903, 1209],
            },
        }

        for server, expected in expected_by_server.items():
            with self.subTest(server=server):
                config = self.config_for(server)
                self.assertEqual(
                    self.worker.get_server_layout_value(
                        config, "crops", "group_simple_result"
                    ),
                    expected["simple"],
                )
                self.assertEqual(
                    self.worker.get_server_layout_value(
                        config, "crops", "group_result_stage_tabs_probe"
                    ),
                    expected["tabs_probe"],
                )
                self.assertEqual(
                    self.worker.get_support_result_avatar_points(config, False),
                    expected["avatars"],
                )
                self.assertEqual(
                    self.worker.get_support_result_avatar_points(config, True),
                    expected["avatars"],
                )
                self.assertEqual(
                    self.worker.get_support_result_detail_buttons(config, False),
                    expected["detail_buttons"],
                )
                self.assertEqual(
                    self.worker.get_support_result_detail_buttons(config, True),
                    expected["detail_buttons"],
                )
                self.assertEqual(
                    self.worker.get_group_detail_buttons(config, 4, True),
                    expected["detail_buttons"],
                )
                self.assertEqual(
                    self.worker.get_group_detail_buttons(config, 2, False),
                    expected["detail_buttons"],
                )
                self.assertEqual(
                    self.worker.get_server_layout_value(
                        config, "clicks", "group_16_result_stage_tab"
                    ),
                    expected["stage_16"],
                )
                self.assertEqual(
                    self.worker.get_server_layout_value(
                        config, "clicks", "group_32_result_stage_tab"
                    ),
                    expected["stage_32"],
                )

    def test_missing_regional_overrides_fall_back_without_affecting_cn(self):
        config = copy.deepcopy(self.config_for("global"))
        for key in (
            "support_result_avatars_without_stage_tabs_global_hmt",
            "support_result_avatars_with_stage_tabs_global_hmt",
            "group_16_result_stage_tab_global_hmt",
            "group_32_result_stage_tab_global_hmt",
            "group_detail_buttons_global_hmt",
            "group_32_detail_buttons_global_hmt",
            "support_result_detail_buttons_without_stage_tabs_global_hmt",
            "support_result_detail_buttons_with_stage_tabs_global_hmt",
        ):
            config["clicks"].pop(key, None)
        for key in (
            "group_simple_result_global_hmt",
            "group_result_stage_tabs_probe_global_hmt",
        ):
            config["crops"].pop(key, None)

        self.assertEqual(
            self.worker.get_server_layout_value(config, "crops", "group_simple_result"),
            LEGACY_SIMPLE_RESULT,
        )
        self.assertEqual(
            self.worker.get_support_result_avatar_points(config, False),
            [[1455, 727], [1899, 727]],
        )
        self.assertEqual(
            self.worker.get_group_detail_buttons(config, 4, True),
            LEGACY_DETAIL_BUTTONS,
        )

    def test_simple_result_crop_moves_without_changing_output_size(self):
        source = Image.new("RGB", (3440, 1440), "black")
        source.putpixel((1555, 793), (10, 20, 30))
        source.putpixel((1555, 844), (40, 50, 60))

        for server, expected_pixel in (
            ("cn", (10, 20, 30)),
            ("global", (40, 50, 60)),
            ("hmt", (40, 50, 60)),
        ):
            with self.subTest(server=server):
                crop = self.worker.crop_from_image(
                    self.config_for(server), source, "group_simple_result"
                )
                self.assertEqual(crop.size, (243, 301))
                self.assertEqual(crop.getpixel((0, 0)), expected_pixel)

    def test_stage_tab_click_uses_resolved_point(self):
        blank = Image.new("RGB", (3440, 1440), "black")
        expected_by_server = {
            "cn": ([1533, 1158], [1903, 1158]),
            "global": ([1533, 1209], [1903, 1209]),
            "hmt": ([1533, 1209], [1903, 1209]),
        }

        for server, (expected_16, expected_32) in expected_by_server.items():
            with self.subTest(server=server):
                config = self.config_for(server)
                clicks = []
                with patch.object(self.worker, "has_group_stage_tabs", return_value=True), \
                     patch.object(self.worker, "screenshot", return_value=blank), \
                     patch.object(
                         self.worker,
                         "click",
                         side_effect=lambda point, _transform: clicks.append(list(point)),
                     ), \
                     patch.object(self.worker.time, "sleep"):
                    self.assertTrue(self.worker.prepare_group_result_page(config, 2))
                    self.assertTrue(self.worker.prepare_group_result_page(config, 4))
                self.assertEqual(clicks, [expected_16, expected_32])

    def test_existing_global_hmt_detailed_record_probe_stays_separate(self):
        self.assertEqual(
            self.worker.get_detailed_result_capture_rect(self.config_for("cn")),
            [1380, 289, 681, 873],
        )
        for server in ("global", "hmt"):
            with self.subTest(server=server):
                self.assertEqual(
                    self.worker.get_detailed_result_capture_rect(self.config_for(server)),
                    [1380, 356, 681, 788],
                )

    def test_detailed_page_inspection_covers_every_server_branch(self):
        """Regression for the detailed-page poll after a black-button click."""
        blank = Image.new("RGB", (3440, 1440), "black")
        expected_sizes = {
            "cn": (681, 873),
            "global": (681, 788),
            "hmt": (681, 788),
        }

        for server, expected_size in expected_sizes.items():
            with self.subTest(server=server):
                ready, detail, metrics = self.worker.inspect_detailed_result_page(
                    self.config_for(server), blank
                )
                self.assertFalse(ready)
                self.assertEqual(detail.size, expected_size)
                self.assertEqual(metrics["readiness_rule"], "not_ready")

    def test_centered_height_transform_applies_result_layout_in_window_mode(self):
        config = self.config_for("global")
        transform = self.worker.get_transform(config, (3152, 1350))
        self.assertEqual(
            self.worker.scale_point(REGIONAL_DETAIL_BUTTONS[0], transform),
            (1696, 822),
        )
        self.assertEqual(
            self.worker.scale_rect(REGIONAL_SIMPLE_RESULT, transform, (3152, 1350)),
            (1421, 791, 1649, 1073),
        )


if __name__ == "__main__":
    unittest.main()
