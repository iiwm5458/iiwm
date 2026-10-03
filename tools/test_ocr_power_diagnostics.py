"""Pure power-log regressions; no OCR model is initialized."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "dataanalysis" / "arena_ocr_tool"))

from recognizer.arena_ocr import OCRItem
from recognizer.image_splitter import ImageBlock
from recognizer.logger import RunLogger
from recognizer import result_parser as parser


def raw_item(text: str, confidence: float = 0.99, x: float = 0.172, y: float = 0.76) -> OCRItem:
    return OCRItem(text, [(x * 1000 - 20, y * 100 - 4), (x * 1000 + 20, y * 100 - 4),
                          (x * 1000 + 20, y * 100 + 4), (x * 1000 - 20, y * 100 + 4)], confidence)


def diagnostic(**overrides) -> dict:
    item = {
        "side": "defender", "team": 5, "slot": 1,
        "initial": None, "row_raw": [], "refinement_attempted": True,
        "refined": None, "refined_support": 0.0, "before_strip": None,
        "strip_attempted": True, "strip_native_raw": [], "strip_prepared_raw": [],
        "strip_native_candidate": None, "strip_prepared_candidate": None,
        "strip_candidate": None, "final": None,
    }
    item.update(overrides)
    return item


class FakeStripOCR:
    def __init__(self):
        self.calls = 0

    def recognize_text_lines(self, images, region_names, batch_size=32):
        self.calls += 1
        native = [("X98970", 0.946801), ("X156442", 0.99), ("X158079", 0.95), None, None]
        prepared = [("X98970", 0.982349), ("X156442", 0.98), ("X158070", 0.96), None, None]
        values = native if self.calls == 1 else prepared
        return [[raw_item(*value)] if value is not None else [] for value in values]


class PowerDiagnosticTests(unittest.TestCase):
    def test_below_range_raw_survives_same_slot_geometry(self):
        bad = raw_item("04686 XX", 0.740736)
        next_slot = raw_item("X156442", 0.944427, x=parser.DEFENDER_POWER_SLOT_CENTERS[1])
        outside = raw_item("X98970", y=0.40)
        evidence = parser._power_row_diagnostic_raw(
            [bad, next_slot, outside], 1000, 100, parser.DEFENDER_POWER_SLOT_CENTERS
        )
        self.assertEqual(len(evidence[0]), 1)
        self.assertEqual(evidence[0][0]["text"], "04686 XX")
        self.assertEqual(evidence[0][0]["confidence"], 0.740736)
        self.assertEqual(evidence[0][0]["candidates"], [])
        self.assertEqual(evidence[0][0]["rejected"], [{"value": 4686, "reason": "below_minimum"}])
        self.assertEqual(evidence[1][0]["candidates"], [156442])

    def test_strip_evidence_keeps_both_reads_without_extra_ocr(self):
        ocr = FakeStripOCR()
        evidence = []
        values = parser._recognize_power_strip_rows(
            [Image.new("RGB", (1000, 100), "white")],
            parser.DEFENDER_POWER_SLOT_CENTERS, ocr, "defender", diagnostics=evidence
        )
        self.assertEqual(ocr.calls, 2)
        self.assertEqual(values, [[98970, 156442, None, None, None]])
        self.assertEqual(evidence[0]["strip_native_raw"][0]["confidence"], 0.946801)
        self.assertEqual(evidence[0]["strip_prepared_raw"][0]["confidence"], 0.982349)
        self.assertEqual(evidence[2]["strip_native_candidate"], 158079)
        self.assertEqual(evidence[2]["strip_prepared_candidate"], 158070)

    def test_missing_five_digit_logs_actual_rejection_and_context(self):
        item = diagnostic(
            row_raw=parser._power_diagnostic_raw([raw_item("04686 XX", 0.740736)]),
            strip_native_raw=parser._power_diagnostic_raw([raw_item("X98970", 0.946801)]),
            strip_prepared_raw=parser._power_diagnostic_raw([raw_item("X98970", 0.982349)]),
            strip_native_candidate=98970, strip_prepared_candidate=98970, strip_candidate=98970,
        )
        original = json.dumps(item, ensure_ascii=False, sort_keys=True)
        with tempfile.TemporaryDirectory() as temp:
            logger = RunLogger(Path(temp))
            block = ImageBlock(3, 1, Image.new("RGB", (10, 10)), (0, 0, 10, 10))
            teams = [[""] * 5 for _ in range(5)]
            teams[4][0] = "波莉"
            parser._emit_power_anomalies([item], {"defender": teams}, {"defender": "00775198"},
                                         block, "国服源图.png", "64进32", logger.warning)
            lines = logger.save().read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)
        payload = json.loads(lines[0].removeprefix("[WARN] power_anomaly="))
        self.assertEqual(payload["player_id"], "00775198")
        self.assertEqual((payload["group"], payload["match"], payload["team"], payload["slot"]), (3, 1, 5, 1))
        self.assertEqual(payload["name"], "波莉")
        self.assertEqual(payload["source_image"], "国服源图.png")
        self.assertIn("strip_empty_fill_requires_six_digits", payload["rejection_reasons"])
        self.assertIn("row_numbers_outside_allowed_range", payload["rejection_reasons"])
        self.assertEqual(json.dumps(item, ensure_ascii=False, sort_keys=True), original)

    def test_normal_recovered_and_empty_slots_are_silent(self):
        self.assertIsNone(parser._power_anomaly_payload(diagnostic(
            initial=156442, before_strip=156442, final=156442,
            strip_native_candidate=156442, strip_prepared_candidate=156442, strip_candidate=156442), "德雷克"))
        self.assertIsNone(parser._power_anomaly_payload(diagnostic(
            refined=98970, before_strip=98970, final=98970,
            strip_native_candidate=98970, strip_prepared_candidate=98970, strip_candidate=98970), "波莉"))
        self.assertIsNone(parser._power_anomaly_payload(diagnostic(), ""))

    def test_real_conflict_and_disabled_strip_are_distinguished(self):
        conflict = parser._power_anomaly_payload(diagnostic(
            initial=156442, before_strip=156442, final=156442,
            strip_native_candidate=56442, strip_prepared_candidate=56442, strip_candidate=56442), "德雷克")
        self.assertEqual(conflict["issue"], "candidate_conflict")
        self.assertIn("resolved_strip_disagreement", conflict["conflicts"])
        self.assertIn("strip_shorter_candidate_ignored", conflict["rejection_reasons"])
        disabled = parser._power_anomaly_payload(diagnostic(strip_attempted=False), "波莉")
        self.assertNotIn("strip_no_agreed_candidate", disabled["rejection_reasons"])

    def test_unselected_refinement_and_high_risk_missing_have_reasons(self):
        kept = parser._power_anomaly_payload(diagnostic(
            initial=220000, refined=150000, refined_support=2.0, before_strip=220000,
            strip_attempted=False, final=220000), "波莉")
        self.assertIn("refined_candidate_not_selected_by_existing_rules", kept["rejection_reasons"])
        missing = parser._power_anomaly_payload(diagnostic(initial=350000, strip_attempted=False), "波莉")
        self.assertIn("high_risk_initial_not_confirmed", missing["rejection_reasons"])


if __name__ == "__main__":
    unittest.main()
