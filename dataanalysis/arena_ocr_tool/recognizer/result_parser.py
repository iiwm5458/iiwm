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
DETAIL_NAME_HARD_TOP_Y = 0.060
DETAIL_NAME_CONDITIONAL_TOP_Y = 0.085
# The HP percentage is printed near the lower edge of each detailed-result
# card, not at the character-name centers above.
DETAIL_HP_SLOT_CENTERS = (0.225, 0.402, 0.582, 0.758, 0.937)
DETAIL_HP_RETRY_X = {
    "attacker": (0.00, 0.32),
    "defender": (0.68, 1.00),
}
DETAIL_HP_RETRY_MIN_CONFIDENCE = 0.75
DETAILED_RESULT_PANEL_X = (0.4019, 0.5992)
DETAILED_RESULT_LEFT_PORTRAIT_X = (0.015, 0.205)
DETAILED_RESULT_RIGHT_PORTRAIT_X = (0.785, 0.985)
DETAILED_DEFEAT_VISUAL_DARK_THRESHOLD = 0.43
DETAILED_DEFEAT_VISUAL_CENTER_DARK_THRESHOLD = 0.50
DETAILED_DEFEAT_STRICT_COUNT = 5
DETAILED_DEFEAT_TEMPLATE_THRESHOLD = 0.78
CLIENT_PROFILE_CN = "cn"
CLIENT_PROFILE_OVERSEAS = "overseas"
OVERSEAS_NICKNAME_LANGUAGES = ("ch", "japan", "korean", "chinese_cht")
OVERSEAS_NICKNAME_MIN_COMMON_TEXT = 2
OVERSEAS_DEFEAT_TEMPLATE_THRESHOLD = 0.85
OVERSEAS_PRECISE_DEFEAT_TEMPLATE_THRESHOLD = 0.65
OVERSEAS_DETAILED_RESULT_PANEL_X = (0.3950, 0.6050)
DETAILED_DEFEAT_STICKER_X = {
    "attacker": (0.026, 0.216),
    "defender": (0.773, 0.974),
}
OVERSEAS_DEFEAT_STICKER_X = {
    "attacker": (0.031, 0.213),
    "defender": (0.795, 1.000),
}
# Overseas 3440x1440 group64 regions manually tightened in the full-image
# calibration tool. Coordinates are local to one match block and deliberately
# exclude the white gutters. The same boxes also cover the HP percentage used
# for an equal-survivor tiebreak. Other overseas resolutions scale these
# normalized coordinates; the Chinese profile never reads them.
OVERSEAS_DEFEAT_SLOT_BOXES = {
    "top": {
        "attacker": (
            ((0.400976, 0.014370, 0.037152, 0.032036), (0.401509, 0.050069, 0.037685, 0.031704), (0.401509, 0.085604, 0.037685, 0.031972), (0.401509, 0.121441, 0.037685, 0.031670), (0.401509, 0.157110, 0.037152, 0.032338)),
            ((0.400976, 0.213499, 0.037152, 0.032135), (0.401509, 0.248270, 0.037685, 0.033106), (0.401509, 0.284301, 0.037685, 0.032653), (0.401509, 0.320112, 0.037685, 0.032101), (0.401509, 0.355380, 0.037152, 0.032705)),
            ((0.400976, 0.413102, 0.037152, 0.031437), (0.401509, 0.448270, 0.037685, 0.031704), (0.401509, 0.483438, 0.037685, 0.032442), (0.401509, 0.518779, 0.037685, 0.032998), (0.401509, 0.555449, 0.037152, 0.031437)),
            ((0.400976, 0.611337, 0.037152, 0.032135), (0.401509, 0.646838, 0.037685, 0.032403), (0.401509, 0.682575, 0.037685, 0.031674), (0.401509, 0.718313, 0.037685, 0.031337), (0.401509, 0.753581, 0.037152, 0.032338)),
            ((0.401509, 0.810470, 0.037152, 0.031734), (0.401509, 0.846139, 0.037685, 0.032243), (0.401509, 0.882105, 0.037685, 0.031575), (0.401509, 0.917972, 0.037685, 0.031670), (0.401509, 0.953110, 0.037152, 0.031790)),
        ),
        "defender": (
            ((0.561952, 0.014802, 0.037717, 0.031605), (0.561952, 0.050500, 0.037717, 0.031273), (0.561952, 0.086035, 0.038251, 0.031540), (0.561952, 0.121009, 0.038251, 0.032532), (0.561952, 0.157541, 0.038251, 0.031907)),
            ((0.561952, 0.213930, 0.037717, 0.031704), (0.561952, 0.248270, 0.037717, 0.032675), (0.561952, 0.285164, 0.038251, 0.031790), (0.561952, 0.319681, 0.038251, 0.032532), (0.561952, 0.355380, 0.038251, 0.032705)),
            ((0.561952, 0.413533, 0.037717, 0.031005), (0.561952, 0.448701, 0.037717, 0.031273), (0.561952, 0.483007, 0.038251, 0.032442), (0.561952, 0.519211, 0.038251, 0.032567), (0.561952, 0.554586, 0.038251, 0.032299)),
            ((0.561952, 0.611769, 0.037717, 0.031704), (0.561952, 0.647269, 0.037717, 0.031972), (0.561952, 0.683438, 0.038251, 0.031242), (0.561952, 0.718313, 0.038251, 0.032200), (0.561952, 0.754012, 0.038251, 0.031907)),
            ((0.561952, 0.810470, 0.037717, 0.031303), (0.561952, 0.846570, 0.037717, 0.031812), (0.561952, 0.882537, 0.038251, 0.031143), (0.561952, 0.917110, 0.038251, 0.032532), (0.561952, 0.953110, 0.038251, 0.031790)),
        ),
    },
    "bottom": {
        "attacker": (
            ((0.400976, 0.019547, 0.037152, 0.032036), (0.401509, 0.054814, 0.037685, 0.031704), (0.401509, 0.089918, 0.037685, 0.031972), (0.401509, 0.125755, 0.037685, 0.031670), (0.401509, 0.162286, 0.037152, 0.032338)),
            ((0.400976, 0.218244, 0.037152, 0.032135), (0.401509, 0.253016, 0.037685, 0.033106), (0.401509, 0.289047, 0.037685, 0.032653), (0.401509, 0.324858, 0.037685, 0.032101), (0.401509, 0.360988, 0.037152, 0.032705)),
            ((0.400976, 0.417847, 0.037152, 0.031437), (0.401509, 0.453016, 0.037685, 0.031704), (0.401509, 0.489047, 0.037685, 0.032442), (0.401509, 0.523956, 0.037685, 0.032998), (0.401509, 0.561057, 0.037152, 0.031437)),
            ((0.400976, 0.616946, 0.037152, 0.032135), (0.401509, 0.652015, 0.037685, 0.032403), (0.401509, 0.687321, 0.037685, 0.031674), (0.401509, 0.723059, 0.037685, 0.031337), (0.401509, 0.759189, 0.037152, 0.032338)),
            ((0.401509, 0.815216, 0.037152, 0.031734), (0.401509, 0.850884, 0.037685, 0.032243), (0.401509, 0.886851, 0.037685, 0.031575), (0.401509, 0.922286, 0.037685, 0.031670), (0.401509, 0.957856, 0.037152, 0.031790)),
        ),
        "defender": (
            ((0.561952, 0.019116, 0.037717, 0.031605), (0.561952, 0.055246, 0.037717, 0.031273), (0.561952, 0.090781, 0.038251, 0.031540), (0.561952, 0.126186, 0.038251, 0.032532), (0.561952, 0.162286, 0.038251, 0.031907)),
            ((0.561952, 0.218244, 0.037717, 0.031704), (0.561952, 0.253447, 0.037717, 0.032675), (0.561952, 0.289478, 0.038251, 0.031790), (0.561952, 0.325289, 0.038251, 0.032532), (0.561952, 0.360988, 0.038251, 0.032705)),
            ((0.561952, 0.417416, 0.037717, 0.031005), (0.561952, 0.453447, 0.037717, 0.031273), (0.561952, 0.488184, 0.038251, 0.032442), (0.561952, 0.524387, 0.038251, 0.032567), (0.561952, 0.560194, 0.038251, 0.032299)),
            ((0.561952, 0.616514, 0.037717, 0.031704), (0.561952, 0.652446, 0.037717, 0.031972), (0.561952, 0.688184, 0.038251, 0.031242), (0.561952, 0.723490, 0.038251, 0.032200), (0.561952, 0.759189, 0.038251, 0.031907)),
            ((0.561952, 0.816079, 0.037717, 0.031303), (0.561952, 0.851747, 0.037717, 0.031812), (0.561952, 0.886851, 0.038251, 0.032006), (0.561952, 0.922286, 0.038251, 0.032532), (0.561419, 0.957856, 0.038251, 0.032222)),
        ),
    },
}
OVERSEAS_PLAYER_REGION_BOXES = {
    "top": {
        "attacker": {
            "nickname": (0.115568, 0.173469, 0.253040, 0.025729),
            "id": (0.113035, 0.199823, 0.144096, 0.025280),
            "id_fallback": (0.113829, 0.198770, 0.140123, 0.027623),
        },
        "defender": {
            "nickname": (0.730549, 0.173956, 0.232976, 0.026911),
            "id": (0.728363, 0.198645, 0.144128, 0.022403),
            "id_fallback": (0.728501, 0.198628, 0.142421, 0.027187),
        },
    },
    "bottom": {
        "attacker": {
            "nickname": (0.115568, 0.177136, 0.253040, 0.024866),
            "id": (0.113035, 0.203059, 0.144096, 0.023986),
            "id_fallback": (0.113829, 0.202006, 0.140123, 0.024387),
        },
        "defender": {
            "nickname": (0.730549, 0.176760, 0.232976, 0.024754),
            "id": (0.728363, 0.202959, 0.144128, 0.023913),
            "id_fallback": (0.728501, 0.201648, 0.142421, 0.024167),
        },
    },
}
DETAILED_DEFEAT_STICKER_Y = (
    (0.087, 0.241),
    (0.269, 0.426),
    (0.449, 0.610),
    (0.635, 0.787),
    (0.812, 0.968),
)
DETAILED_DEFEAT_STICKER_Y_BY_ROUND = (
    ((0.0161, 0.0543), (0.0518, 0.0901), (0.0882, 0.1272), (0.1249, 0.1623), (0.1610, 0.1995)),
    ((0.2148, 0.2531), (0.2509, 0.2907), (0.2873, 0.3265), (0.3240, 0.3614), (0.3597, 0.3990)),
    ((0.4144, 0.4520), (0.4500, 0.4883), (0.4860, 0.5258), (0.5231, 0.5612), (0.5592, 0.5978)),
    ((0.6135, 0.6518), (0.6492, 0.6880), (0.6856, 0.7242), (0.7223, 0.7597), (0.7579, 0.7964)),
    ((0.8122, 0.8501), (0.8483, 0.8869), (0.8847, 0.9233), (0.9210, 0.9584), (0.9570, 0.9937)),
)
DETAILED_DEFEAT_TEXT_TEMPLATE_HEX_ROWS = (
    "000000000000000000",
    "000000000000000000",
    "000000000000000000",
    "000000000000000000",
    "0007c0ff83df3e0000",
    "000fc0ffc7fffffc00",
    "000fc0ffcffffffe00",
    "000ffcffeffffffe00",
    "000ffe7fe7fffffe00",
    "000fffffefcffffe00",
    "000fffffeffffffc00",
    "000fc7ffeffffc7c00",
    "000fc3ffeffffc7c00",
    "007fffffcffffe7c00",
    "007ffe3f0ffffe7c00",
    "007ffe1f6ffffefc00",
    "007ffe1feffffffc00",
    "007efe1feffffff800",
    "007c7e1feffffff800",
    "007e7c7fe7ff9ff000",
    "007e7e7fc7ff1ff000",
    "007c7fffc1ff1ff000",
    "007e7fffc3ff1ff000",
    "007effffe3ffbff800",
    "007fffe7e7fffffc00",
    "007fff87e7fffefc00",
    "007ffe03e7e7fc7c00",
)
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
POWER_GEOMETRY_STRONG_CONFIDENCE = 0.99
POWER_GEOMETRY_MIN_STRONG_VOTES = 3
POWER_GEOMETRY_MIN_VOTE_LEAD = 2
POWER_STRIP_CROP_TOP = 0.64
POWER_STRIP_CROP_BOTTOM = 0.985
POWER_STRIP_CROP_HALF_WIDTH = 0.125
POWER_STRIP_BATCH_SIZE = 32
SHORT_NAME_POWER_PROBE_MIN_CONFIDENCE = 0.70
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
# Overseas roster cards use the same icon artwork but a different card grid.
# These two profiles were fitted from the aligned 1920x1080 and 3440x1440
# group64 exports. Coordinates are local to the cropped roster row except for
# icon_y0, which is local to the whole match block.
OVERSEAS_COLLECTION_GRID_FHD = {
    "block_height": 2296,
    "row_width": {"attacker": 787, "defender": 788},
    "icon_x0": {
        "attacker": (2, 144, 286, 428, 570),
        "defender": (87, 229, 371, 513, 655),
    },
    "icon_y0": (720, 1018, 1316, 1614, 1912),
    "icon_width": 27,
    "icon_height": 29,
    "bottom_match_dy": 11,
}
OVERSEAS_COLLECTION_GRID_WIDE = {
    "block_height": 2318,
    "row_width": {"attacker": 789, "defender": 790},
    "icon_x0": {
        "attacker": (3, 145, 287, 429, 571),
        "defender": (90, 232, 374, 516, 658),
    },
    "icon_y0": (718, 1017, 1316, 1615, 1914),
    "icon_width": 26,
    "icon_height": 29,
    "bottom_match_dy": 12,
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
# A positive icon crop can resemble a manually collected empty-slot crop at
# low resolution.  Keep a small tolerance instead of requiring a positive
# template to beat every empty-slot template outright, while still rejecting
# portrait backgrounds that score materially closer to the empty samples.
COLLECTION_DIRECT_PRESENCE_MARGIN = -0.025
COLLECTION_DIRECT_R15_CYAN_OVERRIDE_DARK_MIN = 0.24
COLLECTION_DIRECT_R15_CYAN_OVERRIDE_DARK_MAX = 0.34
COLLECTION_DIRECT_R15_CYAN_OVERRIDE_WHITE_MAX = 0.46
COLLECTION_DIRECT_R15_CYAN_OVERRIDE_MARGIN = 0.04
COLLECTION_DIRECT_R15_CYAN_OVERRIDE_ACTIVE_MIN = 0.18
COLLECTION_DIRECT_R15_CYAN_OVERRIDE_SCORE_MARGIN = -0.08
NAME_PROFILE_DEFAULT = "default"
NAME_PROFILE_FHD = "fhd"
SOURCE_PROFILE_1920_1080 = "1920x1080"
SOURCE_PROFILE_1920_1200 = "1920x1200"
SOURCE_PROFILE_1920_1440 = "1920x1440"
SOURCE_PROFILE_2560_1080 = "2560x1080"
SOURCE_PROFILE_2560_1440 = "2560x1440"
SOURCE_PROFILE_3840 = "3840x2160"
SOURCE_PROFILE_2560_1600 = "2560x1600"
SOURCE_PROFILE_3440_1440 = "3440x1440"

# Source resolution is available from the imported filename.  Keep the two
# measured overseas anchors intact and derive the remaining source profiles
# from their matching FHD or wide stitch family.  The 2560x1440 client export
# has a verified one-pixel horizontal and two-pixel vertical icon phase.
OVERSEAS_COLLECTION_GRID_BY_SOURCE_PROFILE = {
    SOURCE_PROFILE_1920_1080: OVERSEAS_COLLECTION_GRID_FHD,
    SOURCE_PROFILE_1920_1200: OVERSEAS_COLLECTION_GRID_FHD,
    SOURCE_PROFILE_1920_1440: OVERSEAS_COLLECTION_GRID_FHD,
    SOURCE_PROFILE_2560_1080: OVERSEAS_COLLECTION_GRID_FHD,
    SOURCE_PROFILE_2560_1440: {
        **OVERSEAS_COLLECTION_GRID_WIDE,
        "phase_dx": 1.0,
        "phase_dy": -2.0,
        "template_profile": "overseas_2560x1440",
    },
    SOURCE_PROFILE_2560_1600: OVERSEAS_COLLECTION_GRID_WIDE,
    SOURCE_PROFILE_3440_1440: OVERSEAS_COLLECTION_GRID_WIDE,
    SOURCE_PROFILE_3840: OVERSEAS_COLLECTION_GRID_WIDE,
}
# Exact OCR artifacts observed on multiple client layouts. These preserve the
# colon evidence needed by the existing special-name matcher without lowering
# any general name-matching threshold.
GLOBAL_NAME_TEXT_ALIASES = (
    ("阿妮斯一起", "阿妮斯：超"),
    ("米哈拉一颗", "米哈拉：羁"),
    ("德當克", "德雷克"),
    ("特蓄娜", "特蕾娜"),
    ("蓄贝儿", "蕾贝儿"),
    ("拉誉拉斯", "拉普拉斯"),
    ("\u8d22\u72fc", "\u8c7a\u72fc"),
    ("\u6750\u72fc", "\u8c7a\u72fc"),
    ("\u5bf9\u72fc", "\u8c7a\u72fc"),
    ("\u6e21\u9e21", "\u6e21\u9e26"),
    ("\u95ea\u4eae\u514d\u5973\u90ce", "\u95ea\u4eae\u5154\u5973\u90ce"),
    ("\u95ea\u4eae\u514d\u5973\u90ae", "\u95ea\u4eae\u5154\u5973\u90ce"),
    ("\u7d2b\u9c9c", "\u5a1c\u5609"),
)
FHD_NAME_TEXT_ALIASES: tuple[tuple[str, str], ...] = ()
CN_DETAIL_NAME_TEXT_ALIASES_BY_RESOLUTION = {
    "1920x1080": (("面餐", "基里"),),
}
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
STAT_LEVEL_MAX = 999
STAT_LEVEL_HIGH_VALUE_MIN = 251
STAT_LEVEL_HIGH_DIRECT_CONFIDENCE = 0.90
STAT_LEVEL_RECHECK_BELOW = 50
STAT_LEVEL_AREA = (0.0, 0.948, 1.0, 0.998)
STAT_LEVEL_SLOT_Y0 = 0.980
STAT_LEVEL_SLOT_Y1 = 0.998
STAT_LEVEL_RECHECK_SLOT_BOXES = (
    (0.960, STAT_LEVEL_SLOT_Y1, 0.90),
    (0.970, STAT_LEVEL_SLOT_Y1, 1.00),
    (STAT_LEVEL_SLOT_Y0, STAT_LEVEL_SLOT_Y1, 1.00),
    (0.985, STAT_LEVEL_SLOT_Y1, 1.35),
)
# International and HK/TW detailed screens use the same central layout, but
# their DISCONNECTED sticker is shorter than the Chinese defeat sticker. The
# values describe the dark sticker itself and intentionally exclude the white
# card gutters around it.
OVERSEAS_DEFEAT_STICKER_Y_BY_ROUND = tuple(
    tuple((max(0.0, top - 0.0013), min(1.0, top + 0.0305)) for top, _bottom in row)
    for row in DETAILED_DEFEAT_STICKER_Y_BY_ROUND
)
OVERSEAS_DEFEAT_TEMPLATE_FILES = (
    "disconnected_1920.png",
    "disconnected_3440.png",
)
STAT_LEVEL_MISREAD_DIGIT = "6"
STAT_LEVEL_CORRECT_DIGIT = "9"
STAT_LEVEL_NINE_TAIL_SCORE_MIN = 0.08
STAT_LEVEL_LINE_Y0 = 0.975
STAT_LEVEL_LINE_Y1 = 0.998
STAT_LEVEL_LINE_MIN_VOTES = 3
STAT_LEVEL_LINE_MIN_CONFIDENCE = 0.70
STAT_LEVEL_LINE_HIGH_MIN_VOTES = 4
STAT_LEVEL_LINE_HIGH_MIN_CONFIDENCE = 0.85
STAT_LEVEL_LINE_BATCH_SIZE = 32
OVERSEAS_ID_LEFT_RETRY_PADDING = 0.014


@dataclass
class _PowerObservation:
    value: int
    confidence: float
    anchored: bool
    trailing_marker: bool
    distance: float = 0.0
    text: str = ""


@dataclass(frozen=True)
class _PowerGeometryVote:
    geometry_id: str
    value: int
    confidence: float
    anchored: bool
    trailing_marker: bool


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


def _normalize_client_profile(client_profile: str) -> str:
    return CLIENT_PROFILE_OVERSEAS if str(client_profile or "").strip().lower() == CLIENT_PROFILE_OVERSEAS else CLIENT_PROFILE_CN


def _overseas_calibration_tier(stage_name: str, match_index: int) -> str:
    if stage_name == STAGE_NAME and match_index in (3, 4):
        return "bottom"
    return "top"


def _xywh_to_xyxy(box: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    x, y, width, height = box
    return x, y, x + width, y + height


def _overseas_player_side_box(
    side: str,
    field: str,
    stage_name: str,
    match_index: int,
) -> tuple[float, float, float, float]:
    tier = _overseas_calibration_tier(stage_name, match_index)
    whole_box = _xywh_to_xyxy(OVERSEAS_PLAYER_REGION_BOXES[tier][side][field])
    side_origin = 0.0 if side == "attacker" else 0.57
    side_width = 0.43
    return (
        (whole_box[0] - side_origin) / side_width,
        whole_box[1],
        (whole_box[2] - side_origin) / side_width,
        whole_box[3],
    )


def _overseas_defeat_boxes_for_panel(
    match_image: Image.Image,
    panel_image: Image.Image,
    stage_name: str,
    match_index: int,
) -> dict[str, tuple[tuple[tuple[float, float, float, float], ...], ...]]:
    """Map the manually calibrated block-local boxes into panel pixels."""
    tier = _overseas_calibration_tier(stage_name, match_index)
    panel_left = int(match_image.width * OVERSEAS_DETAILED_RESULT_PANEL_X[0])
    mapped: dict[str, tuple[tuple[tuple[float, float, float, float], ...], ...]] = {}
    for side in ("attacker", "defender"):
        rounds: list[tuple[tuple[float, float, float, float], ...]] = []
        for row_boxes in OVERSEAS_DEFEAT_SLOT_BOXES[tier][side]:
            slots: list[tuple[float, float, float, float]] = []
            for rel_box in row_boxes:
                x0, y0, x1, y1 = _xywh_to_xyxy(rel_box)
                slots.append(
                    (
                        match_image.width * x0 - panel_left,
                        panel_image.height * y0,
                        match_image.width * x1 - panel_left,
                        panel_image.height * y1,
                    )
                )
            rounds.append(tuple(slots))
        mapped[side] = tuple(rounds)
    return mapped


def _panel_boxes_to_round_boxes(
    panel_image: Image.Image,
    row: int,
    boxes: tuple[tuple[float, float, float, float], ...],
) -> tuple[tuple[float, float, float, float], ...]:
    round_top = int(panel_image.height * row / 5)
    return tuple((x0, y0 - round_top, x1, y1 - round_top) for x0, y0, x1, y1 in boxes)


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


def _extract_left_clipped_id(text: str) -> str:
    """Read an ID only when its leading I was clipped inside an ID-only crop."""
    match = re.search(r"(?<![A-Z0-9])D\s*[:：]\s*([0-9]{6,9})(?!\d)", text.upper())
    return match.group(1) if match else ""


def _expand_left_rel_box(
    box: tuple[float, float, float, float],
    padding: float,
) -> tuple[float, float, float, float]:
    return max(0.0, box[0] - padding), box[1], box[2], box[3]


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
    value = text
    for wrong, correct in GLOBAL_NAME_TEXT_ALIASES:
        value = value.replace(wrong, correct)
    if name_profile != NAME_PROFILE_FHD:
        return value
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
    client_profile: str = CLIENT_PROFILE_CN,
    stage_name: str = STAGE_NAME,
    match_index: int = 1,
) -> str:
    if _normalize_client_profile(client_profile) == CLIENT_PROFILE_OVERSEAS:
        id_box = _overseas_player_side_box(side, "id", stage_name, match_index)
        fallback_box = _overseas_player_side_box(side, "id_fallback", stage_name, match_index)
    elif side == "attacker":
        id_box = (0.23, 0.205, 0.86, 0.245)
        fallback_box = (0.15, 0.19, 0.98, 0.255)
    else:
        id_box = (0.02, 0.205, 0.76, 0.245)
        fallback_box = (0.02, 0.19, 0.85, 0.255)
    id_text, id_items = _ocr_text(ocr, _crop_rel(side_image, id_box), f"{side}_id")
    id_source = " ".join([id_text, _items_to_text(id_items)])
    player_id = _extract_id(id_source)
    if player_id:
        return player_id

    fallback_text, fallback_items = _ocr_text(
        ocr,
        _crop_rel(side_image, fallback_box),
        f"{side}_id_fallback",
    )
    fallback_source = " ".join([fallback_text, _items_to_text(fallback_items)])
    player_id = _extract_id(fallback_source)
    if player_id:
        return player_id

    if _normalize_client_profile(client_profile) != CLIENT_PROFILE_OVERSEAS:
        return ""

    # The overseas crop deliberately excludes the language/server labels. A few
    # screenshots place the I in ID directly on its left border, so retry only
    # that edge instead of restoring the old broad, noisy crop.
    retry_box = _expand_left_rel_box(id_box, OVERSEAS_ID_LEFT_RETRY_PADDING)
    retry_text, retry_items = _ocr_text(
        ocr,
        _crop_rel(side_image, retry_box),
        f"{side}_id_left_retry",
    )
    retry_source = " ".join([retry_text, _items_to_text(retry_items)])
    player_id = _extract_id(retry_source)
    if player_id:
        return player_id

    clipped_candidates = [
        candidate
        for candidate in (
            _extract_left_clipped_id(id_source),
            _extract_left_clipped_id(fallback_source),
            _extract_left_clipped_id(retry_source),
        )
        if candidate
    ]
    counts = Counter(clipped_candidates)
    return next((candidate for candidate, count in counts.items() if count >= 2), "")


def _overseas_nickname_images(
    nickname_band: Image.Image,
    ocr: ArenaOCRRecognizer,
) -> list[tuple[str, Image.Image]]:
    """Return tight nickname crops plus a conservative horizontal inset.

    The international profile has Japanese/Korean text models. Their
    recognition-only mode treats every pixel in the supplied crop as one line,
    which can append a neighbouring UI glyph. The multilingual detector finds
    the actual text first; if it cannot, the legacy crop remains available.
    """
    boxes = ocr.detect_nickname_text_boxes(nickname_band)
    if not boxes:
        return [("fallback", prepare_for_ocr(nickname_band))]

    def box_bounds(box: list[tuple[float, float]]) -> tuple[float, float, float, float]:
        x_values = [point[0] for point in box]
        y_values = [point[1] for point in box]
        return min(x_values), min(y_values), max(x_values), max(y_values)

    bounded_boxes = [(box, box_bounds(box)) for box in boxes if len(box) >= 4]
    if not bounded_boxes:
        return [("fallback", prepare_for_ocr(nickname_band))]

    # A detector can occasionally see small parts of the nearby blue profile
    # action button. Start with the largest text-shaped box, then join only
    # horizontally adjacent boxes on the same baseline. This preserves names
    # containing a visual space while excluding those button fragments.
    primary_box, primary_bounds = max(
        bounded_boxes,
        key=lambda item: max(1.0, item[1][2] - item[1][0]) * max(1.0, item[1][3] - item[1][1]),
    )
    px0, py0, px1, py1 = primary_bounds
    primary_height = max(1.0, py1 - py0)
    relevant_boxes = [primary_box]
    for box, (x0, y0, x1, y1) in bounded_boxes:
        if box is primary_box:
            continue
        same_baseline = abs(((y0 + y1) / 2) - ((py0 + py1) / 2)) <= primary_height * 0.45
        horizontal_gap = max(0.0, max(px0, x0) - min(px1, x1))
        if same_baseline and horizontal_gap <= primary_height * 1.25:
            relevant_boxes.append(box)

    points = [point for box in relevant_boxes for point in box]
    if not points:
        return [("fallback", prepare_for_ocr(nickname_band))]
    x_values = [point[0] for point in points]
    y_values = [point[1] for point in points]
    x0, x1 = min(x_values), max(x_values)
    y0, y1 = min(y_values), max(y_values)
    text_height = max(1.0, y1 - y0)
    pad_x = max(2, int(round(text_height * 0.14)))
    pad_y = max(2, int(round(text_height * 0.12)))
    left = max(0, int(x0) - pad_x)
    top = max(0, int(y0) - pad_y)
    right = min(nickname_band.width, int(x1 + 0.999) + pad_x)
    bottom = min(nickname_band.height, int(y1 + 0.999) + pad_y)
    if right <= left or bottom <= top:
        return [("fallback", prepare_for_ocr(nickname_band))]

    tight = nickname_band.crop((left, top, right, bottom))
    images = [("tight", prepare_for_ocr(tight))]
    inset = max(1, int(round(text_height * 0.045)))
    if tight.width > inset * 2 + 8:
        inner = tight.crop((inset, 0, tight.width - inset, tight.height))
        images.append(("tight_inset", prepare_for_ocr(inner)))
    return images


def _nickname_reading(
    raw_text: str,
    confidence: float,
    language: str,
    variant: str,
) -> dict[str, object] | None:
    text = _clean_text(raw_text)
    if not text or len(text) > 28 or re.fullmatch(r"[\d\W_]+", text):
        return None
    upper_text = text.upper()
    if (
        "\u670d\u52a1\u5668" in text
        or re.fullmatch(r"(?:ID|LV|SERVER)", upper_text) is not None
        or re.search(r"(?<![A-Z0-9])(?:ID|LV)\s*[:\uff1a]?\s*\d", upper_text) is not None
        or re.search(r"(?<![A-Z])SERVER\s*[:\uff1a]?\s*[A-Z0-9-]+", upper_text) is not None
    ):
        return None
    has_kana = bool(re.search(r"[\u3040-\u30ff]", text))
    has_hangul = bool(re.search(r"[\u1100-\u11ff\u3130-\u318f\uac00-\ud7af]", text))
    has_han = bool(re.search(r"[\u3400-\u9fff]", text))

    # Korean nicknames commonly mix Hangul with Latin letters and digits. Hanja
    # is exceptionally rare in this UI, so retain the historical cleanup for
    # the occasional Han glyph hallucinated by the Korean recognizer.
    if language == "korean" and has_hangul:
        text = _clean_text(re.sub(r"[\u3400-\u9fff]+", "", text))
        has_hangul = bool(re.search(r"[\u1100-\u11ff\u3130-\u318f\uac00-\ud7af]", text))

    # Script gates prevent foreign recognizers from assigning high-confidence
    # nonsense to a valid Chinese or Latin nickname. A Kanji-only Japanese
    # name remains ambiguous by nature and is intentionally left to the
    # Chinese/Traditional candidates instead of pretending certainty.
    if language == "japan" and not has_kana:
        return None
    if language == "korean" and not has_hangul:
        return None
    if language == "chinese_cht" and not has_han:
        return None

    score = float(confidence)
    if language == "japan" and has_kana:
        score += 0.15
    elif language == "korean" and has_hangul:
        score += 0.15
    return {
        "text": text,
        "language": language,
        "variant": variant,
        "confidence": float(confidence),
        "score": score,
    }


def _is_edge_confirmed_shorter(long_text: str, short_text: str) -> bool:
    if len(short_text) < OVERSEAS_NICKNAME_MIN_COMMON_TEXT or len(long_text) <= len(short_text):
        return False
    if len(long_text) - len(short_text) > 3:
        return False
    return long_text.startswith(short_text) or long_text.endswith(short_text)


def _add_japanese_prolonged_mark_corrections(
    readings: list[dict[str, object]],
    reference_readings: list[dict[str, object]],
) -> None:
    """Repair a low-resolution Japanese long-vowel mark only with proof.

    At low resolutions, the final glyph in ``ばんちょー`` can be read as the
    visually similar Han character ``一``. Do not replace it globally: make a
    corrected candidate only when a wider Japanese-only reading contains the
    identical stem followed by the prolonged sound mark.
    """
    references = [
        str(reading["text"])
        for reading in reference_readings
        if str(reading["language"]) == "japan"
    ]
    if not references:
        return
    corrections: list[dict[str, object]] = []
    for reading in readings:
        if str(reading["language"]) != "japan":
            continue
        text = str(reading["text"])
        if len(text) < 2 or not text.endswith("一") or not re.search(r"[\u3040-\u30ff]", text[:-1]):
            continue
        corrected = f"{text[:-1]}ー"
        if not any(corrected in reference for reference in references):
            continue
        correction = dict(reading)
        correction["text"] = corrected
        correction["variant"] = "prolonged_mark_reference"
        correction["score"] = float(reading["score"]) + 0.035
        corrections.append(correction)
    readings.extend(corrections)


def _repair_japanese_han_tail_from_cross_model_consensus(
    readings: list[dict[str, object]],
    selected_text: str,
) -> str:
    """Repair one kana-shaped tail glyph only when two OCR families agree.

    Overseas nicknames can mix kana and Han characters. At FHD, the Japanese
    recognizer can read a final Han glyph such as ``力`` as the similarly shaped
    katakana ``カ`` while the Chinese recognizers retain the Han suffix. Keep the
    Japanese reading as the structural source and borrow only a 2-4 character
    Han suffix supported by both Chinese model families and both crop variants.
    """
    if not re.search(r"[\u3040-\u30ff]", selected_text):
        return selected_text
    if not any(
        str(reading.get("language") or "") == "japan"
        and str(reading.get("text") or "") == selected_text
        for reading in readings
    ):
        return selected_text

    suffix_support: dict[str, dict[str, object]] = {}
    for reading in readings:
        language = str(reading.get("language") or "")
        if language not in {"ch", "chinese_cht"}:
            continue
        confidence = float(reading.get("confidence") or 0.0)
        if confidence < 0.65:
            continue
        text = str(reading.get("text") or "")
        variant = str(reading.get("variant") or "")
        for length in range(2, min(4, len(text)) + 1):
            suffix = text[-length:]
            if re.fullmatch(r"[\u3400-\u9fff]+", suffix) is None:
                continue
            support = suffix_support.setdefault(
                suffix,
                {"sources": set(), "languages": set(), "confidence": 0.0},
            )
            support["sources"].add((language, variant))
            support["languages"].add(language)
            support["confidence"] = float(support["confidence"]) + confidence

    candidates: list[tuple[tuple[int, int, int, float], str]] = []
    for suffix, support in suffix_support.items():
        sources = support["sources"]
        languages = support["languages"]
        if len(languages) < 2 or len(sources) < 3 or len(selected_text) < len(suffix):
            continue
        current_tail = selected_text[-len(suffix) :]
        differences = [index for index, pair in enumerate(zip(current_tail, suffix)) if pair[0] != pair[1]]
        if len(differences) != 1:
            continue
        difference_index = differences[0]
        old_char = current_tail[difference_index]
        new_char = suffix[difference_index]
        if re.fullmatch(r"[\u3040-\u30ff]", old_char) is None:
            continue
        if re.fullmatch(r"[\u3400-\u9fff]", new_char) is None:
            continue
        shared_chars = [
            char
            for index, char in enumerate(suffix)
            if index != difference_index and re.fullmatch(r"[\u3400-\u9fff]", char)
        ]
        if not shared_chars:
            continue
        repaired = selected_text[: -len(suffix)] + suffix
        rank = (len(languages), len(sources), len(suffix), float(support["confidence"]))
        candidates.append((rank, repaired))

    if not candidates:
        return selected_text
    return max(candidates, key=lambda item: item[0])[1]


def _select_nickname_candidate(readings: list[dict[str, object]], use_edge_consensus: bool) -> str:
    if not readings:
        return ""

    occurrences: dict[tuple[str, str], set[str]] = {}
    for reading in readings:
        key = (str(reading["language"]), str(reading["text"]))
        occurrences.setdefault(key, set()).add(str(reading["variant"]))

    candidates: list[tuple[float, int, int, str]] = []
    for reading in readings:
        language = str(reading["language"])
        text = str(reading["text"])
        stability = len(occurrences[(language, text)])
        score = float(reading["score"]) + (0.025 if stability >= 2 else 0.0)
        # Shorter is deliberately the last tiebreaker. The old positive length
        # tiebreaker chose an extra tail character whenever confidences tied.
        candidates.append((score, stability, -len(text), text))

    if use_edge_consensus:
        for long_reading in readings:
            if str(long_reading["variant"]) != "tight":
                continue
            for short_reading in readings:
                if str(short_reading["variant"]) != "tight_inset":
                    continue
                if str(long_reading["language"]) != str(short_reading["language"]):
                    continue
                long_text = str(long_reading["text"])
                short_text = str(short_reading["text"])
                if not _is_edge_confirmed_shorter(long_text, short_text):
                    continue
                if float(short_reading["score"]) + 0.05 < float(long_reading["score"]):
                    continue
                candidates.append(
                    (
                        max(float(long_reading["score"]), float(short_reading["score"])) + 0.03,
                        2,
                        -len(short_text),
                        short_text,
                    )
                )
    selected = max(candidates, key=lambda value: (value[0], value[1], value[2]))[3]
    if use_edge_consensus:
        selected = _repair_japanese_han_tail_from_cross_model_consensus(readings, selected)
    return selected


def recognize_player_nickname(
    side_image: Image.Image,
    side: str,
    ocr: ArenaOCRRecognizer,
    client_profile: str = CLIENT_PROFILE_CN,
    stage_name: str = STAGE_NAME,
    match_index: int = 1,
) -> str:
    # The nickname is the single text row between the decorative title and ID.
    # The Chinese path deliberately keeps its existing crop and candidate order.
    is_overseas = _normalize_client_profile(client_profile) == CLIENT_PROFILE_OVERSEAS
    name_box = (
        _overseas_player_side_box(side, "nickname", stage_name, match_index)
        if is_overseas
        else ((0.20, 0.172, 0.74, 0.202) if side == "attacker" else (0.12, 0.172, 0.67, 0.202))
    )
    nickname_band = _crop_rel(side_image, name_box)
    image_variants = (
        _overseas_nickname_images(nickname_band, ocr)
        if is_overseas
        else [("fallback", prepare_for_ocr(nickname_band))]
    )
    languages = OVERSEAS_NICKNAME_LANGUAGES if is_overseas else ("ch", "japan", "korean")
    readings: list[dict[str, object]] = []
    for variant, nickname_image in image_variants:
        for raw_text, confidence, language in ocr.recognize_nickname_candidates(
            nickname_image,
            f"{side}_nickname_{variant}",
            languages=languages,
        ):
            reading = _nickname_reading(raw_text, confidence, language, variant)
            if reading is not None:
                readings.append(reading)
    if is_overseas and any(
        str(reading["language"]) == "japan"
        and str(reading["text"]).endswith("一")
        and bool(re.search(r"[\u3040-\u30ff]", str(reading["text"])[:-1]))
        for reading in readings
    ):
        reference_readings: list[dict[str, object]] = []
        for raw_text, confidence, language in ocr.recognize_nickname_candidates(
            prepare_for_ocr(nickname_band),
            f"{side}_nickname_full_reference",
            languages=("japan",),
            include_detected_chinese=False,
        ):
            reading = _nickname_reading(raw_text, confidence, language, "full_reference")
            if reading is not None:
                reference_readings.append(reading)
        _add_japanese_prolonged_mark_corrections(readings, reference_readings)
    return _select_nickname_candidate(readings, use_edge_consensus=is_overseas)


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


def _name_compact(text: str, matcher: NikkeNameMatcher, name_profile: str = NAME_PROFILE_DEFAULT) -> str:
    value = _apply_name_profile_aliases(_clean_text(text), name_profile)
    return matcher.normalize_name(value).replace(CANONICAL_COLON, "")


def _local_names(matcher: NikkeNameMatcher) -> set[str]:
    return {str(name).strip() for name in getattr(matcher, "names", []) if str(name).strip()}


def _compact_len(name: str, matcher: NikkeNameMatcher) -> int:
    return len(matcher.normalize_name(name).replace(CANONICAL_COLON, ""))


def _is_precise_slot_name_target(name: str, matcher: NikkeNameMatcher) -> bool:
    norm = matcher.normalize_name(name)
    return CANONICAL_COLON in norm or _compact_len(name, matcher) >= 5


def _is_short_slot_name_target(name: str, matcher: NikkeNameMatcher) -> bool:
    norm = matcher.normalize_name(name)
    if not norm or CANONICAL_COLON in norm:
        return False
    compact = norm.replace(CANONICAL_COLON, "")
    if re.fullmatch(r"[\u4e00-\u9fff]{1,2}", compact):
        return True
    # Avoid accepting single Latin letters such as UI markers; multi-character
    # short codes like 2B/A2/N102 remain exact-match eligible.
    return bool(re.fullmatch(r"[A-Za-z0-9.\-]{2,4}", compact))


def _base_name_norm(name: str, matcher: NikkeNameMatcher) -> str:
    return matcher.normalize_name(name).split(CANONICAL_COLON, 1)[0]


def _special_suffix_compact(name: str, matcher: NikkeNameMatcher) -> str:
    norm = matcher.normalize_name(name)
    if CANONICAL_COLON not in norm:
        return ""
    return norm.split(CANONICAL_COLON, 1)[1].replace(CANONICAL_COLON, "")


def _has_special_variants(name: str, matcher: NikkeNameMatcher) -> bool:
    base = _base_name_norm(name, matcher)
    if not base:
        return False
    return any(_base_name_norm(special, matcher) == base for special in getattr(matcher, "special_names", []))


def _special_variant_candidates(current_name: str, matcher: NikkeNameMatcher) -> list[str]:
    base = _base_name_norm(current_name, matcher)
    if not base:
        return []
    return [
        special
        for special in getattr(matcher, "special_names", [])
        if _base_name_norm(special, matcher) == base
    ]


def _has_special_slot_evidence(
    text: str,
    special_name: str,
    matcher: NikkeNameMatcher,
    *,
    base_known: bool,
    name_profile: str = NAME_PROFILE_DEFAULT,
) -> bool:
    text_value = _apply_name_profile_aliases(_clean_text(text), name_profile)
    text_norm = matcher.normalize_name(text_value)
    text_compact = text_norm.replace(CANONICAL_COLON, "")
    special_norm = matcher.normalize_name(special_name)
    if CANONICAL_COLON not in special_norm or not text_compact:
        return False
    base_norm, suffix_norm = special_norm.split(CANONICAL_COLON, 1)
    base_compact = base_norm.replace(CANONICAL_COLON, "")
    suffix_compact = suffix_norm.replace(CANONICAL_COLON, "")
    full_compact = special_norm.replace(CANONICAL_COLON, "")
    if not suffix_compact:
        return False

    if CANONICAL_COLON in text_norm:
        text_suffix = text_norm.split(CANONICAL_COLON, 1)[1].replace(CANONICAL_COLON, "")
        if text_suffix and suffix_compact.startswith(text_suffix[: min(2, len(text_suffix))]):
            return True
        if text_suffix and text_suffix in suffix_compact and len(text_suffix) >= 2:
            return True

    if base_known:
        if suffix_compact[:2] and suffix_compact[:2] in text_compact:
            return True
        for length in range(3, min(len(suffix_compact), 6) + 1):
            for start in range(0, len(suffix_compact) - length + 1):
                if suffix_compact[start : start + length] in text_compact:
                    return True
        return False

    if text_compact.startswith(base_compact + suffix_compact[:2]):
        return True
    if base_compact and text_compact.startswith(base_compact[-1:] + suffix_compact[:2]):
        return True
    if len(text_compact) >= 3 and suffix_compact.startswith(text_compact):
        return True
    if len(text_compact) >= 4 and text_compact in full_compact and not text_compact.endswith(suffix_compact[-3:]):
        return True
    return False


def _slot_precise_name_from_texts(
    texts: list[str],
    matcher: NikkeNameMatcher,
    current_name: str = "",
    name_profile: str = NAME_PROFILE_DEFAULT,
) -> tuple[str, float]:
    local_names = _local_names(matcher)
    if not local_names:
        return "", -1.0

    current_base = _base_name_norm(current_name, matcher) if current_name else ""
    if current_base:
        candidates = [
            name
            for name in local_names
            if _is_precise_slot_name_target(name, matcher)
            and (
                _base_name_norm(name, matcher) == current_base
                or matcher.normalize_name(name).replace(CANONICAL_COLON, "").startswith(
                    matcher.normalize_name(current_name).replace(CANONICAL_COLON, "")
                )
            )
        ]
    else:
        candidates = [name for name in local_names if _is_precise_slot_name_target(name, matcher)]
    if not candidates:
        return "", -1.0

    scores: dict[str, float] = {}
    for raw_text in texts:
        text = _apply_name_profile_aliases(_clean_text(raw_text), name_profile)
        if not text or _is_noise_token(text):
            continue
        text_compact = _name_compact(text, matcher, name_profile=name_profile)
        if not text_compact:
            continue

        matched = matcher.match_name(text)
        matched_name = str(matched.get("matched_name") or "").strip()
        matched_score = float(matched.get("score") or 0.0)
        if matched_name in candidates and matched_score >= 92.0:
            if CANONICAL_COLON in matcher.normalize_name(matched_name):
                if _has_special_slot_evidence(
                    text,
                    matched_name,
                    matcher,
                    base_known=bool(current_base and _base_name_norm(matched_name, matcher) == current_base),
                    name_profile=name_profile,
                ):
                    scores[matched_name] = max(scores.get(matched_name, -1.0), matched_score)
            elif len(text_compact) >= 3:
                scores[matched_name] = max(scores.get(matched_name, -1.0), matched_score)

        for candidate in candidates:
            candidate_norm = matcher.normalize_name(candidate)
            candidate_compact = candidate_norm.replace(CANONICAL_COLON, "")
            if not candidate_compact:
                continue
            if CANONICAL_COLON in candidate_norm:
                base_known = bool(current_base and _base_name_norm(candidate, matcher) == current_base)
                if _has_special_slot_evidence(text, candidate, matcher, base_known=base_known, name_profile=name_profile):
                    evidence_score = 98.0 if base_known else 94.0
                    scores[candidate] = max(scores.get(candidate, -1.0), evidence_score)
            elif len(text_compact) >= 3 and (text_compact in candidate_compact or candidate_compact in text_compact):
                scores[candidate] = max(scores.get(candidate, -1.0), 90.0 + min(len(text_compact), 8))

    if not scores:
        return "", -1.0
    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    if len(ordered) > 1 and ordered[0][1] - ordered[1][1] < 4.0:
        return "", -1.0
    return ordered[0]


def _slot_short_name_from_texts(
    texts: list[str],
    matcher: NikkeNameMatcher,
    name_profile: str = NAME_PROFILE_DEFAULT,
) -> tuple[str, float]:
    local_names = _local_names(matcher)
    if not local_names:
        return "", -1.0
    compact_to_names: dict[str, list[str]] = {}
    for name in local_names:
        if not _is_short_slot_name_target(name, matcher):
            continue
        compact_to_names.setdefault(_name_compact(name, matcher), []).append(name)

    scores: dict[str, float] = {}
    for raw_text in texts:
        text = _apply_name_profile_aliases(_clean_text(raw_text), name_profile)
        if not text or _is_noise_token(text):
            continue
        compact = _name_compact(text, matcher, name_profile=name_profile)
        names = compact_to_names.get(compact, [])
        if len(names) == 1:
            scores[names[0]] = max(scores.get(names[0], -1.0), 100.0)

    if not scores:
        return "", -1.0
    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    if len(ordered) > 1 and ordered[0][1] == ordered[1][1]:
        return "", -1.0
    return ordered[0]


def _slot_texts(items: list[OCRItem]) -> list[str]:
    texts = [_clean_text(item.text) for item in items if _clean_text(item.text)]
    joined = _items_to_text(items)
    if joined:
        texts.append(joined)
    return texts


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
    precise_name, _ = _slot_precise_name_from_texts(
        [text, *_slot_texts(items)],
        matcher,
        current_name=current_name,
        name_profile=NAME_PROFILE_FHD,
    )
    if precise_name and precise_name != current_name:
        return precise_name
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
    if not current_name:
        return current_name
    current_is_precise = _is_precise_slot_name_target(current_name, matcher)
    if not _has_special_variants(current_name, matcher) and not current_is_precise:
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
        precise_name, _ = _slot_precise_name_from_texts(
            texts,
            matcher,
            current_name=current_name,
            name_profile=name_profile,
        )
        if precise_name and precise_name != current_name:
            return precise_name
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


def _collection_cv_template_dir(template_profile: str = "") -> Path:
    root = _module_data_dir() / "collection_cv_templates" / "v2_manual"
    if template_profile:
        profile_dir = root / "profiles" / template_profile
        if (profile_dir / "manifest.json").exists():
            return profile_dir
    return root


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


@lru_cache(maxsize=4)
def _collection_direct_templates(template_profile: str = "") -> tuple[_CollectionDirectTemplate, ...]:
    template_dir = _collection_cv_template_dir(template_profile)
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


@lru_cache(maxsize=4)
def _collection_direct_negative_templates(template_profile: str = "") -> tuple[_CollectionDirectTemplate, ...]:
    template_dir = _collection_cv_template_dir(template_profile)
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


@lru_cache(maxsize=4)
def _collection_generic_positive_mask(template_profile: str = "") -> np.ndarray | None:
    templates = _collection_direct_templates(template_profile)
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


def _collection_has_positive_evidence(best_score: float, none_score: float | None) -> bool:
    if none_score is None:
        return True
    return best_score - none_score > COLLECTION_DIRECT_PRESENCE_MARGIN


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


def _classify_collection_icon_by_direct_template(
    icon_image: Image.Image,
    template_profile: str = "",
) -> str | None:
    templates = _collection_direct_templates(template_profile)
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
        stats = _collection_visual_stats(rgb, _collection_generic_positive_mask(template_profile))
        if best_score < COLLECTION_DIRECT_SCORE_THRESHOLD or stats["family_max"] < COLLECTION_DIRECT_FAMILY_THRESHOLD:
            return COLLECTION_NONE
        none_score: float | None = None
        negative_templates = _collection_direct_negative_templates(template_profile)
        if negative_templates:
            none_score = max(_collection_direct_score(candidate, template) for template in negative_templates)
            if not _collection_has_positive_evidence(best_score, none_score):
                return COLLECTION_NONE
        label = _postprocess_collection_direct_label(best_label, scores, stats)
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
    client_profile: str = CLIENT_PROFILE_CN,
    row_height: int | None = None,
) -> tuple[_CollectionSlotGeometry, float]:
    if stage_name != STAGE_NAME or match_index not in {1, 2, 3, 4} or block_height is None:
        return geometry, 0.0
    if source_profile == SOURCE_PROFILE_3840:
        profile = COLLECTION_PRECISE_GROUP64_3840
    elif source_profile == SOURCE_PROFILE_2560_1600:
        # The 16:10 capture uses the verified 2560x1440 wide group64 geometry.
        profile = COLLECTION_PRECISE_GROUP64_WIDE
    else:
        profile = (
            COLLECTION_PRECISE_GROUP64_WIDE
            if block_height >= COLLECTION_PRECISE_GROUP64_WIDE_BLOCK_HEIGHT_MIN
            else COLLECTION_PRECISE_GROUP64_FHD
        )
    x_half_key = "attacker_x_half" if side == "attacker" else "defender_x_half"
    dy = profile["top_dy"] if match_index in {1, 2} else profile["bottom_dy"]
    if (
        source_profile == SOURCE_PROFILE_2560_1600
        and _normalize_client_profile(client_profile) == CLIENT_PROFILE_CN
        and row_height
    ):
        # The 16:10 CN stitch has a one-pixel lower icon phase than the wide
        # reference. Keep the crop size intact and only align it vertically.
        dy += 1.0 / max(1, row_height)
    return (
        _CollectionSlotGeometry(
            x_center=geometry.x_center,
            y_center=geometry.y_center,
            x_half=float(profile[x_half_key]),
            y_half=float(profile["y_half"]),
        ),
        float(dy),
    )


