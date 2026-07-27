from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image


@dataclass
class OCRItem:
    text: str
    bbox: list[tuple[float, float]]
    confidence: float
    region_name: str = ""


class ArenaOCRRecognizer:
    """Small wrapper around PaddleOCR/EasyOCR with a no-engine fallback."""

    _DEFAULT_MODEL_ROOT = Path(__file__).resolve().parent.parent / "models" / "paddle_default"
    _MODEL_REQUIRED_FILES = ("inference.pdmodel", "inference.pdiparams")

    def __init__(self, use_gpu: bool = False, cpu_threads: int = 0) -> None:
        self.use_gpu = use_gpu
        # NIKKE_DISABLED_OCR_CPU_THREAD_LIMIT_20260701:
        # Keep the argument for backward compatibility, but do not pass CPU
        # thread limits to PaddleOCR. Let PaddleOCR use its native defaults.
        # self.cpu_threads = max(0, int(cpu_threads))
        self.cpu_threads = 0
        self.engine_name = "none"
        self.reader: Any = None
        self.error: str | None = None
        self._runtime_error_reported = False
        self._nickname_readers: dict[str, Any | None] = {}
        self._init_engine()

    @property
    def available(self) -> bool:
        return self.reader is not None

    def _init_engine(self) -> None:
        try:
            if self.use_gpu:
                self._add_gpu_dll_directories()
            from paddleocr import PaddleOCR  # type: ignore

            model_dirs = self._default_model_dirs("ch")
            options: dict[str, Any] = {
                "use_angle_cls": True,
                "lang": "ch",
                "use_gpu": self.use_gpu,
                "show_log": False,
                "det_model_dir": str(model_dirs["det"]),
                "rec_model_dir": str(model_dirs["rec"]),
                "cls_model_dir": str(model_dirs["cls"]),
            }
            # NIKKE_DISABLED_OCR_CPU_THREAD_LIMIT_20260701:
            # if self.cpu_threads > 0:
            #     options["cpu_threads"] = self.cpu_threads
            #     if not self.use_gpu:
            #         options["enable_mkldnn"] = True
            self.reader = PaddleOCR(**options)
            self.engine_name = "paddleocr"
            return
        except Exception as exc:
            self.error = f"PaddleOCR unavailable: {exc}"

        try:
            import easyocr  # type: ignore

            self.reader = easyocr.Reader(["ch_sim", "en"], gpu=self.use_gpu, verbose=False)
            self.engine_name = "easyocr"
            return
        except Exception as exc:
            self.error = f"{self.error}; EasyOCR unavailable: {exc}" if self.error else f"EasyOCR unavailable: {exc}"

    @classmethod
    def _require_model_dir(cls, label: str, path: Path) -> Path:
        missing = [name for name in cls._MODEL_REQUIRED_FILES if not (path / name).exists()]
        if missing:
            names = ", ".join(missing)
            raise FileNotFoundError(f"Bundled PaddleOCR {label} model is incomplete: {path} ({names})")
        return path

    @classmethod
    def _default_model_dirs(cls, detector_language: str) -> dict[str, Path]:
        if detector_language == "ch":
            detector_dir = cls._DEFAULT_MODEL_ROOT / "whl" / "det" / "ch" / "ch_PP-OCRv4_det_infer"
        elif detector_language == "ml":
            detector_dir = cls._DEFAULT_MODEL_ROOT / "whl" / "det" / "ml" / "Multilingual_PP-OCRv3_det_infer"
        else:
            raise ValueError(f"Unsupported PaddleOCR detector language: {detector_language}")

        return {
            "det": cls._require_model_dir("detector", detector_dir),
            "rec": cls._require_model_dir(
                "Chinese recognizer",
                cls._DEFAULT_MODEL_ROOT / "whl" / "rec" / "ch" / "ch_PP-OCRv4_rec_infer",
            ),
            "cls": cls._require_model_dir(
                "angle classifier",
                cls._DEFAULT_MODEL_ROOT / "whl" / "cls" / "ch_ppocr_mobile_v2.0_cls_infer",
            ),
        }

    def _add_gpu_dll_directories(self) -> None:
        runtime_root = Path(sys.executable).resolve().parent.parent
        dll_dirs = (
            runtime_root / "Lib" / "site-packages" / "nvidia" / "cuda_runtime" / "bin",
            runtime_root / "Lib" / "site-packages" / "nvidia" / "cublas" / "bin",
            runtime_root / "Lib" / "site-packages" / "nvidia" / "cuda_nvrtc" / "bin",
            runtime_root / "Lib" / "site-packages" / "nvidia" / "cudnn" / "bin",
        )
        handles = getattr(self, "_gpu_dll_dir_handles", [])
        for dll_dir in dll_dirs:
            if not dll_dir.exists():
                continue
            dll_dir_text = str(dll_dir)
            if hasattr(os, "add_dll_directory"):
                try:
                    handles.append(os.add_dll_directory(dll_dir_text))
                except Exception:
                    pass
            path_parts = os.environ.get("PATH", "").split(os.pathsep)
            if dll_dir_text not in path_parts:
                os.environ["PATH"] = dll_dir_text + os.pathsep + os.environ.get("PATH", "")
        self._gpu_dll_dir_handles = handles

    def recognize_region(self, image: Image.Image, region_name: str = "") -> list[OCRItem]:
        if self.reader is None:
            return []

        import numpy as np

        rgb = image.convert("RGB")
        arr = np.array(rgb)
        try:
            if self.engine_name == "paddleocr":
                raw = self.reader.ocr(arr, cls=True)
                items: list[OCRItem] = []
                for page in raw or []:
                    for entry in page or []:
                        if not entry or len(entry) < 2:
                            continue
                        bbox = [(float(x), float(y)) for x, y in entry[0]]
                        text, conf = entry[1]
                        items.append(OCRItem(str(text), bbox, float(conf), region_name))
                return items

            if self.engine_name == "easyocr":
                raw = self.reader.readtext(arr)
                return [
                    OCRItem(str(text), [(float(x), float(y)) for x, y in bbox], float(conf), region_name)
                    for bbox, text, conf in raw
                ]
        except Exception as exc:
            if (
                os.environ.get("NIKKE_OCR_VERBOSE_RUNTIME_ERRORS", "").strip() in {"1", "true", "yes", "on"}
                and not self._runtime_error_reported
            ):
                self.error = f"OCR runtime failed during region recognition: {exc}"
                print(f"[ocr-warning] {self.error}", flush=True)
                self._runtime_error_reported = True
            return []
        return []

    def recognize_text_line(self, image: Image.Image, region_name: str = "") -> list[OCRItem]:
        """Recognize one pre-cropped horizontal text line without detection."""
        if self.reader is None:
            return []

        import numpy as np

        rgb = image.convert("RGB")
        arr = np.array(rgb)
        width, height = rgb.size
        bbox = [(0.0, 0.0), (float(width), 0.0), (float(width), float(height)), (0.0, float(height))]
        try:
            if self.engine_name == "paddleocr":
                raw = self.reader.ocr(arr, det=False, cls=False)
                items: list[OCRItem] = []
                for page in raw or []:
                    for entry in page or []:
                        if not entry or len(entry) < 2 or not isinstance(entry[0], str):
                            continue
                        items.append(OCRItem(str(entry[0]), bbox, float(entry[1]), region_name))
                return items

            if self.engine_name == "easyocr":
                raw = self.reader.readtext(arr, detail=1, paragraph=False)
                return [
                    OCRItem(str(text), [(float(x), float(y)) for x, y in item_bbox], float(conf), region_name)
                    for item_bbox, text, conf in raw
                ]
        except Exception as exc:
            if (
                os.environ.get("NIKKE_OCR_VERBOSE_RUNTIME_ERRORS", "").strip() in {"1", "true", "yes", "on"}
                and not self._runtime_error_reported
            ):
                self.error = f"OCR runtime failed during line recognition: {exc}"
                print(f"[ocr-warning] {self.error}", flush=True)
                self._runtime_error_reported = True
            return []
        return []

    def recognize_text_lines(
        self,
        images: list[Image.Image],
        region_names: list[str] | None = None,
        batch_size: int = 32,
    ) -> list[list[OCRItem]]:
        """Recognize pre-cropped text lines in one Paddle recognition batch."""
        if not images:
            return []
        names = region_names or [""] * len(images)
        if len(names) != len(images):
            raise ValueError("region_names must match images")
        if self.reader is None or self.engine_name != "paddleocr":
            return [self.recognize_text_line(image, name) for image, name in zip(images, names)]

        import numpy as np

        arrays = [np.array(image.convert("RGB")) for image in images]
        recognizer = getattr(self.reader, "text_recognizer", None)
        if recognizer is None:
            return [self.recognize_text_line(image, name) for image, name in zip(images, names)]
        previous_batch_size = getattr(recognizer, "rec_batch_num", None)
        try:
            if previous_batch_size is not None:
                recognizer.rec_batch_num = max(1, int(batch_size))
            raw, _elapsed = recognizer(arrays)
            if len(raw) != len(images):
                raise RuntimeError("PaddleOCR batch result count mismatch")
            results: list[list[OCRItem]] = []
            for image, name, entry in zip(images, names, raw):
                if not entry or len(entry) < 2:
                    results.append([])
                    continue
                width, height = image.size
                bbox = [(0.0, 0.0), (float(width), 0.0), (float(width), float(height)), (0.0, float(height))]
                results.append([OCRItem(str(entry[0]), bbox, float(entry[1]), name)])
            return results
        except Exception as exc:
            if (
                os.environ.get("NIKKE_OCR_VERBOSE_RUNTIME_ERRORS", "").strip() in {"1", "true", "yes", "on"}
                and not self._runtime_error_reported
            ):
                self.error = f"OCR runtime failed during batch line recognition: {exc}"
                print(f"[ocr-warning] {self.error}", flush=True)
                self._runtime_error_reported = True
            return [self.recognize_text_line(image, name) for image, name in zip(images, names)]
        finally:
            if previous_batch_size is not None:
                recognizer.rec_batch_num = previous_batch_size

    def _get_nickname_reader(self, language: str) -> Any | None:
        if language == "ch":
            return self.reader if self.engine_name == "paddleocr" else None
        if language in self._nickname_readers:
            return self._nickname_readers[language]

        model_dir = Path(__file__).resolve().parent.parent / "models" / "nickname" / language
        if not (model_dir / "inference.pdmodel").exists() or not (model_dir / "inference.pdiparams").exists():
            self._nickname_readers[language] = None
            return None

        try:
            from paddleocr import PaddleOCR  # type: ignore

            model_dirs = self._default_model_dirs("ml")
            options: dict[str, Any] = {
                "use_angle_cls": False,
                "lang": language,
                "use_gpu": self.use_gpu,
                "show_log": False,
                "ocr_version": "PP-OCRv3",
                "det_model_dir": str(model_dirs["det"]),
                "rec_model_dir": str(model_dir),
                "cls_model_dir": str(model_dirs["cls"]),
            }
            # NIKKE_DISABLED_OCR_CPU_THREAD_LIMIT_20260701:
            # if self.cpu_threads > 0:
            #     options["cpu_threads"] = self.cpu_threads
            #     if not self.use_gpu:
            #         options["enable_mkldnn"] = True
            reader = PaddleOCR(**options)
        except Exception:
            reader = None
        self._nickname_readers[language] = reader
        return reader

    def detect_nickname_text_boxes(self, image: Image.Image) -> list[list[tuple[float, float]]]:
        """Locate text on a nickname band without recognizing its contents.

        PaddleOCR 2.x cannot reliably run ``ocr(..., rec=False)`` because its
        internal NumPy truth check raises on a detected-box array. Calling the
        detector directly avoids that compatibility issue and lets the overseas
        nickname path crop away nearby UI before recognition.
        """
        if self.engine_name != "paddleocr":
            return []

        reader = self._get_nickname_reader("japan") or self.reader
        detector = getattr(reader, "text_detector", None)
        if detector is None:
            return []

        import numpy as np

        try:
            raw = detector(np.array(image.convert("RGB")))
            boxes = raw[0] if isinstance(raw, tuple) else raw
            if boxes is None:
                return []
            result: list[list[tuple[float, float]]] = []
            for box in boxes:
                points = [(float(point[0]), float(point[1])) for point in box]
                if len(points) >= 4:
                    result.append(points)
            return result
        except Exception:
            return []

    def recognize_nickname_candidates(
        self,
        image: Image.Image,
        region_name: str = "",
        languages: tuple[str, ...] = ("ch", "japan", "korean"),
        include_detected_chinese: bool = True,
    ) -> list[tuple[str, float, str]]:
        """Read one nickname row with the requested offline recognizers.

        The extra language models are recognition-only and loaded lazily. They
        are used solely for nickname rows, so normal lineup OCR keeps its
        existing speed and behavior.
        """
        import numpy as np

        arr = np.array(image.convert("RGB"))
        candidates: list[tuple[str, float, str]] = []

        # Keep detection-based Chinese results as a fallback for unusually
        # spaced names, then add recognition-only readings for all languages.
        if include_detected_chinese:
            for item in self.recognize_region(image, region_name):
                candidates.append((item.text, item.confidence, "ch"))

        for language in languages:
            reader = self._get_nickname_reader(language)
            if reader is None:
                continue
            try:
                raw = reader.ocr(arr, det=False, cls=False)
                for page in raw or []:
                    for entry in page or []:
                        if not entry or len(entry) < 2 or not isinstance(entry[0], str):
                            continue
                        candidates.append((str(entry[0]), float(entry[1]), language))
            except Exception:
                continue
        return candidates
