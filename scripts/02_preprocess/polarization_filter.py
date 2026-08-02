from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np
from obspy import read, Stream
from scipy.signal import hilbert

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.shared import (
    PAPERSTYLE_ALGORITHM_REVISION,
    PAPERSTYLE_FILTERBANK_METHOD,
    PAPERSTYLE_POLARIZATION_METHOD,
    repo_path,
    sha256_file,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_CENTER_FREQUENCIES_HZ = np.array([(1.0 / 16.0) * (2.0 ** (idx / 2.0)) for idx in range(11)], dtype=np.float64)
OPERATOR_PRINCIPAL_AXIS = "principal_axis_projection"
OPERATOR_MONTALBETTI_KANASEWICH = "montalbetti_kanasewich_1970"


def _base_event_id(path_stem: str) -> str:
    if path_stem.endswith("_ZNE"):
        return path_stem[:-4]
    return path_stem


def _select_zne(st, in_path: Path):
    tr_z = st.select(channel="BHZ")
    tr_n = st.select(channel="BHN")
    tr_e = st.select(channel="BHE")

    if not (tr_z and tr_n and tr_e):
        raise ValueError(f"Expected BHZ/BHN/BHE in {in_path}")

    lengths = {len(tr_z[0].data), len(tr_n[0].data), len(tr_e[0].data)}
    sampling_rates = {
        float(tr_z[0].stats.sampling_rate),
        float(tr_n[0].stats.sampling_rate),
        float(tr_e[0].stats.sampling_rate),
    }
    if len(lengths) != 1:
        raise ValueError(f"ZNE components have mismatched lengths in {in_path}")
    if len(sampling_rates) != 1:
        raise ValueError(f"ZNE components have mismatched sampling rates in {in_path}")

    return tr_z[0], tr_n[0], tr_e[0]


def _window_starts(npts: int, win_samples: int, overlap: float) -> list[int]:
    if npts <= 0:
        return []
    win_samples = min(max(1, int(win_samples)), npts)
    hop = max(1, int(round(win_samples * (1.0 - overlap))))
    max_start = max(0, npts - win_samples)
    starts = list(range(0, max_start + 1, hop))
    if starts[-1] != max_start:
        starts.append(max_start)
    return starts


def _principal_axis_and_dop(samples: np.ndarray) -> tuple[np.ndarray, float, np.ndarray]:
    demeaned = samples - np.mean(samples, axis=1, keepdims=True)
    if demeaned.shape[1] < 2:
        return np.array([1.0, 0.0, 0.0], dtype=np.float64), 0.0, np.zeros(3, dtype=np.float64)

    cov = demeaned @ demeaned.T / float(demeaned.shape[1] - 1)
    eigvals, eigvecs = np.linalg.eigh(cov)
    order = np.argsort(np.real(eigvals))
    eigvals = np.real(eigvals[order])
    eigvecs = np.real(eigvecs[:, order])
    eigvals = np.clip(eigvals, 0.0, None)

    total = float(np.sum(eigvals))
    if total <= 0.0 or eigvals[-1] <= 0.0:
        return np.array([1.0, 0.0, 0.0], dtype=np.float64), 0.0, eigvals

    axis = eigvecs[:, -1]
    norm = float(np.linalg.norm(axis))
    if norm <= 0.0:
        axis = np.array([1.0, 0.0, 0.0], dtype=np.float64)
    else:
        axis = axis / norm
    if axis[0] < 0.0:
        axis = -axis

    dop = float((eigvals[-1] - eigvals[-2]) / total)
    return axis.astype(np.float64), float(np.clip(dop, 0.0, 1.0)), eigvals.astype(np.float64)


def principal_axis_dop_filter_arrays(
    z: np.ndarray,
    n: np.ndarray,
    e: np.ndarray,
    sr: float,
    *,
    win_length: float = 5.0,
    overlap: float = 0.9,
    dop_power: float = 1.0,
) -> np.ndarray:
    """Return the vertical component after principal-axis/DOP polarization filtering."""
    z = np.asarray(z, dtype=np.float64)
    n = np.asarray(n, dtype=np.float64)
    e = np.asarray(e, dtype=np.float64)
    if not (z.shape == n.shape == e.shape):
        raise ValueError("Z, N, and E arrays must have identical shape")
    if z.size < 2:
        return np.asarray(z, dtype=np.float64)

    win_samples = max(2, int(round(float(win_length) * float(sr))))
    starts = _window_starts(z.size, win_samples, overlap)
    win_samples = min(win_samples, z.size)

    acc = np.zeros_like(z, dtype=np.float64)
    counts = np.zeros_like(z, dtype=np.float64)

    for start in starts:
        end = min(start + win_samples, z.size)
        samples = np.vstack([z[start:end], n[start:end], e[start:end]])
        axis, dop, _ = _principal_axis_and_dop(samples)
        demeaned = samples - np.mean(samples, axis=1, keepdims=True)
        projected_scalar = axis @ demeaned
        projected_vertical = axis[0] * projected_scalar
        gain = float(dop**dop_power)
        acc[start:end] += projected_vertical * gain
        counts[start:end] += 1.0

    out = np.zeros_like(z, dtype=np.float64)
    covered = counts > 0.0
    out[covered] = acc[covered] / counts[covered]
    return out


def montalbetti_kanasewich_filter_components(
    z: np.ndarray,
    n: np.ndarray,
    e: np.ndarray,
    sr: float,
    *,
    win_length: float = 5.0,
    overlap: float = 0.9,
    rectilinearity_power: float = 1.0,
    direction_power: float = 2.0,
    rectilinearity_contrast: float = 1.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Apply the Montalbetti-Kanasewich component weighting to original components."""
    z = np.asarray(z, dtype=np.float64)
    n = np.asarray(n, dtype=np.float64)
    e = np.asarray(e, dtype=np.float64)
    if not (z.shape == n.shape == e.shape):
        raise ValueError("Z, N, and E arrays must have identical shape")
    if z.size < 2:
        return z.copy(), n.copy(), e.copy()

    win_samples = max(2, int(round(float(win_length) * float(sr))))
    starts = _window_starts(z.size, win_samples, overlap)
    win_samples = min(win_samples, z.size)
    weights = np.zeros((3, z.size), dtype=np.float64)
    counts = np.zeros(z.size, dtype=np.float64)

    for start in starts:
        end = min(start + win_samples, z.size)
        samples = np.vstack([z[start:end], n[start:end], e[start:end]])
        axis, _, eigvals = _principal_axis_and_dop(samples)
        lambda1 = float(eigvals[-1]) if eigvals.size else 0.0
        lambda2 = float(eigvals[-2]) if eigvals.size >= 2 else 0.0
        if lambda1 <= 0.0:
            rl = 0.0
        else:
            rl = 1.0 - (max(lambda2, 0.0) / lambda1) ** float(rectilinearity_contrast)
        rl = float(np.clip(rl, 0.0, 1.0))
        direction = np.abs(axis)
        gain = (rl**float(rectilinearity_power)) * (direction**float(direction_power))
        weights[:, start:end] += gain[:, None]
        counts[start:end] += 1.0

    smoothed = np.zeros_like(weights)
    covered = counts > 0.0
    smoothed[:, covered] = weights[:, covered] / counts[covered]
    return z * smoothed[0], n * smoothed[1], e * smoothed[2]


def montalbetti_kanasewich_filter_arrays(
    z: np.ndarray,
    n: np.ndarray,
    e: np.ndarray,
    sr: float,
    *,
    win_length: float = 5.0,
    overlap: float = 0.9,
    rectilinearity_power: float = 1.0,
    direction_power: float = 2.0,
    rectilinearity_contrast: float = 1.0,
) -> np.ndarray:
    z_f, _, _ = montalbetti_kanasewich_filter_components(
        z,
        n,
        e,
        sr,
        win_length=win_length,
        overlap=overlap,
        rectilinearity_power=rectilinearity_power,
        direction_power=direction_power,
        rectilinearity_contrast=rectilinearity_contrast,
    )
    return z_f


def _metadata(
    *,
    in_path: Path,
    out_path: Path,
    source_zne_sha256: str,
    output_trace_sha256: str,
    win_length: float,
    overlap: float,
    dop_power: float,
    sampling_rate_hz: float,
    npts: int,
    operator: str,
    mk_rectilinearity_power: float,
    mk_direction_power: float,
    mk_rectilinearity_contrast: float,
) -> dict[str, object]:
    if operator == OPERATOR_MONTALBETTI_KANASEWICH:
        method_section = (
            "Montalbetti & Kanasewich (1970), Enhancement of Teleseismic Body Phases with a Polarization Filter, "
            "Geophys. J. R. astr. Soc. 21(2):119-129; "
            "equation-number attribution UNCONFIRMED-from-paywalled-source"
        )
        notes = (
            "Compatibility file names still use paperfaith/Z_polfilt, but the operator is the public "
            "Montalbetti-Kanasewich component-weighting branch. Filter-bank and FDPA files are diagnostics/gates, not stack inputs."
        )
    else:
        method_section = "Principal-axis/DOP projection ablation, not the literal Montalbetti-Kanasewich component weighting"
        notes = (
            "Compatibility file names still use paperfaith/Z_polfilt, but the operator is the labeled "
            "principal-axis/DOP projection ablation. Filter-bank and FDPA files are diagnostics/gates, not stack inputs."
        )
    return {
        "method": PAPERSTYLE_POLARIZATION_METHOD,
        "algorithm_revision": PAPERSTYLE_ALGORITHM_REVISION,
        "operator": operator,
        "legacy_artifact_mode": "paperfaith",
        "is_rectilinearity_z_weight_proxy": False,
        "method_section": method_section,
        "input": str(in_path),
        "output": str(out_path),
        "source_zne_sha256": source_zne_sha256,
        "output_trace_sha256": output_trace_sha256,
        "bandpass_hz": [0.2, 0.8],
        "win_length_s": float(win_length),
        "overlap": float(overlap),
        "dop_power": float(dop_power),
        "mk_rectilinearity_power": float(mk_rectilinearity_power),
        "mk_direction_power": float(mk_direction_power),
        "mk_rectilinearity_contrast": float(mk_rectilinearity_contrast),
        "sampling_rate_hz": float(sampling_rate_hz),
        "npts": int(npts),
        "notes": notes,
    }


def polarization_filter_file(
    in_path: Path,
    out_path: Path,
    win_length: float = 5.0,
    overlap: float = 0.9,
    dop_power: float = 1.0,
    operator: str = OPERATOR_MONTALBETTI_KANASEWICH,
    mk_rectilinearity_power: float = 1.0,
    mk_direction_power: float = 2.0,
    mk_rectilinearity_contrast: float = 1.0,
) -> None:
    source_zne_sha256 = sha256_file(in_path)
    st = read(str(in_path))
    st.filter("bandpass", freqmin=0.2, freqmax=0.8, corners=4, zerophase=True)
    tr_z, tr_n, tr_e = _select_zne(st, in_path)

    z = np.asarray(tr_z.data, dtype=np.float64)
    n = np.asarray(tr_n.data, dtype=np.float64)
    e = np.asarray(tr_e.data, dtype=np.float64)

    sr = float(tr_z.stats.sampling_rate)
    if operator == OPERATOR_PRINCIPAL_AXIS:
        out = principal_axis_dop_filter_arrays(
            z,
            n,
            e,
            sr,
            win_length=win_length,
            overlap=overlap,
            dop_power=dop_power,
        )
    elif operator == OPERATOR_MONTALBETTI_KANASEWICH:
        out = montalbetti_kanasewich_filter_arrays(
            z,
            n,
            e,
            sr,
            win_length=win_length,
            overlap=overlap,
            rectilinearity_power=mk_rectilinearity_power,
            direction_power=mk_direction_power,
            rectilinearity_contrast=mk_rectilinearity_contrast,
        )
    else:
        raise ValueError(f"Unknown polarization operator: {operator}")

    tr = tr_z.copy()
    tr.data = out.astype(np.float32)

    st_out = Stream([tr])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    st_out.write(str(out_path), format="MSEED")
    output_trace_sha256 = sha256_file(out_path)
    out_path.with_suffix(".polarization.json").write_text(
        json.dumps(
            _metadata(
                in_path=in_path,
                out_path=out_path,
                source_zne_sha256=source_zne_sha256,
                output_trace_sha256=output_trace_sha256,
                win_length=win_length,
                overlap=overlap,
                dop_power=dop_power,
                sampling_rate_hz=sr,
                npts=len(out),
                operator=operator,
                mk_rectilinearity_power=mk_rectilinearity_power,
                mk_direction_power=mk_direction_power,
                mk_rectilinearity_contrast=mk_rectilinearity_contrast,
            ),
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    logger.info("Wrote %s", out_path)


def _smooth_envelope(data: np.ndarray, sr: float, envelope_window_s: float) -> np.ndarray:
    env = np.abs(hilbert(np.asarray(data, dtype=np.float64)))
    smooth_n = max(1, int(round(float(envelope_window_s) * float(sr))))
    kernel = np.ones(smooth_n, dtype=np.float64) / float(smooth_n)
    return np.convolve(env, kernel, mode="same")


def _half_octave_edges(center_hz: float) -> tuple[float, float]:
    factor = 2.0**0.25
    return float(center_hz / factor), float(center_hz * factor)


def build_filter_bank_products(
    in_path: Path,
    *,
    center_frequencies_hz: np.ndarray | None = None,
    bandwidth_octaves: float = 0.5,
    polarization_window_s: float = 5.0,
    polarization_overlap: float = 0.9,
    dop_power: float = 1.0,
    envelope_window_s: float = 5.0,
    operator: str = OPERATOR_MONTALBETTI_KANASEWICH,
) -> dict[str, np.ndarray]:
    if bandwidth_octaves != 0.5:
        raise ValueError("Only half-octave filter-bank products are supported for the Paper0 contract")
    centers = np.asarray(
        DEFAULT_CENTER_FREQUENCIES_HZ if center_frequencies_hz is None else center_frequencies_hz,
        dtype=np.float64,
    )
    st0 = read(str(in_path))
    tr_z, _, _ = _select_zne(st0, in_path)
    sr = float(tr_z.stats.sampling_rate)
    npts = int(tr_z.stats.npts)
    nyquist = 0.5 * sr

    filtered = []
    envelopes = []
    edge_rows = []
    for center in centers:
        fmin, fmax = _half_octave_edges(float(center))
        if fmin <= 0.0 or fmax >= nyquist:
            raise ValueError(f"Filter-bank edge out of range for {center} Hz at sr={sr}")
        st = st0.copy()
        st.filter("bandpass", freqmin=fmin, freqmax=fmax, corners=4, zerophase=True)
        z_tr, n_tr, e_tr = _select_zne(st, in_path)
        if operator == OPERATOR_PRINCIPAL_AXIS:
            z = principal_axis_dop_filter_arrays(
                np.asarray(z_tr.data, dtype=np.float64),
                np.asarray(n_tr.data, dtype=np.float64),
                np.asarray(e_tr.data, dtype=np.float64),
                sr,
                win_length=polarization_window_s,
                overlap=polarization_overlap,
                dop_power=dop_power,
            )
        elif operator == OPERATOR_MONTALBETTI_KANASEWICH:
            z = montalbetti_kanasewich_filter_arrays(
                np.asarray(z_tr.data, dtype=np.float64),
                np.asarray(n_tr.data, dtype=np.float64),
                np.asarray(e_tr.data, dtype=np.float64),
                sr,
                win_length=polarization_window_s,
                overlap=polarization_overlap,
            )
        else:
            raise ValueError(f"Unknown polarization operator: {operator}")
        filtered.append(z.astype(np.float32))
        envelopes.append(_smooth_envelope(z, sr, envelope_window_s).astype(np.float32))
        edge_rows.append((fmin, fmax))

    return {
        "method": np.array(PAPERSTYLE_FILTERBANK_METHOD),
        "algorithm_revision": np.array(PAPERSTYLE_ALGORITHM_REVISION),
        "center_frequencies_hz": centers.astype(np.float32),
        "band_edges_hz": np.asarray(edge_rows, dtype=np.float32),
        "bandwidth_octaves": np.array(float(bandwidth_octaves), dtype=np.float32),
        "polarization_window_s": np.array(float(polarization_window_s), dtype=np.float32),
        "polarization_overlap": np.array(float(polarization_overlap), dtype=np.float32),
        "dop_power": np.array(float(dop_power), dtype=np.float32),
        "operator": np.asarray(operator),
        "source_zne_sha256": np.array(sha256_file(in_path)),
        "envelope_window_s": np.array(float(envelope_window_s), dtype=np.float32),
        "filtered_waveforms": np.vstack(filtered).astype(np.float32),
        "envelopes": np.vstack(envelopes).astype(np.float32),
        "time_axis_s": (np.arange(npts, dtype=np.float64) / sr).astype(np.float32),
        "sampling_rate_hz": np.array(sr, dtype=np.float32),
        "npts": np.array(npts, dtype=np.int64),
    }


def write_filter_bank_file(
    in_path: Path,
    out_path: Path,
    *,
    center_frequencies_hz: np.ndarray | None = None,
    bandwidth_octaves: float = 0.5,
    polarization_window_s: float = 5.0,
    polarization_overlap: float = 0.9,
    dop_power: float = 1.0,
    envelope_window_s: float = 5.0,
    operator: str = OPERATOR_MONTALBETTI_KANASEWICH,
) -> None:
    payload = build_filter_bank_products(
        in_path,
        center_frequencies_hz=center_frequencies_hz,
        bandwidth_octaves=bandwidth_octaves,
        polarization_window_s=polarization_window_s,
        polarization_overlap=polarization_overlap,
        dop_power=dop_power,
        envelope_window_s=envelope_window_s,
        operator=operator,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out_path, **payload)
    logger.info("Wrote %s", out_path)


def parse_args():
    parser = argparse.ArgumentParser(description="Apply public time-domain polarization filtering to 3-component ZNE data")
    parser.add_argument("--in-dir", default=str(repo_path("data/processed")))
    parser.add_argument("--out-dir", default=str(repo_path("data/processed")))
    parser.add_argument("--win-length", type=float, default=5.0)
    parser.add_argument("--overlap", type=float, default=0.9)
    parser.add_argument("--dop-power", type=float, default=1.0)
    parser.add_argument(
        "--operator",
        choices=(OPERATOR_PRINCIPAL_AXIS, OPERATOR_MONTALBETTI_KANASEWICH),
        default=OPERATOR_MONTALBETTI_KANASEWICH,
    )
    parser.add_argument("--filter-bank", action=argparse.BooleanOptionalAction, default=True)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    for p in sorted(Path(args.in_dir).glob("*_ZNE.mseed")):
        out = Path(args.out_dir) / f"{_base_event_id(p.stem)}_Z_polfilt.mseed"
        polarization_filter_file(
            p,
            out,
            win_length=args.win_length,
            overlap=args.overlap,
            dop_power=args.dop_power,
            operator=args.operator,
        )
        if args.filter_bank:
            write_filter_bank_file(
                p,
                Path(args.out_dir) / f"{_base_event_id(p.stem)}_mk_filterbank.npz",
                polarization_window_s=args.win_length,
                polarization_overlap=args.overlap,
                dop_power=args.dop_power,
                operator=args.operator,
            )
