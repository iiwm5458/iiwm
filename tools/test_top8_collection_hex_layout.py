"""Regression coverage for the overseas TOP8/final collection-hex layout."""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
OCR_ROOT = ROOT / "dataanalysis" / "arena_ocr_tool"
sys.path.insert(0, str(OCR_ROOT))

from recognizer import result_parser as parser  # noqa: E402
from recognizer.image_splitter import ImageBlock  # noqa: E402


class _Logger:
    def info(self, _message):
        pass

    def error(self, _message):
        pass

    def warning(self, _message):
        pass


class _Progress:
    def update(self, *_args, **_kwargs):
        pass


class OverseasTop8CollectionHexLayoutTest(unittest.TestCase):
    def slot_box(self, source_profile, block_height, row_width, **kwargs):
        return parser._overseas_collection_slot_box(
            Image.new("RGB", (row_width, 320), "black"),
            source_profile=source_profile,
            block_height=block_height,
            stage_code="top8_pyramid",
            **kwargs,
        )

    def test_3440_top8_uses_uniform_hex_frame_and_never_adds_group64_offset(self):
        first = self.slot_box(
            parser.SOURCE_PROFILE_3440_1440,
            2306,
            788,
            side="attacker",
            team_index=1,
            slot_index=1,
            match_index=1,
        )
        quarterfinal = self.slot_box(
            parser.SOURCE_PROFILE_3440_1440,
            2306,
            788,
            side="attacker",
            team_index=1,
            slot_index=1,
            match_index=4,
        )
        self.assertEqual(first, (1, 82, 29, 114))
        self.assertEqual(quarterfinal, first)
        self.assertEqual((first[2] - first[0], first[3] - first[1]), (28, 32))

    def test_2560x1600_top8_uses_its_calibrated_static_anchor(self):
        box = self.slot_box(
            parser.SOURCE_PROFILE_2560_1600,
            2315,
            789,
            side="attacker",
            team_index=1,
            slot_index=1,
            match_index=4,
        )
        self.assertEqual(box, (3, 81, 31, 113))
        self.assertEqual((box[2] - box[0], box[3] - box[1]), (28, 32))

    def test_all_registered_top8_source_profiles_keep_one_uniform_frame_size(self):
        self.assertEqual(
            set(parser.OVERSEAS_TOP8_COLLECTION_GRID_BY_SOURCE_PROFILE),
            {
                parser.SOURCE_PROFILE_1920_1080,
                parser.SOURCE_PROFILE_1920_1200,
                parser.SOURCE_PROFILE_1920_1440,
                parser.SOURCE_PROFILE_2560_1080,
                parser.SOURCE_PROFILE_2560_1440,
                parser.SOURCE_PROFILE_2560_1600,
                parser.SOURCE_PROFILE_3440_1440,
                parser.SOURCE_PROFILE_3840,
            },
        )
        for source_profile, profile in parser.OVERSEAS_TOP8_COLLECTION_GRID_BY_SOURCE_PROFILE.items():
            with self.subTest(source_profile=source_profile):
                self.assertEqual(profile["icon_width"], 28)
                self.assertEqual(profile["icon_height"], 32)
                self.assertIsInstance(profile["icon_y0"], dict)

    def test_scaled_top8_profile_rounds_the_size_once_for_every_slot(self):
        # A non-reference row width exercises the rounding rule.  Individual
        # x anchors may round differently, but their crop widths may not.
        row = Image.new("RGB", (731, 320), "black")
        boxes = [
            parser._overseas_collection_slot_box(
                row,
                side="attacker",
                team_index=2,
                slot_index=slot,
                match_index=4,
                block_height=2390,
                source_profile=parser.SOURCE_PROFILE_3440_1440,
                stage_code="top8_pyramid",
            )
            for slot in range(1, 6)
        ]
        self.assertEqual({box[2] - box[0] for box in boxes}, {26})
        self.assertEqual({box[3] - box[1] for box in boxes}, {33})

    def test_group64_lower_pair_adjustment_is_preserved_and_isolated_from_top8(self):
        row = Image.new("RGB", (787, 320), "black")
        group64_upper = parser._overseas_collection_slot_box(
            row,
            side="attacker",
            team_index=4,
            slot_index=1,
            match_index=2,
            block_height=2296,
            source_profile=parser.SOURCE_PROFILE_1920_1080,
            stage_code="group64",
        )
        group64_lower = parser._overseas_collection_slot_box(
            row,
            side="attacker",
            team_index=4,
            slot_index=1,
            match_index=4,
            block_height=2296,
            source_profile=parser.SOURCE_PROFILE_1920_1080,
            stage_code="group64",
        )
        self.assertEqual(group64_lower[1] - group64_upper[1], 11)
        self.assertEqual(group64_lower[3] - group64_upper[3], 11)

    def test_season_reader_passes_the_top8_stage_code_to_the_parser(self):
        # Keep the stage switch explicit: matching by a translated display
        # label would make this geometry fragile across UI languages.
        import main

        image = Image.new("RGB", (100, 100), "black")
        block = ImageBlock(1, 4, image, (0, 0, 100, 100))
        args = SimpleNamespace(
            stage_code="top8_pyramid",
            layout="auto",
            no_stat_levels=False,
            no_power=False,
            no_collection=False,
            force_detailed_results=False,
            client_profile="overseas",
        )
        with patch.object(main, "load_image", return_value=image), \
             patch.object(main, "split_input_image", return_value=[block]), \
             patch.object(main, "recognize_match_block", return_value=[{"ok": True}]) as recognize:
            records, block_count, terminated = main.recognize_image_records(
                args,
                Path("top8-3440x1440.png"),
                "top8_pyramid",
                ROOT,
                _Logger(),
                object(),
                object(),
                None,
                _Progress(),
                0,
                1,
                source_profile=parser.SOURCE_PROFILE_3440_1440,
            )

        self.assertGreaterEqual(len(records), 1)
        self.assertEqual(block_count, 1)
        self.assertFalse(terminated)
        self.assertEqual(recognize.call_args.kwargs["stage_code"], "top8_pyramid")


if __name__ == "__main__":
    unittest.main(verbosity=2)
