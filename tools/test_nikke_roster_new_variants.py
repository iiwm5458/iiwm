"""Regression checks for newly registered NIKKE variant names and safe aliases."""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROSTER_PATH = ROOT / "dataanalysis" / "arena_ocr_tool" / "data" / "nikke_names.json"
sys.path.insert(0, str(ROOT / "dataanalysis" / "arena_ocr_tool"))
from recognizer.nikke_name_matcher import NikkeNameMatcher  # noqa: E402


NEW_VARIANTS = {
    "贝洛塔：南瓜女巫",
    "玛丽安：女王",
    "长发公主：圣域",
    "红莲：弑神",
}


class NikkeRosterNewVariantsTest(unittest.TestCase):
    def setUp(self):
        self.roster = json.loads(ROSTER_PATH.read_text(encoding="utf-8"))
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        temp_roster = Path(self.temp_dir.name) / "nikke_names.json"
        shutil.copyfile(ROSTER_PATH, temp_roster)
        # Keep the matcher-created recovery copy outside the working tree.
        self.matcher = NikkeNameMatcher(str(temp_roster))

    def test_roster_membership_and_metadata_are_consistent(self):
        names = set(self.roster["names"])
        special_names = set(self.roster["special_names"])
        protected_names = set(self.roster["protected_names"])
        collection_names = set(self.roster["collection_names"])

        self.assertEqual(self.roster["count"], len(names))
        self.assertEqual(self.roster["protected_count"], len(protected_names))
        self.assertEqual(special_names, {name for name in names if "：" in name})
        self.assertEqual(self.roster["special_count"], len(special_names))
        self.assertTrue(NEW_VARIANTS <= names)
        self.assertTrue(NEW_VARIANTS <= special_names)
        self.assertTrue(NEW_VARIANTS <= protected_names)
        self.assertFalse(NEW_VARIANTS & collection_names)

    def test_full_names_and_safe_suffix_evidence_match_the_new_variants(self):
        for raw_text, expected in (
            ("贝洛塔：南瓜女巫", "贝洛塔：南瓜女巫"),
            ("玛丽安：女王", "玛丽安：女王"),
            ("长发公主：圣域", "长发公主：圣域"),
            ("红莲：弑神", "红莲：弑神"),
            ("贝洛塔南", "贝洛塔：南瓜女巫"),
            ("南瓜女巫", "贝洛塔：南瓜女巫"),
            ("玛丽安女", "玛丽安：女王"),
            ("长发公主圣", "长发公主：圣域"),
            ("红莲弑", "红莲：弑神"),
        ):
            with self.subTest(raw_text=raw_text):
                self.assertEqual(self.matcher.match_name(raw_text)["matched_name"], expected)

    def test_existing_base_names_do_not_upgrade_without_suffix_evidence(self):
        for base_name in ("贝洛塔", "长发公主", "红莲"):
            with self.subTest(base_name=base_name):
                self.assertEqual(self.matcher.match_name(base_name)["matched_name"], base_name)
                self.assertNotIn(base_name, self.matcher._special_aliases)

        # 玛丽安 currently has no separate base-name entry.  It must still not
        # be registered as an implicit special alias; re-audit if a base entry
        # is introduced in a future roster update.
        self.assertNotIn("玛丽安", self.matcher._special_aliases)

    def test_short_suffixes_are_not_registered_as_special_aliases(self):
        for suffix, unexpected in (
            ("女王", "玛丽安：女王"),
            ("圣域", "长发公主：圣域"),
            ("弑神", "红莲：弑神"),
        ):
            with self.subTest(suffix=suffix):
                self.assertNotIn(suffix, self.matcher._special_aliases)
                self.assertNotEqual(self.matcher.match_name(suffix)["matched_name"], unexpected)


if __name__ == "__main__":
    unittest.main(verbosity=2)
