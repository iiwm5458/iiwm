from __future__ import annotations

import argparse
import gc
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

TOOL_ROOT = Path(__file__).resolve().parent
if str(TOOL_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOL_ROOT))

from recognizer.arena_ocr import ArenaOCRRecognizer
from recognizer.exporter import export_excel, export_json
from recognizer.image_preprocess import load_image
from recognizer.image_splitter import ImageBlock, classify_layout, save_debug_image, split_input_image
from recognizer.logger import RunLogger
from recognizer.nikke_name_matcher import NikkeNameMatcher
from recognizer.result_parser import recognize_match_block

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


FALLBACK_STAGE_NAME = "\u0036\u0034\u8fdb\u0033\u0032"
STAGE_NAMES = {
    "group64": "\u0036\u0034\u8fdb\u0033\u0032",
    "group32": "\u0033\u0032\u8fdb\u0031\u0036",
    "group16": "\u0031\u0036\u8fdb\u0038",
    "top8": "\u51a0\u519b\u4e89\u9738\u8d5b\u0038\u8fdb\u0034",
    "top4": "\u51a0\u519b\u4e89\u9738\u8d5b\u0034\u8fdb\u0032",
    "final": "\u51a0\u519b\u4e89\u9738\u8d5b\u51a0\u4e9a\u519b",
    "top8_pyramid": "\u51a0\u519b\u4e89\u9738\u8d5b\u4e00\u56fe\u6d41",
}

SEASON_IMAGE_SPECS = (
    ("group64", "season_group64_image", "64\u8fdb32\u5168\u90e8\u6218\u6597\u6570\u636e\uff08\u8be6\uff09"),
    ("group32", "season_group32_image", "32\u8fdb16\u5168\u90e8\u6218\u6597\u6570\u636e\uff08\u8be6\uff09"),
    ("group16", "season_group16_image", "16\u8fdb8\u5168\u90e8\u6218\u6597\u6570\u636e\uff08\u8be6\uff09"),
    ("top8_pyramid", "season_top8_image", "TOP8-\u51b3\u8d5b\u6218\u6597\u6570\u636e\uff08\u8be6\uff09"),
)

EXPECTED_SEASON_BLOCKS = {
    "group64": 32,
    "group32": 16,
    "group16": 8,
    "top8_pyramid": 7,
}

SOURCE_PROFILE_3840 = "3840x2160"


