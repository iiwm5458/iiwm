"""Regression check for the shared detailed post-match capture loop."""

import importlib.util
import unittest
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
