from __future__ import annotations

import os
import json
import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageOps

from .arena_ocr import ArenaOCRRecognizer, OCRItem
from .image_preprocess import prepare_for_ocr
from .image_splitter import ImageBlock, MatchRegions, save_match_debug, split_match_block
from .nikke_name_matcher import CANONICAL_COLON, NikkeNameMatcher


STAGE_NAME = "\u0036\u0034\u8fdb\u0033\u0032"
ATTACKER_CARD_SLOT_CENTERS = (0.14, 0.30, 0.49, 0.69, 0.87)
DEFENDER_CARD_SLOT_CENTERS = (0.215, 0.385, 0.555, 0.725, 0.895)
ATTACKER_POWER_SLOT_CENTERS = (0.082, 0.266, 0.449, 0.633, 0.816)
DEFENDER_POWER_SLOT_CENTERS = (0.172, 0.356, 0.539, 0.722, 0.906)
DETAIL_SLOT_CENTERS = (0.109, 0.291, 0.473, 0.655, 0.837)
DETAILED_RESULT_LEFT_PORTRAIT_X = (0.015, 0.205)
DETAILED_RESULT_RIGHT_PORTRAIT_X = (0.785, 0.985)
DETAILED_DEFEAT_VISUAL_DARK_THRESHOLD = 0.43
DETAILED_DEFEAT_VISUAL_CENTER_DARK_THRESHOLD = 0.50
DETAILED_DEFEAT_STRICT_COUNT = 5
DETAILED_DEFEAT_SOFT_COUNT = 4
RESULT_MODE_DETAILED = "detailed"
RESULT_MODE_SIMPLE = "simple"
RESULT_MODE_AUTO = "auto"
MIN_CARD_POWER = 5_000
CONFIDENT_MIN_CARD_POWER = 10_000
SUSPICIOUS_CARD_POWER = 200_000
HIGH_RISK_CARD_POWER = 300_000
MAX_CARD_POWER = 400_000
STRONG_POWER_RECHECK_SUPPORT = 12.0
POWER_TIGHT_RECHECK_SUPPORT = 20.0
POWER_ANCHORED_CONFIDENCE_FLOOR = 0.88
COLLECTION_ICON_BOX = (0.07, 0.41, 0.23, 0.515)
COLLECTION_NONE = "\u65e0"
COLLECTION_DIRECT_LABELS = ("R", "R15", "SR", "SR15", "SSR", "SSR3")
COLLECTION_TREASURE_LABELS = {"SSR", "SSR3"}
COLLECTION_ROW_ICON_X_OFFSETS = {
    "attacker": (0.120, 0.0965, 0.1027, 0.1189, 0.1153),
    "defender": (0.1045, 0.0913, 0.0778, 0.0642, 0.0506),
}
COLLECTION_ROW_ICON_X_HALF = 0.023
COLLECTION_ROW_ICON_Y_CENTER = 0.350
COLLECTION_ROW_ICON_Y_HALF = 0.073
COLLECTION_ROW_ICON_Y0 = COLLECTION_ROW_ICON_Y_CENTER - COLLECTION_ROW_ICON_Y_HALF
COLLECTION_ROW_ICON_Y1 = COLLECTION_ROW_ICON_Y_CENTER + COLLECTION_ROW_ICON_Y_HALF
COLLECTION_PRECISE_GROUP64_WIDE_BLOCK_HEIGHT_MIN = 2316
COLLECTION_PRECISE_GROUP64_WIDE = {
    "top_dy": -0.0395,
    "bottom_dy": 0.0,
    "attacker_x_half": 0.02008,
    "defender_x_half": 0.02005,
    "y_half": 0.06315,
}
COLLECTION_PRECISE_GROUP64_3840 = {
    "top_dy": -0.0395,
    "bottom_dy": 0.0,
    "attacker_x_half": 0.02008,
    "defender_x_half": 0.02005,
    "y_half": 0.06315,
}
COLLECTION_PRECISE_GROUP64_FHD = {
    "top_dy": -0.0260,
    "bottom_dy": 0.0148,
    "attacker_x_half": 0.02072,
    "defender_x_half": 0.02072,
    "y_half": 0.0599,
}
COLLECTION_TEMPLATE_SIZE = (64, 64)
COLLECTION_TEMPLATE_THRESHOLD = 0.72
COLLECTION_DIRECT_TEMPLATE_SIZE = (48, 48)
COLLECTION_DIRECT_SCORE_THRESHOLD = 0.15
COLLECTION_DIRECT_FAMILY_THRESHOLD = 0.11
COLLECTION_DIRECT_SR_DARK_THRESHOLD = 0.26
COLLECTION_DIRECT_SSR_DARK_THRESHOLD = 0.24
COLLECTION_DIRECT_R_DARK_THRESHOLD = 0.30
COLLECTION_DIRECT_ORANGE_OVERRIDE = 0.07
COLLECTION_DIRECT_CYAN_MARGIN = 0.06
COLLECTION_DIRECT_ORANGE_CYAN_MAX = 0.08
COLLECTION_DIRECT_SR_WHITE_GUARD = 0.30
COLLECTION_DIRECT_SR_DARK_WHITE_RATIO_GUARD = 1.0
COLLECTION_DIRECT_SR_PURPLE_GUARD = 0.15
COLLECTION_DIRECT_SR_ACTIVE_GUARD = 0.15
COLLECTION_DIRECT_SR_LOW_DARK_GUARD = 0.285
COLLECTION_DIRECT_SR_BRIGHT_WHITE_GUARD = 0.40
COLLECTION_DIRECT_SR_LOW_DARK_WHITE_RATIO_GUARD = 0.66
COLLECTION_DIRECT_SR_WEAK_PURPLE_GUARD = 0.21
COLLECTION_DIRECT_SR_SCORE_DELTA_GUARD = -0.04
COLLECTION_DIRECT_R_TO_SR_MARGIN = 0.015
COLLECTION_DIRECT_R_TO_SR_DARK_MAX = 0.03
COLLECTION_DIRECT_NONE_VETO_MARGIN = -0.18
COLLECTION_DIRECT_R_BRIGHT_NONE_MARGIN = -0.04
COLLECTION_DIRECT_R_BRIGHT_ACTIVE_MAX = 0.20
COLLECTION_DIRECT_R_BRIGHT_WHITE_MIN = 0.60
COLLECTION_DIRECT_R15_CYAN_OVERRIDE_DARK_MIN = 0.24
COLLECTION_DIRECT_R15_CYAN_OVERRIDE_DARK_MAX = 0.34
COLLECTION_DIRECT_R15_CYAN_OVERRIDE_WHITE_MAX = 0.46
COLLECTION_DIRECT_R15_CYAN_OVERRIDE_MARGIN = 0.04
COLLECTION_DIRECT_R15_CYAN_OVERRIDE_ACTIVE_MIN = 0.18
COLLECTION_DIRECT_R15_CYAN_OVERRIDE_SCORE_MARGIN = -0.08
NAME_PROFILE_DEFAULT = "default"
NAME_PROFILE_FHD = "fhd"
SOURCE_PROFILE_3840 = "3840x2160"
FHD_NAME_TEXT_ALIASES = (
    ("\u8d22\u72fc", "\u8c7a\u72fc"),
    ("\u6750\u72fc", "\u8c7a\u72fc"),
    ("\u5bf9\u72fc", "\u8c7a\u72fc"),
    ("\u6e21\u9e21", "\u6e21\u9e26"),
)
STAT_LEVEL_HEADERS = (
    "\u6781\u4e50\u51c0\u571f",
    "\u6cf0\u7279\u62c9",
    "\u7c73\u897f\u5229\u65af",
    "\u671d\u5723\u8005",
    "\u53cd\u5e38",
    "\u706b\u529b\u578b",
    "\u9632\u5fa1\u578b",
    "\u8f85\u52a9\u578b",
)
ATTACKER_STAT_LEVEL_CENTERS = (0.070, 0.185, 0.300, 0.399, 0.513, 0.607, 0.731, 0.856)
DEFENDER_STAT_LEVEL_CENTERS = (0.159, 0.274, 0.388, 0.486, 0.601, 0.694, 0.818, 0.944)
STAT_LEVEL_MIN = 1
STAT_LEVEL_MAX = 250
STAT_LEVEL_RECHECK_BELOW = 50
STAT_LEVEL_AREA = (0.0, 0.948, 1.0, 0.998)
STAT_LEVEL_SLOT_Y0 = 0.980
STAT_LEVEL_SLOT_Y1 = 0.998


@dataclass
class _PowerObservation:
    value: int
    confidence: float
    anchored: bool
    trailing_marker: bool
    distance: float = 0.0
    text: str = ""


@dataclass
class _PowerSlotReading:
    value: int | None = None
    confidence: float = 0.0
    text: str = ""
    distance: float = 1.0
    anchored: bool = False
    trailing_marker: bool = False


@dataclass
class _StatLevelObservation:
    value: int
    confidence: float
    from_lv: bool
    text: str = ""
    weight: float = 1.0


@dataclass(frozen=True)
class _CollectionDirectTemplate:
    label: str
    features: np.ndarray
    mask: np.ndarray


@dataclass(frozen=True)
class _CollectionSlotGeometry:
    x_center: float
    y_center: float
    x_half: float
    y_half: float


def _crop_rel(image: Image.Image, box: tuple[float, float, float, float]) -> Image.Image:
    w, h = image.size
    x0 = max(0, min(w, int(w * box[0])))
    y0 = max(0, min(h, int(h * box[1])))
    x1 = max(0, min(w, int(w * box[2])))
    y1 = max(0, min(h, int(h * box[3])))
    if x1 <= x0 or y1 <= y0:
        return image.crop((0, 0, 1, 1))
    return image.crop((x0, y0, x1, y1))


