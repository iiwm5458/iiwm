# Original author / 原作者：iiwm（雪瑶 / 夙辛）
# [utf8-hex] 6969776D7CE99BAAE791B67CE5A499E8BE9B
# [utf8-hex] 68747470733A2F2F737465616D636F6D6D756E6974792E636F6D2F73686172656466696C65732F66696C6564657461696C732F3F69643D33353436393635303538
# [utf8-hex] 6A613DE4B896E7958CE5B9B3E5928C3B6B6F3DEC849CEAB38420ED8F89ED9994
import argparse
import builtins
import ctypes
import difflib
import gc
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageGrab
except ModuleNotFoundError:
    print("Missing Pillow; the current Python runtime cannot capture or stitch images.")
    print("Run: python -m pip install pillow")
    print("Or run run_stitcher.bat in this folder; it prefers the bundled Python runtime.")
    sys.exit(1)


DETAIL_PAGE_CAPTURE_SETTLE_SECONDS = 0.5
PROFILE_PAGE_CAPTURE_SETTLE_SECONDS = 0.35
PROFILE_PAGE_DEFAULT_TIMEOUT_SECONDS = 10.0
PROFILE_PAGE_DEFAULT_POLL_INTERVAL_SECONDS = 0.35
# Season capture always uses these fixed transition waits; they are intentionally
# independent from the user-configurable capture timing controls.
SEASON_TRANSITION_BACK_WAIT_SECONDS = 3.0
SEASON_TOP8_ENTRY_WAIT_SECONDS = 5.0
DETAIL_PAGE_STRICT_THRESHOLDS = {
    "title_blue": 0.45,
    "detail_dark": 0.16,
    "detail_edges": 0.08,
}
GLOBAL_HMT_DETAIL_PAGE_FALLBACK_THRESHOLDS = {
    "title_blue": 0.65,
    "detail_dark": 0.12,
    "detail_edges": 0.14,
}
PROFILE_PAGE_READY_THRESHOLDS = {
    "header_bright": 0.30,
    "lower_bright": 0.40,
    "bottom_bright": 0.35,
    "basic_tab_blue": 0.025,
}


DEFAULT_CONFIG = {
    "reference_size": [3440, 1440],
    "coordinate_mode": "centered_height",
    "output_width": 720,
    "gap_px": 0,
    "background": "#20242a",
    "research_row_padding": 24,
    "research_row_gap": 0,
    "research_row_background": "#f7f8fa",
    "research_card_align": "top",
    "research_card_slot_width_global_hmt": 132,
    "team_summary_output_width": 672,
    "team_summary_x_offset": -8,
    "team_summary_background": "#f7f8fa",
    "duo_column_gap": 18,
    "group_grid_gap": 18,
    "round_robin_grid_gap": 13,
    "round_robin_background": "#FFFFFF",
    "group_data_gap": 18,
    "group_data_column_gap": 42,
    "all_groups_grid_gap": 56,
    "top8_pyramid_layer_gap": 72,
    "support_status_background": "#f7f8fa",
    "framed_output": False,
    "framed_background": "assets/pixiewall-xlesjh-5120x2880.jpg",
    "framed_margin_x": 80,
    "framed_margin_y": 0,
    "framed_opacity": 0.86,
    "framed_edge_blur": 0,
    "framed_bg_center": [0.5, 0.52],
    "save_parts": False,
    "close_profile_after_capture": True,
    "timing": {
        "countdown_seconds": 0,
        "after_round_click_seconds": 0.45,
        "after_avatar_click_seconds": 0.9,
        "after_support_avatar_click_seconds": 1.0,
        "after_group_avatar_click_seconds": 1.0,
        "after_group_tab_click_seconds": 0.8,
        "after_round_robin_group_switch_seconds": 1.3,
        "after_group_result_click_seconds": 0.9,
        "after_bracket_result_click_seconds": 1.0,
        "after_group_detail_click_seconds": 0.7,
        "detail_page_timeout_seconds": 60.0,
        "detail_page_poll_interval_seconds": 0.35,
        "profile_page_poll_enabled": False,
        "profile_page_timeout_seconds": PROFILE_PAGE_DEFAULT_TIMEOUT_SECONDS,
        "profile_page_poll_interval_seconds": PROFILE_PAGE_DEFAULT_POLL_INTERVAL_SECONDS,
        "after_outpost_click_seconds": 0.7,
        "after_profile_close_seconds": 0.4,
        "after_escape_seconds": 0.45,
    },
    "clicks": {
        "avatar": [1477, 579],
        "profile_close": [2049, 138],
        # Outside the central modal at the 3440x1440 reference size.  These
        # points are transformed together with every other capture coordinate.
        "modal_dismiss_side_points": [[1230, 720], [2190, 720]],
        "outpost_tab": [1899, 1333],
        "support_left_avatar": [1548, 430],
        "support_right_avatar": [1875, 430],
        # Player avatars inside the already-open two-player result popup.
        # Keep the tab and no-tab variants separate so either layout can be
        # calibrated independently if a future client revision shifts it.
        "support_result_avatars_without_stage_tabs": [[1455, 727], [1899, 727]],
        "support_result_avatars_with_stage_tabs": [[1455, 727], [1899, 727]],
        # The four avatar centers on the round-robin overview at 3440x1440.
        # They are passed through the same transform as every other capture point.
        "round_robin_avatars": [
            [1429, 568],
            [1427, 749],
            [1429, 933],
            [1425, 1115],
        ],
        # Round-robin GROUP selector coordinates at the 3440x1440 reference.
        # The picker is a five-column grid containing GROUP01 through GROUP64.
        "round_robin_group_selector": [1720, 412],
        "round_robin_group_grid_origin": [1486, 312],
        "round_robin_group_grid_step": [115, 67],
        "round_robin_group_confirm": [1846, 1278],
        "group_64_avatars": [
            [1390, 500],
            [1390, 675],
            [2050, 500],
            [2050, 675],
            [1390, 1040],
            [1390, 1220],
            [2050, 1040],
            [2050, 1220],
        ],
        "group_32_avatars": [
            [1490, 595],
            [1945, 595],
            [1490, 1122],
            [1945, 1122],
        ],
        "group_16_avatars": [
            [1627, 761],
            [1808, 937],
        ],
        "top8_avatars": [
            [1393, 459],
            [1389, 637],
            [2047, 461],
            [2042, 640],
            [1395, 987],
            [1387, 1164],
            [2046, 989],
            [2047, 1170],
        ],
        "top8_4_avatars": [
            [1507, 542],
            [1928, 548],
            [1507, 1073],
            [1928, 1074],
        ],
        "top8_final_avatars": [
            [1626, 714],
            [1808, 886],
        ],
        "group_tabs": [
            [175, 276],
            [490, 276],
            [808, 276],
            [1121, 276],
            [1442, 276],
            [1760, 276],
            [2070, 276],
            [2395, 276]
        ],
        "group_tab_ratios": [
            [0.0691, 0.2542],
            [0.1918, 0.2549],
            [0.3141, 0.2549],
            [0.4375, 0.2542],
            [0.5605, 0.2556],
            [0.6824, 0.2542],
            [0.8055, 0.2556],
            [0.9277, 0.2549]
        ],
        "group_result_buttons": [
            [1629, 596],
            [1796, 596],
            [1636, 1126],
            [1812, 1129],
        ],
        "group_32_result_buttons": [
            [1736, 764],
            [1668, 947],
        ],
        "group_16_result_buttons": [
            [1717, 852],
        ],
        "top8_result_buttons": [
            [1635, 554],
            [1794, 554],
            [1632, 1081],
            [1805, 1085],
        ],
        "top8_4_result_buttons": [
            [1778, 724],
            [1650, 898],
        ],
        "top8_final_result_buttons": [
            [1768, 722],
            [1664, 892],
        ],
        "season_return_button": [80, 1362],
        "season_return_button_ratio": [0.0233, 0.946],
        "season_top8_entry": [1995, 882],
        "season_top8_entry_ratio": [0.58, 0.61],
        "group_16_winner_result_buttons": [
            [1736, 764],
            [1668, 947],
        ],
        "group_16_result_stage_tab": [1533, 1158],
        "group_32_result_stage_tab": [1903, 1158],
        "group_detail_buttons": [
            [1891, 826],
            [1891, 887],
            [1891, 948],
            [1891, 1008],
            [1891, 1070],
        ],
        "group_32_detail_buttons": [
            [1891, 826],
            [1891, 887],
            [1891, 948],
            [1891, 1008],
            [1891, 1070],
        ],
        "support_result_detail_buttons_without_stage_tabs": [
            [1891, 826],
            [1891, 887],
            [1891, 948],
            [1891, 1008],
            [1891, 1070],
        ],
        "support_result_detail_buttons_with_stage_tabs": [
            [1891, 826],
            [1891, 887],
            [1891, 948],
            [1891, 1008],
            [1891, 1070],
        ],
        "round_tabs": {
            "1": [1462, 707],
            "2": [1604, 707],
            "3": [1754, 707],
            "4": [1900, 707],
            "5": [2001, 707],
        },
    },
    "crops": {
        "round_lineup": [1393, 756, 660, 274],
        "profile_basic": [1378, 0, 684, 514],
        "team_summary": [1380, 908, 656, 122],
        "sync_level": [1402, 1174, 638, 64],
        "research_cards": [
            [1500, 724, 132, 112],
            [1650, 724, 132, 112],
            [1800, 724, 132, 112],
            [1578, 850, 132, 112],
            [1728, 850, 132, 112],
            [1460, 1040, 132, 112],
            [1650, 1040, 132, 112],
            [1838, 1040, 132, 112],
        ],
        # Global/HMT needs a small amount of extra space on the eighth card
        # so the right edge of the auxiliary research level remains visible.
        "research_cards_global_hmt": [
            [1500, 724, 132, 112],
            [1650, 724, 132, 112],
            [1800, 724, 132, 112],
            [1578, 850, 132, 112],
            [1728, 850, 132, 112],
            [1460, 1040, 132, 112],
            [1650, 1040, 132, 112],
            [1838, 1040, 144, 112],
        ],
        "outpost_research": [1403, 976, 634, 255],
        "support_status": [1396, 636, 676, 58],
        "group_simple_result": [1555, 793, 243, 301],
        "group_detailed_result": [1380, 289, 681, 873],
        "group_detailed_result_global_hmt": [1380, 356, 681, 788],
        # The round-robin post-match overview: GROUP header plus all four
        # result rows. It is placed to the left of the four profile cards.
        "round_robin_post_result": [1327, 360, 815, 858],
        "round_robin_post_result_global_hmt": [1327, 360, 815, 858],
        "group_detailed_title_probe": [1415, 160, 610, 140],
        # Profile-page probes use the same 3440x1440 reference coordinates as
        # the detailed-result probes and are transformed for every screen size.
        "profile_page_header_probe": [1380, 120, 680, 360],
        "profile_page_lower_probe": [1380, 1030, 680, 220],
        "profile_page_bottom_probe": [1380, 1310, 680, 110],
        "profile_page_basic_tab_probe": [1400, 1350, 310, 70],
        "season_profile_name_probe": [1458, 315, 430, 95],
        "season_result_name_probe": [1368, 300, 704, 420],
        "group_result_stage_tabs_probe": [1450, 1110, 650, 120],
        "group_16_winner_result_button_probes": [
            [1668, 718, 224, 92],
            [1544, 900, 224, 92],
        ],
        "top8_final_result_button_probes": [
            [1705, 700, 127, 50],
            [1595, 874, 140, 38],
        ],
    },
}


user32 = ctypes.windll.user32

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
KEYEVENTF_KEYUP = 0x0002
VK_ESCAPE = 0x1B


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("union", INPUT_UNION)]


def send_mouse(flags):
    extra = ctypes.c_ulong(0)
    event = INPUT(
        type=INPUT_MOUSE,
        union=INPUT_UNION(
            mi=MOUSEINPUT(0, 0, 0, flags, 0, ctypes.pointer(extra))
        ),
    )
    user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(event))


def send_key(vk):
    extra = ctypes.c_ulong(0)
    down = INPUT(
        type=INPUT_KEYBOARD,
        union=INPUT_UNION(ki=KEYBDINPUT(vk, 0, 0, 0, ctypes.pointer(extra))),
    )
    up = INPUT(
        type=INPUT_KEYBOARD,
        union=INPUT_UNION(ki=KEYBDINPUT(vk, 0, KEYEVENTF_KEYUP, 0, ctypes.pointer(extra))),
    )
    user32.SendInput(1, ctypes.byref(down), ctypes.sizeof(down))
    time.sleep(0.05)
    user32.SendInput(1, ctypes.byref(up), ctypes.sizeof(up))


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class WindowCaptureContext:
    """Capture and click against a NIKKE client area, not the whole desktop."""

    def __init__(self, handle):
        self.handle = ctypes.c_void_p(int(handle))

    def client_bounds(self):
        if not user32.IsWindow(self.handle):
            raise RuntimeError("NIKKE game window is no longer available")
        rect = RECT()
        if not user32.GetClientRect(self.handle, ctypes.byref(rect)):
            raise RuntimeError("could not read the NIKKE client area")
        origin = POINT(0, 0)
        if not user32.ClientToScreen(self.handle, ctypes.byref(origin)):
            raise RuntimeError("could not convert NIKKE client coordinates")
        width = int(rect.right - rect.left)
        height = int(rect.bottom - rect.top)
        if width < 320 or height < 240:
            raise RuntimeError("NIKKE client area is too small for capture")
        return int(origin.x), int(origin.y), width, height

    def grab(self):
        left, top, width, height = self.client_bounds()
        bbox = (left, top, left + width, top + height)
        try:
            return ImageGrab.grab(bbox=bbox, all_screens=True)
        except TypeError:
            return ImageGrab.grab(bbox=bbox)

    def to_screen_point(self, x, y):
        left, top, _, _ = self.client_bounds()
        return left + int(round(x)), top + int(round(y))


