from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any


LOCAL_DICTIONARY_SOURCE = "local"
CANONICAL_COLON = "\uff1a"
COLON_CHARS = ":\uff1a\ufe13\ufe55\u2236\ua789\ua4fd"
MIN_DICTIONARY_NAME_COUNT = 50
LOCAL_DICTIONARY_BACKUP_SUFFIX = ".backup"

# Names that share a short base name with an alternate/special version.  Card
# labels often hide the right side of the name, so these hints let us promote a
# partial OCR read only when there is suffix evidence.
DEFAULT_SPECIAL_NAMES = [
    "D\uff1a\u6740\u624b\u59bb\u5b50",
    "\u7d22\u8fbe\uff1a\u95ea\u4eae\u5154\u5973\u90ce",
    "\u5b89\u59ae\uff1a\u5947\u8ff9\u4ed9\u5973",
    "\u963f\u59ae\u65af\uff1a\u95ea\u8000\u590f\u65e5",
    "\u7d22\u6797\uff1a\u971c\u4e4b\u65c5\u7968",
    "\u8fea\u585e\u5c14\uff1a\u51ac\u65e5\u751c\u5fc3",
    "\u62c9\u6bd7\uff1a\u5c0f\u7ea2\u5e3d",
    "\u7ea2\u83b2\uff1a\u6697\u5f71",
    "\u5e03\u4e3d\u5fb7\uff1a\u9759\u9ed8\u8f68\u9053",
    "\u666e\u4e3d\u74e6\u8482\uff1a\u4e0d\u53cb\u5584\u7684\u5973\u4ec6",
]

DEFAULT_EXTRA_NAMES = [
    "\u5a74\u5b81",
    "\u753b\u76ae",
    "\u5c0f\u7ea2\u5e3d",
    "\u62c9\u6bd7",
]

LONG_NAME_HINTS = {
    "\u7d22\u8fbe\uff1a\u95ea\u4eae\u5154\u5973\u90ce": (
        "\u7d22\u8fbe\u95ea",
        "\u7d22\u8fbe\u5154",
        "\u95ea\u4eae\u5154",
    ),
    "\u5b89\u59ae\uff1a\u5947\u8ff9\u4ed9\u5973": (
        "\u5b89\u59ae\u5947",
        "\u5947\u8ff9\u4ed9",
    ),
    "\u963f\u59ae\u65af\uff1a\u95ea\u8000\u590f\u65e5": (
        "\u963f\u59ae\u65af\u95ea",
        "\u95ea\u8000\u590f",
    ),
    "\u7d22\u6797\uff1a\u971c\u4e4b\u65c5\u7968": (
        "\u7d22\u6797\u971c",
        "\u971c\u4e4b\u65c5",
    ),
    "\u8fea\u585e\u5c14\uff1a\u51ac\u65e5\u751c\u5fc3": (
        "\u8fea\u585e\u5c14\u51ac",
        "\u51ac\u65e5\u751c",
    ),
    "\u62c9\u6bd7\uff1a\u5c0f\u7ea2\u5e3d": (
        "\u62c9\u6bd7\u5c0f\u7ea2",
    ),
    "\u7ea2\u83b2\uff1a\u6697\u5f71": (
        "\u7ea2\u83b2\u6697",
    ),
    "\u5e03\u4e3d\u5fb7\uff1a\u9759\u9ed8\u8f68\u9053": (
        "\u5e03\u4e3d\u5fb7\u9759",
        "\u9759\u9ed8\u8f68",
    ),
    "\u666e\u4e3d\u74e6\u8482\uff1a\u4e0d\u53cb\u5584\u7684\u5973\u4ec6": (
        "\u666e\u4e3d\u74e6\u8482\u4e0d",
        "\u4e0d\u53cb\u5584",
        "\u5973\u4ec6",
    ),
}

