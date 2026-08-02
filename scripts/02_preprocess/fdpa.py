from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import numpy as np
from obspy import read

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.shared import (
    PAPERSTYLE_ALGORITHM_REVISION,
    PAPERSTYLE_FDPA_METHOD,
    PAPERSTYLE_FDPA_TRANSFORM_FAMILY,
    repo_path,
    sha256_file,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_FDPA_FREQUENCIES_HZ = np.geomspace(0.2, 0.8, 13).astype(np.float64)


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


def compact_fdpa_frequency_shift_transform(data: np.ndarray, sr: float, frequencies_hz: np.ndarray) -> np.ndarray:
    """Compute the compact Gaussian-windowed frequency shift used by the public FDPA diagnostic."""
    x = np.asarray(data, dtype=np.float64)
    freqs = np.asarray(frequencies_hz, dtype=np.float64)
    if x.size == 0:
        return np.zeros((freqs.size, 0), dtype=np.complex128)
    spectrum = np.fft.fft(x)
    fft_freqs = np.fft.fftfreq(x.size, d=1.0 / float(sr))
    df = float(sr) / float(x.size)
    out = np.zeros((freqs.size, x.size), dtype=np.complex128)
    for idx, freq in enumerate(freqs):
        if freq <= 0.0:
            raise ValueError("FDPA frequencies must be positive")
        bin_shift = int(round(float(freq) / df))
        gaussian = np.exp(-2.0 * np.pi**2 * (fft_freqs / float(freq)) ** 2)
        out[idx] = np.fft.ifft(np.roll(spectrum, -bin_shift) * gaussian)
    return out


def _window_starts(npts: int, win_samples: int, overlap: float) -> list[int]:
    if npts <= 0:
        return []
    win_samples = min(max(2, int(win_samples)), npts)
    hop = max(1, int(round(win_samples * (1.0 - overlap))))
    max_start = max(0, npts - win_samples)
    starts = list(range(0, max_start + 1, hop))
    if starts[-1] != max_start:
        starts.append(max_start)
    return starts


def _fdpa_window_metrics(samples: np.ndarray) -> tuple[float, float, float, float, float, float]:
    cov = samples @ samples.conj().T / max(1, samples.shape[1])
    eigvals, eigvecs = np.linalg.eigh(cov)
    order = np.argsort(np.real(eigvals))
    eigvals = np.clip(np.real(eigvals[order]), 0.0, None)
    eigvecs = eigvecs[:, order]
    total = float(np.sum(eigvals))
    if total <= 0.0 or eigvals[-1] <= 0.0:
        return 0.0, np.nan, np.nan, 0.0, 0.0, 0.0

    dop = float((eigvals[-1] - eigvals[-2]) / total)
    dop = float(np.clip(dop, 0.0, 1.0))

    axis = eigvecs[:, -1]
    if abs(axis[0]) > 0.0:
        axis = axis * np.exp(-1j * np.angle(axis[0]))
    axis_real = np.real(axis)
    axis_abs = np.abs(axis)
    axis_norm = float(np.linalg.norm(axis_abs))
    if axis_norm <= 0.0:
        return dop, np.nan, np.nan, 0.0, 0.0, 0.0
    axis_abs = axis_abs / axis_norm

    vertical = float(axis_abs[0] ** 2)
    horizontal = float(axis_abs[1] ** 2 + axis_abs[2] ** 2)
    vrm = dop * vertical
    hrm = dop * horizontal
    azimuth = (np.degrees(np.arctan2(axis_real[2], axis_real[1])) + 360.0) % 360.0
    inclination = np.degrees(np.arctan2(abs(axis_real[0]), np.hypot(axis_real[1], axis_real[2])))
    return dop, float(azimuth), float(inclination), float(vrm), float(hrm), float(vrm - hrm)


def _circular_mean_degrees(values: np.ndarray) -> float:
    finite = np.asarray(values, dtype=np.float64)
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        return float("nan")
    radians = np.deg2rad(finite)
    mean_sin = float(np.mean(np.sin(radians)))
    mean_cos = float(np.mean(np.cos(radians)))
    if mean_sin == 0.0 and mean_cos == 0.0:
        return float("nan")
    return float((np.degrees(np.arctan2(mean_sin, mean_cos)) + 360.0) % 360.0)


def frequency_dependent_polarization_analysis(
    z: np.ndarray,
    n: np.ndarray,
    e: np.ndarray,
    sr: float,
    *,
    frequencies_hz: np.ndarray | None = None,
    window_overlap: float = 0.9,
    window_cycles: float = 3.0,
    dop_threshold: float = 0.6,
) -> dict[str, np.ndarray]:
    z = np.asarray(z, dtype=np.float64)
    n = np.asarray(n, dtype=np.float64)
    e = np.asarray(e, dtype=np.float64)
    if not (z.shape == n.shape == e.shape):
        raise ValueError("Z, N, and E arrays must have identical shape")
    freqs = np.asarray(DEFAULT_FDPA_FREQUENCIES_HZ if frequencies_hz is None else frequencies_hz, dtype=np.float64)
    sz = compact_fdpa_frequency_shift_transform(z, sr, freqs)
    sn = compact_fdpa_frequency_shift_transform(n, sr, freqs)
    se = compact_fdpa_frequency_shift_transform(e, sr, freqs)

    shape = (freqs.size, z.size)
    dop = np.zeros(shape, dtype=np.float64)
    az_sin = np.zeros(shape, dtype=np.float64)
    az_cos = np.zeros(shape, dtype=np.float64)
    az_counts = np.zeros(shape, dtype=np.float64)
    inc_acc = np.zeros(shape, dtype=np.float64)
    inc_counts = np.zeros(shape, dtype=np.float64)
    vrm = np.zeros(shape, dtype=np.float64)
    hrm = np.zeros(shape, dtype=np.float64)
    vrm_minus_hrm = np.zeros(shape, dtype=np.float64)
    counts = np.zeros(shape, dtype=np.float64)

    for f_idx, freq in enumerate(freqs):
        win_samples = max(2, int(round(float(window_cycles) * float(sr) / float(freq))))
        win_samples = min(win_samples, z.size)
        for start in _window_starts(z.size, win_samples, window_overlap):
            end = min(start + win_samples, z.size)
            samples = np.vstack([sz[f_idx, start:end], sn[f_idx, start:end], se[f_idx, start:end]])
            dop_v, az_v, inc_v, vrm_v, hrm_v, diff_v = _fdpa_window_metrics(samples)
            dop[f_idx, start:end] += dop_v
            if np.isfinite(az_v):
                radians = np.deg2rad(az_v)
                az_sin[f_idx, start:end] += np.sin(radians)
                az_cos[f_idx, start:end] += np.cos(radians)
                az_counts[f_idx, start:end] += 1.0
            if np.isfinite(inc_v):
                inc_acc[f_idx, start:end] += inc_v
                inc_counts[f_idx, start:end] += 1.0
            vrm[f_idx, start:end] += vrm_v
            hrm[f_idx, start:end] += hrm_v
            vrm_minus_hrm[f_idx, start:end] += diff_v
            counts[f_idx, start:end] += 1.0

    covered = counts > 0.0
    for arr in (dop, vrm, hrm, vrm_minus_hrm):
        arr[covered] = arr[covered] / counts[covered]
    azimuth = np.full(shape, np.nan, dtype=np.float64)
    valid_az = az_counts > 0.0
    azimuth[valid_az] = (np.degrees(np.arctan2(az_sin[valid_az], az_cos[valid_az])) + 360.0) % 360.0
    inclination = np.full(shape, np.nan, dtype=np.float64)
    valid_inc = inc_counts > 0.0
    inclination[valid_inc] = inc_acc[valid_inc] / inc_counts[valid_inc]

    dop_mask = dop >= float(dop_threshold)
    return {
        "method": np.array(PAPERSTYLE_FDPA_METHOD),
        "algorithm_revision": np.array(PAPERSTYLE_ALGORITHM_REVISION),
        "transform_family": np.array(PAPERSTYLE_FDPA_TRANSFORM_FAMILY),
        "frequencies_hz": freqs.astype(np.float32),
        "time_axis_s": (np.arange(z.size, dtype=np.float64) / float(sr)).astype(np.float32),
        "window_overlap": np.array(float(window_overlap), dtype=np.float32),
        "window_cycles": np.array(float(window_cycles), dtype=np.float32),
        "dop_threshold": np.array(float(dop_threshold), dtype=np.float32),
        "dop": dop.astype(np.float32),
        "dop_mask": dop_mask,
        "azimuth_deg": azimuth.astype(np.float32),
        "inclination_deg": inclination.astype(np.float32),
        "vrm": vrm.astype(np.float32),
        "hrm": hrm.astype(np.float32),
        "vrm_minus_hrm": vrm_minus_hrm.astype(np.float32),
        "dop_masked_vertical_amplitude": np.where(dop_mask, np.abs(sz), 0.0).astype(np.float32),
    }


def fdpa_file(
    in_path: Path,
    out_path: Path,
    *,
    frequencies_hz: np.ndarray | None = None,
    window_overlap: float = 0.9,
    window_cycles: float = 3.0,
    dop_threshold: float = 0.6,
) -> None:
    st = read(str(in_path))
    st.filter("bandpass", freqmin=0.2, freqmax=0.8, corners=4, zerophase=True)
    tr_z, tr_n, tr_e = _select_zne(st, in_path)
    payload = frequency_dependent_polarization_analysis(
        np.asarray(tr_z.data, dtype=np.float64),
        np.asarray(tr_n.data, dtype=np.float64),
        np.asarray(tr_e.data, dtype=np.float64),
        float(tr_z.stats.sampling_rate),
        frequencies_hz=frequencies_hz,
        window_overlap=window_overlap,
        window_cycles=window_cycles,
        dop_threshold=dop_threshold,
    )
    payload["source_zne_sha256"] = np.array(sha256_file(in_path))
    payload["sampling_rate_hz"] = np.array(float(tr_z.stats.sampling_rate), dtype=np.float32)
    payload["bandpass_hz"] = np.array([0.2, 0.8], dtype=np.float32)
    payload["npts"] = np.array(int(tr_z.stats.npts), dtype=np.int64)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out_path, **payload)
    logger.info("Wrote %s", out_path)


def _parse_frequencies(value: str) -> np.ndarray:
    return np.asarray([float(item.strip()) for item in value.split(",") if item.strip()], dtype=np.float64)


def parse_args():
    parser = argparse.ArgumentParser(description="Run public FDPA diagnostics on 3-component ZNE data")
    parser.add_argument("--in-dir", default=str(repo_path("data/processed")))
    parser.add_argument("--out-dir", default=str(repo_path("data/processed")))
    parser.add_argument("--frequencies-hz", default=",".join(f"{freq:.6g}" for freq in DEFAULT_FDPA_FREQUENCIES_HZ))
    parser.add_argument("--window-overlap", type=float, default=0.9)
    parser.add_argument("--window-cycles", type=float, default=3.0)
    parser.add_argument("--dop-threshold", type=float, default=0.6)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    freqs = _parse_frequencies(args.frequencies_hz)
    for p in sorted(Path(args.in_dir).glob("*_ZNE.mseed")):
        fdpa_file(
            p,
            Path(args.out_dir) / f"{_base_event_id(p.stem)}_fdpa.npz",
            frequencies_hz=freqs,
            window_overlap=args.window_overlap,
            window_cycles=args.window_cycles,
            dop_threshold=args.dop_threshold,
        )
