import argparse
import ctypes
import json
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageGrab, ImageStat
except ModuleNotFoundError:
    print("Missing Pillow. Run: python -m pip install pillow")
    sys.exit(1)


DEFAULT_CONFIG = {
    "reference_size": [3440, 1440],
    "coordinate_mode": "height_anchored",
    "gap_px": 0,
    "background": "#f7f8fa",
    "align_y": "top",
    "save_parts": True,
    "layout": {
        "output_size": [2842, 342],
        "top_padding": 12,
        "bottom_padding": 8,
        "section_gap": 10,
        "equipment_item_gap": 4,
        "equipment_column_gap": 10,
        "equipment_row_gap": 8,
        "primary_height": 320,
        "character_card_size": [186, 320],
        "collectibles_size": [112, 135],
        "battle_attributes_size": [501, 320],
        "skills_size": [473, 320],
        "equipment_row_height": 148,
        "equipment_icon_width": 190,
        "equipment_entry_width": 549,
        "equipment_cell_width": 743,
        "side_padding": 16,
        "border_px": 1,
        "border_color": "#dde1e6",
    },
    "timing": {
        "countdown_seconds": 3,
        "after_filter_click_seconds": 0.75,
        "after_card_click_seconds": 1.0,
        "after_profile_load_seconds": 1.5,
        "after_equipment_click_seconds": 0.7,
        "after_equipment_close_seconds": 0.55,
        "after_skill_click_seconds": 0.75,
        "after_back_seconds": 0.8,
        "after_scroll_seconds": 0.9,
    },
    "color_checks": {
        "burst_filter_active": {
            "rect": [1426, 258, 88, 73],
            "anchor": "center",
            "blue_pixel_ratio": 0.35,
        }
    },
    "clicks": {
        "burst_filter": {"point": [1466, 292], "anchor": "center"},
        "first_character": {"point": [140, 586], "anchor": "left"},
        "equipment_slots": [
            {
                "name": "head",
                "point": [3058, 1038],
                "anchor": "right",
                "rect": [2998, 978, 140, 120],
            },
            {
                "name": "body",
                "point": [3258, 1038],
                "anchor": "right",
                "rect": [3188, 978, 140, 120],
            },
            {
                "name": "arms",
                "point": [3058, 1190],
                "anchor": "right",
                "rect": [2998, 1128, 140, 120],
            },
            {
                "name": "legs",
                "point": [3258, 1188],
                "anchor": "right",
                "rect": [3188, 1128, 140, 120],
            },
        ],
        "skill_tab": {"point": [2928, 1080], "anchor": "right"},
        "skill_tab_retry": [
            {"point": [2928, 1080], "anchor": "right"},
            {"point": [2928, 1062], "anchor": "right"},
            {"point": [2912, 1080], "anchor": "right"},
        ],
        "list_back": {"point": [82, 1360], "anchor": "left"},
        "equipment_close": {"point": [2005, 154], "anchor": "center"},
    },
    "batch": {
        "enabled_rows": 2,
        "columns": 17,
        "card_rect": [47, 424, 186, 320],
        "card_pitch": [197, 344],
        "scroll_point": {"point": [1720, 810], "anchor": "center"},
        "scroll_wheel_clicks": -5,
        "max_scrolls": 40,
        "stop_after_no_new_pages": 2,
        "max_characters": 0,
        "duplicate_hamming_threshold": 18,
        "min_card_color_ratio": 0.03,
    },
    "equipment_detection": {
        "slot_color_ratio_threshold": 0.025,
        "popup_side_probe_rect": [300, 300, 600, 600],
        "popup_right_probe_rect": [2540, 300, 600, 600],
        "popup_panel_probe_rect": [1380, 100, 680, 1100],
        "popup_contrast_threshold": 80,
        "popup_bounds_search_rect": [1250, 40, 940, 1310],
        "popup_close_offset": [74, 43],
        "popup_max_retries": 3,
        "popup_click_offsets": [[0, 0], [-20, 0], [20, 0]],
        "popup_close_retries": 4,
        "type_label_search_rect": [1358, 78, 300, 145],
        "type_templates": {
            "fire": "assets/equipment_type_fire.png",
            "defense": "assets/equipment_type_defense.png",
            "support": "assets/equipment_type_support.png",
        },
        "entry_lock_search_rect": [1930, 890, 105, 300],
        "entry_crop_x": 1400,
        "entry_crop_width": 620,
        "entry_y_padding": 16,
        "icon_search_rect": [1540, 120, 310, 400],
        "icon_padding": [45, 15],
    },
    "skill_detection": {
        "equipment_color_ratio_threshold": 0.08,
        "max_retries": 3,
    },
    "crops": {
        "character_card": {"rect": [47, 424, 186, 320], "anchor": "left"},
        "collectibles": {"rect": [20, 205, 112, 135], "anchor": "left"},
        "battle_attributes": {"rect": [2960, 430, 415, 265], "anchor": "right"},
        "equipment_image": {"rect": [1580, 170, 245, 215], "anchor": "center"},
        "equipment_image_yellow_fire": {
            "rect": [1580, 300, 245, 195],
            "anchor": "center",
        },
        "equipment_image_yellow_default": {
            "rect": [1580, 220, 245, 195],
            "anchor": "center",
        },
        "equipment_entries": {"rect": [1400, 954, 616, 148], "anchor": "center"},
        "skills": {"rect": [2988, 990, 365, 247], "anchor": "right"},
    },
}