MANUAL_SPECIAL_ALIASES: dict[str, tuple[str, ...]] = {
    "D：杀手妻子": ("D杀手", "杀手妻", "杀手妻子"),
    "索达：闪亮兔女郎": (
        "达：闪亮",
        "达闪亮",
        "索达：闪亮",
        "索达闪亮",
        "闪亮兔",
        "闪亮兔女",
        "闪亮兔女郎",
        "：闪亮兔",
    ),
    "安妮：奇迹仙女": ("安妮奇迹", "妮奇迹", "奇迹仙", "奇迹仙女"),
    "阿妮斯：闪耀夏日": ("阿妮斯闪", "妮斯闪耀", "闪耀夏", "闪耀夏日"),
    "索林：霜之旅票": ("索林霜", "林霜之旅", "霜之旅", "霜之旅票"),
    "迪塞尔：冬日甜心": ("迪塞尔冬", "塞尔冬日", "冬日甜", "冬日甜心"),
    "拉毗：小红帽": ("拉毗小红", "毗小红"),
    "红莲：暗影": ("红莲暗", "红莲暗影"),
    "布丽德：静默轨道": ("布丽德静", "丽德静默", "静默轨", "静默轨道"),
    "普丽瓦蒂：不友善的女仆": (
        "瓦蒂：不友善",
        "瓦蒂不友善",
        "不友善",
        "不友善的女",
        "不友善女仆",
        "友善的女仆",
        "女仆",
    ),
}

_SPECIAL_ALIAS_MIN_LEN = 3
_LONG_NAME_MIN_LEN = 5
_SAFE_ALIAS_MAX_LEN = 8


def canonicalize_colons(text: str) -> str:
    value = unicodedata.normalize("NFKC", text or "")
    for colon in COLON_CHARS:
        value = value.replace(colon, CANONICAL_COLON)
    return value


