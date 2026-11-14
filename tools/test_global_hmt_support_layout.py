"""Static checks for the November-2026 Global/HMT paired-support layout.

This test never performs a real screenshot, mouse click, or Win32 input API.
Its capture-sequence checks replace every interaction with in-memory mocks;
it also validates coordinates and composition, optionally against the
maintainer's supplied 3440x1440 reference image when it is available locally.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nikke_round_stitcher as stitcher  # noqa: E402


REFERENCE_IMAGE = Path(r"D:\ts\国际服新版\3440x1440应援界面.png")


def load_global_config():
    with (ROOT / "nikke_round_config.json").open("r", encoding="utf-8") as handle:
        config = stitcher.load_config(ROOT / "nikke_round_config.json")
        # Open the JSON too, so a malformed packaged config is reported here.
        handle.seek(0)
        json.load(handle)
    config["runtime_server"] = "global"
    return config


def synthetic_paired_support_frame(config, active_round=1):
    """Create an in-memory structural fixture, not a game screenshot."""
    layout = stitcher.get_support_duo_global_hmt_layout(config)
    image = Image.new("RGB", (3440, 1440), "#0c1020")
    draw = ImageDraw.Draw(image)
    for name in ("top_lineup", "bottom_lineup"):
        x, y, width, height = layout[name]
        draw.rectangle((x, y, x + width, y + height), fill="#eeeeee")
        # Structured card-like columns give the edge readiness probe content
        # without relying on any external image asset.
        for card_x in range(x + 12, x + width - 8, 115):
            draw.rectangle((card_x, y + 8, min(card_x + 92, x + width - 4), y + height - 8), outline="#151515", width=5)
    x, y, width, height = layout["tabs_probe"]
    draw.rectangle((x, y, x + width, y + height), fill="#f5f5f5")
    active = layout["round_active_probes"][active_round - 1]
    ax, ay, aw, ah = active
    draw.rectangle((ax, ay, ax + aw, ay + ah), fill="#26bff0")
    return image


def test_layout_and_crop_coordinates(config):
    layout = stitcher.get_support_duo_global_hmt_layout(config)
    assert layout["avatars"] == [[1474, 352], [1474, 1103]]
    assert layout["round_tabs"]["1"] == [1447, 1228]
    assert layout["round_tabs"]["5"] == [1997, 1228]
    assert layout["top_lineup"] == [1390, 411, 656, 228]
    assert layout["bottom_lineup"] == [1387, 803, 666, 236]
    assert layout["top_power"] == [1394, 640, 225, 45]
    assert layout["bottom_power"] == [1826, 758, 226, 41]

    frame = synthetic_paired_support_frame(config)
    ready, metrics = stitcher._support_duo_probe_metrics(config, frame, expected_round=1)
    assert ready, metrics
    assert stitcher.crop_support_duo_global_hmt_part(config, frame, "top_lineup").size == (656, 228)
    assert stitcher.crop_support_duo_global_hmt_part(config, frame, "bottom_lineup").size == (666, 236)
    assert stitcher.crop_support_duo_global_hmt_part(config, frame, "top_power").size == (225, 45)
    assert stitcher.crop_support_duo_global_hmt_part(config, frame, "bottom_power").size == (226, 41)


def test_centered_height_transform_for_fullscreen_and_window_content(config):
    """New paired coordinates follow the same transform as all legacy modes."""
    layout = stitcher.get_support_duo_global_hmt_layout(config)
    expected = {
        (3440, 1440): {
            "avatar": (1474, 352),
            "round": (1447, 1228),
            "top_crop": (1390, 411, 2046, 639),
        },
        # 21:9 window content at 2560x1080: 3440-wide reference is slightly
        # wider after height scaling, so centered-height produces a -10 px x offset.
        (2560, 1080): {
            "avatar": (1096, 264),
            "round": (1075, 921),
            "top_crop": (1032, 308, 1524, 479),
        },
        # 16:9 content has letterbox-side cropping under the project's existing
        # centered-height policy; it must still use the same configured geometry.
        (1920, 1080): {
            "avatar": (776, 264),
            "round": (755, 921),
            "top_crop": (712, 308, 1204, 479),
        },
    }
    for size, values in expected.items():
        transform = stitcher.get_transform(config, size)
        assert stitcher.scale_point(layout["avatars"][0], transform) == values["avatar"]
        assert stitcher.scale_point(layout["round_tabs"]["1"], transform) == values["round"]
        assert stitcher.scale_rect(layout["top_lineup"], transform, size) == values["top_crop"]


def test_power_header_and_full_player_composition(config):
    profile = Image.new("RGB", (684, 514), "#666666")
    power = Image.new("RGB", (225, 45), "#31d0f4")
    header = stitcher.make_support_duo_power_header(profile, power, config)
    assert header.width == config["output_width"]
    assert header.height > 48
    # The chip is a compact, unscaled-width header element, and profile data
    # begins below it rather than being covered by it.
    assert header.getpixel((0, 0)) == (49, 208, 244)
    assert header.getpixel((0, int(config["support_duo_power_output_height"]))) == (102, 102, 102)

    top_round = Image.new("RGB", (656, 228), "#efefef")
    bottom_round = Image.new("RGB", (666, 236), "#e5e5e5")
    top_round_canvas = stitcher.make_support_duo_lineup_part(top_round, config)
    bottom_round_canvas = stitcher.make_support_duo_lineup_part(bottom_round, config)
    assert top_round_canvas.size == bottom_round_canvas.size == (720, 255)

    player_parts = {
        "profile": profile,
        "sync_level": Image.new("RGB", (638, 64), "#777777"),
        "team_summary": Image.new("RGB", (720, 110), "#888888"),
        "research_row": Image.new("RGB", (720, 112), "#999999"),
    }
    player = stitcher.compose_support_duo_global_hmt_player(
        player_parts, power, [top_round] * 5, config
    )
    assert player.width == 720
    assert player.getpixel((0, 0)) == (49, 208, 244)


def test_reference_image_if_present(config):
    if not REFERENCE_IMAGE.exists():
        return
    with Image.open(REFERENCE_IMAGE) as image:
        ready, metrics = stitcher._support_duo_probe_metrics(config, image, expected_round=1)
        assert ready, metrics
        assert stitcher.crop_support_duo_global_hmt_part(config, image, "top_lineup").size == (656, 228)
        assert stitcher.crop_support_duo_global_hmt_part(config, image, "bottom_lineup").size == (666, 236)


def test_global_status_flag_never_reaches_legacy_path(config):
    """The old CN status crop must be impossible on an overseas invocation."""
    calls = []
    original = stitcher.run_support_duo_global_hmt_capture
    try:
        def fake_capture(captured_config, output_path, parts_dir):
            calls.append((captured_config, output_path, parts_dir))
            return "overseas-capture"

        stitcher.run_support_duo_global_hmt_capture = fake_capture
        result = stitcher.run_support_duo_capture(
            config, Path("output.png"), Path("parts"), include_support_status=True
        )
    finally:
        stitcher.run_support_duo_global_hmt_capture = original
    assert result == "overseas-capture"
    assert len(calls) == 1


def test_profile_helper_collects_existing_single_player_metadata(config):
    """The paired view changes ROUND cards only, not profile/outpost content."""
    layout = stitcher.get_support_duo_global_hmt_layout(config)
    profile_frame = Image.new("RGB", (3440, 1440), "#f4f4f4")
    paired_frame = synthetic_paired_support_frame(config)
    clicks = []

    def fake_crop_rects(_config, _image, rects):
        if rects == [config["crops"]["sync_level"]]:
            return [Image.new("RGB", (638, 64), "#777777")]
        return [Image.new("RGB", (132, 112), "#999999") for _ in rects]

    with patch.object(stitcher, "screenshot", return_value=profile_frame), \
         patch.object(
             stitcher,
             "click",
             side_effect=lambda point, _transform: clicks.append(list(point)),
         ), \
         patch.object(
             stitcher,
             "wait_for_support_duo_profile_basic_page",
             return_value=profile_frame,
         ), \
         patch.object(
             stitcher,
             "wait_for_support_duo_global_hmt_page",
             return_value=paired_frame,
         ), \
         patch.object(stitcher, "crop_rects_from_image", side_effect=fake_crop_rects), \
         patch.object(
             stitcher,
             "make_research_row",
             return_value=Image.new("RGB", (720, 112), "#999999"),
         ), \
         patch.object(stitcher.time, "sleep"):
        parts, returned_frame = stitcher.capture_support_duo_global_hmt_profile(
            config,
            ROOT / "_unused",
            "top",
            layout["avatars"][0],
        )

    assert returned_frame is paired_frame
    assert clicks == [
        layout["avatars"][0],
        config["clicks"]["outpost_tab"],
        config["clicks"]["profile_close"],
    ]
    assert parts["profile"].size == (684, 514)
    assert parts["sync_level"].size == (638, 64)
    assert parts["research_row"].size == (720, 112)


def test_capture_uses_two_metadata_sets_one_power_set_and_five_paired_rounds(config):
    """Exercise the orchestration with mocks so it cannot emit real input."""
    layout = stitcher.get_support_duo_global_hmt_layout(config)
    paired_frame = synthetic_paired_support_frame(config)
    profile_parts = {
        "top": {
            "profile": Image.new("RGB", (684, 514), "#666666"),
            "sync_level": Image.new("RGB", (638, 64), "#777777"),
            "team_summary": Image.new("RGB", (720, 110), "#888888"),
            "research_row": Image.new("RGB", (720, 112), "#999999"),
        },
        "bottom": {
            "profile": Image.new("RGB", (684, 514), "#555555"),
            "sync_level": Image.new("RGB", (638, 64), "#777777"),
            "team_summary": Image.new("RGB", (720, 110), "#888888"),
            "research_row": Image.new("RGB", (720, 112), "#999999"),
        },
    }
    profile_calls = []
    click_points = []
    crop_names = []

    def fake_profile(_config, _parts_dir, label, avatar_point):
        profile_calls.append((label, list(avatar_point)))
        return profile_parts[label], paired_frame

    def fake_crop(_config, _image, part_name):
        crop_names.append(part_name)
        colours = {
            "top_power": "#2bc6ef",
            "bottom_power": "#ecab38",
            "top_lineup": "#eeeeee",
            "bottom_lineup": "#dddddd",
        }
        sizes = {
            "top_power": (225, 45),
            "bottom_power": (226, 41),
            "top_lineup": (656, 228),
            "bottom_lineup": (666, 236),
        }
        return Image.new("RGB", sizes[part_name], colours[part_name])

    with TemporaryDirectory() as temp_dir:
        output = Path(temp_dir) / "support.png"
        with patch.object(stitcher, "print_screen_context"), \
             patch.object(
                 stitcher,
                 "wait_for_support_duo_global_hmt_page",
                 side_effect=lambda *_args, **_kwargs: paired_frame,
             ), \
             patch.object(
                 stitcher,
                 "capture_support_duo_global_hmt_profile",
                 side_effect=fake_profile,
             ), \
             patch.object(
                 stitcher,
                 "click",
                 side_effect=lambda point, _transform: click_points.append(list(point)),
             ), \
             patch.object(
                 stitcher,
                 "crop_support_duo_global_hmt_part",
                 side_effect=fake_crop,
             ), \
             patch.object(stitcher, "save_framed_output"):
            stitcher.run_support_duo_global_hmt_capture(config, output, Path(temp_dir))

        assert output.exists()
        with Image.open(output) as result:
            assert result.size[0] == config["output_width"] * 2 + config["duo_column_gap"]

    assert profile_calls == [
        ("top", layout["avatars"][0]),
        ("bottom", layout["avatars"][1]),
    ]
    assert click_points == [layout["round_tabs"][str(index)] for index in range(1, 6)]
    assert crop_names.count("top_power") == 1
    assert crop_names.count("bottom_power") == 1
    assert crop_names.count("top_lineup") == 5
    assert crop_names.count("bottom_lineup") == 5


def main():
    config = load_global_config()
    test_layout_and_crop_coordinates(config)
    test_centered_height_transform_for_fullscreen_and_window_content(config)
    test_power_header_and_full_player_composition(config)
    test_reference_image_if_present(config)
    test_global_status_flag_never_reaches_legacy_path(config)
    test_profile_helper_collects_existing_single_player_metadata(config)
    test_capture_uses_two_metadata_sets_one_power_set_and_five_paired_rounds(config)
    print("Global/HMT paired support layout checks passed (no mouse input).")


if __name__ == "__main__":
    main()
