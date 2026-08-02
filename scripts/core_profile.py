"""Shared Mars core velocity-profile kernel.

Authoritative profile family for the Bi et al. public-code parameterization:

    depth = K * cosh(Vp) + b

The released ``interp_line`` calls ``draw_curve`` with (velocity, depth) pairs,
so cosh receives velocity values near 5-8 km/s, never kilometre-scale depths.
This module is the only production implementation of that family; paper-specific
modules may wrap these functions but must not reimplement the formula.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np

MODEL_GENERATOR_FIDELITY_REVISION = "released-eq6-vp-cosh-20260704"
MODEL_GENERATOR_FIDELITY_REL_PATH = "data/models/model_generator_fidelity.json"

FIDELITY_THRESHOLDS = {
    "max_abs_depth_diff_released_km": 1e-9,
    "max_abs_vp_diff_released_km_s": 1e-12,
    "max_abs_vp_diff_printed_eq6_km_s": 1e-12,
}
FIDELITY_SOURCE_HASH_KEYS = {
    "scripts_core_profile.py_sha256": "scripts/core_profile.py",
    "scripts_05_model_gen_generate_nd_model.py_sha256": "scripts/05_model_gen/generate_nd_model.py",
    "scripts_10_paper3_released_reference.py_sha256": "scripts/10_paper3/released_reference.py",
}


def cosh_profile_coefficients(depth1: float, depth2: float, vp1: float, vp2: float) -> Tuple[float, float]:
    """Return K and b for depth = K*cosh(Vp) + b through two endpoints."""
    depth1 = float(depth1)
    depth2 = float(depth2)
    vp1 = float(vp1)
    vp2 = float(vp2)
    values = np.array([depth1, depth2, vp1, vp2], dtype=float)
    if not np.all(np.isfinite(values)):
        raise ValueError("profile endpoints must be finite")
    denom = np.cosh(vp2) - np.cosh(vp1)
    if np.isclose(denom, 0.0):
        raise ValueError("cosh profile coefficients undefined for coincident endpoint velocities")
    K = (depth2 - depth1) / denom
    b = depth1 - K * np.cosh(vp1)
    return float(K), float(b)


def depth_from_vp_cosh_profile(vp: float | np.ndarray, K: float, b: float):
    """Evaluate depth = K*cosh(Vp) + b."""
    return np.asarray(K * np.cosh(vp) + b, dtype=float)


def vp_from_depth_cosh_profile(depth: float | np.ndarray, K: float, b: float):
    """Evaluate the printed inverse, Vp = arccosh((depth - b) / K)."""
    arg = (np.asarray(depth, dtype=float) - float(b)) / float(K)
    if np.any(arg < 1.0):
        raise ValueError("depth outside the cosh profile branch")
    return np.asarray(np.arccosh(arg), dtype=float)


def sample_cosh_profile(
    depth1: float,
    depth2: float,
    vp1: float,
    vp2: float,
    n: int,
) -> Tuple[np.ndarray, np.ndarray]:
    """Sample the corrected family linearly in Vp, returning depths and Vp."""
    if int(n) <= 0:
        raise ValueError("n must be positive")
    depth1 = float(depth1)
    depth2 = float(depth2)
    vp1 = float(vp1)
    vp2 = float(vp2)
    if vp1 == vp2:
        return np.linspace(depth1, depth2, int(n)), np.full(int(n), vp1, dtype=float)
    K, b = cosh_profile_coefficients(depth1, depth2, vp1, vp2)
    vps = np.linspace(vp1, vp2, int(n))
    depths = depth_from_vp_cosh_profile(vps, K, b)
    return depths, vps


def default_model_generator_fidelity_path(repo_root: Path) -> Path:
    return Path(repo_root) / MODEL_GENERATOR_FIDELITY_REL_PATH


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _current_source_hashes(repo_root: Path) -> Dict[str, str]:
    return {
        key: _sha256_file(Path(repo_root) / rel)
        for key, rel in FIDELITY_SOURCE_HASH_KEYS.items()
    }


def validate_model_generator_fidelity_payload(payload: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
    """Validate the fail-closed artifact consumed by model-based downstream runs."""
    detail: Dict[str, Any] = {"revision": payload.get("revision")}
    if payload.get("revision") != MODEL_GENERATOR_FIDELITY_REVISION:
        detail["expected_revision"] = MODEL_GENERATOR_FIDELITY_REVISION
        return False, "blocked_model_generator_fidelity_failed", detail
    if payload.get("passed") is not True or payload.get("status") != "pass":
        detail["status"] = payload.get("status")
        detail["passed"] = payload.get("passed")
        return False, "blocked_model_generator_fidelity_failed", detail
    for key, limit in FIDELITY_THRESHOLDS.items():
        raw = payload.get(key)
        try:
            value = float(raw)
        except (TypeError, ValueError):
            detail[key] = raw
            return False, "blocked_model_generator_fidelity_failed", detail
        detail[key] = value
        if not np.isfinite(value) or value > limit:
            detail[f"{key}_limit"] = limit
            return False, "blocked_model_generator_fidelity_failed", detail
    return True, "ok", detail


def check_model_generator_fidelity_artifact(path: Path, repo_root: Path | None = None) -> Tuple[bool, str, Dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        return False, "blocked_missing_model_generator_fidelity", {"path": str(path)}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return False, "blocked_model_generator_fidelity_failed", {"path": str(path), "error": str(exc)}
    ok, status, detail = validate_model_generator_fidelity_payload(payload)
    if ok:
        root = Path(__file__).resolve().parents[1] if repo_root is None else Path(repo_root)
        for key, expected in _current_source_hashes(root).items():
            actual = payload.get(key)
            if actual != expected:
                detail.update({
                    "hash_key": key,
                    "expected_sha256": expected,
                    "actual_sha256": actual,
                })
                ok = False
                status = "blocked_model_generator_fidelity_failed"
                break
    detail["path"] = str(path)
    return ok, status, detail