class NikkeNameMatcher:
    def __init__(self, dictionary_path: str, threshold: float = 80.0) -> None:
        self.dictionary_path = Path(dictionary_path)
        self.threshold = threshold
        self.special_names: list[str] = []
        self.collection_names: list[str] = []
        self.protected_names: list[str] = []
        self.protected_collection_names: list[str] = []
        self._load_error: Exception | None = None
        self.names = self.load_names()
        self._refresh_special_indexes()
        self._refresh_collection_index()
        self._rapidfuzz = None
        try:
            from rapidfuzz import fuzz, process  # type: ignore

            self._rapidfuzz = (process, fuzz)
        except Exception:
            self._rapidfuzz = None

    def load_names(self) -> list[str]:
        if self.dictionary_path.exists():
            try:
                data = json.loads(self.dictionary_path.read_text(encoding="utf-8-sig"))
                names = self._apply_dictionary_data(data)
                if len(names) < MIN_DICTIONARY_NAME_COUNT:
                    raise ValueError(
                        f"dictionary has too few names: {len(names)} < {MIN_DICTIONARY_NAME_COUNT}"
                    )
                self._load_error = None
                self._write_local_backup_for(names)
                return names
            except Exception as exc:
                self._load_error = exc
                restored = self._restore_from_local_backup()
                if restored:
                    self._load_error = None
                    return restored
                self._clear_loaded_data()
                return []
        self.dictionary_path.parent.mkdir(parents=True, exist_ok=True)
        restored = self._restore_from_local_backup()
        if restored:
            self._load_error = None
            return restored
        self._clear_loaded_data()
        return []

    def _clear_loaded_data(self) -> None:
        self.special_names = []
        self.collection_names = []
        self.protected_names = []
        self.protected_collection_names = []

    def _apply_dictionary_data(self, data: Any) -> list[str]:
        names = self._normalize_loaded_data(data)
        self.special_names = self._normalize_special_data(data, names)
        self.collection_names = self._normalize_collection_data(data, names)
        self.protected_names = self._normalize_protected_data(data, names)
        self.protected_collection_names = self._normalize_protected_collection_data(data, names)
        return names

    def _local_backup_path(self) -> Path:
        return self.dictionary_path.with_name(
            f"{self.dictionary_path.stem}{LOCAL_DICTIONARY_BACKUP_SUFFIX}{self.dictionary_path.suffix}"
        )

    def _dictionary_payload(
        self,
        names: list[str],
        collection_names: list[str],
        protected_names: list[str],
        protected_collection_names: list[str],
    ) -> dict[str, Any]:
        unique_names = {canonicalize_colons(name).strip() for name in names if name and str(name).strip()}
        unique_names.update(DEFAULT_EXTRA_NAMES)
        unique_names.update(DEFAULT_SPECIAL_NAMES)
        unique = sorted(unique_names)
        special_names = self._derive_special_names(unique)
        collection_names = self._normalize_known_names(collection_names, unique)
        protected_names = self._normalize_known_names(protected_names, unique)
        protected_collection_names = self._normalize_known_names(protected_collection_names, unique)
        collection_names = self._normalize_known_names(list(collection_names) + list(protected_collection_names), unique)
        return {
            "source": LOCAL_DICTIONARY_SOURCE,
            "count": len(unique),
            "names": unique,
            "special_count": len(special_names),
            "special_names": special_names,
            "collection_count": len(collection_names),
            "collection_names": collection_names,
            "protected_count": len(protected_names),
            "protected_names": protected_names,
            "protected_collection_count": len(protected_collection_names),
            "protected_collection_names": protected_collection_names,
        }

    def _write_dictionary_payload(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _write_local_backup(self) -> None:
        if len(getattr(self, "names", [])) < MIN_DICTIONARY_NAME_COUNT:
            return
        self._write_local_backup_for(list(self.names))

    def _write_local_backup_for(self, names: list[str]) -> None:
        if len(names) < MIN_DICTIONARY_NAME_COUNT:
            return
        payload = self._dictionary_payload(
            names,
            list(getattr(self, "collection_names", [])),
            list(getattr(self, "protected_names", [])),
            list(getattr(self, "protected_collection_names", [])),
        )
        self._write_dictionary_payload(self._local_backup_path(), payload)

    def _restore_from_local_backup(self) -> list[str]:
        backup_path = self._local_backup_path()
        if not backup_path.exists() or backup_path == self.dictionary_path:
            return []
        try:
            data = json.loads(backup_path.read_text(encoding="utf-8-sig"))
            names = self._apply_dictionary_data(data)
            if len(names) < MIN_DICTIONARY_NAME_COUNT:
                raise ValueError(
                    f"backup dictionary has too few names: {len(names)} < {MIN_DICTIONARY_NAME_COUNT}"
                )
            payload = self._dictionary_payload(
                names,
                list(getattr(self, "collection_names", [])),
                list(getattr(self, "protected_names", [])),
                list(getattr(self, "protected_collection_names", [])),
            )
            self._write_dictionary_payload(self.dictionary_path, payload)
            return names
        except Exception as exc:
            self._load_error = exc
            self._clear_loaded_data()
            return []

    def save_names(
        self,
        names: list[str],
        collection_names: list[str] | None = None,
        protected_names: list[str] | None = None,
        protected_collection_names: list[str] | None = None,
    ) -> None:
        self.dictionary_path.parent.mkdir(parents=True, exist_ok=True)
        unique_names = {canonicalize_colons(name).strip() for name in names if name and str(name).strip()}
        unique_names.update(DEFAULT_EXTRA_NAMES)
        unique_names.update(DEFAULT_SPECIAL_NAMES)
        unique = sorted(unique_names)
        special_names = self._derive_special_names(unique)
        collection_names = (
            list(collection_names)
            if collection_names is not None
            else list(getattr(self, "collection_names", []))
        )
        collection_names = self._normalize_collection_names(collection_names, unique)
        protected_names = (
            list(protected_names)
            if protected_names is not None
            else list(getattr(self, "protected_names", []))
        )
        protected_names = self._normalize_known_names(protected_names, unique)
        protected_collection_names = (
            list(protected_collection_names)
            if protected_collection_names is not None
            else list(getattr(self, "protected_collection_names", []))
        )
        protected_collection_names = self._normalize_known_names(protected_collection_names, unique)
        collection_names = self._normalize_known_names(list(collection_names) + list(protected_collection_names), unique)
        payload = self._dictionary_payload(unique, collection_names, protected_names, protected_collection_names)
        self._write_dictionary_payload(self.dictionary_path, payload)
        self._write_dictionary_payload(self._local_backup_path(), payload)
        if hasattr(self, "names"):
            self.names = list(payload["names"])
            self.special_names = list(payload["special_names"])
            self.collection_names = list(payload["collection_names"])
            self.protected_names = list(payload["protected_names"])
            self.protected_collection_names = list(payload["protected_collection_names"])
            self._refresh_special_indexes()
            self._refresh_collection_index()

    def ensure_dictionary(self) -> dict[str, Any]:
        if len(self.names) >= MIN_DICTIONARY_NAME_COUNT:
            return {"ok": True, "source": "cache", "count": len(self.names), "message": "loaded cache"}
        restored = self._restore_from_local_backup()
        if restored:
            self.names = restored
            self._refresh_special_indexes()
            self._refresh_collection_index()
            return {"ok": True, "source": "local_backup", "count": len(self.names), "message": "restored"}
        message = "dictionary is missing or too small, and no valid local backup is available"
        if getattr(self, "_load_error", None) is not None:
            message = f"{message}: {self._load_error}"
        return {"ok": False, "source": "local_backup", "count": len(self.names), "message": message}

    def _normalize_loaded_data(self, data: Any) -> list[str]:
        raw: list[Any] = []
        if isinstance(data, dict):
            raw.extend(data.get("names", []))
            raw.extend(data.get("special_names", []))
        elif isinstance(data, list):
            raw.extend(data)
        raw.extend(DEFAULT_EXTRA_NAMES)
        raw.extend(DEFAULT_SPECIAL_NAMES)
        return sorted({canonicalize_colons(str(item)).strip() for item in raw if str(item).strip()})

    def _normalize_special_data(self, data: Any, names: list[str]) -> list[str]:
        special = set(self._derive_special_names(names))
        if isinstance(data, dict) and isinstance(data.get("special_names"), list):
            special.update(canonicalize_colons(str(item)).strip() for item in data["special_names"] if str(item).strip())
        special.update(DEFAULT_SPECIAL_NAMES)
        return sorted(name for name in special if self._is_special_name(name))

    def _normalize_collection_data(self, data: Any, names: list[str]) -> list[str]:
        if not isinstance(data, dict) or not isinstance(data.get("collection_names"), list):
            return []
        return self._normalize_collection_names(data["collection_names"], names)

    def _normalize_collection_names(self, raw_names: list[Any], names: list[str]) -> list[str]:
        return self._normalize_known_names(raw_names, names)

    def _normalize_protected_data(self, data: Any, names: list[str]) -> list[str]:
        if not isinstance(data, dict) or not isinstance(data.get("protected_names"), list):
            return self._normalize_known_names(names, names)
        return self._normalize_known_names(data["protected_names"], names)

    def _normalize_protected_collection_data(self, data: Any, names: list[str]) -> list[str]:
        if not isinstance(data, dict) or not isinstance(data.get("protected_collection_names"), list):
            if isinstance(data, dict) and isinstance(data.get("collection_names"), list):
                return self._normalize_known_names(data["collection_names"], names)
            return []
        return self._normalize_known_names(data["protected_collection_names"], names)

    def _normalize_known_names(self, raw_names: list[Any], names: list[str]) -> list[str]:
        names_by_norm = {self.normalize_name(name): name for name in names if name and str(name).strip()}
        known_names: set[str] = set()
        for raw_name in raw_names:
            norm = self.normalize_name(str(raw_name))
            if norm in names_by_norm:
                known_names.add(names_by_norm[norm])
        return sorted(known_names)

    @staticmethod
    def _is_special_name(name: str) -> bool:
        return CANONICAL_COLON in canonicalize_colons(name)

    def _derive_special_names(self, names: list[str]) -> list[str]:
        return sorted({canonicalize_colons(name).strip() for name in names if self._is_special_name(name)})

    def _refresh_special_indexes(self) -> None:
        self.special_names = self._derive_special_names(list(self.names) + list(getattr(self, "special_names", [])))
        self._special_by_base: dict[str, list[str]] = {}
        for name in self.special_names:
            base = self._special_base_norm(name)
            self._special_by_base.setdefault(base, []).append(name)
        self._special_aliases = self._build_special_aliases()

    def _refresh_collection_index(self) -> None:
        self._collection_name_norms = {
            self.normalize_name(name)
            for name in getattr(self, "collection_names", [])
            if name and str(name).strip()
        }

    def has_collection_item(self, name: str) -> bool:
        if not name or str(name).strip().lower() == "unknown":
            return False
        return self.normalize_name(name) in getattr(self, "_collection_name_norms", set())

    @staticmethod
    def normalize_name(text: str) -> str:
        value = canonicalize_colons(text).strip().replace(" ", "")
        value = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9.\uff1a\-]", "", value)
        return value.upper()

    def _special_base_norm(self, name: str) -> str:
        return self.normalize_name(name).split(CANONICAL_COLON, 1)[0]

    def _special_suffix_norm(self, name: str) -> str:
        parts = self.normalize_name(name).split(CANONICAL_COLON, 1)
        return parts[1] if len(parts) > 1 else ""

    def _compact_special_text(self, text: str) -> str:
        normalized = self.normalize_name(text)
        return re.sub(r"[\uff1a:\s.\-·・_/\\（）()\[\]【】「」『』,，。]+", "", normalized)

    def _register_special_alias(self, alias_map: dict[str, set[str]], alias: str, target: str) -> None:
        compact = self._compact_special_text(alias)
        if len(compact) < _SPECIAL_ALIAS_MIN_LEN:
            return
        if compact == self._special_base_norm(target):
            return
        alias_map[compact].add(target)

    @staticmethod
    def _has_cjk(text: str) -> bool:
        return bool(re.search(r"[\u4e00-\u9fff]", text or ""))

    def _is_safe_alias_for_target(self, compact: str, target: str, name_compacts: dict[str, str]) -> bool:
        if len(compact) < _SPECIAL_ALIAS_MIN_LEN:
            return False
        if re.fullmatch(r"\d+", compact):
            return False
        if not self._has_cjk(compact) and len(compact) < _LONG_NAME_MIN_LEN:
            return False
        if compact == self._special_base_norm(target):
            return False
        target_compact = self._compact_special_text(target)
        if compact not in target_compact:
            return False
        owners = {name for name, name_compact in name_compacts.items() if compact in name_compact}
        return not (owners - {target})

    def _register_safe_alias(
        self,
        alias_map: dict[str, set[str]],
        alias: str,
        target: str,
        name_compacts: dict[str, str],
    ) -> None:
        compact = self._compact_special_text(alias)
        if not self._is_safe_alias_for_target(compact, target, name_compacts):
            return
        alias_map[compact].add(target)

    @staticmethod
    def _is_ordered_subsequence(needle: str, haystack: str) -> bool:
        if not needle:
            return False
        start = 0
        for char in needle:
            found = haystack.find(char, start)
            if found < 0:
                return False
            start = found + 1
        return True

    def _hint_belongs_to_name(self, compact: str, name_compact: str) -> bool:
        return compact in name_compact or self._is_ordered_subsequence(compact, name_compact)

    def _is_safe_hint_for_target(self, compact: str, target: str, name_compacts: dict[str, str]) -> bool:
        if len(compact) < _SPECIAL_ALIAS_MIN_LEN:
            return False
        if re.fullmatch(r"\d+", compact):
            return False
        if not self._has_cjk(compact) and len(compact) < _LONG_NAME_MIN_LEN:
            return False
        if compact == self._special_base_norm(target):
            return False
        target_compact = self._compact_special_text(target)
        if not self._hint_belongs_to_name(compact, target_compact):
            return False
        owners = {
            name
            for name, name_compact in name_compacts.items()
            if self._hint_belongs_to_name(compact, name_compact)
        }
        return not (owners - {target})

    def _register_hint_alias(
        self,
        alias_map: dict[str, set[str]],
        alias: str,
        target: str,
        name_compacts: dict[str, str],
    ) -> None:
        compact = self._compact_special_text(alias)
        if not self._is_safe_hint_for_target(compact, target, name_compacts):
            return
        alias_map[compact].add(target)

    def _safe_hint_matches(
        self,
        hint: str,
        target: str,
        variant_norm: str,
        variant_compact: str,
        name_compacts: dict[str, str],
    ) -> bool:
        compact = self._compact_special_text(hint)
        if not self._is_safe_hint_for_target(compact, target, name_compacts):
            return False
        return self.normalize_name(hint) in variant_norm or compact in variant_compact

    def _iter_name_fragments(self, compact: str, min_len: int = _SPECIAL_ALIAS_MIN_LEN) -> list[tuple[str, int, int]]:
        fragments: list[tuple[str, int, int]] = []
        max_len = min(len(compact), _SAFE_ALIAS_MAX_LEN)
        for length in range(min_len, max_len + 1):
            for start in range(0, len(compact) - length + 1):
                fragments.append((compact[start : start + length], start, start + length))
        return fragments

    def _build_special_aliases(self) -> dict[str, str]:
        alias_map: dict[str, set[str]] = defaultdict(set)
        name_compacts = {name: self._compact_special_text(name) for name in self.names if name}
        standalone_norms = {
            self.normalize_name(name)
            for name in self.names
            if name and not self._is_special_name(name)
        }
        for special_name in self.special_names:
            norm = self.normalize_name(special_name)
            if CANONICAL_COLON not in norm:
                continue
            base, suffix = norm.split(CANONICAL_COLON, 1)
            base_compact = self._compact_special_text(base)
            suffix_compact = self._compact_special_text(suffix)
            full_compact = self._compact_special_text(norm)
            suffix_is_standalone = suffix_compact in standalone_norms

            self._register_special_alias(alias_map, full_compact, special_name)
            if not suffix_is_standalone:
                self._register_special_alias(alias_map, suffix_compact, special_name)

                max_suffix_len = min(len(suffix_compact), 8)
                for length in range(_SPECIAL_ALIAS_MIN_LEN, max_suffix_len + 1):
                    for start in range(0, len(suffix_compact) - length + 1):
                        self._register_special_alias(alias_map, suffix_compact[start : start + length], special_name)

            for take in range(1, min(len(suffix_compact), 6) + 1):
                self._register_special_alias(alias_map, base_compact + suffix_compact[:take], special_name)

            # OCR often drops the first character of a long special name when the
            # card label starts scrolling. Keep base-tail + suffix-prefix aliases
            # like "达闪亮" without ever registering the bare base name.
            for tail_len in range(1, min(len(base_compact), 3) + 1):
                for take in range(2, min(len(suffix_compact), 7) + 1):
                    self._register_special_alias(alias_map, base_compact[-tail_len:] + suffix_compact[:take], special_name)

            boundary = len(base_compact)
            for alias, start, end in self._iter_name_fragments(full_compact):
                if end <= boundary:
                    continue
                if suffix_is_standalone and start >= boundary:
                    continue
                self._register_safe_alias(alias_map, alias, special_name, name_compacts)

            for alias in (*LONG_NAME_HINTS.get(special_name, ()), *MANUAL_SPECIAL_ALIASES.get(special_name, ())):
                self._register_hint_alias(alias_map, alias, special_name, name_compacts)

        for name in self.names:
            if not name or self._is_special_name(name):
                continue
            compact = name_compacts.get(name, "")
            if len(compact) < _LONG_NAME_MIN_LEN:
                continue
            self._register_safe_alias(alias_map, compact, name, name_compacts)
            for alias, _, _ in self._iter_name_fragments(compact):
                self._register_safe_alias(alias_map, alias, name, name_compacts)

        return {alias: next(iter(targets)) for alias, targets in alias_map.items() if len(targets) == 1}

    def _special_alias_match(self, variant_norm: str, fuzz: Any | None) -> tuple[str, float, bool]:
        compact_variant = self._compact_special_text(variant_norm)
        if not compact_variant:
            return "", 0.0, False
        if compact_variant in self._special_aliases:
            return self._special_aliases[compact_variant], 100.0, True

        best_name = ""
        best_score = 0.0
        for alias, target in self._special_aliases.items():
            if alias in compact_variant:
                score = 96.0 + min(len(alias), 10) * 0.2
            elif (
                fuzz
                and len(compact_variant) >= 4
                and compact_variant not in self._special_by_base
                and CANONICAL_COLON in variant_norm
            ):
                score = float(fuzz.partial_ratio(compact_variant, alias))
            else:
                continue
            if score > best_score:
                best_name = target
                best_score = score

        if best_name and best_score >= 92.0:
            return best_name, min(best_score, 100.0), True
        return "", 0.0, False

    def _safe_variants(self, raw: str) -> list[str]:
        variants = [canonicalize_colons(raw)]
        stripped = re.sub(r"^[A-Za-z0-9]+(?=[\u4e00-\u9fff])", "", variants[0])
        if stripped and stripped not in variants:
            variants.append(stripped)

        if len(stripped) >= 3:
            suffix = stripped[1:]
            suffix_norm = self.normalize_name(suffix)
            if suffix_norm and any(self.normalize_name(name).startswith(suffix_norm) for name in self.names):
                variants.append(suffix)
        return variants

    def _special_score(self, variant_norm: str, special_name: str, fuzz: Any | None) -> float:
        special_norm = self.normalize_name(special_name)
        base_norm = self._special_base_norm(special_name)
        suffix_norm = self._special_suffix_norm(special_name)
        if not variant_norm or not base_norm or not variant_norm.startswith(base_norm):
            return 0.0

        compact_variant = variant_norm.replace(CANONICAL_COLON, "")
        compact_special = special_norm.replace(CANONICAL_COLON, "")
        compact_base = base_norm.replace(CANONICAL_COLON, "")
        compact_suffix = suffix_norm.replace(CANONICAL_COLON, "")
        suffix_part = compact_variant[len(compact_base) :]

        if variant_norm == special_norm or compact_variant == compact_special:
            return 100.0

        has_colon = CANONICAL_COLON in variant_norm
        common = 0
        for left, right in zip(suffix_part, compact_suffix):
            if left != right:
                break
            common += 1

        if has_colon or common > 0:
            missing_penalty = min(10.0, max(0, len(compact_special) - len(compact_variant)) * 0.7)
            return 94.0 + min(5.0, common * 1.5) - missing_penalty

        if fuzz and suffix_part:
            ratio = float(fuzz.ratio(compact_variant, compact_special))
            partial = float(fuzz.partial_ratio(compact_variant, compact_special))
            if ratio >= 82.0 or partial >= 90.0:
                return max(ratio, partial - 8.0)
        return 0.0

    def _best_special_match(self, raw: str, fuzz: Any | None) -> tuple[str, float, bool]:
        best_name = ""
        best_score = 0.0
        has_special_evidence = False
        for variant in self._safe_variants(raw):
            variant_norm = self.normalize_name(variant)
            if not variant_norm:
                continue
            alias_name, alias_score, alias_evidence = self._special_alias_match(variant_norm, fuzz)
            if alias_name:
                return alias_name, alias_score, alias_evidence
            variant_compact = self._compact_special_text(variant_norm)
            has_special_evidence = has_special_evidence or CANONICAL_COLON in variant_norm
            name_compacts = {name: self._compact_special_text(name) for name in self.names if name}
            for hinted_name, hints in LONG_NAME_HINTS.items():
                if hinted_name not in self.names:
                    continue
                if any(self._safe_hint_matches(hint, hinted_name, variant_norm, variant_compact, name_compacts) for hint in hints):
                    return hinted_name, 100.0, True
            for special_name in self.special_names:
                score = self._special_score(variant_norm, special_name, fuzz)
                if score > 0:
                    base_norm = self._special_base_norm(special_name)
                    compact_variant = variant_norm.replace(CANONICAL_COLON, "")
                    compact_base = base_norm.replace(CANONICAL_COLON, "")
                    suffix_part = compact_variant[len(compact_base) :]
                    has_special_evidence = has_special_evidence or bool(suffix_part) or CANONICAL_COLON in variant_norm
                if score > best_score:
                    best_name = special_name
                    best_score = score
        return best_name, best_score, has_special_evidence

    def match_name(self, raw_text: str) -> dict:
        raw = (raw_text or "").strip()
        if not raw:
            return {"raw_text": raw_text, "matched_name": "unknown", "score": 0.0}
        if not self.names:
            return {"raw_text": raw_text, "matched_name": raw, "score": 0.0}

        normalized_names = [(name, self.normalize_name(name)) for name in self.names]
        best_name = raw
        best_score = 0.0
        fuzz = self._rapidfuzz[1] if self._rapidfuzz else None
        special_name, special_score, has_special_evidence = self._best_special_match(raw, fuzz)

        for variant in self._safe_variants(raw):
            variant_norm = self.normalize_name(variant)
            if not variant_norm:
                continue
            for name, name_norm in normalized_names:
                if variant_norm == name_norm:
                    score = 100.0
                elif len(variant_norm) >= 2 and name_norm.startswith(variant_norm):
                    score = 98.0 - min(8.0, max(0, len(name_norm) - len(variant_norm)) * 0.4)
                elif len(name_norm) >= 2 and variant_norm.startswith(name_norm):
                    score = 94.0 - min(8.0, max(0, len(variant_norm) - len(name_norm)) * 0.5)
                elif fuzz:
                    score = float(fuzz.ratio(variant_norm, name_norm))
                else:
                    from difflib import SequenceMatcher

                    score = SequenceMatcher(None, variant_norm, name_norm).ratio() * 100.0

                if has_special_evidence and name_norm in self._special_by_base:
                    score -= 14.0

                if re.fullmatch(r"[A-Z0-9.\-]{1,3}", name_norm):
                    if not re.fullmatch(r"[A-Z0-9.\-]{1,4}", variant_norm):
                        score = 0.0

                if score > best_score:
                    best_name = name
                    best_score = score

        if special_name and special_score >= 78.0:
            special_base = self._special_base_norm(special_name)
            best_base = self.normalize_name(best_name)
            if special_score >= 92.0 or (
                has_special_evidence and (best_base == special_base or special_score >= best_score - 4.0)
            ):
                return {"raw_text": raw, "matched_name": special_name, "score": special_score}

        if best_score >= self.threshold:
            return {"raw_text": raw, "matched_name": best_name, "score": best_score}
        return {"raw_text": raw, "matched_name": raw, "score": best_score}
