#!/usr/bin/env python3
"""Generate the DRAFT_seismica.md figures and tables from recorded artifacts.

Rendering-only: every scientific number is read from a pinned recorded
artifact, re-derived quantities are asserted against the recorded values
before any figure is written, and a provenance sidecar records input and
output hashes. A pin or control mismatch aborts with a nonzero exit and no
outputs.

Inputs and their authorities are enumerated in NUMBERS.md. The full-set
vespagram NPZ is the S3-parked LOO full-set product
(paper0_evidence/20260726_loo_influence/full_set.npz), fetched to
results/manuscript_inputs/ and byte-verified against the loo_verdict.json pin.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
OUT_DIR = Path(__file__).resolve().parent
FIG_DIR = OUT_DIR / "figures"
TABLE_DIR = OUT_DIR / "tables"

INPUT_PINS = {
    "results/manuscript_inputs/full_set.npz": "f4b3a03af9bff68d6fa2750e9eaaa28511e638de32f569c34e40152483c9c280",
    "history/20260726_publication_assessment/sig_statement_reading.json": "4af7b025e990254fc39dc1219dca163b5e4a3638b206d0cba4fe944c6f6bea0d",
    "history/20260726_publication_assessment/loo/loo_table.csv": "abf357fd0cc525450ff19c5e568a36f62ee312a4951f04b052132e8f5058ae3b",
    "results/tables/peak_comparison.csv": "8df5f5c85473460e19e10021db52c997945f3bee6f4f8aac461251a5a0bf07ce",
    "results/bootstrap/type1_pkikp_occupancy.npz": "f4b22d095bbd00e8ebb6fdcf16d7f9f11a49d9c03256abb1d579eb77d841e3c5",
    "history/20260725_scout_pass2/t2read_feature_competition.json": "53793b24c34956257dc32ccd92ba1d7eabcc312e3a59aeb2bfa430f01778bb91",
    "history/20260725_scout_pass3/comp_assoc_reading.json": "d8140daf2141a1ff5f66010d0ced5d356cd4f4f74d64be7013c256308042842f",
    "history/20260725_research_pipeline_restock/ablpolop_peak_comparison_operator_ablation.csv": "0f927fd408b4a9390b0a91fcd3b3692991cf24d37b788e02d2f4b3dcf851c344",
    "history/20260725_research_pipeline_restock/t3power_power_comparison.json": "798268b094a3adb7dc954c26e12f6308f1b12c698915b12937121c1fa2ba34ad",
    "history/20260725_scout_pass2/taup_phase_prediction_comparison.csv": "e7e8cfee29fff46b84f0e767137d2b646765ed875b7bdded21a9d4ab73dc8c7a",
    "history/20260801_mars_scramble/null_table.csv": "12aa226d7e755b9bc691de9d7d1872b25041ee73993f3829c25eb5849fbe06c6",
    "history/20260801_mars_scramble/frozen_stats.json": "0330244276493fa7470ad685feefe0115cf5577ce428ef1eaa3d16124eb134c4",
    "history/20260801_inject_recov/recovery_table.csv": "0b7a66a46e3f2e3f588676f54235366b95a5440d689d69dcff3f9a53719cd517",
}

TARGET_BOX_T = (584.0, 624.0)
TARGET_BOX_S = (-7.1, -5.9)
PUBLISHED_PAIR = (604.0, -6.5)
PUBLISHED_ERR = (2.0, 0.6)
BRANCH_BOUNDARY_S = 632.0
ARGMAX_WINDOW = (550.0, 700.0)
RECORDED_FLIPS = {"S0325a", "S0474a", "S0864a", "S1012d", "S1022a", "S1039b"}
RECORDED_FWE_FLIPS = {"S0474a", "S1012d", "S1022a", "S1039b"}
TAUP_REFERENCE_P_T_S = 224.131
TAUP_GEOMETRY = "ref29.0deg_src33km"

VARIANT_COLORS = {"A": "#1b9e77", "B": "#d95f02", "C": "#7570b3"}


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fail(message: str) -> None:
    print(f"CONTROL FAILURE: {message}", file=sys.stderr)
    sys.exit(1)


def check(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def verify_pins() -> dict:
    verified = {}
    for rel, pin in INPUT_PINS.items():
        path = REPO / rel
        if not path.is_file():
            fail(f"missing pinned input {rel}")
        actual = sha256_of(path)
        if actual != pin:
            fail(f"digest mismatch for {rel}: {actual} != pinned {pin}")
        verified[rel] = actual
    return verified


def windowed_argmax(field, support, time_axis, slowness_axis, t_range, s_range, min_support):
    tmask = (time_axis >= t_range[0]) & (time_axis <= t_range[1])
    smask = (slowness_axis >= s_range[0]) & (slowness_axis <= s_range[1])
    sub = field[np.ix_(smask, tmask)].copy()
    sub[support[np.ix_(smask, tmask)] < min_support] = -np.inf
    idx = np.unravel_index(np.argmax(sub), sub.shape)
    return (
        float(time_axis[tmask][idx[1]]),
        float(slowness_axis[smask][idx[0]]),
        float(sub[idx]),
    )


def load_and_control():
    sig = json.loads((REPO / "history/20260726_publication_assessment/sig_statement_reading.json").read_text())
    npz = np.load(REPO / "results/manuscript_inputs/full_set.npz", allow_pickle=True)
    field = npz["field"]
    support = npz["support_counts"]
    time_axis = npz["time_axis"]
    slowness_axis = npz["slowness_axis"]
    min_support = int(npz["minimum_support"])

    lane = json.loads(str(npz["lane_json"]))
    check(
        lane
        == {
            "input_type": "envelope",
            "mode": "paperfaith",
            "norm_variant": "A",
            "polarization_operator": "montalbetti_kanasewich_1970",
            "power_window_s": 20.0,
            "stack_method": "nth_root",
        },
        f"full-set NPZ lane is not the registered lane: {lane}",
    )

    # Positive control 1: registered-window global argmax reproduces the SIG reading.
    g_t, g_s, g_p = windowed_argmax(
        field, support, time_axis, slowness_axis, ARGMAX_WINDOW, (-10.0, 0.0), min_support
    )
    rec = sig["pkikp"]["global"]
    check(abs(g_t - rec["time_s"]) < 1e-9, f"global argmax time {g_t} != recorded {rec['time_s']}")
    check(abs(g_s - rec["slowness_sdeg"]) < 1e-9, f"global argmax slowness {g_s} != recorded")
    check(abs(g_p - rec["power"]) < 1e-9, f"global argmax power {g_p} != recorded")

    # Positive control 2: target-box maximum reproduces the SIG reading.
    b_t, b_s, b_p = windowed_argmax(
        field, support, time_axis, slowness_axis, TARGET_BOX_T, TARGET_BOX_S, min_support
    )
    rec_box = sig["pkikp"]["published_target"]
    check(abs(b_t - rec_box["time_s"]) < 1e-9, f"box max time {b_t} != recorded {rec_box['time_s']}")
    check(abs(b_s - rec_box["slowness_sdeg"]) < 1e-9, f"box max slowness {b_s} != recorded")
    check(abs(b_p - rec_box["power"]) < 1e-9, f"box max power {b_p} != recorded")

    # Adverse control: a deliberately shifted box must NOT reproduce the recorded box maximum.
    a_t, _, a_p = windowed_argmax(
        field,
        support,
        time_axis,
        slowness_axis,
        (TARGET_BOX_T[0] + 100.0, TARGET_BOX_T[1] + 100.0),
        TARGET_BOX_S,
        min_support,
    )
    check(
        abs(a_t - rec_box["time_s"]) > 1.0 or abs(a_p - rec_box["power"]) > 1e-6,
        "adverse shifted-box control unexpectedly reproduced the recorded box maximum",
    )

    return sig, npz, field, support, time_axis, slowness_axis, min_support, (g_t, g_s, g_p), (b_t, b_s, b_p)


def load_loo():
    rows = list(csv.DictReader(open(REPO / "history/20260726_publication_assessment/loo/loo_table.csv")))
    check(len(rows) == 23, f"loo_table has {len(rows)} rows, expected 23")
    flips = {r["held_out_event"] for r in rows if r["branch_flip"] == "True"}
    check(flips == RECORDED_FLIPS, f"flip set {sorted(flips)} != recorded {sorted(RECORDED_FLIPS)}")
    flip_dt = [float(r["abs_dt_vs_full_s"]) for r in rows if r["branch_flip"] == "True"]
    nonflip_dt = [float(r["abs_dt_vs_full_s"]) for r in rows if r["branch_flip"] == "False"]
    check(57.4 < min(flip_dt) and max(flip_dt) < 62.0, f"flip |dt| range {min(flip_dt)}..{max(flip_dt)} outside record")
    check(max(nonflip_dt) <= 0.95 + 1e-9, f"non-flip max |dt| {max(nonflip_dt)} exceeds recorded 0.95")
    return rows


def load_occupancy_and_t2read():
    occ = np.load(REPO / "results/bootstrap/type1_pkikp_occupancy.npz", allow_pickle=True)
    check(int(occ["n_bootstrap"]) == 200, "type1 occupancy n_bootstrap != 200")
    check(str(occ["bootstrap_fidelity_level"]) == "methods_robustness_200", "fidelity label mismatch")
    check(not bool(occ["bootstrap_published_equivalent"]), "occupancy claims published equivalence")

    t2 = json.loads((REPO / "history/20260725_scout_pass2/t2read_feature_competition.json").read_text())
    peak_times = np.asarray(occ["peak_times"], dtype=float)
    f662 = float(np.mean(peak_times >= BRANCH_BOUNDARY_S))
    rec_f662 = float(t2["designs"]["type1"]["s1_f662"])
    check(abs(f662 - rec_f662) < 1e-9, f"histogram f662 {f662} != recorded {rec_f662}")
    return occ, t2, peak_times, f662


def load_comp_assoc():
    comp = json.loads((REPO / "history/20260725_scout_pass3/comp_assoc_reading.json").read_text())
    per_design = {}
    for design in ("type1", "type2"):
        per_event = comp["designs"][design]["per_event"]
        check(len(per_event) == 23, f"comp_assoc {design} per_event has {len(per_event)} entries, expected 23")
        per_design[design] = {e["event_id"]: e for e in per_event}
    # Recorded reading (ledger COMP-ASSOC + LOO entries): Type I flags
    # S1039b/S1022a; Type II additionally flags S0474a/S1012d among the flip
    # set. "FWE-flagged" for Fig. 2 / Table 2 means flagged in either design.
    type1_flagged = {e for e, v in per_design["type1"].items() if v["fwe_flag"]}
    type2_flagged = {e for e, v in per_design["type2"].items() if v["fwe_flag"]}
    check(type1_flagged == {"S1022a", "S1039b"}, f"type1 FWE set {sorted(type1_flagged)} != recorded")
    flagged = type1_flagged | type2_flagged
    check(
        flagged & RECORDED_FLIPS == RECORDED_FWE_FLIPS,
        f"FWE-flagged flips {sorted(flagged & RECORDED_FLIPS)} != recorded {sorted(RECORDED_FWE_FLIPS)}",
    )
    return comp, per_design, flagged, type1_flagged, type2_flagged


def load_peak_table(sig):
    rows = list(csv.DictReader(open(REPO / "results/tables/peak_comparison.csv")))
    lane_rows = [
        r
        for r in rows
        if (
            r["mode"] == "paperfaith"
            and r["input_type"] == "envelope"
            and r["norm_variant"] == "A"
            and r["polarization_operator"] == "montalbetti_kanasewich_1970"
            and r["stack_method"] == "nth_root"
            and float(r["power_window_s"]) == 20.0
        )
    ]
    by_label = {(r["phase"], r["peak_label"]): r for r in lane_rows}
    g = by_label[("PKiKP", "global")]
    p = by_label[("PKiKP", "published_target")]
    check(abs(float(g["time_s"]) - sig["pkikp"]["global"]["time_s"]) < 1e-9, "peak-table global != SIG reading")
    check(int(p["target_box_rank"]) == int(sig["pkikp"]["published_target"]["S1_target_box_rank"]), "rank mismatch")
    check(
        abs(float(p["box_peak_background_quantile"]) - sig["pkikp"]["published_target"]["S2_background_quantile"])
        < 1e-9,
        "background quantile mismatch",
    )
    return by_label


def load_ablation():
    rows = list(
        csv.DictReader(
            open(REPO / "history/20260725_research_pipeline_restock/ablpolop_peak_comparison_operator_ablation.csv")
        )
    )
    sel = [
        r
        for r in rows
        if r["phase"] == "PKiKP"
        and r["peak_label"] == "global"
        and r["input_type"] == "envelope"
        and r["stack_method"] == "nth_root"
    ]
    rec = {
        (r["norm_variant"], r["polarization_operator"], float(r["power_window_s"])): (
            float(r["time_s"]),
            float(r["slowness_sdeg"]),
        )
        for r in sel
    }
    a1 = rec[("A", "principal_axis_projection", 1.0)]
    check(abs(a1[0] - 601.9) < 1e-9 and abs(a1[1] - (-3.5353535353535355)) < 1e-9, "A/PA/w1 global != recorded 601.9/-3.54")
    return rec


def load_jitter():
    t3 = json.loads((REPO / "history/20260725_research_pipeline_restock/t3power_power_comparison.json").read_text())
    vals = {
        (ph, j): (t3[ph][j]["dt_vs_j0"], t3[ph][j]["broadening_ratio"])
        for ph in ("pkikp", "pkkp")
        for j in ("type3_j10", "type3_j60")
    }
    check(abs(vals[("pkikp", "type3_j10")][0] - 5.0536) < 5e-3, "PKiKP j10 displacement != recorded 5.05")
    check(abs(vals[("pkikp", "type3_j60")][0] - 27.8829) < 5e-3, "PKiKP j60 displacement != recorded 27.88")
    check(abs(vals[("pkkp", "type3_j10")][0] - 46.7466) < 5e-3, "PKKP j10 displacement != recorded 46.75")
    return vals


def load_taup():
    rows = list(csv.DictReader(open(REPO / "history/20260725_scout_pass2/taup_phase_prediction_comparison.csv")))
    ref_models = {
        r["model_sha256"]
        for r in rows
        if r["geometry"] == TAUP_GEOMETRY and r["phase"] == "P" and abs(float(r["T_s"]) - TAUP_REFERENCE_P_T_S) < 1e-3
    }
    check(len(ref_models) == 1, f"expected exactly one reference model with P at {TAUP_REFERENCE_P_T_S}s, got {len(ref_models)}")
    model = next(iter(ref_models))
    family = [
        r
        for r in rows
        if r["model_sha256"] == model
        and r["geometry"] == TAUP_GEOMETRY
        and r["phase"] in ("PKiKP", "pPKiKP", "sPKiKP")
    ]
    check(len(family) >= 1, "no PKiKP-family TauP rows for the reference model")
    return [(r["phase"], float(r["dt_vs_P_s"]), float(r["ds_vs_P_sdeg"])) for r in family]


def load_scramble_null():
    rows = list(csv.DictReader(open(REPO / "history/20260801_mars_scramble/null_table.csv")))
    stats = json.loads((REPO / "history/20260801_mars_scramble/frozen_stats.json").read_text())
    check(len(rows) == 201, f"null_table has {len(rows)} rows, expected 201")
    check(int(rows[0]["realization"]) == 0, "null_table first row is not realization 0 identity")
    check(
        [int(r["realization"]) for r in rows[1:]] == list(range(1, 201)),
        "null_table does not contain exactly 200 ordered null realizations 1..200",
    )

    identity = rows[0]
    check(float(identity["argmax_time_s"]) == 663.8, "scramble identity time != canonical 663.8")
    check(
        float(identity["argmax_slowness_sdeg"]) == -3.6363636363636367,
        "scramble identity slowness != canonical -3.6363636363636367",
    )
    check(
        float(identity["argmax_power"]) == 0.9326603162534909,
        "scramble identity power != canonical 0.9326603162534909",
    )
    check(
        float(identity["target_box_max_power"]) == 0.7736156900239739,
        "scramble identity target-box power != canonical 0.7736156900239739",
    )

    check(int(stats["n_null"]) == 200, f"frozen scramble n_null {stats['n_null']} != 200")
    check(stats["frozen_thresholds"]["ridge"] == 0.9327, "frozen ridge threshold != 0.9327")
    check(stats["frozen_thresholds"]["target"] == 0.7736, "frozen target threshold != 0.7736")
    check(
        stats["real_values"]["ridge_argmax_power"] == 0.9326603162534909,
        "frozen real ridge value != canonical 0.9326603162534909",
    )
    check(
        stats["real_values"]["target_box_power"] == 0.7736156900239739,
        "frozen real target-box value != canonical 0.7736156900239739",
    )
    check(stats["FAR_ridge"] == 0.755, f"frozen ridge FAR {stats['FAR_ridge']} != 0.755")
    check(stats["FAR_target"] == 0.480, f"frozen target FAR {stats['FAR_target']} != 0.480")

    null_rows = rows[1:]
    ridge = np.asarray([float(r["argmax_power"]) for r in null_rows])
    target = np.asarray([float(r["target_box_max_power"]) for r in null_rows])
    ridge_count = int(np.count_nonzero(ridge >= stats["frozen_thresholds"]["ridge"]))
    target_count = int(np.count_nonzero(target >= stats["frozen_thresholds"]["target"]))
    ridge_median = float(np.median(ridge))
    target_median = float(np.median(target))
    ridge_max = float(np.max(ridge))
    target_max = float(np.max(target))

    check(ridge_count == 151, f"scramble ridge exceedance count {ridge_count} != 151")
    check(target_count == 96, f"scramble target exceedance count {target_count} != 96")
    check(
        ridge_median == stats["ridge_quantiles"]["q50"] == 0.9789989259829242,
        f"scramble ridge median {ridge_median} != frozen q50 {stats['ridge_quantiles']['q50']}",
    )
    check(
        target_median == stats["target_quantiles"]["q50"] == 0.7667363876652029,
        f"scramble target median {target_median} != frozen q50 {stats['target_quantiles']['q50']}",
    )
    check(
        ridge_max == stats["ridge_null_max"] == 1.3326855577951884,
        f"scramble ridge max {ridge_max} != frozen max {stats['ridge_null_max']}",
    )
    check(
        target_max == stats["target_null_max"] == 1.0764746107453875,
        f"scramble target max {target_max} != frozen max {stats['target_null_max']}",
    )

    return {
        "n_null": int(stats["n_null"]),
        "ridge": {
            "values": ridge,
            "real": stats["real_values"]["ridge_argmax_power"],
            "count": ridge_count,
            "far": stats["FAR_ridge"],
            "median": ridge_median,
            "max": ridge_max,
        },
        "target": {
            "values": target,
            "real": stats["real_values"]["target_box_power"],
            "count": target_count,
            "far": stats["FAR_target"],
            "median": target_median,
            "max": target_max,
        },
    }


def load_injection_ladder():
    rows = list(csv.DictReader(open(REPO / "history/20260801_inject_recov/recovery_table.csv")))
    expected_alphas = [0.0, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0]
    check(len(rows) == len(expected_alphas), f"injection ladder has {len(rows)} rows, expected 7")
    check(
        [float(r["alpha"]) for r in rows] == expected_alphas,
        f"injection ladder alphas {[float(r['alpha']) for r in rows]} != {expected_alphas}",
    )
    check(
        all(r["argmax_in_target_box"] in ("True", "False") for r in rows),
        "injection ladder has a non-boolean argmax_in_target_box value",
    )

    parsed = [
        {
            "alpha": float(r["alpha"]),
            "time": float(r["argmax_time_s"]),
            "slowness": float(r["argmax_slowness_sdeg"]),
            "power": float(r["argmax_power"]),
            "support": int(r["argmax_support"]),
            "in_box": r["argmax_in_target_box"] == "True",
            "target_power": float(r["targetbox_max_power"]),
            "target_time": float(r["targetbox_time_s"]),
        }
        for r in rows
    ]

    canonical = parsed[0]
    check(canonical["time"] == 663.8, "injection alpha=0 time != canonical 663.8")
    check(
        canonical["slowness"] == -3.6363636363636367,
        "injection alpha=0 slowness != canonical -3.6363636363636367",
    )
    check(canonical["power"] == 0.9326603162534909, "injection alpha=0 power != canonical 0.9326603162534909")
    check(canonical["support"] == 23, f"injection alpha=0 support {canonical['support']} != canonical 23")
    check(
        canonical["target_power"] == 0.7736156900239739,
        "injection alpha=0 target-box power != canonical 0.7736156900239739",
    )
    check(not canonical["in_box"], "injection alpha=0 argmax_in_target_box is not false")

    alpha_star = parsed[1]
    check(alpha_star["time"] == 602.95, "injection alpha=0.25 time != 602.95")
    check(
        alpha_star["slowness"] == -6.4646464646464645,
        "injection alpha=0.25 slowness != -6.4646464646464645",
    )
    check(alpha_star["power"] == 1.2483490424619448, "injection alpha=0.25 power != 1.2483490424619448")
    check(alpha_star["support"] == 23, f"injection alpha=0.25 support {alpha_star['support']} != 23")
    check(alpha_star["in_box"], "injection alpha=0.25 argmax_in_target_box is not true")
    check(all(r["in_box"] for r in parsed[1:]), "an injection rung >= 0.25 is not in the target box")

    injected_times = [r["time"] for r in parsed[1:]]
    expected_times = [602.95, 603.3, 603.5, 603.65, 603.8, 603.9]
    check(injected_times == expected_times, f"injection argmax times {injected_times} != {expected_times}")
    check(
        all(left <= right for left, right in zip(injected_times, injected_times[1:])),
        f"injection argmax times are not monotone nondecreasing: {injected_times}",
    )
    check(parsed[-1]["time"] == 603.9, f"injection alpha=8 time {parsed[-1]['time']} != 603.9")
    return parsed


def fig1(field, support, time_axis, slowness_axis, min_support, global_peak, box_peak, taup_family):
    tmask = (time_axis >= 520.0) & (time_axis <= 720.0)
    view = np.ma.masked_where(support[:, tmask] < min_support, field[:, tmask])

    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    mesh = ax.pcolormesh(
        time_axis[tmask],
        slowness_axis,
        view,
        cmap="viridis",
        vmin=0.0,
        vmax=float(view.max()),
        shading="nearest",
        rasterized=True,
    )
    fig.colorbar(mesh, ax=ax, label="4th-root stack power (20 s window)")

    ax.add_patch(
        Rectangle(
            (TARGET_BOX_T[0], TARGET_BOX_S[0]),
            TARGET_BOX_T[1] - TARGET_BOX_T[0],
            TARGET_BOX_S[1] - TARGET_BOX_S[0],
            fill=False,
            edgecolor="white",
            linestyle="--",
            linewidth=1.2,
        )
    )
    ax.errorbar(
        PUBLISHED_PAIR[0],
        PUBLISHED_PAIR[1],
        xerr=PUBLISHED_ERR[0],
        yerr=PUBLISHED_ERR[1],
        fmt="o",
        color="#ff7f0e",
        markersize=5,
        capsize=3,
        label="published PKiKP pair (604 s, −6.5 s/deg)",
    )
    ax.plot(
        global_peak[0],
        global_peak[1],
        marker="*",
        color="#e41a1c",
        markersize=14,
        linestyle="none",
        markeredgecolor="black",
        markeredgewidth=0.5,
        label=f"PKiKP-window argmax ({global_peak[0]:.1f} s, {global_peak[1]:.2f} s/deg)",
    )
    ax.plot(
        box_peak[0],
        box_peak[1],
        marker="o",
        color="#00d5ff",
        markersize=10,
        linestyle="none",
        markerfacecolor="none",
        markeredgewidth=1.8,
        zorder=5,
        label=f"target-box maximum ({box_peak[0]:.2f} s, {box_peak[1]:.2f} s/deg)",
    )
    label_offsets = {"PKiKP": (-16, -13), "pPKiKP": (0, 9), "sPKiKP": (18, -13)}
    for phase, dt, ds in taup_family:
        ax.plot(dt, ds, marker="^", color="white", markersize=6, linestyle="none", zorder=4)
        ax.annotate(
            phase,
            (dt, ds),
            textcoords="offset points",
            xytext=label_offsets.get(phase, (0, -11)),
            color="white",
            fontsize="x-small",
            ha="center",
        )
    for t_edge in ARGMAX_WINDOW:
        ax.axvline(t_edge, color="white", linestyle=":", linewidth=0.8, alpha=0.7)
    ax.text(
        ARGMAX_WINDOW[0] + 2,
        -9.7,
        "registered argmax window",
        color="white",
        fontsize="x-small",
        va="bottom",
    )

    ax.set_xlim(520.0, 720.0)
    ax.set_ylim(-10.0, 0.0)
    ax.set_xlabel("time after P (s)")
    ax.set_ylabel("relative slowness (s/deg)")
    ax.set_title("Registered-lane vespagram, full 23-event stack (PKiKP window)")
    ax.legend(loc="upper left", fontsize="x-small", framealpha=0.35, labelcolor="white")
    fig.tight_layout()
    return fig


def fig2(loo_rows, fwe_flagged):
    rows = sorted(loo_rows, key=lambda r: float(r["abs_dt_vs_full_s"]))
    events = [r["held_out_event"] for r in rows]
    dts = np.array([float(r["abs_dt_vs_full_s"]) for r in rows])
    flips = np.array([r["branch_flip"] == "True" for r in rows])
    floor = 0.03
    plotted = np.maximum(dts, floor)

    fig, ax = plt.subplots(figsize=(6.8, 5.4))
    colors = ["#e41a1c" if f else "#377eb8" for f in flips]
    bars = ax.barh(np.arange(len(rows)), plotted, color=colors, edgecolor="black", linewidth=0.4)
    for i, (event, bar) in enumerate(zip(events, bars)):
        if event in fwe_flagged and flips[i]:
            bar.set_hatch("///")
        if dts[i] < floor:
            ax.annotate(
                f"{dts[i]:g} s",
                (floor, i),
                textcoords="offset points",
                xytext=(4, -3),
                fontsize="x-small",
                color="dimgray",
            )
    labels = [f"{e}†" if (e in fwe_flagged and e in RECORDED_FLIPS) else e for e in events]
    ax.set_yticks(np.arange(len(rows)), labels=labels, fontsize="x-small")
    ax.set_xscale("log")
    ax.set_xlim(0.02, 100.0)
    ax.set_xlabel("|Δt| of PKiKP-window argmax when event is held out (s)")
    ax.set_title("Leave-one-out influence, registered lane (23 events)")
    ax.axvline(0.95, color="gray", linestyle=":", linewidth=0.8)
    ax.text(0.95, len(rows) - 0.2, " 0.95 s (non-flip max)", fontsize="x-small", color="gray", va="top")
    handles = [
        plt.Rectangle((0, 0), 1, 1, color="#377eb8"),
        plt.Rectangle((0, 0), 1, 1, color="#e41a1c"),
        plt.Rectangle((0, 0), 1, 1, facecolor="#e41a1c", hatch="///", edgecolor="black"),
    ]
    ax.legend(
        handles,
        ["no branch flip (17)", "branch flip (6)", "flip, FWE-flagged in either design (4)"],
        loc="lower right",
        fontsize="x-small",
    )
    fig.tight_layout()
    return fig


def fig3(peak_times, f662, t2):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.2, 3.8), width_ratios=[2.1, 1.0])

    bins = np.arange(548.0, 680.0, 2.0)
    early = peak_times[peak_times < BRANCH_BOUNDARY_S]
    late = peak_times[peak_times >= BRANCH_BOUNDARY_S]
    ax1.hist(early, bins=bins, color="#d95f02", label=f"early branch ({early.size}/200)")
    ax1.hist(late, bins=bins, color="#7570b3", label=f"662 branch ({late.size}/200)")
    ax1.axvline(BRANCH_BOUNDARY_S, color="black", linestyle="--", linewidth=1.0)
    ax1.text(BRANCH_BOUNDARY_S + 1.5, ax1.get_ylim()[1] * 0.93, "registered boundary 632 s", fontsize="x-small")
    ax1.set_xlabel("per-realization PKiKP-window argmax time (s)")
    ax1.set_ylabel("bootstrap realizations")
    ax1.set_title("Type I bootstrap argmax times (methods_robustness_200)")
    ax1.legend(fontsize="x-small")

    designs = [
        ("Type I\n(event resampling)", t2["designs"]["type1"]),
        ("Type II\n(distance-stratified)", t2["designs"]["type2"]),
    ]
    for i, (label, d) in enumerate(designs):
        f = float(d["s1_f662"])
        lo, hi = (float(x) for x in d["s1_wilson95"])
        ax2.errorbar(i, f, yerr=[[f - lo], [hi - f]], fmt="o", color="#7570b3", capsize=4)
        ax2.annotate(f"{f:.3f}", (i, f), textcoords="offset points", xytext=(8, 0), fontsize="x-small")
    ax2.axhline(0.5, color="gray", linestyle=":", linewidth=0.8)
    ax2.set_xticks([0, 1], labels=[d[0] for d in designs], fontsize="x-small")
    ax2.set_xlim(-0.5, 1.5)
    ax2.set_ylim(0.4, 0.8)
    ax2.set_ylabel("fraction on 662 branch (Wilson 95% CI)")
    ax2.set_title("Branch fraction by design")
    fig.tight_layout()
    return fig


def fig4(ablation, peak_by_label, jitter):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.6, 3.9))

    windows = [1.0, 5.0, 10.0, 20.0]
    x = np.arange(len(windows))
    production = {
        ("A", 20.0): float(peak_by_label[("PKiKP", "global")]["time_s"]),
    }
    prod_rows = list(csv.DictReader(open(REPO / "results/tables/peak_comparison.csv")))
    for r in prod_rows:
        if (
            r["mode"] == "paperfaith"
            and r["input_type"] == "envelope"
            and r["polarization_operator"] == "montalbetti_kanasewich_1970"
            and r["stack_method"] == "nth_root"
            and r["phase"] == "PKiKP"
            and r["peak_label"] == "global"
        ):
            production[(r["norm_variant"], float(r["power_window_s"]))] = float(r["time_s"])

    for variant in ("A", "B", "C"):
        color = VARIANT_COLORS[variant]
        ax1.plot(
            x,
            [production[(variant, w)] for w in windows],
            marker="o",
            color=color,
            linewidth=1.4,
            label=f"{variant}, M–K operator",
        )
        key_pa = [(variant, "principal_axis_projection", w) for w in windows]
        if all(k in ablation for k in key_pa):
            ax1.plot(
                x,
                [ablation[k][0] for k in key_pa],
                marker="s",
                markerfacecolor="none",
                color=color,
                linewidth=1.2,
                linestyle="--",
                label=f"{variant}, principal-axis",
            )
        key_none = [(variant, "not_applicable", w) for w in windows]
        if all(k in ablation for k in key_none):
            ax1.plot(
                x,
                [ablation[k][0] for k in key_none],
                marker="^",
                markerfacecolor="none",
                color=color,
                linewidth=1.2,
                linestyle=":",
                label=f"{variant}, operator removed",
            )

    ax1.axhspan(602.0, 606.0, color="gray", alpha=0.25)
    ax1.text(0.05, 606.5, "published 604 ± 2 s", fontsize="x-small", color="dimgray")
    ax1.axhline(BRANCH_BOUNDARY_S, color="black", linestyle=":", linewidth=0.8)
    ax1.set_xticks(x, labels=[f"{w:g}" for w in windows])
    ax1.set_xlabel("power window (s)")
    ax1.set_ylabel("PKiKP-window argmax time (s)")
    ax1.set_title("PKiKP-window argmax vs polarization operator")
    ax1.legend(fontsize=5.5, ncols=2, loc="center right")

    labels = ["PKiKP\n±10 s", "PKiKP\n±60 s", "PKKP\n±10 s", "PKKP\n±60 s"]
    keys = [("pkikp", "type3_j10"), ("pkikp", "type3_j60"), ("pkkp", "type3_j10"), ("pkkp", "type3_j60")]
    dts = [jitter[k][0] for k in keys]
    broad = [jitter[k][1] for k in keys]
    colors = ["#1b9e77", "#1b9e77", "#a6761d", "#a6761d"]
    bars = ax2.bar(np.arange(4), dts, color=colors, edgecolor="black", linewidth=0.4)
    for bar, b in zip(bars, broad):
        ax2.annotate(
            f"{b:.0f}×",
            (bar.get_x() + bar.get_width() / 2, bar.get_height()),
            textcoords="offset points",
            xytext=(0, 3),
            ha="center",
            fontsize="x-small",
        )
    ax2.axhline(59.8, color="#e41a1c", linestyle="--", linewidth=1.0)
    ax2.text(1.32, 60.8, "observed displacement 663.8 − 604 s", fontsize="x-small", color="#e41a1c")
    ax2.set_xticks(np.arange(4), labels=labels, fontsize="x-small")
    ax2.set_ylabel("occupancy-centroid displacement (s)")
    ax2.set_title("P-pick jitter: displacement and broadening")
    fig.tight_layout()
    return fig


def fig5(scramble):
    fig, axes = plt.subplots(1, 2, figsize=(8.2, 3.8))
    panels = (
        (axes[0], "A", "Supported PKiKP-window argmax power", scramble["ridge"]),
        (axes[1], "B", "Target-box maximum power", scramble["target"]),
    )
    for ax, panel, title, values in panels:
        ax.hist(values["values"], bins=16, color="0.72", edgecolor="black", linewidth=0.6)
        ax.axvline(values["real"], color="black", linestyle="--", linewidth=1.4)
        annotation = (
            f"real value: {values['real']:.4f}\n"
            f"exceedances: {values['count']}/{scramble['n_null']} = {values['far']:.3f}\n"
            f"null median: {values['median']:.4f}"
        )
        ax.text(
            0.97,
            0.95,
            annotation,
            transform=ax.transAxes,
            ha="right",
            va="top",
            fontsize="x-small",
            bbox={"facecolor": "white", "edgecolor": "0.4", "alpha": 0.9, "boxstyle": "round,pad=0.25"},
        )
        ax.text(0.02, 0.96, panel, transform=ax.transAxes, ha="left", va="top", fontweight="bold")
        ax.set_xlabel(title)
        ax.set_ylabel("null realizations")
        ax.set_title("Scramble-null distribution")
    fig.tight_layout()
    return fig


def write_table1(peak_by_label, sig):
    rows = [
        ("PKiKP", "global"),
        ("PKiKP", "published_target"),
        ("PKKP", "peak_1"),
        ("PKKP", "peak_2"),
        ("PKKP", "paper_target"),
    ]
    lines = [
        "# Table 1 — registered-lane peak-table extract",
        "",
        "Lane: paperfaith / envelope / A / montalbetti_kanasewich_1970 / nth_root / 20.0 s.",
        f"Source: `results/tables/peak_comparison.csv` (SHA-256 `{INPUT_PINS['results/tables/peak_comparison.csv'][:12]}…`).",
        "",
        "| Phase | Feature | t (s) | s (s/deg) | Power | Δt vs published (s) | Exact tol. | Folded tol. | Box rank | Bg. quantile |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for phase, label in rows:
        r = peak_by_label[(phase, label)]
        rank = r["target_box_rank"] or "—"
        quant = r["box_peak_background_quantile"]
        quant = f"{float(quant):.4f}" if quant not in ("", None) else "—"
        lines.append(
            "| {phase} | {label} | {t:.2f} | {s:.2f} | {p:.4f} | {dt:+.2f} | {tol} | {ftol} | {rank} | {quant} |".format(
                phase=phase,
                label=label.replace("_", " "),
                t=float(r["time_s"]),
                s=float(r["slowness_sdeg"]),
                p=float(r["power"]),
                dt=float(r["dt_vs_paper_s"]),
                tol=r["within_published_tolerance"],
                ftol=r["within_uncertainty_folded_tolerance"],
                rank=rank,
                quant=quant,
            )
        )
    ratio = sig["pkikp"]["S3_power_ratio_global_over_published_target"]
    lines += [
        "",
        f"Global-to-target-box power ratio: {ratio:.4f} (recorded S3 statistic).",
        "PKKP mirror: rank {rank}, background quantile {q:.4f}, within folded tolerance.".format(
            rank=sig["pkkp_mirror"]["paper_target"]["target_box_rank"],
            q=sig["pkkp_mirror"]["paper_target"]["background_quantile_NEW"],
        ),
        "",
    ]
    (TABLE_DIR / "table1_peak_extract.md").write_text("\n".join(lines))


def write_table2(loo_rows, per_design, type1_flagged, type2_flagged):
    flips = sorted(
        (r for r in loo_rows if r["branch_flip"] == "True"), key=lambda r: r["held_out_event"]
    )
    lines = [
        "# Table 2 — the six flipping events",
        "",
        "Sources: `loo_table.csv` (LOO sweep) and `comp_assoc_reading.json`",
        "(max-T FWE composition test; Δ incl. = P(incl | 662-branch) − P(incl | early-branch),",
        "same-data calibration). FWE column lists the design(s) flagging the event:",
        "I = event resampling, II = distance-stratified, — = neither.",
        "",
        "| Event | Distance (deg) | Held-out argmax t (s) | s (s/deg) | \\|Δt\\| (s) | FWE | Δ incl. (I) | Δ incl. (II) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in flips:
        event = r["held_out_event"]
        designs = "+".join(
            d for d, flagged in (("I", type1_flagged), ("II", type2_flagged)) if event in flagged
        ) or "—"
        lines.append(
            "| {e} | {d:.1f} | {t:.2f} | {s:.2f} | {dt:.1f} | {f} | {d1:+.3f} | {d2:+.3f} |".format(
                e=event,
                d=float(per_design["type1"][event]["distance_deg"]),
                t=float(r["time_s"]),
                s=float(r["slowness_sdeg"]),
                dt=float(r["abs_dt_vs_full_s"]),
                f=designs,
                d1=float(per_design["type1"][event]["delta_incl"]),
                d2=float(per_design["type2"][event]["delta_incl"]),
            )
        )
    lines.append("")
    (TABLE_DIR / "table2_flip_events.md").write_text("\n".join(lines))


def write_table3(rows):
    lines = [
        "# Table 3 — injection-recovery ladder",
        "",
        f"Source: `history/20260801_inject_recov/recovery_table.csv` (SHA-256 `{INPUT_PINS['history/20260801_inject_recov/recovery_table.csv'][:12]}…`).",
        "",
        "| alpha | Global argmax (time s, slowness s/deg, power, support) | Argmax in target box | Target-box max power | Target-box max time (s) |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {alpha:g} | ({time:.2f}, {slowness:.2f}, {power:.4f}, {support:d}) | {in_box} | {target_power:.4f} | {target_time:.2f} |".format(
                alpha=row["alpha"],
                time=row["time"],
                slowness=row["slowness"],
                power=row["power"],
                support=row["support"],
                in_box="yes" if row["in_box"] else "no",
                target_power=row["target_power"],
                target_time=row["target_time"],
            )
        )
    lines += [
        "",
        "a) alpha = 0 is the canonical enforced lane; injected lanes (alpha > 0) are exploratory by necessity (injection invalidates the alignment-stage provenance hash by construction).",
        "",
        "b) the alpha = 8 literal positive control FAILED on the time axis (603.90 s, two 0.05-s cells from 604.0) and is adjudicated a control-tolerance design flaw; it is not quotable as a passed literal control (draft section 5.4; Table S1e).",
        "",
    ]
    (TABLE_DIR / "table3_injection_ladder.md").write_text("\n".join(lines))


def main() -> None:
    verified = verify_pins()
    FIG_DIR.mkdir(exist_ok=True)
    TABLE_DIR.mkdir(exist_ok=True)

    sig, npz, field, support, time_axis, slowness_axis, min_support, global_peak, box_peak = load_and_control()
    loo_rows = load_loo()
    occ, t2, peak_times, f662 = load_occupancy_and_t2read()
    comp, per_design, fwe_flagged, type1_flagged, type2_flagged = load_comp_assoc()
    peak_by_label = load_peak_table(sig)
    ablation = load_ablation()
    jitter = load_jitter()
    taup_family = load_taup()
    scramble = load_scramble_null()
    injection_rows = load_injection_ladder()

    outputs = {}
    for name, fig in (
        ("fig1_vespagram", fig1(field, support, time_axis, slowness_axis, min_support, global_peak, box_peak, taup_family)),
        ("fig2_loo", fig2(loo_rows, fwe_flagged)),
        ("fig3_occupancy", fig3(peak_times, f662, t2)),
        ("fig4_ablation_jitter", fig4(ablation, peak_by_label, jitter)),
        ("fig5_scramble_null", fig5(scramble)),
    ):
        for ext in ("png", "pdf"):
            path = FIG_DIR / f"{name}.{ext}"
            fig.savefig(path, dpi=200)
            outputs[str(path.relative_to(REPO))] = sha256_of(path)
        plt.close(fig)

    write_table1(peak_by_label, sig)
    write_table2(loo_rows, per_design, type1_flagged, type2_flagged)
    write_table3(injection_rows)
    for table in ("table1_peak_extract.md", "table2_flip_events.md", "table3_injection_ladder.md"):
        path = TABLE_DIR / table
        outputs[str(path.relative_to(REPO))] = sha256_of(path)

    provenance = {
        "generator": "papers/Paper0/manuscript/make_figures.py",
        "inputs_sha256": verified,
        "controls": {
            "global_argmax_reproduced": list(global_peak),
            "target_box_max_reproduced": list(box_peak),
            "adverse_shifted_box_differs": True,
            "loo_flip_set_reproduced": sorted(RECORDED_FLIPS),
            "histogram_f662_matches_t2read": f662,
            "fwe_flip_overlap_reproduced": sorted(RECORDED_FWE_FLIPS),
            "scramble_null_recount_reproduced": [scramble["ridge"]["count"], scramble["target"]["count"]],
            "scramble_identity_row_reproduced": True,
            "injection_ladder_reproduced": True,
            "injection_alpha_star": injection_rows[1]["alpha"],
        },
        "matplotlib": matplotlib.__version__,
        "numpy": np.__version__,
        "outputs_sha256": outputs,
    }
    (FIG_DIR / "figure_provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n")
    print("ALL CONTROLS PASSED; figures and tables written")
    for rel in outputs:
        print(" ", rel)


if __name__ == "__main__":
    main()
