Collection CV Template Library v1
=================================

Purpose
-------

This directory stores the first OpenCV-ready template set for NIKKE arena
collection icons. It is separate from the older color-threshold fallback
templates so the next recognizer can be developed and tested without changing
the current production path.

Layout
------

- `templates_full/<label>/`: normalized 96x96 crops that keep most of the
  hexagon body and a little surrounding context.
- `templates_tight/<label>/`: normalized 96x96 crops using the current tight
  OCR/color crop.
- `negatives_full/none/`: same-position crops where no collection icon is
  equipped.
- `negatives_tight/none/`: tight negative crops.
- `contact_sheets/`: visual QA sheets for quick inspection.
- `manifest.json`: source metadata for every template crop.

Labels
------

Positive labels: `R`, `SR`, `SR15`, `SSR`, `SSR15`.

Negative label: `none`.

Sources
-------

The first version combines:

- User-provided single-card examples.
- The 3440-wide 64-to-32 detailed battle image set.
- The 1920x1080 64-to-32 detailed battle image set.

Notes
-----

The full crops may include a small edge of the nearby role icon because the
game UI places these icons very close together. The planned OpenCV recognizer
should use a mask or foreground weighting so only the collection hexagon body
dominates the score.
