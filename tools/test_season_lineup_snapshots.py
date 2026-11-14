"""Regression coverage for overseas TOP8/final lineup snapshot routing."""

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
OCR_ROOT = ROOT / "dataanalysis" / "arena_ocr_tool"
sys.path.insert(0, str(OCR_ROOT))
SPEC = importlib.util.spec_from_file_location("season_snapshot_main", OCR_ROOT / "main.py")
main = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(main)


class Logger:
    def __init__(self):
        self.infos = []
        self.warnings = []

    def info(self, message):
        self.infos.append(message)

    def warning(self, message):
        self.warnings.append(message)

    def save(self, *_args, **_kwargs):
        return Path("season_snapshot.log")


def record(
    match_index,
    round_index,
    attacker_id="00001",
    attacker_name="Raw A",
    attacker_team=None,
    defender_id="00002",
    defender_name="Raw B",
    defender_team=None,
    attacker_stat_levels=None,
    defender_stat_levels=None,
):
    return {
        "stage": main.STAGE_NAMES["top8_pyramid"],
        "group_index": 1,
        "match_index": match_index,
        "round_index": round_index,
        "attacker_player_id": attacker_id,
        "attacker_player_nickname": attacker_name,
        "attacker_team": attacker_team or [],
        "attacker_power": [100000] * 5 if attacker_team else [],
        "attacker_collection": ["无"] * 5 if attacker_team else [],
        "attacker_stat_levels": attacker_stat_levels or [],
        "defender_player_id": defender_id,
        "defender_player_nickname": defender_name,
        "defender_team": defender_team or [],
        "defender_power": [200000] * 5 if defender_team else [],
        "defender_collection": ["无"] * 5 if defender_team else [],
        "defender_stat_levels": defender_stat_levels or [],
        "winner": "attacker",
        "confidence": 1.0,
        "source_image": "TOP8-决赛全部战斗数据（详）.png",
    }


