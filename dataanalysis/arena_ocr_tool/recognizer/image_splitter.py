from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw


BBox = tuple[int, int, int, int]

OUTER_GROUP_GAP = 56
MATCH_COLUMN_GAP = 42
MATCH_ROW_GAP = 18


@dataclass
class ImageBlock:
    group_index: int
    match_index: int
    image: Image.Image
    bbox: BBox


@dataclass
class MatchRegions:
    attacker_area: tuple[Image.Image, BBox]
    center_result_area: tuple[Image.Image, BBox]
    defender_area: tuple[Image.Image, BBox]


def crop(image: Image.Image, bbox: BBox) -> Image.Image:
    return image.crop(bbox)


def classify_layout(image: Image.Image) -> str:
    w, h = image.size
    if w / max(1, h) >= 4.0:
        return "all_groups_single_match"
    if w >= 7000 and h >= 5000:
        return "all_groups"
    if h / max(1, w) >= 1.55:
        return "vertical_matches"
    if w >= 2800 and h >= 2800:
        return "single_group"
    return "single_match"


def split_input_image(
    image: Image.Image,
    layout: str = "auto",
    stage_code: str = "group64",
) -> list[ImageBlock]:
    if layout == "top8_pyramid":
        return split_top8_pyramid(image)
    if stage_code == "group32" and image.width >= 7000 and image.height >= 3000:
        return split_all_groups_image(image, matches_per_group=2, pair_orientation="horizontal")
    layout = classify_layout(image)
    if layout == "all_groups_single_match":
        return split_horizontal_matches(image, 8, gap=OUTER_GROUP_GAP)
    if layout == "all_groups":
        matches_per_group = {"group64": 4, "group32": 2, "group16": 1}.get(stage_code, 4)
        pair_orientation = "horizontal" if stage_code == "group32" else "vertical"
        return split_all_groups_image(
            image,
            matches_per_group=matches_per_group,
            pair_orientation=pair_orientation,
        )
    if layout == "vertical_matches":
        return split_vertical_matches(image, 2)
    if layout == "single_group":
        matches = {"group64": 4, "group32": 2, "group16": 1, "top8": 4, "top4": 2, "final": 1}.get(
            stage_code,
            4,
        )
        pair_orientation = "horizontal" if stage_code == "group32" else "vertical"
        return split_group_image(
            image,
            group_index=1,
            match_count=matches,
            pair_orientation=pair_orientation,
        )
    if stage_code in {"group32", "top4"}:
        return split_horizontal_matches(image, 2, gap=MATCH_COLUMN_GAP)
    return [ImageBlock(1, 1, image, (0, 0, image.width, image.height))]