def _overseas_collection_grid_profile(source_profile: str, block_height: int) -> dict:
    profile = OVERSEAS_COLLECTION_GRID_BY_SOURCE_PROFILE.get(source_profile)
    if profile is not None and abs(block_height - int(profile["block_height"])) <= 6:
        return profile
    return min(
        (OVERSEAS_COLLECTION_GRID_FHD, OVERSEAS_COLLECTION_GRID_WIDE),
        key=lambda candidate: abs(block_height - int(candidate["block_height"])),
    )


def _overseas_collection_slot_box(
    row_image: Image.Image,
    *,
    side: str,
    team_index: int,
    slot_index: int,
    match_index: int | None,
    block_height: int | None,
    source_profile: str = "",
) -> tuple[int, int, int, int] | None:
    if block_height is None or not 1 <= team_index <= 5 or not 1 <= slot_index <= 5:
        return None
    profile = _overseas_collection_grid_profile(source_profile, block_height)
    reference_row_width = float(profile["row_width"][side])
    scale_x = row_image.width / max(1.0, reference_row_width)
    reference_x0 = float(profile["icon_x0"][side][slot_index - 1])
    phase_dx = float(profile.get("phase_dx", 0.0)) * scale_x
    x0 = round(reference_x0 * scale_x + phase_dx)
    x1 = round((reference_x0 + float(profile["icon_width"])) * scale_x + phase_dx)

    reference_block_height = float(profile["block_height"])
    scale_y = block_height / max(1.0, reference_block_height)
    row_start = int(block_height * (0.275 + (team_index - 1) * 0.13))
    reference_y0 = float(profile["icon_y0"][team_index - 1])
    if match_index in {3, 4}:
        reference_y0 += float(profile["bottom_match_dy"])
    phase_dy = float(profile.get("phase_dy", 0.0)) * scale_y
    y0 = round(reference_y0 * scale_y + phase_dy) - row_start
    y1 = round((reference_y0 + float(profile["icon_height"])) * scale_y + phase_dy) - row_start
    return (
        max(0, min(row_image.width, x0)),
        max(0, min(row_image.height, y0)),
        max(0, min(row_image.width, x1)),
        max(0, min(row_image.height, y1)),
    )


