# Bundled PaddleOCR Default Models

This directory contains the verified PaddleOCR 2.7.3 default inference models
required by the application's CPU and GPU OCR readers. `arena_ocr.py` passes
these folders to PaddleOCR explicitly, so ordinary OCR runs do not download
models into the user's `.paddleocr` directory.

Required model folders:

```text
whl/det/ch/ch_PP-OCRv4_det_infer/
whl/det/ml/Multilingual_PP-OCRv3_det_infer/
whl/rec/ch/ch_PP-OCRv4_rec_infer/
whl/cls/ch_ppocr_mobile_v2.0_cls_infer/
```

The first and third folders serve the main Chinese OCR reader. The multilingual
detector is required when the optional Japanese and Korean nickname readers are
initialized. Keep this directory with the CPU OCR component in every release.
