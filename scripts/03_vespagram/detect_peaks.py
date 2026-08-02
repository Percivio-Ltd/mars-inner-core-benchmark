from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import re
import sys
from pathlib import Path

import numpy as np

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.shared import repo_path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


PAPER_PKIKP = (604.0, -6.5)
PAPER_PIKI = PAPER_PKIKP  # backward-compatible alias for older validation code
PAPER_PKKP1 = (1290.0, -8.0)
PAPER_PKKP2 = (1341.0, -7.0)
PKIKP_WINDOW = (550.0, 700.0)
PKKP_WINDOW = (1200.0, 1500.0)
PKKP_PAPER_TARGET_BOX = {
    "t_min": 1320.0,
    "t_max": 1360.0,
    "s_min": -8.0,
    "s_max": -6.0,
}
PKIKP_PUBLISHED_TARGET_BOX = {
    "name": "PKIKP_PUBLISHED",
    "t_min": 584.0,
    "t_max": 624.0,
    "s_min": -7.1,
    "s_max": -5.9,
}
PKKP_PUBLISHED_TARGET_BOX = {
    "name": "PKKP_PUBLISHED",
    **PKKP_PAPER_TARGET_BOX,
}
VESPAGRAM_ARTIFACT_SCHEMA_VERSION = "paper0-vespagram-mask-v1"
LANE_IDENTITY_FIELDS = (
    "mode",
    "input_type",
    "norm_variant",
    "stack_method",
    "power_window_s",
)


def _blocked_status(status: str, file_path: Path, reason: str) -> RuntimeError:
    return RuntimeError(
        json.dumps(
            {
                "status": status,
                "path": str(file_path),
                "reason": reason,
            },
            sort_keys=True,
        )
    )


def _payload_scalar(payload, key: str, default=""):
    if key not in payload:
        return default
    value = payload[key]
    if np.asarray(value).shape == ():
        return value.item()
    return value


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _payload_string_array(payload, key: str) -> list[str]:
    if key not in payload:
        return []
    arr = np.asarray(payload[key])
    if arr.shape == ():
        return [str(arr.item())]
    return [str(item) for item in arr.tolist()]


def _verify_path_hash_array(payload, path_key: str, hash_key: str, file_path: Path) -> list[str]:
    paths = _payload_string_array(payload, path_key)
    hashes = _payload_string_array(payload, hash_key)
    errors: list[str] = []
    if not paths or not hashes:
        return [f"missing {path_key}/{hash_key}"]
    if len(paths) != len(hashes):
        return [f"length mismatch {path_key}/{hash_key}"]
    for path_text, expected in zip(paths, hashes, strict=True):
        path = Path(path_text)
        if not path.exists():
            errors.append(f"missing file for {path_key}: {path}")
            continue
        actual = _sha256_file(path)
        if actual != expected:
            errors.append(f"sha256 mismatch for {path_key}: {path}")
    return errors


def verify_current_provenance(payload, file_path: Path) -> dict[str, object]:
    required_scalar_or_array = [
        "input_provenance_json",
        "deglitch_run_summary_sha256",
    ]
    missing = [key for key in required_scalar_or_array if key not in payload]
    errors: list[str] = []
    if missing:
        errors.extend(f"missing {key}" for key in missing)
    for path_key, hash_key in [
        ("input_trace_paths", "input_trace_sha256"),
        ("input_valid_sample_mask_paths", "input_valid_sample_mask_sha256"),
        ("input_time_paths", "input_time_sha256"),
        ("normalization_metadata_paths", "normalization_metadata_sha256"),
        ("alignment_metadata_paths", "alignment_metadata_sha256"),
        ("rotation_metadata_paths", "rotation_metadata_sha256"),
        ("locked_pick_manifest_paths", "locked_pick_manifest_sha256"),
    ]:
        errors.extend(_verify_path_hash_array(payload, path_key, hash_key, file_path))
    deglitch_hashes = [value for value in _payload_string_array(payload, "deglitch_run_summary_sha256") if value]
    if not deglitch_hashes:
        errors.append("missing nonempty deglitch_run_summary_sha256")
    if errors:
        raise _blocked_status(
            "blocked_missing_current_provenance",
            file_path,
            "; ".join(errors[:5]),
        )
    return {
        "status": "current",
        "checked_path_hash_pairs": 7,
    }