ACTIVE_WINDOW_CAPTURE = None


def enable_window_capture(handle):
    global ACTIVE_WINDOW_CAPTURE
    ACTIVE_WINDOW_CAPTURE = WindowCaptureContext(handle)
    left, top, width, height = ACTIVE_WINDOW_CAPTURE.client_bounds()
    print(
        "window capture enabled: "
        f"handle={int(handle)} client=({left},{top}) {width}x{height}"
    )


def set_dpi_aware():
    try:
        user32.SetProcessDPIAware()
    except Exception:
        pass


def load_config(path):
    if not path.exists():
        return DEFAULT_CONFIG.copy()
    with path.open("r", encoding="utf-8-sig") as f:
        config = json.load(f)
    merged = DEFAULT_CONFIG.copy()
    for key, value in config.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    return merged


def screenshot():
    if ACTIVE_WINDOW_CAPTURE is not None:
        return ACTIVE_WINDOW_CAPTURE.grab()
    return ImageGrab.grab()


def get_transform(config, image_size):
    ref_w, ref_h = config["reference_size"]
    img_w, img_h = image_size
    mode = config.get("coordinate_mode", "centered_height")

    if mode == "stretch":
        return {
            "sx": img_w / ref_w,
            "sy": img_h / ref_h,
            "ox": 0,
            "oy": 0,
            "mode": mode,
        }

    if mode == "centered_width":
        scale = img_w / ref_w
        return {
            "sx": scale,
            "sy": scale,
            "ox": 0,
            "oy": (img_h - ref_h * scale) / 2,
            "mode": mode,
        }

    if mode == "uniform_fit":
        scale = min(img_w / ref_w, img_h / ref_h)
        return {
            "sx": scale,
            "sy": scale,
            "ox": (img_w - ref_w * scale) / 2,
            "oy": (img_h - ref_h * scale) / 2,
            "mode": mode,
        }

    scale = img_h / ref_h
    return {
        "sx": scale,
        "sy": scale,
        "ox": (img_w - ref_w * scale) / 2,
        "oy": 0,
        "mode": "centered_height",
    }


def scale_point(point, transform):
    return (
        round(point[0] * transform["sx"] + transform["ox"]),
        round(point[1] * transform["sy"] + transform["oy"]),
    )


def scale_rect(rect, transform, image_size):
    x, y, w, h = rect
    left = round(x * transform["sx"] + transform["ox"])
    top = round(y * transform["sy"] + transform["oy"])
    right = round((x + w) * transform["sx"] + transform["ox"])
    bottom = round((y + h) * transform["sy"] + transform["oy"])
    img_w, img_h = image_size
    return (
        max(0, min(left, img_w)),
        max(0, min(top, img_h)),
        max(0, min(right, img_w)),
        max(0, min(bottom, img_h)),
    )


def click(point, transform, duration=0.06):
    x, y = scale_point(point, transform)
    click_screen_point(x, y, duration)


def click_screen_point(x, y, duration=0.06):
    if ACTIVE_WINDOW_CAPTURE is not None:
        x, y = ACTIVE_WINDOW_CAPTURE.to_screen_point(x, y)
    user32.SetCursorPos(x, y)
    time.sleep(max(duration, 0.08))
    send_mouse(MOUSEEVENTF_LEFTDOWN)
    time.sleep(max(duration, 0.08))
    send_mouse(MOUSEEVENTF_LEFTUP)


def click_screen_ratio(ratio, image_size, duration=0.06):
    x = round(float(ratio[0]) * image_size[0])
    y = round(float(ratio[1]) * image_size[1])
    click_screen_point(x, y, duration)


def click_group_tab(config, group_index, transform):
    ratios = config["clicks"].get("group_tab_ratios", [])
    if len(ratios) >= group_index:
        click_screen_ratio(ratios[group_index - 1], screenshot().size)
        return

    tabs = config["clicks"].get("group_tabs", [])
    if len(tabs) < group_index:
        raise SystemExit("group_tabs must contain GROUP01-GROUP08 click points")
    click(tabs[group_index - 1], transform)


def countdown(seconds):
    for i in range(seconds, 0, -1):
        print(f"{i}...")
        time.sleep(1)


def crop_from_image(config, img, crop_name):
    transform = get_transform(config, img.size)
    box = scale_rect(config["crops"][crop_name], transform, img.size)
    return img.crop(box)


def crop_current(config, crop_name):
    return crop_from_image(config, screenshot(), crop_name)


def get_round_robin_post_result_rect(config):
    crops = config.get("crops", {})
    server = str(config.get("runtime_server", "cn")).strip().lower()
    if server in {"global", "hmt"}:
        regional_rect = crops.get("round_robin_post_result_global_hmt")
        if regional_rect:
            return regional_rect
    return crops["round_robin_post_result"]


def capture_round_robin_post_result(config):
    """Capture the current GROUP's four-row post-match result overview."""
    current = screenshot()
    transform = get_transform(config, current.size)
    box = scale_rect(get_round_robin_post_result_rect(config), transform, current.size)
    return current.crop(box)


def get_research_card_rects(config):
    crops = config["crops"]
    server = str(config.get("runtime_server", "cn")).strip().lower()
    if server in {"global", "hmt"}:
        regional_rects = crops.get("research_cards_global_hmt")
        if regional_rects:
            return regional_rects
    return crops["research_cards"]


class DetailPageTimeout(RuntimeError):
    def __init__(self, context, timeout_seconds):
        self.context = context
        self.timeout_seconds = timeout_seconds
        super().__init__(f"{context}: detailed battle record was not ready after {timeout_seconds:.1f}s")


def _probe_image(img, max_width=200):
    if img.width <= max_width:
        return img.convert("RGB")
    height = max(1, round(img.height * max_width / img.width))
    return img.convert("RGB").resize((max_width, height), Image.Resampling.BILINEAR)


def _ratio_matching(img, predicate):
    pixels = list(img.getdata())
    if not pixels:
        return 0.0
    return sum(1 for r, g, b in pixels if predicate(r, g, b)) / len(pixels)


def inspect_detailed_result_page(config, img):
    """Return whether the post-click screen is the fully loaded battle record page."""
    crops = config.get("crops", {})
    title_rect = crops.get("group_detailed_title_probe")
    detail_rect = crops.get("group_detailed_result")
    if not title_rect or not detail_rect:
        return False, None, {"reason": "detail probes are not configured"}

    transform = get_transform(config, img.size)
    title = _probe_image(img.crop(scale_rect(title_rect, transform, img.size)))
    detail = img.crop(scale_rect(detail_rect, transform, img.size))
    detail_probe = _probe_image(detail)

    title_blue_ratio = _ratio_matching(
        title,
        lambda r, g, b: b >= 150 and g >= 95 and r <= 95 and (b - r) >= 75,
    )
    detail_dark_ratio = _ratio_matching(
        detail_probe,
        lambda r, g, b: r <= 75 and g <= 75 and b <= 75,
    )
    edge_probe = detail_probe.convert("L").filter(ImageFilter.FIND_EDGES)
    detail_edge_ratio = sum(1 for value in edge_probe.getdata() if value >= 75) / max(1, detail_probe.width * detail_probe.height)

    metrics = {
        "title_blue": title_blue_ratio,
        "detail_dark": detail_dark_ratio,
        "detail_edges": detail_edge_ratio,
    }
    strict_ready = all(
        metrics[name] >= threshold for name, threshold in DETAIL_PAGE_STRICT_THRESHOLDS.items()
    )
    server = str(config.get("runtime_server", "cn")).strip().lower()
    regional_fallback_ready = (
        server in {"global", "hmt"}
        and all(
            metrics[name] >= threshold
            for name, threshold in GLOBAL_HMT_DETAIL_PAGE_FALLBACK_THRESHOLDS.items()
        )
    )
    # Global/HMT can display fully loaded opponent cards as DISCONNECTED, which
    # lowers the dark-pixel ratio below the original CN-focused threshold. Keep
    # CN strict for now; revisit this fallback if a future CN client shows it.
    if strict_ready:
        metrics["readiness_rule"] = "strict"
    elif regional_fallback_ready:
        metrics["readiness_rule"] = "global_hmt_disconnected_fallback"
    else:
        metrics["readiness_rule"] = "not_ready"
    is_ready = strict_ready or regional_fallback_ready
    return is_ready, detail, metrics


def inspect_profile_basic_page(config, img):
    """Return whether the full player basic-information page is visible.

    The probe intentionally avoids OCR and language-dependent text. A loaded
    profile page has a tall light panel and an active cyan basic-information
    tab, while the preceding lineup dialogs do not occupy the lower probes.
    """
    crops = config.get("crops", {})
    probe_names = {
        "header": "profile_page_header_probe",
        "lower": "profile_page_lower_probe",
        "bottom": "profile_page_bottom_probe",
        "basic_tab": "profile_page_basic_tab_probe",
    }
    if any(not crops.get(name) for name in probe_names.values()):
        return False, {"reason": "profile probes are not configured"}

    transform = get_transform(config, img.size)
    probes = {
        label: _probe_image(img.crop(scale_rect(crops[crop_name], transform, img.size)))
        for label, crop_name in probe_names.items()
    }
    metrics = {
        "header_bright": _ratio_matching(
            probes["header"],
            lambda r, g, b: r >= 175 and g >= 175 and b >= 175,
        ),
        "lower_bright": _ratio_matching(
            probes["lower"],
            lambda r, g, b: r >= 175 and g >= 175 and b >= 175,
        ),
        "bottom_bright": _ratio_matching(
            probes["bottom"],
            lambda r, g, b: r >= 175 and g >= 175 and b >= 175,
        ),
        "basic_tab_blue": _ratio_matching(
            probes["basic_tab"],
            lambda r, g, b: b >= 150 and g >= 110 and r <= 100 and (b - r) >= 70,
        ),
    }
    is_ready = all(
        metrics[name] >= threshold for name, threshold in PROFILE_PAGE_READY_THRESHOLDS.items()
    )
    return is_ready, metrics


def wait_for_profile_basic_page(config, context):
    """Capture the basic profile after an optional readiness poll.

    A timeout is deliberately non-fatal: when a visual variation prevents a
    match, the current screen is still captured so one false negative cannot
    stop an otherwise valid screenshot task.
    """
    timings = config["timing"]
    minimum_wait = max(0.45, min(5.0, float(timings.get("after_avatar_click_seconds", 0.9))))
    if not bool(timings.get("profile_page_poll_enabled", False)):
        time.sleep(minimum_wait)
        return crop_current(config, "profile_basic")

    timeout_seconds = max(
        1.0,
        min(10.0, float(timings.get("profile_page_timeout_seconds", PROFILE_PAGE_DEFAULT_TIMEOUT_SECONDS))),
    )
    poll_seconds = max(
        0.2,
        min(1.0, float(timings.get("profile_page_poll_interval_seconds", PROFILE_PAGE_DEFAULT_POLL_INTERVAL_SECONDS))),
    )
    started_at = time.monotonic()
    deadline = started_at + timeout_seconds
    stable_hits = 0
    latest_metrics = None

    while True:
        current_img = screenshot()
        ready, latest_metrics = inspect_profile_basic_page(config, current_img)
        if ready:
            stable_hits += 1
            elapsed = time.monotonic() - started_at
            if stable_hits >= 2 and elapsed >= minimum_wait:
                time.sleep(PROFILE_PAGE_CAPTURE_SETTLE_SECONDS)
                final_img = screenshot()
                print(
                    f"{context}: basic profile page ready "
                    f"(header_bright={latest_metrics['header_bright']:.3f}, "
                    f"lower_bright={latest_metrics['lower_bright']:.3f}, "
                    f"bottom_bright={latest_metrics['bottom_bright']:.3f}, "
                    f"basic_tab_blue={latest_metrics['basic_tab_blue']:.3f})"
                )
                return crop_from_image(config, final_img, "profile_basic")
        else:
            stable_hits = 0

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            print(f"{context}: basic profile page poll timeout; capturing current screen; metrics={latest_metrics}")
            return crop_from_image(config, screenshot(), "profile_basic")
        time.sleep(min(poll_seconds, remaining))


