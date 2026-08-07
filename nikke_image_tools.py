"""Small image utilities used by both NIKKE C ARENA GUI editions."""

from __future__ import annotations

# [utf8-hex] 656E3D576F726C64205065616365

import argparse
from io import BytesIO
import json
import math
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageOps


Image.MAX_IMAGE_PIXELS = None
SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg"}
MAX_ANNOTATION_PIXELS = 250_000_000
JPEG_MAX_DIMENSION = 65_500
ROUND_ROBIN_TILE_FRAME_MARGIN = 33
ROUND_ROBIN_TILE_LABEL_HEIGHT = 64
ROUND_ROBIN_TILE_LABEL_SCALE = 8
ROUND_ROBIN_BACKGROUND_COLORS = {
    "white": (255, 255, 255),
    "pink": (255, 240, 246),
    "blue": (41, 199, 255),
    "black": (0, 0, 0),
    "ivory": (255, 246, 229),
}
STITCH_BACKGROUND_COLORS = {
    "white": (255, 255, 255),
    "pink": (255, 240, 246),
    "blue": (41, 199, 255),
    "black": (0, 0, 0),
    "ivory": (255, 246, 229),
}
STITCH_BACKGROUND_OPTIONS = (*STITCH_BACKGROUND_COLORS, "transparent", "custom")
CUSTOM_STITCH_CONTENT_OPACITY = 0.86

OUTER_GROUP_GAP = 56
MATCH_COLUMN_GAP = 42
MATCH_ROW_GAP = 18
# Four-pair GROUP blocks are assembled with the same 42px stage gap on both
# axes; two-pair GROUP blocks use the normal 18px vertical gap.
MATCH_STAGE_ROW_GAP = 42

# The detailed-result panel differs slightly between client builds.  Each
# profile is intentionally keyed by client and screenshot resolution so later
# calibration can adjust one target without shifting another.
DETAIL_ANNOTATION_PROFILES = {
    "cn": {
        "default": {"attacker": (0.4025, 0.004, 0.4980, 0.196), "defender": (0.5020, 0.004, 0.5985, 0.196)},
        "1920x1080": {"attacker": (0.4025, 0.004, 0.4980, 0.196), "defender": (0.5020, 0.004, 0.5985, 0.196)},
        "2560x1440": {"attacker": (0.4025, 0.004, 0.4980, 0.196), "defender": (0.5020, 0.004, 0.5985, 0.196)},
        "3440x1440": {"attacker": (0.4025, 0.004, 0.4980, 0.196), "defender": (0.5020, 0.004, 0.5985, 0.196)},
        "3840x2160": {"attacker": (0.4025, 0.004, 0.4980, 0.196), "defender": (0.5020, 0.004, 0.5985, 0.196)},
        "2560x1600": {"attacker": (0.4025, 0.004, 0.4980, 0.196), "defender": (0.5020, 0.004, 0.5985, 0.196)},
    },
    "overseas": {
        "default": {"attacker": (0.3955, 0.004, 0.4980, 0.196), "defender": (0.5020, 0.004, 0.6045, 0.196)},
        "1920x1080": {"attacker": (0.3955, 0.004, 0.4980, 0.196), "defender": (0.5020, 0.004, 0.6045, 0.196)},
        "2560x1440": {"attacker": (0.3955, 0.004, 0.4980, 0.196), "defender": (0.5020, 0.004, 0.6045, 0.196)},
        "3440x1440": {"attacker": (0.3955, 0.004, 0.4980, 0.196), "defender": (0.5020, 0.004, 0.6045, 0.196)},
        "3840x2160": {"attacker": (0.3955, 0.004, 0.4980, 0.196), "defender": (0.5020, 0.004, 0.6045, 0.196)},
        "2560x1600": {"attacker": (0.3955, 0.004, 0.4980, 0.196), "defender": (0.5020, 0.004, 0.6045, 0.196)},
    },
    "hmt": {
        "default": {"attacker": (0.3955, 0.004, 0.4980, 0.196), "defender": (0.5020, 0.004, 0.6045, 0.196)},
        "1920x1080": {"attacker": (0.3955, 0.004, 0.4980, 0.196), "defender": (0.5020, 0.004, 0.6045, 0.196)},
        "2560x1440": {"attacker": (0.3955, 0.004, 0.4980, 0.196), "defender": (0.5020, 0.004, 0.6045, 0.196)},
        "3440x1440": {"attacker": (0.3955, 0.004, 0.4980, 0.196), "defender": (0.5020, 0.004, 0.6045, 0.196)},
        "3840x2160": {"attacker": (0.3955, 0.004, 0.4980, 0.196), "defender": (0.5020, 0.004, 0.6045, 0.196)},
        "2560x1600": {"attacker": (0.3955, 0.004, 0.4980, 0.196), "defender": (0.5020, 0.004, 0.6045, 0.196)},
    },
}

# Player cards and the central detailed-result panel are stitched into one
# match block.  These profiles intentionally remain separate from the OCR
# cropping profiles: this tool only decorates the two player cards and never
# alters the central detailed-result panel used by OCR.
PLAYER_PANEL_ANNOTATION_PROFILES = {
    "cn": {
        "default": {
            "attacker_panel": (0.004, 0.003, 0.398, 0.997),
            "defender_panel": (0.602, 0.003, 0.996, 0.997),
            "attacker_team": (0.008, 0.198, 0.394, 0.868),
            "defender_team": (0.606, 0.198, 0.992, 0.868),
        },
        "1920x1080": {
            "attacker_panel": (0.004, 0.003, 0.398, 0.997), "defender_panel": (0.602, 0.003, 0.996, 0.997),
            "attacker_team": (0.008, 0.198, 0.394, 0.868), "defender_team": (0.606, 0.198, 0.992, 0.868),
        },
        "2560x1440": {
            "attacker_panel": (0.004, 0.003, 0.398, 0.997), "defender_panel": (0.602, 0.003, 0.996, 0.997),
            "attacker_team": (0.008, 0.198, 0.394, 0.868), "defender_team": (0.606, 0.198, 0.992, 0.868),
        },
        "3440x1440": {
            "attacker_panel": (0.004, 0.003, 0.398, 0.997), "defender_panel": (0.602, 0.003, 0.996, 0.997),
            "attacker_team": (0.008, 0.198, 0.394, 0.868), "defender_team": (0.606, 0.198, 0.992, 0.868),
        },
        "3840x2160": {
            "attacker_panel": (0.004, 0.003, 0.398, 0.997), "defender_panel": (0.602, 0.003, 0.996, 0.997),
            "attacker_team": (0.008, 0.198, 0.394, 0.868), "defender_team": (0.606, 0.198, 0.992, 0.868),
        },
        "2560x1600": {
            "attacker_panel": (0.004, 0.003, 0.398, 0.997), "defender_panel": (0.602, 0.003, 0.996, 0.997),
            "attacker_team": (0.008, 0.198, 0.394, 0.868), "defender_team": (0.606, 0.198, 0.992, 0.868),
        },
    },
    "overseas": {
        "default": {
            "attacker_panel": (0.004, 0.003, 0.391, 0.997),
            "defender_panel": (0.609, 0.003, 0.996, 0.997),
            "attacker_team": (0.008, 0.198, 0.387, 0.868),
            "defender_team": (0.613, 0.198, 0.992, 0.868),
        },
        "1920x1080": {
            "attacker_panel": (0.004, 0.003, 0.391, 0.997), "defender_panel": (0.609, 0.003, 0.996, 0.997),
            "attacker_team": (0.008, 0.198, 0.387, 0.868), "defender_team": (0.613, 0.198, 0.992, 0.868),
        },
        "2560x1440": {
            "attacker_panel": (0.004, 0.003, 0.391, 0.997), "defender_panel": (0.609, 0.003, 0.996, 0.997),
            "attacker_team": (0.008, 0.198, 0.387, 0.868), "defender_team": (0.613, 0.198, 0.992, 0.868),
        },
        "3440x1440": {
            "attacker_panel": (0.004, 0.003, 0.391, 0.997), "defender_panel": (0.609, 0.003, 0.996, 0.997),
            "attacker_team": (0.008, 0.198, 0.387, 0.868), "defender_team": (0.613, 0.198, 0.992, 0.868),
        },
        "3840x2160": {
            "attacker_panel": (0.004, 0.003, 0.391, 0.997), "defender_panel": (0.609, 0.003, 0.996, 0.997),
            "attacker_team": (0.008, 0.198, 0.387, 0.868), "defender_team": (0.613, 0.198, 0.992, 0.868),
        },
        "2560x1600": {
            "attacker_panel": (0.004, 0.003, 0.391, 0.997), "defender_panel": (0.609, 0.003, 0.996, 0.997),
            "attacker_team": (0.008, 0.198, 0.387, 0.868), "defender_team": (0.613, 0.198, 0.992, 0.868),
        },
    },
    "hmt": {},
}
PLAYER_PANEL_ANNOTATION_PROFILES["hmt"] = {
    resolution: dict(profile)
    for resolution, profile in PLAYER_PANEL_ANNOTATION_PROFILES["overseas"].items()
}