def _peak_result(time, slowness, power, slow_idx, time_idx, support_count, status="ok", excluded_reason=""):
    return {
        "time": time,
        "slowness": slowness,
        "power": power,
        "slow_idx": int(slow_idx),
        "time_idx": int(time_idx),
        "support_count": int(support_count),
        "status": status,
        "excluded_reason": excluded_reason,
    }


def find_global_peak(data, t_axis, s_axis, t_min, t_max, support_counts, minimum_support):
    mask_t = (t_axis >= t_min) & (t_axis <= t_max)
    if not np.any(mask_t):
        return _peak_result(
            float("nan"),
            float("nan"),
            float("nan"),
            -1,
            -1,
            0,
            status="blocked_empty_window",
            excluded_reason="no_time_samples_in_window",
        )
    finite_supported = np.isfinite(data) & (support_counts >= int(minimum_support))
    candidate_mask = finite_supported[:, mask_t]
    sub = np.where(candidate_mask, data[:, mask_t], -np.inf)
    if sub.size == 0 or not np.any(np.isfinite(sub)):
        return _peak_result(
            float("nan"),
            float("nan"),
            float("nan"),
            -1,
            -1,
            0,
            status="blocked_low_support",
            excluded_reason="no_finite_cells_meeting_minimum_support",
        )
    idx = int(np.argmax(sub))
    i, j = divmod(idx, sub.shape[1])
    time_axis_window = t_axis[mask_t]
    global_time_indices = np.flatnonzero(mask_t)
    global_j = int(global_time_indices[j])
    return _peak_result(
        time_axis_window[j],
        s_axis[i],
        float(sub[i, j]),
        i,
        global_j,
        int(support_counts[i, global_j]),
    )


def neighborhood_mask(s_axis, t_axis, s_min, s_max, t_min, t_max):
    return (s_axis[:, None] >= s_min) & (s_axis[:, None] <= s_max) & (t_axis[None, :] >= t_min) & (t_axis[None, :] <= t_max)


def _is_local_maximum(data: np.ndarray, slow_idx: int, time_idx: int) -> bool:
    if slow_idx < 0 or time_idx < 0:
        return False
    if not np.isfinite(data[slow_idx, time_idx]):
        return False
    i0 = max(0, slow_idx - 1)
    i1 = min(data.shape[0], slow_idx + 2)
    j0 = max(0, time_idx - 1)
    j1 = min(data.shape[1], time_idx + 2)
    return bool(data[slow_idx, time_idx] >= np.nanmax(data[i0:i1, j0:j1]))


def _background_quantile(data: np.ndarray, power: float) -> float:
    finite = np.asarray(data, dtype=np.float64)
    finite = finite[np.isfinite(finite)]
    if finite.size == 0 or not np.isfinite(power):
        return float("nan")
    return float(np.mean(finite <= float(power)))


def _rank_within_mask(data: np.ndarray, mask: np.ndarray, power: float, support_counts: np.ndarray, minimum_support: int) -> int:
    support_mask = support_counts >= int(minimum_support)
    values = np.asarray(data[mask & support_mask], dtype=np.float64)
    values = values[np.isfinite(values)]
    if values.size == 0 or not np.isfinite(power):
        return 0
    return int(1 + np.sum(values > float(power)))


def _box_support_stats(
    data: np.ndarray,
    mask: np.ndarray,
    support_counts: np.ndarray,
    minimum_support: int,
    reference_power: float,
) -> dict[str, object]:
    total = int(np.count_nonzero(mask))
    support_mask = mask & (support_counts >= int(minimum_support)) & np.isfinite(data)
    valid = int(np.count_nonzero(support_mask))
    if total <= 0:
        supported_fraction = 0.0
    else:
        supported_fraction = float(valid / total)
    if valid <= 0 or not np.isfinite(reference_power) or reference_power <= 0.0:
        occupancy = 0.0
    else:
        occupancy = float(np.count_nonzero(support_mask & (data >= 0.85 * float(reference_power))) / valid)
    return {
        "box_total_cell_count": total,
        "box_valid_cell_count": valid,
        "box_supported_cell_fraction": supported_fraction,
        "box_occupancy_in_band": occupancy,
    }