def _classify_collection_icon_by_color(icon_image: Image.Image, preserve_r_level: bool = False) -> str:
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
    return "R15" if preserve_r_level and is_level_15 else "R"


def _classify_collection_icon(icon_image: Image.Image, template_profile: str = "") -> str:
    template_label = _classify_collection_icon_by_direct_template(icon_image, template_profile)
    if template_label is not None and template_label != COLLECTION_NONE:
        return template_label
    if template_profile:
        color_label = _classify_collection_icon_by_color(icon_image, preserve_r_level=True)
        if color_label != COLLECTION_NONE:
            return color_label
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
    client_profile: str = CLIENT_PROFILE_CN,
) -> list[str]:
    levels: list[str] = []
    x_offsets = COLLECTION_ROW_ICON_X_OFFSETS.get(side, COLLECTION_ROW_ICON_X_OFFSETS["attacker"])
    overseas_grid = (
        _overseas_collection_grid_profile(source_profile, block_height)
        if _normalize_client_profile(client_profile) == CLIENT_PROFILE_OVERSEAS and block_height is not None
        else None
    )
    template_profile = str((overseas_grid or {}).get("template_profile", ""))
    for slot in range(slot_count):
        x_offset = x_offsets[min(slot, len(x_offsets) - 1)]
        icon_center = centers[slot] - x_offset
        if _normalize_client_profile(client_profile) == CLIENT_PROFILE_OVERSEAS:
            icon_box = _overseas_collection_slot_box(
                row_image,
                side=side,
                team_index=team_index,
                slot_index=slot + 1,
                match_index=match_index,
                block_height=block_height,
                source_profile=source_profile,
            )
            if icon_box is None or icon_box[2] <= icon_box[0] or icon_box[3] <= icon_box[1]:
                levels.append(COLLECTION_NONE)
                continue
            levels.append(_classify_collection_icon(row_image.crop(icon_box), template_profile))
            continue
        geometry = _collection_slot_geometry(side, team_index, slot + 1, icon_center)
        geometry, dy = _collection_precise_group64_geometry(
            geometry,
            side=side,
            match_index=match_index,
            stage_name=stage_name,
            block_height=block_height,
            source_profile=source_profile,
            client_profile=client_profile,
            row_height=row_image.height,
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

    # On the compact cycle-level strip Paddle occasionally drops the L in Lv
    # but keeps a clear V plus all digits (for example, v381). This remains a
    # bounded level-prefix rule, not a general acceptance of bare numbers.
    for match in re.finditer(r"(?<![A-Za-z])(?:[Ll][Vv]|[Vv])\s*([0-9]{1,3})(?!\d)", normalized):
        value = int(match.group(1))
        if STAT_LEVEL_MIN <= value <= STAT_LEVEL_MAX:
            observations.append(
                _StatLevelObservation(value, max(0.0, min(1.0, float(confidence or 0.0))), True, raw_text, weight)
            )

    if observations:
        return observations

    compact = re.sub(r"\s+", "", normalized)
    malformed_repairs = (
        (r"(?:[Zz2])?6\^7", 97),
        (r"86\^7", 98),
    )
    for pattern, value in malformed_repairs:
        if re.fullmatch(pattern, compact):
            observations.append(
                _StatLevelObservation(value, max(0.0, min(1.0, float(confidence or 0.0))), False, raw_text, weight)
            )
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

    chosen = max(grouped, key=score)
    if chosen in {26, 86} and not any(item.from_lv for item in grouped[chosen]):
        repaired_candidates = [value for value in grouped if 90 <= value <= 99]
        if repaired_candidates:
            return max(repaired_candidates, key=score)
    return chosen


def _is_stat_level_value_trusted(
    value: int | None,
    observations: list[_StatLevelObservation],
) -> bool:
    """Require explicit, high-confidence Lv evidence for unusually high levels."""
    if value is None:
        return False
    if value < STAT_LEVEL_HIGH_VALUE_MIN:
        return True
    return any(
        observation.value == value
        and observation.from_lv
        and observation.confidence >= STAT_LEVEL_HIGH_DIRECT_CONFIDENCE
        for observation in observations
    )


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


def _recognize_stat_level_crop_observations(
    image: Image.Image,
    ocr: ArenaOCRRecognizer,
    region_name: str,
    weight_scale: float = 1.0,
) -> list[_StatLevelObservation]:
    observations: list[_StatLevelObservation] = []
    for index, (variant, weight) in enumerate(_stat_level_preprocess_variants(image), start=1):
        items = ocr.recognize_region(prepare_for_ocr(variant), f"{region_name}_v{index}")
        for item in items:
            observations.extend(
                _stat_level_observations_from_text(item.text, item.confidence, weight=weight * weight_scale)
            )
    return observations


def _recognize_stat_level_crop(
    image: Image.Image,
    ocr: ArenaOCRRecognizer,
    region_name: str,
) -> int | None:
    observations = _recognize_stat_level_crop_observations(image, ocr, region_name)
    return _choose_stat_level(observations)


def _recognize_stat_level_slot_observations(
    side_image: Image.Image,
    left: float,
    right: float,
    ocr: ArenaOCRRecognizer,
    region_name: str,
) -> list[_StatLevelObservation]:
    observations: list[_StatLevelObservation] = []
    for index, (top, bottom, weight) in enumerate(STAT_LEVEL_RECHECK_SLOT_BOXES, start=1):
        slot_image = _crop_rel(side_image, (left, top, right, bottom))
        observations.extend(
            _recognize_stat_level_crop_observations(slot_image, ocr, f"{region_name}_box{index}", weight_scale=weight)
        )
    return observations


def _stat_level_slot_bounds(centers: tuple[float, ...], index: int) -> tuple[float, float]:
    left = 0.0 if index == 0 else (centers[index - 1] + centers[index]) / 2
    right = 1.0 if index == len(centers) - 1 else (centers[index] + centers[index + 1]) / 2
    return max(0.0, left), min(1.0, right)


def _stat_level_merged_item_slots(
    item: OCRItem,
    prepared_width: int,
    centers: tuple[float, ...],
) -> set[int]:
    """Return slots covered by a detector box that contains multiple Lv values."""
    normalized = str(item.text or "").translate(_LEVEL_TRANSLATION)
    if len(re.findall(r"[Ll][Vv]\s*\d{1,3}(?!\d)", normalized)) < 2:
        return set()
    xs = [point[0] for point in item.bbox]
    if not xs:
        return set()
    left = min(xs) / max(1, prepared_width)
    right = max(xs) / max(1, prepared_width)
    return {
        index
        for index, center in enumerate(centers)
        if left - 0.025 <= center <= right + 0.025
    }


def _choose_stat_level_line_confirmation(observations: list[_StatLevelObservation]) -> int | None:
    """Return a conservative consensus from recognition-only numeric line reads."""
    if not observations:
        return None
    grouped: dict[int, list[_StatLevelObservation]] = {}
    for observation in observations:
        grouped.setdefault(observation.value, []).append(observation)

    candidates: list[tuple[int, int, float, float]] = []
    for value, items in grouped.items():
        count = len(items)
        mean_confidence = sum(item.confidence for item in items) / count
        if value >= STAT_LEVEL_HIGH_VALUE_MIN:
            if count < STAT_LEVEL_LINE_HIGH_MIN_VOTES or mean_confidence < STAT_LEVEL_LINE_HIGH_MIN_CONFIDENCE:
                continue
        elif count < STAT_LEVEL_LINE_MIN_VOTES or mean_confidence < STAT_LEVEL_LINE_MIN_CONFIDENCE:
            continue
        candidates.append((value, count, mean_confidence, sum(item.confidence for item in items)))
    if not candidates:
        return None
    return max(candidates, key=lambda item: (item[1], item[2], item[3]))[0]


def _recognize_stat_level_line_confirmations(
    side_image: Image.Image,
    centers: tuple[float, ...],
    indices: set[int],
    ocr: ArenaOCRRecognizer,
    side: str,
) -> dict[int, int]:
    """Batch-read only ambiguous slots from their tightly cropped numeric line."""
    if not indices:
        return {}
    images: list[Image.Image] = []
    names: list[str] = []
    metadata: list[tuple[int, float]] = []
    for index in sorted(indices):
        left, right = _stat_level_slot_bounds(centers, index)
        line_image = _crop_rel(side_image, (left, STAT_LEVEL_LINE_Y0, right, STAT_LEVEL_LINE_Y1))
        for variant_index, (variant, weight) in enumerate(_stat_level_preprocess_variants(line_image), start=1):
            images.append(prepare_for_ocr(variant))
            names.append(f"{side}_stat_level_{index + 1}_line_v{variant_index}")
            metadata.append((index, weight))

    grouped: dict[int, list[_StatLevelObservation]] = {index: [] for index in indices}
    for (index, weight), items in zip(
        metadata,
        ocr.recognize_text_lines(images, names, batch_size=STAT_LEVEL_LINE_BATCH_SIZE),
    ):
        for item in items:
            grouped[index].extend(_stat_level_observations_from_text(item.text, item.confidence, weight=weight))

    return {
        index: confirmed
        for index, observations in grouped.items()
        if (confirmed := _choose_stat_level_line_confirmation(observations)) is not None
    }


def _stat_level_trailing_digit_tail_scores(image: Image.Image, count: int) -> list[float] | None:
    """Return topology scores for the requested rightmost numeric tails."""
    if count < 1:
        return None
    gray = np.asarray(image.convert("L"), dtype=np.uint8)
    if gray.size == 0:
        return None
    height, width = gray.shape[:2]
    if height < 8 or width < 8:
        return None

    # The label and separator sit above the value. Keep only the lower value
    # band, then select one lower tail for each requested trailing digit.
    threshold = max(105, min(165, int(np.percentile(gray, 24))))
    mask = (gray < threshold).astype(np.uint8)
    mask[: int(height * 0.42), :] = 0
    component_count, labels, stats, _centroids = cv2.connectedComponentsWithStats(mask, 8)
    tails: list[tuple[int, int, int, int, int, int]] = []
    min_height = max(4, int(round(height * 0.08)))
    for component_index in range(1, component_count):
        x, y, component_width, component_height, area = (int(value) for value in stats[component_index])
        if x < int(width * 0.18) or y < int(height * 0.55):
            continue
        if component_width > int(width * 0.45) or component_height < min_height or area < 12:
            continue
        tails.append((x, y, component_width, component_height, area, component_index))

    # A rendered 9/6 is split into its upper loop and lower tail. Restricting
    # the candidates to the bottom band leaves one tail per visible digit.
    tails.sort(key=lambda item: item[0])
    if len(tails) < count:
        return None
    tails = tails[-count:]
    if max(item[1] for item in tails) - min(item[1] for item in tails) > max(3, int(round(height * 0.16))):
        return None
    min_gap = max(2, int(round(width * 0.08)))
    if any(right[0] - left[0] < min_gap for left, right in zip(tails, tails[1:])):
        return None

    scores: list[float] = []
    for x, y, component_width, component_height, _area, component_index in tails:
        digit = (labels[y : y + component_height, x : x + component_width] == component_index).astype(np.uint8)
        normalized = cv2.resize(digit, (32, 48), interpolation=cv2.INTER_NEAREST)
        upper_right = float(normalized[6:23, 22:32].mean())
        lower_left = float(normalized[27:44, 0:10].mean())
        scores.append(upper_right - lower_left)
    return scores


def _repair_stat_level_trailing_sixes(
    value: int | None,
    side_image: Image.Image,
    centers: tuple[float, ...],
    index: int,
) -> int | None:
    if value is None:
        return value
    value_text = str(value)
    if not value_text.isdigit() or not value_text.endswith(STAT_LEVEL_MISREAD_DIGIT):
        return value
    trailing_six_count = len(value_text) - len(value_text.rstrip(STAT_LEVEL_MISREAD_DIGIT))
    # Only repair a full trailing 99 that Paddle rendered as at least 66.
    # A lone final 6 is a common legitimate digit (for example Lv116).
    if trailing_six_count < 2:
        return value
    left, right = _stat_level_slot_bounds(centers, index)
    slot_image = _crop_rel(side_image, (left, 0.94, right, 1.0))
    scores = _stat_level_trailing_digit_tail_scores(slot_image, trailing_six_count)
    if not scores:
        return value
    repaired_text = list(value_text)
    tail_start = len(value_text) - trailing_six_count
    for offset, score in enumerate(scores):
        if score >= STAT_LEVEL_NINE_TAIL_SCORE_MIN:
            repaired_text[tail_start + offset] = STAT_LEVEL_CORRECT_DIGIT
    repaired = int("".join(repaired_text))
    if not STAT_LEVEL_MIN <= repaired <= STAT_LEVEL_MAX:
        return value
    return repaired


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
    line_confirmation_indices: set[int] = set()
    forced_slot_recheck_indices: set[int] = set()
    width = max(1, prepared.width)
    for item in items:
        observations = _stat_level_observations_from_text(item.text, item.confidence)
        merged_slots = sorted(_stat_level_merged_item_slots(item, width, centers))
        if merged_slots:
            # A high-resolution detector may combine adjacent values such as
            # "Lv102 Lv139" into one box. The text order still follows the
            # horizontal stat order, while the box center cannot identify an
            # individual slot. Assign exact one-to-one merges directly; for
            # any mismatch, defer to the existing independent slot recheck.
            merged_lv_observations = [observation for observation in observations if observation.from_lv]
            if len(merged_lv_observations) == len(merged_slots):
                for slot, observation in zip(merged_slots, merged_lv_observations):
                    slot_observations[slot].append(observation)
            else:
                forced_slot_recheck_indices.update(merged_slots)
            continue
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
        if not has_lv_source:
            line_confirmation_indices.add(index)
        if (
            index not in forced_slot_recheck_indices
            and
            value is not None
            and has_lv_source
            and value >= STAT_LEVEL_RECHECK_BELOW
            and _is_stat_level_value_trusted(value, slot_observations[index])
        ):
            continue
        left, right = _stat_level_slot_bounds(centers, index)
        slot_recheck_observations = _recognize_stat_level_slot_observations(
            side_image,
            left,
            right,
            ocr,
            f"{side}_stat_level_{index + 1}",
        )
        slot_value = _choose_stat_level(slot_observations[index] + slot_recheck_observations)
        levels[index] = slot_value if _is_stat_level_value_trusted(slot_value, slot_recheck_observations + slot_observations[index]) else None

    line_confirmations = _recognize_stat_level_line_confirmations(
        side_image,
        centers,
        line_confirmation_indices,
        ocr,
        side,
    )
    for index, value in line_confirmations.items():
        current = levels[index]
        # For malformed merged boxes, the wider detector recheck is the
        # primary source. The narrow recognition-only crop can truncate a
        # three-digit value, so use it only when the recheck found nothing.
        if index in forced_slot_recheck_indices and current is not None:
            continue
        if current is None or len(str(value)) >= len(str(current)):
            levels[index] = value

    # Paddle can systematically read a visually distinct trailing 9 as 6.
    # Repair only the affected trailing digits whose lower-tail topology is
    # independently consistent with 9. This covers 66 -> 99, 266 -> 299,
    # 366 -> 399, and 666 -> 999 without altering genuine 6 values.
    for index, value in enumerate(levels):
        levels[index] = _repair_stat_level_trailing_sixes(value, side_image, centers, index)
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


def _power_strip_verify_enabled(ocr: ArenaOCRRecognizer) -> bool:
    mode = os.environ.get("NIKKE_POWER_STRIP_VERIFY", "auto").strip().lower()
    if mode in {"0", "false", "no", "off", "fast"}:
        return False
    if mode in {"1", "true", "yes", "on", "always"}:
        return ocr.engine_name == "paddleocr"
    return ocr.engine_name == "paddleocr"


def _isolate_power_strip(image: Image.Image) -> Image.Image:
    gray = np.asarray(image.convert("L"), dtype=np.uint8)
    if gray.size == 0:
        return image
    height, width = gray.shape[:2]
    mask = ((gray < 185) & (gray > 35)).astype(np.uint8)
    mask[: int(height * 0.35), :] = 0
    mask[int(height * 0.80) :, :] = 0
    row_projection = mask.sum(axis=1)
    active_rows = np.where(row_projection > max(4, int(round(width * 0.025))))[0]
    if active_rows.size == 0:
        return image.crop((0, int(height * 0.38), width, int(height * 0.78)))

    groups: list[tuple[int, int]] = []
    start = previous = int(active_rows[0])
    for row in active_rows[1:]:
        row = int(row)
        if row <= previous + 1:
            previous = row
            continue
        groups.append((start, previous))
        start = previous = row
    groups.append((start, previous))
    best_start, best_end = max(groups, key=lambda item: int(row_projection[item[0] : item[1] + 1].sum()))
    y0 = max(0, best_start - 8)
    y1 = min(height, best_end + 9)
    band_mask = ((gray[y0:y1] < 185) & (gray[y0:y1] > 35)).astype(np.uint8)
    col_projection = band_mask.sum(axis=0)
    active_cols = np.where(col_projection > 0)[0]
    if active_cols.size:
        x0 = max(0, int(active_cols[0]) - 8)
        x1 = min(width, int(active_cols[-1]) + 9)
    else:
        x0, x1 = 0, width
    return image.crop((x0, y0, x1, y1))


def _power_strip_value(items: list[OCRItem]) -> int | None:
    observations: list[_PowerObservation] = []
    for item in items:
        observations.extend(_extract_power_observations_clean(item.text, item.confidence))
    value, _support = _choose_power_observation(observations)
    return value


def _has_valid_power_observation(
    items: list[OCRItem],
    min_confidence: float = SHORT_NAME_POWER_PROBE_MIN_CONFIDENCE,
) -> bool:
    for item in items:
        if float(item.confidence or 0.0) < min_confidence:
            continue
        if _extract_power_observations_clean(item.text, item.confidence):
            return True
    return False


def _probe_power_presence_for_short_name(
    row_image: Image.Image,
    center: float,
    ocr: ArenaOCRRecognizer,
    region_name: str,
) -> bool:
    """Confirm an occupied blank-name slot without exporting its power value."""
    crop = _crop_rel(
        row_image,
        (
            max(0.0, center - POWER_STRIP_CROP_HALF_WIDTH),
            POWER_STRIP_CROP_TOP,
            min(1.0, center + POWER_STRIP_CROP_HALF_WIDTH),
            POWER_STRIP_CROP_BOTTOM,
        ),
    )
    band = _isolate_power_strip(crop)
    variants = [band, prepare_for_ocr(band)]
    names = [f"{region_name}_native", f"{region_name}_prepared"]
    return any(
        _has_valid_power_observation(items)
        for items in ocr.recognize_text_lines(variants, names, batch_size=2)
    )


def _recognize_power_strip_rows(
    row_images: list[Image.Image],
    centers: tuple[float, ...],
    ocr: ArenaOCRRecognizer,
    side: str,
) -> list[list[int | None]]:
    bands: list[Image.Image] = []
    region_names: list[str] = []
    for row_index, row_image in enumerate(row_images, start=1):
        for slot_index, center in enumerate(centers, start=1):
            crop = _crop_rel(
                row_image,
                (
                    max(0.0, center - POWER_STRIP_CROP_HALF_WIDTH),
                    POWER_STRIP_CROP_TOP,
                    min(1.0, center + POWER_STRIP_CROP_HALF_WIDTH),
                    POWER_STRIP_CROP_BOTTOM,
                ),
            )
            bands.append(_isolate_power_strip(crop))
            region_names.append(f"{side}_power_strip_{row_index}_{slot_index}")

    if not bands:
        return []
    native_items = ocr.recognize_text_lines(bands, region_names, batch_size=POWER_STRIP_BATCH_SIZE)
    prepared_bands = [prepare_for_ocr(band) for band in bands]
    prepared_items = ocr.recognize_text_lines(prepared_bands, region_names, batch_size=POWER_STRIP_BATCH_SIZE)
    values: list[int | None] = []
    for native, prepared in zip(native_items, prepared_items):
        native_value = _power_strip_value(native)
        prepared_value = _power_strip_value(prepared)
        values.append(native_value if native_value is not None and native_value == prepared_value else None)
    return [values[index : index + len(centers)] for index in range(0, len(values), len(centers))]


def _merge_power_strip_value(current: int | None, candidate: int | None) -> int | None:
    if candidate is None:
        return current
    if current is None:
        return candidate if len(str(candidate)) >= 6 else None
    if len(str(candidate)) < len(str(current)):
        return current
    return candidate


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


def _power_geometry_vote_from_observations(
    observations: list[_PowerObservation],
    geometry_id: str,
) -> _PowerGeometryVote | None:
    """Return one high-confidence five-digit vote from a physical crop.

    Preprocessing variants of the same crop are correlated evidence. They may
    pick the sharpest candidate for this crop, but never contribute multiple
    votes to the later cross-crop consensus.
    """
    if not geometry_id:
        return None
    grouped: dict[int, list[_PowerObservation]] = {}
    for item in observations:
        if MIN_CARD_POWER <= item.value <= MAX_CARD_POWER and len(str(item.value)) == 5:
            grouped.setdefault(item.value, []).append(item)
    if not grouped:
        return None

    def quality(item: _PowerObservation) -> float:
        return (
            max(0.0, min(1.0, item.confidence))
            + (0.05 if item.anchored else 0.0)
            - (0.12 if item.trailing_marker else 0.0)
            - item.distance * 0.10
        )

    representatives = {
        value: max(items, key=quality)
        for value, items in grouped.items()
    }
    ranked = sorted(representatives.items(), key=lambda pair: quality(pair[1]), reverse=True)
    value, best = ranked[0]
    if best.confidence < POWER_GEOMETRY_STRONG_CONFIDENCE:
        return None
    if len(ranked) > 1:
        runner_up = ranked[1][1]
        if (
            runner_up.confidence >= POWER_GEOMETRY_STRONG_CONFIDENCE
            and quality(best) - quality(runner_up) < 0.02
        ):
            return None
    return _PowerGeometryVote(
        geometry_id=geometry_id,
        value=value,
        confidence=best.confidence,
        anchored=best.anchored,
        trailing_marker=best.trailing_marker,
    )


def _resolve_power_geometry_consensus(
    current_value: int | None,
    current_support: float,
    votes: list[_PowerGeometryVote],
) -> tuple[int | None, float]:
    """Override a conflicted five-digit result only with strong crop consensus."""
    if current_value is None or len(str(current_value)) != 5:
        return current_value, current_support
    grouped: dict[int, dict[str, _PowerGeometryVote]] = {}
    for vote in votes:
        grouped.setdefault(vote.value, {})[vote.geometry_id] = vote
    current_count = len(grouped.get(current_value, {}))
    alternatives = [
        (value, list(by_geometry.values()))
        for value, by_geometry in grouped.items()
        if value != current_value
        and len(by_geometry) >= POWER_GEOMETRY_MIN_STRONG_VOTES
        and len(by_geometry) >= current_count + POWER_GEOMETRY_MIN_VOTE_LEAD
    ]
    if not alternatives:
        return current_value, current_support

    replacement, replacement_votes = max(
        alternatives,
        key=lambda item: (
            len(item[1]),
            sum(vote.confidence for vote in item[1]),
            sum(1 for vote in item[1] if vote.anchored),
            -sum(1 for vote in item[1] if vote.trailing_marker),
        ),
    )
    return replacement, max(current_support, POWER_TIGHT_RECHECK_SUPPORT)


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
    geometry_id: str = "",
    geometry_votes: list[_PowerGeometryVote] | None = None,
) -> tuple[int | None, float]:
    observations: list[_PowerObservation] = []
    early_observations: list[_PowerObservation] = []
    crop_width = max(0.0001, crop_right - crop_left)

    def finish(value: int | None, support: float) -> tuple[int | None, float]:
        if geometry_votes is not None:
            vote = _power_geometry_vote_from_observations(observations, geometry_id)
            if vote is not None:
                geometry_votes.append(vote)
        return value, support

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
                    return finish(value, STRONG_POWER_RECHECK_SUPPORT)
        chosen, support = _choose_power_observation(observations)
        if early_stop and _is_confident_power_candidate(chosen) and support >= STRONG_POWER_RECHECK_SUPPORT:
            return finish(chosen, support)
    value, support = _choose_power_observation(observations)
    return finish(value, support)


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
        geometry_votes: list[_PowerGeometryVote],
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
                geometry_id=f"{suffix}{index}",
                geometry_votes=geometry_votes,
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

    tight_geometry_votes: list[_PowerGeometryVote] = []
    tight_value, tight_support = scan_boxes(tight_boxes, "tight", observations, tight_geometry_votes)
    tight_value, tight_support = _resolve_power_geometry_consensus(
        tight_value,
        tight_support,
        tight_geometry_votes,
    )
    if _is_confident_power_candidate(tight_value) and tight_support >= POWER_TIGHT_RECHECK_SUPPORT:
        return tight_value, tight_support

    active_wide_boxes = wide_boxes[: max(1, max_boxes)] if max_boxes is not None else wide_boxes
    wide_geometry_votes: list[_PowerGeometryVote] = []
    scan_boxes(active_wide_boxes, "box", observations, wide_geometry_votes)
    value, support = _choose_power_observation(observations)
    return _resolve_power_geometry_consensus(
        value,
        support,
        tight_geometry_votes + wide_geometry_votes,
    )


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
    client_profile: str = CLIENT_PROFILE_CN,
) -> tuple[list[list[str]], list[list[int | None]], list[list[str]]]:
    teams: list[list[str]] = []
    powers: list[list[int | None]] = []
    collections: list[list[str]] = []
    centers = ATTACKER_CARD_SLOT_CENTERS if side == "attacker" else DEFENDER_CARD_SLOT_CENTERS
    power_centers = ATTACKER_POWER_SLOT_CENTERS if side == "attacker" else DEFENDER_POWER_SLOT_CENTERS
    power_mode = _power_ocr_mode()
    name_profile = _name_profile_from_block_height(block_height)
    power_strip_enabled = include_power and _power_strip_verify_enabled(ocr)
    power_strip_rows: list[Image.Image] = []

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
        if power_strip_enabled:
            power_strip_rows.append(row_image)
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
                client_profile=client_profile,
            )
            if include_collection
            else [COLLECTION_NONE] * 5
        )
        if include_power:
            power_readings = _match_power_slot_readings(items, prepared.width, prepared.height, row_power_centers)
            power_slots = [reading.value for reading in power_readings]
            power_presence_slots = [
                value is not None and MIN_CARD_POWER <= int(value) <= MAX_CARD_POWER
                for value in power_slots
            ]
        else:
            power_readings = [_PowerSlotReading() for _ in range(5)]
            power_slots = [None] * 5
            # The row OCR has already run for names. Reuse any power numbers it
            # detected as occupancy evidence without enabling power export.
            presence_readings = _match_power_slot_readings(
                items,
                prepared.width,
                prepared.height,
                row_power_centers,
            )
            power_presence_slots = [
                reading.value is not None and MIN_CARD_POWER <= int(reading.value) <= MAX_CARD_POWER
                for reading in presence_readings
            ]

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
            slot_has_power = power_presence_slots[slot]
            fallback_texts = _slot_texts(card_items)
            if not card_name and slot_has_power:
                card_name, _ = _slot_precise_name_from_texts(
                    fallback_texts,
                    matcher,
                    current_name="",
                    name_profile=name_profile,
                )
            if not card_name and slot_has_power:
                card_name, _ = _slot_short_name_from_texts(
                    fallback_texts,
                    matcher,
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
                fallback_texts.extend(_slot_texts(label_items))
                card_name, _, _ = _best_positioned_character_match(
                    label_items,
                    matcher,
                    prepared_label,
                    name_profile=name_profile,
                )
                if not card_name and slot_has_power:
                    card_name, _ = _slot_precise_name_from_texts(
                        _slot_texts(label_items),
                        matcher,
                        current_name="",
                        name_profile=name_profile,
                    )
                if not card_name and slot_has_power:
                    card_name, _ = _slot_short_name_from_texts(
                        _slot_texts(label_items),
                        matcher,
                        name_profile=name_profile,
                    )
            if not card_name and not include_power and not slot_has_power:
                slot_has_power = _probe_power_presence_for_short_name(
                    row_image,
                    row_power_centers[slot],
                    ocr,
                    f"team_row_{row + 1}_slot_{slot + 1}_short_name_power_probe",
                )
                power_presence_slots[slot] = slot_has_power
            if not card_name and not include_power and slot_has_power:
                card_name, _ = _slot_precise_name_from_texts(
                    fallback_texts,
                    matcher,
                    current_name="",
                    name_profile=name_profile,
                )
            if not card_name and not include_power and slot_has_power:
                card_name, _ = _slot_short_name_from_texts(
                    fallback_texts,
                    matcher,
                    name_profile=name_profile,
                )
            if card_name:
                slots[slot] = card_name

        for slot in range(5):
            if not slots[slot]:
                continue
            if not _has_special_variants(slots[slot], matcher) and not _is_precise_slot_name_target(slots[slot], matcher):
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
    if power_strip_enabled:
        strip_rows = _recognize_power_strip_rows(power_strip_rows, power_centers, ocr, side)
        for row_index, strip_slots in enumerate(strip_rows):
            if row_index >= len(powers):
                break
            for slot_index, candidate in enumerate(strip_slots):
                if slot_index >= len(powers[row_index]):
                    break
                powers[row_index][slot_index] = _merge_power_strip_value(powers[row_index][slot_index], candidate)
    return teams, powers, collections


def _detail_item_bounds(item: OCRItem) -> tuple[float, float, float, float] | None:
    xs = [point[0] for point in item.bbox]
    ys = [point[1] for point in item.bbox]
    if not xs or not ys:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def _detail_joined_name_candidates(items: list[tuple[OCRItem, str]]) -> list[str]:
    positioned: list[tuple[float, float, float, float, str]] = []
    for item, text in items:
        bounds = _detail_item_bounds(item)
        if bounds is None:
            continue
        x0, y0, x1, y1 = bounds
        positioned.append((x0, y0, x1, y1, text))
    positioned.sort(key=lambda value: (value[0], value[1]))

    joined: list[str] = []

    def extend(chain: list[int]) -> None:
        if len(chain) >= 2:
            value = "".join(positioned[index][4] for index in chain)
            if 3 <= len(value) <= 20 and value not in joined:
                joined.append(value)
        if len(chain) >= 3:
            return
        last_index = chain[-1]
        _lx0, ly0, lx1, ly1, _last_text = positioned[last_index]
        last_height = max(1.0, ly1 - ly0)
        last_center_y = (ly0 + ly1) / 2
        for next_index in range(last_index + 1, len(positioned)):
            nx0, ny0, nx1, ny1, _next_text = positioned[next_index]
            next_height = max(1.0, ny1 - ny0)
            next_center_y = (ny0 + ny1) / 2
            gap = nx0 - lx1
            if gap > max(last_height, next_height) * 1.4:
                break
            if gap < -max(last_height, next_height) * 0.80:
                continue
            if abs(next_center_y - last_center_y) > max(last_height, next_height) * 0.45:
                continue
            extend(chain + [next_index])

    for index in range(len(positioned)):
        extend([index])
    return joined


def _joined_special_name_from_fragments(
    texts: list[str],
    current_name: str,
    matcher: NikkeNameMatcher,
    name_profile: str,
) -> tuple[str, float]:
    precise_name, precise_score = _slot_precise_name_from_texts(
        texts,
        matcher,
        current_name=current_name,
        name_profile=name_profile,
    )
    if precise_name:
        return precise_name, precise_score

    current_base = _base_name_norm(current_name, matcher) if current_name else ""
    best_name = ""
    best_score = -1.0
    for text in texts:
        candidate, score = _best_character_match(text, matcher, name_profile=name_profile)
        candidate_norm = matcher.normalize_name(candidate)
        if not candidate or CANONICAL_COLON not in candidate_norm or score < 90.0:
            continue
        candidate_base, candidate_suffix = candidate_norm.split(CANONICAL_COLON, 1)
        if current_base and candidate_base != current_base:
            continue
        text_norm = matcher.normalize_name(_apply_name_profile_aliases(_clean_text(text), name_profile))
        text_compact = text_norm.replace(CANONICAL_COLON, "")
        base_compact = candidate_base.replace(CANONICAL_COLON, "")
        suffix_compact = candidate_suffix.replace(CANONICAL_COLON, "")
        suffix_evidence = text_compact[len(base_compact) :] if text_compact.startswith(base_compact) else text_compact
        has_evidence = any(
            suffix_compact[start : start + 2] in suffix_evidence
            for start in range(max(0, len(suffix_compact) - 1))
        )
        if not has_evidence:
            continue
        if score > best_score:
            best_name = candidate
            best_score = score
    return best_name, best_score


def _match_detail_team_slots(
    items: list[OCRItem],
    matcher: NikkeNameMatcher,
    image_width: int,
    image_height: int,
    name_profile: str = NAME_PROFILE_DEFAULT,
    slot_boxes: tuple[list[tuple[float, float, float, float] | None], list[tuple[float, float, float, float] | None]]
    | None = None,
    merge_adjacent_name_fragments: bool = False,
) -> tuple[list[str], list[str], list[float], list[float]]:
    teams = [[""] * 5, [""] * 5]
    scores = [[-1.0] * 5, [-1.0] * 5]
    slot_text_items: list[list[list[tuple[OCRItem, str]]]] = [
        [[] for _ in range(5)],
        [[] for _ in range(5)],
    ]
    width = max(1, image_width)
    height = max(1, image_height)
    for item in items:
        text = _clean_text(item.text)
        if _is_noise_token(text) or not re.search(r"[\u4e00-\u9fffA-Za-z]", text):
            continue
        xs = [point[0] for point in item.bbox]
        ys = [point[1] for point in item.bbox]
        if not xs or not ys:
            continue
        x_ratio = (sum(xs) / len(xs)) / width
        y_ratio = (sum(ys) / len(ys)) / height
        conditional_top_slot = False
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
            if y_ratio < DETAIL_NAME_HARD_TOP_Y or 0.46 <= x_ratio <= 0.54:
                continue
            slot = min(range(5), key=lambda index: abs(y_ratio - DETAIL_SLOT_CENTERS[index]))
            if abs(y_ratio - DETAIL_SLOT_CENTERS[slot]) > 0.055:
                continue
            side = 0 if x_ratio < 0.5 else 1
            conditional_top_slot = y_ratio < DETAIL_NAME_CONDITIONAL_TOP_Y
            if conditional_top_slot and slot != 0:
                continue

        fragment_text = str(item.text or "").strip().strip(" |/\\") or text
        slot_text_items[side][slot].append((item, fragment_text))

        name, match_score = _best_character_match(text, matcher, name_profile=name_profile)
        if not name or name == "unknown" or match_score < matcher.threshold:
            precise_name, precise_score = _slot_precise_name_from_texts(
                [text],
                matcher,
                current_name="",
                name_profile=name_profile,
            )
            if precise_name:
                name = precise_name
                match_score = precise_score
            else:
                short_name, short_score = _slot_short_name_from_texts(
                    [text],
                    matcher,
                    name_profile=name_profile,
                )
                if not short_name:
                    continue
                name = short_name
                match_score = short_score
        if conditional_top_slot and (
            match_score < matcher.threshold or (matcher.names and name not in matcher.names)
        ):
            continue
        combined_score = match_score + max(0.0, min(1.0, item.confidence)) * 2.0
        if combined_score > scores[side][slot]:
            teams[side][slot] = name
            scores[side][slot] = combined_score

    if merge_adjacent_name_fragments:
        for side in range(2):
            for slot in range(5):
                joined_texts = _detail_joined_name_candidates(slot_text_items[side][slot])
                if not joined_texts:
                    continue
                joined_name, joined_score = _joined_special_name_from_fragments(
                    joined_texts,
                    teams[side][slot],
                    matcher,
                    name_profile,
                )
                if not joined_name:
                    continue
                current_norm = matcher.normalize_name(teams[side][slot])
                joined_norm = matcher.normalize_name(joined_name)
                if current_norm and _base_name_norm(current_norm, matcher) != _base_name_norm(joined_norm, matcher):
                    continue
                if current_norm and len(joined_norm) <= len(current_norm):
                    continue
                teams[side][slot] = joined_name
                scores[side][slot] = max(scores[side][slot], joined_score + 2.0)
    return teams[0], teams[1], scores[0], scores[1]


def _detail_round_crop(
    center_image: Image.Image,
    row: int,
) -> tuple[Image.Image, tuple[float, float, float, float]]:
    center_size = tuple(float(value) for value in center_image.size)
    rel_box = (0.0, row / 5, 1.0, (row + 1) / 5)
    return _crop_rel(center_image, rel_box), _box_rel_to_abs((0.0, 0.0), center_size, rel_box)


def _detailed_result_panel_image(
    match_image: Image.Image,
    client_profile: str = CLIENT_PROFILE_CN,
) -> Image.Image:
    panel_x = (
        OVERSEAS_DETAILED_RESULT_PANEL_X
        if _normalize_client_profile(client_profile) == CLIENT_PROFILE_OVERSEAS
        else DETAILED_RESULT_PANEL_X
    )
    return _crop_rel(match_image, (panel_x[0], 0.0, panel_x[1], 1.0))


def _detail_name_image(
    match_image: Image.Image,
    legacy_center_image: Image.Image,
    result_mode: str,
    client_profile: str,
) -> Image.Image:
    """Keep profile-specific crops separate while sharing name OCR logic."""
    if (
        result_mode == RESULT_MODE_DETAILED
        and _normalize_client_profile(client_profile) == CLIENT_PROFILE_OVERSEAS
    ):
        return _detailed_result_panel_image(match_image, client_profile=CLIENT_PROFILE_OVERSEAS)
    return legacy_center_image


def _source_resolution_key(source_name: str) -> str:
    normalized = str(source_name or "").replace("×", "x")
    match = re.search(r"(?<!\d)(\d{4})\s*[xX]\s*(\d{4})(?!\d)", normalized)
    if not match:
        return ""
    return f"{match.group(1)}x{match.group(2)}"


def _apply_scoped_detail_name_aliases(
    items: list[OCRItem],
    client_profile: str,
    source_name: str,
) -> list[OCRItem]:
    if _normalize_client_profile(client_profile) != CLIENT_PROFILE_CN:
        return items
    aliases = CN_DETAIL_NAME_TEXT_ALIASES_BY_RESOLUTION.get(_source_resolution_key(source_name), ())
    if not aliases:
        return items

    mapped: list[OCRItem] = []
    for item in items:
        cleaned = _clean_text(item.text)
        replacement = next((correct for wrong, correct in aliases if cleaned == wrong), "")
        if not replacement:
            mapped.append(item)
            continue
        mapped.append(
            OCRItem(
                text=replacement,
                bbox=list(item.bbox),
                confidence=item.confidence,
                region_name=item.region_name,
            )
        )
    return mapped


def recognize_detail_team_rows(
    center_image: Image.Image,
    ocr: ArenaOCRRecognizer,
    matcher: NikkeNameMatcher,
    block_height: int | None = None,
    client_profile: str = CLIENT_PROFILE_CN,
    source_name: str = "",
) -> tuple[list[list[str]], list[list[str]], list[list[float]], list[list[float]], list[list[OCRItem]]]:
    attacker_rows: list[list[str]] = []
    defender_rows: list[list[str]] = []
    attacker_scores: list[list[float]] = []
    defender_scores: list[list[float]] = []
    round_items: list[list[OCRItem]] = []
    name_profile = _name_profile_from_block_height(block_height)
    # Paddle can split one displayed Nikke name into overlapping text boxes at
    # any resolution or client profile. Rejoining already detected boxes is a
    # geometry-only post-process and does not add OCR calls.
    merge_adjacent_name_fragments = True

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
        items = _apply_scoped_detail_name_aliases(items, client_profile, source_name)
        attacker, defender, attacker_score, defender_score = _match_detail_team_slots(
            items,
            matcher,
            prepared.width,
            prepared.height,
            name_profile=name_profile,
            merge_adjacent_name_fragments=merge_adjacent_name_fragments,
        )
        if name_profile == NAME_PROFILE_FHD and ("" in attacker or "" in defender):
            upscaled = round_image.resize((round_image.width * 3, round_image.height * 3), Image.Resampling.LANCZOS)
            extra_items = ocr.recognize_region(upscaled, f"detail_round_{row + 1}_fhd_up3")
            extra_items = _apply_scoped_detail_name_aliases(extra_items, client_profile, source_name)
            extra_attacker, extra_defender, extra_attacker_score, extra_defender_score = _match_detail_team_slots(
                extra_items,
                matcher,
                upscaled.width,
                upscaled.height,
                name_profile=name_profile,
                merge_adjacent_name_fragments=merge_adjacent_name_fragments,
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


def _detail_hp_slot_bounds(index: int) -> tuple[float, float]:
    center = DETAIL_HP_SLOT_CENTERS[index]
    top = 0.0 if index == 0 else (DETAIL_HP_SLOT_CENTERS[index - 1] + center) / 2
    bottom = 1.0 if index == len(DETAIL_HP_SLOT_CENTERS) - 1 else (center + DETAIL_HP_SLOT_CENTERS[index + 1]) / 2
    return max(0.0, top), min(1.0, bottom)


def _detail_hp_slot_from_y_ratio(y_ratio: float) -> int | None:
    for index, center in enumerate(DETAIL_HP_SLOT_CENTERS):
        top, bottom = _detail_hp_slot_bounds(index)
        if top <= y_ratio <= bottom:
            return index
    return None


@lru_cache(maxsize=1)
def _defeat_text_template_image() -> Image.Image:
    rows: list[list[int]] = []
    for row in DETAILED_DEFEAT_TEXT_TEMPLATE_HEX_ROWS:
        bits = bin(int(row, 16))[2:].zfill(72)
        rows.append([255 if bit == "1" else 0 for bit in bits])
    return Image.fromarray(np.asarray(rows, dtype=np.uint8), mode="L").convert("RGB")


def _defeat_template_binary(image: Image.Image) -> np.ndarray:
    rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    _threshold, binary = cv2.threshold(gray, 72, 255, cv2.THRESH_BINARY)
    return binary


@lru_cache(maxsize=1)
def _overseas_defeat_label_templates() -> tuple[np.ndarray, ...]:
    template_dir = _module_data_dir() / "defeat_templates" / "overseas"
    templates: list[np.ndarray] = []
    for file_name in OVERSEAS_DEFEAT_TEMPLATE_FILES:
        path = template_dir / file_name
        if not path.is_file():
            continue
        try:
            with Image.open(path) as image:
                templates.append(np.asarray(image.convert("L"), dtype=np.uint8))
        except (OSError, ValueError):
            continue
    return tuple(templates)


def _overseas_defeat_template_score(crop: Image.Image) -> float:
    if crop.width < 8 or crop.height < 8:
        return 0.0
    source = np.asarray(crop.convert("L"), dtype=np.uint8)
    best_score = 0.0
    for template in _overseas_defeat_label_templates():
        for scale in np.linspace(0.80, 1.20, 17):
            width = max(4, int(round(template.shape[1] * scale)))
            height = max(4, int(round(template.shape[0] * scale)))
            if width > source.shape[1] or height > source.shape[0]:
                continue
            scaled = cv2.resize(template, (width, height), interpolation=cv2.INTER_AREA)
            score = float(cv2.minMaxLoc(cv2.matchTemplate(source, scaled, cv2.TM_CCOEFF_NORMED))[1])
            best_score = max(best_score, score)
    return best_score


def _defeat_template_score(crop: Image.Image) -> float:
    if crop.width < 8 or crop.height < 8:
        return 0.0
    source = _defeat_template_binary(crop)
    template = _defeat_template_binary(_defeat_text_template_image())
    best_score = 0.0
    for scale in np.linspace(0.32, 1.35, 42):
        width = max(4, int(round(template.shape[1] * scale)))
        height = max(4, int(round(template.shape[0] * scale)))
        if width > source.shape[1] or height > source.shape[0]:
            continue
        scaled = cv2.resize(template, (width, height), interpolation=cv2.INTER_AREA)
        if np.count_nonzero(scaled) < 5:
            continue
        score = float(cv2.minMaxLoc(cv2.matchTemplate(source, scaled, cv2.TM_CCOEFF_NORMED))[1])
        best_score = max(best_score, score)
    return best_score


def _is_defeat_sticker_visual(crop: Image.Image, client_profile: str = CLIENT_PROFILE_CN) -> bool:
    if _normalize_client_profile(client_profile) == CLIENT_PROFILE_OVERSEAS:
        return _overseas_defeat_template_score(crop) >= OVERSEAS_DEFEAT_TEMPLATE_THRESHOLD
    return _defeat_template_score(crop) >= DETAILED_DEFEAT_TEMPLATE_THRESHOLD


def _contains_defeat_sticker_visual(crop: Image.Image, client_profile: str = CLIENT_PROFILE_CN) -> bool:
    if _is_defeat_sticker_visual(crop, client_profile=client_profile):
        return True
    if crop.width < 16 or crop.height < 20:
        return False
    width = crop.width
    height = crop.height
    window_specs = (
        (0.34, 0.62),
        (0.46, 0.72),
        (0.58, 0.84),
    )
    for width_ratio, height_ratio in window_specs:
        win_w = max(12, min(width, int(round(width * width_ratio))))
        win_h = max(18, min(height, int(round(height * height_ratio))))
        if win_w >= width and win_h >= height:
            continue
        x_steps = 4 if width > win_w else 1
        y_steps = 3 if height > win_h else 1
        for xi in range(x_steps):
            x0 = 0 if x_steps == 1 else int(round((width - win_w) * xi / (x_steps - 1)))
            for yi in range(y_steps):
                y0 = 0 if y_steps == 1 else int(round((height - win_h) * yi / (y_steps - 1)))
                if _is_defeat_sticker_visual(
                    crop.crop((x0, y0, x0 + win_w, y0 + win_h)),
                    client_profile=client_profile,
                ):
                    return True
    return False


def _detail_defeat_x_ranges(side: str) -> tuple[tuple[float, float], ...]:
    if side == "attacker":
        return (
            DETAILED_RESULT_LEFT_PORTRAIT_X,
            (0.00, 0.24),
            (0.12, 0.36),
        )
    return (
        DETAILED_RESULT_RIGHT_PORTRAIT_X,
        (0.64, 0.88),
        (0.76, 1.00),
    )


def _detect_detail_visual_defeat_slots(
    round_image: Image.Image,
    side: str,
    defeat_boxes: list[tuple[float, float, float, float] | None] | None = None,
    client_profile: str = CLIENT_PROFILE_CN,
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
            flags.append(
                _is_defeat_sticker_visual(
                    round_image.crop((x0, y0, x1, y1)),
                    client_profile=client_profile,
                )
            )
        return flags

    x0_ratio, x1_ratio = DETAILED_DEFEAT_STICKER_X[side]
    flags: list[bool] = []
    for crop_top, crop_bottom in DETAILED_DEFEAT_STICKER_Y:
        crop = _crop_rel(round_image, (x0_ratio, crop_top, x1_ratio, crop_bottom))
        flags.append(_is_defeat_sticker_visual(crop, client_profile=client_profile))
    return flags


def _detect_detail_visual_defeat_slots_from_panel(
    panel_image: Image.Image,
    row: int,
    side: str,
    client_profile: str = CLIENT_PROFILE_CN,
    slot_boxes: tuple[tuple[float, float, float, float], ...] | None = None,
) -> list[bool]:
    if slot_boxes is not None:
        flags: list[bool] = []
        for x0, y0, x1, y1 in slot_boxes:
            crop_box = (
                max(0, min(panel_image.width, int(round(x0)))),
                max(0, min(panel_image.height, int(round(y0)))),
                max(0, min(panel_image.width, int(round(x1)))),
                max(0, min(panel_image.height, int(round(y1)))),
            )
            if crop_box[2] <= crop_box[0] or crop_box[3] <= crop_box[1]:
                flags.append(False)
                continue
            crop = panel_image.crop(crop_box)
            if _normalize_client_profile(client_profile) == CLIENT_PROFILE_OVERSEAS:
                flags.append(
                    _overseas_defeat_template_score(crop)
                    >= OVERSEAS_PRECISE_DEFEAT_TEMPLATE_THRESHOLD
                )
            else:
                flags.append(_is_defeat_sticker_visual(crop, client_profile=client_profile))
        return flags

    is_overseas = _normalize_client_profile(client_profile) == CLIENT_PROFILE_OVERSEAS
    x_ranges = OVERSEAS_DEFEAT_STICKER_X if is_overseas else DETAILED_DEFEAT_STICKER_X
    y_ranges = OVERSEAS_DEFEAT_STICKER_Y_BY_ROUND if is_overseas else DETAILED_DEFEAT_STICKER_Y_BY_ROUND
    x0_ratio, x1_ratio = x_ranges[side]
    flags: list[bool] = []
    for crop_top, crop_bottom in y_ranges[row]:
        crop = _crop_rel(panel_image, (x0_ratio, crop_top, x1_ratio, crop_bottom))
        flags.append(_is_defeat_sticker_visual(crop, client_profile=client_profile))
    return flags


def _winner_from_detail_defeat_flags(
    attacker_flags: list[bool],
    defender_flags: list[bool],
    client_profile: str = CLIENT_PROFILE_CN,
    allow_empty_defeat_flags: bool = False,
) -> tuple[str, float]:
    """Resolve a detailed result by survivor count before considering HP.

    A defeated-sticker flag represents one eliminated Nikke. More surviving
    Nikkes always wins. China does not display the per-Nikke HP percentage, so
    a survivor-count tie there follows the game's defender-advantage rule.
    Overseas ties are deliberately returned as unknown for the caller to
    resolve from complete per-slot HP readings.
    """
    attacker_defeats = sum(bool(value) for value in attacker_flags)
    defender_defeats = sum(bool(value) for value in defender_flags)
    total_slots = len(DETAIL_SLOT_CENTERS)
    if not allow_empty_defeat_flags and attacker_defeats + defender_defeats == 0:
        return "unknown", 0.0
    if attacker_defeats > defender_defeats:
        return "defender", 0.96
    if defender_defeats > attacker_defeats:
        return "attacker", 0.96

    attacker_survivors = total_slots - attacker_defeats
    defender_survivors = total_slots - defender_defeats
    if attacker_survivors != defender_survivors:
        return ("attacker", 0.96) if attacker_survivors > defender_survivors else ("defender", 0.96)
    if _normalize_client_profile(client_profile) == CLIENT_PROFILE_CN:
        return "defender", 0.90
    return "unknown", 0.55


def _detail_defeat_flags_from_panel(
    panel_image: Image.Image,
    row: int,
    client_profile: str = CLIENT_PROFILE_CN,
    precise_boxes: dict[str, tuple[tuple[tuple[float, float, float, float], ...], ...]] | None = None,
) -> tuple[list[bool], list[bool]]:
    attacker_flags = _detect_detail_visual_defeat_slots_from_panel(
        panel_image,
        row,
        "attacker",
        client_profile=client_profile,
        slot_boxes=precise_boxes["attacker"][row] if precise_boxes is not None else None,
    )
    defender_flags = _detect_detail_visual_defeat_slots_from_panel(
        panel_image,
        row,
        "defender",
        client_profile=client_profile,
        slot_boxes=precise_boxes["defender"][row] if precise_boxes is not None else None,
    )
    return attacker_flags, defender_flags


def _detect_round_winner_by_detailed_defeat_panel(
    panel_image: Image.Image,
    row: int,
    client_profile: str = CLIENT_PROFILE_CN,
) -> tuple[str, float]:
    attacker_flags, defender_flags = _detail_defeat_flags_from_panel(
        panel_image,
        row,
        client_profile=client_profile,
    )
    return _winner_from_detail_defeat_flags(
        attacker_flags,
        defender_flags,
        client_profile=client_profile,
        allow_empty_defeat_flags=True,
    )


def _detect_detail_text_defeat_slots(
    round_image: Image.Image,
    items: list[OCRItem],
    defeat_boxes: dict[str, list[tuple[float, float, float, float] | None]] | None = None,
    client_profile: str = CLIENT_PROFILE_CN,
) -> dict[str, list[bool]]:
    coord_size = _ocr_coordinate_size(items, round_image)
    flags = {
        "attacker": [False] * len(DETAIL_SLOT_CENTERS),
        "defender": [False] * len(DETAIL_SLOT_CENTERS),
    }
    for item in items:
        if not _is_defeat_result_text(item.text, client_profile=client_profile):
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


def _is_defeat_result_text(text: str, client_profile: str = CLIENT_PROFILE_CN) -> bool:
    raw_text = str(text or "")
    if any(token in raw_text for token in ("\u6218\u8d25", "\u6230\u6557")):
        return True
    compact_text = re.sub(r"\s+", "", raw_text).upper()
    return (
        _normalize_client_profile(client_profile) == CLIENT_PROFILE_OVERSEAS
        and "DISCONNECT" in compact_text
    )


def _detect_round_winner_by_detailed_defeat(
    round_image: Image.Image,
    items: list[OCRItem] | None = None,
    defeat_boxes: dict[str, list[tuple[float, float, float, float] | None]] | None = None,
    client_profile: str = CLIENT_PROFILE_CN,
) -> tuple[str, float]:
    if items is None:
        items = []
    text_flags = _detect_detail_text_defeat_slots(
        round_image,
        items,
        defeat_boxes=defeat_boxes,
        client_profile=client_profile,
    )
    attacker_defeat_boxes = defeat_boxes.get("attacker") if defeat_boxes else None
    defender_defeat_boxes = defeat_boxes.get("defender") if defeat_boxes else None
    attacker_visual_flags = _detect_detail_visual_defeat_slots(
        round_image,
        "attacker",
        defeat_boxes=attacker_defeat_boxes,
        client_profile=client_profile,
    )
    defender_visual_flags = _detect_detail_visual_defeat_slots(
        round_image,
        "defender",
        defeat_boxes=defender_defeat_boxes,
        client_profile=client_profile,
    )
    if sum(attacker_visual_flags) >= DETAILED_DEFEAT_STRICT_COUNT and sum(defender_visual_flags) >= DETAILED_DEFEAT_STRICT_COUNT:
        attacker_visual_flags = [False] * len(DETAIL_SLOT_CENTERS)
        defender_visual_flags = [False] * len(DETAIL_SLOT_CENTERS)
    attacker_flags = [
        visual or text
        for visual, text in zip(attacker_visual_flags, text_flags["attacker"])
    ]
    defender_flags = [
        visual or text
        for visual, text in zip(defender_visual_flags, text_flags["defender"])
    ]
    return _winner_from_detail_defeat_flags(
        attacker_flags,
        defender_flags,
        client_profile=client_profile,
        allow_empty_defeat_flags=False,
    )


def _detect_round_winner_by_text(
    round_image: Image.Image,
    ocr: ArenaOCRRecognizer,
    items: list[OCRItem] | None = None,
    client_profile: str = CLIENT_PROFILE_CN,
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
        if _is_defeat_result_text(item.text, client_profile=client_profile) or "LOSE" in text:
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


def _parse_detail_hp_percent(text: str) -> float | None:
    compact = str(text or "").replace(" ", "")
    match = re.search(r"(?<!\d)(\d{1,3}(?:[.,]\d{1,2})?)\s*[%％]", compact)
    if not match:
        return None
    try:
        value = float(match.group(1).replace(",", "."))
    except ValueError:
        return None
    return value if 0.0 <= value <= 100.0 else None


def _recognize_detail_hp_slot(
    round_image: Image.Image,
    side: str,
    slot: int,
    ocr: ArenaOCRRecognizer,
    precise_box: tuple[float, float, float, float] | None = None,
) -> tuple[float, float] | None:
    """Retry one visually crowded survivor HP label at a larger scale."""
    if precise_box is None:
        x0_ratio, x1_ratio = DETAIL_HP_RETRY_X[side]
        y0_ratio, y1_ratio = _detail_hp_slot_bounds(slot)
        crop = _crop_rel(round_image, (x0_ratio, y0_ratio, x1_ratio, y1_ratio))
    else:
        x0, y0, x1, y1 = precise_box
        crop_box = (
            max(0, min(round_image.width, int(round(x0)))),
            max(0, min(round_image.height, int(round(y0)))),
            max(0, min(round_image.width, int(round(x1)))),
            max(0, min(round_image.height, int(round(y1)))),
        )
        if crop_box[2] <= crop_box[0] or crop_box[3] <= crop_box[1]:
            return None
        crop = round_image.crop(crop_box)
    if crop.width < 8 or crop.height < 8:
        return None
    enlarged = crop.resize((crop.width * 4, crop.height * 4), Image.Resampling.LANCZOS)
    variants = (
        enlarged,
        ImageEnhance.Contrast(enlarged).enhance(2.3),
    )
    best: tuple[float, float] | None = None
    for image in variants:
        for item in ocr.recognize_region(image, f"{side}_hp_retry_{slot + 1}"):
            value = _parse_detail_hp_percent(item.text)
            if value is None or item.confidence < DETAIL_HP_RETRY_MIN_CONFIDENCE:
                continue
            candidate = (value, float(item.confidence))
            if best is None or candidate[1] > best[1]:
                best = candidate
    return best


def _detailed_survivor_hp_totals(
    round_image: Image.Image,
    items: list[OCRItem],
    attacker_defeat_flags: list[bool],
    defender_defeat_flags: list[bool],
    ocr: ArenaOCRRecognizer | None = None,
    precise_boxes: dict[str, tuple[tuple[float, float, float, float], ...]] | None = None,
) -> tuple[dict[str, float] | None, dict[str, tuple[int, ...]]]:
    """Read one HP percentage for every surviving detailed-result card.

    Returning no totals is intentional when OCR misses any survivor. A partial
    sum can look plausible but must never decide a battle.
    """
    values: dict[str, list[tuple[float, float] | None]] = {
        "attacker": [None] * len(DETAIL_SLOT_CENTERS),
        "defender": [None] * len(DETAIL_SLOT_CENTERS),
    }
    defeat_flags = {
        "attacker": list(attacker_defeat_flags),
        "defender": list(defender_defeat_flags),
    }
    coord_size = _ocr_coordinate_size(items, round_image)
    for item in items:
        value = _parse_detail_hp_percent(item.text)
        if value is None:
            continue
        x_ratio, y_ratio = _ocr_item_center_ratio(item, round_image, coord_size)
        if 0.46 <= x_ratio <= 0.54:
            continue
        side = "attacker" if x_ratio < 0.5 else "defender"
        slot = _detail_hp_slot_from_y_ratio(y_ratio)
        if slot is None or slot >= len(defeat_flags[side]) or defeat_flags[side][slot]:
            continue
        previous = values[side][slot]
        candidate = (value, float(item.confidence))
        if previous is None or candidate[1] > previous[1]:
            values[side][slot] = candidate

    if ocr is not None:
        for side in ("attacker", "defender"):
            for slot, is_defeated in enumerate(defeat_flags[side]):
                if is_defeated or values[side][slot] is not None:
                    continue
                retry = _recognize_detail_hp_slot(
                    round_image,
                    side,
                    slot,
                    ocr,
                    precise_box=precise_boxes[side][slot] if precise_boxes is not None else None,
                )
                if retry is not None:
                    values[side][slot] = retry

    missing: dict[str, tuple[int, ...]] = {}
    totals: dict[str, float] = {}
    for side in ("attacker", "defender"):
        missing_slots = tuple(
            index + 1
            for index, is_defeated in enumerate(defeat_flags[side])
            if not is_defeated and values[side][index] is None
        )
        missing[side] = missing_slots
        if missing_slots:
            continue
        totals[side] = sum(value[0] for value in values[side] if value is not None)
    if missing["attacker"] or missing["defender"]:
        return None, missing
    return totals, missing


def _detect_overseas_health_tiebreak(
    round_image: Image.Image,
    items: list[OCRItem],
    attacker_defeat_flags: list[bool],
    defender_defeat_flags: list[bool],
    ocr: ArenaOCRRecognizer | None = None,
    precise_boxes: dict[str, tuple[tuple[float, float, float, float], ...]] | None = None,
) -> tuple[str, float]:
    """Resolve equal-survivor overseas rounds from complete HP totals only."""
    totals, missing = _detailed_survivor_hp_totals(
        round_image,
        items,
        attacker_defeat_flags,
        defender_defeat_flags,
        ocr=ocr,
        precise_boxes=precise_boxes,
    )
    if totals is None or missing["attacker"] or missing["defender"]:
        return "unknown", 0.0
    difference = totals["attacker"] - totals["defender"]
    if abs(difference) < 0.005:
        return "draw", 0.94
    winner = "attacker" if difference > 0 else "defender"
    return winner, min(0.94, 0.82 + min(0.12, abs(difference) / 100.0))


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
    client_profile: str = CLIENT_PROFILE_CN,
    precise_defeat_boxes: dict[str, tuple[tuple[tuple[float, float, float, float], ...], ...]] | None = None,
) -> tuple[str, float]:
    round_image, _round_abs = _detail_round_crop(center_image, row)
    if result_mode == RESULT_MODE_DETAILED:
        attacker_flags, defender_flags = _detail_defeat_flags_from_panel(
            center_image,
            row,
            client_profile=client_profile,
            precise_boxes=precise_defeat_boxes,
        )
        detail_winner, detail_conf = _winner_from_detail_defeat_flags(
            attacker_flags,
            defender_flags,
            client_profile=client_profile,
            allow_empty_defeat_flags=True,
        )
        if detail_winner != "unknown":
            return detail_winner, detail_conf
        # Overseas ties must be settled only by a complete sum of surviving
        # card HP values. Do not let a partial percentage read fall through to
        # a looser text/color heuristic.
        health_items = items
        if health_items is None:
            health_items = ocr.recognize_region(prepare_for_ocr(round_image), "round_result")
        precise_hp_boxes = None
        if precise_defeat_boxes is not None:
            precise_hp_boxes = {
                side: _panel_boxes_to_round_boxes(center_image, row, precise_defeat_boxes[side][row])
                for side in ("attacker", "defender")
            }
        health_winner, health_conf = _detect_overseas_health_tiebreak(
            round_image,
            health_items,
            attacker_flags,
            defender_flags,
            ocr=ocr,
            precise_boxes=precise_hp_boxes,
        )
        if health_winner != "unknown":
            return health_winner, health_conf
        return "unknown", detail_conf
    if result_mode == RESULT_MODE_AUTO:
        detail_winner, detail_conf = _detect_round_winner_by_detailed_defeat(
            round_image,
            items=items,
            client_profile=client_profile,
        )
        if detail_winner != "unknown":
            return detail_winner, detail_conf
    text_winner, text_conf = _detect_round_winner_by_text(
        round_image,
        ocr,
        items=items,
        client_profile=client_profile,
    )
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
    force_detailed_results: bool = False,
    client_profile: str = CLIENT_PROFILE_CN,
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
        client_profile=client_profile,
        stage_name=stage_name,
        match_index=block.match_index,
    )
    defender_id = recognize_player_id(
        defender_image,
        "defender",
        ocr,
        client_profile=client_profile,
        stage_name=stage_name,
        match_index=block.match_index,
    )
    attacker_nickname = recognize_player_nickname(
        attacker_image,
        "attacker",
        ocr,
        client_profile=client_profile,
        stage_name=stage_name,
        match_index=block.match_index,
    )
    defender_nickname = recognize_player_nickname(
        defender_image,
        "defender",
        ocr,
        client_profile=client_profile,
        stage_name=stage_name,
        match_index=block.match_index,
    )
    result_mode = RESULT_MODE_DETAILED if force_detailed_results else _infer_result_mode(source_name)
    winner_center_image = (
        _detailed_result_panel_image(block.image, client_profile=client_profile)
        if result_mode == RESULT_MODE_DETAILED
        else center_image
    )
    precise_defeat_boxes = (
        _overseas_defeat_boxes_for_panel(
            block.image,
            winner_center_image,
            stage_name,
            block.match_index,
        )
        if result_mode == RESULT_MODE_DETAILED
        and _normalize_client_profile(client_profile) == CLIENT_PROFILE_OVERSEAS
        else None
    )
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
            client_profile=client_profile,
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
            client_profile=client_profile,
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
        # Detailed-result name OCR shares one parser, but each client profile
        # selects its own calibrated panel coordinates above.
        detail_name_image = _detail_name_image(
            block.image,
            center_image,
            result_mode,
            client_profile,
        )
        detail_attacker, detail_defender, attacker_scores, defender_scores, detail_items = recognize_detail_team_rows(
            detail_name_image,
            ocr,
            matcher,
            block_height=block.image.height,
            client_profile=client_profile,
            source_name=source_name if result_mode == RESULT_MODE_DETAILED else "",
        )
        attacker_teams = _merge_team_sources(attacker_teams, detail_attacker, attacker_scores, matcher)
        defender_teams = _merge_team_sources(defender_teams, detail_defender, defender_scores, matcher)

    if include_collection:
        attacker_collections = [
            _gate_collection_slots_by_character_names(team, collection, matcher)
            for team, collection in zip(attacker_teams, attacker_collections)
        ]
        defender_collections = [
            _gate_collection_slots_by_character_names(team, collection, matcher)
            for team, collection in zip(defender_teams, defender_collections)
        ]

    records: list[dict] = []
    for row in range(5):
        winner_items = None if result_mode == RESULT_MODE_DETAILED else (detail_items[row] if include_teams else None)
        winner, winner_conf = detect_round_winner(
            winner_center_image,
            row,
            ocr,
            items=winner_items,
            result_mode=result_mode,
            client_profile=client_profile,
            precise_defeat_boxes=precise_defeat_boxes,
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
