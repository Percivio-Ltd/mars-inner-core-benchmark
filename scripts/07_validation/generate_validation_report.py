from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from obspy import UTCDateTime, read
from obspy.taup import TauPyModel

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.shared import (
    find_best_event_match,
    import_local_module,
    load_event_table,
    read_catalog,
    repo_path,
    sha256_file,
)
from scripts.paper0_bootstrap_fidelity import BOOTSTRAP_FIDELITY_LEVELS

align_mod = import_local_module("marsquake_validation_align", "scripts/02_preprocess/align_and_cut.py")
paper0_provenance = import_local_module("marsquake_validation_paper0_provenance", "scripts/paper0_provenance.py")
detect_mod = import_local_module("marsquake_validation_detect", "scripts/03_vespagram/detect_peaks.py")
model_mod = import_local_module("marsquake_validation_model", "scripts/05_model_gen/generate_nd_model.py")
branch_registry = import_local_module("marsquake_validation_branch_registry", "scripts/branch_registry.py")

BENCHMARK_COMBO = {
    "mode": "paperfaith",
    "input_type": "envelope",
    "variant": "A",
    "stack_method": "nth_root",
    "power_window_s": 20,
}
REGISTERED_PRIMARY_LANE_BY_PHASE = {"PKiKP": "A", "PKKP": "A"}
REGISTERED_NAMED_ENDPOINTS = {
    ("PKiKP", "global"): {
        "registered_key": "pkikp_global",
        "endpoint_label": "displaced_ridge",
        "display_label": "displaced_ridge",
        "window": "550-700s",
        "role": "current broad-window PKiKP maximum",
    },
    ("PKiKP", "published_target"): {
        "registered_key": "pkikp_published_target",
        "endpoint_label": "published_PKIKP_box",
        "display_label": "published_PKIKP_box",
        "window": "584-624s",
        "role": "published PKiKP target-box maximum",
    },
    ("PKKP", "paper_target"): {
        "registered_key": "pkkp_paper_target",
        "endpoint_label": "PKKP_target",
        "display_label": "PKKP_target",
        "window": "1320-1360s",
        "role": "published PKKP target-box maximum",
    },
}
VERIFIED_DEGLITCH_STATUS = "mps_ucla_verified"
HISTORICAL_PRE_CURRENT_BASELINE = {
    "pkikp_global": {"time_s": 666.15, "slowness_sdeg": -4.04},
    "pkkp_paper_target": {"time_s": 1341.05, "slowness_sdeg": -6.97},
}
REPRESENTATIVE_EVENTS = ("S0235b", "S0173a", "S1222a")
INCREMENTAL_VALIDATION_DIR = "incremental_validation"
REGISTERED_MODEL_QUERY_SOURCE_DEPTH_KM = 33.0
REGISTERED_MODEL_QUERY_DISTANCE_DEG = 29.0
REGISTERED_MODEL_EXPECTED_ARRIVAL_TIMES_S = {
    "P": 224.13,
    "PKiKP": 808.14,
}
REGISTERED_MODEL_ARRIVAL_TOLERANCE_S = 0.01
VALIDATION_CHECKS = (
    "inventory",
    "preprocessing",
    "alignment",
    "benchmark",
    "bootstrap",
    "type2_distance_stratified",
    "type3_alignment_jitter",
    "deglitch",
    "model",
)


def check_status(ok: bool, fail_text: str, pass_text: str = "ok") -> dict:
    return {"status": "pass" if ok else "fail", "detail": pass_text if ok else fail_text}


def warn_status(detail: str) -> dict:
    return {"status": "warn", "detail": detail}


def benchmark_lane_label() -> str:
    return (
        f"{BENCHMARK_COMBO['mode']}/{BENCHMARK_COMBO['input_type']}/{BENCHMARK_COMBO['variant']}/"
        f"{BENCHMARK_COMBO['stack_method']}/win{BENCHMARK_COMBO['power_window_s']}"
    )


def _row_bool(row: dict, key: str) -> bool:
    return str(row.get(key, "")).strip().lower() in {"1", "true", "yes"}


def _format_delta(name: str, value: float, unit: str) -> str:
    return f"Δ{name}={value:.2f}{unit}"


def _bootstrap_check_detail(phase: str, row: dict, paper_target: tuple[float, float]) -> dict:
    degenerate = _row_bool(row, "degenerate_fit")
    if degenerate:
        argmax_dt = float(row["occupancy_argmax_time_s"]) - paper_target[0]
        argmax_ds = float(row["occupancy_argmax_slowness_sdeg"]) - paper_target[1]
        median_dt = float(row["weighted_median_time_s"]) - paper_target[0]
        median_ds = float(row["weighted_median_slowness_sdeg"]) - paper_target[1]
        status = "warn" if max(abs(argmax_dt), abs(median_dt)) > 20 or max(abs(argmax_ds), abs(median_ds)) > 1.5 else "pass"
        reasons = str(row.get("fit_quality_reasons", "")).strip() or "registered fit-quality criteria"
        return {
            "status": status,
            "detail": (
                "85% bootstrap robust estimators vs paper target: "
                f"occupancy argmax {_format_delta('t', argmax_dt, 's')} "
                f"{_format_delta('s', argmax_ds, 's/deg')}; "
                f"weighted median {_format_delta('t', median_dt, 's')} "
                f"{_format_delta('s', median_ds, 's/deg')}; "
                f"gaussian fit degenerate_fit=True ({reasons})"
            ),
        }

    dt = float(row["mean_time_s"]) - paper_target[0]
    ds = float(row["mean_slowness_sdeg"]) - paper_target[1]
    return {
        "status": "warn" if abs(dt) > 20 or abs(ds) > 1.5 else "pass",
        "detail": (
            "85% bootstrap Gaussian fit vs paper target: "
            f"{_format_delta('t', dt, 's')} {_format_delta('s', ds, 's/deg')}"
        ),
    }


def _benchmark_check_detail(check: dict) -> str:
    detail = str(check.get("detail", ""))
    if "stale coordinates" in detail or "historical" in detail:
        return (
            "current-run audit does not gate on the historical pre-current-run baseline; "
            "published-target replication gates remain separate"
        )
    return detail


def _deglitch_label(deglitch: dict) -> str:
    level = str(deglitch.get("attestation_level") or deglitch.get("verified_only_gate") or "unknown").strip()
    if deglitch.get("accepted_partial_lane_by_design"):
        level = f"{level}-by-design"
    strict_gate = str(deglitch.get("verified_only_gate") or VERIFIED_DEGLITCH_STATUS).strip()
    return f"attestation={level}; strict_gate={strict_gate}"


def _pick_time_value(p_pick) -> UTCDateTime:
    if isinstance(p_pick, dict):
        return UTCDateTime(p_pick["time"])
    return UTCDateTime(p_pick.time)


def _read_single_trace(path: Path):
    st = read(str(path))
    if not st:
        raise ValueError(f"Empty stream: {path}")
    return st[0]