PIXEL_GLYPHS = {
    "A": ("01110", "10001", "10001", "11111", "10001"),
    "E": ("11111", "10000", "11110", "10000", "11111"),
    "G": ("01111", "10000", "10111", "10001", "01111"),
    "I": ("111", "010", "010", "010", "111"),
    "L": ("10000", "10000", "10000", "10000", "11111"),
    "N": ("10001", "11001", "10101", "10011", "10001"),
    "O": ("01110", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "11110", "10000", "10000"),
    "R": ("11110", "10001", "11110", "10100", "10010"),
    "S": ("01111", "10000", "01110", "00001", "11110"),
    "U": ("10001", "10001", "10001", "10001", "01110"),
    "W": ("10001", "10001", "10101", "10101", "01010"),
    "0": ("01110", "10001", "10001", "10001", "01110"),
    "1": ("010", "110", "010", "010", "111"),
    "2": ("11110", "00001", "01110", "10000", "11111"),
    "3": ("11110", "00001", "01110", "00001", "11110"),
    "4": ("10010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "11110"),
    "6": ("01111", "10000", "11110", "10001", "01110"),
    "7": ("11111", "00010", "00100", "01000", "01000"),
    "8": ("01110", "10001", "01110", "10001", "01110"),
    "9": ("01110", "10001", "01111", "00001", "11110"),
    " ": ("00", "00", "00", "00", "00"),
}

# These are deliberately fixed pixel presets.  Player-card output is stitched
# to a stable 720px panel width, so marker sizing must not depend on portraits,
# title-band colours, or other live image content.
OUTCOME_LABEL_SCALES = {
    "small": 4,
    "medium": 6,
    "large": 8,
}


@dataclass(frozen=True)
class AnnotationBlock:
    group_index: int
    match_index: int
    bbox: tuple[int, int, int, int]


@dataclass(frozen=True)
class AnnotationRecord:
    source_image: str
    group_index: int
    match_index: int
    round_index: int
    winner: str
    attacker_name: str
    attacker_id: str
    defender_name: str
    defender_id: str


@dataclass(frozen=True)
class MatchOutcome:
    group_index: int
    match_index: int
    winner: str
    attacker_name: str
    attacker_id: str
    defender_name: str
    defender_id: str


@dataclass(frozen=True)
class PlayerCardLayout:
    width: int
    height: int
    lineup_top: int
    lineup_bottom: int
    label_down_shift: int


class ImageToolError(RuntimeError):
    pass


def image_path(value: str) -> Path:
    path = Path(value)
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"Image file does not exist: {path}")
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise argparse.ArgumentTypeError("Only PNG, JPG, and JPEG images are supported.")
    return path


def output_directory(value: str) -> Path:
    path = Path(value)
    path.mkdir(parents=True, exist_ok=True)
    return path


def input_directory(value: str) -> Path:
    path = Path(value)
    if not path.is_dir():
        raise argparse.ArgumentTypeError(f"Image folder does not exist: {path}")
    return path


def unique_output_path(directory: Path, filename: str) -> Path:
    candidate = directory / filename
    if not candidate.exists():
        return candidate

    for index in range(2, 1000):
        alternate = candidate.with_stem(f"{candidate.stem}-{index}")
        if not alternate.exists():
            return alternate
    return candidate.with_stem(f"{candidate.stem}-{datetime.now():%H%M%S}")


def load_image(path: Path, mode: str) -> Image.Image:
    with Image.open(path) as opened:
        normalized = ImageOps.exif_transpose(opened)
        return normalized.convert(mode)


def flatten_to_rgb(image: Image.Image) -> Image.Image:
    if image.mode == "RGB":
        return image
    flattened = Image.new("RGB", image.size, "white")
    flattened.paste(image, mask=image.getchannel("A"))
    return flattened


COMPRESSION_MODE_LABELS = {
    "high": "高清压缩",
    "deep": "深度压缩",
    "extreme": "极限压缩",
}
EXTREME_TARGET_BYTES = 10 * 1024 * 1024


def jpeg_bytes(image: Image.Image, quality: int, subsampling: int) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=quality, subsampling=subsampling, optimize=True)
    return buffer.getvalue()


def scaled_size_preserving_aspect_ratio(
    width: int,
    height: int,
    scale: float,
) -> tuple[int, int]:
    """Return the nearest downscaled size while keeping the source aspect ratio."""
    target_width = max(1, round(width * scale))
    target_height = max(1, round(height * scale))
    if width <= 0 or height <= 0:
        return target_width, target_height

    # Prefer dimensions that retain the exact ratio for common screenshot sizes.
    divisor = math.gcd(width, height)
    base_width, base_height = width // divisor, height // divisor
    multiplier = max(1, min(divisor, math.floor(min(target_width / base_width, target_height / base_height))))
    exact_width, exact_height = base_width * multiplier, base_height * multiplier
    if (
        exact_width <= target_width
        and exact_height <= target_height
        and exact_width >= target_width * 0.95
        and exact_height >= target_height * 0.95
    ):
        return exact_width, exact_height
    return target_width, target_height


def extreme_jpeg_bytes(image: Image.Image) -> tuple[bytes, tuple[int, int]]:
    """Make a share-friendly JPEG that is kept near the 10 MiB target.

    This mode preserves the image's aspect ratio whenever dimensional reduction
    is necessary, so an extreme-compressed screenshot never looks stretched.
    """
    working = image
    encoded = b""
    for _ in range(4):
        encoded = jpeg_bytes(working, quality=60, subsampling=2)
        if len(encoded) <= EXTREME_TARGET_BYTES:
            return encoded, working.size
        scale = min(0.97, max(0.45, (EXTREME_TARGET_BYTES / len(encoded)) ** 0.5 * 0.96))
        resized = scaled_size_preserving_aspect_ratio(working.width, working.height, scale)
        if resized == working.size:
            break
        working = working.resize(resized, Image.Resampling.LANCZOS)

    # Keep reducing detailed source images until the compact-file target is met.
    for _ in range(4):
        encoded = jpeg_bytes(working, quality=48, subsampling=2)
        if len(encoded) <= EXTREME_TARGET_BYTES:
            return encoded, working.size
        scale = min(0.94, max(0.45, (EXTREME_TARGET_BYTES / len(encoded)) ** 0.5 * 0.96))
        resized = scaled_size_preserving_aspect_ratio(working.width, working.height, scale)
        if resized == working.size:
            break
        working = working.resize(resized, Image.Resampling.LANCZOS)
    return encoded, working.size


def compress_images(paths: list[Path], destination: Path, mode: str) -> list[Path]:
    if mode not in COMPRESSION_MODE_LABELS:
        raise ImageToolError("不支持的压缩等级。")
    outputs: list[Path] = []
    for source in paths:
        image = flatten_to_rgb(load_image(source, "RGBA"))
        width, height = image.size
        if mode == "high":
            output = unique_output_path(destination, f"{source.stem}_高清压缩_质量95_{width}x{height}.jpg")
            image.save(output, format="JPEG", quality=95, subsampling=0, optimize=True)
        elif mode == "deep":
            output = unique_output_path(destination, f"{source.stem}_深度压缩_质量78_{width}x{height}.jpg")
            image.save(output, format="JPEG", quality=78, subsampling=2, optimize=True)
        else:
            encoded, (output_width, output_height) = extreme_jpeg_bytes(image)
            output = unique_output_path(destination, f"{source.stem}_极限压缩_约10MiB_{output_width}x{output_height}.jpg")
            output.write_bytes(encoded)
        outputs.append(output)
    return outputs


def image_size(path: Path) -> tuple[int, int]:
    with Image.open(path) as opened:
        return opened.size


