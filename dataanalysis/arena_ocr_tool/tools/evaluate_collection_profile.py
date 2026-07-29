"""Compare overseas collection classifications for a single group64 export."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from recognizer.image_splitter import split_input_image, split_match_block
from recognizer.result_parser import (
    ATTACKER_CARD_SLOT_CENTERS,
    CLIENT_PROFILE_OVERSEAS,
    DEFENDER_CARD_SLOT_CENTERS,
    _classify_collection_icon,
    _classify_collection_icon_by_color,
    _classify_collection_icon_by_direct_template,
    _overseas_collection_slot_box,
    recognize_collection_slots,
)


def _row_image(area: Image.Image, team_index: int) -> Image.Image:
    start = 0.275
    end = 0.925
    row_h = (end - start) / 5
    return area.crop(
        (
            round(area.width * 0.01),
            round(area.height * (start + (team_index - 1) * row_h)),
            round(area.width * 0.99),
            round(area.height * (start + team_index * row_h)),
        )
    )


def _classify(source: Path, source_profile: str) -> Counter[str]:
    counts: Counter[str] = Counter()
    with Image.open(source) as source_image:
        blocks = split_input_image(source_image.convert("RGB"), stage_code="group64")
        for block in blocks:
            regions = split_match_block(block.image)
            for side, area, centers in (
                ("attacker", regions.attacker_area[0], ATTACKER_CARD_SLOT_CENTERS),
                ("defender", regions.defender_area[0], DEFENDER_CARD_SLOT_CENTERS),
            ):
                for team_index in range(1, 6):
                    counts.update(
                        recognize_collection_slots(
                            _row_image(area, team_index),
                            centers,
                            side=side,
                            team_index=team_index,
                            match_index=block.match_index,
                            block_height=block.image.height,
                            source_profile=source_profile,
                            client_profile=CLIENT_PROFILE_OVERSEAS,
                        )
                    )
    return counts


def _diagnostic(source: Path, source_profile: str) -> dict[str, dict[str, int]]:
    result = {"direct": Counter(), "color": Counter(), "final": Counter()}
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
                            source_profile=source_profile,
                        )
                        icon = row.crop(box)
                        result["direct"][_classify_collection_icon_by_direct_template(icon, "overseas_2560x1440") or "None"] += 1
                        result["color"][_classify_collection_icon_by_color(icon, preserve_r_level=True)] += 1
                        result["final"][_classify_collection_icon(icon, "overseas_2560x1440")] += 1
    return {key: dict(sorted(value.items())) for key, value in result.items()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--profile", default="2560x1440")
    parser.add_argument("--diagnostic", action="store_true")
    args = parser.parse_args()
    print("baseline", dict(sorted(_classify(args.source, "").items())))
    print("profile", dict(sorted(_classify(args.source, args.profile).items())))
    if args.diagnostic:
        print("diagnostic", _diagnostic(args.source, args.profile))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