def _save_figure(fig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _relative_l2(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a)
    if denom == 0:
        return float(np.linalg.norm(b))
    return float(np.linalg.norm(a - b) / denom)


def _load_peak_rows(path: Path):
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _read_bootstrap_rows(path: Path):
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _payload_scalar(payload, key: str, default=None):
    if key not in payload.files:
        return default
    value = np.asarray(payload[key]).item()
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value


def _bool_scalar(value) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes"}
    return bool(value)


def _read_bootstrap_fidelity(payload, artifact_name: str) -> dict:
    missing = [
        key
        for key in (
            "n_bootstrap",
            "bootstrap_fidelity_level",
            "bootstrap_published_equivalent",
            "declared_published_n_bootstrap",
        )
        if key not in payload.files
    ]
    if missing:
        raise ValueError(f"{artifact_name}: missing bootstrap fidelity keys: {', '.join(missing)}")
    level = str(_payload_scalar(payload, "bootstrap_fidelity_level", ""))
    n_bootstrap = int(_payload_scalar(payload, "n_bootstrap", -1))
    published_equivalent = _bool_scalar(_payload_scalar(payload, "bootstrap_published_equivalent", False))
    published_n = int(_payload_scalar(payload, "declared_published_n_bootstrap", 10000))
    expected = BOOTSTRAP_FIDELITY_LEVELS.get(level)
    if expected is None:
        raise ValueError(f"{artifact_name}: unregistered bootstrap fidelity level {level}")
    if n_bootstrap != int(expected["n_bootstrap"]):
        raise ValueError(
            f"{artifact_name}: fidelity {level} requires N={expected['n_bootstrap']}; got N={n_bootstrap}"
        )
    if published_equivalent != bool(expected["published_equivalent"]):
        raise ValueError(f"{artifact_name}: published-equivalent flag does not match fidelity {level}")
    if published_n != int(expected["published_n_bootstrap"]):
        raise ValueError(f"{artifact_name}: published N does not match fidelity {level}")
    return {
        "level": level,
        "n_bootstrap": n_bootstrap,
        "published_equivalent": published_equivalent,
        "published_n_bootstrap": published_n,
    }


def build_event_inventory(event_table: Path, catalog_path: Path, raw_dir: Path, processed_dir: Path, out_dir: Path):
    rows = load_event_table(event_table)
    catalog = read_catalog(catalog_path)
    inventory = []
    complete_count = 0
    large_time_delta = 0

    for row in rows:
        event_id = row["event_id"]
        origin = row["origin_time"]
        try:
            event, time_delta = find_best_event_match(catalog, event_id, origin)
            matched_by_id = align_mod._event_matches_id(event, event_id)
            p_pick = align_mod.get_matching_pick(event, event_id)
            pick_time = _pick_time_value(p_pick).isoformat()
        except ValueError:
            event = None
            time_delta = float("inf")
            matched_by_id = False
            pick_time = ""

        raw_path = raw_dir / f"{event_id}.mseed"
        zne_path = processed_dir / f"{event_id}_ZNE.mseed"
        z_filt_path = processed_dir / f"{event_id}_Z_filt.mseed"
        z_polfilt_path = processed_dir / f"{event_id}_Z_polfilt.mseed"
        aligned_ablation = processed_dir / f"{event_id}_aligned_ablation.mseed"
        aligned_paperfaith = processed_dir / f"{event_id}_aligned_paperfaith.mseed"
        waveform_c = processed_dir / f"{event_id}_paperfaith_C_waveform.npy"
        envelope_c = processed_dir / f"{event_id}_paperfaith_C_envelope.npy"
        times_c = processed_dir / f"{event_id}_paperfaith_C_times.npy"
        benchmark_normalized_paths = [
            processed_dir / f"{event_id}_ablation_A_waveform.npy",
            processed_dir / f"{event_id}_ablation_A_envelope.npy",
            processed_dir / f"{event_id}_ablation_A_times.npy",
            processed_dir / f"{event_id}_ablation_B_waveform.npy",
            processed_dir / f"{event_id}_ablation_B_envelope.npy",
            processed_dir / f"{event_id}_ablation_B_times.npy",
            processed_dir / f"{event_id}_ablation_C_waveform.npy",
            processed_dir / f"{event_id}_ablation_C_envelope.npy",
            processed_dir / f"{event_id}_ablation_C_times.npy",
            processed_dir / f"{event_id}_paperfaith_A_waveform.npy",
            processed_dir / f"{event_id}_paperfaith_A_envelope.npy",
            processed_dir / f"{event_id}_paperfaith_A_times.npy",
            processed_dir / f"{event_id}_paperfaith_B_waveform.npy",
            processed_dir / f"{event_id}_paperfaith_B_envelope.npy",
            processed_dir / f"{event_id}_paperfaith_B_times.npy",
            waveform_c,
            envelope_c,
            times_c,
        ]
        try:
            align_mod.validate_paperstyle_polarization_products(event_id, processed_dir)
            paperstyle_polarization_current = True
            paperstyle_polarization_status = "current"
        except RuntimeError as exc:
            paperstyle_polarization_current = False
            paperstyle_polarization_status = str(exc)
        normalization_errors = []
        for variant in ("C", "A", "B"):
            for input_type in ("waveform", "envelope"):
                try:
                    paper0_provenance.validate_normalized_products(event_id, processed_dir, "paperfaith", variant, input_type)
                except RuntimeError as exc:
                    normalization_errors.append(f"{variant}/{input_type}: {exc}")
        paperstyle_normalization_current = not normalization_errors
        paperstyle_normalization_status = "current" if paperstyle_normalization_current else "; ".join(normalization_errors[:3])
        ablation_errors = []
        for variant in ("C", "A", "B"):
            for input_type in ("waveform", "envelope"):
                try:
                    paper0_provenance.validate_normalized_products(event_id, processed_dir, "ablation", variant, input_type)
                except RuntimeError as exc:
                    ablation_errors.append(f"{variant}/{input_type}: {exc}")
        ablation_normalization_current = not ablation_errors
        ablation_normalization_status = "current" if ablation_normalization_current else "; ".join(ablation_errors[:2])

        raw_exists = raw_path.exists()
        file_set = [
            raw_exists,
            zne_path.exists(),
            z_filt_path.exists(),
            z_polfilt_path.exists(),
            paperstyle_polarization_current,
            paperstyle_normalization_current,
            ablation_normalization_current,
            aligned_ablation.exists(),
            aligned_paperfaith.exists(),
            all(path.exists() for path in benchmark_normalized_paths),
        ]
        complete = all(file_set)
        if complete:
            complete_count += 1

        if abs(float(time_delta)) > 30:
            large_time_delta += 1

        raw_sha = sha256_file(raw_path) if raw_exists else ""
        if complete:
            tr = _read_single_trace(aligned_paperfaith)
            sampling_rate = float(tr.stats.sampling_rate)
            npts = int(tr.stats.npts)
            duration_s = float(npts / sampling_rate)
        else:
            sampling_rate = float("nan")
            npts = 0
            duration_s = float("nan")

        inventory.append(
            {
                "event_id": event_id,
                "set": row["set"],
                "distance_deg": row["distance_deg"],
                "origin_time": origin,
                "catalog_time_delta_s": float(time_delta),
                "matched_by_id": bool(matched_by_id),
                "p_pick_utc": pick_time,
                "raw_sha256": raw_sha,
                "sampling_rate_hz": sampling_rate,
                "aligned_npts": npts,
                "aligned_duration_s": duration_s,
                "complete_processing": complete,
                "paperstyle_polarization_current": paperstyle_polarization_current,
                "paperstyle_polarization_status": paperstyle_polarization_status,
                "paperstyle_normalization_current": paperstyle_normalization_current,
                "paperstyle_normalization_status": paperstyle_normalization_status,
                "ablation_normalization_current": ablation_normalization_current,
                "ablation_normalization_status": ablation_normalization_status,
            }
        )

    out_path = out_dir / "tables" / "event_inventory.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(inventory[0].keys()))
        writer.writeheader()
        writer.writerows(inventory)

    return {
        "rows": inventory,
        "summary": {
            "n_events": len(rows),
            "n_complete": complete_count,
            "n_large_catalog_time_delta": large_time_delta,
            "output_csv": str(out_path),
            "checks": {
                "all_events_complete": check_status(complete_count == len(rows), f"{complete_count}/{len(rows)} complete"),
                "catalog_matches_explainable": {
                    "status": "pass" if large_time_delta == 0 else "warn",
                    "detail": "all catalog matches within 30 s" if large_time_delta == 0 else f"{large_time_delta} events required event-id fallback",
                },
            },
        },
    }


def representative_event_ids(rows):
    available = {row["event_id"] for row in rows}
    chosen = [event_id for event_id in REPRESENTATIVE_EVENTS if event_id in available]
    if len(chosen) == 3:
        return chosen
    for row in rows:
        if row["event_id"] not in chosen:
            chosen.append(row["event_id"])
        if len(chosen) == 3:
            break
    return chosen


def plot_preprocessing_gallery(event_ids, processed_dir: Path, out_dir: Path):
    summaries = []
    for event_id in event_ids:
        zne = read(str(processed_dir / f"{event_id}_ZNE.mseed"))
        z_trace = zne.select(channel="BHZ")[0]
        n_trace = zne.select(channel="BHN")[0]
        e_trace = zne.select(channel="BHE")[0]
        raw_t = np.arange(z_trace.stats.npts) / float(z_trace.stats.sampling_rate)

        paper0_provenance.validate_normalized_products(event_id, processed_dir, "ablation", "C", "waveform")
        ablation = _read_single_trace(processed_dir / f"{event_id}_aligned_ablation.mseed")
        paper0_provenance.validate_normalized_products(event_id, processed_dir, "paperfaith", "C", "waveform")
        paperfaith = _read_single_trace(processed_dir / f"{event_id}_aligned_paperfaith.mseed")
        rel_t = np.load(processed_dir / f"{event_id}_paperfaith_times.npy")
        diff = np.asarray(paperfaith.data, dtype=np.float64) - np.asarray(ablation.data, dtype=np.float64)
        rel_l2 = _relative_l2(np.asarray(ablation.data, dtype=np.float64), np.asarray(paperfaith.data, dtype=np.float64))

        fig, axes = plt.subplots(4, 1, figsize=(12, 10), sharex=False)
        axes[0].plot(raw_t, z_trace.data, label="Z", lw=0.8)
        axes[0].plot(raw_t, n_trace.data, label="N", lw=0.8, alpha=0.8)
        axes[0].plot(raw_t, e_trace.data, label="E", lw=0.8, alpha=0.8)
        axes[0].set_title(f"{event_id}: rotated ZNE")
        axes[0].legend(loc="upper right", ncol=3, fontsize=8)

        axes[1].plot(rel_t, ablation.data, color="tab:blue", lw=0.8)
        axes[1].axvline(0.0, color="black", ls="--", lw=0.8)
        axes[1].set_title("Aligned ablation Z")

        axes[2].plot(rel_t, paperfaith.data, color="tab:orange", lw=0.8)
        axes[2].axvline(0.0, color="black", ls="--", lw=0.8)
        axes[2].set_title("Aligned public paper-style Z")

        axes[3].plot(rel_t, diff, color="tab:red", lw=0.8)
        axes[3].axvline(0.0, color="black", ls="--", lw=0.8)
        axes[3].set_title(f"Difference (public paper-style - ablation), rel L2={rel_l2:.4f}")
        axes[3].set_xlabel("Time relative to P (s)")

        for ax in axes[1:]:
            ax.set_xlim(-100, 1500)

        out_path = out_dir / "figures" / f"{event_id}_preprocessing_gallery.png"
        _save_figure(fig, out_path)
        summaries.append(
            {
                "event_id": event_id,
                "relative_l2_diff": rel_l2,
                "figure": str(out_path),
                "check": {
                    "status": "pass" if rel_l2 > 0.0 else "warn",
                    "detail": "public paper-style branch differs from ablation" if rel_l2 > 0.0 else "branches are identical",
                },
            }
        )
    return summaries


def build_alignment_sheet(rows, processed_dir: Path, out_dir: Path, mode: str, input_type: str):
    selected = [row for row in rows if row["set"] == "vespagram"]
    selected = sorted(selected, key=lambda row: float(row["distance_deg"]))
    arrays = []
    labels = []
    distances = []
    reference_time = None
    lengths = set()
    finite = True

    for row in selected:
        event_id = row["event_id"]
        if mode == "paperfaith":
            paper0_provenance.validate_normalized_products(event_id, processed_dir, "paperfaith", "C", input_type)
        elif mode == "ablation":
            paper0_provenance.validate_normalized_products(event_id, processed_dir, "ablation", "C", input_type)
        arr = np.load(processed_dir / f"{event_id}_{mode}_C_{input_type}.npy")
        time_axis = np.load(processed_dir / f"{event_id}_{mode}_C_times.npy")
        arrays.append(arr)
        labels.append(event_id)
        distances.append(float(row["distance_deg"]))
        lengths.add(arr.shape[0])
        finite = finite and np.isfinite(arr).all() and np.isfinite(time_axis).all()
        if reference_time is None:
            reference_time = time_axis

    matrix = np.stack(arrays, axis=0)
    fig, axes = plt.subplots(2, 1, figsize=(13, 9), sharex=True)
    im = axes[0].imshow(
        matrix,
        aspect="auto",
        origin="lower",
        extent=[reference_time[0], reference_time[-1], 0, len(labels)],
        cmap="RdBu_r",
        vmin=-np.percentile(np.abs(matrix), 95),
        vmax=np.percentile(np.abs(matrix), 95),
    )
    axes[0].set_yticks(np.arange(len(labels)) + 0.5)
    axes[0].set_yticklabels([f"{event_id} ({distance:.1f}°)" for event_id, distance in zip(labels, distances)], fontsize=7)
    axes[0].axvline(0.0, color="black", ls="--", lw=0.8)
    axes[0].set_title(f"Aligned {mode} {input_type} (variant C)")
    fig.colorbar(im, ax=axes[0], fraction=0.02, pad=0.01)

    axes[1].plot(reference_time, np.mean(np.abs(matrix), axis=0), color="tab:blue")
    axes[1].axvline(0.0, color="black", ls="--", lw=0.8)
    axes[1].set_title("Mean absolute amplitude across vespagram events")
    axes[1].set_xlabel("Time relative to P (s)")

    out_path = out_dir / "figures" / f"alignment_{mode}_{input_type}_C.png"
    _save_figure(fig, out_path)
    return {
        "mode": mode,
        "input_type": input_type,
        "n_events": len(labels),
        "uniform_length": len(lengths) == 1,
        "finite": bool(finite),
        "figure": str(out_path),
        "check": {
            "status": "pass" if len(lengths) == 1 and finite else "fail",
            "detail": f"{len(labels)} events, lengths={sorted(lengths)}",
        },
    }


def benchmark_peak_map(vesp_path: Path, require_current_provenance: bool = False):
    vals, payload_meta = detect_mod.detect(vesp_path, require_current_provenance=require_current_provenance)
    out = {}
    for phase, label, time_s, slowness_sdeg, power in vals:
        endpoint = REGISTERED_NAMED_ENDPOINTS.get((phase, label))
        key = (
            endpoint["registered_key"]
            if endpoint is not None
            else ("pkikp_global" if phase == "PKiKP" else f"pkkp_{label}")
        )
        row = {
            "phase": phase,
            "peak_label": label,
            "registered_key": key,
            "endpoint_label": endpoint["endpoint_label"] if endpoint else "",
            "display_label": endpoint["display_label"] if endpoint else key,
            "window": endpoint["window"] if endpoint else "",
            "role": endpoint["role"] if endpoint else "",
            "primary_lane_variant": REGISTERED_PRIMARY_LANE_BY_PHASE.get(phase, ""),
            "time_s": float(time_s),
            "slowness_sdeg": float(slowness_sdeg),
            "power": float(power),
        }
        out[key] = row
        if endpoint is not None:
            out[endpoint["endpoint_label"]] = dict(row)
    out["_current_provenance_status"] = payload_meta.get("current_provenance_status", "not_required")
    return out


def _named_endpoint_rows(peaks: dict) -> list[dict]:
    return [
        dict(peaks["published_PKIKP_box"]),
        dict(peaks["displaced_ridge"]),
        dict(peaks["PKKP_target"]),
    ]


def plot_benchmark_vespagram(
    vesp_path: Path,
    out_dir: Path,
    validation_mode: str = "current-run",
    require_current_provenance: bool = False,
):
    payload = np.load(vesp_path, allow_pickle=False)
    v = payload["vespagram"]
    s = payload["slowness_axis"]
    t = payload["time_axis"]
    peaks = benchmark_peak_map(vesp_path, require_current_provenance=require_current_provenance)

    fig, axes = plt.subplots(3, 1, figsize=(12, 11), sharex=False)
    panels = [
        ("Full benchmark vespagram", (t[0], t[-1]), (s[0], s[-1])),
        ("PKiKP window", (550, 700), (-10, 0)),
        ("PKKP window", (1200, 1500), (-10, 0)),
    ]
    for ax, (title, xlim, ylim) in zip(axes, panels):
        im = ax.imshow(
            v,
            aspect="auto",
            origin="lower",
            extent=[t[0], t[-1], s[0], s[-1]],
            cmap="viridis",
        )
        ax.set_xlim(*xlim)
        ax.set_ylim(*ylim)
        ax.set_title(title)
        ax.set_ylabel("Slowness (s/°)")
        fig.colorbar(im, ax=ax, fraction=0.02, pad=0.01)

    axes[0].scatter([HISTORICAL_PRE_CURRENT_BASELINE["pkikp_global"]["time_s"]], [HISTORICAL_PRE_CURRENT_BASELINE["pkikp_global"]["slowness_sdeg"]], c="white", edgecolors="black", label="Historical PKiKP")
    axes[0].scatter([HISTORICAL_PRE_CURRENT_BASELINE["pkkp_paper_target"]["time_s"]], [HISTORICAL_PRE_CURRENT_BASELINE["pkkp_paper_target"]["slowness_sdeg"]], c="red", edgecolors="white", label="Historical PKKP target")
    axes[0].legend(loc="upper right", fontsize=8)
    axes[1].scatter([peaks["displaced_ridge"]["time_s"]], [peaks["displaced_ridge"]["slowness_sdeg"]], c="lime", edgecolors="black", label="displaced_ridge")
    axes[1].scatter([peaks["published_PKIKP_box"]["time_s"]], [peaks["published_PKIKP_box"]["slowness_sdeg"]], c="white", edgecolors="black", label="published_PKIKP_box")
    axes[1].legend(loc="upper right", fontsize=8)
    axes[2].scatter([peaks["PKKP_target"]["time_s"]], [peaks["PKKP_target"]["slowness_sdeg"]], c="red", edgecolors="white")
    axes[2].scatter([detect_mod.PAPER_PKKP1[0], detect_mod.PAPER_PKKP2[0]], [detect_mod.PAPER_PKKP1[1], detect_mod.PAPER_PKKP2[1]], c=["cyan", "magenta"], edgecolors="black")
    axes[-1].set_xlabel("Time relative to P (s)")

    out_path = out_dir / "figures" / "benchmark_vespagram_validation.png"
    _save_figure(fig, out_path)

    pkikp_dt = peaks["displaced_ridge"]["time_s"] - HISTORICAL_PRE_CURRENT_BASELINE["pkikp_global"]["time_s"]
    pkikp_ds = peaks["displaced_ridge"]["slowness_sdeg"] - HISTORICAL_PRE_CURRENT_BASELINE["pkikp_global"]["slowness_sdeg"]
    pkkp_dt = peaks["PKKP_target"]["time_s"] - HISTORICAL_PRE_CURRENT_BASELINE["pkkp_paper_target"]["time_s"]
    pkkp_ds = peaks["PKKP_target"]["slowness_sdeg"] - HISTORICAL_PRE_CURRENT_BASELINE["pkkp_paper_target"]["slowness_sdeg"]
    stable = max(abs(pkikp_dt), abs(pkikp_ds), abs(pkkp_dt), abs(pkkp_ds)) < 0.1
    historical_regression = validation_mode == "historical-regression"

    return {
        "figure": str(out_path),
        "peaks": peaks,
        "named_endpoint_rows": _named_endpoint_rows(peaks),
        "current_provenance_status": peaks.get("_current_provenance_status", "not_required"),
        "validation_mode": validation_mode,
        "historical_pre_current_baseline": HISTORICAL_PRE_CURRENT_BASELINE,
        "deltas_vs_recorded": {
            "pkikp_dt_s": float(pkikp_dt),
            "pkikp_ds_sdeg": float(pkikp_ds),
            "pkkp_target_dt_s": float(pkkp_dt),
            "pkkp_target_ds_sdeg": float(pkkp_ds),
        },
        "check": {
            "status": ("pass" if stable else "warn") if historical_regression else "pass",
            "detail": (
                "historical regression matches March 10 Paper0 values"
                if historical_regression and stable
                else "historical regression differs from March 10 Paper0 values"
                if historical_regression
                else "current-run audit does not gate on the historical pre-current-run baseline; published-target replication gates remain separate"
            ),
        },
    }


def summarize_bootstrap_fidelity(bootstrap_dir: Path) -> dict:
    required = {
        "pkikp": bootstrap_dir / "type1_pkikp_occupancy.npz",
        "pkkp": bootstrap_dir / "type1_pkkp_occupancy.npz",
    }
    failures = []
    rows = {}
    for phase, path in required.items():
        if not path.exists():
            failures.append(f"missing {path.name}")
            continue
        try:
            with np.load(path, allow_pickle=False) as payload:
                rows[phase] = _read_bootstrap_fidelity(payload, path.name)
        except Exception as exc:
            failures.append(f"{path.name}: {exc}")
    if failures:
        return {
            "status": "fail",
            "detail": "; ".join(failures),
            "level": "unavailable",
            "n_bootstrap": 0,
            "published_equivalent": False,
            "published_n_bootstrap": 10000,
            "phases": rows,
        }
    if len({(row["level"], row["n_bootstrap"], row["published_equivalent"], row["published_n_bootstrap"]) for row in rows.values()}) != 1:
        return {
            "status": "fail",
            "detail": "inconsistent bootstrap fidelity metadata across Type I phase artifacts",
            "level": "inconsistent",
            "n_bootstrap": 0,
            "published_equivalent": False,
            "published_n_bootstrap": 10000,
            "phases": rows,
        }
    first = next(iter(rows.values()))
    status = "pass"
    detail = (
        f"{first['level']} with N={first['n_bootstrap']}; "
        f"published-equivalent={first['published_equivalent']}"
    )
    return {
        "status": status,
        "detail": detail,
        "level": first["level"],
        "n_bootstrap": int(first["n_bootstrap"]),
        "published_equivalent": bool(first["published_equivalent"]),
        "published_n_bootstrap": int(first["published_n_bootstrap"]),
        "phases": rows,
    }


def plot_bootstrap_diagnostics(bootstrap_dir: Path, bootstrap_csv: Path, out_dir: Path, benchmark_summary: dict):
    fidelity = summarize_bootstrap_fidelity(bootstrap_dir)
    if fidelity["status"] == "fail":
        return {
            "figures": {},
            "bootstrap_85": {},
            "checks": {
                "pkikp": {"status": "fail", "detail": fidelity["detail"]},
                "pkkp": {"status": "fail", "detail": fidelity["detail"]},
            },
            "fidelity": fidelity,
        }
    bootstrap_rows = _read_bootstrap_rows(bootstrap_csv)
    bootstrap_85 = {
        row["phase"]: row
        for row in bootstrap_rows
        if int(float(row["threshold_pct"])) == 85
    }

    figure_paths = {}
    checks = {}
    for phase in ("pkikp", "pkkp"):
        name = f"type1_{phase}_occupancy.npz"
        payload = np.load(bootstrap_dir / name, allow_pickle=False)
        occ = payload["occupancy"]
        s = payload["slowness_axis"]
        t = payload["time_axis"]

        fig, ax = plt.subplots(figsize=(10, 4.5))
        im = ax.imshow(
            occ,
            aspect="auto",
            origin="lower",
            extent=[t[0], t[-1], s[0], s[-1]],
            cmap="magma",
        )
        row = bootstrap_85[phase]
        if _row_bool(row, "degenerate_fit"):
            ax.scatter(
                [float(row["occupancy_argmax_time_s"])],
                [float(row["occupancy_argmax_slowness_sdeg"])],
                c="cyan",
                edgecolors="black",
                label="Bootstrap 85% argmax",
            )
            ax.scatter(
                [float(row["weighted_median_time_s"])],
                [float(row["weighted_median_slowness_sdeg"])],
                c="deepskyblue",
                marker="x",
                label="Bootstrap 85% weighted median",
            )
        else:
            ax.scatter([float(row["mean_time_s"])], [float(row["mean_slowness_sdeg"])], c="cyan", edgecolors="black", label="Bootstrap 85% Gaussian fit")
        if phase == "pkikp":
            ax.scatter([detect_mod.PAPER_PKIKP[0]], [detect_mod.PAPER_PKIKP[1]], c="white", edgecolors="black", label="Paper target")
            peak_rows = benchmark_summary["peaks"]
            single = peak_rows["displaced_ridge"] if "displaced_ridge" in peak_rows else peak_rows["pkikp_global"]
        else:
            ax.scatter([detect_mod.PAPER_PKKP2[0]], [detect_mod.PAPER_PKKP2[1]], c="white", edgecolors="black", label="Paper target")
            peak_rows = benchmark_summary["peaks"]
            single = peak_rows["PKKP_target"] if "PKKP_target" in peak_rows else peak_rows["pkkp_paper_target"]
        ax.scatter([single["time_s"]], [single["slowness_sdeg"]], c="lime", edgecolors="black", label="Single vespagram")
        ax.legend(loc="upper right", fontsize=8)
        ax.set_title(f"Bootstrap occupancy: {phase.upper()}")
        ax.set_xlabel("Time relative to P (s)")
        ax.set_ylabel("Slowness (s/°)")
        fig.colorbar(im, ax=ax, fraction=0.02, pad=0.01)

        out_path = out_dir / "figures" / f"bootstrap_{phase}_diagnostic.png"
        _save_figure(fig, out_path)
        figure_paths[phase] = str(out_path)

        paper_target = detect_mod.PAPER_PKIKP if phase == "pkikp" else detect_mod.PAPER_PKKP2
        checks[phase] = _bootstrap_check_detail(phase, row, paper_target)

    return {
        "figures": figure_paths,
        "bootstrap_85": bootstrap_85,
        "checks": checks,
        "fidelity": fidelity,
    }


def check_type3_jitter_artifacts(bootstrap_dir: Path) -> dict:
    required = {
        "pkikp": bootstrap_dir / "type3_pkikp_p_pick_jitter.npz",
        "pkkp": bootstrap_dir / "type3_pkkp_p_pick_jitter.npz",
    }
    rows = {}
    failures = []
    for phase, path in required.items():
        if not path.exists():
            failures.append(f"missing {path.name}")
            rows[phase] = {"status": "fail", "path": str(path), "reason": "missing"}
            continue
        try:
            with np.load(path, allow_pickle=False) as payload:
                needed = {
                    "occupancy",
                    "occupancy_maps",
                    "jitter_seconds",
                    "event_ids",
                    "peak_times",
                    "base_peak_time_s",
                    "base_peak_slowness_sdeg",
                    "mode",
                    "variant",
                    "input_type",
                    "input_provenance_json",
                }
                missing = sorted(needed.difference(payload.files))
                if missing:
                    raise ValueError(f"missing keys: {', '.join(missing)}")
                fidelity = _read_bootstrap_fidelity(payload, path.name)
                rows[phase] = {
                    "status": "pass",
                    "path": str(path),
                    "n_bootstrap": int(payload["n_bootstrap"]),
                    "bootstrap_fidelity_level": fidelity["level"],
                    "published_equivalent": fidelity["published_equivalent"],
                    "n_events": int(payload["event_ids"].size),
                    "jitter_limit_s": float(payload["jitter_limit_s"]),
                    "base_peak_time_s": float(payload["base_peak_time_s"]),
                    "base_peak_slowness_sdeg": float(payload["base_peak_slowness_sdeg"]),
                    "mode": str(payload["mode"]),
                    "variant": str(payload["variant"]),
                    "input_type": str(payload["input_type"]),
                }
        except Exception as exc:
            failures.append(f"{path.name}: {exc}")
            rows[phase] = {"status": "fail", "path": str(path), "reason": str(exc)}
    return {
        "status": "fail" if failures else "pass",
        "detail": "; ".join(failures) if failures else "Type III jitter artifacts are present and structurally valid",
        "phases": rows,
    }


def check_type2_distance_artifacts(bootstrap_dir: Path) -> dict:
    required = {
        "pkikp": bootstrap_dir / "type2_pkikp_distance_stratified_occupancy.npz",
        "pkkp": bootstrap_dir / "type2_pkkp_distance_stratified_occupancy.npz",
    }
    rows = {}
    failures = []
    for phase, path in required.items():
        if not path.exists():
            failures.append(f"missing {path.name}")
            rows[phase] = {"status": "fail", "path": str(path), "reason": "missing"}
            continue
        try:
            with np.load(path, allow_pickle=False) as payload:
                needed = {
                    "occupancy",
                    "occupancy_maps",
                    "threshold_pcts",
                    "peak_times",
                    "peak_slownesses",
                    "peak_powers",
                    "event_ids",
                    "distances",
                    "bootstrap_type",
                    "distance_bin_labels",
                    "selected_distance_bin_labels",
                    "selected_event_indices",
                    "support_at_peaks",
                    "minimum_support",
                    "stack_method",
                    "nth_root_order",
                    "power_window_s",
                    "mode",
                    "variant",
                    "input_type",
                    "input_provenance_json",
                }
                missing = sorted(needed.difference(payload.files))
                if missing:
                    raise ValueError(f"missing keys: {', '.join(missing)}")
                fidelity = _read_bootstrap_fidelity(payload, path.name)
                bootstrap_type = str(_payload_scalar(payload, "bootstrap_type", ""))
                if bootstrap_type != "type2_distance_stratified":
                    raise ValueError(f"unexpected bootstrap_type={bootstrap_type}")
                selected = np.asarray(payload["selected_distance_bin_labels"])
                if selected.ndim != 2 or selected.shape[0] != int(payload["n_bootstrap"]):
                    raise ValueError("selected_distance_bin_labels shape does not match n_bootstrap")
                rows[phase] = {
                    "status": "pass",
                    "path": str(path),
                    "n_bootstrap": int(payload["n_bootstrap"]),
                    "bootstrap_fidelity_level": fidelity["level"],
                    "published_equivalent": fidelity["published_equivalent"],
                    "n_events": int(payload["event_ids"].size),
                    "mode": str(_payload_scalar(payload, "mode", "")),
                    "variant": str(_payload_scalar(payload, "variant", "")),
                    "input_type": str(_payload_scalar(payload, "input_type", "")),
                }
        except Exception as exc:
            failures.append(f"{path.name}: {exc}")
            rows[phase] = {"status": "fail", "path": str(path), "reason": str(exc)}
    return {
        "status": "fail" if failures else "pass",
        "detail": "; ".join(failures) if failures else "Type II distance-stratified artifacts are present and structurally valid",
        "phases": rows,
    }


def check_deglitch_summary(processed_dir: Path) -> dict:
    candidates = [
        processed_dir / "deglitch_run_summary.json",
        repo_path("data/deglitched/deglitch_run_summary.json"),
    ]
    summary_path = next((path for path in candidates if path.exists()), None)
    if summary_path is None:
        return {
            "status": "fail",
            "detail": "missing deglitch_run_summary.json",
            "summary_path": "",
        }
    try:
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
        complete = payload.get("run_status") == "complete"
        events = payload.get("events", [])
        status_counts = payload.get("status_counts", {})
        unverified_statuses = sorted(status for status in status_counts if status != VERIFIED_DEGLITCH_STATUS)
        verified = complete and bool(events) and not unverified_statuses and set(status_counts) == {VERIFIED_DEGLITCH_STATUS}
        accepted_partial_lane = complete and bool(events) and set(status_counts) == {"succeeded_mps_only"}
        if verified:
            attestation_level = VERIFIED_DEGLITCH_STATUS
        elif accepted_partial_lane:
            attestation_level = "succeeded_mps_only"
        elif unverified_statuses:
            attestation_level = ",".join(unverified_statuses)
        else:
            attestation_level = "unverified"
        return {
            "status": "pass" if verified else "fail",
            "detail": (
                "deglitch run summary verified MPS+UCLA for every event"
                if verified
                else (
                    "deglitch run summary is missing verified MPS+UCLA status for every event; "
                    f"unverified statuses: {', '.join(unverified_statuses) if unverified_statuses else 'none'}"
                )
            ),
            "summary_path": str(summary_path),
            "summary_sha256": sha256_file(summary_path),
            "status_counts": status_counts,
            "verified_only_gate": VERIFIED_DEGLITCH_STATUS,
            "unverified_statuses": unverified_statuses,
            "attestation_level": attestation_level,
            "accepted_partial_lane_by_design": accepted_partial_lane,
            "n_events": len(events),
        }
    except Exception as exc:
        return {
            "status": "fail",
            "detail": f"could not parse deglitch summary: {exc}",
            "summary_path": str(summary_path),
        }


def validate_branch_registry_for_validation_report(path: Path | None) -> dict:
    if path is None:
        return {
            "status": "not_requested",
            "detail": "branch registry validation was not requested",
            "path": "",
            "row_count": 0,
            "endpoints": [],
        }
    path = Path(path)
    if not path.exists():
        return {
            "status": "fail",
            "detail": f"missing branch registry: {path}",
            "path": str(path),
            "row_count": 0,
            "endpoints": [],
        }
    try:
        rows = branch_registry.validate_registry_consistency(
            branch_registry.read_registry(path),
            required_same=("branch", "lane", "code_commit"),
        )
    except Exception as exc:
        return {
            "status": "fail",
            "detail": str(exc),
            "path": str(path),
            "row_count": 0,
            "endpoints": [],
        }
    return {
        "status": "pass",
        "detail": "branch registry rows are schema-valid and consistent on branch/lane/commit",
        "path": str(path),
        "row_count": len(rows),
        "endpoints": sorted(str(row["endpoint"]) for row in rows),
        "branch": rows[0]["branch"],
        "lane": rows[0]["lane"],
        "code_commit": rows[0]["code_commit"],
    }


def _combine_sections(mantle: np.ndarray, oc: np.ndarray, ic: np.ndarray) -> np.ndarray:
    parts = []
    for arr in (mantle, oc, ic):
        if arr.size:
            parts.append(arr)
    return np.vstack(parts)


def check_model_taup_archive(generated_model: Path) -> dict:
    generated_model = Path(generated_model)
    npz_path = generated_model if generated_model.suffix == ".npz" else generated_model.with_suffix(".npz")
    result = {
        "model_npz": str(npz_path),
        "source_depth_km": REGISTERED_MODEL_QUERY_SOURCE_DEPTH_KM,
        "distance_deg": REGISTERED_MODEL_QUERY_DISTANCE_DEG,
        "expected_arrival_times_s": dict(REGISTERED_MODEL_EXPECTED_ARRIVAL_TIMES_S),
        "arrival_tolerance_s": REGISTERED_MODEL_ARRIVAL_TOLERANCE_S,
        "arrival_times_s": {},
    }
    if not npz_path.is_file():
        result["check"] = check_status(
            False,
            f"missing generated TauP model archive: {npz_path}",
        )
        return result

    try:
        model = TauPyModel(model=str(npz_path))
        arrivals = model.get_travel_times(
            source_depth_in_km=REGISTERED_MODEL_QUERY_SOURCE_DEPTH_KM,
            distance_in_degree=REGISTERED_MODEL_QUERY_DISTANCE_DEG,
            phase_list=list(REGISTERED_MODEL_EXPECTED_ARRIVAL_TIMES_S),
        )
    except Exception as exc:
        result["check"] = check_status(
            False,
            f"could not load/query generated TauP model archive {npz_path}: {type(exc).__name__}: {exc}",
        )
        return result

    errors = []
    arrival_times: dict[str, float] = {}
    for phase, expected in REGISTERED_MODEL_EXPECTED_ARRIVAL_TIMES_S.items():
        finite = sorted(
            float(arrival.time)
            for arrival in arrivals
            if arrival.phase.name == phase and np.isfinite(arrival.time)
        )
        if not finite:
            errors.append(f"missing finite {phase} arrival")
            continue
        actual = finite[0]
        arrival_times[phase] = actual
        if abs(actual - expected) > REGISTERED_MODEL_ARRIVAL_TOLERANCE_S:
            errors.append(
                f"stale {phase} arrival {actual:.6f}s differs from registered "
                f"{expected:.2f}s by more than {REGISTERED_MODEL_ARRIVAL_TOLERANCE_S:.2f}s"
            )
    result["arrival_times_s"] = arrival_times

    p_time = arrival_times.get("P")
    pkikp_time = arrival_times.get("PKiKP")
    if p_time is not None and pkikp_time is not None and not p_time < pkikp_time:
        errors.append(
            f"arrival ordering violated: P={p_time:.6f}s must precede PKiKP={pkikp_time:.6f}s"
        )

    result["check"] = check_status(
        not errors,
        "; ".join(errors),
        (
            "generated TauP archive returns finite ordered registered arrivals "
            f"at {REGISTERED_MODEL_QUERY_DISTANCE_DEG:.1f} deg/"
            f"{REGISTERED_MODEL_QUERY_SOURCE_DEPTH_KM:.0f} km"
        ),
    )
    return result


def plot_model_profiles(base_model: Path, generated_model: Path, out_dir: Path):
    base_mantle, base_oc, base_ic, _ = model_mod.read_nd_model(base_model)
    gen_mantle, gen_oc, gen_ic, _ = model_mod.read_nd_model(generated_model)
    base = _combine_sections(base_mantle, base_oc, base_ic)
    gen = _combine_sections(gen_mantle, gen_oc, gen_ic)

    fig, axes = plt.subplots(1, 3, figsize=(14, 8), sharey=True)
    labels = [("Vp", 1), ("Vs", 2), ("Density", 3)]
    for ax, (label, idx) in zip(axes, labels):
        ax.plot(base[:, idx], base[:, 0], label="Base AK_mean", lw=1.0)
        ax.plot(gen[:, idx], gen[:, 0], label="Generated ref", lw=1.2)
        ax.set_xlabel(label)
        ax.invert_yaxis()
        ax.grid(alpha=0.2)
    axes[0].set_ylabel("Depth (km)")
    axes[0].legend(loc="best", fontsize=8)
    axes[0].set_title("Base vs generated model profiles")

    out_path = out_dir / "figures" / "model_profile_validation.png"
    _save_figure(fig, out_path)

    outer_core_vs_zero = bool(np.allclose(gen_oc[:, 2], 0.0))
    depth_monotonic = bool(np.all(np.diff(gen[:, 0]) >= 0.0))
    taup = check_model_taup_archive(generated_model)
    taup_ok = taup["check"]["status"] == "pass"
    profile_ok = outer_core_vs_zero and depth_monotonic
    errors = []
    if not outer_core_vs_zero:
        errors.append("generated model outer-core Vs is not zero")
    if not depth_monotonic:
        errors.append("generated model depths are not non-decreasing")
    if not taup_ok:
        errors.append(taup["check"]["detail"])

    return {
        "figure": str(out_path),
        "generated_model": str(generated_model),
        "generated_npz_exists": generated_model.with_suffix(".npz").exists(),
        "outer_core_vs_zero": outer_core_vs_zero,
        "depth_monotonic": depth_monotonic,
        "taup": taup,
        "check": check_status(
            profile_ok and taup_ok,
            "; ".join(errors),
            "generated model has liquid outer core, non-decreasing depths, and registered TauP arrivals",
        ),
    }


def write_markdown_summary(summary: dict, path: Path):
    lane = benchmark_lane_label()
    benchmark_check = summary["benchmark"]["check"]
    deglitch = summary["deglitch"]
    fidelity = summary.get("bootstrap_fidelity", summary.get("bootstrap", {}).get("fidelity", {}))
    endpoint_rows = {}
    for row in summary["benchmark"].get("named_endpoint_rows", []):
        label = row.get("endpoint_label") or row.get("display_label")
        if label:
            endpoint_rows[label] = row
    if not endpoint_rows:
        endpoint_rows = {
            key: value
            for key, value in summary["benchmark"]["peaks"].items()
            if key in {"published_PKIKP_box", "displaced_ridge", "PKKP_target"}
        }
    lines = [
        "# Validation Summary",
        "",
        f"- Inventory: {summary['inventory']['summary']['n_complete']}/{summary['inventory']['summary']['n_events']} events complete",
        f"- Benchmark combo: {BENCHMARK_COMBO['mode']} / {BENCHMARK_COMBO['input_type']} / {BENCHMARK_COMBO['variant']} / {BENCHMARK_COMBO['stack_method']} / {BENCHMARK_COMBO['power_window_s']} s",
        (
            f"- Benchmark check [lane={lane}; audit=current-run-stale-baseline]: "
            f"{benchmark_check['status']} — {_benchmark_check_detail(benchmark_check)}"
        ),
        (
            "- Benchmark displaced_ridge "
            f"[key=displaced_ridge; lane={lane}; window=550-700s]: "
            f"t={float(endpoint_rows['displaced_ridge']['time_s']):.2f}s, "
            f"s={float(endpoint_rows['displaced_ridge']['slowness_sdeg']):.2f}s/deg"
        ),
        (
            "- Benchmark published_PKIKP_box "
            f"[key=published_PKIKP_box; lane={lane}; window=584-624s]: "
            f"t={float(endpoint_rows['published_PKIKP_box']['time_s']):.2f}s, "
            f"s={float(endpoint_rows['published_PKIKP_box']['slowness_sdeg']):.2f}s/deg"
        ),
        (
            "- Benchmark PKKP_target "
            f"[key=PKKP_target; lane={lane}; window=1320-1360s]: "
            f"t={float(endpoint_rows['PKKP_target']['time_s']):.2f}s, "
            f"s={float(endpoint_rows['PKKP_target']['slowness_sdeg']):.2f}s/deg"
        ),
        "- Delta notation: all validation offsets use explicit Δ versus the named target",
        (
            f"- Bootstrap fidelity: {fidelity.get('level', 'unavailable')} "
            f"(N={int(fidelity.get('n_bootstrap', 0))}; "
            f"published-equivalent={bool(fidelity.get('published_equivalent', False))}; "
            f"published N={int(fidelity.get('published_n_bootstrap', 10000))})"
        ),
        f"- Bootstrap PKiKP: {summary['bootstrap']['checks']['pkikp']['status']} — {summary['bootstrap']['checks']['pkikp']['detail']}",
        f"- Bootstrap PKKP: {summary['bootstrap']['checks']['pkkp']['status']} — {summary['bootstrap']['checks']['pkkp']['detail']}",
        f"- Type II distance-stratified artifacts: {summary['type2_distance_stratified']['status']} — {summary['type2_distance_stratified']['detail']}",
        f"- Type III jitter artifacts: {summary['type3_alignment_jitter']['status']} — {summary['type3_alignment_jitter']['detail']}",
        f"- Deglitch summary [{_deglitch_label(deglitch)}]: {deglitch['status']} — {deglitch['detail']}",
        f"- Model profile: {summary['model']['check']['status']} — {summary['model']['check']['detail']}",
        "",
        "## Representative event galleries",
    ]
    for item in summary["preprocessing"]:
        lines.append(f"- {item['event_id']}: rel L2 diff = {item['relative_l2_diff']:.4f} ({item['figure']})")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def evaluate_validation_status(summary: dict) -> dict:
    failures = []

    def add_if_failed(name: str, check: dict | None):
        if not check:
            failures.append(f"{name}: missing check")
            return
        if str(check.get("status", "")).lower() == "fail":
            detail = str(check.get("detail", "")).strip()
            failures.append(f"{name}: {detail}" if detail else name)

    inventory_checks = summary.get("inventory", {}).get("summary", {}).get("checks", {})
    add_if_failed("inventory.all_events_complete", inventory_checks.get("all_events_complete"))
    add_if_failed("benchmark.current_run", summary.get("benchmark", {}).get("check"))
    add_if_failed("bootstrap.fidelity", summary.get("bootstrap_fidelity"))
    add_if_failed("type2_distance_stratified", summary.get("type2_distance_stratified"))
    add_if_failed("type3_alignment_jitter", summary.get("type3_alignment_jitter"))
    add_if_failed("deglitch", summary.get("deglitch"))
    if summary.get("branch_registry", {}).get("status") != "not_requested":
        add_if_failed("branch_registry", summary.get("branch_registry"))
    add_if_failed("model", summary.get("model", {}).get("check"))
    for item in summary.get("preprocessing", []):
        event_id = str(item.get("event_id", "unknown"))
        add_if_failed(f"preprocessing.{event_id}", item.get("check"))
    for name, item in summary.get("alignment", {}).items():
        add_if_failed(f"alignment.{name}", item.get("check"))

    enforcement = summary.get("current_provenance_enforcement", {})
    if enforcement.get("requested") and not enforcement.get("enforced"):
        failures.append(
            "current_provenance_enforcement: requested but not enforced by peak/validation consumer"
        )

    return {
        "status": "failed" if failures else "passed",
        "failures": failures,
        "paper_ready": not failures,
    }


def validation_exit_code(summary: dict, strict_gates: bool) -> int:
    if strict_gates and summary.get("validation_status", {}).get("status") != "passed":
        return 2
    return 0


def _incremental_validation_path(out_dir: Path, check: str) -> Path:
    return out_dir / INCREMENTAL_VALIDATION_DIR / f"{check}.json"


def _compute_validation_fragment(
    check: str,
    event_table: Path,
    catalog_path: Path,
    raw_dir: Path,
    processed_dir: Path,
    vesp_dir: Path,
    bootstrap_dir: Path,
    bootstrap_csv: Path,
    base_model: Path,
    generated_model: Path,
    out_dir: Path,
    validation_mode: str = "current-run",
    require_current_provenance: bool = False,
    computed_fragments: dict[str, dict] | None = None,
    read_incremental_fragments: bool = False,
) -> dict:
    if check == "inventory":
        return {"inventory": build_event_inventory(event_table, catalog_path, raw_dir, processed_dir, out_dir)}
    if check == "preprocessing":
        return {
            "preprocessing": plot_preprocessing_gallery(
                representative_event_ids(load_event_table(event_table)),
                processed_dir,
                out_dir,
            )
        }
    if check == "alignment":
        loaded_event_table = load_event_table(event_table)
        return {
            "alignment": {
                "ablation_waveform": build_alignment_sheet(loaded_event_table, processed_dir, out_dir, "ablation", "waveform"),
                "paperfaith_waveform": build_alignment_sheet(loaded_event_table, processed_dir, out_dir, "paperfaith", "waveform"),
                "paperfaith_envelope": build_alignment_sheet(loaded_event_table, processed_dir, out_dir, "paperfaith", "envelope"),
            }
        }
    if check == "benchmark":
        benchmark_path = (
            vesp_dir
            / BENCHMARK_COMBO["mode"]
            / BENCHMARK_COMBO["input_type"]
            / BENCHMARK_COMBO["variant"]
            / f"{BENCHMARK_COMBO['stack_method']}_win{BENCHMARK_COMBO['power_window_s']}.npz"
        )
        return {
            "benchmark": plot_benchmark_vespagram(
                benchmark_path,
                out_dir,
                validation_mode=validation_mode,
                require_current_provenance=require_current_provenance,
            )
        }
    if check == "bootstrap":
        benchmark = None
        if computed_fragments is not None:
            benchmark = computed_fragments.get("benchmark", {}).get("benchmark")
        if benchmark is None and read_incremental_fragments:
            benchmark_fragment = _read_incremental_validation_fragment(out_dir, "benchmark").get("summary_fragment", {})
            benchmark = benchmark_fragment.get("benchmark")
        if benchmark is None:
            benchmark_path = (
                vesp_dir
                / BENCHMARK_COMBO["mode"]
                / BENCHMARK_COMBO["input_type"]
                / BENCHMARK_COMBO["variant"]
                / f"{BENCHMARK_COMBO['stack_method']}_win{BENCHMARK_COMBO['power_window_s']}.npz"
            )
            benchmark = plot_benchmark_vespagram(
                benchmark_path,
                out_dir,
                validation_mode=validation_mode,
                require_current_provenance=require_current_provenance,
            )
        bootstrap = plot_bootstrap_diagnostics(bootstrap_dir, bootstrap_csv, out_dir, benchmark)
        return {"bootstrap": bootstrap, "bootstrap_fidelity": bootstrap["fidelity"]}
    if check == "type2_distance_stratified":
        return {"type2_distance_stratified": check_type2_distance_artifacts(bootstrap_dir)}
    if check == "type3_alignment_jitter":
        return {"type3_alignment_jitter": check_type3_jitter_artifacts(bootstrap_dir)}
    if check == "deglitch":
        return {"deglitch": check_deglitch_summary(processed_dir)}
    if check == "model":
        return {"model": plot_model_profiles(base_model, generated_model, out_dir)}
    raise ValueError(f"Unknown validation check: {check}")


def _read_incremental_validation_fragment(out_dir: Path, check: str) -> dict:
    path = _incremental_validation_path(out_dir, check)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def run_incremental_validation_check(
    event_table: Path,
    catalog_path: Path,
    raw_dir: Path,
    processed_dir: Path,
    vesp_dir: Path,
    bootstrap_dir: Path,
    bootstrap_csv: Path,
    base_model: Path,
    generated_model: Path,
    out_dir: Path,
    check: str,
    validation_mode: str = "current-run",
    require_current_provenance: bool = False,
) -> tuple[Path, dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    fragment = {
        "check": check,
        "summary_fragment": _compute_validation_fragment(
            check,
            event_table,
            catalog_path,
            raw_dir,
            processed_dir,
            vesp_dir,
            bootstrap_dir,
            bootstrap_csv,
            base_model,
            generated_model,
            out_dir,
            validation_mode=validation_mode,
            require_current_provenance=require_current_provenance,
            read_incremental_fragments=True,
        ),
    }
    json_path = _incremental_validation_path(out_dir, check)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(fragment, indent=2, sort_keys=True), encoding="utf-8")
    return json_path, fragment


def _combine_validation_fragments(
    fragments: list[dict],
    validation_mode: str,
    require_current_provenance: bool,
    branch_registry_path: Path | None = None,
) -> dict:
    summary: dict = {}
    for fragment in fragments:
        summary.update(fragment.get("summary_fragment", {}))
    provenance_status = str(summary.get("benchmark", {}).get("current_provenance_status", "not_required"))
    current_provenance_enforcement = {
        "requested": bool(require_current_provenance),
        "enforced": bool(require_current_provenance and provenance_status == "current"),
        "status": provenance_status,
    }
    summary.update(
        {
            "validation_mode": validation_mode,
            "require_current_provenance": require_current_provenance,
            "current_provenance_enforcement": current_provenance_enforcement,
            "branch_registry": validate_branch_registry_for_validation_report(branch_registry_path),
        }
    )
    summary["validation_status"] = evaluate_validation_status(summary)
    summary["validation"] = summary["validation_status"]
    return summary


def aggregate_validation_report(
    out_dir: Path,
    validation_mode: str = "current-run",
    require_current_provenance: bool = False,
    branch_registry_path: Path | None = None,
) -> tuple[Path, Path, dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    fragments = []
    missing = []
    for check in VALIDATION_CHECKS:
        fragment = _read_incremental_validation_fragment(out_dir, check)
        if fragment:
            fragments.append(fragment)
        else:
            missing.append(check)
    if missing:
        summary = {
            "validation_mode": validation_mode,
            "require_current_provenance": require_current_provenance,
            "current_provenance_enforcement": {
                "requested": bool(require_current_provenance),
                "enforced": False,
                "status": "missing_incremental_validation",
            },
            "validation_status": {
                "status": "failed",
                "failures": [f"missing incremental validation check: {check}" for check in missing],
                "paper_ready": False,
            },
        }
        summary["validation"] = summary["validation_status"]
        json_path = out_dir / "validation_summary.json"
        md_path = out_dir / "validation_summary.md"
        json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        md_path.write_text(
            "# Validation Summary\n\n"
            + "\n".join(f"- Missing incremental validation check: {check}" for check in missing)
            + "\n",
            encoding="utf-8",
        )
        return json_path, md_path, summary

    summary = _combine_validation_fragments(fragments, validation_mode, require_current_provenance, branch_registry_path)
    json_path = out_dir / "validation_summary.json"
    md_path = out_dir / "validation_summary.md"
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_markdown_summary(summary, md_path)
    return json_path, md_path, summary


def generate_validation_report(
    event_table: Path,
    catalog_path: Path,
    raw_dir: Path,
    processed_dir: Path,
    vesp_dir: Path,
    bootstrap_dir: Path,
    bootstrap_csv: Path,
    base_model: Path,
    generated_model: Path,
    out_dir: Path,
    validation_mode: str = "current-run",
    require_current_provenance: bool = False,
    branch_registry_path: Path | None = None,
):
    out_dir.mkdir(parents=True, exist_ok=True)
    fragments = []
    computed_fragments: dict[str, dict] = {}
    for check in VALIDATION_CHECKS:
        summary_fragment = _compute_validation_fragment(
            check,
            event_table,
            catalog_path,
            raw_dir,
            processed_dir,
            vesp_dir,
            bootstrap_dir,
            bootstrap_csv,
            base_model,
            generated_model,
            out_dir,
            validation_mode=validation_mode,
            require_current_provenance=require_current_provenance,
            computed_fragments=computed_fragments,
        )
        fragments.append({"check": check, "summary_fragment": summary_fragment})
        computed_fragments[check] = summary_fragment
    summary = _combine_validation_fragments(fragments, validation_mode, require_current_provenance, branch_registry_path)

    json_path = out_dir / "validation_summary.json"
    md_path = out_dir / "validation_summary.md"
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_markdown_summary(summary, md_path)
    return json_path, md_path


def parse_args(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Generate automated validation report for the Paper0 baseline")
    parser.add_argument("--event-table", default=str(repo_path("manifest/event_table.csv")))
    parser.add_argument("--catalog", default=str(repo_path("data/raw/mqs_v14_catalog.xml")))
    parser.add_argument("--raw-dir", default=str(repo_path("data/raw")))
    parser.add_argument("--processed-dir", default=str(repo_path("data/processed")))
    parser.add_argument("--vesp-dir", default=str(repo_path("results/vespagrams")))
    parser.add_argument("--bootstrap-dir", default=str(repo_path("results/bootstrap")))
    parser.add_argument("--bootstrap-csv", default=str(repo_path("results/tables/bootstrap_picks.csv")))
    parser.add_argument("--base-model", default=str(repo_path("data/models/reference/AK_mean.nd")))
    parser.add_argument("--generated-model", default=str(repo_path("data/models/paper0_ref_1800.00-5.00-5.80-600.00-0.300.nd")))
    parser.add_argument("--out-dir", default=str(repo_path("results/validation")))
    parser.add_argument("--mode", choices=("current-run", "historical-regression"), default="current-run")
    parser.add_argument("--require-current-provenance", action="store_true")
    parser.add_argument("--branch-registry", default="")
    parser.add_argument("--strict-gates", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--incremental-check", choices=VALIDATION_CHECKS)
    parser.add_argument("--aggregate-only", action="store_true")
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = parse_args()
    if args.aggregate_only:
        json_path, md_path, summary = aggregate_validation_report(
            out_dir=Path(args.out_dir),
            validation_mode=args.mode,
            require_current_provenance=args.require_current_provenance,
            branch_registry_path=Path(args.branch_registry) if args.branch_registry else None,
        )
    elif args.incremental_check:
        json_path, fragment = run_incremental_validation_check(
            event_table=Path(args.event_table),
            catalog_path=Path(args.catalog),
            raw_dir=Path(args.raw_dir),
            processed_dir=Path(args.processed_dir),
            vesp_dir=Path(args.vesp_dir),
            bootstrap_dir=Path(args.bootstrap_dir),
            bootstrap_csv=Path(args.bootstrap_csv),
            base_model=Path(args.base_model),
            generated_model=Path(args.generated_model),
            out_dir=Path(args.out_dir),
            check=args.incremental_check,
            validation_mode=args.mode,
            require_current_provenance=args.require_current_provenance,
        )
        md_path = json_path.with_suffix(".md")
        md_path.write_text(f"# Validation Check\n\n- {args.incremental_check}: recorded\n", encoding="utf-8")
        summary = _combine_validation_fragments(
            [fragment],
            args.mode,
            args.require_current_provenance,
            Path(args.branch_registry) if args.branch_registry else None,
        )
    else:
        json_path, md_path = generate_validation_report(
            event_table=Path(args.event_table),
            catalog_path=Path(args.catalog),
            raw_dir=Path(args.raw_dir),
            processed_dir=Path(args.processed_dir),
            vesp_dir=Path(args.vesp_dir),
            bootstrap_dir=Path(args.bootstrap_dir),
            bootstrap_csv=Path(args.bootstrap_csv),
            base_model=Path(args.base_model),
            generated_model=Path(args.generated_model),
            out_dir=Path(args.out_dir),
            validation_mode=args.mode,
            require_current_provenance=args.require_current_provenance,
            branch_registry_path=Path(args.branch_registry) if args.branch_registry else None,
        )
        summary = json.loads(json_path.read_text(encoding="utf-8"))
    print(json_path)
    print(md_path)
    sys.exit(validation_exit_code(summary, strict_gates=args.strict_gates))
