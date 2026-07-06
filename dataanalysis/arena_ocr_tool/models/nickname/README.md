# Offline nickname OCR models

The `japan` and `korean` directories contain recognition-only PP-OCRv3
models used for player nicknames. They are loaded lazily and are not used for
lineup/card OCR.

Model sources:

- https://huggingface.co/PaddlePaddle/japan_PP-OCRv3_mobile_rec
- https://huggingface.co/PaddlePaddle/korean_PP-OCRv3_mobile_rec

Keep both directories when packaging the application. Runtime recognition is
offline and does not need to download language data.