def _box_rel_to_abs(
    origin: tuple[float, float],
    size: tuple[float, float],
    box: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    ox, oy = origin
    w, h = size
    return (ox + w * box[0], oy + h * box[1], ox + w * box[2], oy + h * box[3])


def _box_abs_to_rel(
    box: tuple[float, float, float, float],
    origin: tuple[float, float],
    size: tuple[float, float],
) -> tuple[float, float, float, float]:
    ox, oy = origin
    w, h = max(1.0, size[0]), max(1.0, size[1])
    return ((box[0] - ox) / w, (box[1] - oy) / h, (box[2] - ox) / w, (box[3] - oy) / h)


def _clamp_abs_box(
    box: tuple[float, float, float, float],
    origin: tuple[float, float],
    size: tuple[float, float],
) -> tuple[float, float, float, float]:
    ox, oy = origin
    w, h = size
    return (
        max(ox, min(ox + w, box[0])),
        max(oy, min(oy + h, box[1])),
        max(ox, min(ox + w, box[2])),
        max(oy, min(oy + h, box[3])),
    )


def _module_data_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "data"


def _items_to_text(items: list[OCRItem]) -> str:
    return " ".join(item.text.strip() for item in items if item.text.strip())


def _ocr_text(ocr: ArenaOCRRecognizer, image: Image.Image, region_name: str) -> tuple[str, list[OCRItem]]:
    items = ocr.recognize_region(prepare_for_ocr(image), region_name)
    return _items_to_text(items), items


def _clean_text(text: str) -> str:
    text = (text or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text.strip(" :：|/\\")


def _extract_id(text: str) -> str:
    match = re.search(r"ID\s*[:：]?\s*([0-9]{6,})", text, flags=re.IGNORECASE)
    return match.group(1) if match else ""


def _is_noise_token(text: str) -> bool:
    text = _clean_text(text)
    if not text:
        return True
    if re.fullmatch(r"[xX×*]?\d[\d,.Kk/%]*", text):
        return True
    noise_keywords = (
        "ID",
        "服务器",
        "服务",
        "同步等级",
        "部队战斗力",
        "作战人员",
        "部队现状",
        "时装",
        "全爆裂",
        "战败",
        "WIN",
        "LOSE",
        "ROUND",
        "ARENA",
        "Lv",
        "LV",
        "MAX",
    )
    return any(keyword in text for keyword in noise_keywords)


def _character_token_variants(text: str) -> list[str]:
    text = _clean_text(text)
    return [text] if text else []


def _name_profile_from_block_height(block_height: int | None) -> str:
    if block_height is not None and block_height < COLLECTION_PRECISE_GROUP64_WIDE_BLOCK_HEIGHT_MIN:
        return NAME_PROFILE_FHD
    return NAME_PROFILE_DEFAULT


def _apply_name_profile_aliases(text: str, name_profile: str) -> str:
    if name_profile != NAME_PROFILE_FHD:
        return text
    value = text
    for wrong, correct in FHD_NAME_TEXT_ALIASES:
        value = value.replace(wrong, correct)
    return value


def _best_character_match(
    text: str,
    matcher: NikkeNameMatcher,
    name_profile: str = NAME_PROFILE_DEFAULT,
) -> tuple[str, float]:
    best_name = ""
    best_score = -1.0
    for variant in _character_token_variants(text):
        variant = _apply_name_profile_aliases(variant, name_profile)
        matched = matcher.match_name(variant)
        name = str(matched.get("matched_name") or "").strip()
        score = float(matched.get("score") or 0.0)
        if name == "unknown":
            name = ""
        if matcher.names and name in matcher.names and score >= best_score:
            best_name = name
            best_score = score
        elif not matcher.names and variant and score >= best_score:
            best_name = variant
            best_score = score
    return best_name, best_score


def recognize_player_id(
    side_image: Image.Image,
    side: str,
    ocr: ArenaOCRRecognizer,
) -> str:
    if side == "attacker":
        id_box = (0.23, 0.205, 0.86, 0.245)
        fallback_box = (0.15, 0.19, 0.98, 0.255)
    else:
        id_box = (0.02, 0.205, 0.76, 0.245)
        fallback_box = (0.02, 0.19, 0.85, 0.255)
    id_text, id_items = _ocr_text(ocr, _crop_rel(side_image, id_box), f"{side}_id")
    player_id = _extract_id(" ".join([id_text, _items_to_text(id_items)]))
    if player_id:
        return player_id

    fallback_text, fallback_items = _ocr_text(
        ocr,
        _crop_rel(side_image, fallback_box),
        f"{side}_id_fallback",
    )
    return _extract_id(" ".join([fallback_text, _items_to_text(fallback_items)]))


def recognize_player_nickname(
    side_image: Image.Image,
    side: str,
    ocr: ArenaOCRRecognizer,
) -> str:
    # The nickname is the single text row between the decorative title and ID.
    # Keep this crop narrow so badges, server text and profile titles stay out.
    name_box = (0.20, 0.172, 0.74, 0.202) if side == "attacker" else (0.12, 0.172, 0.67, 0.202)
    nickname_image = prepare_for_ocr(_crop_rel(side_image, name_box))
    readings = ocr.recognize_nickname_candidates(nickname_image, f"{side}_nickname")
    candidates: list[tuple[float, int, str]] = []
    for raw_text, confidence, language in readings:
        text = _clean_text(raw_text)
        if not text or len(text) > 28 or re.fullmatch(r"[\d\W_]+", text):
            continue
        if any(token in text.upper() for token in ("ID", "LV", "SERVER")) or "\u670d\u52a1\u5668" in text:
            continue
        has_kana = bool(re.search(r"[\u3040-\u30ff]", text))
        has_hangul = bool(re.search(r"[\u1100-\u11ff\u3130-\u318f\uac00-\ud7af]", text))

        # The Korean dictionary occasionally appends one spurious Han glyph to
        # an otherwise clean Hangul result. Korean nicknames commonly mix
        # Hangul with Latin letters/numbers, but Hanja is exceptionally rare in
        # this UI, so discard only those Han glyphs when Hangul is present.
        if language == "korean" and has_hangul:
            text = _clean_text(re.sub(r"[\u3400-\u9fff]+", "", text))
            has_hangul = bool(re.search(r"[\u1100-\u11ff\u3130-\u318f\uac00-\ud7af]", text))

        # Japanese/Korean recognizers are deliberately script-gated. Without
        # this guard they can assign high confidence to nonsense readings of a
        # perfectly valid Chinese or Latin nickname.
        if language == "japan" and not has_kana:
            continue
        if language == "korean" and not has_hangul:
            continue
        score = float(confidence)
        if language == "japan" and has_kana:
            score += 0.15
        elif language == "korean" and has_hangul:
            score += 0.15
        candidates.append((score, len(text), text))
    if not candidates:
        return ""
    return max(candidates, key=lambda value: (value[0], value[1]))[2]


def _candidate_character_texts(items: list[OCRItem]) -> list[tuple[float, str, float]]:
    candidates: list[tuple[float, str, float]] = []
    for item in items:
        text = _clean_text(item.text)
        if _is_noise_token(text):
            continue
        if len(text) <= 1 or len(text) > 18:
            continue
        if not re.search(r"[\u4e00-\u9fffA-Za-z]", text):
            continue
        xs = [p[0] for p in item.bbox]
        x_center = sum(xs) / len(xs) if xs else 0.0
        candidates.append((x_center, text, item.confidence))
    return sorted(candidates, key=lambda pair: pair[0])


def _match_character_names(
    items: list[OCRItem],
    matcher: NikkeNameMatcher,
    name_profile: str = NAME_PROFILE_DEFAULT,
) -> list[str]:
    names: list[str] = []
    for _, text, _ in _candidate_character_texts(items):
        name, score = _best_character_match(text, matcher, name_profile=name_profile)
        if not name or name == "unknown":
            continue
        if matcher.names and name not in matcher.names and score < matcher.threshold:
            continue
        if matcher.names and score < 68.0:
            continue
        if name not in names:
            names.append(name)
        if len(names) >= 5:
            break
    return names


def _best_positioned_character_match(
    items: list[OCRItem],
    matcher: NikkeNameMatcher,
    image: Image.Image,
    name_profile: str = NAME_PROFILE_DEFAULT,
    target_x_ratio: float = 0.62,
) -> tuple[str, float, str]:
    if not items:
        return "", -1.0, ""
    coord_size = _ocr_coordinate_size(items, image)
    best_name = ""
    best_score = -1.0
    best_text = ""
    for item in items:
        text = _clean_text(item.text)
        if _is_noise_token(text):
            continue
        if len(text) <= 1 or len(text) > 18:
            continue
        if not re.search(r"[\u4e00-\u9fffA-Za-z]", text):
            continue
        name, match_score = _best_character_match(text, matcher, name_profile=name_profile)
        if not name or name == "unknown" or match_score < matcher.threshold:
            continue
        if (
            name_profile == NAME_PROFILE_FHD
            and CANONICAL_COLON in matcher.normalize_name(name)
            and not _has_special_suffix_evidence(text, name, matcher)
        ):
            continue
        x_ratio, _ = _ocr_item_center_ratio(item, image, coord_size)
        # Card names are rendered in the lower-right part of the card. In FHD
        # crops, adjacent cards can leak into the left edge, so rank by the
        # expected local label position instead of taking the first OCR token.
        if x_ratio < 0.30 or x_ratio > 0.98:
            continue
        distance = abs(x_ratio - target_x_ratio)
        if distance > 0.46:
            continue
        positioned_score = match_score + max(0.0, min(1.0, item.confidence)) * 2.0 - distance * 45.0
        if positioned_score > best_score:
            best_name = name
            best_score = positioned_score
            best_text = text
    return best_name, best_score, best_text


def _base_name_norm(name: str, matcher: NikkeNameMatcher) -> str:
    return matcher.normalize_name(name).split(CANONICAL_COLON, 1)[0]


def _has_special_variants(name: str, matcher: NikkeNameMatcher) -> bool:
    base = _base_name_norm(name, matcher)
    if not base:
        return False
    return any(_base_name_norm(special, matcher) == base for special in getattr(matcher, "special_names", []))


def _special_upgrade_from_texts(texts: list[str], current_name: str, matcher: NikkeNameMatcher) -> str:
    base = _base_name_norm(current_name, matcher)
    if not base:
        return current_name

    special_candidates = [
        special
        for special in getattr(matcher, "special_names", [])
        if _base_name_norm(special, matcher) == base
    ]
    if not special_candidates:
        return current_name

    joined = _clean_text(" ".join(text for text in texts if text))
    if not joined:
        return current_name

    matched = matcher.match_name(joined)
    matched_name = str(matched.get("matched_name") or "").strip()
    score = float(matched.get("score") or 0.0)
    if matched_name in special_candidates and score >= max(72.0, matcher.threshold - 10.0):
        return matched_name

    joined_norm = matcher.normalize_name(joined).replace(CANONICAL_COLON, "")
    for special in special_candidates:
        special_norm = matcher.normalize_name(special)
        suffix_norm = special_norm.split(CANONICAL_COLON, 1)[1] if CANONICAL_COLON in special_norm else ""
        suffix_compact = suffix_norm.replace(CANONICAL_COLON, "")
        if suffix_compact and suffix_compact[:2] in joined_norm:
            return special
    return current_name


def _has_special_suffix_evidence(text: str, special_name: str, matcher: NikkeNameMatcher) -> bool:
    text_norm = matcher.normalize_name(text)
    if CANONICAL_COLON not in text_norm:
        return False
    text_suffix = text_norm.split(CANONICAL_COLON, 1)[1].replace(CANONICAL_COLON, "")
    special_norm = matcher.normalize_name(special_name)
    if CANONICAL_COLON not in special_norm:
        return False
    special_suffix = special_norm.split(CANONICAL_COLON, 1)[1].replace(CANONICAL_COLON, "")
    if not text_suffix or not special_suffix:
        return False
    take = min(2, len(text_suffix))
    return special_suffix.startswith(text_suffix[:take])


def _promote_fhd_special_from_label(
    current_name: str,
    card_image: Image.Image,
    ocr: ArenaOCRRecognizer,
    matcher: NikkeNameMatcher,
    region_name: str,
    label_image: Image.Image | None = None,
) -> str:
    if label_image is None:
        label_image = _crop_rel(card_image, (0.0, 0.47, 1.0, 1.0))
    prepared = prepare_for_ocr(label_image)
    items = ocr.recognize_region(prepared, f"{region_name}_fhd_label")
    name, _, text = _best_positioned_character_match(
        items,
        matcher,
        prepared,
        name_profile=NAME_PROFILE_FHD,
    )
    if (
        name
        and name != current_name
        and _base_name_norm(name, matcher) == _base_name_norm(current_name, matcher)
        and _has_special_suffix_evidence(text, name, matcher)
    ):
        return name
    return current_name


def _promote_special_card_name(
    current_name: str,
    card_image: Image.Image,
    ocr: ArenaOCRRecognizer,
    matcher: NikkeNameMatcher,
    region_name: str,
    name_profile: str = NAME_PROFILE_DEFAULT,
    label_image: Image.Image | None = None,
) -> str:
    if not current_name or not _has_special_variants(current_name, matcher):
        return current_name

    if name_profile == NAME_PROFILE_FHD:
        return _promote_fhd_special_from_label(current_name, card_image, ocr, matcher, region_name, label_image=label_image)

    texts: list[str] = []
    # The visible card label sits low on the card and can be truncated by the
    # frame. Scan a few overlapping strips only for names that have known
    # special variants, so normal cards do not pay extra OCR cost.
    for index, box in enumerate(((0.02, 0.48, 1.00, 0.78), (0.02, 0.54, 1.00, 0.88), (0.00, 0.60, 1.00, 0.96)), start=1):
        label_image = _crop_rel(card_image, box)
        items = ocr.recognize_region(prepare_for_ocr(label_image), f"{region_name}_special_{index}")
        texts.extend(item.text for item in items)
        texts.append(_items_to_text(items))
        upgraded = _special_upgrade_from_texts(texts, current_name, matcher)
        if upgraded != current_name:
            return upgraded
    return current_name


def _match_character_slots(
    items: list[OCRItem],
    matcher: NikkeNameMatcher,
    image_width: int,
    centers: tuple[float, ...],
    slot_count: int = 5,
    name_profile: str = NAME_PROFILE_DEFAULT,
) -> list[str]:
    slots: list[str] = [""] * slot_count
    slot_scores: list[float] = [-1.0] * slot_count
    width = max(1, image_width)
    centers = centers[:slot_count]
    for x_center, text, ocr_confidence in _candidate_character_texts(items):
        name, match_score = _best_character_match(text, matcher, name_profile=name_profile)
        if not name or name == "unknown" or match_score < matcher.threshold:
            continue
        x_ratio = x_center / width
        slot = min(range(slot_count), key=lambda index: abs(x_ratio - centers[index]))
        combined_score = match_score + max(0.0, min(1.0, ocr_confidence)) * 2.0
        if combined_score > slot_scores[slot]:
            slots[slot] = name
            slot_scores[slot] = combined_score
    return slots


def _match_power_slots(
    items: list[OCRItem],
    image_width: int,
    image_height: int,
    centers: tuple[float, ...],
    slot_count: int = 5,
) -> list[int | None]:
    slots: list[int | None] = [None] * slot_count
    slot_scores: list[float] = [-1.0] * slot_count
    width = max(1, image_width)
    height = max(1, image_height)
    centers = centers[:slot_count]
    for item in items:
        value = _extract_card_power(item.text)
        if value is None:
            continue
        xs = [point[0] for point in item.bbox]
        ys = [point[1] for point in item.bbox]
        if not xs or not ys:
            continue
        x_ratio = (sum(xs) / len(xs)) / width
        y_ratio = (sum(ys) / len(ys)) / height
        if not 0.70 <= y_ratio <= 0.90:
            continue
        slot = min(range(slot_count), key=lambda index: abs(x_ratio - centers[index]))
        distance = abs(x_ratio - centers[slot])
        if distance > 0.09:
            continue
        score = max(0.0, min(1.0, item.confidence)) - distance
        if score > slot_scores[slot]:
            slots[slot] = value
            slot_scores[slot] = score
    return slots


def _collection_feature_vector(image: Image.Image) -> tuple[tuple[int, int, int, int, int], ...]:
    resized = image.convert("RGB").resize(COLLECTION_TEMPLATE_SIZE, Image.Resampling.LANCZOS)
    features: list[tuple[int, int, int, int, int]] = []
    for r, g, b in resized.getdata():
        mx = max(r, g, b)
        mn = min(r, g, b)
        dark = int(mx < 105)
        white = int(mx > 170 and mx - mn < 78)
        cyan = int(b > 110 and g > 100 and r < 170 and b - r > 22 and g - r > 8)
        purple = int(b > 100 and r > 80 and g < 180 and b - g > 22 and r - g > -14)
        orange = int(r > 150 and 30 < g < 210 and b < 160 and r - b > 42 and r - g > 16)
        features.append((dark, white, cyan, purple, orange))
    return tuple(features)


@lru_cache(maxsize=1)
def _collection_template_features() -> tuple[tuple[str, tuple[tuple[int, int, int, int, int], ...]], ...]:
    template_dir = _module_data_dir() / "collection_templates"
    templates: list[tuple[str, tuple[tuple[int, int, int, int, int], ...]]] = []
    for label in ("R", "SR", "SR15", "SSR", "SSR15"):
        for path in sorted(template_dir.glob(f"{label}*.png")):
            try:
                templates.append((label, _collection_feature_vector(Image.open(path))))
            except Exception:
                continue
    return tuple(templates)


def _collection_template_score(
    candidate: tuple[tuple[int, int, int, int, int], ...],
    template: tuple[tuple[int, int, int, int, int], ...],
) -> float:
    if not candidate or len(candidate) != len(template):
        return 0.0
    weights = (0.95, 0.35, 1.45, 1.45, 1.45)
    total_weight = sum(weights) * len(candidate)
    diff = 0.0
    for cand_pixel, template_pixel in zip(candidate, template):
        for index, weight in enumerate(weights):
            diff += abs(cand_pixel[index] - template_pixel[index]) * weight
    return max(0.0, 1.0 - diff / max(1.0, total_weight))


def _match_collection_template(icon_image: Image.Image) -> str | None:
    templates = _collection_template_features()
    if not templates:
        return None
    candidate = _collection_feature_vector(icon_image)
    best_label = COLLECTION_NONE
    best_score = 0.0
    for label, template in templates:
        score = _collection_template_score(candidate, template)
        if score > best_score:
            best_label = label
            best_score = score
    if best_score >= COLLECTION_TEMPLATE_THRESHOLD:
        return best_label
    return COLLECTION_NONE


def _normalize_collection_label(label: str) -> str:
    text = str(label or "").strip().upper()
    if text == "SSR15":
        return "SSR3"
    if text in COLLECTION_DIRECT_LABELS:
        return text
    return COLLECTION_NONE


def _collection_cv_template_dir() -> Path:
    return _module_data_dir() / "collection_cv_templates" / "v2_manual"


def _collection_direct_features(rgb: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)
    hue = hsv[:, :, 0] / 179.0 * 2.0 * np.pi
    saturation = hsv[:, :, 1] / 255.0
    value = hsv[:, :, 2] / 255.0
    rgb_f = rgb.astype(np.float32) / 255.0
    return np.stack(
        (
            np.cos(hue),
            np.sin(hue),
            saturation,
            value,
            rgb_f[:, :, 0],
            rgb_f[:, :, 1],
            rgb_f[:, :, 2],
        ),
        axis=2,
    ).astype(np.float32)


@lru_cache(maxsize=1)
def _collection_direct_templates() -> tuple[_CollectionDirectTemplate, ...]:
    template_dir = _collection_cv_template_dir()
    manifest_path = template_dir / "manifest.json"
    if not manifest_path.exists():
        return tuple()
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return tuple()

    templates: list[_CollectionDirectTemplate] = []
    for entry in manifest.get("templates", []):
        label = _normalize_collection_label(entry.get("label", ""))
        if label not in COLLECTION_DIRECT_LABELS:
            continue
        relative_path = entry.get("path") or entry.get("tight_path") or entry.get("full_path")
        if not relative_path:
            continue
        path = template_dir / relative_path
        if not path.exists():
            continue
        try:
            image = Image.open(path).convert("RGBA").resize(COLLECTION_DIRECT_TEMPLATE_SIZE, Image.Resampling.LANCZOS)
            rgba = np.asarray(image, dtype=np.uint8)
            mask = rgba[:, :, 3] > 24
            if float(mask.mean()) < 0.04:
                mask[:, :] = True
            templates.append(
                _CollectionDirectTemplate(
                    label=label,
                    features=_collection_direct_features(rgba[:, :, :3]),
                    mask=cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8)).astype(bool),
                )
            )
        except Exception:
            continue
    return tuple(templates)


