from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
from obspy.taup import taup_create

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.shared import import_local_module, make_relative_path, sha256_file

core_profile = import_local_module("marsquake_shared_core_profile_model_gen", "scripts/core_profile.py")

MODEL_GENERATOR_FIDELITY_REVISION = core_profile.MODEL_GENERATOR_FIDELITY_REVISION
sample_cosh_profile = core_profile.sample_cosh_profile
cosh_profile_coefficients = core_profile.cosh_profile_coefficients
vp_from_depth_cosh_profile = core_profile.vp_from_depth_cosh_profile


def read_nd_model(path: Path):
    headers = []
    mantle, oc, ic = [], [], []
    section = "mantle"
    for ln in path.read_text().splitlines():
        raw = ln.strip()
        if not raw or raw.startswith("#"):
            continue
        low = raw.lower()
        if low in {"mantle", "outer-core", "inner-core"}:
            section = low
            headers.append(low)
            continue
        parts = re.split(r"\s+", raw)
        if len(parts) < 4:
            continue
        vals = [float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3])]
        if section == "mantle":
            mantle.append(vals)
        elif section == "outer-core":
            oc.append(vals)
        else:
            ic.append(vals)
    return np.array(mantle), np.array(oc), np.array(ic), headers


def model_generator_fidelity_report() -> dict:
    """Compare the shared kernel against the released interp_line and printed Eq. 6."""
    released = import_local_module(
        "marsquake_released_reference_model_gen",
        "scripts/10_paper3/released_reference.py",
    )
    p1 = [1589.5, 5.0, 0.0, 6.8]
    p2 = [2789.5, 5.8, 0.0, 6.8]
    released_rows = released.interp_line(p1, p2, n=15)
    depths, vps = sample_cosh_profile(1589.5, 2789.5, 5.0, 5.8, 15)
    K, b = cosh_profile_coefficients(1589.5, 2789.5, 5.0, 5.8)
    vp_eq6 = vp_from_depth_cosh_profile(released_rows[:, 0], K, b)
    metrics = {
        "max_abs_depth_diff_released_km": float(np.max(np.abs(depths - released_rows[:, 0]))),
        "max_abs_vp_diff_released_km_s": float(np.max(np.abs(vps - released_rows[:, 1]))),
        "max_abs_vp_diff_printed_eq6_km_s": float(np.max(np.abs(vp_eq6 - released_rows[:, 1]))),
    }
    passed = all(
        metrics[key] <= core_profile.FIDELITY_THRESHOLDS[key]
        for key in core_profile.FIDELITY_THRESHOLDS
    )
    payload = {
        "status": "pass" if passed else "fail",
        "passed": bool(passed),
        "revision": MODEL_GENERATOR_FIDELITY_REVISION,
        "n_outer_core_nodes": 15,
        "profile_kernel": "scripts/core_profile.py:sample_cosh_profile",
        "released_reference": "scripts/10_paper3/released_reference.py:interp_line",
        "source_reference": (
            "references/original_paper/Mars_IC-main/MCMC_inversion-main/"
            "MCMC_inversion_M_vesp.py:24-34"
        ),
        **metrics,
    }
    for rel in [
        "scripts/core_profile.py",
        "scripts/05_model_gen/generate_nd_model.py",
        "scripts/10_paper3/released_reference.py",
    ]:
        path = Path(__file__).resolve().parents[2] / rel
        payload[f"{rel.replace('/', '_')}_sha256"] = sha256_file(path)
    return payload