def _find_peak_in_mask(data: np.ndarray, t_axis: np.ndarray, s_axis: np.ndarray, mask: np.ndarray, support_counts: np.ndarray, minimum_support: int):
    candidate_mask = mask & np.isfinite(data) & (support_counts >= int(minimum_support))
    if not np.any(candidate_mask):
        return _peak_result(
            float("nan"),
            float("nan"),
            float("nan"),
            -1,
            -1,
            0,
            status="blocked_low_support",
            excluded_reason="no_finite_cells_meeting_minimum_support",
        )
    cand = np.where(candidate_mask)
    idx = int(np.argmax(data[cand]))
    i = int(cand[0][idx])
    j = int(cand[1][idx])
    return _peak_result(t_axis[j], s_axis[i], float(data[i, j]), i, j, int(support_counts[i, j]))


def detect(file_path: Path, *, require_current_provenance: bool = False):
    payload = np.load(file_path, allow_pickle=False)
    if "support_counts" not in payload or "minimum_support" not in payload:
        raise _blocked_status("blocked_missing_support_map", file_path, "vespagram payload lacks support_counts/minimum_support")
    if _payload_scalar(payload, "artifact_schema_version", "") != VESPAGRAM_ARTIFACT_SCHEMA_VERSION:
        raise _blocked_status("blocked_legacy_vespagram_schema", file_path, "vespagram artifact_schema_version mismatch")

    v = np.asarray(payload["vespagram"], dtype=np.float64)
    support_counts = np.asarray(payload["support_counts"], dtype=np.int32)
    s = np.asarray(payload["slowness_axis"], dtype=np.float64)
    t = np.asarray(payload["time_axis"], dtype=np.float64)
    minimum_support = int(np.asarray(payload["minimum_support"]).item())
    if support_counts.shape != v.shape:
        raise _blocked_status("blocked_support_shape_mismatch", file_path, "support_counts shape does not match vespagram")
    provenance = {"status": "not_required"}
    if require_current_provenance:
        provenance = verify_current_provenance(payload, file_path)

    mode = _payload_scalar(payload, "mode", "")
    input_type = _payload_scalar(payload, "input_type", "")
    norm_variant = _payload_scalar(payload, "norm_variant", "")
    polarization_operator = str(_payload_scalar(payload, "polarization_operator", ""))
    stack_method = _payload_scalar(payload, "stack_method", "")
    power_window_s = _payload_scalar(payload, "power_window_s", "")
    if isinstance(power_window_s, (np.floating, np.integer, float, int)):
        power_window_s = str(float(power_window_s))
    elif power_window_s is None:
        power_window_s = ""
    else:
        power_window_s = str(power_window_s)

    p = find_global_peak(v, t, s, *PKIKP_WINDOW, support_counts, minimum_support)
    q = find_global_peak(v, t, s, *PKKP_WINDOW, support_counts, minimum_support)

    pkikp_published_mask = neighborhood_mask(
        s,
        t,
        PKIKP_PUBLISHED_TARGET_BOX["s_min"],
        PKIKP_PUBLISHED_TARGET_BOX["s_max"],
        PKIKP_PUBLISHED_TARGET_BOX["t_min"],
        PKIKP_PUBLISHED_TARGET_BOX["t_max"],
    )
    pkikp_published = _find_peak_in_mask(v, t, s, pkikp_published_mask, support_counts, minimum_support)

    mask = np.zeros_like(v, dtype=bool)
    t_mask = np.abs(t - q["time"]) <= 30 if np.isfinite(q["time"]) else np.zeros_like(t, dtype=bool)
    s_mask = np.abs(s - q["slowness"]) <= 1.5 if np.isfinite(q["slowness"]) else np.zeros_like(s, dtype=bool)
    if q["status"] == "ok" and t_mask.any() and s_mask.any():
        mask[np.ix_(s_mask, t_mask)] = True
        v2 = v.copy()
        v2[mask] = np.nan
        r = find_global_peak(v2, t, s, *PKKP_WINDOW, support_counts, minimum_support)
    else:
        r = _peak_result(
            float("nan"),
            float("nan"),
            float("nan"),
            -1,
            -1,
            0,
            status="blocked_prerequisite_peak",
            excluded_reason="PKKP peak_1 unavailable",
        )

    paper_mask = neighborhood_mask(
        s,
        t,
        PKKP_PUBLISHED_TARGET_BOX["s_min"],
        PKKP_PUBLISHED_TARGET_BOX["s_max"],
        PKKP_PUBLISHED_TARGET_BOX["t_min"],
        PKKP_PUBLISHED_TARGET_BOX["t_max"],
    )
    paper = _find_peak_in_mask(v, t, s, paper_mask, support_counts, minimum_support)

    pkkp_broad_mask = neighborhood_mask(s, t, -10.0, 0.0, *PKKP_WINDOW)
    pkikp_broad_mask = neighborhood_mask(s, t, -10.0, 0.0, *PKIKP_WINDOW)

    def diag(result, rank_mask, *, box_mask=None, published_target_box=""):
        out = {
            "local_max_neighbor_check": _is_local_maximum(v, result["slow_idx"], result["time_idx"]),
            "box_peak_background_quantile": _background_quantile(v, result["power"]),
            "target_box_rank": _rank_within_mask(v, rank_mask, result["power"], support_counts, minimum_support),
            "support_count": result["support_count"],
            "minimum_support": minimum_support,
            "status": result["status"],
            "excluded_reason": result["excluded_reason"],
            "published_target_box": published_target_box,
        }
        if box_mask is not None:
            out.update(_box_support_stats(v, box_mask, support_counts, minimum_support, result["power"]))
        else:
            out.update(
                {
                    "box_total_cell_count": 0,
                    "box_valid_cell_count": 0,
                    "box_supported_cell_fraction": float("nan"),
                    "box_occupancy_in_band": float("nan"),
                }
            )
        return out

    diagnostics = {
        ("PKiKP", "global"): diag(p, pkikp_broad_mask),
        ("PKiKP", "published_target"): diag(
            pkikp_published,
            pkikp_broad_mask,
            box_mask=pkikp_published_mask,
            published_target_box="PKIKP_PUBLISHED",
        ),
        ("PKKP", "peak_1"): diag(q, pkkp_broad_mask),
        ("PKKP", "peak_2"): diag(r, pkkp_broad_mask),
        ("PKKP", "paper_target"): diag(
            paper,
            pkkp_broad_mask,
            box_mask=paper_mask,
            published_target_box="PKKP_PUBLISHED",
        ),
    }

    return (
        [
            ("PKiKP", "global", p["time"], p["slowness"], p["power"]),
            ("PKiKP", "published_target", pkikp_published["time"], pkikp_published["slowness"], pkikp_published["power"]),
            ("PKKP", "peak_1", q["time"], q["slowness"], q["power"]),
            ("PKKP", "peak_2", r["time"], r["slowness"], r["power"]),
            ("PKKP", "paper_target", paper["time"], paper["slowness"], paper["power"]),
        ],
        {
            "mode": mode,
            "input_type": input_type,
            "norm_variant": norm_variant,
            "polarization_operator": polarization_operator,
            "stack_method": stack_method,
            "power_window_s": power_window_s,
            "diagnostics": diagnostics,
            "current_provenance_status": provenance["status"],
            "distance_errors": np.asarray(payload["distance_errors"], dtype=np.float64) if "distance_errors" in payload else np.array([], dtype=np.float64),
        },
    )


