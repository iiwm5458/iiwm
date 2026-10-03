"""Check roster power slot alignment without creating workbook artifacts."""

import importlib.util
import unittest
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "ocr_exporter_test",
    ROOT / "dataanalysis" / "arena_ocr_tool" / "recognizer" / "exporter.py",
)
exporter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(exporter)
MISSING = "\u672a\u8bc6\u522b"


class RosterPowerExportTest(unittest.TestCase):
    def test_missing_first_middle_last_and_multiple_slots_keep_alignment(self):
        cases = [
            (
                [None, 156442, 158079, 146465, 156664],
                f"{MISSING} / 156442 / 158079 / 146465 / 156664",
            ),
            (
                [98970, 156442, "", 146465, 156664],
                f"98970 / 156442 / {MISSING} / 146465 / 156664",
            ),
            (
                [98970, 156442, 158079, 146465, None],
                f"98970 / 156442 / 158079 / 146465 / {MISSING}",
            ),
            (
                [None, 156442, "", None, 156664],
                f"{MISSING} / 156442 / {MISSING} / {MISSING} / 156664",
            ),
        ]
        for powers, expected in cases:
            with self.subTest(powers=powers):
                row = exporter._roster_row(
                    {"powers": {5: powers}}, include_stat_levels=False
                )
                self.assertEqual(row[15], expected)

    def test_normal_values_and_zero_are_preserved(self):
        self.assertEqual(
            exporter._join_roster_powers([98970, 156442, 158079, 146465, 156664]),
            "98970 / 156442 / 158079 / 146465 / 156664",
        )
        self.assertEqual(
            exporter._join_roster_powers([0, "0", 158079, 146465, 156664]),
            "0 / 0 / 158079 / 146465 / 156664",
        )

    def test_short_or_missing_power_lists_still_have_five_slots(self):
        for values in (None, [], [None] * 5, [""] * 5):
            with self.subTest(values=values):
                self.assertEqual(
                    exporter._join_roster_powers(values), " / ".join([MISSING] * 5)
                )
        self.assertEqual(
            exporter._join_roster_powers([98970]),
            " / ".join(["98970"] + [MISSING] * 4),
        )
        self.assertEqual(
            exporter._join_roster_powers([1, 2, 3, 4, 5, 6]), "1 / 2 / 3 / 4 / 5"
        )

    def test_names_collections_and_source_data_are_unchanged(self):
        entry = {
            "nickname": "Player",
            "player_id": "00775198",
            "teams": {"1": ["Polly", "", "Alice", None, "Noir"]},
            "powers": {"1": [None, 156442, 158079, 146465, 156664]},
            "collections": {"1": ["SR", None, "", "R", "SR"]},
        }
        original = deepcopy(entry)
        row = exporter._roster_row(entry, include_stat_levels=False)
        self.assertEqual(row[2], "Polly / Alice / Noir")
        self.assertEqual(row[4], "SR / R / SR")
        self.assertEqual(entry, original)
        json_entry = exporter._roster_json_entry(entry, include_stat_levels=False)
        self.assertEqual(json_entry["\u9635\u5bb91\u6218\u529b"], entry["powers"]["1"])
        self.assertEqual(json_entry["\u9635\u5bb91"], entry["teams"]["1"])
        self.assertEqual(json_entry["\u9635\u5bb91\u6536\u85cf"], entry["collections"]["1"])

    def test_no_power_export_omits_power_columns(self):
        entry = {
            "nickname": "Player",
            "player_id": "00775198",
            "teams": {1: ["Polly"]},
            "powers": {1: [None, 156442, 158079, 146465, 156664]},
            "collections": {1: ["SR"]},
        }
        row = exporter._roster_row(
            entry, include_power=False, include_stat_levels=False
        )
        self.assertEqual(row, ["Player", "00775198", "Polly", "SR"] + [""] * 8)
        headers = exporter.build_roster_headers(
            include_power=False, include_stat_levels=False
        )
        self.assertEqual(len(row), len(headers))
        self.assertFalse(any(header.endswith("\u6218\u529b") for header in headers))
        json_entry = exporter._roster_json_entry(
            entry, include_power=False, include_stat_levels=False
        )
        self.assertFalse(any(key.endswith("\u6218\u529b") for key in json_entry))

    def test_arena_detail_keeps_numeric_or_empty_values(self):
        row = exporter._row(
            {"attacker_power": [None, 156442, 158079, 146465, 156664]}
        )
        self.assertIsNone(row[6])
        self.assertEqual(row[8], 156442)
        lineup = exporter._lineup([], [None, 156442])
        self.assertIsNone(lineup[0]["\u6218\u529b"])
        self.assertEqual(lineup[1]["\u6218\u529b"], 156442)


if __name__ == "__main__":
    unittest.main(verbosity=2)