user32 = ctypes.windll.user32

INPUT_MOUSE = 0
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_WHEEL = 0x0800


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("union", INPUT_UNION)]


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def set_dpi_aware():
    try:
        user32.SetProcessDPIAware()
    except Exception:
        pass


def load_config(path):
    if not path.exists():
        return json.loads(json.dumps(DEFAULT_CONFIG))
    with path.open("r", encoding="utf-8") as f:
        config = json.load(f)
    return deep_merge(DEFAULT_CONFIG, config)


def deep_merge(base, override):
    result = json.loads(json.dumps(base))
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def screenshot():
    return ImageGrab.grab()


def resource_path(path):
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / path


def get_transform(config, image_size):
    ref_w, ref_h = config["reference_size"]
    img_w, img_h = image_size
    mode = config.get("coordinate_mode", "height_anchored")
    if mode == "stretch":
        return {"sx": img_w / ref_w, "sy": img_h / ref_h, "mode": mode}
    scale = img_h / ref_h
    return {"sx": scale, "sy": scale, "mode": mode}


def _anchor(item):
    if isinstance(item, dict):
        return item.get("anchor", "center")
    return "center"


def _value(item, key):
    if isinstance(item, dict):
        return item[key]
    return item


def scale_x(x, width, anchor, transform, image_width, ref_width):
    sx = transform["sx"]
    if transform["mode"] == "stretch":
        return x * sx
    if anchor == "left":
        return x * sx
    if anchor == "right":
        return image_width - (ref_width - x) * sx
    return image_width / 2 + (x - ref_width / 2) * sx


def scale_point(item, config, transform, image_size):
    point = _value(item, "point")
    anchor = _anchor(item)
    ref_w, _ = config["reference_size"]
    img_w, _ = image_size
    x = scale_x(point[0], 0, anchor, transform, img_w, ref_w)
    y = point[1] * transform["sy"]
    return round(x), round(y)


def scale_rect(item, config, transform, image_size):
    rect = _value(item, "rect")
    anchor = _anchor(item)
    ref_w, _ = config["reference_size"]
    img_w, img_h = image_size
    x, y, w, h = rect
    scaled_w = w * transform["sx"]
    left = scale_x(x, w, anchor, transform, img_w, ref_w)
    if anchor == "right" and transform["mode"] != "stretch":
        left = img_w - (ref_w - x) * transform["sx"]
    top = y * transform["sy"]
    right = left + scaled_w
    bottom = top + h * transform["sy"]
    return (
        max(0, min(round(left), img_w)),
        max(0, min(round(top), img_h)),
        max(0, min(round(right), img_w)),
        max(0, min(round(bottom), img_h)),
    )


def send_mouse(flags):
    extra = ctypes.c_ulong(0)
    event = INPUT(
        type=INPUT_MOUSE,
        union=INPUT_UNION(
            mi=MOUSEINPUT(0, 0, 0, flags, 0, ctypes.pointer(extra))
        ),
    )
    user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(event))


def send_mouse_wheel(clicks):
    delta = int(clicks) * 120
    extra = ctypes.c_ulong(0)
    event = INPUT(
        type=INPUT_MOUSE,
        union=INPUT_UNION(
            mi=MOUSEINPUT(
                0,
                0,
                delta & 0xFFFFFFFF,
                MOUSEEVENTF_WHEEL,
                0,
                ctypes.pointer(extra),
            )
        ),
    )
    user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(event))


def click(item, config, transform, image_size, duration=0.06):
    x, y = scale_point(item, config, transform, image_size)
    click_absolute(x, y, duration)


def click_absolute(x, y, duration=0.06):
    user32.SetCursorPos(x, y)
    time.sleep(max(duration, 0.08))
    send_mouse(MOUSEEVENTF_LEFTDOWN)
    time.sleep(max(duration, 0.08))
    send_mouse(MOUSEEVENTF_LEFTUP)


def countdown(seconds):
    for i in range(seconds, 0, -1):
        print(f"{i}...")
        time.sleep(1)


def is_blue_filter_active(img, config, transform):
    check = config["color_checks"]["burst_filter_active"]
    box = scale_rect(check, config, transform, img.size)
    sample = img.crop(box).convert("RGB")
    total = max(sample.width * sample.height, 1)
    blue = 0
    for r, g, b in sample.getdata():
        if b > 150 and g > 120 and r < 100:
            blue += 1
    ratio = blue / total
    return ratio >= float(check.get("blue_pixel_ratio", 0.35)), ratio


def crop_from_image(img, crop_item, config, transform):
    return img.crop(scale_rect(crop_item, config, transform, img.size))


def save_part(parts_dir, name, img):
    parts_dir.mkdir(parents=True, exist_ok=True)
    path = parts_dir / f"{name}.png"
    img.save(path)
    print(f"saved part: {path}")


def average_hash(img, size=16):
    small = img.convert("L").resize((size, size), Image.Resampling.LANCZOS)
    pixels = list(small.getdata())
    avg = sum(pixels) / len(pixels)
    return tuple(1 if pixel >= avg else 0 for pixel in pixels)


