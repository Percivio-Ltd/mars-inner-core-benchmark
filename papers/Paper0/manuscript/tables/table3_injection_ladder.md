# Table 3 — injection-recovery ladder

Source: `history/20260801_inject_recov/recovery_table.csv` (SHA-256 `0b7a66a46e3f…`).

| alpha | Global argmax (time s, slowness s/deg, power, support) | Argmax in target box | Target-box max power | Target-box max time (s) |
| --- | --- | --- | --- | --- |
| 0 | (663.80, -3.64, 0.9327, 23) | no | 0.7736 | 601.95 |
| 0.25 | (602.95, -6.46, 1.2483, 23) | yes | 1.2483 | 602.95 |
| 0.5 | (603.30, -6.46, 1.6204, 23) | yes | 1.6204 | 603.30 |
| 1 | (603.50, -6.46, 2.1772, 23) | yes | 2.1772 | 603.50 |
| 2 | (603.65, -6.46, 3.0591, 23) | yes | 3.0591 | 603.65 |
| 4 | (603.80, -6.46, 4.6325, 23) | yes | 4.6325 | 603.80 |
| 8 | (603.90, -6.46, 7.5507, 23) | yes | 7.5507 | 603.90 |

a) alpha = 0 is the canonical enforced lane; injected lanes (alpha > 0) are exploratory by necessity (injection invalidates the alignment-stage provenance hash by construction).

b) the alpha = 8 literal positive control FAILED on the time axis (603.90 s, two 0.05-s cells from 604.0) and is adjudicated a control-tolerance design flaw; it is not quotable as a passed literal control (draft section 5.4; Table S1e).