def split_top8_pyramid(image: Image.Image) -> list[ImageBlock]:
    # The pyramid exporter uses three equal-height layers with a small vertical
    # gap: final (1 match), top 4 (2 matches), and top 8 (4 matches).
    layer_gap = max(1, int(round(image.height * 72 / 7062)))
    column_gap = max(1, int(round(image.width * 42 / 7470)))
    layer_height = max(1, (image.height - layer_gap * 2) // 3)
    pair_width = max(1, (image.width - column_gap * 3) // 4)
    counts = (1, 2, 4)
    blocks: list[ImageBlock] = []
    match_index = 1
    for layer_index, count in enumerate(counts):
        y0 = layer_index * (layer_height + layer_gap)
        y1 = min(image.height, y0 + layer_height)
        layer_width = count * pair_width + max(0, count - 1) * column_gap
        layer_x0 = max(0, (image.width - layer_width) // 2)
        for column in range(count):
            x0 = layer_x0 + column * (pair_width + column_gap)
            x1 = min(image.width, x0 + pair_width)
            blocks.append(ImageBlock(1, match_index, image.crop((x0, y0, x1, y1)), (x0, y0, x1, y1)))
            match_index += 1
    return blocks


def split_vertical_matches(
    image: Image.Image,
    count: int,
    group_index: int = 1,
    offset: tuple[int, int] = (0, 0),
) -> list[ImageBlock]:
    blocks: list[ImageBlock] = []
    for index in range(count):
        y0 = image.height * index // count
        y1 = image.height if index == count - 1 else image.height * (index + 1) // count
        bbox = (offset[0], y0 + offset[1], image.width + offset[0], y1 + offset[1])
        blocks.append(ImageBlock(group_index, index + 1, image.crop((0, y0, image.width, y1)), bbox))
    return blocks


def split_horizontal_matches(
    image: Image.Image,
    count: int,
    gap: int = 0,
    group_index_start: int = 1,
) -> list[ImageBlock]:
    blocks: list[ImageBlock] = []
    content_width = image.width - gap * max(0, count - 1)
    block_width = max(1, content_width // count)
    for index in range(count):
        x0 = index * (block_width + gap)
        x1 = image.width if index == count - 1 else x0 + block_width
        blocks.append(
            ImageBlock(group_index_start + index, 1, image.crop((x0, 0, x1, image.height)), (x0, 0, x1, image.height))
        )
    return blocks


def split_all_groups_image(
    image: Image.Image,
    matches_per_group: int = 4,
    pair_orientation: str = "vertical",
) -> list[ImageBlock]:
    blocks: list[ImageBlock] = []
    group_w = max(1, (image.width - OUTER_GROUP_GAP * 3) // 4)
    group_h = max(1, (image.height - OUTER_GROUP_GAP) // 2)
    for row in range(2):
        for col in range(4):
            group_index = row * 4 + col + 1
            x0 = col * (group_w + OUTER_GROUP_GAP)
            y0 = row * (group_h + OUTER_GROUP_GAP)
            x1 = image.width if col == 3 else x0 + group_w
            y1 = image.height if row == 1 else y0 + group_h
            group = image.crop((x0, y0, x1, y1))
            group_matches = split_group_image(
                group,
                group_index=group_index,
                offset=(x0, y0),
                match_count=matches_per_group,
                pair_orientation=pair_orientation,
            )
            for match in group_matches:
                blocks.append(match)
    return blocks


def split_group_image(
    image: Image.Image,
    group_index: int = 1,
    offset: tuple[int, int] = (0, 0),
    match_count: int = 4,
    pair_orientation: str = "vertical",
) -> list[ImageBlock]:
    if match_count <= 1:
        return [ImageBlock(group_index, 1, image, (offset[0], offset[1], offset[0] + image.width, offset[1] + image.height))]

    blocks: list[ImageBlock] = []
    if match_count == 2 and pair_orientation == "horizontal":
        cols, rows = 2, 1
    elif match_count == 2:
        cols, rows = 1, 2
    else:
        cols, rows = 2, 2
    cell_w = max(1, (image.width - MATCH_COLUMN_GAP * (cols - 1)) // cols)
    cell_h = max(1, (image.height - MATCH_ROW_GAP * (rows - 1)) // rows)
    for row in range(rows):
        for col in range(cols):
            match_index = row * cols + col + 1
            if match_index > match_count:
                break
            x0 = col * (cell_w + MATCH_COLUMN_GAP)
            y0 = row * (cell_h + MATCH_ROW_GAP)
            x1 = image.width if col == cols - 1 else x0 + cell_w
            y1 = image.height if row == rows - 1 else y0 + cell_h
            bbox = (x0 + offset[0], y0 + offset[1], x1 + offset[0], y1 + offset[1])
            blocks.append(ImageBlock(group_index, match_index, image.crop((x0, y0, x1, y1)), bbox))
    return blocks


def split_match_block(match_image: Image.Image) -> MatchRegions:
    w, h = match_image.size
    left_x1 = int(w * 0.43)
    center_x0 = int(w * 0.43)
    center_x1 = int(w * 0.57)
    right_x0 = int(w * 0.57)
    return MatchRegions(
        attacker_area=(match_image.crop((0, 0, left_x1, h)), (0, 0, left_x1, h)),
        center_result_area=(match_image.crop((center_x0, 0, center_x1, h)), (center_x0, 0, center_x1, h)),
        defender_area=(match_image.crop((right_x0, 0, w, h)), (right_x0, 0, w, h)),
    )


def save_debug_image(source: Image.Image, blocks: list[ImageBlock], output_dir: Path, stem: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    canvas = source.copy()
    draw = ImageDraw.Draw(canvas)
    for block in blocks:
        draw.rectangle(block.bbox, outline=(255, 70, 70), width=8)
        draw.text((block.bbox[0] + 10, block.bbox[1] + 10), f"G{block.group_index} M{block.match_index}", fill=(255, 70, 70))
    path = output_dir / f"{stem}_blocks_debug.png"
    canvas.save(path)
    return path


def save_match_debug(block: ImageBlock, regions: MatchRegions, output_dir: Path, stem: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    canvas = block.image.copy()
    draw = ImageDraw.Draw(canvas)
    boxes = [
        ("attacker", regions.attacker_area[1], (60, 210, 255)),
        ("center", regions.center_result_area[1], (255, 210, 60)),
        ("defender", regions.defender_area[1], (255, 90, 180)),
    ]
    for label, bbox, color in boxes:
        draw.rectangle(bbox, outline=color, width=4)
        draw.text((bbox[0] + 6, bbox[1] + 6), label, fill=color)
    path = output_dir / f"{stem}_g{block.group_index:02d}_m{block.match_index:02d}_debug.png"
    canvas.save(path)
    return path