def get_detailed_result_capture_rect(config):
    server = str(config.get("runtime_server", "cn")).strip().lower()
    if server in {"global", "hmt"}:
        regional_rect = config.get("crops", {}).get("group_detailed_result_global_hmt")
        if regional_rect:
            return regional_rect
    return config["crops"]["group_detailed_result"]


def wait_for_detailed_result_page(config, context):
    """Wait for one black-button detail page without issuing any extra input."""
    timings = config["timing"]
    timeout_seconds = max(10.0, min(180.0, float(timings.get("detail_page_timeout_seconds", 60.0))))
    poll_seconds = max(0.2, min(1.0, float(timings.get("detail_page_poll_interval_seconds", 0.35))))
    minimum_wait = max(0.0, min(5.0, float(timings.get("after_group_detail_click_seconds", 0.7))))
    deadline = time.monotonic() + timeout_seconds
    stable_hits = 0
    latest_metrics = None

    if minimum_wait:
        time.sleep(min(minimum_wait, timeout_seconds))

    while True:
        ready, detail, latest_metrics = inspect_detailed_result_page(config, screenshot())
        if ready:
            stable_hits += 1
            if stable_hits >= 2:
                time.sleep(DETAIL_PAGE_CAPTURE_SETTLE_SECONDS)
                final_img = screenshot()
                transform = get_transform(config, final_img.size)
                final_box = scale_rect(get_detailed_result_capture_rect(config), transform, final_img.size)
                print(
                    f"{context}: detailed battle record ready "
                    f"(title_blue={latest_metrics['title_blue']:.3f}, "
                    f"detail_dark={latest_metrics['detail_dark']:.3f}, "
                    f"detail_edges={latest_metrics['detail_edges']:.3f}, "
                    f"rule={latest_metrics['readiness_rule']})"
                )
                return final_img.crop(final_box)
        else:
            stable_hits = 0

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            print(f"{context}: detailed battle record timeout; metrics={latest_metrics}")
            raise DetailPageTimeout(context, timeout_seconds)
        time.sleep(min(poll_seconds, remaining))


def crop_rects_from_image(config, img, rects):
    transform = get_transform(config, img.size)
    parts = []
    for rect in rects:
        box = scale_rect(rect, transform, img.size)
        parts.append(img.crop(box))
    return parts


def resize_to_width(img, width):
    if not width or img.width == width:
        return img
    height = round(img.height * width / img.width)
    return img.resize((width, height), Image.Resampling.LANCZOS)


def resize_to_height(img, height):
    if not height or img.height == height:
        return img
    width = round(img.width * height / img.height)
    return img.resize((width, height), Image.Resampling.LANCZOS)


def stitch(parts, config):
    output_width = int(config["output_width"])
    gap = int(config.get("gap_px", 0))
    background = config.get("background", "#20242a")
    parts = [resize_to_width(part, output_width) for part in parts]
    width = max(part.width for part in parts)
    height = sum(part.height for part in parts) + gap * max(0, len(parts) - 1)
    canvas = Image.new("RGB", (width, height), background)

    y = 0
    for part in parts:
        x = (width - part.width) // 2
        canvas.paste(part.convert("RGB"), (x, y))
        y += part.height + gap
    return canvas


def place_on_output_canvas(img, config, width_key, offset_key):
    output_width = int(config["output_width"])
    target_width = int(config.get(width_key, output_width))
    x_offset = int(config.get(offset_key, 0))
    target_width = max(1, min(output_width, target_width))
    fitted = resize_to_width(img, target_width)
    background = config.get("team_summary_background", config.get("background", "#20242a"))
    canvas = Image.new("RGB", (output_width, fitted.height), background)
    x = (output_width - fitted.width) // 2 + x_offset
    x = max(0, min(output_width - fitted.width, x))
    canvas.paste(fitted.convert("RGB"), (x, 0))
    return canvas


def make_research_row(cards, config):
    padding = int(config.get("research_row_padding", 32))
    gap = int(config.get("research_row_gap", 10))
    background = config.get("research_row_background", "#f7f8fa")
    align = config.get("research_card_align", "bottom")
    server = str(config.get("runtime_server", "cn")).strip().lower()
    regional_slot_width = 0
    if server in {"global", "hmt"}:
        regional_slot_width = int(config.get("research_card_slot_width_global_hmt", 0) or 0)
    layout_widths = [regional_slot_width if regional_slot_width > 0 else card.width for card in cards]
    width = sum(layout_widths) + gap * max(0, len(cards) - 1) + padding * 2
    height = max(card.height for card in cards)
    canvas = Image.new("RGB", (width, height), background)

    x = padding
    for card, layout_width in zip(cards, layout_widths):
        if align == "bottom":
            y = height - card.height
        elif align == "top":
            y = 0
        else:
            y = (height - card.height) // 2
        canvas.paste(card.convert("RGB"), (x, y))
        x += layout_width + gap
    return canvas


