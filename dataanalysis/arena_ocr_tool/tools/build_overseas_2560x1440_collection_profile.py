"""Build the isolated collection-template profile for overseas 2560x1440 exports."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from recognizer.image_splitter import split_input_image, split_match_block
from recognizer.result_parser import (
    COLLECTION_NONE,
    _classify_collection_icon_by_color,
    _overseas_collection_slot_box,
    _collection_visual_stats,
)


PROFILE_NAME = "overseas_2560x1440"
LABELS = ("R", "R15", "SR", "SR15", "SSR", "SSR3", COLLECTION_NONE)
SAMPLES_PER_LABEL = 5


def _row_image(area: Image.Image, team_index: int) -> Image.Image:
    start = 0.275
    end = 0.925
    row_h = (end - start) / 5
    y0 = round(area.height * (start + (team_index - 1) * row_h))
    y1 = round(area.height * (start + team_index * row_h))
    return area.crop((round(area.width * 0.01), y0, round(area.width * 0.99), y1))


def _template_quality(label: str, icon: Image.Image) -> float | None:
    rgb = np.asarray(icon.convert("RGB").resize((48, 48), Image.Resampling.LANCZOS), dtype=np.uint8)
    stats = _collection_visual_stats(rgb)
    if label == COLLECTION_NONE:
        return 1.0 - stats["family_max"] if stats["family_max"] < 0.10 else None
    family = "cyan" if label.startswith("R") else "purple" if label.startswith("SR") else "orange"
    primary = stats[family]
    secondary = max(value for key, value in stats.items() if key in {"cyan", "purple", "orange"} and key != family)
    if primary < 0.10 or primary - secondary < 0.04:
        return None
    if label.endswith("15") or label == "SSR3":
        if stats["dark"] < 0.12:
            return None
    return primary - secondary + stats["active"] * 0.15


def _candidate_icons(source: Path) -> dict[str, list[tuple[float, Image.Image]]]:
    candidates: dict[str, list[tuple[float, Image.Image]]] = defaultdict(list)
    with Image.open(source) as source_image:
        blocks = split_input_image(source_image.convert("RGB"), stage_code="group64")
        for block in blocks:
            regions = split_match_block(block.image)
            for side, area in (("attacker", regions.attacker_area[0]), ("defender", regions.defender_area[0])):
                for team_index in range(1, 6):
                    row = _row_image(area, team_index)
                    for slot_index in range(1, 6):
                        box = _overseas_collection_slot_box(
                            row,
                            side=side,
                            team_index=team_index,
                            slot_index=slot_index,
                            match_index=block.match_index,
                            block_height=block.image.height,
                            source_profile="2560x1440",
                        )
                        if box is None:
                            continue
                        icon = row.crop(box).copy()
                        label = _classify_collection_icon_by_color(icon, preserve_r_level=True)
                        quality = _template_quality(label, icon)
                        if quality is not None:
                            candidates[label].append((quality, icon))
    for label in candidates:
        candidates[label].sort(key=lambda entry: entry[0], reverse=True)
    return candidates


def build(source: Path) -> Path:
    root = PROJECT_ROOT / "data" / "collection_cv_templates" / "v2_manual" / "profiles" / PROFILE_NAME
    if root.exists():
        for path in root.rglob("*.png"):
            path.unlink()
    candidates = _candidate_icons(source)
    base_root = root.parents[1]
    base_manifest = json.loads((base_root / "manifest.json").read_text(encoding="utf-8"))
    entries = [
        {
            "label": entry["label"],
            "kind": "positive",
            "path": "../../" + str(entry["path"]).replace("\\", "/"),
        }
        for entry in base_manifest.get("templates", [])
        if entry.get("kind") == "positive" and entry.get("label") in LABELS and entry.get("label") != COLLECTION_NONE
    ]
    manifest = {
        "version": 1,
        "profile": PROFILE_NAME,
        "source": source.name,
        "crop_phase": {"x": 1, "y": -2},
        "templates": entries,
    }
    (root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rows = len(LABELS)
    sheet = Image.new("RGB", (SAMPLES_PER_LABEL * 48, rows * 48), "#202020")
    for row_index, label in enumerate(LABELS):
        for column_index, (_, icon) in enumerate(candidates[label][:SAMPLES_PER_LABEL]):
            preview = icon.convert("RGB").resize((36, 38), Image.Resampling.NEAREST)
            x = column_index * 48 + 6
            y = row_index * 48 + 5
            sheet.paste(preview, (x, y))
    sheet.save(root / "template_contact_sheet.png")
    counts = {label: len(candidates[label]) for label in LABELS}
    print(json.dumps({"profile": str(root), "candidates": counts, "templates": len(entries)}, ensure_ascii=False))
    return root


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    if not args.source.exists():
        raise FileNotFoundError(args.source)
    build(args.source)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