def stitch_images(
    paths: list[Path],
    destination: Path,
    direction: str,
    gap: int,
    background: str = "white",
    background_image: Path | None = None,
) -> Path:
    dimensions = [image_size(path) for path in paths]
    all_jpeg = all(path.suffix.lower() in {".jpg", ".jpeg"} for path in paths)
    all_png = all(path.suffix.lower() == ".png" for path in paths)
    if background not in STITCH_BACKGROUND_OPTIONS:
        background = "white"
    if background == "transparent" and not all_png:
        raise ImageToolError("透明背景仅支持全部选择 PNG 图像。")
    if background == "custom" and background_image is None:
        raise ImageToolError("未找到自定义背景图。请将 JPG 或 PNG 图片放入 custom_backgrounds 后重试。")
    if direction == "vertical":
        canvas_width = max(width for width, _ in dimensions)
        canvas_height = sum(height for _, height in dimensions) + gap * (len(paths) - 1)
    else:
        canvas_width = sum(width for width, _ in dimensions) + gap * (len(paths) - 1)
        canvas_height = max(height for _, height in dimensions)

    can_save_jpeg = (
        background != "transparent"
        and all_jpeg
        and max(canvas_width, canvas_height) <= JPEG_MAX_DIMENSION
    )
    output_mode = "RGB" if can_save_jpeg and background != "custom" else "RGBA"
    try:
        canvas_size = (canvas_width, canvas_height)
        if background == "transparent":
            canvas = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        elif background == "custom":
            custom_background = load_image(background_image, "RGBA")
            canvas = ImageOps.fit(
                custom_background,
                canvas_size,
                method=Image.Resampling.LANCZOS,
                centering=(0.5, 0.5),
            )
        else:
            fill = STITCH_BACKGROUND_COLORS[background]
            canvas = Image.new(output_mode, canvas_size, fill)

        content = Image.new("RGBA", canvas_size, (0, 0, 0, 0)) if background == "custom" else canvas
        offset = 0
        # Each source is centered on the opposite axis and pasted one at a time to limit peak memory use.
        for source, (width, height) in zip(paths, dimensions):
            image = load_image(source, "RGBA" if background == "custom" else output_mode)
            if direction == "vertical":
                position = ((canvas_width - width) // 2, offset)
                offset += height + gap
            else:
                position = (offset, (canvas_height - height) // 2)
                offset += width + gap
            if content.mode == "RGBA":
                content.alpha_composite(image, dest=position)
            else:
                content.paste(image, position)

        if background == "custom":
            alpha = content.getchannel("A").point(
                lambda value: round(value * CUSTOM_STITCH_CONTENT_OPACITY)
            )
            content.putalpha(alpha)
            canvas.alpha_composite(content)

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        direction_label = "纵向" if direction == "vertical" else "横向"
        extension = "jpg" if can_save_jpeg else "png"
        output = unique_output_path(
            destination,
            f"图像拼接_{direction_label}_{stamp}_{canvas_width}x{canvas_height}.{extension}",
        )
        if can_save_jpeg:
            canvas.convert("RGB").save(output, format="JPEG", quality=95, subsampling=0, optimize=True)
        else:
            canvas.save(output, format="PNG", optimize=True)
        return output
    except MemoryError as exc:
        raise ImageToolError(
            "图像拼接需要的内存超过当前设备可用容量。请关闭占用内存较高的程序，或改用更小的图片后重试。"
        ) from exc


ROUND_ROBIN_GROUP_FILE_PATTERN = re.compile(
    r"^group0*(?P<index>[1-9]|[1-5][0-9]|6[0-4])(?:[-_].*)?$",
    flags=re.IGNORECASE,
)


def round_robin_group_images(directory: Path) -> list[tuple[int, Path]]:
    """Return one direct-child capture per GROUP, preferring the newest retry."""
    candidates: dict[int, Path] = {}
    for path in directory.iterdir():
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        match = ROUND_ROBIN_GROUP_FILE_PATTERN.match(path.stem)
        if not match:
            continue
        group_index = int(match.group("index"))
        current = candidates.get(group_index)
        if current is None or path.stat().st_mtime > current.stat().st_mtime:
            candidates[group_index] = path
    return sorted(candidates.items(), key=lambda item: item[0])


def round_robin_background_fill(background: str, mode: str) -> tuple[int, ...]:
    color = ROUND_ROBIN_BACKGROUND_COLORS.get(background, ROUND_ROBIN_BACKGROUND_COLORS["white"])
    return color if mode == "RGB" else (*color, 255)


def paste_image(canvas: Image.Image, image: Image.Image, position: tuple[int, int]) -> None:
    if canvas.mode == "RGBA":
        canvas.alpha_composite(image, dest=position)
    else:
        canvas.paste(image, position)


def round_robin_group_tile_size(width: int, height: int, group_labels: bool) -> tuple[int, int]:
    if not group_labels:
        return width, height
    return (
        width + ROUND_ROBIN_TILE_FRAME_MARGIN * 2,
        height + ROUND_ROBIN_TILE_LABEL_HEIGHT + ROUND_ROBIN_TILE_FRAME_MARGIN * 2,
    )


def build_round_robin_group_tile(
    image: Image.Image,
    group_index: int,
    background: str,
    group_labels: bool,
) -> Image.Image:
    """Place optional GROUP chrome outside the original screenshot pixels."""
    if not group_labels:
        return image

    tile_width, tile_height = round_robin_group_tile_size(*image.size, True)
    tile = Image.new(image.mode, (tile_width, tile_height), round_robin_background_fill(background, image.mode))
    image_position = (
        ROUND_ROBIN_TILE_FRAME_MARGIN,
        ROUND_ROBIN_TILE_LABEL_HEIGHT + ROUND_ROBIN_TILE_FRAME_MARGIN,
    )
    paste_image(tile, image, image_position)

    draw = ImageDraw.Draw(tile)
    label_plate = (13, 21, 45) if tile.mode == "RGB" else (13, 21, 45, 235)
    # Reuse the chunky gradient pixel outline used by the main image-tool
    # result markers, but leave this tile without a second in-frame label.
    draw_pixel_frame(
        tile,
        (0, 0, tile_width - 1, tile_height - 1),
        (29, 192, 255),
        (225, 252, 255),
        "",
    )

    label = f"GROUP{group_index}"
    text_width = pixel_text_width(label, ROUND_ROBIN_TILE_LABEL_SCALE)
    text_height = 5 * ROUND_ROBIN_TILE_LABEL_SCALE
    text_x = max(8, (tile_width - text_width) // 2)
    text_y = max(8, (ROUND_ROBIN_TILE_LABEL_HEIGHT - text_height) // 2)
    pad_x = ROUND_ROBIN_TILE_LABEL_SCALE
    pad_y = max(4, ROUND_ROBIN_TILE_LABEL_SCALE // 2)
    draw.rounded_rectangle(
        (
            text_x - pad_x,
            text_y - pad_y,
            text_x + text_width + pad_x,
            text_y + text_height + pad_y,
        ),
        radius=4,
        fill=label_plate,
    )
    draw_pixel_text(
        tile,
        label,
        (text_x, text_y),
        ROUND_ROBIN_TILE_LABEL_SCALE,
        (177, 126, 255),
        (74, 210, 255),
    )
    return tile


def stitch_round_robin_folder(
    directory: Path,
    destination: Path,
    layout: str,
    gap: int,
    group_labels: bool,
    background: str,
) -> tuple[list[Path], list[int]]:
    sources = round_robin_group_images(directory)
    source_map = dict(sources)
    missing_groups = [group for group in range(1, 65) if group not in source_map]
    if missing_groups:
        missing_text = ", ".join(f"GROUP{group:02d}" for group in missing_groups)
        raise ImageToolError(f"所选文件夹缺少以下小组循环赛截图：{missing_text}")

    if layout not in {"vertical", "horizontal"}:
        raise ImageToolError("小组循环赛图像仅支持纵向或横向拼接。")

    all_sources = [(group_index, source_map[group_index]) for group_index in range(1, 65)]
    all_jpeg = all(path.suffix.lower() in {".jpg", ".jpeg"} for _, path in sources)
    output_mode = "RGB" if all_jpeg else "RGBA"

    try:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        layout_label = {"vertical": "纵向", "horizontal": "横向"}[layout]
        label_suffix = "_GROUP标记" if group_labels else ""
        outputs: list[Path] = []
        for batch_start in range(1, 65, 8):
            batch = all_sources[batch_start - 1 : batch_start + 7]
            dimensions = [
                (group_index, path, *round_robin_group_tile_size(*image_size(path), group_labels))
                for group_index, path in batch
            ]
            cell_width = max(width for _, _, width, _ in dimensions)
            cell_height = max(height for _, _, _, height in dimensions)
            if layout == "vertical":
                canvas_width = cell_width
                canvas_height = cell_height * len(dimensions) + gap * (len(dimensions) - 1)
            else:
                canvas_width = cell_width * len(dimensions) + gap * (len(dimensions) - 1)
                canvas_height = cell_height

            can_save_jpeg = all_jpeg and max(canvas_width, canvas_height) <= JPEG_MAX_DIMENSION
            canvas = Image.new(
                output_mode,
                (canvas_width, canvas_height),
                round_robin_background_fill(background, output_mode),
            )
            offset = 0
            for group_index, path, tile_width, tile_height in dimensions:
                image = build_round_robin_group_tile(
                    load_image(path, output_mode),
                    group_index,
                    background,
                    group_labels,
                )
                if layout == "vertical":
                    position = ((canvas_width - tile_width) // 2, offset)
                    offset += tile_height + gap
                else:
                    position = (offset, (canvas_height - tile_height) // 2)
                    offset += tile_width + gap
                paste_image(canvas, image, position)

            batch_end = batch_start + 7
            extension = "jpg" if can_save_jpeg else "png"
            output = unique_output_path(
                destination,
                (
                    f"小组循环赛图像拼接_{layout_label}_GROUP{batch_start:02d}-{batch_end:02d}"
                    f"{label_suffix}_{stamp}_{canvas_width}x{canvas_height}.{extension}"
                ),
            )
            if can_save_jpeg:
                canvas.save(output, format="JPEG", quality=95, subsampling=0, optimize=True)
            else:
                canvas.save(output, format="PNG", optimize=True)
            outputs.append(output)
        return outputs, [group_index for group_index, _ in all_sources]
    except MemoryError as exc:
        raise ImageToolError(
            "拼接图像所需内存超过当前可用容量。请关闭占用内存较高的程序，或减少本次拼接的截图数量后重试。"
        ) from exc


def data_path(value: str) -> Path:
    path = Path(value)
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"Result data file does not exist: {path}")
    if path.suffix.lower() not in {".json", ".xlsx"}:
        raise argparse.ArgumentTypeError("Only JSON and XLSX result data files are supported.")
    return path


def normalized_source_name(value: str) -> str:
    text = Path(str(value or "")).stem.casefold().replace("×", "x")
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"[_-]胜负标注(?:[_-].*)?$", "", text)
    text = re.sub(r"[_-](?:国服|国际服|港澳台)$", "", text)
    return text


def normalize_winner(value: object) -> str:
    text = str(value or "").strip().casefold()
    if text in {"attacker", "attack", "攻方", "left", "左"}:
        return "attacker"
    if text in {"defender", "defense", "守方", "right", "右"}:
        return "defender"
    return "unknown"


def parse_record_position(round_key: object) -> tuple[int, int, int]:
    text = str(round_key or "").replace(" ", "")
    group_match = re.search(r"第(\d+)组", text)
    group_index = int(group_match.group(1)) if group_match else 1
    match_round = re.search(r"M(\d+)G(\d+)", text, flags=re.IGNORECASE)
    # Championship records reuse M1/M2/M3/M4 in separate bracket layers.
    # Resolve the layer first so the seven TOP8 matches keep unique positions.
    if "冠军争霸" in text:
        round_match = re.search(r"G(\d+)", text, flags=re.IGNORECASE)
        round_index = int(round_match.group(1)) if round_match else 0
        if "冠亚军" in text or "2进1" in text:
            return 1, 1, round_index
        if "4进2" in text:
            match_index = int(match_round.group(1)) if match_round else 1
            return 1, 1 + match_index, round_index
        if "8进4" in text:
            match_index = int(match_round.group(1)) if match_round else 1
            return 1, 3 + match_index, round_index
    if match_round:
        return group_index, int(match_round.group(1)), int(match_round.group(2))

    round_match = re.search(r"G(\d+)", text, flags=re.IGNORECASE)
    round_index = int(round_match.group(1)) if round_match else 0
    if "冠亚军" in text:
        return group_index, 1, round_index
    if "2进1" in text:
        # 晋级赛的 16进8 记录为“第 N 组 2进1 Gx”；旧逻辑把它们
        # 全部硬归到第 1 组，导致只有 GROUP1 能被标记。
        return group_index, 1, round_index
    if "4进2" in text:
        match_match = re.search(r"M(\d+)", text, flags=re.IGNORECASE)
        return 1, 1 + (int(match_match.group(1)) if match_match else 1), round_index
    if "8进4" in text:
        match_match = re.search(r"M(\d+)", text, flags=re.IGNORECASE)
        return 1, 3 + (int(match_match.group(1)) if match_match else 1), round_index
    return group_index, 1, round_index


def xlsx_rows(path: Path) -> list[dict[str, str]]:
    namespace = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    with zipfile.ZipFile(path) as archive:
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in root.findall(f"{namespace}si"):
                shared_strings.append("".join(node.text or "" for node in item.iter(f"{namespace}t")))

        sheet_names = sorted(name for name in archive.namelist() if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", name))
        if not sheet_names:
            raise ImageToolError("Excel 文件中未找到战果数据工作表。")
        root = ET.fromstring(archive.read(sheet_names[0]))

    rows: list[list[str]] = []
    for row in root.findall(f".//{namespace}row"):
        values: dict[int, str] = {}
        for cell in row.findall(f"{namespace}c"):
            reference = cell.attrib.get("r", "")
            column_letters = re.match(r"[A-Z]+", reference)
            if not column_letters:
                continue
            column = 0
            for letter in column_letters.group(0):
                column = column * 26 + ord(letter) - 64
            raw_value = cell.findtext(f"{namespace}v", default="")
            if cell.attrib.get("t") == "s" and raw_value.isdigit():
                value = shared_strings[int(raw_value)] if int(raw_value) < len(shared_strings) else ""
            elif cell.attrib.get("t") == "inlineStr":
                value = "".join(node.text or "" for node in cell.iter(f"{namespace}t"))
            else:
                value = raw_value
            values[column - 1] = value
        if values:
            rows.append([values.get(index, "") for index in range(max(values) + 1)])

    if not rows:
        raise ImageToolError("Excel 文件中没有可读取的数据。")
    headers = [str(value).strip() for value in rows[0]]
    required = {"对局轮次", "胜方", "源图片"}
    if not required.issubset(set(headers)):
        raise ImageToolError("Excel 第一张工作表缺少对局轮次、胜方或源图片列。")
    return [dict(zip(headers, row)) for row in rows[1:] if any(str(value).strip() for value in row)]


def load_annotation_records(path: Path) -> list[AnnotationRecord]:
    if path.suffix.lower() == ".json":
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ImageToolError(f"无法读取 JSON 识别结果：{exc}") from exc
        if isinstance(payload, dict):
            payload = payload.get("records") or payload.get("data") or []
        if not isinstance(payload, list):
            raise ImageToolError("JSON 识别结果格式不正确。")
        rows = [item for item in payload if isinstance(item, dict)]
    else:
        try:
            rows = xlsx_rows(path)
        except (OSError, ValueError, ET.ParseError, zipfile.BadZipFile) as exc:
            raise ImageToolError(f"无法读取 Excel 识别结果：{exc}") from exc

    records: list[AnnotationRecord] = []
    for item in rows:
        source = str(item.get("源图片") or item.get("source_image") or "").strip()
        round_key = item.get("对局轮次") or item.get("round_key") or ""
        winner = normalize_winner(item.get("胜方") or item.get("winner"))
        group_index, match_index, round_index = parse_record_position(round_key)
        if not source or winner == "unknown" or round_index not in {1, 2, 3, 4, 5}:
            continue
        records.append(
            AnnotationRecord(
                source_image=source,
                group_index=group_index,
                match_index=match_index,
                round_index=round_index,
                winner=winner,
                attacker_name=str(item.get("功方选手") or item.get("attacker_name") or "").strip(),
                attacker_id=str(item.get("功方选手ID") or item.get("attacker_id") or "").strip(),
                defender_name=str(item.get("守方选手") or item.get("defender_name") or "").strip(),
                defender_id=str(item.get("守方选手ID") or item.get("defender_id") or "").strip(),
            )
        )
    if not records:
        raise ImageToolError("识别结果中没有可用于战果标记的胜负记录。")
    return records


def stage_from_filename(path: Path) -> str:
    name = path.stem.casefold().replace(" ", "")
    if "64进32" in name:
        return "group64"
    if "32进16" in name:
        return "group32"
    if "16进8" in name:
        return "group16"
    if "冠亚军" in name or "2进1" in name:
        return "final"
    if "4进2" in name or "4强" in name:
        return "top4"
    if "8进4" in name or "8强" in name:
        return "top8"
    if "top8" in name or "to8" in name or "冠军争霸" in name or "决赛" in name:
        return "top8_pyramid"
    raise ImageToolError(f"无法从文件名判断战果阶段：{path.name}")


def server_from_filename(path: Path, fallback: str) -> str:
    name = path.stem.casefold()
    if "港澳台" in name:
        return "hmt"
    if "国际服" in name:
        return "overseas"
    if "国服" in name:
        return "cn"
    return fallback if fallback in DETAIL_ANNOTATION_PROFILES else "cn"


def resolution_from_filename(path: Path) -> str:
    match = re.search(r"(?<!\d)(\d{3,5})\s*[xX×]\s*(\d{3,5})(?!\d)", path.stem)
    return f"{match.group(1)}x{match.group(2)}" if match else "default"


def add_group_blocks(
    blocks: list[AnnotationBlock],
    group_index: int,
    group_box: tuple[int, int, int, int],
    match_count: int,
    horizontal: bool,
    row_gap: int = MATCH_ROW_GAP,
) -> None:
    x0, y0, x1, y1 = group_box
    group_width = x1 - x0
    group_height = y1 - y0
    if match_count == 1:
        blocks.append(AnnotationBlock(group_index, 1, group_box))
        return
    if match_count == 2 and horizontal:
        columns, rows = 2, 1
    elif match_count == 2:
        columns, rows = 1, 2
    else:
        columns, rows = 2, 2
    cell_width = max(1, (group_width - MATCH_COLUMN_GAP * (columns - 1)) // columns)
    cell_height = max(1, (group_height - row_gap * (rows - 1)) // rows)
    for row in range(rows):
        for column in range(columns):
            match_index = row * columns + column + 1
            if match_index > match_count:
                return
            left = x0 + column * (cell_width + MATCH_COLUMN_GAP)
            top = y0 + row * (cell_height + row_gap)
            right = x1 if column == columns - 1 else left + cell_width
            bottom = y1 if row == rows - 1 else top + cell_height
            blocks.append(AnnotationBlock(group_index, match_index, (left, top, right, bottom)))


def split_annotation_blocks(size: tuple[int, int], stage: str) -> list[AnnotationBlock]:
    width, height = size
    blocks: list[AnnotationBlock] = []
    if stage in {"group64", "group32"} and width >= 7000 and height >= 3000:
        group_width = max(1, (width - OUTER_GROUP_GAP * 3) // 4)
        group_height = max(1, (height - OUTER_GROUP_GAP) // 2)
        match_count = 4 if stage == "group64" else 2
        horizontal = stage == "group32"
        for row in range(2):
            for column in range(4):
                group_index = row * 4 + column + 1
                x0 = column * (group_width + OUTER_GROUP_GAP)
                y0 = row * (group_height + OUTER_GROUP_GAP)
                x1 = width if column == 3 else x0 + group_width
                y1 = height if row == 1 else y0 + group_height
                add_group_blocks(
                    blocks,
                    group_index,
                    (x0, y0, x1, y1),
                    match_count,
                    horizontal,
                    MATCH_STAGE_ROW_GAP if stage == "group64" else MATCH_ROW_GAP,
                )
        return blocks
    if stage == "group16" and width / max(1, height) >= 4.0:
        content_width = width - OUTER_GROUP_GAP * 7
        group_width = max(1, content_width // 8)
        for index in range(8):
            x0 = index * (group_width + OUTER_GROUP_GAP)
            x1 = width if index == 7 else x0 + group_width
            blocks.append(AnnotationBlock(index + 1, 1, (x0, 0, x1, height)))
        return blocks
    if stage == "top8_pyramid":
        layer_gap = max(1, int(round(height * 72 / 7062)))
        column_gap = max(1, int(round(width * 42 / 7470)))
        layer_height = max(1, (height - layer_gap * 2) // 3)
        pair_width = max(1, (width - column_gap * 3) // 4)
        match_index = 1
        for layer_index, count in enumerate((1, 2, 4)):
            y0 = layer_index * (layer_height + layer_gap)
            y1 = min(height, y0 + layer_height)
            layer_width = count * pair_width + max(0, count - 1) * column_gap
            layer_x0 = max(0, (width - layer_width) // 2)
            for column in range(count):
                x0 = layer_x0 + column * (pair_width + column_gap)
                x1 = min(width, x0 + pair_width)
                blocks.append(AnnotationBlock(1, match_index, (x0, y0, x1, y1)))
                match_index += 1
        return blocks
    if stage == "top4":
        add_group_blocks(blocks, 1, (0, 0, width, height), 2, True)
        return blocks
    if stage == "top8":
        add_group_blocks(blocks, 1, (0, 0, width, height), 4, False)
        return blocks
    match_count = 4 if stage == "group64" else 2 if stage == "group32" else 1
    add_group_blocks(blocks, 1, (0, 0, width, height), match_count, stage == "group32")
    return blocks


def interpolate_color(start: tuple[int, int, int], end: tuple[int, int, int], fraction: float) -> tuple[int, int, int, int]:
    fraction = min(1.0, max(0.0, fraction))
    return tuple(int(round(start[index] + (end[index] - start[index]) * fraction)) for index in range(3)) + (255,)


def clamp_box(box: tuple[float, float, float, float], size: tuple[int, int]) -> tuple[int, int, int, int]:
    width, height = size
    x0, y0, x1, y1 = box
    return (
        max(0, min(width - 1, int(round(x0)))),
        max(0, min(height - 1, int(round(y0)))),
        max(1, min(width, int(round(x1)))),
        max(1, min(height, int(round(y1)))),
    )


def detail_team_box(
    block: AnnotationBlock,
    side: str,
    round_index: int,
    profile: dict[str, tuple[float, float, float, float]],
) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = block.bbox
    block_width = x1 - x0
    block_height = y1 - y0
    rel_x0, rel_y0, rel_x1, rel_y1 = profile[side]
    row_top = (round_index - 1) / 5
    row_bottom = round_index / 5
    return clamp_box(
        (
            x0 + block_width * rel_x0,
            y0 + block_height * (row_top + rel_y0),
            x0 + block_width * rel_x1,
            y0 + block_height * (row_top + rel_y1),
        ),
        (x1, y1),
    )


def pixel_text_width(text: str, scale: int) -> int:
    width = 0
    for index, char in enumerate(text):
        glyph = PIXEL_GLYPHS.get(char, PIXEL_GLYPHS[" "])
        width += len(glyph[0]) * scale
        if index < len(text) - 1:
            width += scale
    return width


def draw_pixel_text(
    image: Image.Image,
    text: str,
    position: tuple[int, int],
    scale: int,
    start: tuple[int, int, int],
    end: tuple[int, int, int],
) -> None:
    draw = ImageDraw.Draw(image)
    x, y = position
    for char in text:
        glyph = PIXEL_GLYPHS.get(char, PIXEL_GLYPHS[" "])
        glyph_height = len(glyph)
        for row, pixels in enumerate(glyph):
            color = interpolate_color(start, end, row / max(1, glyph_height - 1))
            for column, enabled in enumerate(pixels):
                if enabled != "1":
                    continue
                draw.rectangle(
                    (x + column * scale, y + row * scale, x + (column + 1) * scale - 1, y + (row + 1) * scale - 1),
                    fill=color,
                )
        x += (len(glyph[0]) + 1) * scale


def draw_pixel_frame(
    image: Image.Image,
    box: tuple[int, int, int, int],
    start: tuple[int, int, int],
    end: tuple[int, int, int],
    label: str,
    label_down_shift: int = 0,
    label_size: str = "small",
) -> None:
    x0, y0, x1, y1 = box
    width = max(1, x1 - x0)
    height = max(1, y1 - y0)
    unit = max(1, min(5, int(min(width, height) / 42)))
    thickness = max(1, unit)
    cut = unit * 2
    draw = ImageDraw.Draw(image)
    segments = (
        (x0 + cut, y0, x1 - cut, y0 + thickness),
        (x0 + cut, y1 - thickness, x1 - cut, y1),
        (x0, y0 + cut, x0 + thickness, y1 - cut),
        (x1 - thickness, y0 + cut, x1, y1 - cut),
        (x0 + thickness, y0 + thickness, x0 + cut, y0 + thickness * 2),
        (x1 - cut, y0 + thickness, x1 - thickness, y0 + thickness * 2),
        (x0 + thickness, y1 - thickness * 2, x0 + cut, y1 - thickness),
        (x1 - cut, y1 - thickness * 2, x1 - thickness, y1 - thickness),
    )
    for index, segment in enumerate(segments):
        draw.rectangle(segment, fill=interpolate_color(start, end, index / max(1, len(segments) - 1)))

    # Keep the current small marker unchanged while offering two larger,
    # pre-authored pixel sizes.  Never derive marker size from portrait or
    # black-header pixels: some player art intentionally covers that region.
    text_scale = OUTCOME_LABEL_SCALES.get(label_size, OUTCOME_LABEL_SCALES["small"])
    text_width = pixel_text_width(label, text_scale)
    # Centre the WIN/LOSE label inside the black header of the player card.
    text_x = max(x0 + unit, min(x1 - text_width - unit, x0 + (width - text_width) // 2))
    text_y = y0 + cut + unit + max(0, int(label_down_shift))
    if text_x >= x0 and text_y + text_scale * 5 < y1:
        draw_pixel_text(image, label, (text_x, text_y), text_scale, start, end)


def gray_out_losing_team(image: Image.Image, box: tuple[int, int, int, int]) -> None:
    x0, y0, x1, y1 = box
    if x1 <= x0 or y1 <= y0:
        return
    original = image.crop(box).convert("RGB")
    grayscale = ImageOps.grayscale(original).convert("RGB")
    # Keep the defeated lineup recognisable: it should read as subdued rather
    # than as a nearly black overlay.
    grayscale = ImageEnhance.Brightness(grayscale).enhance(0.80)
    muted = Image.blend(original, grayscale, 0.60)
    image.paste(muted, (x0, y0))


def draw_group_marker(image: Image.Image, box: tuple[int, int, int, int], group_index: int) -> None:
    x0, y0, x1, y1 = box
    width = max(1, x1 - x0)
    height = max(1, y1 - y0)
    unit = max(1, min(6, int(min(width, height) / 180)))
    label = f"GROUP{group_index}"
    start = (164, 126, 255)
    end = (104, 216, 255)
    draw = ImageDraw.Draw(image)
    thickness = max(1, unit)
    # Group blocks are separated by the stitcher's 42/56 px gaps.  The frame
    # stays clear of neighbours while expanding farther above and below to read
    # as a single enclosing boundary around the entire GROUP.
    horizontal_outset = max(8, min(18, unit * 3))
    vertical_outset = max(12, min(24, unit * 4))
    frame_x0 = max(0, x0 - horizontal_outset)
    frame_y0 = max(0, y0 - vertical_outset)
    frame_x1 = min(image.width - 1, x1 + horizontal_outset)
    frame_y1 = min(image.height - 1, y1 + vertical_outset)
    frame_color = interpolate_color(start, end, 0.5)
    draw.rectangle((frame_x0, frame_y0, frame_x1, frame_y0 + thickness - 1), fill=frame_color)
    draw.rectangle((frame_x0, frame_y1 - thickness + 1, frame_x1, frame_y1), fill=frame_color)
    draw.rectangle((frame_x0, frame_y0, frame_x0 + thickness - 1, frame_y1), fill=frame_color)
    draw.rectangle((frame_x1 - thickness + 1, frame_y0, frame_x1, frame_y1), fill=frame_color)
    text_scale = max(1, min(5, int(width / max(1, len(label) * 9))))
    # Outcome labels are centred in the first player card's title band, leaving
    # the upper-left corner of the enclosing group block for its identifier.
    text_height = text_scale * 5
    text_width = pixel_text_width(label, text_scale)
    text_x = min(x1 - text_width - unit, x0 + unit * 2)
    text_y = min(y1 - text_height - unit, y0 + unit * 2)
    # Reinforce contrast while keeping the label inside the group title band.
    draw.rectangle(
        (
            max(x0, text_x - unit * 2),
            max(y0, text_y - unit),
            min(x1, text_x + text_width + unit * 2),
            min(y1, text_y + text_height + unit),
        ),
        fill=(9, 18, 32, 220),
    )
    draw_pixel_text(
        image,
        label,
        (text_x, text_y),
        text_scale,
        start,
        end,
    )


def detail_profile_for_image(path: Path, fallback_server: str) -> tuple[str, str, dict[str, tuple[float, float, float, float]]]:
    server = server_from_filename(path, fallback_server)
    resolution = resolution_from_filename(path)
    profiles = DETAIL_ANNOTATION_PROFILES[server]
    return server, resolution, profiles.get(resolution, profiles["default"])


def resized_height(source_width: int, source_height: int, target_width: int) -> int:
    if source_width <= 0 or source_height <= 0:
        return 1
    return max(1, round(source_height * target_width / source_width))


def player_card_layout(server: str) -> PlayerCardLayout:
    """Derive player-card geometry from the same crop/stitch settings as capture.

    Every profile page is vertically stitched to ``output_width`` before it is
    paired with detailed battle data.  Using that source layout keeps annotation
    bounds exact across screen resolutions instead of estimating them from a
    percentage of a final composite image.
    """
    defaults = {
        "output_width": 720,
        "profile_basic": (684, 514),
        "sync_level": (638, 64),
        "round_lineup": (660, 274),
        "team_summary": (656, 122),
        "team_summary_output_width": 672,
        "research_card": (132, 112),
        "research_count": 8,
        "research_row_padding": 24,
        "research_row_gap": 0,
    }
    try:
        config = json.loads(Path(__file__).with_name("nikke_round_config.json").read_text(encoding="utf-8"))
        crops = config.get("crops", {})
        output_width = int(config.get("output_width", defaults["output_width"]))

        def crop_size(name: str, fallback: tuple[int, int]) -> tuple[int, int]:
            rect = crops.get(name) or []
            return (int(rect[2]), int(rect[3])) if len(rect) >= 4 else fallback

        profile_size = crop_size("profile_basic", defaults["profile_basic"])
        sync_size = crop_size("sync_level", defaults["sync_level"])
        round_size = crop_size("round_lineup", defaults["round_lineup"])
        team_size = crop_size("team_summary", defaults["team_summary"])
        card_rects = crops.get("research_cards_global_hmt") if server in {"overseas", "hmt"} else crops.get("research_cards")
        card_rects = card_rects or []
        card_sizes = [(int(rect[2]), int(rect[3])) for rect in card_rects if len(rect) >= 4]
        if not card_sizes:
            card_sizes = [defaults["research_card"]] * defaults["research_count"]
        regional_slot_width = int(config.get("research_card_slot_width_global_hmt", 0) or 0)
        use_regional_slot = server in {"overseas", "hmt"} and regional_slot_width > 0
        research_width = (
            sum(regional_slot_width if use_regional_slot else width for width, _ in card_sizes)
            + int(config.get("research_row_gap", defaults["research_row_gap"])) * max(0, len(card_sizes) - 1)
            + int(config.get("research_row_padding", defaults["research_row_padding"])) * 2
        )
        research_height = max(height for _, height in card_sizes)
        team_output_width = min(output_width, int(config.get("team_summary_output_width", defaults["team_summary_output_width"])))
    except (OSError, ValueError, TypeError, KeyError):
        output_width = defaults["output_width"]
        profile_size = defaults["profile_basic"]
        sync_size = defaults["sync_level"]
        round_size = defaults["round_lineup"]
        team_size = defaults["team_summary"]
        team_output_width = defaults["team_summary_output_width"]
        research_width = defaults["research_card"][0] * defaults["research_count"] + defaults["research_row_padding"] * 2
        research_height = defaults["research_card"][1]

    profile_height = resized_height(*profile_size, output_width)
    sync_height = resized_height(*sync_size, output_width)
    round_height = resized_height(*round_size, output_width)
    team_height = resized_height(*team_size, team_output_width)
    research_height = resized_height(research_width, research_height, output_width)
    lineup_top = profile_height + sync_height
    lineup_bottom = lineup_top + round_height * 5
    return PlayerCardLayout(
        width=output_width,
        height=lineup_bottom + team_height + research_height,
        lineup_top=lineup_top,
        lineup_bottom=lineup_bottom,
        label_down_shift=max(3, round(output_width / 90)),
    )


def player_panel_box(
    block: AnnotationBlock,
    layout: PlayerCardLayout,
    side: str,
    region: str,
) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = block.bbox
    # The final card width is fixed by output_width, while its height can vary
    # slightly at some source resolutions because the transformed crop aspect
    # ratios round differently.  Scale only the vertical subregions from the
    # actual stitched match block.
    card_height = max(1, y1 - y0)
    if side == "attacker":
        panel_x0, panel_x1 = x0, min(x1, x0 + layout.width)
    else:
        panel_x0, panel_x1 = max(x0, x1 - layout.width), x1
    if region == "panel":
        return (panel_x0, y0, panel_x1, y0 + card_height)
    vertical_scale = card_height / max(1, layout.height)
    return (
        panel_x0,
        min(y0 + round(layout.lineup_top * vertical_scale), y0 + card_height),
        panel_x1,
        min(y0 + round(layout.lineup_bottom * vertical_scale), y0 + card_height),
    )


def first_nonempty(values: list[str]) -> str:
    return next((value for value in values if value), "")


def build_match_outcomes(records: list[AnnotationRecord]) -> tuple[list[MatchOutcome], int, list[str]]:
    grouped: dict[tuple[int, int], list[AnnotationRecord]] = defaultdict(list)
    for record in records:
        grouped[(record.group_index, record.match_index)].append(record)

    outcomes: list[MatchOutcome] = []
    skipped_matches = 0
    warnings: list[str] = []
    for (group_index, match_index), match_records in sorted(grouped.items()):
        attacker_wins = sum(record.winner == "attacker" for record in match_records)
        defender_wins = sum(record.winner == "defender" for record in match_records)
        if max(attacker_wins, defender_wins) < 3 or attacker_wins == defender_wins:
            skipped_matches += 1
            warnings.append(f"第{group_index}组 M{match_index} 胜负记录不完整，未标记该对玩家。")
            continue
        outcomes.append(
            MatchOutcome(
                group_index=group_index,
                match_index=match_index,
                winner="attacker" if attacker_wins > defender_wins else "defender",
                attacker_name=first_nonempty([record.attacker_name for record in match_records]),
                attacker_id=first_nonempty([record.attacker_id for record in match_records]),
                defender_name=first_nonempty([record.defender_name for record in match_records]),
                defender_id=first_nonempty([record.defender_id for record in match_records]),
            )
        )
    return outcomes, skipped_matches, warnings


def annotate_detailed_round_frames_legacy(
    image: Image.Image,
    records: list[AnnotationRecord],
    blocks: dict[tuple[int, int], AnnotationBlock],
    profile: dict[str, tuple[float, float, float, float]],
    gray_loser: bool,
) -> int:
    """Reserved legacy behavior: central detailed-result Round annotations.

    The visual target is now the left/right player roster panels.  Keep the
    former implementation here, deliberately disabled, so it can be restored
    without reconstructing the old central-panel coordinate logic.
    """
    # for record in records:
    #     block = blocks.get((record.group_index, record.match_index))
    #     if block is None:
    #         continue
    #     loser_side = "defender" if record.winner == "attacker" else "attacker"
    #     winner_box = detail_team_box(block, record.winner, record.round_index, profile)
    #     loser_box = detail_team_box(block, loser_side, record.round_index, profile)
    #     if gray_loser:
    #         gray_out_losing_team(image, loser_box)
    #     draw_pixel_frame(image, winner_box, (29, 192, 255), (225, 252, 255), "WIN")
    #     draw_pixel_frame(image, loser_box, (248, 88, 78), (255, 223, 215), "LOSE")
    return 0


def annotate_image(
    source: Path,
    destination: Path,
    records: list[AnnotationRecord],
    client_profile: str,
    gray_loser: bool,
    label_size: str = "small",
) -> tuple[Path | None, dict[str, int | str]]:
    matching = [record for record in records if normalized_source_name(record.source_image) == normalized_source_name(source.name)]
    if not matching:
        return None, {"annotated_players": 0, "annotated_matches": 0, "skipped_matches": 0, "group_labels": 0, "warning": f"未在结果数据中找到：{source.name}"}

    with Image.open(source) as opened:
        # Screenshots do not use transparency.  Staying in RGB avoids a full
        # image-sized alpha allocation before annotation and makes large
        # all-GROUP exports materially faster to process.
        image = ImageOps.exif_transpose(opened).convert("RGB")
    if image.width * image.height > MAX_ANNOTATION_PIXELS:
        raise ImageToolError("战果图像过大。请先压缩或拆分图像后再标记。")

    stage = stage_from_filename(source)
    blocks = split_annotation_blocks(image.size, stage)
    block_index = {(block.group_index, block.match_index): block for block in blocks}
    server = server_from_filename(source, client_profile)
    resolution = resolution_from_filename(source)
    layout = player_card_layout(server)
    outcomes, skipped_matches, warnings = build_match_outcomes(matching)
    annotated_matches = 0
    annotated_players = 0
    for outcome in outcomes:
        block = block_index.get((outcome.group_index, outcome.match_index))
        if block is None:
            skipped_matches += 1
            warnings.append(f"第{outcome.group_index}组 M{outcome.match_index} 未找到对应的拼图位置。")
            continue
        winner_side = outcome.winner
        loser_side = "defender" if winner_side == "attacker" else "attacker"
        winner_box = player_panel_box(block, layout, winner_side, "panel")
        loser_box = player_panel_box(block, layout, loser_side, "panel")
        label_down_shift = max(2, round(layout.label_down_shift * (winner_box[3] - winner_box[1]) / max(1, layout.height)))
        if gray_loser:
            gray_out_losing_team(image, player_panel_box(block, layout, loser_side, "team"))
        draw_pixel_frame(image, winner_box, (29, 192, 255), (225, 252, 255), "WIN", label_down_shift, label_size)
        draw_pixel_frame(image, loser_box, (248, 88, 78), (255, 223, 215), "LOSE", label_down_shift, label_size)
        annotated_matches += 1
        annotated_players += 2

    if annotated_matches == 0:
        return None, {
            "annotated_players": 0,
            "annotated_matches": 0,
            "skipped_matches": skipped_matches,
            "group_labels": 0,
            "warning": "；".join(warnings) or f"未能将结果数据匹配到图像中的玩家阵容位置：{source.name}",
        }

    group_labels = 0
    if stage in {"group64", "group32", "group16"}:
        group_boxes: dict[int, list[tuple[int, int, int, int]]] = defaultdict(list)
        for block in blocks:
            group_boxes[block.group_index].append(block.bbox)
        for group_index, boxes in group_boxes.items():
            draw_group_marker(
                image,
                (min(box[0] for box in boxes), min(box[1] for box in boxes), max(box[2] for box in boxes), max(box[3] for box in boxes)),
                group_index,
            )
            group_labels += 1

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    extension = ".png" if source.suffix.lower() == ".png" else ".jpg"
    output = unique_output_path(destination, f"{source.stem}_胜负标注_{stamp}{extension}")
    if extension == ".png":
        # ``optimize=True`` performs a very expensive second compression pass
        # on huge screenshots.  Level 3 remains lossless while completing much
        # sooner; the trade-off is only a slightly larger PNG file.
        image.save(output, format="PNG", compress_level=3)
    else:
        image.save(output, format="JPEG", quality=95, subsampling=0, optimize=False)
    return output, {
        "annotated_players": annotated_players,
        "annotated_matches": annotated_matches,
        "skipped_matches": skipped_matches,
        "group_labels": group_labels,
        "server": server,
        "resolution": resolution,
        "warning": "；".join(warnings),
    }


def annotate_images(
    paths: list[Path],
    destination: Path,
    data_file: Path,
    client_profile: str,
    gray_loser: bool,
    label_size: str = "small",
) -> tuple[list[Path], dict[str, int], list[str]]:
    records = load_annotation_records(data_file)
    outputs: list[Path] = []
    totals = {"annotated_players": 0, "annotated_matches": 0, "skipped_matches": 0, "group_labels": 0}
    warnings: list[str] = []
    for source in paths:
        output, stats = annotate_image(source, destination, records, client_profile, gray_loser, label_size)
        if output is not None:
            outputs.append(output)
        for key in totals:
            totals[key] += int(stats.get(key, 0))
        warning = str(stats.get("warning") or "")
        if warning:
            warnings.append(warning)
    if not outputs:
        message = "；".join(warnings) if warnings else "没有找到可标记的战果图像。"
        raise ImageToolError(message)
    return outputs, totals, warnings


def detail_dark_ratio(image: Image.Image, box: tuple[int, int, int, int]) -> float:
    """Return the coverage of the dark defeat overlay within one detail side."""
    x0, y0, x1, y1 = box
    if x1 <= x0 or y1 <= y0:
        return 0.0
    pixel_bytes = image.crop((x0, y0, x1, y1)).tobytes()
    total = max(1, len(pixel_bytes) // 3)
    dark = sum(
        1
        for offset in range(0, len(pixel_bytes), 3)
        if max(pixel_bytes[offset], pixel_bytes[offset + 1], pixel_bytes[offset + 2]) < 55
    )
    return dark / total


def detect_direct_detail_winner(image: Image.Image, server: str) -> tuple[str, list[dict[str, float | int | str]]]:
    """Determine a two-player result from the five detailed battle sections.

    Final and other standalone two-player detail exports keep both roster
    panels at 720 px wide.  Their middle column contains five vertically
    stacked rounds.  The defeated side receives a large dark ``战败`` or
    ``DISCONNECTED`` overlay, which is reliable without invoking OCR.
    """
    layout = player_card_layout(server)
    center_left = layout.width
    center_right = image.width - layout.width
    center_width = center_right - center_left
    height_delta = abs(image.height - layout.height)
    if center_width < 160 or height_delta > max(36, round(layout.height * 0.035)):
        raise ImageToolError("该图不是可直接标记的双人详细战果图。请确认图中包含左右玩家阵容与中间五局详细战果页。")

    center_mid = center_left + center_width // 2
    horizontal_padding = max(4, round(center_width * 0.045))
    left_x0, left_x1 = center_left + horizontal_padding, center_mid - horizontal_padding
    right_x0, right_x1 = center_mid + horizontal_padding, center_right - horizontal_padding
    if left_x1 <= left_x0 or right_x1 <= right_x0:
        raise ImageToolError("无法定位图片中间的详细战果区域。")

    outcomes: list[dict[str, float | int | str]] = []
    for round_index in range(1, 6):
        y0 = round(image.height * (round_index - 1) / 5)
        y1 = round(image.height * round_index / 5)
        left_dark = detail_dark_ratio(image, (left_x0, y0, left_x1, y1))
        right_dark = detail_dark_ratio(image, (right_x0, y0, right_x1, y1))
        difference = abs(left_dark - right_dark)
        loser = "unknown"
        # Defeat overlays cover much more of the result card than ordinary
        # text/icons.  A small adaptive margin also covers JPEG screenshots.
        if max(left_dark, right_dark) >= 0.10 and difference >= 0.018:
            loser = "attacker" if left_dark > right_dark else "defender"
        outcomes.append(
            {
                "round": round_index,
                "left_dark": round(left_dark, 4),
                "right_dark": round(right_dark, 4),
                "loser": loser,
            }
        )

    attacker_wins = sum(item["loser"] == "defender" for item in outcomes)
    defender_wins = sum(item["loser"] == "attacker" for item in outcomes)
    if max(attacker_wins, defender_wins) < 3 or attacker_wins == defender_wins:
        raise ImageToolError("无法从中间详细战果页稳定判断胜负。请确认选择的是完整的双人详细战果图后重试。")
    return ("attacker" if attacker_wins > defender_wins else "defender"), outcomes


def annotate_direct_detail_image(
    source: Path,
    destination: Path,
    client_profile: str,
    gray_loser: bool,
    label_size: str = "small",
) -> tuple[Path, dict[str, int | str | list[dict[str, float | int | str]]]]:
    with Image.open(source) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGB")
    if image.width * image.height > MAX_ANNOTATION_PIXELS:
        raise ImageToolError("战果图像过大。请先压缩或拆分图像后再标记。")

    server = server_from_filename(source, client_profile)
    winner_side, round_outcomes = detect_direct_detail_winner(image, server)
    loser_side = "defender" if winner_side == "attacker" else "attacker"
    layout = player_card_layout(server)
    whole_match = AnnotationBlock(group_index=0, match_index=1, bbox=(0, 0, image.width, image.height))
    winner_box = player_panel_box(whole_match, layout, winner_side, "panel")
    loser_box = player_panel_box(whole_match, layout, loser_side, "panel")
    label_down_shift = max(2, round(layout.label_down_shift * (winner_box[3] - winner_box[1]) / max(1, layout.height)))
    if gray_loser:
        gray_out_losing_team(image, player_panel_box(whole_match, layout, loser_side, "team"))
    draw_pixel_frame(image, winner_box, (29, 192, 255), (225, 252, 255), "WIN", label_down_shift, label_size)
    draw_pixel_frame(image, loser_box, (248, 88, 78), (255, 223, 215), "LOSE", label_down_shift, label_size)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    extension = ".png" if source.suffix.lower() == ".png" else ".jpg"
    output = unique_output_path(destination, f"{source.stem}_胜负标注_{stamp}{extension}")
    if extension == ".png":
        image.save(output, format="PNG", compress_level=3)
    else:
        image.save(output, format="JPEG", quality=95, subsampling=0, optimize=False)
    return output, {
        "annotated_players": 2,
        "annotated_matches": 1,
        "skipped_matches": 0,
        "group_labels": 0,
        "server": server,
        "winner": winner_side,
        "rounds": round_outcomes,
    }


def annotate_direct_detail_images(
    paths: list[Path],
    destination: Path,
    client_profile: str,
    gray_loser: bool,
    label_size: str = "small",
) -> tuple[list[Path], dict[str, int | str | list[dict[str, float | int | str]]]]:
    if len(paths) != 1:
        raise ImageToolError("单张详细战果自动标记仅支持选择 1 张图像。")
    output, metadata = annotate_direct_detail_image(paths[0], destination, client_profile, gray_loser, label_size)
    return [output], metadata


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="NIKKE C ARENA image utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)

    compress = subparsers.add_parser("compress", help="Convert PNG screenshots to high-quality JPEG files")
    compress.add_argument("images", nargs="+", type=image_path)
    compress.add_argument("--output-dir", required=True, type=output_directory)
    compress.add_argument("--mode", choices=tuple(COMPRESSION_MODE_LABELS), default="high")

    stitch = subparsers.add_parser("stitch", help="Stitch images without resizing")
    stitch.add_argument("images", nargs="+", type=image_path)
    stitch.add_argument("--output-dir", required=True, type=output_directory)
    stitch.add_argument("--direction", required=True, choices=("vertical", "horizontal"))
    stitch.add_argument("--gap", required=True, type=int)
    stitch.add_argument("--background", choices=STITCH_BACKGROUND_OPTIONS, default="white")
    stitch.add_argument("--background-image", type=image_path)

    round_robin_stitch = subparsers.add_parser(
        "stitch-round-robin-folder",
        help="Stitch direct-child Group01-Group64 screenshots from a folder",
    )
    round_robin_stitch.add_argument("--input-dir", required=True, type=input_directory)
    round_robin_stitch.add_argument("--output-dir", required=True, type=output_directory)
    round_robin_stitch.add_argument("--layout", required=True, choices=("vertical", "horizontal"))
    round_robin_stitch.add_argument("--gap", required=True, type=int)
    round_robin_stitch.add_argument("--group-labels", action="store_true")
    round_robin_stitch.add_argument(
        "--background",
        choices=tuple(ROUND_ROBIN_BACKGROUND_COLORS),
        default="white",
        help="Background colour for round-robin-only output gutters and GROUP labels.",
    )

    annotate = subparsers.add_parser("annotate", help="Mark detailed battle screenshots from exported result data")
    annotate.add_argument("images", nargs="+", type=image_path)
    annotate.add_argument("--output-dir", required=True, type=output_directory)
    annotate.add_argument("--data-file", required=True, type=data_path)
    annotate.add_argument("--client-profile", choices=("cn", "overseas", "hmt"), default="cn")
    annotate.add_argument("--gray-loser", action="store_true")
    annotate.add_argument("--label-size", choices=tuple(OUTCOME_LABEL_SCALES), default="small")

    annotate_direct = subparsers.add_parser("annotate-direct", help="Mark one two-player detailed result screenshot without OCR data")
    annotate_direct.add_argument("images", nargs="+", type=image_path)
    annotate_direct.add_argument("--output-dir", required=True, type=output_directory)
    annotate_direct.add_argument("--client-profile", choices=("cn", "overseas", "hmt"), default="cn")
    annotate_direct.add_argument("--gray-loser", action="store_true")
    annotate_direct.add_argument("--label-size", choices=tuple(OUTCOME_LABEL_SCALES), default="small")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "compress":
            outputs = compress_images(args.images, args.output_dir, args.mode)
            metadata = {}
        elif args.command == "stitch":
            if len(args.images) < 2:
                raise ImageToolError("拼接图像至少需要选择 2 张图像。")
            if args.gap < 0 or args.gap > 5000:
                raise ImageToolError("图像间距需为 0 到 5000 的整数。")
            outputs = [
                stitch_images(
                    args.images,
                    args.output_dir,
                    args.direction,
                    args.gap,
                    args.background,
                    args.background_image,
                )
            ]
            metadata = {"background": args.background}
        elif args.command == "stitch-round-robin-folder":
            if args.gap < 0 or args.gap > 5000:
                raise ImageToolError("图像间距需为 0 到 5000 的整数像素。")
            outputs, group_indices = stitch_round_robin_folder(
                args.input_dir,
                args.output_dir,
                args.layout,
                args.gap,
                args.group_labels,
                args.background,
            )
            metadata = {
                "layout": args.layout,
                "group_labels": args.group_labels,
                "background": args.background,
                "group_count": len(group_indices),
                "group_indices": group_indices,
            }
        elif args.command == "annotate":
            outputs, metadata, warnings = annotate_images(
                args.images,
                args.output_dir,
                args.data_file,
                args.client_profile,
                args.gray_loser,
                args.label_size,
            )
            metadata["warnings"] = warnings
        else:
            outputs, metadata = annotate_direct_detail_images(
                args.images,
                args.output_dir,
                args.client_profile,
                args.gray_loser,
                args.label_size,
            )
    except (ImageToolError, MemoryError, OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "command": args.command,
                "output_dir": str(args.output_dir),
                "outputs": [str(path) for path in outputs],
                **metadata,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