class SeasonLineupSnapshotTest(unittest.TestCase):
    def setUp(self):
        self.logger = Logger()
        self.promotion = {
            "00001": {
                "player_id": "00001",
                "nickname": "Canonical A",
                "group_index": 1,
                "match_index": 1,
                "side": "attacker",
                "teams": {1: ["Initial A"]},
                "powers": {1: [111111] * 5},
                "collections": {1: ["无"] * 5},
                "stat_levels": [1] * 8,
            },
            "00002": {
                "player_id": "00002",
                "nickname": "Canonical B",
                "group_index": 1,
                "match_index": 1,
                "side": "defender",
                "teams": {1: ["Initial B"]},
                "powers": {1: [222222] * 5},
                "collections": {1: ["无"] * 5},
                "stat_levels": [2] * 8,
            },
        }

    def test_top8_snapshot_keeps_canonical_identity_and_new_lineup(self):
        records = [
            record(
                4,
                round_index,
                attacker_name="OCR typo A",
                attacker_team=[f"Top8 A{round_index}"],
                defender_team=[f"Top8 B{round_index}"],
            )
            for round_index in range(1, 6)
        ]
        snapshot = main.build_lineup_snapshot(records, self.promotion, self.logger, "top8")

        self.assertEqual(set(snapshot), {"00001", "00002"})
        self.assertEqual(snapshot["00001"]["nickname"], "Canonical A")
        self.assertEqual(snapshot["00001"]["stat_levels"], [1] * 8)
        self.assertEqual(snapshot["00001"]["teams"][3], ["Top8 A3"])
        self.assertEqual(snapshot["00002"]["teams"][5], ["Top8 B5"])

    def test_top4_uses_top8_snapshot_and_final_uses_final_snapshot(self):
        top8_records = [
            record(
                4,
                round_index,
                attacker_team=[f"Top8 A{round_index}"],
                defender_team=[f"Top8 B{round_index}"],
            )
            for round_index in range(1, 6)
        ]
        top8_snapshot = main.build_lineup_snapshot(
            top8_records, self.promotion, self.logger, "top8"
        )

        top4_records = [record(2, 2, attacker_team=["Wrong A"], defender_team=["Wrong B"])]
        main.enrich_records_from_roster(top4_records, top8_snapshot, self.logger)
        self.assertEqual(top4_records[0]["attacker_team"], ["Top8 A2"])
        self.assertEqual(top4_records[0]["defender_team"], ["Top8 B2"])
        self.assertEqual(top4_records[0]["attacker_stat_levels"], [1] * 8)

        final_records = [
            record(
                1,
                round_index,
                attacker_team=[f"Final A{round_index}"],
                defender_team=[f"Final B{round_index}"],
            )
            for round_index in range(1, 6)
        ]
        final_snapshot = main.build_lineup_snapshot(
            final_records, top8_snapshot, self.logger, "final"
        )
        main.enrich_records_from_roster(final_records, final_snapshot, self.logger)
        self.assertEqual(final_records[2]["attacker_team"], ["Final A3"])
        self.assertEqual(final_records[2]["defender_team"], ["Final B3"])
        self.assertEqual(final_records[2]["attacker_stat_levels"], [1] * 8)

    def test_unmatched_snapshot_does_not_fall_back_to_old_lineup(self):
        records = [
            record(
                4,
                round_index,
                attacker_id="99999",
                attacker_name="New A",
                attacker_team=[f"New A{round_index}"],
            )
            for round_index in range(1, 6)
        ]
        snapshot = main.build_lineup_snapshot(records, self.promotion, self.logger, "top8")
        self.assertEqual(snapshot["99999"]["teams"][4], ["New A4"])
        self.assertTrue(any("top8_snapshot_player_unmatched" in item for item in self.logger.warnings))

        main.enrich_records_from_roster(records, snapshot, self.logger, warning_context="top8")
        self.assertEqual(records[3]["attacker_team"], ["New A4"])
        self.assertNotEqual(records[3]["attacker_team"], ["Initial A"])

    def test_pyramid_layer_policy_and_routing_are_fixed(self):
        self.assertTrue(main.top8_pyramid_needs_lineup(SimpleNamespace(match_index=1)))
        self.assertFalse(main.top8_pyramid_needs_lineup(SimpleNamespace(match_index=2)))
        self.assertFalse(main.top8_pyramid_needs_lineup(SimpleNamespace(match_index=3)))
        self.assertTrue(main.top8_pyramid_needs_lineup(SimpleNamespace(match_index=4)))
        self.assertTrue(main.top8_pyramid_needs_stat_levels(SimpleNamespace(match_index=4), True))
        self.assertFalse(main.top8_pyramid_needs_stat_levels(SimpleNamespace(match_index=1), True))

        records = [record(match_index, 1) for match_index in range(1, 8)]
        self.assertEqual([r["match_index"] for r in main.top8_pyramid_records(records, "final")], [1])
        self.assertEqual([r["match_index"] for r in main.top8_pyramid_records(records, "top4")], [2, 3])
        self.assertEqual([r["match_index"] for r in main.top8_pyramid_records(records, "top8")], [4, 5, 6, 7])

    def test_only_complete_season_or_top8_only_is_allowed(self):
        specs = [(code, Path(f"{code}.png"), code) for code, _, _ in main.SEASON_IMAGE_SPECS]
        self.assertEqual(main.classify_season_image_specs(specs), "full")
        self.assertEqual(main.classify_season_image_specs([specs[-1]]), "top8_only")
        self.assertEqual(main.classify_season_image_specs(specs[:2]), "")

    def test_full_season_run_passes_three_snapshots_to_exporter(self):
        promotion_records = [
            record(
                1,
                round_index,
                attacker_name="Canonical A",
                defender_name="Canonical B",
                attacker_team=[f"Initial A{round_index}"],
                defender_team=[f"Initial B{round_index}"],
                attacker_stat_levels=[1] * 8,
                defender_stat_levels=[2] * 8,
            )
            for round_index in range(1, 6)
        ]
        for item in promotion_records:
            item["stage"] = main.STAGE_NAMES["group64"]
        top8_records = []
        for match_index in (1, 2, 4):
            for round_index in range(1, 6):
                top8_records.append(
                    record(
                        match_index,
                        round_index,
                        attacker_team=[
                            f"{'Final' if match_index == 1 else 'Top8' if match_index == 4 else 'Wrong'} A{round_index}"
                        ],
                        defender_team=[
                            f"{'Final' if match_index == 1 else 'Top8' if match_index == 4 else 'Wrong'} B{round_index}"
                        ],
                    )
                )
        # In the real run the middle TOP4 blocks skip lineup OCR.  Model that
        # directly here so enrich_records_from_roster must supply Top8 values.
        for item in top8_records:
            if item["match_index"] == 2:
                item["attacker_team"] = []
                item["defender_team"] = []
                item["attacker_power"] = []
                item["defender_power"] = []
                item["attacker_collection"] = []
                item["defender_collection"] = []

        stage_results = {
            "group64": promotion_records,
            "group32": [],
            "group16": [],
            "top8_pyramid": top8_records,
        }

        def fake_recognize(args, image_path, stage_code, *_args, **_kwargs):
            return stage_results[stage_code], 1, False

        args = SimpleNamespace(
            progress_file=None,
            no_stat_levels=False,
            no_power=False,
            no_collection=False,
            debug=False,
            client_profile="overseas",
            control_file=None,
            cooldown_sleep=0,
            thermal_mode="safe",
        )
        specs = [(code, Path(f"{code}.png"), code) for code, _, _ in main.SEASON_IMAGE_SPECS]
        captured = {}

        def capture_json(*call_args, **kwargs):
            captured["json"] = {"records": call_args[0], **kwargs}
            return Path("x.json")

        def capture_excel(*call_args, **kwargs):
            captured["excel"] = {"records": call_args[0], **kwargs}
            return Path("x.xlsx")

        with tempfile.TemporaryDirectory() as temp_dir, \
             patch.object(main, "initialize_ocr", return_value=(object(), object())), \
             patch.object(main, "recognize_image_records", side_effect=fake_recognize), \
             patch.object(main, "export_json", side_effect=capture_json), \
             patch.object(main, "export_excel", side_effect=capture_excel):
            exit_code = main.run_season_images(
                args, specs, Path(temp_dir), self.logger, OCR_ROOT
            )

        self.assertEqual(exit_code, 0)
        exported = captured["excel"]
        self.assertEqual(exported["roster"]["00001"]["nickname"], "Canonical A")
        self.assertEqual(exported["top8_roster"]["00001"]["teams"][2], ["Top8 A2"])
        self.assertEqual(exported["final_roster"]["00001"]["teams"][3], ["Final A3"])
        top4_record = next(
            item for item in exported["records"] if item["match_index"] == 2 and item["round_index"] == 2
        )
        self.assertEqual(top4_record["attacker_team"], ["Top8 A2"])
        self.assertEqual(top4_record["attacker_stat_levels"], [1] * 8)

    def test_top8_only_run_bootstraps_identity_from_bottom_layer(self):
        source_records = []
        for match_index in (1, 2, 4):
            for round_index in range(1, 6):
                label = "Final" if match_index == 1 else "Top8" if match_index == 4 else "Wrong"
                source_records.append(
                    record(
                        match_index,
                        round_index,
                        attacker_team=[f"{label} A{round_index}"] if match_index != 2 else [],
                        defender_team=[f"{label} B{round_index}"] if match_index != 2 else [],
                        attacker_stat_levels=[9] * 8 if match_index == 1 else [1] * 8,
                        defender_stat_levels=[8] * 8 if match_index == 1 else [2] * 8,
                    )
                )

        policy_calls = []

        def fake_recognize(*call_args, **kwargs):
            policy_calls.append(kwargs)
            return source_records, 7, False

        args = SimpleNamespace(
            progress_file=None,
            no_stat_levels=False,
            no_power=False,
            no_collection=False,
            debug=False,
            client_profile="overseas",
            control_file=None,
            cooldown_sleep=0,
            thermal_mode="safe",
        )
        captured = {}

        def capture_export(kind):
            def save(call_args, kwargs):
                captured[kind] = {"records": call_args[0], **kwargs}
                return Path(f"{kind}.out")
            return save

        with tempfile.TemporaryDirectory() as temp_dir, \
             patch.object(main, "initialize_ocr", return_value=(object(), object())), \
             patch.object(main, "recognize_image_records", side_effect=fake_recognize), \
             patch.object(main, "export_json", side_effect=lambda *a, **kw: capture_export("json")(a, kw)), \
             patch.object(main, "export_excel", side_effect=lambda *a, **kw: capture_export("excel")(a, kw)):
            exit_code = main.run_season_images(
                args,
                [("top8_pyramid", Path("top8.png"), "TOP8")],
                Path(temp_dir),
                self.logger,
                OCR_ROOT,
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(policy_calls), 1)
        self.assertTrue(policy_calls[0]["lineup_selector"](SimpleNamespace(match_index=4)))
        self.assertFalse(policy_calls[0]["lineup_selector"](SimpleNamespace(match_index=2)))
        self.assertTrue(policy_calls[0]["stat_level_selector"](SimpleNamespace(match_index=4)))
        self.assertFalse(policy_calls[0]["stat_level_selector"](SimpleNamespace(match_index=1)))

        exported = captured["excel"]
        self.assertEqual(exported["roster"], {})
        self.assertEqual(exported["roster_note"], "未提供64进32截图，无法生成晋级赛阵容")
        self.assertEqual(exported["top8_roster"]["00001"]["stat_levels"], [1] * 8)
        self.assertEqual(exported["final_roster"]["00001"]["stat_levels"], [1] * 8)
        top4_record = next(
            item for item in exported["records"] if item["match_index"] == 2 and item["round_index"] == 5
        )
        self.assertEqual(top4_record["attacker_team"], ["Top8 A5"])
        final_record = next(
            item for item in exported["records"] if item["match_index"] == 1 and item["round_index"] == 5
        )
        self.assertEqual(final_record["attacker_team"], ["Final A5"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
