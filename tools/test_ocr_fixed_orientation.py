"""Verify fixed-orientation OCR and conservative power merging without models."""

import sys
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock, patch

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "dataanalysis" / "arena_ocr_tool"))
from recognizer.arena_ocr import ArenaOCRRecognizer  # noqa: E402
from recognizer.result_parser import _merge_power_strip_value  # noqa: E402


class FixedOrientationOCRTest(unittest.TestCase):
    def setUp(self):
        self.reader = Mock()
        self.paddle_factory = Mock(return_value=self.reader)
        paddle_module = ModuleType("paddleocr")
        paddle_module.PaddleOCR = self.paddle_factory
        module_patch = patch.dict(sys.modules, {"paddleocr": paddle_module})
        model_patch = patch.object(
            ArenaOCRRecognizer,
            "_default_model_dirs",
            return_value={name: Path("unused-test-model") / name for name in ("det", "rec", "cls")},
        )
        gpu_patch = patch.object(ArenaOCRRecognizer, "_add_gpu_dll_directories")
        for mock_patch in (module_patch, model_patch, gpu_patch):
            mock_patch.start()
            self.addCleanup(mock_patch.stop)
        self.image = Image.new("RGB", (100, 20))

    def test_cpu_and_gpu_initialization_disable_angle_classifier(self):
        for use_gpu in (False, True):
            with self.subTest(use_gpu=use_gpu):
                self.paddle_factory.reset_mock()
                recognizer = ArenaOCRRecognizer(use_gpu=use_gpu)
                self.assertEqual(recognizer.engine_name, "paddleocr")
                self.assertIs(recognizer.reader, self.reader)
                self.assertFalse(self.paddle_factory.call_args.kwargs["use_angle_cls"])
                self.assertEqual(self.paddle_factory.call_args.kwargs["use_gpu"], use_gpu)
                # Keep bundled model directories explicit to avoid a network fallback.
                self.assertEqual(
                    self.paddle_factory.call_args.kwargs["cls_model_dir"],
                    str(Path("unused-test-model") / "cls"),
                )

    def test_region_recognition_disables_classification_and_preserves_text(self):
        self.reader.ocr.return_value = [
            [[[(1, 2), (90, 2), (90, 18), (1, 18)], ("X 98970", 0.99)]]
        ]
        recognizer = ArenaOCRRecognizer()
        items = recognizer.recognize_region(self.image, "power")
        self.assertEqual(len(items), 1)
        self.assertEqual((items[0].text, items[0].region_name), ("X 98970", "power"))
        self.assertEqual(self.reader.ocr.call_args.kwargs, {"cls": False})
        self.assertEqual(self.reader.ocr.call_args.args[0].shape, (20, 100, 3))

    def test_text_line_recognition_disables_detection_and_classification(self):
        self.reader.ocr.return_value = [[("98970", 0.99)]]
        recognizer = ArenaOCRRecognizer()
        items = recognizer.recognize_text_line(self.image, "power-strip")
        self.assertEqual(len(items), 1)
        self.assertEqual((items[0].text, items[0].region_name), ("98970", "power-strip"))
        self.assertEqual(self.reader.ocr.call_args.kwargs, {"det": False, "cls": False})
        self.assertEqual(items[0].bbox, [(0.0, 0.0), (100.0, 0.0), (100.0, 20.0), (0.0, 20.0)])


class ConservativePowerMergeTest(unittest.TestCase):
    def test_five_digits_cannot_fill_missing_or_replace_six_digits(self):
        self.assertIsNone(_merge_power_strip_value(None, 98970))
        self.assertEqual(_merge_power_strip_value(198970, 98970), 198970)
        self.assertEqual(_merge_power_strip_value(156442, 56442), 156442)

    def test_six_digits_can_fill_missing(self):
        self.assertEqual(_merge_power_strip_value(None, 198970), 198970)
        self.assertEqual(_merge_power_strip_value(None, 156442), 156442)

    def test_empty_candidate_does_not_erase_existing_power(self):
        for current in (98970, 198970, None):
            with self.subTest(current=current):
                self.assertEqual(_merge_power_strip_value(current, None), current)

    def test_existing_five_digits_keep_supported_same_width_updates(self):
        self.assertEqual(_merge_power_strip_value(98970, 98970), 98970)
        self.assertEqual(_merge_power_strip_value(98970, 98770), 98770)
        self.assertEqual(_merge_power_strip_value(98970, 8970), 98970)


if __name__ == "__main__":
    unittest.main(verbosity=2)
