"""Regression checks for the three seasonal lineup snapshot exports."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "ocr_snapshot_exporter_test",
    ROOT / "dataanalysis" / "arena_ocr_tool" / "recognizer" / "exporter.py",
)
exporter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(exporter)


def roster_entry(name: str, player_id: str) -> dict:
    return {
        "nickname": name,
        "player_id": player_id,
        "group_index": 1,
        "match_index": 1,
        "side": "attacker",
        "teams": {1: ["爱丽丝", "红莲", "桃乐丝", "诺雅", "波莉"]},
        "powers": {1: [100001, 100002, 100003, 100004, 100005]},
        "collections": {1: ["无"] * 5},
        "stat_levels": [1] * 8,
    }


class SeasonalSnapshotExportTest(unittest.TestCase):
    def test_full_season_creates_three_named_roster_sheets_and_json_files(self):
        promotion = {"p": roster_entry("晋级选手", "000001")}
        top8 = {"t": roster_entry("八强选手", "000002")}
        final = {"f": roster_entry("决赛选手", "000003")}
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            excel_path = exporter.export_excel(
                [],
                output_dir,
                "season",
                roster=promotion,
                top8_roster=top8,
                final_roster=final,
            )
            exporter.export_json(
                [],
                output_dir,
                "season",
                roster=promotion,
                top8_roster=top8,
                final_roster=final,
            )

            from openpyxl import load_workbook

            workbook = load_workbook(excel_path)
            self.assertEqual(
                workbook.sheetnames,
                ["ArenaData", "晋级赛阵容", "8强阵容", "决赛阵容"],
            )
            self.assertEqual(workbook["晋级赛阵容"].cell(2, 2).value, "000001")
            self.assertEqual(workbook["8强阵容"].cell(2, 2).value, "000002")
            self.assertEqual(workbook["决赛阵容"].cell(2, 2).value, "000003")
            for suffix, expected_name in (
                ("roster", "晋级选手"),
                ("top8_roster", "八强选手"),
                ("final_roster", "决赛选手"),
            ):
                data = json.loads((output_dir / f"season_{suffix}.json").read_text(encoding="utf-8"))
                self.assertEqual(data[0]["参赛选手"], expected_name)

    def test_top8_only_keeps_explicit_missing_promotion_note(self):
        top8 = {"t": roster_entry("八强选手", "000002")}
        final = {"f": roster_entry("决赛选手", "000003")}
        note = "未提供64进32截图，无法生成晋级赛阵容"
        with tempfile.TemporaryDirectory() as temp_dir:
            excel_path = exporter.export_excel(
                [],
                Path(temp_dir),
                "top8_only",
                top8_roster=top8,
                final_roster=final,
                roster_note=note,
            )
            from openpyxl import load_workbook

            workbook = load_workbook(excel_path)
            self.assertEqual(
                workbook.sheetnames,
                ["ArenaData", "晋级赛阵容", "8强阵容", "决赛阵容"],
            )
            promotion_sheet = workbook["晋级赛阵容"]
            self.assertEqual(promotion_sheet.cell(2, 1).value, note)
            self.assertEqual(promotion_sheet.max_row, 2)
            self.assertEqual(workbook["8强阵容"].max_row, 2)
            self.assertEqual(workbook["决赛阵容"].max_row, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
