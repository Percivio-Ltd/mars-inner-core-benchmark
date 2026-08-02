from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np
from obspy import read

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.shared import repo_path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def _base_event_id(path_stem: str) -> str:
    if path_stem.endswith("_Z_filt"):
        return path_stem[:-7]
    return path_stem


def flag_glitches(input_path: Path, output_path: Path, threshold: float = 10.0) -> list:
    st = read(str(input_path))
    tr = st.select(channel="BHZ")[0]
    data = np.asarray(tr.data, dtype=np.float64)
    sr = float(tr.stats.sampling_rate)
    win = max(1, int(round(sr)))
    n = len(data) // win
    if n == 0:
        return []
    windows = data[: n * win].reshape(n, win)
    rms = np.sqrt(np.mean(windows**2, axis=1))
    med = np.median(rms) if len(rms) else 0.0
    flags = []
    if med == 0.0:
        return []
    for i, r in enumerate(rms):
        ratio = float(r / med)
        if ratio > threshold:
            flags.append(
                {
                    "start_s": float(i * win / sr),
                    "end_s": float((i + 1) * win / sr),
                    "rms_ratio": ratio,
                }
            )
    output_path.write_text(json.dumps(flags, indent=2))
    logger.info("Wrote %s with %d flags", output_path, len(flags))
    return flags


def parse_args():
    parser = argparse.ArgumentParser(description="Flag high-amplitude 1-second RMS windows")
    parser.add_argument("--in-dir", default=str(repo_path("data/processed")))
    parser.add_argument("--out-dir", default=str(repo_path("data/processed")))
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    for p in sorted(Path(args.in_dir).glob("*_filt.mseed")):
        out = Path(args.out_dir) / f"{_base_event_id(p.stem)}_glitch_flags.json"
        flag_glitches(p, out)
