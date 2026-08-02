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

from scripts.shared import ABLATION_BANDPASS_REVISION, repo_path, sha256_file

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def _base_event_id(path_stem: str) -> str:
    # Input naming convention from rotate step: EVENTID_ZNE
    return path_stem.rsplit("_", 1)[0]


def bandpass_file(in_path: Path, out_path: Path) -> None:
    source_zne_sha256 = sha256_file(in_path)
    st = read(str(in_path))
    st = st.select(channel="BHZ")
    if not st:
        raise ValueError(f"No BHZ trace in {in_path}")

    st.filter("bandpass", freqmin=0.2, freqmax=0.8, corners=4, zerophase=True)
    for tr in st:
        tr.data = np.asarray(tr.data, dtype=np.float32)
        tr.stats.mseed = {"encoding": "FLOAT32"}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    st.write(str(out_path), format="MSEED")
    tr = st[0]
    out_path.with_suffix(".bandpass.json").write_text(
        json.dumps(
            {
                "method": "zero_phase_bhz_bandpass",
                "algorithm_revision": ABLATION_BANDPASS_REVISION,
                "input": str(in_path),
                "output": str(out_path),
                "source_zne_sha256": source_zne_sha256,
                "output_trace_sha256": sha256_file(out_path),
                "channel": "BHZ",
                "bandpass_hz": [0.2, 0.8],
                "corners": 4,
                "zerophase": True,
                "sampling_rate_hz": float(tr.stats.sampling_rate),
                "npts": int(tr.stats.npts),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    logger.info("Wrote %s", out_path)


def parse_args():
    parser = argparse.ArgumentParser(description="Apply bandpass filter to Z component")
    parser.add_argument("--in-dir", default=str(repo_path("data/processed")))
    parser.add_argument("--out-dir", default=str(repo_path("data/processed")))
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    in_dir = Path(args.in_dir)
    out_dir = Path(args.out_dir)
    for f in sorted(in_dir.glob("*_ZNE.mseed")):
        out_file = out_dir / f"{_base_event_id(f.stem)}_Z_filt.mseed"
        bandpass_file(f, out_file)