@lru_cache(maxsize=1)
def _collection_direct_negative_templates() -> tuple[_CollectionDirectTemplate, ...]:
    template_dir = _collection_cv_template_dir()
    manifest_path = template_dir / "manifest.json"
    if not manifest_path.exists():
        return tuple()
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return tuple()

    templates: list[_CollectionDirectTemplate] = []
    for entry in manifest.get("templates", []):
        label = _normalize_collection_label(entry.get("label", ""))
        if label != COLLECTION_NONE and entry.get("kind") != "negative":
            continue
        relative_path = entry.get("path") or entry.get("tight_path") or entry.get("full_path")
        if not relative_path:
            continue
        path = template_dir / relative_path
        if not path.exists():
            continue
        try:
            image = Image.open(path).convert("RGBA").resize(COLLECTION_DIRECT_TEMPLATE_SIZE, Image.Resampling.LANCZOS)
            rgba = np.asarray(image, dtype=np.uint8)
            mask = rgba[:, :, 3] > 24
            if float(mask.mean()) < 0.04:
                mask[:, :] = True
            templates.append(
                _CollectionDirectTemplate(
                    label=COLLECTION_NONE,
                    features=_collection_direct_features(rgba[:, :, :3]),
                    mask=cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8)).astype(bool),
                )
            )
        except Exception:
            continue
    return tuple(templates)


@lru_cache(maxsize=1)
def _collection_generic_positive_mask() -> np.ndarray | None:
    templates = _collection_direct_templates()
    if not templates:
        return None
    masks = np.stack([template.mask for template in templates]).astype(np.float32)
    mask = masks.mean(axis=0) > 0.18
    if float(mask.mean()) < 0.04:
        mask[:, :] = True
    return mask


def _collection_direct_score(candidate: np.ndarray, template: _CollectionDirectTemplate) -> float:
    weights = np.asarray((1.2, 1.2, 1.4, 0.8, 0.35, 0.35, 0.35), dtype=np.float32)
    diff = np.abs(candidate - template.features) * weights
    denominator = max(1.0, float(template.mask.sum()) * float(weights.sum()))
    score = 1.0 - float((diff * template.mask[:, :, None]).sum()) / denominator
    return max(0.0, min(1.0, score))


def _collection_visual_stats(rgb: np.ndarray, mask: np.ndarray | None = None) -> dict[str, float]:
    if mask is None:
        mask = np.ones(rgb.shape[:2], dtype=bool)
    hsv = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2HSV)
    hue = hsv[:, :, 0]
    saturation = hsv[:, :, 1] / 255.0
    value = hsv[:, :, 2] / 255.0
    active = mask & (saturation > 0.22) & (value > 0.25)
    cyan = active & (hue >= 78) & (hue <= 105)
    purple = active & (hue >= 122) & (hue <= 162)
    orange = active & (((hue >= 2) & (hue <= 28)) | ((hue >= 170) & (hue <= 179)))
    dark = mask & (value < 0.45)
    white = mask & (saturation < 0.22) & (value > 0.68)
    total = max(1, int(mask.sum()))
    return {
        "cyan": float(cyan.sum() / total),
        "purple": float(purple.sum() / total),
        "orange": float(orange.sum() / total),
        "active": float(active.sum() / total),
        "family_max": float(max(cyan.sum(), purple.sum(), orange.sum()) / total),
        "family_sum": float((cyan.sum() + purple.sum() + orange.sum()) / total),
        "dark": float(dark.sum() / total),
        "white": float(white.sum() / total),
        "dark_white_ratio": float(dark.sum() / max(1, int(white.sum()))),
    }


def _postprocess_collection_direct_label(label: str, scores: dict[str, float], stats: dict[str, float]) -> str:
    adjusted = label
    if (
        adjusted in {"R", "R15"}
        and stats["orange"] >= COLLECTION_DIRECT_ORANGE_OVERRIDE
        and stats["orange"] > stats["cyan"] + COLLECTION_DIRECT_CYAN_MARGIN
        and stats["cyan"] < COLLECTION_DIRECT_ORANGE_CYAN_MAX
    ):
        adjusted = "SSR3" if stats["dark"] >= COLLECTION_DIRECT_SSR_DARK_THRESHOLD else "SSR"
    if adjusted in {"SR", "SR15"}:
        is_level_15 = stats["dark"] >= COLLECTION_DIRECT_SR_DARK_THRESHOLD
        if (
            is_level_15
            and stats["white"] >= COLLECTION_DIRECT_SR_WHITE_GUARD
            and stats["dark_white_ratio"] < COLLECTION_DIRECT_SR_DARK_WHITE_RATIO_GUARD
            and (
                stats["purple"] < COLLECTION_DIRECT_SR_PURPLE_GUARD
                or stats["active"] < COLLECTION_DIRECT_SR_ACTIVE_GUARD
            )
        ):
            is_level_15 = False
        if (
            is_level_15
            and stats["dark"] <= COLLECTION_DIRECT_SR_LOW_DARK_GUARD
            and stats["white"] >= COLLECTION_DIRECT_SR_BRIGHT_WHITE_GUARD
            and stats["dark_white_ratio"] <= COLLECTION_DIRECT_SR_LOW_DARK_WHITE_RATIO_GUARD
            and stats["purple"] <= COLLECTION_DIRECT_SR_WEAK_PURPLE_GUARD
            and scores.get("SR15", 0.0) - scores.get("SR", 0.0) <= COLLECTION_DIRECT_SR_SCORE_DELTA_GUARD
        ):
            is_level_15 = False
        return "SR15" if is_level_15 else "SR"
    if (
        adjusted in {"SSR", "SSR3"}
        and stats["dark"] >= COLLECTION_DIRECT_R15_CYAN_OVERRIDE_DARK_MIN
        and stats["dark"] <= COLLECTION_DIRECT_R15_CYAN_OVERRIDE_DARK_MAX
        and stats["white"] <= COLLECTION_DIRECT_R15_CYAN_OVERRIDE_WHITE_MAX
        and stats["cyan"] >= stats["orange"] + COLLECTION_DIRECT_R15_CYAN_OVERRIDE_MARGIN
        and stats["active"] >= COLLECTION_DIRECT_R15_CYAN_OVERRIDE_ACTIVE_MIN
        and scores.get("R15", 0.0) - scores.get("R", 0.0) >= COLLECTION_DIRECT_R15_CYAN_OVERRIDE_SCORE_MARGIN
    ):
        return "R15"
    if adjusted in {"SSR", "SSR3"}:
        return "SSR3" if stats["dark"] >= COLLECTION_DIRECT_SSR_DARK_THRESHOLD else "SSR"
    if adjusted in {"R", "R15"}:
        return "R15" if stats["dark"] >= COLLECTION_DIRECT_R_DARK_THRESHOLD else "R"
    return adjusted