def write_model_generator_fidelity_report(path: Path) -> dict:
    payload = model_generator_fidelity_report()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def generate_nd_model(
    R_OC,
    Vp_CMB,
    Vp_OC_ICB,
    R_IC,
    dVp_ICB,
    base_model_path: Path,
    out_dir: Path | str = "data/models/generated/",
    tag: str | None = None,
    R_mars: float = 3389.5,
):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    params = {
        "R_OC": R_OC,
        "Vp_CMB": Vp_CMB,
        "Vp_OC_ICB": Vp_OC_ICB,
        "R_IC": R_IC,
        "dVp_ICB": dVp_ICB,
        "R_mars": R_mars,
    }
    for name, value in params.items():
        if not np.isfinite(float(value)):
            raise ValueError(f"{name} must be finite")
    if not (0.0 < float(R_IC) < float(R_OC) < float(R_mars)):
        raise ValueError("Radii must satisfy 0 < R_IC < R_OC < R_mars")
    if float(Vp_CMB) <= 0.0 or float(Vp_OC_ICB) <= 0.0:
        raise ValueError("Core Vp parameters must be positive")

    mantle, oc, ic, _ = read_nd_model(Path(base_model_path))
    if mantle.size == 0 or oc.size == 0 or ic.size == 0:
        raise ValueError("Malformed base .nd model")

    # estimate density at core boundaries from existing model, then build replacement sections
    def depth_interp(points, depth):
        d = points[:, 0]
        val = points[:, 1]
        return float(np.interp(depth, d, val))

    def rho_interp(points, depth):
        d = points[:, 0]
        val = points[:, 3]
        return float(np.interp(depth, d, val))

    depth_CMB = R_mars - R_OC
    depth_ICB = R_mars - R_IC

    rho_CMB = rho_interp(np.vstack([mantle, oc]), depth_CMB)
    rho_ICB = rho_interp(np.vstack([oc, ic]), depth_ICB)

    vp_CMB = float(Vp_CMB)
    vp_oc_bottom = float(Vp_OC_ICB)
    vp_OC_gradient = (vp_oc_bottom - vp_CMB) / (R_OC - R_IC)
    vp_ICB = vp_oc_bottom * (1.0 + dVp_ICB)
    vp_ic_bottom = vp_ICB + vp_OC_gradient * R_IC

    # Released interp_line receives (velocity, depth) pairs: sample Vp linearly
    # and compute depth = K*cosh(Vp)+b (identical to printed Eq. 6).
    oc_depths, oc_vp = sample_cosh_profile(depth_CMB, depth_ICB, vp_CMB, vp_oc_bottom, 15)
    oc_vs = np.zeros_like(oc_vp, dtype=float)
    oc_rho = np.linspace(rho_CMB, rho_ICB, len(oc_vp))

    ic_depths, ic_vp = sample_cosh_profile(depth_ICB, R_mars, vp_ICB, vp_ic_bottom, 5)
    ic_vs = ic_vp / np.sqrt(3)
    ic_rho = np.full_like(ic_vp, fill_value=6.5)
    if not (np.all(np.isfinite(oc_vp)) and np.all(np.isfinite(ic_vp)) and np.all(np.isfinite(ic_vs))):
        raise ValueError("Generated core velocities must be finite")
    if np.any(oc_vp <= 0.0) or np.any(ic_vp <= 0.0) or np.any(ic_vs < 0.0):
        raise ValueError("Generated core velocities must be non-negative, with positive Vp")
    if np.any(ic_vs > ic_vp):
        raise ValueError("Generated model would contain Vs > Vp")

    mantle_depths = mantle[:, 0]
    mantle_vp = mantle[:, 1]
    mantle_vs = mantle[:, 2]
    mantle_rho = mantle[:, 3]
    mantle_mask = mantle_depths < depth_CMB
    mantle_rows = mantle[mantle_mask]
    mantle_boundary_row = np.array([
        depth_CMB,
        np.interp(depth_CMB, mantle_depths, mantle_vp),
        np.interp(depth_CMB, mantle_depths, mantle_vs),
        np.interp(depth_CMB, mantle_depths, mantle_rho),
    ])
    if mantle_rows.size == 0:
        raise ValueError("Malformed base mantle profile: no depth points above CMB")
    if mantle_rows[-1, 0] < depth_CMB:
        mantle_rows = np.vstack([mantle_rows, mantle_boundary_row])
    all_rows = np.vstack([
        mantle_rows,
        np.column_stack([oc_depths, oc_vp, oc_vs, oc_rho]),
        np.column_stack([ic_depths, ic_vp, ic_vs, ic_rho]),
    ])
    if np.any(all_rows[:, 2] > all_rows[:, 1]):
        raise ValueError("Generated model would contain Vs > Vp")

    out_name = f"{R_OC:.2f}-{Vp_CMB:.2f}-{Vp_OC_ICB:.2f}-{R_IC:.2f}-{dVp_ICB:.3f}"
    if tag:
        out_name = f"{tag}_{out_name}"
    out_nd = out_dir / f"{out_name}.nd"

    with out_nd.open("w", encoding="utf-8") as f:
        # TauP expects the first non-comment line to be numeric depth data,
        # so we keep the file TauP-compatible by not emitting a leading
        # mantle-token line while retaining section markers for downstream users.
        for row in mantle_rows:
            f.write(f"{row[0]:.4f}\t  {row[1]:.4f}\t  {row[2]:.4f}\t  {row[3]:.4f}\n")
        f.write("outer-core\n")
        for z in range(len(oc_depths)):
            f.write(f"{oc_depths[z]:.4f}\t  {oc_vp[z]:.4f}\t  {oc_vs[z]:.4f}\t  {oc_rho[z]:.4f}\n")
        f.write("inner-core\n")
        for z in range(len(ic_depths)):
            f.write(f"{ic_depths[z]:.4f}\t  {ic_vp[z]:.4f}\t  {ic_vs[z]:.4f}\t  {ic_rho[z]:.4f}\n")

    taup_create.build_taup_model(filename=str(out_nd), output_folder=str(out_dir))
    npz = out_dir / f"{out_name}.npz"
    if not npz.exists():
        raise RuntimeError("TauP build failed")
    return out_nd, npz


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate TauP-compatible .nd model")
    parser.add_argument(
        "--write-fidelity-report",
        default=None,
        help="write the model-generator fidelity artifact and exit",
    )
    parser.add_argument("--R_OC", type=float)
    parser.add_argument("--Vp_CMB", type=float)
    parser.add_argument("--Vp_OC_ICB", type=float)
    parser.add_argument("--R_IC", type=float)
    parser.add_argument("--dVp_ICB", type=float)
    parser.add_argument("--base-model")
    parser.add_argument("--out-dir", default="data/models")
    parser.add_argument("--tag", default=None)
    args = parser.parse_args()

    if args.write_fidelity_report:
        payload = write_model_generator_fidelity_report(Path(args.write_fidelity_report))
        print(json.dumps({
            "status": payload["status"],
            "path": make_relative_path(Path(args.write_fidelity_report)),
            "revision": payload["revision"],
        }))
        raise SystemExit(0 if payload["passed"] else 1)

    required = ["R_OC", "Vp_CMB", "Vp_OC_ICB", "R_IC", "dVp_ICB", "base_model"]
    missing = [name for name in required if getattr(args, name) is None]
    if missing:
        parser.error(f"missing required generation arguments: {', '.join('--' + name.replace('_', '-') for name in missing)}")

    generate_nd_model(
        args.R_OC,
        args.Vp_CMB,
        args.Vp_OC_ICB,
        args.R_IC,
        args.dVp_ICB,
        Path(args.base_model),
        out_dir=args.out_dir,
        tag=args.tag,
    )
