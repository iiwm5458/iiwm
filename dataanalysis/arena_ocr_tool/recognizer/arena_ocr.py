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

            options = {
                "use_angle_cls": True,
                "lang": "ch",
                "use_gpu": self.use_gpu,
                "show_log": False,
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

            options: dict[str, Any] = {
                "use_angle_cls": False,
                "lang": language,
                "use_gpu": self.use_gpu,
                "show_log": False,
                "ocr_version": "PP-OCRv3",
                "rec_model_dir": str(model_dir),
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

    def recognize_nickname_candidates(self, image: Image.Image, region_name: str = "") -> list[tuple[str, float, str]]:
        """Read one nickname row with Chinese, Japanese and Korean recognizers.

        The extra language models are recognition-only and loaded lazily. They
        are used solely for nickname rows, so normal lineup OCR keeps its
        existing speed and behavior.
        """
        import numpy as np

        arr = np.array(image.convert("RGB"))
        candidates: list[tuple[str, float, str]] = []

        # Keep detection-based Chinese results as a fallback for unusually
        # spaced names, then add recognition-only readings for all languages.
        for item in self.recognize_region(image, region_name):
            candidates.append((item.text, item.confidence, "ch"))

        for language in ("ch", "japan", "korean"):
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