def _classify_collection_icon_by_direct_template(icon_image: Image.Image) -> str | None:
    templates = _collection_direct_templates()
    if not templates:
        return None
    try:
        rgb = np.asarray(
            icon_image.convert("RGB").resize(COLLECTION_DIRECT_TEMPLATE_SIZE, Image.Resampling.LANCZOS),
            dtype=np.uint8,
        )
        candidate = _collection_direct_features(rgb)
        scores: dict[str, float] = {}
        for template in templates:
            score = _collection_direct_score(candidate, template)
            if score > scores.get(template.label, 0.0):
                scores[template.label] = score
        if not scores:
            return None
        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        best_label, best_score = ranked[0]
        second_score = ranked[1][1] if len(ranked) > 1 else 0.0
        stats = _collection_visual_stats(rgb, _collection_generic_positive_mask())
        if best_score < COLLECTION_DIRECT_SCORE_THRESHOLD or stats["family_max"] < COLLECTION_DIRECT_FAMILY_THRESHOLD:
            return COLLECTION_NONE
        none_score: float | None = None
        negative_templates = _collection_direct_negative_templates()
        if negative_templates:
            none_score = max(_collection_direct_score(candidate, template) for template in negative_templates)
            if best_score - none_score <= COLLECTION_DIRECT_NONE_VETO_MARGIN:
                return COLLECTION_NONE
        label = _postprocess_collection_direct_label(best_label, scores, stats)
        if (
            label == "R"
            and none_score is not None
            and best_score - none_score <= COLLECTION_DIRECT_R_BRIGHT_NONE_MARGIN
            and stats["active"] <= COLLECTION_DIRECT_R_BRIGHT_ACTIVE_MAX
            and stats["white"] >= COLLECTION_DIRECT_R_BRIGHT_WHITE_MIN
        ):
            return COLLECTION_NONE
        if (
            label == "R"
            and stats["dark"] <= COLLECTION_DIRECT_R_TO_SR_DARK_MAX
            and best_score - second_score <= COLLECTION_DIRECT_R_TO_SR_MARGIN
            and _classify_collection_icon_by_color(icon_image) == "SR"
        ):
            return "SR"
        return label
    except Exception:
        return None