def hamming_distance(left, right):
    return sum(1 for a, b in zip(left, right) if a != b)


def card_color_ratio(img):
    pixels = img.convert("RGB").getdata()
    total = max(img.width * img.height, 1)
    colorful = 0
    for r, g, b in pixels:
        if max(r, g, b) - min(r, g, b) > 32 and max(r, g, b) < 250:
            colorful += 1
    return colorful / total


def mean_absolute_gray_diff(left, right):
    left = left.convert("L")
    right = right.convert("L").resize(left.size, Image.Resampling.LANCZOS)
    left_data = list(left.getdata())
    right_data = list(right.getdata())
    return sum(abs(a - b) for a, b in zip(left_data, right_data)) / max(len(left_data), 1)


def template_search_gray_diff(region, template, step=2):
    region = region.convert("L")
    template = template.convert("L")
    region = region.resize(
        (max(1, region.width // 2), max(1, region.height // 2)),
        Image.Resampling.BILINEAR,
    )
    template = template.resize(
        (max(1, template.width // 2), max(1, template.height // 2)),
        Image.Resampling.BILINEAR,
    )
    rw, rh = region.size
    tw, th = template.size
    if tw > rw or th > rh:
        template = template.resize((min(tw, rw), min(th, rh)), Image.Resampling.LANCZOS)
        tw, th = template.size
    best = None
    for y in range(0, rh - th + 1, step):
        for x in range(0, rw - tw + 1, step):
            diff = mean_absolute_gray_diff(region.crop((x, y, x + tw, y + th)), template)
            if best is None or diff < best[0]:
                best = (diff, x, y)
    if best is None:
        return 9999.0
    return best[0]


def is_duplicate_card(card_hash, seen_hashes, threshold):
    return any(hamming_distance(card_hash, seen) <= threshold for seen in seen_hashes)


def make_rect_item(rect, anchor="left"):
    return {"rect": rect, "anchor": anchor}


def make_point_item(point, anchor="left"):
    return {"point": point, "anchor": anchor}


def rect_center(rect):
    x, y, w, h = rect
    return [x + w / 2, y + h / 2]


def equipment_slot_has_item(profile_img, slot, config, transform):
    rect = {"rect": slot["rect"], "anchor": slot.get("anchor", "right")}
    crop = crop_from_image(profile_img, rect, config, transform)
    ratio = card_color_ratio(crop)
    threshold = float(
        config.get("equipment_detection", {}).get("slot_color_ratio_threshold", 0.025)
    )
    return ratio >= threshold, ratio


def mean_luminance(img):
    return ImageStat.Stat(img.convert("L")).mean[0]


def is_popup_panel_pixel(r, g, b):
    return min(r, g, b) > 160 and max(r, g, b) - min(r, g, b) < 55


def find_equipment_popup_bounds(img, config, transform):
    detection = config.get("equipment_detection", {})
    search_item = {
        "rect": detection.get("popup_bounds_search_rect", [1250, 40, 940, 1310]),
        "anchor": "center",
    }
    search_box = scale_rect(search_item, config, transform, img.size)
    region = img.crop(search_box).convert("RGB")
    step_x = max(1, round(2 * transform["sx"]))
    step_y = max(1, round(2 * transform["sy"]))
    sampled_width = max(1, len(range(0, region.width, step_x)))
    row_threshold = sampled_width * 0.53
    panel_rows = []
    for y in range(0, region.height, step_y):
        bright = sum(
            1
            for x in range(0, region.width, step_x)
            if is_popup_panel_pixel(*region.getpixel((x, y)))
        )
        if bright >= row_threshold:
            panel_rows.append(y)
    if not panel_rows:
        return None

    top_local = min(panel_rows)
    bottom_local = max(panel_rows)
    probe_y = min(region.height - 1, top_local + max(2, round(20 * transform["sy"])))
    runs = []
    start = None
    for x in range(region.width):
        bright = is_popup_panel_pixel(*region.getpixel((x, probe_y)))
        if bright and start is None:
            start = x
        elif not bright and start is not None:
            if x - start >= round(500 * transform["sx"]):
                runs.append((start, x - 1))
            start = None
    if start is not None and region.width - start >= round(500 * transform["sx"]):
        runs.append((start, region.width - 1))
    if not runs:
        return None

    left_local, right_local = max(runs, key=lambda run: run[1] - run[0])
    panel_width = right_local - left_local + 1
    min_width = round(600 * transform["sx"])
    max_width = round(850 * transform["sx"])
    if not (min_width <= panel_width <= max_width):
        return None
    return (
        search_box[0] + left_local,
        search_box[1] + top_local,
        search_box[0] + right_local + 1,
        search_box[1] + bottom_local + 1,
    )


def equipment_popup_is_open(img, config, transform):
    detection = config.get("equipment_detection", {})
    side_item = {
        "rect": detection.get("popup_side_probe_rect", [300, 300, 600, 600]),
        "anchor": "left",
    }
    right_item = {
        "rect": detection.get("popup_right_probe_rect", [2540, 300, 600, 600]),
        "anchor": "right",
    }
    panel_item = {
        "rect": detection.get("popup_panel_probe_rect", [1380, 100, 680, 1100]),
        "anchor": "center",
    }
    side = crop_from_image(img, side_item, config, transform)
    right = crop_from_image(img, right_item, config, transform)
    panel = crop_from_image(img, panel_item, config, transform)
    contrast = mean_luminance(panel) - max(mean_luminance(side), mean_luminance(right))
    threshold = float(detection.get("popup_contrast_threshold", 80))
    bounds = find_equipment_popup_bounds(img, config, transform)
    return contrast >= threshold and bounds is not None, contrast


def equipment_slot_click_item(slot, offset):
    point = rect_center(slot["rect"])
    point[0] += offset[0]
    point[1] += offset[1]
    return make_point_item(point, slot.get("anchor", "right"))


def open_equipment_popup(slot, profile_img, config, transform):
    detection = config.get("equipment_detection", {})
    offsets = detection.get("popup_click_offsets", [[0, 0], [-20, 0], [20, 0]])
    retries = int(detection.get("popup_max_retries", 3))
    wait_seconds = float(config["timing"]["after_equipment_click_seconds"])
    name = slot.get("name", "equipment")

    for attempt in range(retries):
        offset = offsets[min(attempt, len(offsets) - 1)]
        click(equipment_slot_click_item(slot, offset), config, transform, profile_img.size)
        time.sleep(wait_seconds)
        popup_img = screenshot()
        opened, contrast = equipment_popup_is_open(popup_img, config, transform)
        if opened:
            if attempt:
                print(f"{name}: popup opened after retry {attempt + 1}, contrast={contrast:.1f}")
            return popup_img
        print(f"{name}: popup did not open, retry {attempt + 1}, contrast={contrast:.1f}")
    return None


def close_equipment_popup(config, transform, image_size):
    detection = config.get("equipment_detection", {})
    retries = int(detection.get("popup_close_retries", 3))
    wait_seconds = float(config["timing"]["after_equipment_close_seconds"])
    for attempt in range(retries):
        current = screenshot()
        opened, contrast = equipment_popup_is_open(current, config, transform)
        if not opened:
            return True
        bounds = find_equipment_popup_bounds(current, config, transform)
        if bounds is None:
            print(f"equipment popup bounds not found, close retry {attempt + 1}")
            time.sleep(wait_seconds)
            continue
        offset_x, offset_y = detection.get("popup_close_offset", [74, 43])
        close_x = round(bounds[2] - offset_x * transform["sx"])
        close_y = round(bounds[1] + offset_y * transform["sy"])
        click_absolute(close_x, close_y)
        time.sleep(wait_seconds)
        current = screenshot()
        opened, contrast = equipment_popup_is_open(current, config, transform)
        if not opened:
            return True
        print(
            "equipment popup still open, "
            f"close retry {attempt + 1}, point=({close_x},{close_y}), contrast={contrast:.1f}"
        )
    return False


def detect_equipment_type(equip_img, config, transform):
    detection = config.get("equipment_detection", {})
    label_rect = {
        "rect": detection.get("type_label_search_rect", [1358, 78, 300, 145]),
        "anchor": "center",
    }
    label_region = crop_from_image(equip_img, label_rect, config, transform)
    scores = []
    for name, rel_path in detection.get("type_templates", {}).items():
        path = resource_path(rel_path)
        if not path.exists():
            continue
        template = Image.open(path)
        scaled_size = (
            max(1, round(template.width * transform["sx"])),
            max(1, round(template.height * transform["sy"])),
        )
        template = template.resize(scaled_size, Image.Resampling.LANCZOS)
        scores.append((template_search_gray_diff(label_region, template), name))
    if not scores:
        return "unknown", None
    score, name = min(scores)
    return name, score


def find_equipment_entries_rect(equip_img, config, transform):
    detection = config.get("equipment_detection", {})
    search_item = {
        "rect": detection.get("entry_lock_search_rect", [1930, 890, 105, 300]),
        "anchor": "center",
    }
    box = scale_rect(search_item, config, transform, equip_img.size)
    search = equip_img.crop(box).convert("RGB")
    ys = []
    for y in range(search.height):
        dark = 0
        for x in range(search.width):
            r, g, b = search.getpixel((x, y))
            if r < 55 and g < 55 and b < 55:
                dark += 1
        if dark >= 8:
            ys.append(y + box[1])
    if not ys:
        return None

    pad = int(detection.get("entry_y_padding", 16) * transform["sy"])
    top = max(0, min(ys) - pad)
    bottom = min(equip_img.height, max(ys) + pad)
    left = round(
        scale_x(
            detection.get("entry_crop_x", 1400),
            0,
            "center",
            transform,
            equip_img.width,
            config["reference_size"][0],
        )
    )
    width = round(detection.get("entry_crop_width", 620) * transform["sx"])
    return (left, top, min(equip_img.width, left + width), bottom)


def is_equipment_icon_pixel(r, g, b):
    saturation = max(r, g, b) - min(r, g, b)
    if r > 210 and g < 120 and b < 80:
        return False
    if saturation > 35 and max(r, g, b) > 70 and min(r, g, b) < 245:
        return True
    if r < 95 and g < 95 and b < 95:
        return True
    return False


def find_equipment_icon_rect(equip_img, config, transform):
    detection = config.get("equipment_detection", {})
    search_item = {
        "rect": detection.get("icon_search_rect", [1540, 120, 310, 400]),
        "anchor": "center",
    }
    search_box = scale_rect(search_item, config, transform, equip_img.size)
    region = equip_img.crop(search_box).convert("RGB")
    width, height = region.size
    mask = bytearray(width * height)
    for y in range(height):
        for x in range(width):
            if is_equipment_icon_pixel(*region.getpixel((x, y))):
                mask[y * width + x] = 1

    seen = bytearray(width * height)
    best = None
    min_side = max(12, round(20 * transform["sx"]))
    max_side = max(80, round(190 * transform["sx"]))
    for start, value in enumerate(mask):
        if not value or seen[start]:
            continue
        stack = [start]
        seen[start] = 1
        xs = []
        ys = []
        while stack:
            point = stack.pop()
            x = point % width
            y = point // width
            xs.append(x)
            ys.append(y)
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= nx < width and 0 <= ny < height:
                    index = ny * width + nx
                    if mask[index] and not seen[index]:
                        seen[index] = 1
                        stack.append(index)
        area = len(xs)
        if area < 30:
            continue
        left = min(xs) + search_box[0]
        top = min(ys) + search_box[1]
        right = max(xs) + search_box[0] + 1
        bottom = max(ys) + search_box[1] + 1
        comp_width = right - left
        comp_height = bottom - top
        if not (min_side <= comp_width <= max_side and min_side <= comp_height <= max_side):
            continue
        if best is None or area > best[4]:
            best = (left, top, right, bottom, area)

    if best is None:
        return scale_rect(config["crops"]["equipment_image"], config, transform, equip_img.size)

    pad_x_ref, pad_y_ref = detection.get("icon_padding", [45, 25])
    pad_x = round(pad_x_ref * transform["sx"])
    pad_y = round(pad_y_ref * transform["sy"])
    return (
        max(0, best[0] - pad_x),
        max(0, best[1] - pad_y),
        min(equip_img.width, best[2] + pad_x),
        min(equip_img.height, best[3] + pad_y),
    )


def capture_equipment_parts(equip_img, slot_name, config, transform):
    opened, contrast = equipment_popup_is_open(equip_img, config, transform)
    if not opened:
        print(f"{slot_name}: rejected non-popup screenshot, contrast={contrast:.1f}")
        return []
    equip_type, score = detect_equipment_type(equip_img, config, transform)
    entries_box = find_equipment_entries_rect(equip_img, config, transform)
    has_entries = entries_box is not None
    image_part = equip_img.crop(find_equipment_icon_rect(equip_img, config, transform))
    result = [(f"{slot_name}_image", image_part)]
    if has_entries:
        result.append((f"{slot_name}_entries", equip_img.crop(entries_box)))

    score_text = "n/a" if score is None else f"{score:.1f}"
    entry_text = "with entries" if has_entries else "image only"
    print(f"{slot_name}: type={equip_type}, score={score_text}, {entry_text}")
    return result


def capture_skills_part(config, transform, image_size, label=""):
    detection = config.get("skill_detection", {})
    threshold = float(detection.get("equipment_color_ratio_threshold", 0.08))
    max_retries = int(detection.get("max_retries", 3))
    candidates = config["clicks"].get("skill_tab_retry") or [config["clicks"]["skill_tab"]]
    timings = config["timing"]
    last_part = None
    last_ratio = None

    for attempt in range(max_retries):
        target = candidates[min(attempt, len(candidates) - 1)]
        click(target, config, transform, image_size)
        time.sleep(float(timings["after_skill_click_seconds"]))
        skill_img = screenshot()
        part = crop_from_image(skill_img, config["crops"]["skills"], config, transform)
        ratio = card_color_ratio(part)
        last_part = part
        last_ratio = ratio
        if ratio < threshold:
            if attempt:
                print(f"{label}skills captured after retry {attempt + 1}, color ratio={ratio:.3f}")
            return part, skill_img
        print(f"{label}skills look like equipment, retry {attempt + 1}, color ratio={ratio:.3f}")

    print(f"{label}warning: using last skills crop, color ratio={last_ratio:.3f}")
    return last_part, screenshot()


def stitch_horizontal(parts, config):
    gap = int(config.get("gap_px", 0))
    bg = config.get("background", "#f7f8fa")
    align = config.get("align_y", "top")
    width = sum(img.width for _, img in parts) + gap * max(0, len(parts) - 1)
    height = max(img.height for _, img in parts)
    canvas = Image.new("RGB", (width, height), bg)
    x = 0
    for _, img in parts:
        if align == "center":
            y = (height - img.height) // 2
        elif align == "bottom":
            y = height - img.height
        else:
            y = 0
        canvas.paste(img.convert("RGB"), (x, y))
        x += img.width + gap
    return canvas


def resize_to_height(img, height):
    if not height or img.height == height:
        return img
    width = round(img.width * height / img.height)
    return img.resize((width, height), Image.Resampling.LANCZOS)


def fit_to_box(img, width, height, background):
    if img is None:
        return Image.new("RGB", (width, height), background)
    scale = min(width / img.width, height / img.height)
    resized = img.resize(
        (max(1, round(img.width * scale)), max(1, round(img.height * scale))),
        Image.Resampling.LANCZOS,
    )
    canvas = Image.new("RGB", (width, height), background)
    paste(canvas, resized, (width - resized.width) // 2, (height - resized.height) // 2)
    return canvas


def paste(canvas, img, x, y):
    canvas.paste(img.convert("RGB"), (round(x), round(y)))


def make_equipment_cell(icon, entries, layout, background):
    row_height = int(layout.get("equipment_row_height", 148))
    icon_width = int(layout.get("equipment_icon_width", 190))
    entry_width = int(layout.get("equipment_entry_width", 549))
    item_gap = int(layout.get("equipment_item_gap", 4))
    cell_width = int(layout.get("equipment_cell_width", icon_width + item_gap + entry_width))
    canvas = Image.new("RGB", (cell_width, row_height), background)
    icon_box = fit_to_box(icon, icon_width, row_height, background)
    paste(canvas, icon_box, 0, 0)
    if entries is not None:
        entry_box = fit_to_box(entries, entry_width, row_height, background)
        paste(canvas, entry_box, icon_width + item_gap, 0)
    return canvas


def make_equipment_grid(parts_by_name, config):
    layout = config.get("layout", {})
    bg = config.get("background", "#f7f8fa")
    row_height = int(layout.get("equipment_row_height", 148))
    column_gap = int(layout.get("equipment_column_gap", 10))
    row_gap = int(layout.get("equipment_row_gap", 8))
    cell_width = int(layout.get("equipment_cell_width", 743))
    slots = ["head", "body", "arms", "legs"]
    cells = []
    for slot in slots:
        icon = parts_by_name.get(f"{slot}_image")
        cells.append(
            make_equipment_cell(
                icon,
                parts_by_name.get(f"{slot}_entries"),
                layout,
                bg,
            )
        )
    width = cell_width * 2 + column_gap
    height = row_height * 2 + row_gap
    canvas = Image.new("RGB", (width, height), bg)
    positions = [
        (0, 0),
        (cell_width + column_gap, 0),
        (0, row_height + row_gap),
        (cell_width + column_gap, row_height + row_gap),
    ]
    for cell, (x, y) in zip(cells, positions):
        paste(canvas, cell, x, y)
    return canvas


def stitch_character_layout(parts, config):
    parts_by_name = {name: img for name, img in parts}
    layout = config.get("layout", {})
    bg = config.get("background", "#f7f8fa")
    top = int(layout.get("top_padding", 12))
    bottom = int(layout.get("bottom_padding", 8))
    gap = int(layout.get("section_gap", 10))
    side = int(layout.get("side_padding", 0))
    border = int(layout.get("border_px", 0))
    border_color = layout.get("border_color", "#d6d6d6")
    primary_height = int(layout.get("primary_height", parts_by_name["character_card"].height))
    card_size = layout.get("character_card_size", [186, primary_height])
    collectibles_size = layout.get("collectibles_size", [112, 135])
    battle_size = layout.get("battle_attributes_size", [501, primary_height])
    skills_size = layout.get("skills_size", [473, primary_height])

    card = fit_to_box(parts_by_name["character_card"], card_size[0], card_size[1], bg)
    collectibles = fit_to_box(
        parts_by_name["collectibles"],
        collectibles_size[0],
        collectibles_size[1],
        bg,
    )
    battle = fit_to_box(
        parts_by_name["battle_attributes"],
        battle_size[0],
        battle_size[1],
        bg,
    )
    skills = fit_to_box(parts_by_name["skills"], skills_size[0], skills_size[1], bg)
    equipment = make_equipment_grid(parts_by_name, config)

    sections = [card, collectibles, battle, skills, equipment]
    content_height = primary_height
    content_width = sum(section.width for section in sections) + gap * (len(sections) - 1)
    expected_width = content_width + side * 2 + border * 2
    expected_height = top + content_height + bottom + border * 2
    output_size = layout.get("output_size", [expected_width, expected_height])
    width, height = int(output_size[0]), int(output_size[1])
    if (width, height) != (expected_width, expected_height):
        print(
            "layout warning: fixed output "
            f"{width}x{height}, computed content {expected_width}x{expected_height}"
        )
    canvas = Image.new("RGB", (width, height), bg)

    x = border + side
    for section in sections:
        y = border + top + (content_height - section.height) // 2
        paste(canvas, section, x, y)
        x += section.width + gap
    if border > 0:
        draw = ImageDraw.Draw(canvas)
        for offset in range(border):
            draw.rectangle(
                (offset, offset, width - offset - 1, height - offset - 1),
                outline=border_color,
            )
    return canvas


def run_capture(config, output_path, parts_dir):
    img = screenshot()
    transform = get_transform(config, img.size)
    print(
        "screen: "
        f"{img.width}x{img.height}, "
        f"mode={transform['mode']}, "
        f"scale=({transform['sx']:.4f}, {transform['sy']:.4f})"
    )
    timings = config["timing"]
    parts = []

    active, ratio = is_blue_filter_active(img, config, transform)
    print(f"burst filter blue ratio: {ratio:.3f}")
    if not active:
        print("activating burst filter I")
        click(config["clicks"]["burst_filter"], config, transform, img.size)
        time.sleep(float(timings["after_filter_click_seconds"]))

    img = screenshot()
    card = crop_from_image(img, config["crops"]["character_card"], config, transform)
    parts.append(("character_card", card))

    print("opening first character")
    click(config["clicks"]["first_character"], config, transform, img.size)
    time.sleep(float(timings["after_card_click_seconds"]))
    time.sleep(float(timings.get("after_profile_load_seconds", 1.5)))

    profile_img = screenshot()
    parts.append(
        (
            "collectibles",
            crop_from_image(profile_img, config["crops"]["collectibles"], config, transform),
        )
    )
    parts.append(
        (
            "battle_attributes",
            crop_from_image(
                profile_img,
                config["crops"]["battle_attributes"],
                config,
                transform,
            ),
        )
    )

    for slot in config["clicks"]["equipment_slots"]:
        name = slot.get("name", "equipment")
        has_item, ratio = equipment_slot_has_item(profile_img, slot, config, transform)
        if not has_item:
            print(f"skipping empty equipment: {name}, color ratio={ratio:.3f}")
            continue
        print(f"capturing equipment: {name}")
        equip_img = open_equipment_popup(slot, profile_img, config, transform)
        if equip_img is None:
            print(f"skipping equipment because popup failed: {name}")
            continue
        parts.extend(capture_equipment_parts(equip_img, name, config, transform))
        if not close_equipment_popup(config, transform, equip_img.size):
            raise RuntimeError(
                "Equipment popup could not be closed after dynamic retries; task stopped safely."
            )

    print("opening skills")
    skills_part, skill_img = capture_skills_part(config, transform, profile_img.size)
    parts.append(("skills", skills_part))

    if config.get("save_parts"):
        for name, part in parts:
            save_part(parts_dir, name, part)

    final_img = stitch_character_layout(parts, config)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    final_img.save(output_path)
    print(f"done: {output_path}")


def activate_filter_if_needed(config, transform):
    img = screenshot()
    active, ratio = is_blue_filter_active(img, config, transform)
    print(f"burst filter blue ratio: {ratio:.3f}")
    if not active:
        print("activating burst filter I")
        click(config["clicks"]["burst_filter"], config, transform, img.size)
        time.sleep(float(config["timing"]["after_filter_click_seconds"]))


def capture_character_at(config, transform, card_item, output_path, parts_dir, index):
    list_img = screenshot()
    timings = config["timing"]
    parts = [
        (
            "character_card",
            crop_from_image(list_img, card_item, config, transform),
        )
    ]

    print(f"opening character {index:03d}")
    click(make_point_item(rect_center(card_item["rect"]), card_item.get("anchor", "left")), config, transform, list_img.size)
    time.sleep(float(timings["after_card_click_seconds"]))
    time.sleep(float(timings.get("after_profile_load_seconds", 1.5)))

    profile_img = screenshot()
    parts.append(
        (
            "collectibles",
            crop_from_image(profile_img, config["crops"]["collectibles"], config, transform),
        )
    )
    parts.append(
        (
            "battle_attributes",
            crop_from_image(
                profile_img,
                config["crops"]["battle_attributes"],
                config,
                transform,
            ),
        )
    )

    for slot in config["clicks"]["equipment_slots"]:
        name = slot.get("name", "equipment")
        has_item, ratio = equipment_slot_has_item(profile_img, slot, config, transform)
        if not has_item:
            print(f"skipping {index:03d} empty equipment: {name}, color ratio={ratio:.3f}")
            continue
        print(f"capturing {index:03d} equipment: {name}")
        equip_img = open_equipment_popup(slot, profile_img, config, transform)
        if equip_img is None:
            print(f"skipping {index:03d} equipment because popup failed: {name}")
            continue
        parts.extend(capture_equipment_parts(equip_img, name, config, transform))
        if not close_equipment_popup(config, transform, equip_img.size):
            raise RuntimeError(
                "Equipment popup could not be closed after dynamic retries; task stopped safely."
            )

    print(f"opening {index:03d} skills")
    skills_part, skill_img = capture_skills_part(config, transform, profile_img.size, f"{index:03d} ")
    parts.append(("skills", skills_part))

    if config.get("save_parts"):
        for name, part in parts:
            save_part(parts_dir, name, part)

    final_img = stitch_character_layout(parts, config)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    final_img.save(output_path)
    print(f"done character {index:03d}: {output_path}")

    click(config["clicks"]["list_back"], config, transform, skill_img.size)
    time.sleep(float(timings["after_back_seconds"]))


def iter_batch_card_items(config):
    batch = config["batch"]
    columns = int(batch.get("columns", 17))
    rows = int(batch.get("enabled_rows", 2))
    base_x, base_y, width, height = batch["card_rect"]
    pitch_x, pitch_y = batch["card_pitch"]
    for row in range(rows):
        for column in range(columns):
            yield {
                "rect": [
                    base_x + pitch_x * column,
                    base_y + pitch_y * row,
                    width,
                    height,
                ],
                "anchor": "left",
                "row": row,
                "column": column,
            }


def scroll_character_list(config, transform, image_size):
    batch = config["batch"]
    point = batch.get("scroll_point", {"point": [1720, 810], "anchor": "center"})
    x, y = scale_point(point, config, transform, image_size)
    user32.SetCursorPos(x, y)
    time.sleep(0.1)
    send_mouse_wheel(int(batch.get("scroll_wheel_clicks", -5)))
    time.sleep(float(config["timing"]["after_scroll_seconds"]))


def run_batch_capture(config, output_dir, max_characters_override=0):
    first = screenshot()
    transform = get_transform(config, first.size)
    print(
        "screen: "
        f"{first.width}x{first.height}, "
        f"mode={transform['mode']}, "
        f"scale=({transform['sx']:.4f}, {transform['sy']:.4f})"
    )
    activate_filter_if_needed(config, transform)

    output_dir.mkdir(parents=True, exist_ok=True)
    batch = config["batch"]
    seen_hashes = []
    exported = 0
    no_new_pages = 0
    max_scrolls = int(batch.get("max_scrolls", 40))
    stop_after_no_new = int(batch.get("stop_after_no_new_pages", 2))
    max_characters = int(max_characters_override or batch.get("max_characters", 0))
    duplicate_threshold = int(batch.get("duplicate_hamming_threshold", 18))
    min_color_ratio = float(batch.get("min_card_color_ratio", 0.03))

    for page_index in range(max_scrolls + 1):
        print(f"scanning visible page {page_index + 1}")
        page_img = screenshot()
        page_new = 0

        for card_item in iter_batch_card_items(config):
            card = crop_from_image(page_img, card_item, config, transform)
            ratio = card_color_ratio(card)
            if ratio < min_color_ratio:
                continue
            card_hash = average_hash(card)
            if is_duplicate_card(card_hash, seen_hashes, duplicate_threshold):
                continue

            seen_hashes.append(card_hash)
            exported += 1
            page_new += 1
            output_path = output_dir / f"{exported:03d}.png"
            parts_dir = output_dir / f"{exported:03d}_parts"
            capture_character_at(config, transform, card_item, output_path, parts_dir, exported)

            page_img = screenshot()
            if max_characters and exported >= max_characters:
                print(f"reached max characters: {max_characters}")
                print(f"batch done: {exported} exported to {output_dir}")
                return

        if page_new == 0:
            no_new_pages += 1
        else:
            no_new_pages = 0
        print(f"visible page {page_index + 1}: {page_new} new, total {exported}")
        if no_new_pages >= stop_after_no_new:
            break
        if page_index < max_scrolls:
            scroll_character_list(config, transform, page_img.size)

    print(f"batch done: {exported} exported to {output_dir}")


def preview_regions(config, output_path):
    img = screenshot()
    transform = get_transform(config, img.size)
    draw = ImageDraw.Draw(img)
    colors = {
        "character_card": "red",
        "collectibles": "magenta",
        "battle_attributes": "cyan",
        "equipment_image": "yellow",
        "equipment_entries": "orange",
        "skills": "lime",
    }
    for name, crop_item in config["crops"].items():
        box = scale_rect(crop_item, config, transform, img.size)
        color = colors.get(name, "white")
        draw.rectangle(box, outline=color, width=4)
        draw.text((box[0] + 8, box[1] + 8), name, fill=color)

    click_items = [
        ("burst_filter", config["clicks"]["burst_filter"]),
        ("first_character", config["clicks"]["first_character"]),
        ("skill_tab", config["clicks"]["skill_tab"]),
    ]
    click_items.extend(
        (f"slot_{slot.get('name', index)}", slot)
        for index, slot in enumerate(config["clicks"]["equipment_slots"], 1)
    )
    for name, item in click_items:
        x, y = scale_point(item, config, transform, img.size)
        draw.ellipse((x - 9, y - 9, x + 9, y + 9), outline="white", width=3)
        draw.text((x + 12, y - 12), name, fill="white")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)
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
        description="Capture one NIKKE character details page and stitch selected regions horizontally."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=here / "nikke_character_capture_config.json",
        help="Path to config JSON.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=here / "screenshots" / date_dir / f"nikke_character_{timestamp}.png",
        help="Final stitched image path.",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Capture all visible/scrollable characters in order with overlap dedupe.",
    )
    parser.add_argument(
        "--max-characters",
        type=int,
        default=0,
        help="Batch mode safety limit. 0 means use config/no limit.",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Save an annotated screenshot showing crop regions and click points. No clicks are performed.",
    )
    parser.add_argument(
        "--mouse-pos",
        action="store_true",
        help="Print current mouse coordinates for calibration.",
    )
    return parser.parse_args()


def main():
    set_dpi_aware()
    args = parse_args()
    if args.mouse_pos:
        mouse_pos_loop()
        return

    config = load_config(args.config)
    if args.preview:
        preview_regions(config, args.output)
        return

    seconds = int(config["timing"].get("countdown_seconds", 3))
    print("put the game on the character list screen now")
    countdown(seconds)
    if args.batch:
        if args.output.suffix:
            output_dir = args.output.with_suffix("")
        else:
            output_dir = args.output
        run_batch_capture(config, output_dir, args.max_characters)
        return

    run_capture(config, args.output, args.output.with_suffix(""))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("cancelled")
        sys.exit(130)
    except RuntimeError as error:
        print(f"automation stopped safely: {error}")
        sys.exit(2)