class ProgressReporter:
    def __init__(self, progress_file: str | None):
        self.path = Path(progress_file).expanduser() if progress_file else None
        self.started = time.monotonic()
        self.last_label = ""

    def update(self, completed: int, total: int, label: str = "") -> None:
        if label and label != self.last_label:
            percent = 0.0 if int(total or 0) <= 0 else (int(completed or 0) / max(1, int(total or 0))) * 100.0
            print(f"[progress] {completed}/{total} {percent:.2f}% {label}", flush=True)
            self.last_label = label
        if not self.path:
            return
        total = max(0, int(total or 0))
        completed = max(0, min(int(completed or 0), total)) if total else max(0, int(completed or 0))
        elapsed = max(0.0, time.monotonic() - self.started)
        percent = 0.0 if total <= 0 else (completed / total) * 100.0
        eta_seconds = None
        if total > 0 and completed > 0 and completed < total:
            eta_seconds = (elapsed / completed) * (total - completed)
        elif total > 0 and completed >= total:
            eta_seconds = 0.0

        payload = {
            "completed": completed,
            "total": total,
            "percent": round(percent, 2),
            "eta_seconds": None if eta_seconds is None else round(float(eta_seconds), 1),
            "elapsed_seconds": round(elapsed, 1),
            "label": label,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self.path.with_name(self.path.name + ".tmp")
            tmp_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            tmp_path.replace(self.path)
        except Exception:
            pass


class OcrTerminated(Exception):
    """Raised when the GUI asks the OCR worker to stop at a safe boundary."""


class OcrRunControl:
    def __init__(
        self,
        mode: str = "safe",
        control_file: str | None = None,
        cooldown_sleep: float = 0.0,
        logger: RunLogger | None = None,
    ) -> None:
        self.mode = mode if mode in {"safe", "performance"} else "safe"
        self.path = Path(control_file).expanduser() if control_file else None
        self.cooldown_sleep = max(0.0, float(cooldown_sleep or 0.0))
        self.logger = logger
        self._pause_logged = False

    def _read_state(self) -> dict:
        if not self.path or not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8-sig"))
        except Exception:
            return {}

    def _requested_sleep(self, state: dict) -> float:
        if self.mode != "safe":
            return 0.0
        value = state.get("requested_sleep_seconds", self.cooldown_sleep)
        try:
            return max(0.0, float(value or 0.0))
        except (TypeError, ValueError):
            return self.cooldown_sleep

    def check(self, label: str = "") -> None:
        state = self._read_state()
        if bool(state.get("terminate")):
            if self.logger:
                self.logger.warning(f"ocr_terminated_by_control label={label}")
            raise OcrTerminated("OCR terminated by user request.")

        while bool(state.get("pause")):
            if not self._pause_logged:
                print(f"[control] paused: {label}", flush=True)
                if self.logger:
                    self.logger.warning(f"ocr_paused_by_control label={label}")
                self._pause_logged = True
            time.sleep(1.0)
            state = self._read_state()
            if bool(state.get("terminate")):
                if self.logger:
                    self.logger.warning(f"ocr_terminated_while_paused label={label}")
                raise OcrTerminated("OCR terminated by user request.")
        self._pause_logged = False

    def after_block(self, label: str = "") -> None:
        state = self._read_state()
        if bool(state.get("terminate")):
            if self.logger:
                self.logger.warning(f"ocr_terminated_by_control label={label}")
            raise OcrTerminated("OCR terminated by user request.")

        sleep_seconds = self._requested_sleep(state)
        if sleep_seconds > 0:
            print(f"[control] cooldown {sleep_seconds:.2f}s {label}", flush=True)
            time.sleep(sleep_seconds)
        self.check(label)


def infer_stage_code(image_path: Path, image, requested_stage_code: str) -> str:
    if requested_stage_code != "auto":
        return requested_stage_code

    stem = image_path.stem.lower()
    if "top8_pyramid" in stem:
        return "top8_pyramid"
    if "top2" in stem or "final" in stem:
        return "final"
    if "top4" in stem:
        return "top4"
    if "top8" in stem:
        return "top8"
    if "group8" in stem:
        return "group64"
    if "group4" in stem:
        return "group32"
    if "group2" in stem:
        return "group16"

    layout = classify_layout(image)
    width, height = image.size
    if layout == "all_groups_single_match":
        return "group16"
    if layout == "all_groups":
        # Full 64-player composites are much wider than 32-player composites.
        # This keeps manually imported files such as "64强-我要所有人..." usable
        # even when their filenames do not contain group8/group4.
        return "group64" if width >= 10000 else "group32"
    if layout == "single_group":
        return "group64"
    return "group64"


def source_profile_from_path(path: Path | str | None) -> str:
    if not path:
        return ""
    text = str(path).lower()
    if re.search(r"3840\s*[x×]\s*2160", text) or ("3840" in text and "2160" in text):
        return SOURCE_PROFILE_3840
    return ""


def source_profile_from_args(args: argparse.Namespace) -> str:
    paths = [
        args.image,
        args.manifest,
        args.season_group64_image,
        args.season_group32_image,
        args.season_group16_image,
        args.season_top8_image,
    ]
    return SOURCE_PROFILE_3840 if any(source_profile_from_path(path) == SOURCE_PROFILE_3840 for path in paths) else ""


def configure_source_profile(args: argparse.Namespace, logger: RunLogger) -> str:
    profile = source_profile_from_args(args)
    if profile == SOURCE_PROFILE_3840:
        os.environ["NIKKE_OCR_SOURCE_PROFILE"] = SOURCE_PROFILE_3840
        if args.use_gpu:
            os.environ["NIKKE_ENABLE_GPU_DLL_DIRECTORIES"] = "1"
            os.environ["NIKKE_OCR_VERBOSE_RUNTIME_ERRORS"] = "1"
        logger.info("ocr_source_profile=3840x2160")
    else:
        os.environ.pop("NIKKE_OCR_SOURCE_PROFILE", None)
        os.environ.pop("NIKKE_ENABLE_GPU_DLL_DIRECTORIES", None)
        os.environ.pop("NIKKE_OCR_VERBOSE_RUNTIME_ERRORS", None)
    return profile


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Recognize NIKKE C ARENA detailed post-battle screenshots.")
    parser.add_argument("--image", default=None, help="Input PNG/JPG/JPEG screenshot path.")
    parser.add_argument("--manifest", default=None, help="Manifest JSON generated by the capture tool.")
    parser.add_argument("--season-group64-image", default=None, help="Season OCR image for all GROUP 8-to-4 battles.")
    parser.add_argument("--season-group32-image", default=None, help="Season OCR image for all GROUP 4-to-2 battles.")
    parser.add_argument("--season-group16-image", default=None, help="Season OCR image for all GROUP 2-to-1 battles.")
    parser.add_argument("--season-top8-image", default=None, help="Season OCR image for TOP8/final pyramid battles.")
    parser.add_argument("--output-dir", default=None, help="Directory for JSON/XLSX/debug output.")
    parser.add_argument("--debug", action="store_true", help="Save debug split images and logs.")
    parser.add_argument("--use-gpu", action="store_true", help="Allow OCR backend to use GPU when available.")
    parser.add_argument("--cpu-threads", type=int, default=0, help=argparse.SUPPRESS)
    parser.add_argument(
        "--stage-code",
        choices=["auto", *sorted(STAGE_NAMES)],
        default="auto",
        help="Stage label written to JSON/Excel for automatic capture export.",
    )
    parser.add_argument(
        "--layout",
        choices=["auto", "top8_pyramid"],
        default="auto",
        help="Optional layout override for generated composite images.",
    )
    parser.add_argument(
        "--progress-file",
        default=None,
        help="Optional JSON file for GUI progress polling.",
    )
    parser.add_argument(
        "--thermal-mode",
        choices=["safe", "performance"],
        default="safe",
        help="OCR thermal protection mode. Safe mode may sleep briefly between match blocks.",
    )
    parser.add_argument(
        "--control-file",
        default=None,
        help="Optional JSON file used by the GUI to request pause/terminate at block boundaries.",
    )
    parser.add_argument(
        "--cooldown-sleep",
        type=float,
        default=0.0,
        help="Seconds to sleep after each match block in safe thermal mode.",
    )
    parser.add_argument("--no-power", action="store_true", help="Skip Nikke power OCR and omit power columns.")
    parser.add_argument("--no-collection", action="store_true", help="Skip collection OCR and omit collection columns.")
    parser.add_argument("--no-stat-levels", action="store_true", help="Skip cycle/stat level OCR and omit level columns.")
    return parser.parse_args()


def initialize_ocr(args: argparse.Namespace, base_dir: Path, logger: RunLogger):
    ocr = ArenaOCRRecognizer(use_gpu=args.use_gpu)
    logger.info(f"ocr_engine={ocr.engine_name}")
    print(f"[ocr] engine={ocr.engine_name} use_gpu={args.use_gpu}", flush=True)
    if not ocr.available:
        logger.warning(ocr.error or "No OCR engine is available; text fields will be unknown.")
        logger.save()
        print(
            "No OCR engine is available. Install PaddleOCR in the Python runtime used by the launcher.",
            file=sys.stderr,
        )
        return None, None

    matcher = NikkeNameMatcher(str(base_dir / "data" / "nikke_names.json"))
    dictionary_status = matcher.ensure_dictionary()
    logger.info(f"name_dictionary_count={len(matcher.names)}")
    logger.info(
        "name_dictionary_status="
        f"{dictionary_status.get('source')}:{dictionary_status.get('count')}:{dictionary_status.get('message')}"
    )
    return ocr, matcher


def build_run_control(args: argparse.Namespace, logger: RunLogger) -> OcrRunControl | None:
    if not args.control_file and float(args.cooldown_sleep or 0.0) <= 0:
        return None
    return OcrRunControl(
        mode=args.thermal_mode,
        control_file=args.control_file,
        cooldown_sleep=args.cooldown_sleep,
        logger=logger,
    )


def fallback_records(stage_name: str, block: ImageBlock, source_name: str) -> list[dict]:
    records = []
    for round_index in range(1, 6):
        records.append(
            {
                "stage": stage_name,
                "group_index": block.group_index,
                "match_index": block.match_index,
                "round_index": round_index,
                "attacker_player_id": "",
                "attacker_player_nickname": "",
                "attacker_stat_levels": [],
                "defender_player_id": "",
                "defender_player_nickname": "",
                "defender_stat_levels": [],
                "attacker_team": [],
                "attacker_power": [],
                "attacker_collection": [],
                "defender_team": [],
                "defender_power": [],
                "defender_collection": [],
                "winner": "unknown",
                "confidence": 0.0,
                "source_image": source_name,
            }
        )
    return records


def collect_season_image_specs(args: argparse.Namespace) -> list[tuple[str, Path, str]]:
    specs: list[tuple[str, Path, str]] = []
    for stage_code, attr_name, label in SEASON_IMAGE_SPECS:
        raw_path = getattr(args, attr_name, None)
        if raw_path:
            specs.append((stage_code, Path(raw_path).expanduser(), label))
    return specs


def _safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_player_id(value) -> str:
    text = str(value or "").strip()
    digits = re.sub(r"\D+", "", text)
    return digits if len(digits) >= 4 else text


def _normalize_nickname(value) -> str:
    return re.sub(r"\s+", "", str(value or "")).casefold()


def _filled_count(values: list) -> int:
    return sum(1 for value in (values or []) if value not in ("", None))


def _collection_filled_count(values: list) -> int:
    return sum(1 for value in (values or []) if value not in ("", None, "\u65e0"))


def _remember_round_values(target: dict[int, list], round_index: int, values: list) -> None:
    if not round_index:
        return
    values = list(values or [])[:5]
    if not values:
        return
    current = target.get(round_index) or []
    if _filled_count(values) >= _filled_count(current):
        target[round_index] = values


def _remember_collection_values(target: dict[int, list], round_index: int, values: list) -> None:
    if not round_index:
        return
    values = list(values or [])[:5]
    if not values:
        return
    current = target.get(round_index) or []
    if not current or _collection_filled_count(values) >= _collection_filled_count(current):
        target[round_index] = values


def _merge_roster_side(roster: dict[str, dict], record: dict, side: str) -> None:
    player_id = _normalize_player_id(record.get(f"{side}_player_id"))
    nickname = str(record.get(f"{side}_player_nickname") or "").strip()
    name_key = _normalize_nickname(nickname)
    if not player_id and not name_key:
        return

    key = player_id or f"name:{name_key}"
    entry = roster.get(key)
    if entry is None:
        entry = {
            "player_id": player_id,
            "nickname": nickname,
            "group_index": record.get("group_index", ""),
            "match_index": record.get("match_index", ""),
                "side": side,
                "teams": {},
                "powers": {},
                "collections": {},
                "stat_levels": [],
            }
        roster[key] = entry
    elif player_id and not entry.get("player_id"):
        entry["player_id"] = player_id
    if nickname and not entry.get("nickname"):
        entry["nickname"] = nickname

    round_index = _safe_int(record.get("round_index"))
    _remember_round_values(entry["teams"], round_index, record.get(f"{side}_team") or [])
    _remember_round_values(entry["powers"], round_index, record.get(f"{side}_power") or [])
    _remember_collection_values(entry["collections"], round_index, record.get(f"{side}_collection") or [])
    stat_levels = list(record.get(f"{side}_stat_levels") or [])[:8]
    if _filled_count(stat_levels) >= _filled_count(entry.get("stat_levels") or []):
        entry["stat_levels"] = stat_levels


def build_player_roster(records: list[dict]) -> dict[str, dict]:
    roster: dict[str, dict] = {}
    for record in records:
        _merge_roster_side(roster, record, "attacker")
        _merge_roster_side(roster, record, "defender")
    return roster


def build_group64_roster(records: list[dict], logger: RunLogger, context: str) -> dict[str, dict]:
    group64_stage = STAGE_NAMES.get("group64", FALLBACK_STAGE_NAME)
    roster_records = [record for record in records if str(record.get("stage") or "") == group64_stage]
    if not roster_records:
        return {}

    roster = build_player_roster(roster_records)
    logger.info(f"{context}_roster_players={len(roster)}")
    if len(roster) < 64:
        logger.warning(f"{context}_roster_player_count_below_64={len(roster)}")
    return roster


def _build_roster_indexes(roster: dict[str, dict]) -> tuple[dict[str, dict], dict[str, dict]]:
    by_id: dict[str, dict] = {}
    by_name: dict[str, dict] = {}
    for entry in roster.values():
        player_id = _normalize_player_id(entry.get("player_id"))
        nickname_key = _normalize_nickname(entry.get("nickname"))
        if player_id:
            by_id[player_id] = entry
        if nickname_key and nickname_key not in by_name:
            by_name[nickname_key] = entry
    return by_id, by_name


def _lookup_roster_entry(
    by_id: dict[str, dict],
    by_name: dict[str, dict],
    player_id: str,
    nickname: str,
) -> tuple[dict | None, str]:
    normalized_id = _normalize_player_id(player_id)
    if normalized_id and normalized_id in by_id:
        return by_id[normalized_id], "id"
    nickname_key = _normalize_nickname(nickname)
    if nickname_key and nickname_key in by_name:
        return by_name[nickname_key], "nickname"
    return None, ""


def enrich_records_from_roster(records: list[dict], roster: dict[str, dict], logger: RunLogger) -> None:
    by_id, by_name = _build_roster_indexes(roster)
    for record in records:
        round_index = _safe_int(record.get("round_index"))
        for side in ("attacker", "defender"):
            player_id = _normalize_player_id(record.get(f"{side}_player_id"))
            nickname = str(record.get(f"{side}_player_nickname") or "").strip()
            entry, match_kind = _lookup_roster_entry(by_id, by_name, player_id, nickname)
            if not entry:
                continue
            roster_id = _normalize_player_id(entry.get("player_id"))
            roster_name = str(entry.get("nickname") or "").strip()
            if match_kind == "id" and nickname and roster_name and _normalize_nickname(nickname) != _normalize_nickname(roster_name):
                logger.warning(f"nickname corrected by player_id: {nickname} -> {roster_name}")
            if roster_id:
                record[f"{side}_player_id"] = roster_id
            if roster_name:
                record[f"{side}_player_nickname"] = roster_name

            team = (entry.get("teams") or {}).get(round_index)
            power = (entry.get("powers") or {}).get(round_index)
            collection = (entry.get("collections") or {}).get(round_index)
            stat_levels = entry.get("stat_levels") or []
            if team:
                record[f"{side}_team"] = team
            if power:
                record[f"{side}_power"] = power
            if collection:
                record[f"{side}_collection"] = collection
            if stat_levels:
                record[f"{side}_stat_levels"] = stat_levels


def recognize_image_records(
    args: argparse.Namespace,
    image_path: Path,
    stage_code: str,
    output_dir: Path,
    logger: RunLogger,
    ocr: ArenaOCRRecognizer,
    matcher: NikkeNameMatcher,
    debug_dir: Path | None,
    progress: ProgressReporter,
    progress_offset: int,
    progress_total: int,
    include_teams: bool = True,
    control: OcrRunControl | None = None,
    source_profile: str = "",
) -> tuple[list[dict], int, bool]:
    source_name = image_path.name
    progress.update(progress_offset, progress_total, f"loading image: {source_name}")
    image = load_image(str(image_path))
    effective_stage_code = stage_code
    if effective_stage_code == "auto":
        effective_stage_code = infer_stage_code(image_path, image, args.stage_code)
    stage_name = STAGE_NAMES.get(effective_stage_code, FALLBACK_STAGE_NAME)
    logger.info(f"season_source={source_name}")
    logger.info(f"season_stage_code={effective_stage_code}")
    print(f"[image] source={source_name} stage={effective_stage_code} include_teams={include_teams}", flush=True)

    layout = "top8_pyramid" if effective_stage_code == "top8_pyramid" else args.layout
    try:
        blocks = split_input_image(image, layout=layout, stage_code=effective_stage_code)
        logger.info(f"season_blocks_{effective_stage_code}={len(blocks)}")
        print(f"[split] source={source_name} blocks={len(blocks)} layout={layout}", flush=True)
        if debug_dir:
            save_debug_image(image, blocks, debug_dir, f"{image_path.stem}_{effective_stage_code}")
    except Exception:
        try:
            image.close()
        except Exception:
            pass
        raise

    records: list[dict] = []
    processed_blocks = 0
    terminated = False
    try:
        for index, block in enumerate(blocks, 1):
            block_label = f"{source_name} block {index}/{len(blocks)}"
            try:
                if control:
                    control.check(block_label)
            except OcrTerminated:
                terminated = True
                break

            try:
                block_records = recognize_match_block(
                    block,
                    source_name=source_name,
                    ocr=ocr,
                    matcher=matcher,
                    debug_dir=debug_dir,
                    stage_name=stage_name,
                    include_teams=include_teams,
                    include_power=not args.no_power,
                    include_collection=not args.no_collection,
                    include_stat_levels=not args.no_stat_levels,
                    source_profile=source_profile,
                )
                if not block_records:
                    block_records = fallback_records(stage_name, block, source_name)
                records.extend(block_records)
            except Exception as exc:
                logger.error(
                    f"failed season block {source_name} group={block.group_index} match={block.match_index}: {exc}"
                )
                records.extend(fallback_records(stage_name, block, source_name))
            finally:
                progress.update(
                    progress_offset + index,
                    progress_total,
                    block_label,
                )
                processed_blocks = index

            try:
                if control:
                    control.after_block(block_label)
            except OcrTerminated:
                terminated = True
                break
    finally:
        try:
            image.close()
        except Exception:
            pass
        gc.collect()

    return records, processed_blocks, terminated


def run_season_images(
    args: argparse.Namespace,
    specs: list[tuple[str, Path, str]],
    output_dir: Path,
    logger: RunLogger,
    base_dir: Path,
) -> int:
    progress = ProgressReporter(args.progress_file)
    progress_total = sum(EXPECTED_SEASON_BLOCKS.get(stage_code, 1) for stage_code, _, _ in specs)
    progress.update(0, progress_total, "initializing OCR: season images")
    run_source_profile = os.environ.get("NIKKE_OCR_SOURCE_PROFILE", "")
    ocr, matcher = initialize_ocr(args, base_dir, logger)
    if ocr is None:
        return 4

    debug_dir = output_dir / "debug" if args.debug else None
    records: list[dict] = []
    roster: dict[str, dict] = {}
    completed_blocks = 0
    control = build_run_control(args, logger)
    terminated = False
    for stage_code, image_path, label in specs:
        include_teams = stage_code == "group64"
        try:
            stage_records, block_count, stage_terminated = recognize_image_records(
                args,
                image_path,
                stage_code,
                output_dir,
                logger,
                ocr,
                matcher,
                debug_dir,
                progress,
                completed_blocks,
                progress_total,
                include_teams=include_teams,
                control=control,
                source_profile=source_profile_from_path(image_path) or run_source_profile,
            )
        except Exception as exc:
            logger.error(f"failed season image {image_path.name}: {exc}")
            logger.save()
            print(f"Failed to read season image ({label}): {exc}", file=sys.stderr)
            return 4

        if stage_code == "group64":
            roster = build_player_roster(stage_records)
            logger.info(f"season_roster_players={len(roster)}")
            if len(roster) < 64:
                logger.warning(f"season_roster_player_count_below_64={len(roster)}")
        else:
            enrich_records_from_roster(stage_records, roster, logger)
        records.extend(stage_records)
        completed_blocks += block_count
        if stage_terminated:
            terminated = True
            break

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = f"arena_season_images_{stamp}" + ("_partial" if terminated else "")
    json_path = export_json(
        records,
        output_dir,
        stem,
        roster=roster,
        include_power=not args.no_power,
        include_collection=not args.no_collection,
        include_stat_levels=not args.no_stat_levels,
    )
    excel_path = export_excel(
        records,
        output_dir,
        stem,
        roster=roster,
        include_power=not args.no_power,
        include_collection=not args.no_collection,
        include_stat_levels=not args.no_stat_levels,
    )
    log_path = logger.save(f"season_images_ocr_{stamp}.log")
    if terminated:
        progress.update(completed_blocks, progress_total, "terminated: season images")
    else:
        progress.update(progress_total, progress_total, "exported: season images")

    print(f"records={len(records)}")
    print(f"roster_players={len(roster)}")
    print(f"json={json_path}")
    print(f"excel={excel_path}")
    print(f"log={log_path}")
    if debug_dir:
        print(f"debug={debug_dir}")
    return 130 if terminated else 0


def run_manifest(args: argparse.Namespace, manifest_path: Path, output_dir: Path, logger: RunLogger, base_dir: Path) -> int:
    progress = ProgressReporter(args.progress_file)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        logger.error(f"failed to read manifest: {exc}")
        logger.save()
        print(f"Failed to read manifest: {exc}", file=sys.stderr)
        return 3

    blocks_meta = manifest.get("blocks") or []
    if not blocks_meta:
        logger.error("manifest has no blocks")
        logger.save()
        print(f"Manifest has no blocks: {manifest_path}", file=sys.stderr)
        return 3

    logger.info(f"manifest={manifest_path.name}")
    logger.info(f"manifest_blocks={len(blocks_meta)}")
    progress.update(0, len(blocks_meta), f"initializing OCR: {manifest_path.name}")
    ocr, matcher = initialize_ocr(args, base_dir, logger)
    if ocr is None:
        return 4

    records: list[dict] = []
    control = build_run_control(args, logger)
    run_source_profile = os.environ.get("NIKKE_OCR_SOURCE_PROFILE", "")
    terminated = False
    processed_blocks = 0
    for index, meta in enumerate(blocks_meta, 1):
        block_label = f"manifest block {index}/{len(blocks_meta)}"
        try:
            if control:
                control.check(block_label)
        except OcrTerminated:
            terminated = True
            break

        image = None
        block_path = Path(meta.get("image", "")).expanduser()
        if not block_path.is_absolute():
            block_path = manifest_path.parent / block_path
        stage_code = meta.get("stage_code") or manifest.get("stage_code") or args.stage_code
        if stage_code == "auto":
            stage_code = "group64"
        stage_name = meta.get("stage_name") or STAGE_NAMES.get(stage_code, FALLBACK_STAGE_NAME)
        source_name = Path(meta.get("source_image") or block_path.name).name
        source_profile = source_profile_from_path(meta.get("source_image")) or source_profile_from_path(block_path) or run_source_profile

        try:
            image = load_image(str(block_path))
            block = ImageBlock(
                group_index=int(meta.get("group_index", 1)),
                match_index=int(meta.get("match_index", index)),
                image=image,
                bbox=(0, 0, image.width, image.height),
            )
            block_records = recognize_match_block(
                block,
                source_name=source_name,
                ocr=ocr,
                matcher=matcher,
                debug_dir=None,
                stage_name=stage_name,
                include_power=not args.no_power,
                include_collection=not args.no_collection,
                include_stat_levels=not args.no_stat_levels,
                source_profile=source_profile,
            )
            if not block_records:
                block_records = fallback_records(stage_name, block, source_name)
            records.extend(block_records)
        except Exception as exc:
            logger.error(f"failed manifest block {index} ({block_path.name}): {exc}")
            fallback_block = ImageBlock(
                group_index=int(meta.get("group_index", 1)),
                match_index=int(meta.get("match_index", index)),
                image=None,
                bbox=(0, 0, 0, 0),
            )
            records.extend(fallback_records(stage_name, fallback_block, source_name))
        finally:
            progress.update(index, len(blocks_meta), f"{source_name} block {index}/{len(blocks_meta)}")
            processed_blocks = index
            try:
                image.close()
            except Exception:
                pass
            del image
            gc.collect()
        try:
            if control:
                control.after_block(f"{source_name} block {index}/{len(blocks_meta)}")
        except OcrTerminated:
            terminated = True
            break

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    source_stem = manifest_path.stem.replace("_manifest", "")
    stem = f"arena_64groups_{source_stem}_{stamp}" + ("_partial" if terminated else "")
    roster = build_group64_roster(records, logger, "manifest")
    json_path = export_json(
        records,
        output_dir,
        stem,
        roster=roster,
        include_power=not args.no_power,
        include_collection=not args.no_collection,
        include_stat_levels=not args.no_stat_levels,
    )
    excel_path = export_excel(
        records,
        output_dir,
        stem,
        roster=roster,
        include_power=not args.no_power,
        include_collection=not args.no_collection,
        include_stat_levels=not args.no_stat_levels,
    )
    log_path = logger.save(f"{source_stem}_ocr.log")
    if terminated:
        progress.update(processed_blocks, len(blocks_meta), f"terminated: {source_stem}")
    else:
        progress.update(len(blocks_meta), len(blocks_meta), f"exported: {source_stem}")

    print(f"records={len(records)}")
    print(f"roster_players={len(roster)}")
    print(f"json={json_path}")
    print(f"excel={excel_path}")
    print(f"log={log_path}")
    return 130 if terminated else 0


def main() -> int:
    args = parse_args()
    image_path = Path(args.image).expanduser() if args.image else None
    manifest_path = Path(args.manifest).expanduser() if args.manifest else None
    season_specs = collect_season_image_specs(args)
    if season_specs and (image_path or manifest_path):
        print("Season image mode cannot be combined with --image or --manifest.", file=sys.stderr)
        return 2
    if not image_path and not manifest_path and not season_specs:
        print("Input image, manifest, or season images are required.", file=sys.stderr)
        return 2
    if season_specs and not any(stage_code == "group64" for stage_code, _, _ in season_specs):
        print("Season image mode requires --season-group64-image as the roster source.", file=sys.stderr)
        return 2
    if image_path and not image_path.exists():
        print(f"Input image not found: {image_path}", file=sys.stderr)
        return 2
    if manifest_path and not manifest_path.exists():
        print(f"Manifest not found: {manifest_path}", file=sys.stderr)
        return 2
    for _, season_image_path, _ in season_specs:
        if not season_image_path.exists():
            print(f"Season image not found: {season_image_path}", file=sys.stderr)
            return 2

    base_dir = Path(__file__).resolve().parent
    output_dir = Path(args.output_dir) if args.output_dir else base_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    debug_dir = output_dir / "debug" if args.debug else None
    logger = RunLogger(output_dir)
    run_source_profile = configure_source_profile(args, logger)
    if season_specs:
        logger.info(f"python_executable={sys.executable}")
        logger.info("ocr_cpu_threads=backend-default")
        logger.info(f"ocr_use_gpu={args.use_gpu}")
        logger.info("ocr_mode=season_images")
        return run_season_images(args, season_specs, output_dir, logger, base_dir)
    if manifest_path:
        logger.info(f"python_executable={sys.executable}")
        logger.info("ocr_cpu_threads=backend-default")
        logger.info(f"ocr_use_gpu={args.use_gpu}")
        logger.info(f"requested_stage_code={args.stage_code}")
        return run_manifest(args, manifest_path, output_dir, logger, base_dir)

    source_name = image_path.name
    source_stem = Path(source_name).stem
    logger.info(f"source={source_name}")
    logger.info(f"python_executable={sys.executable}")
    logger.info("ocr_cpu_threads=backend-default")
    logger.info(f"ocr_use_gpu={args.use_gpu}")
    logger.info(f"requested_stage_code={args.stage_code}")
    progress = ProgressReporter(args.progress_file)
    progress.update(0, 0, f"loading image: {source_name}")

    try:
        image = load_image(str(image_path))
    except Exception as exc:
        logger.error(f"failed to read image: {exc}")
        logger.save()
        print(f"Failed to read image: {exc}", file=sys.stderr)
        return 3

    effective_stage_code = infer_stage_code(image_path, image, args.stage_code)
    stage_name = STAGE_NAMES.get(effective_stage_code, FALLBACK_STAGE_NAME)
    logger.info(f"effective_stage_code={effective_stage_code}")

    ocr, matcher = initialize_ocr(args, base_dir, logger)
    if ocr is None:
        return 4

    try:
        blocks = split_input_image(image, layout=args.layout, stage_code=effective_stage_code)
        logger.info(f"detected_match_blocks={len(blocks)}")
        if debug_dir:
            save_debug_image(image, blocks, debug_dir, image_path.stem)
    except Exception as exc:
        logger.error(f"failed to split image: {exc}")
        logger.save()
        print(f"Failed to split image: {exc}", file=sys.stderr)
        return 4

    records: list[dict] = []
    control = build_run_control(args, logger)
    terminated = False
    processed_blocks = 0
    progress.update(0, len(blocks), f"recognizing: {source_name}")
    for index, block in enumerate(blocks, 1):
        block_label = f"{source_name} block {index}/{len(blocks)}"
        try:
            if control:
                control.check(block_label)
        except OcrTerminated:
            terminated = True
            break

        try:
            records.extend(
                recognize_match_block(
                    block,
                    source_name=source_name,
                    ocr=ocr,
                    matcher=matcher,
                    debug_dir=debug_dir,
                    stage_name=stage_name,
                    include_power=not args.no_power,
                    include_collection=not args.no_collection,
                    include_stat_levels=not args.no_stat_levels,
                    source_profile=source_profile_from_path(image_path) or run_source_profile,
                )
            )
        except Exception as exc:
            logger.error(f"failed block group={block.group_index} match={block.match_index}: {exc}")
            records.extend(fallback_records(stage_name, block, source_name))
        finally:
            progress.update(index, len(blocks), block_label)
            processed_blocks = index
        try:
            if control:
                control.after_block(block_label)
        except OcrTerminated:
            terminated = True
            break

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = f"arena_64groups_{source_stem}_{stamp}" + ("_partial" if terminated else "")
    roster = build_group64_roster(records, logger, "single_image")
    json_path = export_json(
        records,
        output_dir,
        stem,
        roster=roster,
        include_power=not args.no_power,
        include_collection=not args.no_collection,
        include_stat_levels=not args.no_stat_levels,
    )
    excel_path = export_excel(
        records,
        output_dir,
        stem,
        roster=roster,
        include_power=not args.no_power,
        include_collection=not args.no_collection,
        include_stat_levels=not args.no_stat_levels,
    )
    log_path = logger.save(f"{source_stem}_ocr.log")
    if terminated:
        progress.update(processed_blocks, len(blocks), f"terminated: {source_name}")
    else:
        progress.update(len(blocks), len(blocks), f"exported: {source_name}")

    print(f"records={len(records)}")
    print(f"roster_players={len(roster)}")
    print(f"json={json_path}")
    print(f"excel={excel_path}")
    print(f"log={log_path}")
    if debug_dir:
        print(f"debug={debug_dir}")
    return 130 if terminated else 0


if __name__ == "__main__":
    raise SystemExit(main())
