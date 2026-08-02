# P0-UCLA-PROD — raw-input executability census (2026-08-02)

Follow-up to `PRODUCTION_ATTEMPT_1.md`: the cheapest discriminating action it
registered. The production runner was executed directly on each of the 26
manifest-verified raw event files (worktree copies staged and SHA-verified for
attempt 1). Per-event exit status and crash site only; no harness, no
pipeline stage, no scientific readout, no benchmark surface produced or
inspected. Outputs under `worktree/lead_controls/raw_census/<event>/`; log at
`/Users/artuskg/marsquake_runs/20260802_ucla_prod/raw_census.log`.

## Result: 22 of 26 raw events complete; 4 fail at three further shipped-code sites

PASS (22, with per-channel UCLA detection rows U/V/W):
S0105a 25/25/20 · S0173a 15/13/10 · S0189a 15/17/12 · S0235b 8/11/5 ·
S0290b 18/16/10 · S0325a 9/6/17 · S0474a 13/13/7 · S0484b 15/18/21 ·
S0802a 16/20/15 · S0820a 10/12/8 · S0864a 11/9/11 · S0916d 12/13/13 ·
S0918a 12/11/6 · S1012d 20/20/14 · S1022a 10/15/13 · S1039b 13/14/10 ·
S1048d 11/14/11 · S1102a 6/4/7 · S1133c 7/8/10 · S1153a 11/8/10 ·
S1157a 6/4/10 · S1415a 23/20/20

FAIL (4, all members of the 23-event vespagram stack set; the three
validation events S1102a/S1153a/S1415a all PASS):

| Event | Crash | Class |
| --- | --- | --- |
| S1197a | `aa(_,2): out of bound (0x0)` | empty glitch list indexed (same site as chained attempt) |
| S1222a | `aa(_,2): out of bound (0x0)` | same |
| S0784a | `data(0): subscripts must be integers 1 to (2^63)-1` | zero subscript computed at a detection edge |
| S1015f | `filtfilt: X must be a vector or matrix with length greater than 6` | too-short segment (data gap) fed to filtering |

## Interpretation

- Zero raw events crash at the `I2(1)` STA/LTA site that killed 22/26 events
  in the chained attempt — confirming the chained failures were caused by MPS
  pre-cleaning (detector starvation), not by these events' raw data.
- Shipped UCLA_v4 carries at least four distinct input-dependent fragilities
  (`I2` starvation, empty `aa` list, zero subscript, short-segment filtfilt).
  It is not robust software; it presupposes glitch-rich, gap-free input.
- A UCLA-on-raw lane — the card's pre-recorded non-executed alternative — is
  executable for 22/26 events (19 stack + all 3 validation events). The
  chained lane remains inexecutable as recorded in attempt 1.

Census outputs are execution evidence only and must not be reused as lane
products; any registered lane regenerates its products fresh.
