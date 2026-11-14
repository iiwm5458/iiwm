"""Regression coverage for overseas capture-time lineup snapshot refreshes."""

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "nikke_round_config.json"
STITCHER_PATH = PROJECT_ROOT / "nikke_round_stitcher.py"


def load_stitcher():
    spec = importlib.util.spec_from_file_location(
        "nikke_round_stitcher_capture_snapshot_test", STITCHER_PATH
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class CaptureSeasonLineupSnapshotTest(unittest.TestCase):
    def setUp(self):
        self.worker = load_stitcher()
        # Never permit a unit test to reach the Win32 cursor/click bridge.
        # Individual tests can still assert the higher-level ``click`` call,
        # but any newly introduced screen-ratio route remains inert by default.
        self._screen_click_guard = patch.object(self.worker, "click_screen_point")
        self._screen_click_guard.start()
        self.addCleanup(self._screen_click_guard.stop)

    def config_for(self, server, low_memory=False):
        config = self.worker.load_config(CONFIG_PATH)
        config["runtime_server"] = server
        config["low_memory"] = low_memory
        return config

    @staticmethod
    def players(count, prefix="player"):
        return [
            {
                "key": f"{prefix}{index:02d}",
                "nickname": f"nickname{index:02d}",
                "aliases": [f"nickname{index:02d}", f"alias{index:02d}"],
                "group_index": index,
                "slot_index": index,
                "profile": f"profile{index:02d}",
                "image": Image.new("RGB", (8, 8), (index, 0, 0)),
            }
            for index in range(1, count + 1)
        ]

    def test_refresh_replaces_only_visual_cache_and_uses_existing_points(self):
        config = self.config_for("global")
        players = self.players(8)
        expected_identity = [
            (
                player["key"],
                player["nickname"],
                list(player["aliases"]),
                player["group_index"],
                player["slot_index"],
                player["profile"],
            )
            for player in players
        ]
        refreshed = [Image.new("RGB", (8, 8), (0, index, 0)) for index in range(1, 9)]
        clicked = []
        captured_labels = []

        def capture(_config, _parts_dir, label, **kwargs):
            captured_labels.append((label, kwargs))
            return refreshed[len(captured_labels) - 1]

        with patch.object(
            self.worker, "screenshot", return_value=Image.new("RGB", (3440, 1440), "black")
        ), patch.object(
            self.worker,
            "click",
            side_effect=lambda point, _transform: clicked.append(list(point)),
        ), patch.object(self.worker, "wait_for_player_lineup_page") as wait, patch.object(
            self.worker, "capture_player_image", side_effect=capture
        ), patch.object(self.worker, "press_escape_twice") as dismiss:
            self.worker.refresh_cached_players_from_bracket(
                config,
                PROJECT_ROOT / "_unused",
                players,
                "top8_avatars",
                "top8_lineup",
            )

        self.assertEqual(clicked, config["clicks"]["top8_avatars"])
        self.assertEqual(wait.call_count, 8)
        self.assertEqual(dismiss.call_count, 8)
        self.assertEqual(len(captured_labels), 8)
        for index, player in enumerate(players):
            self.assertIs(player["image"], refreshed[index])
            self.assertNotIn("image_path", player)
            self.assertEqual(
                (
                    player["key"],
                    player["nickname"],
                    player["aliases"],
                    player["group_index"],
                    player["slot_index"],
                    player["profile"],
                ),
                expected_identity[index],
            )
            self.assertFalse(captured_labels[index][1]["return_metadata"])

    def test_low_memory_refresh_keeps_old_file_and_writes_stage_cache(self):
        config = self.config_for("hmt", low_memory=True)
        player = self.players(1)[0]
        original = Image.new("RGB", (8, 8), "red")
        refreshed = Image.new("RGB", (8, 8), "green")
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            old_path = temp_path / "initial.png"
            original.save(old_path)
            player.pop("image")
            player["image_path"] = str(old_path)

            self.worker.replace_cached_player_image(
                config, player, refreshed, temp_path / "top8_lineup_cache"
            )

            self.assertTrue(old_path.exists())
            self.assertNotIn("image", player)
            cached_path = Path(player["image_path"])
            self.assertTrue(cached_path.exists())
            self.assertNotEqual(cached_path, old_path)
            with Image.open(cached_path) as cached:
                self.assertEqual(cached.convert("RGB").getpixel((0, 0)), (0, 128, 0))

    def test_refresh_rejects_point_count_mismatch_before_clicking(self):
        config = self.config_for("global")
        players = self.players(2)
        with patch.object(self.worker, "click") as click:
            with self.assertRaises(SystemExit):
                self.worker.refresh_cached_players_from_bracket(
                    config,
                    PROJECT_ROOT / "_unused",
                    players,
                    "top8_avatars",
                    "top8_lineup",
                )
        click.assert_not_called()

    def test_season_refresh_order_is_overseas_only(self):
        for server in ("global", "hmt", "cn"):
            with self.subTest(server=server), tempfile.TemporaryDirectory() as temp_dir:
                config = self.config_for(server)
                events = []

                def capture_seed(_config, group_index, _parts_dir, _ocr):
                    return self.players(8, f"group{group_index}_seed")

                def collect_group(
                    _config,
                    _parts_dir,
                    group_size,
                    _post_data_mode,
                    stage_pairs,
                    group_index,
                    _stage_code,
                ):
                    image = Image.new("RGB", (2, 2), "white")
                    if group_size == 8:
                        return image, [
                            {"key": f"g{group_index}_32_{index}", "nickname": f"g{group_index}_32_{index}", "image": image.copy()}
                            for index in range(1, 5)
                        ]
                    if group_size == 4:
                        return image, [
                            {"key": f"g{group_index}_16_{index}", "nickname": f"g{group_index}_16_{index}", "image": image.copy()}
                            for index in range(1, 3)
                        ]
                    return image, [
                        {
                            "key": f"winner{group_index}",
                            "nickname": f"winner{group_index}",
                            "image": image.copy(),
                        }
                    ]

                def collect_top8(
                    _config,
                    _parts_dir,
                    group_size,
                    _post_data_mode,
                    stage_pairs,
                    _stage_code,
                ):
                    events.append(f"stage{group_size}")
                    return Image.new("RGB", (2, 2), "white"), [pair[0] for pair in stage_pairs]

                def refresh(_config, _parts_dir, players, avatar_key, stage_label):
                    events.append(f"refresh:{avatar_key}:{len(players)}:{stage_label}")

                # ``run_season_capture`` switches GROUP tabs before every
                # cached-stage collection.  Patch that boundary explicitly:
                # unlike the other capture helpers it reaches the real
                # screen-ratio click path, so leaving it live would move and
                # click the user's mouse during a unit test.
                with patch.object(self.worker, "print_screen_context"), patch.object(
                    self.worker, "click_group_tab"
                ), patch.object(
                    self.worker, "get_season_ocr", return_value=None
                ), patch.object(
                    self.worker, "capture_seed_players_for_group", side_effect=capture_seed
                ), patch.object(
                    self.worker, "collect_cached_group_stage", side_effect=collect_group
                ), patch.object(
                    self.worker,
                    "stitch_grid_with_gap",
                    return_value=Image.new("RGB", (2, 2), "white"),
                ), patch.object(self.worker, "save_final_image"), patch.object(
                    self.worker,
                    "navigate_from_group_to_top8",
                    side_effect=lambda _config: events.append("navigate"),
                ), patch.object(
                    self.worker, "collect_cached_top8_stage", side_effect=collect_top8
                ), patch.object(
                    self.worker, "refresh_cached_players_from_bracket", side_effect=refresh
                ), patch.object(
                    self.worker,
                    "stitch_pyramid_layers",
                    return_value=Image.new("RGB", (2, 2), "white"),
                ):
                    self.worker.run_season_capture(
                        config,
                        Path(temp_dir) / "64进32全部战斗数据（详）.png",
                        Path(temp_dir) / "parts",
                    )

                self.assertLess(events.index("navigate"), events.index("stage8"))
                self.assertLess(events.index("stage8"), events.index("stage4"))
                self.assertLess(events.index("stage4"), events.index("stage2"))
                refresh_events = [event for event in events if event.startswith("refresh:")]
                if server == "cn":
                    self.assertEqual(refresh_events, [])
                else:
                    self.assertEqual(
                        refresh_events,
                        [
                            "refresh:top8_avatars:8:top8_lineup",
                            "refresh:top8_final_avatars:2:final_lineup",
                        ],
                    )
                    self.assertLess(events.index(refresh_events[0]), events.index("stage8"))
                    self.assertGreater(events.index(refresh_events[1]), events.index("stage4"))
                    self.assertLess(events.index(refresh_events[1]), events.index("stage2"))


if __name__ == "__main__":
    unittest.main()
