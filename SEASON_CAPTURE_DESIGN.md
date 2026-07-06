# C ARENA season capture design

## Goal

Capture all GROUP 64->32, 32->16 and 16-player matches, then capture the TOP8
championship bracket without repeatedly opening and recognizing the same player
profile.

## Reuse model

1. Start from GROUP01 and visit the eight initial players in each GROUP.
2. Store each player's profile image, lineup image and OCR result once, keyed by
   player ID.
3. For later result pages, identify both players and reference their cached
   profile/lineup data instead of opening both profiles again.
4. Capture only new match-result data. Compositing and JSON/Excel export use the
   cached player records plus the current match record.
5. Repeat for GROUP01-GROUP08, then enter the TOP8 championship bracket and
   reuse the same player cache.

## Cache shape

```text
players[player_id]
  nickname
  profile_image
  lineup_image
  lineup_ocr
  card_powers
  profile_fingerprint

matches[stage/group/match]
  attacker_player_id
  defender_player_id
  simple_result
  detailed_round_results
  winner_player_id
```

Player matching should prefer player ID. Where a result page does not expose an
ID, use normalized nickname plus a small avatar/profile fingerprint, then reject
ambiguous matches instead of silently choosing one.

## Outputs

- GROUP01-GROUP08 images for 64-player, 32-player and 16-player stages.
- TOP8 championship pyramid image.
- Optional background-board variants.
- Optional JSON and Excel assembled from cached player data and match records.

## Reliability

- Save cache checkpoints after each player and each match so Alt+2 or a crash
  can resume without repeating completed OCR.
- Keep raw screenshots until final export succeeds.
- Do not overwrite a high-confidence player record with a weaker later match.

## Pending navigation

The exact UI actions that move from the GROUP promotion bracket to the TOP8
championship bracket are intentionally pending. The one-click execution button
must stay non-operational until that transition is defined and verified.