def cover_crop(img, size, center):
    target_w, target_h = size
    scale = max(target_w / img.width, target_h / img.height)
    resized = img.resize((round(img.width * scale), round(img.height * scale)), Image.Resampling.LANCZOS)
    cx = int(resized.width * float(center[0]))
    cy = int(resized.height * float(center[1]))
    left = max(0, min(resized.width - target_w, cx - target_w // 2))
    top = max(0, min(resized.height - target_h, cy - target_h // 2))
    return resized.crop((left, top, left + target_w, top + target_h))


def make_soft_mask(size, blur_radius):
    if blur_radius <= 0:
        return Image.new("L", size, 255)
    mask = Image.new("L", size, 0)
    inset = max(blur_radius * 2, 1)
    draw = ImageDraw.Draw(mask)
    draw.rectangle(
        (inset, inset, size[0] - inset - 1, size[1] - inset - 1),
        fill=255,
    )
    return mask.filter(ImageFilter.GaussianBlur(blur_radius))


def save_framed_output(final_img, config, output_path):
    if not config.get("framed_output", True):
        return

    bg_path = Path(config.get("framed_background", ""))
    if not bg_path.is_absolute():
        bg_path = Path(__file__).resolve().parent / bg_path
    if not bg_path.exists():
        stem = bg_path.with_suffix("")
        for suffix in (".png", ".jpg", ".jpeg"):
            candidate = stem.with_suffix(suffix)
            if candidate.exists():
                bg_path = candidate
                break
    if not bg_path.exists():
        print(f"framed background not found: {bg_path}")
        return

    margin_x = int(config.get("framed_margin_x", 86))
    margin_y = int(config.get("framed_margin_y", 96))
    frame_size = (final_img.width + margin_x * 2, final_img.height + margin_y * 2)
    center = config.get("framed_bg_center", [0.62, 0.5])

    bg = Image.open(bg_path).convert("RGB")
    frame = cover_crop(bg, frame_size, center).convert("RGBA")

    opacity = max(0.0, min(1.0, float(config.get("framed_opacity", 0.9))))
    edge_blur = max(0, int(config.get("framed_edge_blur", 10)))
    content = final_img.convert("RGBA")
    original_alpha = content.getchannel("A")
    opacity_mask = make_soft_mask(content.size, edge_blur)
    opacity_mask = opacity_mask.point(lambda value: round(value * opacity))
    alpha = ImageChops.multiply(original_alpha, opacity_mask)
    content.putalpha(alpha)
    frame.alpha_composite(content, (margin_x, margin_y))

    framed_path = output_path
    frame.convert("RGB").save(framed_path)
    print(f"framed: {framed_path}")


def save_part(img, output_dir, name):
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{name}.png"
    img.save(path)
    print(f"saved part: {path}")


def maybe_collect_garbage(config):
    if config.get("low_memory"):
        gc.collect()


def print_screen_context(config):
    first = screenshot()
    transform = get_transform(config, first.size)
    print(
        "screen: "
        f"{first.width}x{first.height}, "
        f"mode={transform['mode']}, "
        f"scale={transform['sx']:.4f}, "
        f"offset=({transform['ox']:.1f}, {transform['oy']:.1f})"
    )
    return transform


_SEASON_OCR = None
_SEASON_OCR_INITIALIZED = False


def get_season_ocr(config):
    global _SEASON_OCR, _SEASON_OCR_INITIALIZED
    if _SEASON_OCR_INITIALIZED:
        return _SEASON_OCR
    _SEASON_OCR_INITIALIZED = True
    tool_dir = Path(__file__).resolve().parent / "dataanalysis" / "arena_ocr_tool"
    if not tool_dir.exists():
        print(f"season cache: OCR tool not found: {tool_dir}")
        return None
    if str(tool_dir) not in sys.path:
        sys.path.insert(0, str(tool_dir))
    try:
        from recognizer.arena_ocr import ArenaOCRRecognizer

        ocr_config = config.get("ocr", {})
        cpu_threads = int(ocr_config.get("cpu_threads", config.get("season_ocr_cpu_threads", 2)))
        use_gpu = bool(ocr_config.get("use_gpu", False))
        _SEASON_OCR = ArenaOCRRecognizer(use_gpu=use_gpu, cpu_threads=cpu_threads)
        if not getattr(_SEASON_OCR, "available", False):
            print(f"season cache: OCR unavailable: {getattr(_SEASON_OCR, 'error', '')}")
            _SEASON_OCR = None
        return _SEASON_OCR
    except Exception as exc:
        print(f"season cache: OCR init failed: {exc}")
        _SEASON_OCR = None
        return None


def crop_rel(img, box):
    w, h = img.size
    left = max(0, min(w, int(w * box[0])))
    top = max(0, min(h, int(h * box[1])))
    right = max(0, min(w, int(w * box[2])))
    bottom = max(0, min(h, int(h * box[3])))
    if right <= left or bottom <= top:
        return img.crop((0, 0, 1, 1))
    return img.crop((left, top, right, bottom))


def normalize_player_name(text):
    text = str(text or "").strip()
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"[^\w\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]+", "", text)
    return text.lower()


def is_season_name_noise(text):
    raw = str(text or "").strip()
    cleaned = normalize_player_name(raw)
    if not cleaned or len(cleaned) > 30:
        return True
    if re.fullmatch(r"[\d.,kK%]+", raw):
        return True
    upper = raw.upper()
    noise_tokens = (
        "ID",
        "LV",
        "ROUND",
        "WIN",
        "LOSE",
        "VS",
        "GROUP",
        "ARENA",
        "TOP",
        "NO DATA",
        "NIKKE",
    )
    if any(token in upper for token in noise_tokens):
        return True
    cn_noise = (
        "服务器",
        "同步",
        "等级",
        "战斗",
        "结果",
        "战果",
        "战败",
        "部队",
        "作战",
        "人员",
        "时装",
        "现状",
        "冠军",
        "晋级",
        "挑战者",
        "空白",
    )
    return any(token in raw for token in cn_noise)


def ocr_text_items(ocr, img, region_name):
    if ocr is None:
        return []
    try:
        items = ocr.recognize_region(img.convert("RGB"), region_name)
    except Exception:
        return []
    result = []
    for item in items:
        text = str(getattr(item, "text", "")).strip()
        if not text:
            continue
        bbox = getattr(item, "bbox", []) or []
        xs = [float(point[0]) for point in bbox] if bbox else [0.0]
        ys = [float(point[1]) for point in bbox] if bbox else [0.0]
        result.append(
            {
                "text": text,
                "x": sum(xs) / len(xs),
                "y": sum(ys) / len(ys),
                "confidence": float(getattr(item, "confidence", 0.0) or 0.0),
                "region": region_name,
            }
        )
    return result


def ocr_nickname_candidates(ocr, img, region_name):
    if ocr is None:
        return []
    candidates = []
    try:
        readings = ocr.recognize_nickname_candidates(img.convert("RGB"), region_name)
    except Exception:
        readings = []
    for text, confidence, language in readings:
        text = str(text or "").strip()
        if is_season_name_noise(text):
            continue
        candidates.append(
            {
                "text": text,
                "confidence": float(confidence or 0.0),
                "language": str(language or ""),
                "x": img.width / 2,
                "y": img.height / 2,
                "region": region_name,
            }
        )
    for item in ocr_text_items(ocr, img, region_name):
        if not is_season_name_noise(item["text"]):
            candidates.append(item)
    return candidates


def recognize_profile_aliases(profile_part, config, ocr, fallback):
    aliases = []
    crops = [
        crop_rel(profile_part, (0.16, 0.36, 0.74, 0.59)),
        crop_rel(profile_part, (0.12, 0.32, 0.82, 0.66)),
        crop_rel(profile_part, (0.00, 0.25, 0.88, 0.70)),
    ]
    for index, part in enumerate(crops, 1):
        for item in ocr_nickname_candidates(ocr, part, f"profile_name_{index}"):
            text = item["text"]
            if normalize_player_name(text) and text not in aliases:
                aliases.append(text)
    if fallback not in aliases:
        aliases.append(fallback)
    return aliases[:8]


def player_alias_score(candidate, player):
    candidate_norm = normalize_player_name(candidate)
    if not candidate_norm:
        return 0.0
    best = 0.0
    for alias in player.get("aliases", []):
        alias_norm = normalize_player_name(alias)
        if not alias_norm:
            continue
        if candidate_norm == alias_norm:
            return 1.0
        if candidate_norm in alias_norm or alias_norm in candidate_norm:
            best = max(best, 0.92)
        best = max(best, difflib.SequenceMatcher(None, candidate_norm, alias_norm).ratio())
    return best


def match_player_details_from_candidates(candidates, players, min_score=0.62):
    details = []
    for item in candidates:
        text = item.get("text", "")
        text_norm = normalize_player_name(text)
        if not text_norm:
            continue

        scored = sorted(
            ((player_alias_score(text_norm, player), player) for player in players),
            key=lambda entry: entry[0],
            reverse=True,
        )
        if not scored or scored[0][0] < min_score:
            continue

        best_score, best_player = scored[0]
        second_score = scored[1][0] if len(scored) > 1 else 0.0
        details.append(
            {
                "score": best_score,
                "second_score": second_score,
                "margin": best_score - second_score,
                "x": float(item.get("x", 0.0)),
                "player": best_player,
                "text": text_norm,
            }
        )

    details.sort(key=lambda value: (-value["score"], value["x"]))
    chosen = []
    seen_keys = set()
    for item in details:
        key = item["player"].get("key")
        if key in seen_keys:
            continue
        chosen.append(item)
        seen_keys.add(key)
        if len(chosen) >= 2:
            break
    chosen.sort(key=lambda value: value["x"])
    return chosen


def match_players_from_candidates(candidates, players, fallback_players=None, min_score=0.62):
    result = [entry["player"] for entry in match_player_details_from_candidates(candidates, players, min_score)]
    if len(result) < 2 and fallback_players:
        for player in fallback_players:
            if player and player.get("key") not in {picked.get("key") for picked in result}:
                result.append(player)
            if len(result) >= 2:
                break
    return result[:2]


def result_name_candidates_from_screen(config, ocr):
    img = screenshot()
    parts = []
    if "season_result_name_probe" in config.get("crops", {}):
        parts.extend(crop_rects_from_image(config, img, [config["crops"]["season_result_name_probe"]]))
    parts.append(crop_rel(img, (0.38, 0.18, 0.62, 0.52)))
    parts.append(crop_rel(img, (0.35, 0.25, 0.65, 0.72)))

    items = []
    for index, part in enumerate(parts, 1):
        candidates = ocr_nickname_candidates(ocr, part, f"season_result_names_{index}")
        for item in candidates:
            item = dict(item)
            item["x"] = float(item.get("x", 0.0)) + (index - 1) * 0.01
            items.append(item)
    return items


def add_player_alias(player, alias):
    alias_norm = normalize_player_name(alias)
    if not alias_norm or is_season_name_noise(alias_norm):
        return False
    aliases = player.setdefault("aliases", [])
    for existing in aliases:
        if normalize_player_name(existing) == alias_norm:
            return False
    aliases.append(alias_norm)
    return True


def reinforce_pair_aliases_from_result(pair, candidates, min_score=0.78):
    """Use battle-result names as aliases only when they strongly resemble the expected pair."""
    if not pair:
        return
    for item in candidates:
        text = normalize_player_name(item.get("text", ""))
        if not text:
            continue
        scored = sorted(
            ((player_alias_score(text, player), player) for player in pair if player),
            key=lambda entry: entry[0],
            reverse=True,
        )
        if not scored or scored[0][0] < min_score:
            continue
        second_score = scored[1][0] if len(scored) > 1 else 0.0
        if scored[0][0] >= 0.94 or (scored[0][0] - second_score) >= 0.12:
            add_player_alias(scored[0][1], text)


def result_pair_confidence(pair, candidates):
    if len(pair) < 2:
        return 0.0
    scores = []
    for player in pair[:2]:
        best = 0.0
        for item in candidates:
            best = max(best, player_alias_score(item.get("text", ""), player))
        scores.append(best)
    return min(scores) if scores else 0.0


def detect_result_winner_side(config):
    """Return 0 for left player win, 1 for right player win, or None if unclear."""
    try:
        part = crop_current(config, "group_simple_result").convert("RGB")
    except Exception:
        return None
    width, height = part.size
    if width < 10 or height < 10:
        return None

    left = part.crop((0, 0, width // 2, height))
    right = part.crop((width // 2, 0, width, height))

    def cyan_win_score(img):
        score = 0
        for r, g, b in img.getdata():
            if g >= 130 and b >= 145 and r <= 125 and (b - r) >= 45 and (g - r) >= 25:
                score += 1
        return score

    left_score = cyan_win_score(left)
    right_score = cyan_win_score(right)
    print(f"winner detect: left_cyan={left_score}, right_cyan={right_score}")
    if max(left_score, right_score) < 20:
        return None
    if abs(left_score - right_score) < max(12, max(left_score, right_score) * 0.12):
        return None
    return 0 if left_score > right_score else 1


def fallback_pair(players, indexes):
    result = []
    for index in indexes:
        if 0 <= index < len(players):
            result.append(players[index])
    return result


def player_image(player):
    image = player.get("image")
    if image is not None:
        return image
    image_path = player.get("image_path")
    if image_path:
        with Image.open(image_path) as img:
            return img.convert("RGB").copy()
    raise KeyError("cached player has neither image nor image_path")


def capture_player_image(config, parts_dir, label="player", close_profile=None, return_metadata=False, ocr=None):
    timings = config["timing"]
    round_tabs = config["clicks"]["round_tabs"]
    if close_profile is None:
        close_profile = bool(config.get("close_profile_after_capture"))

    round_parts = []
    for round_no in ["1", "2", "3", "4", "5"]:
        print(f"{label}: capturing Round {int(round_no):02d}")
        transform = get_transform(config, screenshot().size)
        click(round_tabs[round_no], transform)
        time.sleep(float(timings["after_round_click_seconds"]))
        part = crop_current(config, "round_lineup")
        round_parts.append(part)
        if config.get("save_parts"):
            save_part(part, parts_dir, f"{label}_round_{int(round_no):02d}")

    print(f"{label}: opening profile")
    transform = get_transform(config, screenshot().size)
    click(config["clicks"]["avatar"], transform)
    profile_part = wait_for_profile_basic_page(config, label)
    aliases = []
    if return_metadata:
        aliases = recognize_profile_aliases(profile_part, config, ocr, label)
    team_summary_part = place_on_output_canvas(
        crop_current(config, "team_summary"),
        config,
        "team_summary_output_width",
        "team_summary_x_offset",
    )
    if config.get("save_parts"):
        save_part(profile_part, parts_dir, f"{label}_profile_basic")
        save_part(team_summary_part, parts_dir, f"{label}_team_summary")

    print(f"{label}: opening outpost tab")
    transform = get_transform(config, screenshot().size)
    click(config["clicks"]["outpost_tab"], transform)
    time.sleep(float(timings["after_outpost_click_seconds"]))
    outpost_img = screenshot()
    sync_level_part = crop_rects_from_image(config, outpost_img, [config["crops"]["sync_level"]])[0]
    research_cards = crop_rects_from_image(config, outpost_img, get_research_card_rects(config))
    research_row_part = make_research_row(research_cards, config)
    if config.get("save_parts"):
        save_part(sync_level_part, parts_dir, f"{label}_sync_level")
        save_part(research_row_part, parts_dir, f"{label}_research_row")
        for index, card in enumerate(research_cards, 1):
            save_part(card, parts_dir, f"{label}_research_card_{index:02d}")

    if close_profile:
        transform = get_transform(config, screenshot().size)
        click(config["clicks"]["profile_close"], transform)
        time.sleep(float(timings["after_profile_close_seconds"]))

    final_img = stitch([profile_part, sync_level_part] + round_parts + [team_summary_part, research_row_part], config)
    if return_metadata:
        return {
            "image": final_img,
            "profile": profile_part,
            "aliases": aliases,
            "nickname": aliases[0] if aliases else label,
        }
    return final_img


def append_bottom(base, bottom, config):
    width = max(base.width, bottom.width)
    height = base.height + bottom.height
    canvas = Image.new("RGB", (width, height), config.get("background", "#20242a"))
    canvas.paste(base.convert("RGB"), ((width - base.width) // 2, 0))
    canvas.paste(bottom.convert("RGB"), ((width - bottom.width) // 2, base.height))
    return canvas


def stitch_columns(parts, config):
    gap = int(config.get("duo_column_gap", 18))
    width = sum(part.width for part in parts) + gap * max(0, len(parts) - 1)
    height = max(part.height for part in parts)
    canvas = Image.new("RGB", (width, height), config.get("background", "#20242a"))
    x = 0
    for part in parts:
        canvas.paste(part.convert("RGB"), (x, 0))
        x += part.width + gap
    return canvas


def stitch_grid(parts, columns, config):
    if not parts:
        raise ValueError("no parts to stitch")
    gap = int(config.get("group_grid_gap", config.get("duo_column_gap", 18)))
    return stitch_grid_with_gap(parts, columns, gap, config.get("background", "#20242a"))


def stitch_grid_with_gap(parts, columns, gap, background):
    if not parts:
        raise ValueError("no parts to stitch")
    columns = max(1, int(columns))
    rows = (len(parts) + columns - 1) // columns
    cell_w = max(part.width for part in parts)
    cell_h = max(part.height for part in parts)
    width = columns * cell_w + gap * (columns - 1)
    height = rows * cell_h + gap * (rows - 1)
    canvas = Image.new("RGB", (width, height), background)
    for index, part in enumerate(parts):
        row = index // columns
        col = index % columns
        x = col * (cell_w + gap) + (cell_w - part.width) // 2
        y = row * (cell_h + gap)
        canvas.paste(part.convert("RGB"), (x, y))
    return canvas


def stitch_vertical(parts, config, gap=None, background=None):
    gap = int(config.get("gap_px", 0) if gap is None else gap)
    background = config.get("background", "#20242a") if background is None else background
    width = max(part.width for part in parts)
    height = sum(part.height for part in parts) + gap * max(0, len(parts) - 1)
    canvas = Image.new("RGB", (width, height), background)
    y = 0
    for part in parts:
        canvas.paste(part.convert("RGB"), ((width - part.width) // 2, y))
        y += part.height + gap
    return canvas


def stitch_pair_with_data(left, data, right, config, mode):
    gap = int(config.get("group_data_gap", config.get("group_grid_gap", 18)))
    if mode == "detailed":
        data = resize_to_height(data, max(left.height, right.height))
    height = max(left.height, data.height, right.height)
    width = left.width + data.width + right.width + gap * 2
    canvas = Image.new("RGB", (width, height), config.get("background", "#20242a"))
    x = 0
    for part in (left, data, right):
        y = (height - part.height) // 2
        canvas.paste(part.convert("RGB"), (x, y))
        x += part.width + gap
    return canvas


def stitch_group_pairs_with_data(player_images, data_parts, config, mode, single_row=False):
    pairs = []
    pair_count = min(len(data_parts), len(player_images) // 2)
    if pair_count < 1:
        raise ValueError("not enough group post-data parts to stitch")
    for pair_index in range(pair_count):
        left = player_images[pair_index * 2]
        right = player_images[pair_index * 2 + 1]
        pairs.append(stitch_pair_with_data(left, data_parts[pair_index], right, config, mode))

    row_gap = int(config.get("group_grid_gap", 18))
    if len(pairs) == 1:
        return pairs[0]
    if single_row:
        column_gap = int(config.get("group_data_column_gap", row_gap))
        return stitch_grid_with_gap(
            pairs,
            len(pairs),
            column_gap,
            config.get("background", "#20242a"),
        )
    if len(pairs) == 2:
        return stitch_vertical(pairs, config, gap=row_gap, background=config.get("background", "#20242a"))

    column_gap = int(config.get("group_data_column_gap", row_gap))
    cols = 2
    cell_w = max(part.width for part in pairs)
    cell_h = max(part.height for part in pairs)
    stage_gap = column_gap
    canvas = Image.new(
        "RGB",
        (cell_w * cols + column_gap, cell_h * 2 + stage_gap),
        config.get("background", "#20242a"),
    )
    for index, part in enumerate(pairs):
        row = index // cols
        col = index % cols
        x = col * (cell_w + column_gap) + (cell_w - part.width) // 2
        y = row * (cell_h + stage_gap)
        canvas.paste(part.convert("RGB"), (x, y))
    return canvas


def stitch_round_robin_capture(player_images, config, post_result=None):
    """Compose four player pages, optionally preceded by the GROUP result panel."""
    gap = int(config.get("round_robin_grid_gap", 13))
    background = config.get("round_robin_background", "#FFFFFF")
    players = stitch_grid_with_gap(player_images, 4, gap, background)
    if post_result is None:
        return players

    height = max(post_result.height, players.height)
    width = post_result.width + gap + players.width
    canvas = Image.new("RGB", (width, height), background)
    canvas.paste(post_result.convert("RGB"), (0, (height - post_result.height) // 2))
    canvas.paste(players.convert("RGB"), (post_result.width + gap, (height - players.height) // 2))
    return canvas


def round_robin_player_capture_config(config):
    """Use the round-robin canvas colour inside each player composition too."""
    player_config = dict(config)
    player_config["background"] = config.get(
        "round_robin_background", config.get("background", "#FFFFFF")
    )
    return player_config


def make_support_status_part(img, config, target_width):
    part = crop_rects_from_image(config, img, [config["crops"]["support_status"]])[0]
    fitted = resize_to_width(part, target_width)
    canvas = Image.new("RGB", (target_width, fitted.height), config.get("support_status_background", "#f7f8fa"))
    canvas.paste(fitted.convert("RGB"), ((target_width - fitted.width) // 2, 0))
    return canvas


def should_click_modal_backdrop(config):
    return str(config.get("runtime_server", "cn")).strip().lower() in {"global", "hmt"}


def dismiss_current_popup(config, count=1):
    delay = float(config["timing"].get("after_escape_seconds", 0.45))
    side_points = config.get("clicks", {}).get("modal_dismiss_side_points", [])
    use_backdrop_click = should_click_modal_backdrop(config)
    if use_backdrop_click and not side_points:
        raise SystemExit("modal_dismiss_side_points is required for Global and HMT popup dismissal")

    for index in range(max(1, int(count))):
        if use_backdrop_click:
            transform = get_transform(config, screenshot().size)
            click(side_points[index % len(side_points)], transform)
        else:
            send_key(VK_ESCAPE)
        time.sleep(delay)


def press_escape_twice(config):
    dismiss_current_popup(config, count=2)


def run_capture(config, output_path, parts_dir):
    print_screen_context(config)
    final_img = capture_player_image(config, parts_dir, "single")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    final_img.save(output_path)
    save_framed_output(final_img, config, output_path)
    print(f"done: {output_path}")


def run_support_duo_capture(config, output_path, parts_dir, include_support_status=False):
    transform = print_screen_context(config)
    timings = config["timing"]
    support_screen_img = screenshot()

    print("support: opening left player")
    click(config["clicks"]["support_left_avatar"], transform)
    time.sleep(float(timings.get("after_support_avatar_click_seconds", 1.0)))
    left_img = capture_player_image(config, parts_dir, "support_left", close_profile=False)

    print("support: returning to support screen")
    press_escape_twice(config)
    transform = get_transform(config, screenshot().size)

    print("support: opening right player")
    click(config["clicks"]["support_right_avatar"], transform)
    time.sleep(float(timings.get("after_support_avatar_click_seconds", 1.0)))
    right_img = capture_player_image(config, parts_dir, "support_right", close_profile=False)

    final_img = stitch_columns([left_img, right_img], config)
    if include_support_status:
        status_part = make_support_status_part(support_screen_img, config, final_img.width)
        final_img = append_bottom(final_img, status_part, config)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    final_img.save(output_path)
    save_framed_output(final_img, config, output_path)
    print(f"done: {output_path}")


def get_support_result_avatar_points(config, with_stage_tabs):
    clicks = config["clicks"]
    key = (
        "support_result_avatars_with_stage_tabs"
        if with_stage_tabs
        else "support_result_avatars_without_stage_tabs"
    )
    points = clicks.get(key, [])
    if len(points) != 2:
        raise SystemExit(f"{key} must contain exactly two player avatar points")
    return points


def get_support_result_detail_buttons(config, with_stage_tabs):
    clicks = config["clicks"]
    key = (
        "support_result_detail_buttons_with_stage_tabs"
        if with_stage_tabs
        else "support_result_detail_buttons_without_stage_tabs"
    )
    fallback = (
        clicks.get("group_32_detail_buttons", clicks.get("group_detail_buttons", []))
        if with_stage_tabs
        else clicks.get("group_detail_buttons", [])
    )
    return clicks.get(key, fallback)


def capture_support_result_data(config, parts_dir, detailed, with_stage_tabs):
    """Capture the active pair-result popup without changing its stage tab."""
    if not detailed:
        part = crop_current(config, "group_simple_result")
        if config.get("save_parts"):
            save_part(part, parts_dir, "support_result_simple")
        return part

    detail_buttons = get_support_result_detail_buttons(config, with_stage_tabs)
    if not detail_buttons:
        raise SystemExit("support-result detailed battle buttons are not configured")

    round_parts = []
    for detail_index, detail_point in enumerate(detail_buttons, 1):
        print(f"support result detailed: opening detail {detail_index}/{len(detail_buttons)}")
        transform = get_transform(config, screenshot().size)
        click(detail_point, transform)
        part = wait_for_detailed_result_page(config, f"support result detailed {detail_index}")
        round_parts.append(part)
        if config.get("save_parts"):
            save_part(part, parts_dir, f"support_result_detailed_{detail_index:02d}")
        press_escape(config, 1)

    return stitch_vertical(round_parts, config, gap=0, background="#f7f8fa")


def run_support_result_capture(config, output_path, parts_dir, detailed=True):
    """Capture both profiles and the active two-player result popup as one pair block."""
    transform = print_screen_context(config)
    timings = config["timing"]
    with_stage_tabs = has_group_stage_tabs(config)
    avatar_points = get_support_result_avatar_points(config, with_stage_tabs)
    layout_label = "with stage tabs" if with_stage_tabs else "without stage tabs"
    print(f"support result: {layout_label}")

    player_images = []
    for index, point in enumerate(avatar_points, 1):
        print(f"support result: opening player {index}/2")
        click(point, transform)
        time.sleep(float(timings.get("after_support_avatar_click_seconds", 1.0)))
        player_images.append(
            capture_player_image(config, parts_dir, f"support_result_{index:02d}", close_profile=False)
        )
        print("support result: returning to pair result")
        press_escape_twice(config)
        transform = get_transform(config, screenshot().size)

    data_part = capture_support_result_data(config, parts_dir, detailed, with_stage_tabs)
    mode = "detailed" if detailed else "simple"
    final_img = stitch_group_pairs_with_data(
        player_images,
        [data_part],
        config,
        mode,
        single_row=True,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    final_img.save(output_path)
    save_framed_output(final_img, config, output_path)
    print(f"done: {output_path}")


def press_escape(config, count=1):
    dismiss_current_popup(config, count=count)


def get_group_result_buttons(config, group_size, bracket_mode="group"):
    clicks = config["clicks"]
    group_size = int(group_size)
    if bracket_mode == "top8":
        if group_size == 4:
            return clicks.get("top8_4_result_buttons", [])
        return clicks.get("top8_result_buttons", [])
    if group_size == 4:
        return clicks.get("group_32_result_buttons", [])
    if group_size == 2:
        return clicks.get("group_16_result_buttons", [])
    return clicks.get("group_result_buttons", [])


def purple_pixel_score(img):
    score = 0
    for r, g, b in img.convert("RGB").getdata():
        if r > 95 and b > 125 and g < 125 and (b - g) > 45 and (r - g) > 25:
            score += 1
    return score


def pink_pixel_score(img):
    score = 0
    for r, g, b in img.convert("RGB").getdata():
        if r > 180 and b > 100 and g < 125 and (r - g) > 60 and (b - g) > 30:
            score += 1
    return score


def select_colored_result_button(config, button_key, probe_key, score_fn, label):
    buttons = config["clicks"].get(button_key, [])
    probes = config.get("crops", {}).get(probe_key, [])
    if not buttons:
        return None
    if len(probes) < len(buttons):
        raise ValueError(f"{probe_key} must contain one probe for each result button")

    img = screenshot()
    transform = get_transform(config, img.size)
    scored = []
    for index, rect in enumerate(probes[:len(buttons)]):
        box = scale_rect(rect, transform, img.size)
        scored.append((score_fn(img.crop(box)), index))
    scored.sort(reverse=True)
    best_score, best_index = scored[0]
    print(f"{label}: result button {best_index + 1}/{len(buttons)}, color_score={best_score}")
    return buttons[best_index]


def get_group_16_winner_result_button(config):
    return select_colored_result_button(
        config,
        "group_16_winner_result_buttons",
        "group_16_winner_result_button_probes",
        purple_pixel_score,
        "group 16",
    )


def get_top8_final_result_button(config):
    return select_colored_result_button(
        config,
        "top8_final_result_buttons",
        "top8_final_result_button_probes",
        pink_pixel_score,
        "top8 final",
    )


def get_group_result_sequence(config, group_size, bracket_mode="group"):
    group_size = int(group_size)
    if bracket_mode == "top8":
        if group_size == 2:
            point = get_top8_final_result_button(config)
            return [point] if point else []
        return get_group_result_buttons(config, group_size, bracket_mode)
    if group_size == 2:
        point = get_group_16_winner_result_button(config)
        return [point] if point else []
    return get_group_result_buttons(config, group_size, bracket_mode)


def has_group_stage_tabs(config):
    crop_name = "group_result_stage_tabs_probe"
    if crop_name not in config.get("crops", {}):
        return False
    probe = crop_current(config, crop_name).convert("RGB")
    blue_pixels = 0
    for r, g, b in probe.getdata():
        if b > 165 and g > 125 and r < 115 and (b - r) > 65 and (g - r) > 35:
            blue_pixels += 1
    threshold = max(18, probe.width * probe.height * 0.00055)
    return blue_pixels > threshold


def prepare_group_result_page(config, group_size, select_stage_tab=True):
    group_size = int(group_size)
    if group_size not in (2, 4):
        return False
    has_tabs = has_group_stage_tabs(config)
    if not has_tabs:
        return False
    if not select_stage_tab:
        return True

    target = "group_32_result_stage_tab" if group_size == 4 else "group_16_result_stage_tab"
    point = config["clicks"].get(target)
    if not point:
        return has_tabs
    print(f"group post: selecting {group_size * 8}-strong stage tab")
    transform = get_transform(config, screenshot().size)
    click(point, transform)
    time.sleep(float(config["timing"].get("after_group_result_click_seconds", 0.9)))
    return has_tabs


def get_group_detail_buttons(config, group_size, with_stage_tabs):
    clicks = config["clicks"]
    if int(group_size) in (2, 4) and with_stage_tabs:
        return clicks.get("group_32_detail_buttons", clicks.get("group_detail_buttons", []))
    return clicks.get("group_detail_buttons", [])


def collect_group_simple_results(config, parts_dir, group_size, bracket_mode="group"):
    timings = config["timing"]
    results = []
    result_buttons = get_group_result_sequence(config, group_size, bracket_mode)
    for index, point in enumerate(result_buttons, 1):
        print(f"group post simple: opening result {index}/{len(result_buttons)}")
        transform = get_transform(config, screenshot().size)
        click(point, transform)
        time.sleep(float(timings.get("after_bracket_result_click_seconds", 1.0)))
        prepare_group_result_page(config, group_size, select_stage_tab=(int(group_size) != 2))
        part = crop_current(config, "group_simple_result")
        results.append(part)
        if config.get("save_parts"):
            save_part(part, parts_dir, f"group_simple_result_{index:02d}")
        press_escape(config, 1)
    return results


def collect_group_detailed_results(config, parts_dir, group_size, bracket_mode="group"):
    timings = config["timing"]
    result_parts = []
    result_buttons = get_group_result_sequence(config, group_size, bracket_mode)
    for result_index, point in enumerate(result_buttons, 1):
        print(f"group post detailed: opening result {result_index}/{len(result_buttons)}")
        transform = get_transform(config, screenshot().size)
        click(point, transform)
        time.sleep(float(timings.get("after_bracket_result_click_seconds", 1.0)))
        with_stage_tabs = prepare_group_result_page(config, group_size, select_stage_tab=(int(group_size) != 2))
        detail_buttons = get_group_detail_buttons(config, group_size, with_stage_tabs)

        round_parts = []
        for detail_index, detail_point in enumerate(detail_buttons, 1):
            print(f"group post detailed: opening detail {result_index}.{detail_index}")
            transform = get_transform(config, screenshot().size)
            click(detail_point, transform)
            part = wait_for_detailed_result_page(config, f"group post detailed {result_index}.{detail_index}")
            round_parts.append(part)
            if config.get("save_parts"):
                save_part(part, parts_dir, f"group_detailed_result_{result_index:02d}_{detail_index:02d}")
            press_escape(config, 1)

        result_parts.append(stitch_vertical(round_parts, config, gap=0, background="#f7f8fa"))
        press_escape(config, 1)
    return result_parts


def capture_group_image(
    config,
    parts_dir,
    group_size,
    post_data_mode="none",
    part_prefix=None,
    return_to_group=False,
    bracket_mode="group",
    single_row=False,
):
    transform = get_transform(config, screenshot().size)
    timings = config["timing"]
    if bracket_mode == "top8":
        group_map = {
            8: ("top8_avatars", 4, "top8"),
            4: ("top8_4_avatars", 4, "top4"),
            2: ("top8_final_avatars", 2, "top2"),
        }
    else:
        group_map = {
            8: ("group_64_avatars", 4, "64"),
            4: ("group_32_avatars", 4, "32"),
            2: ("group_16_avatars", 2, "16"),
        }
    key, columns, round_label = group_map.get(int(group_size), (None, 2, str(group_size)))
    points = config["clicks"].get(key, [])
    if not points:
        raise SystemExit(f"group {round_label} is not configured yet")

    player_images = []
    for index, point in enumerate(points, 1):
        print(f"group {round_label}: opening player {index}/{len(points)}")
        click(point, transform)
        time.sleep(float(timings.get("after_group_avatar_click_seconds", 1.0)))
        prefix = f"group{round_label}_{index:02d}" if part_prefix is None else f"{part_prefix}_{index:02d}"
        player_images.append(
            capture_player_image(config, parts_dir, prefix, close_profile=False)
        )
        if index < len(points) or post_data_mode != "none" or return_to_group:
            print(f"group {round_label}: returning to group screen")
            press_escape_twice(config)
            transform = get_transform(config, screenshot().size)

    if post_data_mode == "simple":
        data_parts = collect_group_simple_results(config, parts_dir, group_size, bracket_mode)
        return stitch_group_pairs_with_data(player_images, data_parts, config, "simple", single_row)
    if post_data_mode == "detailed":
        data_parts = collect_group_detailed_results(config, parts_dir, group_size, bracket_mode)
        return stitch_group_pairs_with_data(player_images, data_parts, config, "detailed", single_row)
    return stitch_grid(player_images, len(player_images) if single_row else columns, config)


def run_group_capture(config, output_path, parts_dir, group_size, post_data_mode="none"):
    print_screen_context(config)
    final_img = capture_group_image(
        config,
        parts_dir,
        group_size,
        post_data_mode,
        return_to_group=True,
        single_row=(int(group_size) in (2, 4)),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    final_img.save(output_path)
    save_framed_output(final_img, config, output_path)
    print(f"done: {output_path}")


def run_round_robin_capture(config, output_path, parts_dir, include_post_result=False):
    """Collect the four players shown on a round-robin overview in display order."""
    transform = print_screen_context(config)
    timings = config["timing"]
    points = config["clicks"].get("round_robin_avatars", [])
    if len(points) != 4:
        raise SystemExit("round_robin_avatars must contain exactly four player avatar points")

    post_result = None
    if include_post_result:
        print("round-robin: capturing post-match result overview")
        post_result = capture_round_robin_post_result(config)

    player_config = round_robin_player_capture_config(config)
    player_images = []
    for index, point in enumerate(points, 1):
        print(f"round-robin: opening player {index}/4")
        click(point, transform)
        time.sleep(float(timings.get("after_group_avatar_click_seconds", 1.0)))
        player_images.append(
            capture_player_image(
                player_config,
                parts_dir,
                f"round_robin_{index:02d}",
                close_profile=False,
            )
        )

        # Return to the overview after every player, including the last one.
        # CN uses Esc; Global and HMT reuse the established backdrop-click path.
        print("round-robin: returning to overview")
        press_escape_twice(config)
        transform = get_transform(config, screenshot().size)

    final_img = stitch_round_robin_capture(player_images, config, post_result)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    final_img.save(output_path)
    print(f"done: {output_path}")


def round_robin_group_output_path(output_path, group_index):
    """Build a non-destructive deep-compressed JPEG output path for one GROUP."""
    stem = f"Group{int(group_index):02d}-{output_path.stem}"
    candidate = output_path.with_name(f"{stem}.jpg")
    if not candidate.exists():
        return candidate
    for suffix in range(2, 1000):
        candidate = output_path.with_name(f"{stem}-{suffix}.jpg")
        if not candidate.exists():
            return candidate
    stamp = datetime.now().strftime("%H%M%S")
    return output_path.with_name(f"{stem}-{stamp}.jpg")


def save_round_robin_deep_jpeg(image, output_path, config):
    """Match the image tool's deep-compression preset without launching it 64 times."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(
        output_path,
        format="JPEG",
        quality=78,
        subsampling=2,
        optimize=True,
    )
    maybe_collect_garbage(config)


def select_round_robin_group(config, group_index):
    if not 1 <= int(group_index) <= 64:
        raise ValueError("round-robin GROUP must be between 1 and 64")

    clicks = config["clicks"]
    timings = config["timing"]
    selector = clicks.get("round_robin_group_selector")
    grid_origin = clicks.get("round_robin_group_grid_origin")
    grid_step = clicks.get("round_robin_group_grid_step")
    confirm = clicks.get("round_robin_group_confirm")
    if not selector or not grid_origin or not grid_step or not confirm:
        raise SystemExit("round-robin GROUP selector coordinates are missing")

    delay = float(timings.get("after_group_tab_click_seconds", 0.8))
    transform = get_transform(config, screenshot().size)
    click(selector, transform)
    time.sleep(delay)

    index = int(group_index) - 1
    point = [
        int(grid_origin[0]) + (index % 5) * int(grid_step[0]),
        int(grid_origin[1]) + (index // 5) * int(grid_step[1]),
    ]
    transform = get_transform(config, screenshot().size)
    click(point, transform)
    time.sleep(delay)
    transform = get_transform(config, screenshot().size)
    click(confirm, transform)
    time.sleep(
        float(timings.get("after_round_robin_group_switch_seconds", 1.3))
    )


def capture_round_robin_group_image(config, parts_dir, group_index, include_post_result=False):
    """Capture one selected round-robin GROUP and return to its overview."""
    transform = print_screen_context(config)
    timings = config["timing"]
    points = config["clicks"].get("round_robin_avatars", [])
    if len(points) != 4:
        raise SystemExit("round_robin_avatars must contain exactly four player avatar points")

    post_result = None
    if include_post_result:
        print(f"round-robin: GROUP{group_index:02d} capturing post-match result overview")
        post_result = capture_round_robin_post_result(config)

    player_config = round_robin_player_capture_config(config)
    player_images = []
    for player_index, point in enumerate(points, 1):
        print(f"round-robin: GROUP{group_index:02d} opening player {player_index}/4")
        click(point, transform)
        time.sleep(float(timings.get("after_group_avatar_click_seconds", 1.0)))
        player_images.append(
            capture_player_image(
                player_config,
                parts_dir,
                f"round_robin_group{group_index:02d}_{player_index:02d}",
                close_profile=False,
            )
        )

        # Return to the selected overview after every profile. CN uses Esc;
        # Global/HMT reuse the existing safe backdrop-click route.
        print(f"round-robin: GROUP{group_index:02d} returning to overview")
        press_escape_twice(config)
        transform = get_transform(config, screenshot().size)

    return stitch_round_robin_capture(player_images, config, post_result)


def run_all_round_robin_groups_capture(
    config,
    output_path,
    parts_dir,
    start_group=1,
    include_post_result=False,
):
    """Select and export each requested round-robin GROUP as an individual JPEG."""
    start_group = int(start_group)
    if not 1 <= start_group <= 64:
        raise SystemExit("round-robin start GROUP must be between 1 and 64")

    print(f"round-robin-all: starting from GROUP{start_group:02d}/64")
    for group_index in range(start_group, 65):
        print(f"round-robin-all: selecting GROUP{group_index:02d}/64")
        select_round_robin_group(config, group_index)
        final_img = capture_round_robin_group_image(
            config,
            parts_dir / f"group{group_index:02d}",
            group_index,
            include_post_result,
        )
        group_output = round_robin_group_output_path(output_path, group_index)
        save_round_robin_deep_jpeg(final_img, group_output, config)
        print(f"round-robin-all: GROUP{group_index:02d}/64 saved: {group_output}")


def run_top8_capture(config, output_path, parts_dir, top8_size, post_data_mode="none"):
    print_screen_context(config)
    final_img = capture_group_image(
        config,
        parts_dir,
        int(top8_size),
        post_data_mode,
        return_to_group=True,
        bracket_mode="top8",
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    final_img.save(output_path)
    save_framed_output(final_img, config, output_path)
    print(f"done: {output_path}")


def stitch_pyramid_layers(layers, config):
    gap = int(config.get("top8_pyramid_layer_gap", config.get("all_groups_grid_gap", 56)))
    width = max(layer.width for layer in layers)
    height = sum(layer.height for layer in layers) + gap * max(0, len(layers) - 1)
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    y = 0
    for layer in layers:
        canvas.alpha_composite(layer.convert("RGBA"), ((width - layer.width) // 2, y))
        y += layer.height + gap
    return canvas


def run_top8_pyramid_capture(config, output_path, parts_dir, post_data_mode="none"):
    print_screen_context(config)
    stage_images = {}
    for size in (8, 4, 2):
        print(f"top8 pyramid: capturing stage size {size}")
        stage_images[size] = capture_group_image(
            config,
            parts_dir / f"top{size}",
            size,
            post_data_mode,
            part_prefix=f"top{size}",
            return_to_group=True,
            bracket_mode="top8",
            single_row=True,
        )
    final_img = stitch_pyramid_layers(
        [stage_images[2], stage_images[4], stage_images[8]],
        config,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    final_img.save(output_path)
    save_framed_output(final_img, config, output_path)
    print(f"done: {output_path}")


def run_all_groups_capture(config, output_path, parts_dir, group_size, post_data_mode="none"):
    transform = print_screen_context(config)
    timings = config["timing"]
    tabs = config["clicks"].get("group_tabs", [])
    ratios = config["clicks"].get("group_tab_ratios", [])
    if len(tabs) < 8 and len(ratios) < 8:
        raise SystemExit("group_tabs must contain GROUP01-GROUP08 click points")
    if int(group_size) not in (2, 4, 8):
        raise SystemExit("all groups capture is currently available for 64/32/16 group modes only")

    group_images = []
    for group_index in range(1, 9):
        print(f"all groups: switching to GROUP{group_index:02d}/08")
        click_group_tab(config, group_index, transform)
        time.sleep(float(timings.get("after_group_tab_click_seconds", 0.8)))
        group_images.append(
            capture_group_image(
                config,
                parts_dir / f"group{group_index:02d}",
                group_size,
                post_data_mode,
                part_prefix=f"group{group_index:02d}",
                return_to_group=True,
                single_row=(int(group_size) in (2, 4)),
            )
        )
        transform = get_transform(config, screenshot().size)

    gap = int(config.get("all_groups_grid_gap", config.get("group_grid_gap", 18)))
    columns = 8 if int(group_size) == 2 else 4
    final_img = stitch_grid_with_gap(group_images, columns, gap, config.get("background", "#20242a"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    final_img.save(output_path)
    save_framed_output(final_img, config, output_path)
    print(f"done: {output_path}")


def output_with_suffix(output_path, suffix):
    return output_path.with_name(f"{output_path.stem}_{suffix}{output_path.suffix}")


def season_named_output_path(output_path, title):
    main_title = "64进32全部战斗数据（详）"
    stem = output_path.stem
    if stem.startswith(main_title):
        tail = stem[len(main_title):]
        return output_path.with_name(f"{title}{tail}{output_path.suffix}")
    return None


def save_final_image(final_img, config, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    final_img.save(output_path)
    save_framed_output(final_img, config, output_path)
    print(f"done: {output_path}")
    maybe_collect_garbage(config)


def click_config_point_or_ratio(config, point_key, ratio_key=None):
    img = screenshot()
    if ratio_key:
        ratio = config["clicks"].get(ratio_key)
        if ratio:
            click_screen_ratio(ratio, img.size)
            return
    point = config["clicks"].get(point_key)
    if not point:
        raise SystemExit(f"missing click config: {point_key}")
    click(point, get_transform(config, img.size))


def navigate_from_group_to_top8(config):
    print("season: returning to championship arena selection")
    server = str(config.get("runtime_server", "cn")).strip().lower()
    if server in {"global", "hmt"}:
        # The lower-left return control is anchored to the full screen.  Its
        # ratio stays clear of the homepage button immediately to its right.
        click_config_point_or_ratio(config, "season_return_button", "season_return_button_ratio")
    else:
        press_escape(config, 1)
    time.sleep(SEASON_TRANSITION_BACK_WAIT_SECONDS)
    print("season: opening TOP8 championship bracket")
    click_config_point_or_ratio(config, "season_top8_entry", "season_top8_entry_ratio")
    time.sleep(SEASON_TOP8_ENTRY_WAIT_SECONDS)


def make_cached_player(bundle, key, group_index=None, slot_index=None):
    aliases = []
    for alias in bundle.get("aliases", []):
        if normalize_player_name(alias) and alias not in aliases:
            aliases.append(alias)
    if key not in aliases:
        aliases.append(key)
    player = {
        "key": key,
        "group_index": group_index,
        "slot_index": slot_index,
        "nickname": aliases[0] if aliases else key,
        "aliases": aliases,
        "profile": bundle.get("profile"),
    }
    if bundle.get("image") is not None:
        player["image"] = bundle["image"]
    if bundle.get("image_path"):
        player["image_path"] = str(bundle["image_path"])
    return player


def capture_seed_players_for_group(config, group_index, parts_dir, ocr):
    points = config["clicks"].get("group_64_avatars", [])
    if not points:
        raise SystemExit("group_64_avatars is not configured")

    timings = config["timing"]
    transform = get_transform(config, screenshot().size)
    players = []
    for slot_index, point in enumerate(points, 1):
        key = f"group{group_index:02d}_seed{slot_index:02d}"
        print(f"season cache: GROUP{group_index:02d} opening seed player {slot_index}/{len(points)}")
        click(point, transform)
        time.sleep(float(timings.get("after_group_avatar_click_seconds", 1.0)))
        bundle = capture_player_image(
            config,
            parts_dir,
            key,
            close_profile=False,
            return_metadata=True,
            ocr=ocr,
        )
        if config.get("low_memory"):
            cache_dir = parts_dir / "cached_players"
            cache_dir.mkdir(parents=True, exist_ok=True)
            cached_path = cache_dir / f"{key}.png"
            bundle["image"].save(cached_path)
            bundle["image"].close()
            bundle["image"] = None
            bundle["profile"] = None
            bundle["image_path"] = cached_path
            maybe_collect_garbage(config)
        player = make_cached_player(bundle, key, group_index, slot_index)
        print(f"season cache: {key} aliases={','.join(player['aliases'][:4])}")
        players.append(player)

        print("season cache: returning to group bracket")
        press_escape_twice(config)
        transform = get_transform(config, screenshot().size)
    return players


def default_stage_fallback_pairs(players, group_size):
    group_size = int(group_size)
    if group_size == 8:
        indexes = [(0, 1), (2, 3), (4, 5), (6, 7)]
    elif group_size == 4:
        indexes = [(0, 1), (2, 3)]
    else:
        indexes = [(0, 1)]
    return [fallback_pair(players, pair) for pair in indexes]


def describe_player(player):
    if not player:
        return "?"
    return player.get("nickname") or player.get("key") or "?"


def unique_players_from_pairs(stage_pairs):
    players = []
    seen = set()
    for pair in stage_pairs:
        for player in pair:
            key = player.get("key") if player else None
            if key and key not in seen:
                seen.add(key)
                players.append(player)
    return players


def maybe_correct_pair_from_result(pair, stage_pool, candidates, min_score=0.72):
    if not stage_pool or len(stage_pool) <= 2:
        return pair, False, result_pair_confidence(pair, candidates)
    current_confidence = result_pair_confidence(pair, candidates)
    details = match_player_details_from_candidates(candidates, stage_pool, min_score=min_score)
    if len(details) < 2:
        return pair, False, current_confidence
    corrected = [entry["player"] for entry in details[:2]]
    corrected_confidence = result_pair_confidence(corrected, candidates)
    pair_keys = [player.get("key") for player in pair[:2]]
    corrected_keys = [player.get("key") for player in corrected[:2]]
    same_players = set(pair_keys) == set(corrected_keys)
    matched_text = " | ".join(f"{entry['text']}->{describe_player(entry['player'])}:{entry['score']:.2f}" for entry in details[:2])
    if corrected_keys != pair_keys and (same_players or corrected_confidence >= 0.70):
        print(f"result name match: {matched_text}")
        return corrected[:2], True, corrected_confidence
    if corrected_confidence > current_confidence and same_players:
        print(f"result name order match: {matched_text}")
        return corrected[:2], corrected_keys != pair_keys, corrected_confidence
    return pair, False, current_confidence


def collect_cached_stage_results(
    config,
    parts_dir,
    group_size,
    post_data_mode,
    stage_pairs,
    bracket_mode="group",
    stage_label="stage",
):
    timings = config["timing"]
    result_buttons = get_group_result_sequence(config, group_size, bracket_mode)
    if not result_buttons:
        raise SystemExit(f"{stage_label}: result buttons are not configured")

    ocr = get_season_ocr(config)
    matched_pairs = []
    data_parts = []
    winners = []
    stage_pool = unique_players_from_pairs(stage_pairs)

    if len(stage_pairs) != len(result_buttons):
        print(
            f"{stage_label}: warning: result button count {len(result_buttons)} "
            f"does not match pair count {len(stage_pairs)}"
        )

    for result_index, point in enumerate(result_buttons[: len(stage_pairs)], 1):
        pair = stage_pairs[result_index - 1]
        if len(pair) < 2:
            raise SystemExit(f"{stage_label}: invalid pair for result {result_index}")

        print(f"{stage_label}: opening result {result_index}/{len(result_buttons)}")
        transform = get_transform(config, screenshot().size)
        click(point, transform)
        time.sleep(float(timings.get("after_bracket_result_click_seconds", 1.0)))

        with_stage_tabs = prepare_group_result_page(
            config,
            group_size,
            select_stage_tab=(int(group_size) != 2),
        )
        candidates = result_name_candidates_from_screen(config, ocr)
        pair, corrected, confidence = maybe_correct_pair_from_result(pair, stage_pool, candidates)
        reinforce_pair_aliases_from_result(pair, candidates)
        matched_pairs.append(pair)
        print(
            f"{stage_label}: bracket result {result_index}: "
            f"{describe_player(pair[0])} vs {describe_player(pair[1])}; "
            f"name_confidence={confidence:.2f}"
            f"{' corrected_by_result_names' if corrected else ''}"
        )

        winner_side = detect_result_winner_side(config)
        if winner_side is None:
            print(f"{stage_label}: warning: winner detection unclear for result {result_index}; using left side")
            winner_side = 0
        winners.append(pair[winner_side])
        print(f"{stage_label}: winner result {result_index}: {describe_player(pair[winner_side])}")

        if post_data_mode == "simple":
            part = crop_current(config, "group_simple_result")
            data_parts.append(part)
            if config.get("save_parts"):
                save_part(part, parts_dir, f"{stage_label}_simple_{result_index:02d}")
        elif post_data_mode == "detailed":
            detail_buttons = get_group_detail_buttons(config, group_size, with_stage_tabs)
            round_parts = []
            for detail_index, detail_point in enumerate(detail_buttons, 1):
                print(f"{stage_label}: opening detail {result_index}.{detail_index}")
                transform = get_transform(config, screenshot().size)
                click(detail_point, transform)
                part = wait_for_detailed_result_page(config, f"{stage_label} detailed {result_index}.{detail_index}")
                round_parts.append(part)
                if config.get("save_parts"):
                    save_part(part, parts_dir, f"{stage_label}_detailed_{result_index:02d}_{detail_index:02d}")
                press_escape(config, 1)
            if round_parts:
                data_parts.append(stitch_vertical(round_parts, config, gap=0, background="#f7f8fa"))

        press_escape(config, 1)

    return matched_pairs, data_parts, winners


def stitch_cached_stage(matched_pairs, data_parts, config, mode, single_row=False):
    if mode in ("simple", "detailed") and data_parts:
        pair_images = []
        for pair, data in zip(matched_pairs, data_parts):
            pair_images.append(
                stitch_pair_with_data(
                    player_image(pair[0]),
                    data,
                    player_image(pair[1]),
                    config,
                    mode,
                )
            )
        if len(pair_images) == 1:
            return pair_images[0]
        if single_row:
            gap = int(config.get("group_data_column_gap", config.get("group_grid_gap", 18)))
            return stitch_grid_with_gap(pair_images, len(pair_images), gap, config.get("background", "#20242a"))
        if len(pair_images) == 2:
            return stitch_vertical(
                pair_images,
                config,
                gap=int(config.get("group_grid_gap", 18)),
                background=config.get("background", "#20242a"),
            )
        return stitch_grid_with_gap(
            pair_images,
            2,
            int(config.get("group_data_column_gap", config.get("group_grid_gap", 18))),
            config.get("background", "#20242a"),
        )

    images = []
    for pair in matched_pairs:
        images.extend([player_image(pair[0]), player_image(pair[1])])
    if not images:
        raise ValueError("no cached stage images to stitch")
    columns = len(images) if single_row else (4 if len(images) >= 8 else 2)
    return stitch_grid(images, columns, config)


def build_cached_match_images(matched_pairs, data_parts, config, mode):
    if mode in ("simple", "detailed") and data_parts:
        result = []
        for pair, data in zip(matched_pairs, data_parts):
            result.append(
                stitch_pair_with_data(
                    player_image(pair[0]),
                    data,
                    player_image(pair[1]),
                    config,
                    mode,
                )
            )
        return result

    result = []
    for pair in matched_pairs:
        result.append(stitch_grid([player_image(pair[0]), player_image(pair[1])], 2, config))
    return result


def collect_cached_group_stage(
    config,
    parts_dir,
    group_size,
    post_data_mode,
    stage_pairs,
    group_index,
    stage_code=None,
):
    pairs, data_parts, winners = collect_cached_stage_results(
        config,
        parts_dir,
        group_size,
        post_data_mode,
        stage_pairs,
        bracket_mode="group",
        stage_label=f"group{group_index:02d}_{group_size}",
    )
    image = stitch_cached_stage(
        pairs,
        data_parts,
        config,
        post_data_mode,
        single_row=(int(group_size) in (2, 4)),
    )
    return image, winners


def collect_cached_top8_stage(config, parts_dir, group_size, post_data_mode, stage_pairs, stage_code=None):
    pairs, data_parts, winners = collect_cached_stage_results(
        config,
        parts_dir,
        group_size,
        post_data_mode,
        stage_pairs,
        bracket_mode="top8",
        stage_label=f"top8_{group_size}",
    )
    image = stitch_cached_stage(pairs, data_parts, config, post_data_mode, single_row=True)
    return image, winners


def run_season_capture(config, output_path, parts_dir, post_data_mode="none"):
    transform = print_screen_context(config)
    timings = config["timing"]
    ocr = get_season_ocr(config)
    if ocr is None:
        print("season cache: OCR is unavailable; cached matching will fall back to bracket order")

    group32_path = season_named_output_path(output_path, "32进16全部战斗数据（详）") or output_with_suffix(output_path, "group32_all")
    group16_path = season_named_output_path(output_path, "16进8全部战斗数据（详）") or output_with_suffix(output_path, "group16_all")
    top8_path = season_named_output_path(output_path, "TOP8-决赛战斗数据（详）") or output_with_suffix(output_path, "top8_pyramid")
    all_players = []
    group64_images = []
    group32_images = []
    group16_images = []
    top8_players = []

    for group_index in range(1, 9):
        print(f"season: switching to GROUP{group_index:02d}/08")
        click_group_tab(config, group_index, transform)
        time.sleep(float(timings.get("after_group_tab_click_seconds", 0.8)))

        group_dir = parts_dir / f"group{group_index:02d}"
        group_players = capture_seed_players_for_group(config, group_index, group_dir / "players", ocr)
        all_players.extend(group_players)

        print(f"season: GROUP{group_index:02d} collecting 64->32 results from cache")
        stage64_pairs = default_stage_fallback_pairs(group_players, 8)
        group64_image, group32_players = collect_cached_group_stage(
            config,
            group_dir / "64",
            8,
            post_data_mode,
            stage64_pairs,
            group_index,
            "group64",
        )
        group64_images.append(group64_image)

        print(f"season: GROUP{group_index:02d} collecting 32->16 results from cache")
        stage32_pairs = default_stage_fallback_pairs(group32_players, 4)
        group32_image, group16_players = collect_cached_group_stage(
            config,
            group_dir / "32",
            4,
            post_data_mode,
            stage32_pairs,
            group_index,
            "group32",
        )
        group32_images.append(group32_image)

        print(f"season: GROUP{group_index:02d} collecting 16->8 results from cache")
        stage16_pairs = default_stage_fallback_pairs(group16_players, 2)
        group16_image, group_winner = collect_cached_group_stage(
            config,
            group_dir / "16",
            2,
            post_data_mode,
            stage16_pairs,
            group_index,
            "group16",
        )
        group16_images.append(group16_image)
        if group_winner:
            top8_players.append(group_winner[0])
        transform = get_transform(config, screenshot().size)

    gap = int(config.get("all_groups_grid_gap", config.get("group_grid_gap", 18)))
    final64 = stitch_grid_with_gap(group64_images, 4, gap, config.get("background", "#20242a"))
    final32 = stitch_grid_with_gap(group32_images, 4, gap, config.get("background", "#20242a"))
    final16 = stitch_grid_with_gap(group16_images, 8, gap, config.get("background", "#20242a"))

    save_final_image(final64, config, output_path)
    save_final_image(final32, config, group32_path)
    save_final_image(final16, config, group16_path)
    if config.get("low_memory"):
        for img in (final64, final32, final16):
            try:
                img.close()
            except Exception:
                pass
        for image_list in (group64_images, group32_images, group16_images):
            for img in image_list:
                try:
                    img.close()
                except Exception:
                    pass
            image_list.clear()
        del final64, final32, final16
        maybe_collect_garbage(config)

    navigate_from_group_to_top8(config)

    if len(top8_players) < 8:
        raise SystemExit(f"season: expected 8 TOP8 players, got {len(top8_players)}")
    print("season: collecting TOP8 championship data from cached group winners")
    top8_pairs = default_stage_fallback_pairs(top8_players, 8)
    top8_stage8, top4_players = collect_cached_top8_stage(
        config,
        parts_dir / "top8" / "8",
        8,
        post_data_mode,
        top8_pairs,
        "top8",
    )
    top4_pairs = default_stage_fallback_pairs(top4_players, 4)
    top8_stage4, final_players = collect_cached_top8_stage(
        config,
        parts_dir / "top8" / "4",
        4,
        post_data_mode,
        top4_pairs,
        "top4",
    )
    final_pairs = default_stage_fallback_pairs(final_players, 2)
    top8_stage2, _champion = collect_cached_top8_stage(
        config,
        parts_dir / "top8" / "2",
        2,
        post_data_mode,
        final_pairs,
        "final",
    )
    top8_final = stitch_pyramid_layers([top8_stage2, top8_stage4, top8_stage8], config)
    save_final_image(top8_final, config, top8_path)
    if config.get("low_memory"):
        try:
            top8_final.close()
        except Exception:
            pass
        for img in (top8_stage2, top8_stage4, top8_stage8):
            try:
                img.close()
            except Exception:
                pass
        del top8_final, top8_stage2, top8_stage4, top8_stage8
        maybe_collect_garbage(config)

    print(f"also: {group32_path}")
    print(f"also: {group16_path}")
    print(f"also: {top8_path}")


def preview_regions(config, output_path):
    img = screenshot()
    transform = get_transform(config, img.size)
    draw = ImageDraw.Draw(img)

    colors = {
        "round_lineup": "cyan",
        "profile_basic": "red",
        "team_summary": "orange",
        "sync_level": "magenta",
        "research_cards": "lime",
    }
    for name, color in colors.items():
        crop = get_research_card_rects(config) if name == "research_cards" else config["crops"][name]
        rects = crop if name == "research_cards" else [crop]
        for rect in rects:
            box = scale_rect(rect, transform, img.size)
            draw.rectangle(box, outline=color, width=4)
            draw.text((box[0] + 8, box[1] + 8), name, fill=color)

    for name, point in config["clicks"]["round_tabs"].items():
        x, y = scale_point(point, transform)
        draw.ellipse((x - 8, y - 8, x + 8, y + 8), outline="yellow", width=3)
        draw.text((x + 10, y - 10), f"R{name}", fill="yellow")

    for name in ["avatar", "profile_close", "outpost_tab"]:
        x, y = scale_point(config["clicks"][name], transform)
        draw.ellipse((x - 10, y - 10, x + 10, y + 10), outline="lime", width=3)
        draw.text((x + 12, y - 12), name, fill="lime")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)
    print(
        "screen: "
        f"{img.width}x{img.height}, "
        f"mode={transform['mode']}, "
        f"scale={transform['sx']:.4f}, "
        f"offset=({transform['ox']:.1f}, {transform['oy']:.1f})"
    )
    print(f"preview saved: {output_path}")


def mouse_pos_loop():
    print("move mouse to a target point; press Ctrl+C to stop")
    try:
        while True:
            pt = POINT()
            user32.GetCursorPos(ctypes.byref(pt))
            print(f"x={pt.x}, y={pt.y}", end="\r", flush=True)
            time.sleep(0.1)
    except KeyboardInterrupt:
        print()


def parse_args():
    here = Path(__file__).resolve().parent
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    date_dir = datetime.now().strftime("%Y-%m-%d")
    parser = argparse.ArgumentParser(
        description="Capture NIKKE arena profile and Round 01-05 lineups, then stitch them vertically."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=here / "nikke_round_config.json",
        help="Path to config JSON.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=here / "screenshots" / date_dir / f"nikke_stitched_{timestamp}.png",
        help="Final stitched image path.",
    )
    parser.add_argument(
        "--framed-output",
        action="store_true",
        help="Also save a framed image using the selected background.",
    )
    parser.add_argument(
        "--framed-background",
        type=Path,
        default=None,
        help="Background image path used when --framed-output is enabled.",
    )
    parser.add_argument(
        "--support-duo",
        action="store_true",
        help="Capture both players from the support information screen and stitch them side by side.",
    )
    parser.add_argument(
        "--support-result",
        action="store_true",
        help="Capture both players and the active two-player result popup as one pair block.",
    )
    parser.add_argument(
        "--support-result-simple",
        action="store_true",
        help="With --support-result, capture the simplified result panel instead of detailed battle records.",
    )
    parser.add_argument(
        "--round-robin",
        action="store_true",
        help="Capture the four players shown on the C ARENA round-robin overview in one horizontal image.",
    )
    parser.add_argument(
        "--round-robin-all",
        action="store_true",
        help="Select and export individual round-robin screenshots for GROUP01 through GROUP64.",
    )
    parser.add_argument(
        "--round-robin-post-result",
        action="store_true",
        help="Capture the four-row round-robin post-match result panel before player profiles.",
    )
    parser.add_argument(
        "--round-robin-start-group",
        type=int,
        choices=range(1, 65),
        default=1,
        help="First GROUP to capture when --round-robin-all is enabled.",
    )
    parser.add_argument(
        "--round-robin-group-switch-delay",
        type=float,
        default=None,
        help="Delay after confirming a round-robin GROUP before opening its first player.",
    )
    parser.add_argument(
        "--round-robin-gap",
        type=int,
        default=None,
        help="Horizontal gap in pixels between the four round-robin player captures.",
    )
    parser.add_argument(
        "--round-robin-background",
        choices=("white", "pink", "blue", "black", "ivory"),
        default=None,
        help="Background colour used only for round-robin player-image stitching.",
    )
    parser.add_argument(
        "--include-support-status",
        action="store_true",
        help="Append the support status comparison bar to the support duo output.",
    )
    parser.add_argument(
        "--group-size",
        type=int,
        choices=[2, 4, 8],
        default=None,
        help="Capture a C ARENA group bracket: 8 players, 4 players, or reserved 2-player mode.",
    )
    parser.add_argument(
        "--top8-size",
        type=int,
        choices=[2, 4, 8],
        default=None,
        help="Capture the eight-player, four-player, or final stage shown on the C ARENA championship bracket.",
    )
    parser.add_argument(
        "--top8-pyramid",
        action="store_true",
        help="Capture TOP8, TOP4, and the final, then export one centered pyramid layout.",
    )
    parser.add_argument(
        "--season-capture",
        action="store_true",
        help="Capture all GROUP 64/32/16 data, then enter TOP8 and export the championship data flow.",
    )
    parser.add_argument(
        "--group-post-data",
        choices=["none", "simple", "detailed"],
        default="none",
        help="For group capture, insert post-match data between each player pair.",
    )
    parser.add_argument(
        "--all-groups",
        action="store_true",
        help="For group capture, iterate GROUP01-GROUP08 and stitch all group outputs in a 2x4 grid.",
    )
    parser.add_argument(
        "--click-delay",
        type=float,
        default=None,
        help="Minimum delay in seconds after UI clicks before the next automatic screenshot.",
    )
    parser.add_argument(
        "--avatar-profile-delay",
        type=float,
        default=None,
        help="Delay in seconds after opening a player profile before capturing its basic information page.",
    )
    parser.add_argument(
        "--bracket-result-delay",
        type=float,
        default=None,
        help="Delay in seconds after clicking a bracket result tag before using the result page.",
    )
    parser.add_argument(
        "--detail-click-delay",
        type=float,
        default=None,
        help="Legacy override for the minimum delay before detailed-page readiness checks.",
    )
    parser.add_argument(
        "--detail-page-min-wait",
        type=float,
        default=None,
        help="Minimum delay in seconds before detailed-page readiness checks begin.",
    )
    parser.add_argument(
        "--detail-page-timeout",
        type=float,
        default=None,
        help="Maximum seconds to wait for one detailed battle record page before stopping safely.",
    )
    parser.add_argument(
        "--low-memory",
        action="store_true",
        help="Store cached player images on disk and release large temporary images more aggressively.",
    )
    parser.add_argument(
        "--server",
        choices=["cn", "global", "hmt"],
        default="cn",
        help="NIKKE client server code. Global and HMT dismiss popups by clicking their backdrop.",
    )
    parser.add_argument(
        "--window-handle",
        type=lambda value: int(value, 0),
        default=None,
        help="Capture inside this NIKKE client window handle instead of the full desktop.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress logs. Useful when launched from the GUI for long batch captures.",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Save an annotated screenshot showing crop regions and click points. No clicks are performed.",
    )
    parser.add_argument(
        "--mouse-pos",
        action="store_true",
        help="Print current mouse coordinates for config calibration.",
    )
    return parser.parse_args()


def main():
    set_dpi_aware()
    args = parse_args()
    if args.quiet:
        builtins.print = lambda *args, **kwargs: None

    if args.mouse_pos:
        mouse_pos_loop()
        return

    config = load_config(args.config)
    config["runtime_server"] = args.server
    if args.window_handle is not None:
        enable_window_capture(args.window_handle)
    if args.low_memory:
        config["low_memory"] = True
    if args.framed_output:
        config["framed_output"] = True
    if args.framed_background is not None:
        config["framed_background"] = str(args.framed_background)
    if args.click_delay is not None:
        click_delay = max(0.0, min(5.0, float(args.click_delay)))
        for key in (
            "after_round_click_seconds",
            "after_support_avatar_click_seconds",
            "after_group_avatar_click_seconds",
            "after_group_tab_click_seconds",
            "after_group_result_click_seconds",
            "after_outpost_click_seconds",
        ):
            config["timing"][key] = max(float(config["timing"].get(key, 0)), click_delay)
    if args.avatar_profile_delay is not None:
        config["timing"]["after_avatar_click_seconds"] = max(
            0.45, min(5.0, float(args.avatar_profile_delay))
        )
    if args.round_robin_group_switch_delay is not None:
        config["timing"]["after_round_robin_group_switch_seconds"] = max(
            0.45, min(10.0, float(args.round_robin_group_switch_delay))
        )
    if args.round_robin_gap is not None:
        config["round_robin_grid_gap"] = max(0, min(5000, int(args.round_robin_gap)))
    if args.round_robin_background is not None:
        config["round_robin_background"] = {
            "white": "#FFFFFF",
            "pink": "#FFF0F6",
            "blue": "#29C7FF",
            "black": "#000000",
            "ivory": "#FFF6E5",
        }[args.round_robin_background]
    if args.bracket_result_delay is not None:
        config["timing"]["after_bracket_result_click_seconds"] = max(
            0.45, min(5.0, float(args.bracket_result_delay))
        )
    if args.detail_click_delay is not None:
        detail_click_delay = max(0.0, min(5.0, float(args.detail_click_delay)))
        key = "after_group_detail_click_seconds"
        config["timing"][key] = detail_click_delay
    if args.detail_page_min_wait is not None:
        detail_page_min_wait = max(0.0, min(5.0, float(args.detail_page_min_wait)))
        config["timing"]["after_group_detail_click_seconds"] = detail_page_min_wait
    if args.detail_page_timeout is not None:
        detail_page_timeout = max(10.0, min(180.0, float(args.detail_page_timeout)))
        config["timing"]["detail_page_timeout_seconds"] = detail_page_timeout
    if args.preview:
        preview_regions(config, args.output)
        return

    seconds = int(config["timing"].get("countdown_seconds", 3))
    print("put the game on the arena popup screen now")
    countdown(seconds)
    parts_dir = args.output.with_suffix("")
    if args.round_robin_all:
        if not args.round_robin:
            raise SystemExit("--round-robin-all requires --round-robin")
        run_all_round_robin_groups_capture(
            config,
            args.output,
            parts_dir,
            args.round_robin_start_group,
            args.round_robin_post_result,
        )
    elif args.round_robin:
        run_round_robin_capture(
            config,
            args.output,
            parts_dir,
            args.round_robin_post_result,
        )
    elif args.season_capture:
        run_season_capture(config, args.output, parts_dir, args.group_post_data)
    elif args.top8_pyramid:
        run_top8_pyramid_capture(config, args.output, parts_dir, args.group_post_data)
    elif args.top8_size:
        run_top8_capture(config, args.output, parts_dir, args.top8_size, args.group_post_data)
    elif args.group_size:
        if args.all_groups:
            run_all_groups_capture(config, args.output, parts_dir, args.group_size, args.group_post_data)
        else:
            run_group_capture(config, args.output, parts_dir, args.group_size, args.group_post_data)
    elif args.support_result:
        run_support_result_capture(
            config,
            args.output,
            parts_dir,
            detailed=not args.support_result_simple,
        )
    elif args.support_duo:
        run_support_duo_capture(config, args.output, parts_dir, args.include_support_status)
    else:
        run_capture(config, args.output, parts_dir)


if __name__ == "__main__":
    try:
        main()
    except DetailPageTimeout as exc:
        # Keep this machine-readable even when --quiet has disabled regular progress output.
        sys.stdout.write(f"NIKKE_DETAIL_PAGE_TIMEOUT|{exc.context}|{exc.timeout_seconds:.1f}\n")
        sys.stdout.flush()
        sys.exit(42)
    except KeyboardInterrupt:
        print("cancelled")
        sys.exit(130)