def parse_combo_from_path(npz_path: Path, input_dir: Path):
    try:
        rel = npz_path.relative_to(input_dir)
    except ValueError:
        rel = npz_path

    parts = rel.parts
    mode = input_type = norm_variant = stack_method = power_window_s = ""
    if len(parts) >= 4:
        # expected: mode/input_type/variant/method_winXX.npz
        mode = parts[0]
        input_type = parts[1]
        norm_variant = parts[2]
        method_file = Path(parts[3]).stem
    else:
        mode = rel.parent.name if rel.parent.name else "unknown"
        input_type = ""
        method_file = rel.stem

    method_match = re.match(r"(?P<method>.+?)_win(?P<window>\d+)", method_file)
    if method_match:
        stack_method = method_match.group("method")
        power_window_s = str(float(method_match.group("window")))
    else:
        m = re.search(r"_win(?P<window>\d+)$", method_file)
        if m and m.group("window"):
            power_window_s = str(float(m.group("window")))
        elif m is None and "_" in method_file:
            parts2 = method_file.split("_")
            try:
                power_window_s = str(float(parts2[-1]))
                stack_method = "_".join(parts2[:-1])
            except ValueError:
                power_window_s = ""
                stack_method = method_file
        else:
            stack_method = method_file
    return mode, input_type, norm_variant, stack_method, power_window_s


