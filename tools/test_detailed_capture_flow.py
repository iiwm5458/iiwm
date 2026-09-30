"""Regression check for the shared detailed post-match capture loop."""

import importlib.util
import unittest
from unittest.mock import Mock, call, patch
from pathlib import Path

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STITCHER_PATH = PROJECT_ROOT / "nikke_round_stitcher.py"


def load_stitcher():
    spec = importlib.util.spec_from_file_location("nikke_round_stitcher_test", STITCHER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class DetailedCaptureFlowTest(unittest.TestCase):
    def test_popup_dismissal_uses_side_clicks_for_all_servers(self):
        stitcher = load_stitcher()
        for server in ("cn", "global", "hmt"):
            for count in (1, 2):
                for size in ((3440, 1440), (1920, 1080)):
                    with self.subTest(server=server, count=count, size=size):
                        config = stitcher.load_config(PROJECT_ROOT / "nikke_round_config.json")
                        config["runtime_server"] = server
                        clicks = []
                        with patch.object(stitcher, "screenshot", return_value=Image.new("RGB", size)), \
                             patch.object(stitcher, "click_screen_point", side_effect=lambda x, y, duration: clicks.append((x, y))), \
                             patch.object(stitcher, "send_key") as keys, \
                             patch.object(stitcher.time, "sleep") as sleep:
                            if count == 2:
                                stitcher.press_escape_twice(config)
                            else:
                                stitcher.press_escape(config)
                        expected = [(1230, 720), (2190, 720)] if size == (3440, 1440) else [(592, 540), (1312, 540)]
                        self.assertEqual(clicks, expected[:count])
                        keys.assert_not_called()
                        self.assertEqual(sleep.call_args_list, [call(config["timing"]["after_escape_seconds"])] * count)

    def test_missing_side_points_does_not_fall_back_to_escape(self):
        stitcher = load_stitcher()
        config = stitcher.load_config(PROJECT_ROOT / "nikke_round_config.json")
        config["runtime_server"] = "cn"
        config["clicks"]["modal_dismiss_side_points"] = []
        with patch.object(stitcher, "send_key") as keys:
            with self.assertRaises(SystemExit):
                stitcher.dismiss_current_popup(config)
            keys.assert_not_called()

    def test_season_navigation_clicks_return_before_top8(self):
        stitcher = load_stitcher()
        for server in ("cn", "global", "hmt"):
            with self.subTest(server=server):
                config = stitcher.load_config(PROJECT_ROOT / "nikke_round_config.json")
                config["runtime_server"] = server
                with patch.object(stitcher, "click_config_point_or_ratio") as click, \
                     patch.object(stitcher, "send_key") as keys, \
                     patch.object(stitcher.time, "sleep") as sleep:
                    stitcher.navigate_from_group_to_top8(config)
                self.assertEqual(click.call_args_list, [
                    call(config, "season_return_button", "season_return_button_ratio"),
                    call(config, "season_top8_entry", "season_top8_entry_ratio"),
                ])
                self.assertEqual(sleep.call_args_list, [
                    call(stitcher.SEASON_TRANSITION_BACK_WAIT_SECONDS),
                    call(stitcher.SEASON_TOP8_ENTRY_WAIT_SECONDS),
                ])
                keys.assert_not_called()

    def test_automatic_and_manual_click_modes_remain_distinct(self):
        stitcher = load_stitcher()
        for manual in (False, True):
            with self.subTest(manual=manual):
                with patch.object(stitcher, "MANUAL_LEFT_CLICK", manual), \
                     patch.object(stitcher, "user32", Mock()) as user32, \
                     patch.object(stitcher, "send_mouse") as mouse, \
                     patch.object(stitcher, "wait_for_manual_left_click") as confirm, \
                     patch.object(stitcher.time, "sleep"):
                    stitcher.click_screen_point(1230, 720)
                user32.SetCursorPos.assert_called_once_with(1230, 720)
                if manual:
                    mouse.assert_not_called()
                    confirm.assert_called_once_with(1230, 720)
                else:
                    confirm.assert_not_called()
                    self.assertEqual(mouse.call_args_list, [
                        call(stitcher.MOUSEEVENTF_LEFTDOWN), call(stitcher.MOUSEEVENTF_LEFTUP),
                    ])

    def test_result_page_advances_to_black_detail_button(self):
        stitcher = load_stitcher()
        config = stitcher.load_config(PROJECT_ROOT / "nikke_round_config.json")
        config["timing"]["after_group_result_click_seconds"] = 0
        config["save_parts"] = False

        clicks = []
        original = {
            "screenshot": stitcher.screenshot,
            "click": stitcher.click,
            "get_group_result_sequence": stitcher.get_group_result_sequence,
            "prepare_group_result_page": stitcher.prepare_group_result_page,
            "get_group_detail_buttons": stitcher.get_group_detail_buttons,
            "wait_for_detailed_result_page": stitcher.wait_for_detailed_result_page,
            "press_escape": stitcher.press_escape,
            "stitch_vertical": stitcher.stitch_vertical,
        }
        try:
            stitcher.screenshot = lambda: Image.new("RGB", (3440, 1440), "black")
            stitcher.click = lambda point, _transform: clicks.append(tuple(point))
            stitcher.get_group_result_sequence = lambda *_args, **_kwargs: [(110, 210)]
            stitcher.prepare_group_result_page = lambda *_args, **_kwargs: False
            stitcher.get_group_detail_buttons = lambda *_args, **_kwargs: [(310, 410)]
            stitcher.wait_for_detailed_result_page = lambda *_args, **_kwargs: Image.new("RGB", (24, 24), "white")
            stitcher.press_escape = lambda *_args, **_kwargs: None
            stitcher.stitch_vertical = lambda parts, *_args, **_kwargs: parts[0]

            result = stitcher.collect_group_detailed_results(config, PROJECT_ROOT / "_unused", 4)
        finally:
            for name, value in original.items():
                setattr(stitcher, name, value)

        self.assertEqual(clicks, [(110, 210), (310, 410)])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].size, (24, 24))


if __name__ == "__main__":
    unittest.main()
