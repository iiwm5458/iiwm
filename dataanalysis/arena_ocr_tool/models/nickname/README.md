# Offline nickname OCR models

The `japan`, `korean`, and `chinese_cht` directories contain recognition-only
PP-OCRv3 models used for player nicknames. They are loaded lazily and are not
used for lineup/card OCR. The Traditional Chinese model is used only by the
international/HK-TW nickname path; it preserves its original script and does
not convert names to Simplified Chinese.

Model sources:

- https://huggingface.co/PaddlePaddle/japan_PP-OCRv3_mobile_rec
- https://huggingface.co/PaddlePaddle/korean_PP-OCRv3_mobile_rec
- https://paddleocr.bj.bcebos.com/PP-OCRv3/multilingual/chinese_cht_PP-OCRv3_rec_infer.tar

Keep all three directories when packaging the application. Runtime recognition
is offline and does not need to download language data.