def _normalization_lane(mode: str, variant: str) -> str:
    if mode == "paperfaith" and variant == "A":
        return "headline_targeted_window_eq1"
    if variant == "C":
        return "ablation_full_window"
    if variant == "B":
        return "targeted_pkkp_window"
    return "unspecified"


def _lane_value_is_empty(value) -> bool:
    return value is None or str(value).strip() == ""


def _normalized_lane_value(field: str, value):
    if field == "power_window_s":
        try:
            number = float(value)
        except (TypeError, ValueError):
            return str(value).strip()
        return number if np.isfinite(number) else str(value).strip()
    return str(value).strip()


def validate_payload_path_lane_identity(
    file_path: Path,
    payload_meta: dict,
    path_meta: dict,
    *,
    require_current_provenance: bool,
) -> None:
    for field in LANE_IDENTITY_FIELDS:
        payload_value = payload_meta.get(field, "")
        path_value = path_meta.get(field, "")
        if _lane_value_is_empty(payload_value):
            if require_current_provenance:
                raise _blocked_status(
                    "blocked_missing_current_provenance",
                    file_path,
                    (
                        f"vespagram payload lacks nonempty lane identity field {field}; "
                        f"payload value={payload_value!r}, path value={path_value!r}"
                    ),
                )
            continue
        if _normalized_lane_value(field, payload_value) != _normalized_lane_value(field, path_value):
            raise _blocked_status(
                "blocked_lane_identity_mismatch",
                file_path,
                (
                    f"lane identity mismatch for field {field}: "
                    f"payload value={payload_value!r}, path value={path_value!r}"
                ),
            )


