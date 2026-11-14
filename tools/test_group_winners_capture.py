"""Non-interactive checks for the Group01-08 outgoing-player capture path.

This test imports the shared worker but replaces every capture/click primitive.
It never reads the desktop, moves the mouse, or opens the game client.
"""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
WORKER_PATH = ROOT / "nikke_round_stitcher.py"
SPEC = importlib.util.spec_from_file_location("nikke_round_stitcher_test", WORKER_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Cannot import worker: {WORKER_PATH}")
WORKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WORKER)


def make_marker_image(index: int | None) -> Image.Image:
    image = Image.new("RGB", (3440, 1440), "#1D2634")
    if index is not None:
        rect = WORKER.DEFAULT_CONFIG["crops"]["group_16_winner_result_button_probes"][index]
        x, y, width, height = rect
        ImageDraw.Draw(image).rectangle(
            (x, y, x + width - 1, y + height - 1),
            fill=(160, 35, 205),
        )
    return image


class GroupWinnerMarkerTests(unittest.TestCase):
    def setUp(self):
        self.config = WORKER.load_config(ROOT / "nikke_round_config.json")
        self.original_screenshot = WORKER.screenshot

    def tearDown(self):
        WORKER.screenshot = self.original_screenshot

    def test_purple_branch_index_maps_to_the_matching_outgoing_avatar(self):
        for index in (0, 1):
            image = make_marker_image(index)
            WORKER.screenshot = lambda image=image: image
            marker = WORKER.get_group_16_winner_marker(self.config)
            self.assertEqual(index, marker["index"])
            self.assertTrue(WORKER.is_confident_group_16_winner_marker(marker))
            self.assertEqual(
                self.config["clicks"]["group_16_winner_avatars"][index],
                WORKER.get_group_16_winner_avatar(self.config, marker["index"]),
            )

    def test_no_purple_marker_is_not_treated_as_a_winner(self):
        image = make_marker_image(None)
        WORKER.screenshot = lambda: image
        marker = WORKER.get_group_16_winner_marker(self.config)
        self.assertFalse(WORKER.is_confident_group_16_winner_marker(marker))

    def test_winner_points_and_probes_scale_inside_representative_clients(self):
        """Use the same worker transform for fullscreen and client captures.

        ``WindowCaptureContext`` supplies the NIKKE client size to this
        transform, so checking representative ultrawide, 16:10, 16:9 and
        smaller-client sizes verifies that the central winner markers remain
        addressable without introducing separate desktop/window coordinates.
        """
        sizes = ((3440, 1440), (3152, 1382), (2560, 1600), (2560, 1080), (1920, 1080), (1280, 720))
        avatars = self.config["clicks"]["group_16_winner_avatars"]
        probes = self.config["crops"]["group_16_winner_result_button_probes"]
        tab_ratios = self.config["clicks"]["group_tab_ratios"]

        for image_size in sizes:
            with self.subTest(image_size=image_size):
                transform = WORKER.get_transform(self.config, image_size)
                for point in avatars:
                    x, y = WORKER.scale_point(point, transform)
                    self.assertGreaterEqual(x, 0)
                    self.assertLess(x, image_size[0])
                    self.assertGreaterEqual(y, 0)
                    self.assertLess(y, image_size[1])
                for rect in probes:
                    left, top, right, bottom = WORKER.scale_rect(rect, transform, image_size)
                    self.assertLess(left, right)
                    self.assertLess(top, bottom)
                for ratio in tab_ratios:
                    x = round(ratio[0] * image_size[0])
                    y = round(ratio[1] * image_size[1])
                    self.assertGreaterEqual(x, 0)
                    self.assertLess(x, image_size[0])
                    self.assertGreaterEqual(y, 0)
                    self.assertLess(y, image_size[1])

    def test_group_winner_run_collects_exactly_eight_direct_profiles(self):
        config = {
            "clicks": {
                "group_tabs": [[100 + index, 100] for index in range(8)],
                "group_tab_ratios": [],
                "group_16_winner_avatars": [[111, 222], [333, 444]],
            },
            "timing": {"after_group_tab_click_seconds": 0},
            "round_robin_grid_gap": 7,
            "round_robin_background": "#FFFFFF",
            "background": "#20242A",
            "framed_output": False,
        }
        selected_indexes = []
        avatar_clicks = []
        captured_labels = []
        dismissed = []
        saved = []
        image = Image.new("RGB", (3440, 1440), "black")

        def marker_for_group(_config, group_index):
            index = (group_index - 1) % 2
            selected_indexes.append(index)
            return {"index": index, "scores": [9000, 0], "score_ratios": [0.4, 0.0]}

        def record_click(point, _transform):
            avatar_clicks.append(point)

        def fake_capture(_config, _parts_dir, label, close_profile):
            self.assertFalse(close_profile)
            captured_labels.append(label)
            return Image.new("RGB", (10, 4), "#FFFFFF")

        def fake_save(final_img, output_path, output_format, _config):
            saved.append((final_img.size, output_path, output_format))

        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "out.png"
            with patch.object(WORKER, "print_screen_context", return_value={}), patch.object(
                WORKER, "click_group_tab"
            ), patch.object(WORKER, "wait_for_group_16_winner_marker", side_effect=marker_for_group), patch.object(
                WORKER, "screenshot", return_value=image
            ), patch.object(WORKER, "get_transform", return_value={}), patch.object(
                WORKER, "click", side_effect=record_click
            ), patch.object(WORKER, "wait_for_player_lineup_page"), patch.object(
                WORKER, "capture_player_image", side_effect=fake_capture
            ), patch.object(WORKER, "press_escape_twice", side_effect=lambda _config: dismissed.append(True)), patch.object(
                WORKER, "save_group_winners_output", side_effect=fake_save
            ), patch.object(WORKER.time, "sleep"):
                final_path = WORKER.run_group_winners_capture(
                    config,
                    output,
                    Path(temp_dir) / "parts",
                    "jpg78",
                )

        self.assertEqual([0, 1, 0, 1, 0, 1, 0, 1], selected_indexes)
        self.assertEqual(
            [[111, 222], [333, 444], [111, 222], [333, 444], [111, 222], [333, 444], [111, 222], [333, 444]],
            avatar_clicks,
        )
        self.assertEqual([f"group_winner_{index:02d}" for index in range(1, 9)], captured_labels)
        self.assertEqual(8, len(dismissed))
        self.assertEqual((129, 4), saved[0][0])
        self.assertEqual("jpg78", saved[0][2])
        self.assertEqual(".jpg", final_path.suffix)

    def test_png_and_jpg78_writers_keep_the_requested_format(self):
        image = Image.new("RGB", (8, 4), "#663399")
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            png_path = WORKER.group_winners_output_path(temp / "winner.jpg", "png")
            jpg_path = WORKER.group_winners_output_path(temp / "winner.png", "jpg78")
            WORKER.save_round_robin_group_output(image, png_path, "png", {})
            WORKER.save_round_robin_group_output(image, jpg_path, "jpg78", {})
            with Image.open(png_path) as png:
                self.assertEqual("PNG", png.format)
            with Image.open(jpg_path) as jpg:
                self.assertEqual("JPEG", jpg.format)

    def test_framed_group_winners_still_use_the_selected_codec(self):
        image = Image.new("RGB", (8, 4), "#663399")
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            background_path = temp / "background.png"
            Image.new("RGB", (32, 24), "#102030").save(background_path)
            config = {
                "framed_output": True,
                "framed_background": str(background_path),
                "framed_margin_x": 2,
                "framed_margin_y": 1,
                "framed_opacity": 1.0,
                "framed_edge_blur": 0,
                "framed_bg_center": [0.5, 0.5],
            }
            png_path = temp / "framed.png"
            jpg_path = temp / "framed.jpg"
            WORKER.save_group_winners_output(image, png_path, "png", config)
            WORKER.save_group_winners_output(image, jpg_path, "jpg78", config)
            with Image.open(png_path) as png:
                self.assertEqual("PNG", png.format)
                self.assertEqual((12, 6), png.size)
            with Image.open(jpg_path) as jpg:
                self.assertEqual("JPEG", jpg.format)
                self.assertEqual((12, 6), jpg.size)


if __name__ == "__main__":
    unittest.main()