@lru_cache(maxsize=1)
def _collection_detailed_slot_geometries() -> dict[str, dict[int, dict[int, _CollectionSlotGeometry]]]:
    template_dir = _collection_cv_template_dir()
    manifest_path = template_dir / "manifest.json"
    calibration_path = template_dir / "position_calibration_detailed.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            configured = manifest.get("position_calibration_detailed")
            if configured:
                calibration_path = template_dir / configured
        except Exception:
            pass
    if not calibration_path.exists():
        return {}
    try:
        calibration = json.loads(calibration_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    result: dict[str, dict[int, dict[int, _CollectionSlotGeometry]]] = {}
    for side, teams in (calibration.get("recommended") or {}).items():
        result.setdefault(side, {})
        for team_index, slots in teams.items():
            team_key = int(team_index)
            result[side].setdefault(team_key, {})
            for slot_index, values in slots.items():
                slot_key = int(slot_index)
                result[side][team_key][slot_key] = _CollectionSlotGeometry(
                    x_center=float(values["x_center"]),
                    y_center=float(values["y_center"]),
                    x_half=float(values["x_half"]),
                    y_half=float(values["y_half"]),
                )
    return result


def _collection_slot_geometry(
    side: str,
    team_index: int,
    slot_index: int,
    fallback_center: float,
) -> _CollectionSlotGeometry:
    detailed = _collection_detailed_slot_geometries().get(side, {}).get(team_index, {}).get(slot_index)
    if detailed:
        return detailed
    return _CollectionSlotGeometry(
        x_center=fallback_center,
        y_center=COLLECTION_ROW_ICON_Y_CENTER,
        x_half=COLLECTION_ROW_ICON_X_HALF,
        y_half=COLLECTION_ROW_ICON_Y_HALF,
    )


def _collection_precise_group64_geometry(
    geometry: _CollectionSlotGeometry,
    *,
    side: str,
    match_index: int | None,
    stage_name: str,
    block_height: int | None,
    source_profile: str = "",
) -> tuple[_CollectionSlotGeometry, float]:
    if stage_name != STAGE_NAME or match_index not in {1, 2, 3, 4} or block_height is None:
        return geometry, 0.0
    if source_profile == SOURCE_PROFILE_3840:
        profile = COLLECTION_PRECISE_GROUP64_3840
    else:
        profile = (
            COLLECTION_PRECISE_GROUP64_WIDE
            if block_height >= COLLECTION_PRECISE_GROUP64_WIDE_BLOCK_HEIGHT_MIN
            else COLLECTION_PRECISE_GROUP64_FHD
        )
    x_half_key = "attacker_x_half" if side == "attacker" else "defender_x_half"
    dy = profile["top_dy"] if match_index in {1, 2} else profile["bottom_dy"]
    return (
        _CollectionSlotGeometry(
            x_center=geometry.x_center,
            y_center=geometry.y_center,
            x_half=float(profile[x_half_key]),
            y_half=float(profile["y_half"]),
        ),
        float(dy),
    )


def _classify_collection_icon_by_color(icon_image: Image.Image) -> str:
    icon_image = icon_image.convert("RGB")
    total = max(1, icon_image.width * icon_image.height)
    dark = 0
    white = 0
    cyan = 0
    purple = 0
    orange = 0
    colored = 0
    for r, g, b in icon_image.getdata():
        mx = max(r, g, b)
        mn = min(r, g, b)
        if mx < 115:
            dark += 1
        if mx > 175 and mx - mn < 70:
            white += 1
        if mx - mn > 45 and mx > 105:
            colored += 1
        if b > 115 and g > 105 and r < 165 and b - r > 25 and g - r > 10:
            cyan += 1
        if b > 105 and r > 85 and g < 185 and b - g > 18 and r - g > -18:
            purple += 1
        if r > 155 and 35 < g < 205 and b < 165 and r - b > 38 and r - g > 14:
            orange += 1

    scores = {
        "R": cyan / total,
        "SR": purple / total,
        "SSR": orange / total,
    }
    rarity, score = max(scores.items(), key=lambda item: item[1])
    second_score = sorted(scores.values())[-2]
    if score - second_score < 0.08 and scores["SR"] >= 0.065:
        rarity = "SR"
    frame_ratio = max(dark / total, white / total)
    if score < 0.065 or colored / total < 0.06 or frame_ratio < 0.10:
        return COLLECTION_NONE
    white_ratio = white / total
    dark_ratio = dark / total
    is_level_15 = dark_ratio > 0.17 or (white_ratio > 0 and dark_ratio / white_ratio > 0.45 and dark_ratio > 0.10)
    if rarity == "SR":
        return "SR15" if is_level_15 else "SR"
    if rarity == "SSR":
        return "SSR3" if is_level_15 else "SSR"
    return "R"


def _classify_collection_icon(icon_image: Image.Image) -> str:
    template_label = _classify_collection_icon_by_direct_template(icon_image)
    if template_label is not None:
        return template_label
    return _classify_collection_icon_by_color(icon_image)


def recognize_collection_level(card_image: Image.Image) -> str:
    icon_image = _crop_rel(card_image, COLLECTION_ICON_BOX)
    return _classify_collection_icon(icon_image)


def recognize_collection_slots(
    row_image: Image.Image,
    centers: tuple[float, ...],
    slot_count: int = 5,
    side: str = "attacker",
    team_index: int = 1,
    match_index: int | None = None,
    stage_name: str = STAGE_NAME,
    block_height: int | None = None,
    source_profile: str = "",
) -> list[str]:
    levels: list[str] = []
    x_offsets = COLLECTION_ROW_ICON_X_OFFSETS.get(side, COLLECTION_ROW_ICON_X_OFFSETS["attacker"])
    for slot in range(slot_count):
        x_offset = x_offsets[min(slot, len(x_offsets) - 1)]
        icon_center = centers[slot] - x_offset
        geometry = _collection_slot_geometry(side, team_index, slot + 1, icon_center)
        geometry, dy = _collection_precise_group64_geometry(
            geometry,
            side=side,
            match_index=match_index,
            stage_name=stage_name,
            block_height=block_height,
            source_profile=source_profile,
        )
        icon_image = _crop_rel(
            row_image,
            (
                max(0.0, geometry.x_center - geometry.x_half),
                max(0.0, geometry.y_center + dy - geometry.y_half),
                min(1.0, geometry.x_center + geometry.x_half),
                min(1.0, geometry.y_center + dy + geometry.y_half),
            ),
        )
        levels.append(_classify_collection_icon(icon_image))
    return levels


_LEVEL_TRANSLATION = str.maketrans(
    {
        "O": "0",
        "o": "0",
        "Q": "0",
        "I": "1",
        "l": "1",
        "|": "1",
        "S": "5",
        "s": "5",
        "B": "8",
    }
)


def _stat_level_observations_from_text(
    text: str,
    confidence: float = 0.0,
    weight: float = 1.0,
) -> list[_StatLevelObservation]:
    raw_text = str(text or "")
    normalized = raw_text.translate(_LEVEL_TRANSLATION)
    observations: list[_StatLevelObservation] = []

    for match in re.finditer(r"[Ll][Vv]\s*([0-9]{1,3})", normalized):
        value = int(match.group(1))
        if STAT_LEVEL_MIN <= value <= STAT_LEVEL_MAX:
            observations.append(
                _StatLevelObservation(value, max(0.0, min(1.0, float(confidence or 0.0))), True, raw_text, weight)
            )

    if observations:
        return observations

    digit_groups = re.findall(r"(?<!\d)(\d{1,3})(?!\d)", normalized)
    if len(digit_groups) != 1 or re.search(r"[\^/\\]", normalized):
        return []
    value = int(digit_groups[0])
    if STAT_LEVEL_MIN <= value <= STAT_LEVEL_MAX:
        observations.append(
            _StatLevelObservation(value, max(0.0, min(1.0, float(confidence or 0.0))), False, raw_text, weight)
        )
    return observations


def _choose_stat_level(observations: list[_StatLevelObservation]) -> int | None:
    if not observations:
        return None
    grouped: dict[int, list[_StatLevelObservation]] = {}
    for observation in observations:
        grouped.setdefault(observation.value, []).append(observation)

    def score(value: int) -> tuple[float, int, float]:
        items = grouped[value]
        from_lv_count = sum(1 for item in items if item.from_lv)
        confidence_sum = sum(item.confidence for item in items)
        weight_sum = sum(item.weight for item in items)
        return (weight_sum + confidence_sum * 0.75 + from_lv_count * 4.0, from_lv_count, max(item.confidence for item in items))

    return max(grouped, key=score)


def _stat_level_preprocess_variants(image: Image.Image) -> list[tuple[Image.Image, float]]:
    gray = ImageOps.grayscale(image.convert("RGB"))
    upscaled = image.resize((max(1, image.width * 5), max(1, image.height * 5)), Image.Resampling.LANCZOS)
    gray_upscaled = gray.resize((max(1, image.width * 5), max(1, image.height * 5)), Image.Resampling.LANCZOS)
    binary = gray.point(lambda px: 255 if px > 150 else 0).resize(
        (max(1, image.width * 5), max(1, image.height * 5)),
        Image.Resampling.LANCZOS,
    )
    inverted = ImageOps.invert(gray).resize((max(1, image.width * 5), max(1, image.height * 5)), Image.Resampling.LANCZOS)
    return [
        (image.convert("RGB"), 1.0),
        (upscaled.convert("RGB"), 2.0),
        (gray_upscaled.convert("RGB"), 1.2),
        (binary.convert("RGB"), 3.0),
        (inverted.convert("RGB"), 1.0),
    ]


def _recognize_stat_level_crop(
    image: Image.Image,
    ocr: ArenaOCRRecognizer,
    region_name: str,
) -> int | None:
    observations: list[_StatLevelObservation] = []
    for index, (variant, weight) in enumerate(_stat_level_preprocess_variants(image), start=1):
        items = ocr.recognize_region(prepare_for_ocr(variant), f"{region_name}_v{index}")
        for item in items:
            observations.extend(_stat_level_observations_from_text(item.text, item.confidence, weight=weight))
    return _choose_stat_level(observations)


def _stat_level_slot_bounds(centers: tuple[float, ...], index: int) -> tuple[float, float]:
    left = 0.0 if index == 0 else (centers[index - 1] + centers[index]) / 2
    right = 1.0 if index == len(centers) - 1 else (centers[index] + centers[index + 1]) / 2
    return max(0.0, left), min(1.0, right)


def recognize_stat_levels(
    side_image: Image.Image,
    side: str,
    ocr: ArenaOCRRecognizer,
) -> list[int | None]:
    centers = ATTACKER_STAT_LEVEL_CENTERS if side == "attacker" else DEFENDER_STAT_LEVEL_CENTERS
    stat_area_box = STAT_LEVEL_AREA
    stat_area = _crop_rel(side_image, stat_area_box)
    prepared = prepare_for_ocr(stat_area)
    items = ocr.recognize_region(prepared, f"{side}_stat_levels")
    slot_observations: list[list[_StatLevelObservation]] = [[] for _ in centers]
    width = max(1, prepared.width)
    for item in items:
        observations = _stat_level_observations_from_text(item.text, item.confidence)
        if not observations:
            continue
        xs = [point[0] for point in item.bbox]
        if not xs:
            continue
        x_ratio = (sum(xs) / len(xs)) / width
        slot = min(range(len(centers)), key=lambda index: abs(x_ratio - centers[index]))
        if abs(x_ratio - centers[slot]) > 0.10:
            continue
        slot_observations[slot].extend(observations)

    levels = [_choose_stat_level(observations) for observations in slot_observations]
    for index, value in enumerate(levels):
        has_lv_source = any(observation.from_lv for observation in slot_observations[index])
        if value is not None and has_lv_source and value >= STAT_LEVEL_RECHECK_BELOW:
            continue
        left, right = _stat_level_slot_bounds(centers, index)
        slot_box = (left, STAT_LEVEL_SLOT_Y0, right, STAT_LEVEL_SLOT_Y1)
        slot_image = _crop_rel(side_image, slot_box)
        slot_value = _recognize_stat_level_crop(slot_image, ocr, f"{side}_stat_level_{index + 1}")
        if slot_value is not None:
            levels[index] = slot_value
    return levels


_POWER_TRANSLATION = str.maketrans(
    {
        "O": "0",
        "o": "0",
        "Q": "0",
        "D": "0",
        "I": "1",
        "l": "1",
        "|": "1",
        "!": "1",
        "Z": "2",
        "z": "2",
        "A": "4",
        "a": "4",
        "S": "5",
        "s": "5",
        "G": "6",
        "B": "8",
    }
)


def _normalize_power_text(text: str) -> str:
    normalized = (text or "").translate(_POWER_TRANSLATION)
    return re.sub(r"(?<=\d)[,\s]+(?=\d{3}\b)", "", normalized)


def _extract_power_observations_clean(text: str, confidence: float = 0.0) -> list[_PowerObservation]:
    normalized = _normalize_power_text(text)
    observations: list[_PowerObservation] = []
    marker_pattern = r"[xX*※]"
    for match in re.finditer(r"(?<!\d)(\d{4,6})(?!\d)", normalized):
        value = int(match.group(1))
        if not MIN_CARD_POWER <= value <= MAX_CARD_POWER:
            continue
        prefix = re.sub(r"\s+", "", normalized[max(0, match.start() - 4) : match.start()])
        suffix = re.sub(r"\s+", "", normalized[match.end() : match.end() + 4])
        observations.append(
            _PowerObservation(
                value=value,
                confidence=max(0.0, min(1.0, float(confidence or 0.0))),
                anchored=bool(re.search(marker_pattern + r"$", prefix)),
                trailing_marker=bool(re.search(r"^" + marker_pattern, suffix)),
                text=str(text or ""),
            )
        )
    return observations


def _extract_card_power_clean(text: str) -> int | None:
    observations = _extract_power_observations_clean(text)
    if not observations:
        return None
    return max((observation.value for observation in observations), key=lambda value: (len(str(value)), value))


def _extract_card_power(text: str) -> int | None:
    return _extract_card_power_clean(text)
    normalized = (text or "").translate(_POWER_TRANSLATION)
    normalized = re.sub(r"(?<=\d)[,\s，.。](?=\d{3}\b)", "", normalized)
    normalized = re.sub(r"[^\d]+", " ", normalized)
    matches = re.findall(r"(?<!\d)(\d{4,6})(?!\d)", normalized)
    if not matches:
        return None
    values = [int(match) for match in matches]
    values = [value for value in values if MIN_CARD_POWER <= value <= MAX_CARD_POWER]
    if not values:
        return None
    return max(values, key=lambda value: (len(str(value)), value))


def _extract_power_observations(text: str, confidence: float = 0.0) -> list[_PowerObservation]:
    return _extract_power_observations_clean(text, confidence)
    normalized = (text or "").translate(_POWER_TRANSLATION)
    normalized = re.sub(r"(?<=\d)[,\s锛?銆俔(?=\d{3}\b)", "", normalized)
    observations: list[_PowerObservation] = []
    marker_pattern = r"[xX脳×*]"
    for match in re.finditer(r"(?<!\d)(\d{4,6})(?!\d)", normalized):
        value = int(match.group(1))
        if not MIN_CARD_POWER <= value <= MAX_CARD_POWER:
            continue
        prefix = re.sub(r"\s+", "", normalized[max(0, match.start() - 4) : match.start()])
        suffix = re.sub(r"\s+", "", normalized[match.end() : match.end() + 4])
        observations.append(
            _PowerObservation(
                value=value,
                confidence=max(0.0, min(1.0, float(confidence or 0.0))),
                anchored=bool(re.search(marker_pattern + r"$", prefix)),
                trailing_marker=bool(re.search(r"^" + marker_pattern, suffix)),
                text=str(text or ""),
            )
        )
    return observations


def _match_power_slot_readings(
    items: list[OCRItem],
    image_width: int,
    image_height: int,
    centers: tuple[float, ...],
    slot_count: int = 5,
) -> list[_PowerSlotReading]:
    readings = [_PowerSlotReading() for _ in range(slot_count)]
    slot_scores: list[float] = [-1.0] * slot_count
    width = max(1, image_width)
    height = max(1, image_height)
    centers = centers[:slot_count]
    for item in items:
        observations = _extract_power_observations(item.text, item.confidence)
        if not observations:
            continue
        xs = [point[0] for point in item.bbox]
        ys = [point[1] for point in item.bbox]
        if not xs or not ys:
            continue
        x_ratio = (sum(xs) / len(xs)) / width
        y_ratio = (sum(ys) / len(ys)) / height
        if not 0.70 <= y_ratio <= 0.90:
            continue
        slot = min(range(slot_count), key=lambda index: abs(x_ratio - centers[index]))
        distance = abs(x_ratio - centers[slot])
        if distance > 0.09:
            continue
        value, support = _choose_power_observation(
            [
                _PowerObservation(
                    value=observation.value,
                    confidence=observation.confidence,
                    anchored=observation.anchored,
                    trailing_marker=observation.trailing_marker,
                    distance=distance,
                    text=observation.text,
                )
                for observation in observations
            ]
        )
        if value is None:
            continue
        selected = next((observation for observation in observations if observation.value == value), observations[0])
        score = support + max(0.0, min(1.0, item.confidence)) - distance
        if score > slot_scores[slot]:
            readings[slot] = _PowerSlotReading(
                value=value,
                confidence=max(0.0, min(1.0, item.confidence)),
                text=str(item.text or ""),
                distance=distance,
                anchored=selected.anchored,
                trailing_marker=selected.trailing_marker,
            )
            slot_scores[slot] = score
    return readings


def _power_ocr_mode() -> str:
    mode = os.environ.get("NIKKE_POWER_OCR_MODE", "adaptive").strip().lower()
    if mode in {"full", "accurate", "always"}:
        return "accurate"
    if mode in {"off", "row", "fast"}:
        return "fast"
    return "adaptive"


def _power_verify_existing() -> bool:
    value = os.environ.get("NIKKE_POWER_VERIFY_EXISTING", "0").strip().lower()
    return value not in {"0", "false", "no", "off", "fast"}


def _power_preprocess_variants(image: Image.Image, max_variants: int | None = None) -> list[Image.Image]:
    variants: list[Image.Image] = []

    def add_variant(variant: Image.Image) -> bool:
        variants.append(variant)
        return max_variants is not None and len(variants) >= max(1, max_variants)

    base = image.convert("RGB")
    if add_variant(base):
        return variants

    gray = ImageOps.grayscale(base)
    if add_variant(gray.convert("RGB")):
        return variants

    pad_x = max(2, int(round(gray.width * 0.08)))
    padded = ImageOps.expand(gray, border=(pad_x, 2, 2, 2), fill=0)
    upscaled = gray.resize((max(1, gray.width * 4), max(1, gray.height * 4)), Image.Resampling.LANCZOS)
    if add_variant(upscaled.convert("RGB")):
        return variants

    padded_upscaled = padded.resize((max(1, padded.width * 4), max(1, padded.height * 4)), Image.Resampling.LANCZOS)
    if add_variant(padded_upscaled.convert("RGB")):
        return variants
    if add_variant(ImageOps.autocontrast(upscaled).convert("RGB")):
        return variants
    if add_variant(ImageOps.autocontrast(padded_upscaled).convert("RGB")):
        return variants

    for contrast in (1.45, 1.85, 2.35):
        if add_variant(ImageEnhance.Contrast(upscaled).enhance(contrast).convert("RGB")):
            return variants
        if add_variant(ImageEnhance.Contrast(padded_upscaled).enhance(contrast).convert("RGB")):
            return variants
    sharpened = ImageEnhance.Sharpness(ImageOps.autocontrast(upscaled)).enhance(2.0)
    if add_variant(sharpened.convert("RGB")):
        return variants
    for threshold in (105, 125, 145, 165):
        if add_variant(upscaled.point(lambda px, t=threshold: 255 if px > t else 0).convert("RGB")):
            return variants
        if add_variant(padded_upscaled.point(lambda px, t=threshold: 255 if px > t else 0).convert("RGB")):
            return variants
    variants = variants[:14]
    return variants


def _choose_power_candidate(candidates: list[int]) -> int | None:
    plausible = [value for value in candidates if MIN_CARD_POWER <= value <= MAX_CARD_POWER]
    if not plausible:
        return None
    confident = [value for value in plausible if _is_confident_power_candidate(value)]
    if confident:
        plausible = confident
    plausible_strings = sorted({str(value) for value in plausible}, key=lambda text: (-len(text), text))
    for longer in plausible_strings:
        if len(longer) < 5:
            continue
        for shorter in plausible_strings:
            if len(shorter) + 1 == len(longer) and longer.endswith(shorter):
                return int(longer)
    counts = Counter(plausible)
    best_count = max(counts.values())
    winners = [value for value, count in counts.items() if count == best_count]
    if len(winners) == 1:
        return winners[0]
    ordered = sorted(plausible)
    median = ordered[len(ordered) // 2]
    return min(winners, key=lambda value: (abs(value - median), -len(str(value)), value))


def _choose_power_observation(observations: list[_PowerObservation]) -> tuple[int | None, float]:
    plausible = [item for item in observations if MIN_CARD_POWER <= item.value <= MAX_CARD_POWER]
    if not plausible:
        return None, 0.0
    confident = [item for item in plausible if _is_confident_power_candidate(item.value)]
    if confident:
        plausible = confident

    grouped: dict[int, list[_PowerObservation]] = {}
    for item in plausible:
        grouped.setdefault(item.value, []).append(item)

    def group_score(value: int, items: list[_PowerObservation]) -> tuple[float, int, int, float, int]:
        count = len(items)
        confidence_sum = sum(max(0.0, min(1.0, item.confidence)) for item in items)
        anchored = [item for item in items if item.anchored]
        trailing_count = sum(1 for item in items if item.trailing_marker)
        max_confidence = max((item.confidence for item in items), default=0.0)
        avg_distance = sum(item.distance for item in items) / max(1, count)
        score = count + confidence_sum * 0.55 - trailing_count * 0.35 - avg_distance * 3.0
        if len(str(value)) >= 5:
            score += 1.5
        if anchored:
            max_anchor_confidence = max(item.confidence for item in anchored)
            score += len(anchored) * 4.0
            if max_anchor_confidence >= 0.85:
                score += 8.0
        return (score, len(anchored), count, max_confidence, len(str(value)))

    best_value = max(grouped, key=lambda value: group_score(value, grouped[value]))
    return best_value, group_score(best_value, grouped[best_value])[0]


def _is_confident_power_candidate(value: int | None) -> bool:
    if value is None:
        return False
    return CONFIDENT_MIN_CARD_POWER <= value <= MAX_CARD_POWER and len(str(value)) >= 5


def _is_high_risk_power(value: int | None) -> bool:
    return value is not None and HIGH_RISK_CARD_POWER <= value <= MAX_CARD_POWER


def _is_mid_risk_power(value: int | None) -> bool:
    return value is not None and SUSPICIOUS_CARD_POWER <= value < HIGH_RISK_CARD_POWER


def _is_power_slot_suspicious(value: int | None, row_values: list[int | None]) -> bool:
    if value is None:
        return True
    if value < CONFIDENT_MIN_CARD_POWER:
        return True
    if _is_mid_risk_power(value):
        return True
    if _is_high_risk_power(value):
        return True

    filled = [int(item) for item in row_values if item is not None and CONFIDENT_MIN_CARD_POWER <= item <= MAX_CARD_POWER]
    if len(filled) < 3:
        return False
    ordered = sorted(filled)
    median = ordered[len(ordered) // 2]
    if median >= 100_000 and value < 50_000 and value < median * 0.45:
        return True
    if median <= 220_000 and value > max(300_000, median * 2.5):
        return True
    return False


def _is_power_slot_reading_uncertain(reading: _PowerSlotReading, row_values: list[int | None]) -> bool:
    value = reading.value
    if _is_power_slot_suspicious(value, row_values):
        return True
    if value is None or not 10_000 <= value < 100_000:
        return False
    if reading.anchored and not reading.trailing_marker and reading.confidence >= POWER_ANCHORED_CONFIDENCE_FLOOR:
        return False
    if reading.trailing_marker or reading.confidence < 0.97:
        return True
    high_values = [item for item in row_values if item is not None and item >= 100_000]
    return len(high_values) >= 2 and not reading.anchored


def _is_visually_empty_power_row(row_image: Image.Image) -> bool:
    rgb = np.asarray(row_image.convert("RGB").resize((160, 48), Image.Resampling.BILINEAR), dtype=np.uint8)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    stddev = float(gray.std())
    dark_ratio = float(np.mean(gray < 70))
    bright_ratio = float(np.mean(gray > 230))
    edges = cv2.Canny(gray, 60, 140)
    edge_ratio = float(np.mean(edges > 0))
    # True blank/near-blank rows are low texture and mostly light background.
    return stddev < 18.0 and edge_ratio < 0.035 and dark_ratio < 0.03 and bright_ratio > 0.52


def _resolve_power_slot_value(
    current: int | None,
    refined: int | None,
    row_values: list[int | None],
    refined_support: float = 0.0,
    allow_strong_replace: bool = False,
) -> int | None:
    if _is_high_risk_power(current):
        if refined == current:
            return current
        if refined is not None and _is_confident_power_candidate(refined) and not _is_high_risk_power(refined):
            return refined
        return None
    if refined is None:
        return current
    if current is None:
        return refined
    if refined == current:
        return current
    if _is_mid_risk_power(current):
        if _is_confident_power_candidate(refined) and refined_support >= STRONG_POWER_RECHECK_SUPPORT:
            return refined
        return current
    if allow_strong_replace and refined_support >= STRONG_POWER_RECHECK_SUPPORT and _is_confident_power_candidate(refined):
        return refined
    if not _is_power_slot_suspicious(current, row_values):
        return current
    if _is_confident_power_candidate(refined):
        return refined
    return current


def _gate_collection_slots_by_character_names(
    names: list[str],
    collection_slots: list[str],
    matcher: NikkeNameMatcher,
) -> list[str]:
    if not hasattr(matcher, "has_collection_item"):
        return collection_slots

    gated = list(collection_slots)
    for index, name in enumerate(names[: len(gated)]):
        if not name or gated[index] not in COLLECTION_TREASURE_LABELS:
            continue
        try:
            if not matcher.has_collection_item(name):
                gated[index] = COLLECTION_NONE
        except Exception:
            continue
    return gated


def _recognize_power_from_crop(
    power_image: Image.Image,
    ocr: ArenaOCRRecognizer,
    region_name: str,
    max_variants: int | None = None,
    early_stop: bool = False,
) -> int | None:
    value, _support = _recognize_power_from_crop_with_support(
        power_image,
        ocr,
        region_name,
        max_variants=max_variants,
        early_stop=early_stop,
    )
    return value


def _recognize_power_from_crop_with_support(
    power_image: Image.Image,
    ocr: ArenaOCRRecognizer,
    region_name: str,
    max_variants: int | None = None,
    early_stop: bool = False,
    crop_left: float = 0.0,
    crop_right: float = 1.0,
    target_center: float | None = None,
    max_distance: float = 0.09,
) -> tuple[int | None, float]:
    observations: list[_PowerObservation] = []
    early_observations: list[_PowerObservation] = []
    crop_width = max(0.0001, crop_right - crop_left)
    for index, variant in enumerate(_power_preprocess_variants(power_image, max_variants=max_variants), start=1):
        prepared = prepare_for_ocr(variant)
        power_items = ocr.recognize_region(prepared, f"{region_name}_v{index}")
        for item in power_items:
            item_observations = _extract_power_observations(item.text, item.confidence)
            if not item_observations:
                continue
            xs = [point[0] for point in item.bbox]
            if not xs:
                continue
            x_ratio = (sum(xs) / len(xs)) / max(1, prepared.width)
            global_x = crop_left + x_ratio * crop_width
            distance = 0.0 if target_center is None else abs(global_x - target_center)
            if target_center is not None and distance > max_distance:
                continue
            for observation in item_observations:
                observations.append(
                    _PowerObservation(
                        value=observation.value,
                        confidence=observation.confidence,
                        anchored=observation.anchored,
                        trailing_marker=observation.trailing_marker,
                        distance=distance,
                        text=observation.text,
                    )
                )
                if index <= 2:
                    early_observations.append(observations[-1])
        if early_stop and index == 2:
            early_groups: dict[int, list[_PowerObservation]] = {}
            for observation in early_observations:
                if not _is_confident_power_candidate(observation.value) or _is_high_risk_power(observation.value):
                    continue
                early_groups.setdefault(observation.value, []).append(observation)
            for value, items in early_groups.items():
                if len(items) >= 2 and max(item.confidence for item in items) >= 0.98:
                    return value, STRONG_POWER_RECHECK_SUPPORT
        chosen, support = _choose_power_observation(observations)
        if early_stop and _is_confident_power_candidate(chosen) and support >= STRONG_POWER_RECHECK_SUPPORT:
            return chosen, support
    return _choose_power_observation(observations)


def _recognize_power_from_slot(
    row_image: Image.Image,
    center: float,
    ocr: ArenaOCRRecognizer,
    region_name: str,
    max_variants: int | None = None,
    max_boxes: int | None = None,
    early_stop: bool = False,
) -> int | None:
    value, _support = _recognize_power_from_slot_with_support(
        row_image,
        center,
        ocr,
        region_name,
        max_variants=max_variants,
        max_boxes=max_boxes,
        early_stop=early_stop,
    )
    return value


def _recognize_power_from_slot_with_support(
    row_image: Image.Image,
    center: float,
    ocr: ArenaOCRRecognizer,
    region_name: str,
    max_variants: int | None = None,
    max_boxes: int | None = None,
    early_stop: bool = False,
) -> tuple[int | None, float]:
    observations: list[_PowerObservation] = []
    tight_boxes = (
        (0.080, 0.78, 0.080, 0.94),
        (0.080, 0.80, 0.080, 0.94),
        (0.090, 0.78, 0.090, 0.94),
        (0.090, 0.80, 0.090, 0.94),
        (0.100, 0.80, 0.100, 0.94),
        (0.120, 0.72, 0.120, 0.94),
    )
    wide_boxes = (
        (0.120, 0.76, 0.120, 0.995),
        (0.095, 0.70, 0.085, 0.995),
        (0.115, 0.66, 0.105, 0.995),
        (0.135, 0.60, 0.125, 0.995),
        (0.155, 0.54, 0.145, 0.995),
        (0.180, 0.50, 0.165, 0.995),
    )

    def scan_boxes(
        active_boxes: tuple[tuple[float, float, float, float], ...],
        suffix: str,
        target: list[_PowerObservation],
    ) -> tuple[int | None, float]:
        start_index = len(target) + 1
        local: list[_PowerObservation] = []
        for index, (left, top, right, bottom) in enumerate(active_boxes, start=start_index):
            crop_left = max(0.0, center - left)
            crop_right = min(1.0, center + right)
            power_image = _crop_rel(
                row_image,
                (crop_left, top, crop_right, bottom),
            )
            value, support = _recognize_power_from_crop_with_support(
                power_image,
                ocr,
                f"{region_name}_{suffix}{index}",
                max_variants=max_variants,
                early_stop=early_stop,
                crop_left=crop_left,
                crop_right=crop_right,
                target_center=center,
                max_distance=0.085,
            )
            if value is not None:
                observation = _PowerObservation(
                    value=value,
                    confidence=min(1.0, support / STRONG_POWER_RECHECK_SUPPORT),
                    anchored=support >= STRONG_POWER_RECHECK_SUPPORT,
                    trailing_marker=False,
                    text=str(value),
                )
                local.append(observation)
                target.append(observation)
            chosen, combined_support = _choose_power_observation(local)
            if early_stop and _is_confident_power_candidate(chosen) and combined_support >= STRONG_POWER_RECHECK_SUPPORT:
                return chosen, combined_support
        return _choose_power_observation(local)

    tight_value, tight_support = scan_boxes(tight_boxes, "tight", observations)
    if _is_confident_power_candidate(tight_value) and tight_support >= POWER_TIGHT_RECHECK_SUPPORT:
        return tight_value, tight_support

    active_wide_boxes = wide_boxes[: max(1, max_boxes)] if max_boxes is not None else wide_boxes
    scan_boxes(active_wide_boxes, "box", observations)
    return _choose_power_observation(observations)


def recognize_team_rows(
    area: Image.Image,
    ocr: ArenaOCRRecognizer,
    matcher: NikkeNameMatcher,
    side: str,
    include_power: bool = True,
    include_collection: bool = True,
    match_index: int | None = None,
    stage_name: str = STAGE_NAME,
    block_height: int | None = None,
    source_profile: str = "",
) -> tuple[list[list[str]], list[list[int | None]], list[list[str]]]:
    teams: list[list[str]] = []
    powers: list[list[int | None]] = []
    collections: list[list[str]] = []
    centers = ATTACKER_CARD_SLOT_CENTERS if side == "attacker" else DEFENDER_CARD_SLOT_CENTERS
    power_centers = ATTACKER_POWER_SLOT_CENTERS if side == "attacker" else DEFENDER_POWER_SLOT_CENTERS
    power_mode = _power_ocr_mode()
    name_profile = _name_profile_from_block_height(block_height)

    # The first playable card row starts below the sync-level strip. The bottom
    # team stats row is intentionally excluded to avoid matching research names.
    start = 0.275
    end = 0.925
    row_h = (end - start) / 5
    for row in range(5):
        y0 = start + row * row_h
        y1 = start + (row + 1) * row_h
        default_row_box = (0.01, y0, 0.99, y1)
        row_image = _crop_rel(area, default_row_box)
        name_slot_boxes: list[tuple[float, float, float, float] | None] = [None] * 5
        name_label_boxes: list[tuple[float, float, float, float] | None] = [None] * 5
        row_centers = centers
        row_power_centers = power_centers
        prepared = prepare_for_ocr(row_image)
        items = ocr.recognize_region(prepared, f"team_row_{row + 1}")
        row_ocr_empty = len(items) == 0
        slots = _match_character_slots(items, matcher, prepared.width, row_centers, name_profile=name_profile)
        collection_slots = (
            recognize_collection_slots(
                row_image,
                centers,
                side=side,
                team_index=row + 1,
                match_index=match_index,
                stage_name=stage_name,
                block_height=block_height,
                source_profile=source_profile,
            )
            if include_collection
            else [COLLECTION_NONE] * 5
        )
        if include_power:
            power_readings = _match_power_slot_readings(items, prepared.width, prepared.height, row_power_centers)
            power_slots = [reading.value for reading in power_readings]
        else:
            power_readings = [_PowerSlotReading() for _ in range(5)]
            power_slots = [None] * 5

        # Retry only blank slots with a tighter single-card crop. This improves
        # small/long labels without multiplying OCR work for every card.
        for slot in range(5):
            if slots[slot]:
                continue
            center = row_centers[slot]
            fallback_box = (max(0.0, center - 0.085), 0.0, min(1.0, center + 0.085), 1.0)
            card_box = name_slot_boxes[slot] or fallback_box
            card_image = _crop_rel(row_image, card_box)
            prepared_card = prepare_for_ocr(card_image)
            card_items = ocr.recognize_region(prepared_card, f"team_row_{row + 1}_slot_{slot + 1}")
            card_name, _, _ = _best_positioned_character_match(
                card_items,
                matcher,
                prepared_card,
                name_profile=name_profile,
            )
            if not card_name and name_profile == NAME_PROFILE_FHD:
                label_image = (
                    _crop_rel(row_image, name_label_boxes[slot])
                    if name_label_boxes[slot] is not None
                    else _crop_rel(card_image, (0.0, 0.47, 1.0, 1.0))
                )
                prepared_label = prepare_for_ocr(label_image)
                label_items = ocr.recognize_region(
                    prepared_label,
                    f"team_row_{row + 1}_slot_{slot + 1}_fhd_label",
                )
                card_name, _, _ = _best_positioned_character_match(
                    label_items,
                    matcher,
                    prepared_label,
                    name_profile=name_profile,
                )
            if card_name:
                slots[slot] = card_name

        for slot in range(5):
            if not slots[slot] or not _has_special_variants(slots[slot], matcher):
                continue
            center = row_centers[slot]
            card_image = _crop_rel(
                row_image,
                name_slot_boxes[slot] or (max(0.0, center - 0.095), 0.0, min(1.0, center + 0.095), 1.0),
            )
            label_image = _crop_rel(row_image, name_label_boxes[slot]) if name_label_boxes[slot] is not None else None
            slots[slot] = _promote_special_card_name(
                slots[slot],
                card_image,
                ocr,
                matcher,
                f"team_row_{row + 1}_slot_{slot + 1}",
                name_profile=name_profile,
                label_image=label_image,
            )

        if include_collection:
            collection_slots = _gate_collection_slots_by_character_names(slots, collection_slots, matcher)

        # Row-level OCR is the default path. Tight per-slot OCR is reserved for
        # missing/suspicious slots in adaptive mode; accurate mode keeps the old
        # exhaustive verification behavior for comparison runs.
        verify_existing_power = _power_verify_existing()
        if include_power:
            for slot in range(5):
                if power_mode == "fast":
                    continue
                if power_mode == "adaptive":
                    reading = power_readings[slot]
                    should_refine = (
                        verify_existing_power
                        or _is_power_slot_suspicious(power_slots[slot], power_slots)
                        or _is_power_slot_reading_uncertain(reading, power_slots)
                    )
                    if not should_refine:
                        continue
                    if row_ocr_empty and all(value is None for value in power_slots) and _is_visually_empty_power_row(row_image):
                        max_variants = 2
                        max_boxes = 1
                        early_stop = True
                    else:
                        max_variants = 10
                        max_boxes = 4
                        early_stop = False
                else:
                    max_variants = None
                    max_boxes = None
                    early_stop = False
                center = row_power_centers[slot]
                precise_power, precise_support = _recognize_power_from_slot_with_support(
                    row_image,
                    center,
                    ocr,
                    f"team_power_{row + 1}_slot_{slot + 1}",
                    max_variants=max_variants,
                    max_boxes=max_boxes,
                    early_stop=early_stop,
                )
                allow_strong_replace = power_mode == "adaptive" and _is_power_slot_reading_uncertain(
                    power_readings[slot],
                    power_slots,
                )
                power_slots[slot] = _resolve_power_slot_value(
                    power_slots[slot],
                    precise_power,
                    power_slots,
                    refined_support=precise_support,
                    allow_strong_replace=allow_strong_replace,
                )
        teams.append(slots)
        powers.append(power_slots)
        collections.append(collection_slots)
    return teams, powers, collections


def _match_detail_team_slots(
    items: list[OCRItem],
    matcher: NikkeNameMatcher,
    image_width: int,
    image_height: int,
    name_profile: str = NAME_PROFILE_DEFAULT,
    slot_boxes: tuple[list[tuple[float, float, float, float] | None], list[tuple[float, float, float, float] | None]]
    | None = None,
) -> tuple[list[str], list[str], list[float], list[float]]:
    teams = [[""] * 5, [""] * 5]
    scores = [[-1.0] * 5, [-1.0] * 5]
    width = max(1, image_width)
    height = max(1, image_height)
    for item in items:
        text = _clean_text(item.text)
        if _is_noise_token(text) or not re.search(r"[\u4e00-\u9fffA-Za-z]", text):
            continue
        name, match_score = _best_character_match(text, matcher, name_profile=name_profile)
        if not name or name == "unknown" or match_score < matcher.threshold:
            continue
        xs = [point[0] for point in item.bbox]
        ys = [point[1] for point in item.bbox]
        if not xs or not ys:
            continue
        x_ratio = (sum(xs) / len(xs)) / width
        y_ratio = (sum(ys) / len(ys)) / height
        if slot_boxes:
            side = -1
            slot = -1
            x = x_ratio * width
            y = y_ratio * height
            for side_index, boxes in enumerate(slot_boxes):
                for slot_index, box in enumerate(boxes):
                    if box is None:
                        continue
                    x0, y0, x1, y1 = box
                    if x0 <= x <= x1 and y0 <= y <= y1:
                        side = side_index
                        slot = slot_index
                        break
                if side >= 0:
                    break
            if side < 0 or slot < 0:
                continue
        else:
            if y_ratio < 0.085 or 0.46 <= x_ratio <= 0.54:
                continue
            slot = min(range(5), key=lambda index: abs(y_ratio - DETAIL_SLOT_CENTERS[index]))
            if abs(y_ratio - DETAIL_SLOT_CENTERS[slot]) > 0.055:
                continue
            side = 0 if x_ratio < 0.5 else 1
        combined_score = match_score + max(0.0, min(1.0, item.confidence)) * 2.0
        if combined_score > scores[side][slot]:
            teams[side][slot] = name
            scores[side][slot] = combined_score
    return teams[0], teams[1], scores[0], scores[1]


def _detail_round_crop(
    center_image: Image.Image,
    row: int,
) -> tuple[Image.Image, tuple[float, float, float, float]]:
    center_size = tuple(float(value) for value in center_image.size)
    rel_box = (0.0, row / 5, 1.0, (row + 1) / 5)
    return _crop_rel(center_image, rel_box), _box_rel_to_abs((0.0, 0.0), center_size, rel_box)


def recognize_detail_team_rows(
    center_image: Image.Image,
    ocr: ArenaOCRRecognizer,
    matcher: NikkeNameMatcher,
    block_height: int | None = None,
) -> tuple[list[list[str]], list[list[str]], list[list[float]], list[list[float]], list[list[OCRItem]]]:
    attacker_rows: list[list[str]] = []
    defender_rows: list[list[str]] = []
    attacker_scores: list[list[float]] = []
    defender_scores: list[list[float]] = []
    round_items: list[list[OCRItem]] = []
    name_profile = _name_profile_from_block_height(block_height)

    def merge_recheck(
        current: list[str],
        scores: list[float],
        extra: list[str],
        extra_scores: list[float],
    ) -> None:
        for index, extra_name in enumerate(extra):
            if not extra_name or extra_scores[index] < matcher.threshold:
                continue
            current_name = current[index]
            if not current_name:
                current[index] = extra_name
                scores[index] = extra_scores[index]
                continue
            current_norm = matcher.normalize_name(current_name)
            extra_norm = matcher.normalize_name(extra_name)
            if (
                current_norm.split(CANONICAL_COLON, 1)[0] == extra_norm.split(CANONICAL_COLON, 1)[0]
                and len(extra_norm) > len(current_norm)
            ):
                current[index] = extra_name
                scores[index] = extra_scores[index]

    for row in range(5):
        round_image, _round_abs = _detail_round_crop(center_image, row)
        prepared = prepare_for_ocr(round_image)
        items = ocr.recognize_region(prepared, f"detail_round_{row + 1}")
        attacker, defender, attacker_score, defender_score = _match_detail_team_slots(
            items,
            matcher,
            prepared.width,
            prepared.height,
            name_profile=name_profile,
        )
        if name_profile == NAME_PROFILE_FHD and ("" in attacker or "" in defender):
            upscaled = round_image.resize((round_image.width * 3, round_image.height * 3), Image.Resampling.LANCZOS)
            extra_items = ocr.recognize_region(upscaled, f"detail_round_{row + 1}_fhd_up3")
            extra_attacker, extra_defender, extra_attacker_score, extra_defender_score = _match_detail_team_slots(
                extra_items,
                matcher,
                upscaled.width,
                upscaled.height,
                name_profile=name_profile,
            )
            merge_recheck(attacker, attacker_score, extra_attacker, extra_attacker_score)
            merge_recheck(defender, defender_score, extra_defender, extra_defender_score)
        attacker_rows.append(attacker)
        defender_rows.append(defender)
        attacker_scores.append(attacker_score)
        defender_scores.append(defender_score)
        round_items.append(items)
    return attacker_rows, defender_rows, attacker_scores, defender_scores, round_items


def _merge_team_sources(
    card_rows: list[list[str]],
    detail_rows: list[list[str]],
    detail_scores: list[list[float]],
    matcher: NikkeNameMatcher,
) -> list[list[str]]:
    def same_base(card_norm: str, detail_norm: str) -> bool:
        if not card_norm or not detail_norm:
            return False
        return card_norm.split(CANONICAL_COLON, 1)[0] == detail_norm.split(CANONICAL_COLON, 1)[0]

    def should_trust_detail_name(card_norm: str, detail_norm: str, detail_score: float) -> bool:
        if detail_score < matcher.threshold or not same_base(card_norm, detail_norm):
            return False
        return card_norm != detail_norm

    merged: list[list[str]] = []
    for row in range(5):
        merged_row: list[str] = []
        for slot in range(5):
            card_name = card_rows[row][slot] if row < len(card_rows) and slot < len(card_rows[row]) else ""
            detail_name = detail_rows[row][slot] if row < len(detail_rows) and slot < len(detail_rows[row]) else ""
            detail_score = detail_scores[row][slot] if row < len(detail_scores) and slot < len(detail_scores[row]) else -1.0
            if not detail_name:
                merged_row.append(card_name)
                continue
            if not card_name or card_name == detail_name:
                merged_row.append(detail_name)
                continue
            card_norm = matcher.normalize_name(card_name)
            detail_norm = matcher.normalize_name(detail_name)
            if should_trust_detail_name(card_norm, detail_norm, detail_score):
                merged_row.append(detail_name)
            elif card_norm in detail_norm and len(detail_norm) > len(card_norm):
                merged_row.append(detail_name)
            elif detail_norm in card_norm and len(card_norm) > len(detail_norm):
                merged_row.append(card_name)
            else:
                merged_row.append(card_name)
        merged.append(merged_row)
    return merged


def _slice_center_round(center_image: Image.Image, row: int, rows: int = 5) -> Image.Image:
    h = center_image.height
    y0 = int(h * row / rows)
    y1 = int(h * (row + 1) / rows)
    return center_image.crop((0, y0, center_image.width, y1))


def _infer_result_mode(source_name: str) -> str:
    text = str(source_name or "").lower()
    if "简" in text or "simple" in text:
        return RESULT_MODE_SIMPLE
    if "详" in text or "detailed" in text:
        return RESULT_MODE_DETAILED
    return RESULT_MODE_AUTO


def _ocr_coordinate_size(items: list[OCRItem], image: Image.Image) -> tuple[float, float]:
    max_x = 0.0
    max_y = 0.0
    for item in items:
        for x, y in item.bbox:
            max_x = max(max_x, float(x))
            max_y = max(max_y, float(y))
    width = float(image.width)
    height = float(image.height)
    if max_x > width * 1.15:
        width *= 2.0
    if max_y > height * 1.15:
        height *= 2.0
    return max(1.0, width), max(1.0, height)


def _ocr_item_center_ratio(item: OCRItem, image: Image.Image, coord_size: tuple[float, float]) -> tuple[float, float]:
    xs = [point[0] for point in item.bbox]
    ys = [point[1] for point in item.bbox]
    if not xs or not ys:
        return 0.0, 0.0
    return (sum(xs) / len(xs)) / coord_size[0], (sum(ys) / len(ys)) / coord_size[1]


def _detail_slot_bounds(index: int) -> tuple[float, float]:
    center = DETAIL_SLOT_CENTERS[index]
    top = 0.0 if index == 0 else (DETAIL_SLOT_CENTERS[index - 1] + center) / 2
    bottom = 1.0 if index == len(DETAIL_SLOT_CENTERS) - 1 else (center + DETAIL_SLOT_CENTERS[index + 1]) / 2
    return max(0.0, top), min(1.0, bottom)


def _detail_slot_from_y_ratio(y_ratio: float) -> int | None:
    for index in range(len(DETAIL_SLOT_CENTERS)):
        top, bottom = _detail_slot_bounds(index)
        if top <= y_ratio <= bottom:
            return index
    return None


def _is_defeat_sticker_visual(crop: Image.Image) -> bool:
    if crop.width < 4 or crop.height < 4:
        return False
    rgb = np.asarray(crop.convert("RGB").resize((96, 120), Image.Resampling.LANCZOS), dtype=np.uint8)
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    value = hsv[:, :, 2].astype(np.float32) / 255.0
    dark = value < 0.30
    dark_ratio = float(dark.mean())
    center_dark_ratio = float(dark[int(120 * 0.20) : int(120 * 0.85), :].mean())
    return (
        dark_ratio >= DETAILED_DEFEAT_VISUAL_DARK_THRESHOLD
        or center_dark_ratio >= DETAILED_DEFEAT_VISUAL_CENTER_DARK_THRESHOLD
    )


def _detect_detail_visual_defeat_slots(
    round_image: Image.Image,
    side: str,
    defeat_boxes: list[tuple[float, float, float, float] | None] | None = None,
) -> list[bool]:
    if defeat_boxes:
        flags: list[bool] = []
        for box in defeat_boxes:
            if box is None:
                flags.append(False)
                continue
            x0 = max(0, min(round_image.width, int(round(box[0]))))
            y0 = max(0, min(round_image.height, int(round(box[1]))))
            x1 = max(0, min(round_image.width, int(round(box[2]))))
            y1 = max(0, min(round_image.height, int(round(box[3]))))
            if x1 <= x0 or y1 <= y0:
                flags.append(False)
                continue
            flags.append(_is_defeat_sticker_visual(round_image.crop((x0, y0, x1, y1))))
        return flags

    x0_ratio, x1_ratio = DETAILED_RESULT_LEFT_PORTRAIT_X if side == "attacker" else DETAILED_RESULT_RIGHT_PORTRAIT_X
    flags: list[bool] = []
    for index in range(len(DETAIL_SLOT_CENTERS)):
        top, bottom = _detail_slot_bounds(index)
        height = bottom - top
        crop_top = top + height * 0.06
        crop_bottom = bottom - height * 0.04
        if index == 0:
            crop_top = max(crop_top, 0.070)
        crop = _crop_rel(round_image, (x0_ratio, crop_top, x1_ratio, crop_bottom))
        flags.append(_is_defeat_sticker_visual(crop))
    return flags


def _detect_detail_text_defeat_slots(
    round_image: Image.Image,
    items: list[OCRItem],
    defeat_boxes: dict[str, list[tuple[float, float, float, float] | None]] | None = None,
) -> dict[str, list[bool]]:
    coord_size = _ocr_coordinate_size(items, round_image)
    flags = {
        "attacker": [False] * len(DETAIL_SLOT_CENTERS),
        "defender": [False] * len(DETAIL_SLOT_CENTERS),
    }
    for item in items:
        if "战败" not in item.text:
            continue
        x_ratio, y_ratio = _ocr_item_center_ratio(item, round_image, coord_size)
        if defeat_boxes:
            x = x_ratio * round_image.width
            y = y_ratio * round_image.height
            for side, boxes in defeat_boxes.items():
                for slot, box in enumerate(boxes):
                    if box is None:
                        continue
                    x0, y0, x1, y1 = box
                    if x0 <= x <= x1 and y0 <= y <= y1:
                        flags[side][slot] = True
            continue
        slot = _detail_slot_from_y_ratio(y_ratio)
        if slot is not None:
            side = "attacker" if x_ratio < 0.5 else "defender"
            flags[side][slot] = True
    return flags


def _detect_round_winner_by_detailed_defeat(
    round_image: Image.Image,
    items: list[OCRItem] | None = None,
    defeat_boxes: dict[str, list[tuple[float, float, float, float] | None]] | None = None,
) -> tuple[str, float]:
    if items is None:
        items = []
    text_flags = _detect_detail_text_defeat_slots(round_image, items, defeat_boxes=defeat_boxes)
    attacker_defeat_boxes = defeat_boxes.get("attacker") if defeat_boxes else None
    defender_defeat_boxes = defeat_boxes.get("defender") if defeat_boxes else None
    attacker_flags = [
        visual or text
        for visual, text in zip(
            _detect_detail_visual_defeat_slots(round_image, "attacker", defeat_boxes=attacker_defeat_boxes),
            text_flags["attacker"],
        )
    ]
    defender_flags = [
        visual or text
        for visual, text in zip(
            _detect_detail_visual_defeat_slots(round_image, "defender", defeat_boxes=defender_defeat_boxes),
            text_flags["defender"],
        )
    ]
    attacker_defeats = sum(attacker_flags)
    defender_defeats = sum(defender_flags)

    if defender_defeats >= DETAILED_DEFEAT_STRICT_COUNT and attacker_defeats < DETAILED_DEFEAT_STRICT_COUNT:
        return "attacker", 0.96
    if attacker_defeats >= DETAILED_DEFEAT_STRICT_COUNT and defender_defeats < DETAILED_DEFEAT_STRICT_COUNT:
        return "defender", 0.96
    if defender_defeats >= DETAILED_DEFEAT_SOFT_COUNT and attacker_defeats <= 2:
        return "attacker", 0.78
    if attacker_defeats >= DETAILED_DEFEAT_SOFT_COUNT and defender_defeats <= 2:
        return "defender", 0.78
    return "unknown", 0.35


def _detect_round_winner_by_text(
    round_image: Image.Image,
    ocr: ArenaOCRRecognizer,
    items: list[OCRItem] | None = None,
) -> tuple[str, float]:
    if items is None:
        items = ocr.recognize_region(prepare_for_ocr(round_image), "round_result")
    if not items:
        return "unknown", 0.0

    coord_size = _ocr_coordinate_size(items, round_image)
    left_loses = 0
    right_loses = 0
    left_wins = 0
    right_wins = 0
    for item in items:
        text = item.text.upper()
        x_ratio, _y_ratio = _ocr_item_center_ratio(item, round_image, coord_size)
        is_left = x_ratio < 0.5
        if "战败" in item.text or "LOSE" in text:
            if is_left:
                left_loses += 1
            else:
                right_loses += 1
        if "WIN" in text or "胜" in item.text:
            if is_left:
                left_wins += 1
            else:
                right_wins += 1

    attacker_score = right_loses + left_wins
    defender_score = left_loses + right_wins
    diff = abs(attacker_score - defender_score)
    if diff == 0:
        return "unknown", 0.35
    if attacker_score > defender_score:
        return "attacker", min(0.96, 0.65 + diff * 0.07)
    return "defender", min(0.96, 0.65 + diff * 0.07)


def _detect_round_winner_by_color(round_image: Image.Image) -> tuple[str, float]:
    rgb = round_image.convert("RGB")
    w, h = rgb.size
    pixels = rgb.load()

    def score_region(x0: int, x1: int) -> int:
        score = 0
        step_x = max(1, (x1 - x0) // 90)
        step_y = max(1, h // 90)
        for y in range(0, h, step_y):
            for x in range(x0, x1, step_x):
                r, g, b = pixels[x, y]
                cyan = b > 145 and g > 130 and r < 150
                red = r > 170 and g < 150 and b < 150
                dark = r < 70 and g < 70 and b < 70
                if cyan:
                    score += 2
                if red or dark:
                    score -= 1
        return score

    left_score = score_region(0, w // 2)
    right_score = score_region(w // 2, w)
    diff = abs(left_score - right_score)
    if diff < 4:
        return "unknown", 0.25
    if left_score > right_score:
        return "attacker", min(0.90, 0.52 + diff / 90.0)
    return "defender", min(0.90, 0.52 + diff / 90.0)


def detect_round_winner(
    center_image: Image.Image,
    row: int,
    ocr: ArenaOCRRecognizer,
    items: list[OCRItem] | None = None,
    result_mode: str = RESULT_MODE_AUTO,
) -> tuple[str, float]:
    round_image, _round_abs = _detail_round_crop(center_image, row)
    if result_mode == RESULT_MODE_DETAILED:
        detail_winner, detail_conf = _detect_round_winner_by_detailed_defeat(
            round_image,
            items=items,
        )
        if detail_winner != "unknown":
            return detail_winner, detail_conf
        text_winner, text_conf = _detect_round_winner_by_text(round_image, ocr, items=items)
        if text_winner != "unknown":
            return text_winner, text_conf
        return _detect_round_winner_by_color(round_image)
    if result_mode == RESULT_MODE_AUTO:
        detail_winner, detail_conf = _detect_round_winner_by_detailed_defeat(
            round_image,
            items=items,
        )
        if detail_winner != "unknown":
            return detail_winner, detail_conf
    text_winner, text_conf = _detect_round_winner_by_text(round_image, ocr, items=items)
    if text_winner != "unknown":
        return text_winner, text_conf
    return _detect_round_winner_by_color(round_image)


def recognize_match_block(
    block: ImageBlock,
    source_name: str,
    ocr: ArenaOCRRecognizer,
    matcher: NikkeNameMatcher,
    debug_dir: Path | None = None,
    stage_name: str = STAGE_NAME,
    include_teams: bool = True,
    include_power: bool = True,
    include_collection: bool = True,
    include_stat_levels: bool = True,
    source_profile: str = "",
) -> list[dict]:
    regions: MatchRegions = split_match_block(block.image)
    if debug_dir:
        save_match_debug(block, regions, debug_dir, Path(source_name).stem)

    attacker_image = regions.attacker_area[0]
    center_image = regions.center_result_area[0]
    defender_image = regions.defender_area[0]

    attacker_id = recognize_player_id(
        attacker_image,
        "attacker",
        ocr,
    )
    defender_id = recognize_player_id(
        defender_image,
        "defender",
        ocr,
    )
    attacker_nickname = recognize_player_nickname(
        attacker_image,
        "attacker",
        ocr,
    )
    defender_nickname = recognize_player_nickname(
        defender_image,
        "defender",
        ocr,
    )
    result_mode = _infer_result_mode(source_name)
    if ocr.available and include_teams:
        attacker_stat_levels = (
            recognize_stat_levels(
                attacker_image,
                "attacker",
                ocr,
            )
            if include_stat_levels
            else []
        )
        defender_stat_levels = (
            recognize_stat_levels(
                defender_image,
                "defender",
                ocr,
            )
            if include_stat_levels
            else []
        )
        attacker_teams, attacker_powers, attacker_collections = recognize_team_rows(
            attacker_image,
            ocr,
            matcher,
            "attacker",
            include_power=include_power,
            include_collection=include_collection,
            match_index=block.match_index,
            stage_name=stage_name,
            block_height=block.image.height,
            source_profile=source_profile,
        )
        defender_teams, defender_powers, defender_collections = recognize_team_rows(
            defender_image,
            ocr,
            matcher,
            "defender",
            include_power=include_power,
            include_collection=include_collection,
            match_index=block.match_index,
            stage_name=stage_name,
            block_height=block.image.height,
            source_profile=source_profile,
        )
    else:
        attacker_stat_levels = []
        defender_stat_levels = []
        attacker_teams = [[] for _ in range(5)]
        defender_teams = [[] for _ in range(5)]
        attacker_powers = [[None] * 5 for _ in range(5)]
        defender_powers = [[None] * 5 for _ in range(5)]
        attacker_collections = [[COLLECTION_NONE] * 5 for _ in range(5)]
        defender_collections = [[COLLECTION_NONE] * 5 for _ in range(5)]
    detail_items: list[list[OCRItem]] = [[] for _ in range(5)]
    if ocr.available and include_teams:
        detail_attacker, detail_defender, attacker_scores, defender_scores, detail_items = recognize_detail_team_rows(
            center_image,
            ocr,
            matcher,
            block_height=block.image.height,
        )
        attacker_teams = _merge_team_sources(attacker_teams, detail_attacker, attacker_scores, matcher)
        defender_teams = _merge_team_sources(defender_teams, detail_defender, defender_scores, matcher)

    records: list[dict] = []
    for row in range(5):
        winner_items = detail_items[row] if include_teams else None
        winner, winner_conf = detect_round_winner(
            center_image,
            row,
            ocr,
            items=winner_items,
            result_mode=result_mode,
        )
        recognized_count = sum(bool(name) for name in attacker_teams[row] + defender_teams[row])
        team_conf = 0.15 * recognized_count
        confidence = max(0.0, min(1.0, 0.40 * winner_conf + team_conf))
        if not ocr.available:
            confidence = min(confidence, 0.35)
        records.append(
            {
                "stage": stage_name,
                "group_index": block.group_index,
                "match_index": block.match_index,
                "round_index": row + 1,
                "attacker_player_id": attacker_id,
                "attacker_player_nickname": attacker_nickname,
                "attacker_stat_levels": attacker_stat_levels,
                "defender_player_id": defender_id,
                "defender_player_nickname": defender_nickname,
                "defender_stat_levels": defender_stat_levels,
                "attacker_team": attacker_teams[row],
                "attacker_power": attacker_powers[row],
                "attacker_collection": attacker_collections[row],
                "defender_team": defender_teams[row],
                "defender_power": defender_powers[row],
                "defender_collection": defender_collections[row],
                "winner": winner,
                "confidence": round(confidence, 4),
                "source_image": source_name,
            }
        )
    return records