def run_detect(input_dir: Path, output_csv: Path, *, require_current_provenance: bool = False):
    rows = []
    for npz in sorted(Path(input_dir).glob("**/*.npz")):
        stem = npz.stem
        if stem.endswith("_sub"):
            continue

        fallback_meta = {
            "mode": "",
            "input_type": "",
            "norm_variant": "",
            "polarization_operator": "",
            "stack_method": "",
            "power_window_s": "",
        }
        path_meta = dict(zip(
            ["mode", "input_type", "norm_variant", "stack_method", "power_window_s"],
            parse_combo_from_path(npz, input_dir),
        ))
        vals, payload_meta = detect(npz, require_current_provenance=require_current_provenance)
        validate_payload_path_lane_identity(
            npz,
            payload_meta,
            path_meta,
            require_current_provenance=require_current_provenance,
        )
        meta = {**fallback_meta, **payload_meta, **path_meta}
        diagnostics = payload_meta.get("diagnostics", {})
        distance_errors = np.asarray(payload_meta.get("distance_errors", []), dtype=np.float64)
        distance_errors = distance_errors[np.isfinite(distance_errors)]
        median_distance_error = float(np.median(distance_errors)) if distance_errors.size else float("nan")
        max_distance_error = float(np.max(distance_errors)) if distance_errors.size else float("nan")

        for phase, label, t_s, s_deg, power in vals:
            paper_time = PAPER_PKIKP[0] if phase == "PKiKP" else (PAPER_PKKP2[0] if label != "peak_1" else PAPER_PKKP1[0])
            paper_slow = PAPER_PKIKP[1] if phase == "PKiKP" else (PAPER_PKKP2[1] if label != "peak_1" else PAPER_PKKP1[1])
            dt = float(t_s) - float(paper_time)
            ds = float(s_deg) - float(paper_slow)
            tolerance_t = 2.0 if phase == "PKiKP" else (5.0 if label == "paper_target" else 30.0)
            tolerance_s = 0.6 if phase == "PKiKP" else (0.4 if label == "paper_target" else 1.5)
            grid_miss = float("nan")
            if np.isfinite(dt) and np.isfinite(ds) and tolerance_t > 0 and tolerance_s > 0:
                grid_miss = float(np.sqrt((dt / tolerance_t) ** 2 + (ds / tolerance_s) ** 2))
            moveout_uncertainty = (
                float(abs(paper_slow) * median_distance_error)
                if np.isfinite(median_distance_error)
                else float("nan")
            )
            folded_tolerance = (
                float(tolerance_t + moveout_uncertainty)
                if np.isfinite(moveout_uncertainty)
                else float("nan")
            )
            diag = diagnostics.get((phase, label), {})
            status = str(diag.get("status", "ok"))
            rows.append(
                {
                    "mode": meta["mode"],
                    "input_type": meta["input_type"],
                    "norm_variant": meta["norm_variant"],
                    "polarization_operator": meta.get("polarization_operator", ""),
                    "stack_method": meta["stack_method"],
                    "power_window_s": meta["power_window_s"],
                    "phase": phase,
                    "peak_label": label,
                    "time_s": t_s,
                    "slowness_sdeg": s_deg,
                    "power": power,
                    "support_count": diag.get("support_count", 0),
                    "minimum_support": diag.get("minimum_support", ""),
                    "status": status,
                    "excluded_reason": diag.get("excluded_reason", ""),
                    "paper_time_s": paper_time,
                    "paper_slowness_sdeg": paper_slow,
                    "dt_vs_paper_s": dt,
                    "ds_vs_paper_sdeg": ds,
                    "within_published_tolerance": bool(status == "ok" and abs(dt) <= tolerance_t and abs(ds) <= tolerance_s),
                    "grid_coordinate_miss_norm": grid_miss,
                    "median_distance_error_deg": median_distance_error,
                    "max_distance_error_deg": max_distance_error,
                    "distance_uncertainty_moveout_s": moveout_uncertainty,
                    "uncertainty_folded_time_tolerance_s": folded_tolerance,
                    "within_uncertainty_folded_tolerance": bool(
                        status == "ok"
                        and np.isfinite(folded_tolerance)
                        and abs(dt) <= folded_tolerance
                        and abs(ds) <= tolerance_s
                    ),
                    "local_max_neighbor_check": bool(diag.get("local_max_neighbor_check", False)),
                    "box_peak_background_quantile": diag.get("box_peak_background_quantile", float("nan")),
                    "target_box_rank": diag.get("target_box_rank", 0),
                    "published_target_box": diag.get("published_target_box", ""),
                    "box_occupancy_in_band": diag.get("box_occupancy_in_band", float("nan")),
                    "box_supported_cell_fraction": diag.get("box_supported_cell_fraction", float("nan")),
                    "box_valid_cell_count": diag.get("box_valid_cell_count", 0),
                    "box_total_cell_count": diag.get("box_total_cell_count", 0),
                    "normalization_lane": _normalization_lane(meta["mode"], meta["norm_variant"]),
                    "current_provenance_status": meta.get("current_provenance_status", "not_required"),
                }
            )

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "mode",
                "input_type",
                "norm_variant",
                "polarization_operator",
                "stack_method",
                "power_window_s",
                "phase",
                "peak_label",
                "time_s",
                "slowness_sdeg",
                "power",
                "support_count",
                "minimum_support",
                "status",
                "excluded_reason",
                "paper_time_s",
                "paper_slowness_sdeg",
                "dt_vs_paper_s",
                "ds_vs_paper_sdeg",
                "within_published_tolerance",
                "grid_coordinate_miss_norm",
                "median_distance_error_deg",
                "max_distance_error_deg",
                "distance_uncertainty_moveout_s",
                "uncertainty_folded_time_tolerance_s",
                "within_uncertainty_folded_tolerance",
                "local_max_neighbor_check",
                "box_peak_background_quantile",
                "target_box_rank",
                "published_target_box",
                "box_occupancy_in_band",
                "box_supported_cell_fraction",
                "box_valid_cell_count",
                "box_total_cell_count",
                "normalization_lane",
                "current_provenance_status",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    logger.info("Wrote %s (%d rows)", output_csv, len(rows))


def parse_args():
    parser = argparse.ArgumentParser(description="Detect peaks in vespagram outputs")
    parser.add_argument("--input-dir", default=str(repo_path("results/vespagrams")))
    parser.add_argument("--out-csv", default=str(repo_path("results/tables/peak_comparison.csv")))
    parser.add_argument("--require-current-provenance", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_detect(Path(args.input_dir), Path(args.out_csv), require_current_provenance=args.require_current_provenance)
