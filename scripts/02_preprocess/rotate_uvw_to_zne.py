from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np
from obspy import Stream, read
from obspy.signal.rotate import rotate2zne

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.shared import ROTATION_ZNE_REVISION, repo_path, sha256_file

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)
VERIFIED_DEGLITCH_STATUS = "mps_ucla_verified"
DEGLITCH_STATUS_VOCABULARY = (
    "succeeded_mps_only",
    "ucla_unverified",
    VERIFIED_DEGLITCH_STATUS,
    "sidecar_attested_not_independently_verified",
)
DEFAULT_ALLOWED_DEGLITCH_STATUSES = (VERIFIED_DEGLITCH_STATUS,)
UVW_ALIGNMENT_ERROR = "UVW traces must share starttime, sampling_rate, and npts before rotation"


def get_channel_stream(st, code: str):
    for tr in st:
        if tr.stats.channel.endswith(code):
            return tr
    raise ValueError(f"Missing {code} channel")


def validate_deglitch_statuses(statuses: set[str] | None) -> set[str]:
    allowed = set(statuses or DEFAULT_ALLOWED_DEGLITCH_STATUSES)
    unknown = sorted(allowed.difference(DEGLITCH_STATUS_VOCABULARY))
    if unknown:
        expected = ", ".join(DEGLITCH_STATUS_VOCABULARY)
        raise ValueError(f"Unknown deglitch status: {', '.join(unknown)}; expected one of: {expected}")
    return allowed


def _starttime_ns(trace) -> int:
    starttime = trace.stats.starttime
    if hasattr(starttime, "_ns"):
        return int(starttime._ns)
    return int(round(float(starttime.timestamp) * 1_000_000_000))


def _assert_uvw_alignment(traces) -> float:
    traces = tuple(traces)
    sampling_rates = {float(trace.stats.sampling_rate) for trace in traces}
    npts_values = {int(trace.stats.npts) for trace in traces}
    if len(sampling_rates) != 1 or len(npts_values) != 1:
        raise ValueError(UVW_ALIGNMENT_ERROR)

    starttimes_ns = [_starttime_ns(trace) for trace in traces]
    spread_s = (max(starttimes_ns) - min(starttimes_ns)) / 1_000_000_000.0
    sample_period_s = 1.0 / next(iter(sampling_rates))
    if spread_s >= sample_period_s:
        raise ValueError(UVW_ALIGNMENT_ERROR)
    return round(spread_s, 9)


def rotate_to_zne(input_path: Path, output_path: Path, *, deglitch_run_summary_path: Path | None = None) -> None:
    st = read(str(input_path))
    if not st:
        raise ValueError(f"Empty stream for {input_path}")

    tr_u = get_channel_stream(st, "BHU")
    tr_v = get_channel_stream(st, "BHV")
    tr_w = get_channel_stream(st, "BHW")
    uvw_starttime_max_spread_s = _assert_uvw_alignment((tr_u, tr_v, tr_w))

    z, n, e = rotate2zne(
        data_1=np.asarray(tr_u.data, dtype=np.float64),
        azimuth_1=135.0,
        dip_1=-29.3,
        data_2=np.asarray(tr_v.data, dtype=np.float64),
        azimuth_2=15.0,
        dip_2=-29.3,
        data_3=np.asarray(tr_w.data, dtype=np.float64),
        azimuth_3=255.0,
        dip_3=-29.3,
    )

    template = tr_u.copy()
    out = Stream()
    for code, data in [("Z", z), ("N", n), ("E", e)]:
        tr = template.copy()
        tr.data = np.asarray(data, dtype=np.float32)
        tr.stats.channel = f"BH{code}"
        out.append(tr)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.write(str(output_path), format="MSEED")
    deglitch_metadata_path = input_path.with_suffix(".deglitch.json")
    metadata = {
        "method": "uvw_to_zne_nominal_seis_vbb",
        "algorithm_revision": ROTATION_ZNE_REVISION,
        "uvw_starttime_max_spread_s": uvw_starttime_max_spread_s,
        "input_deglitched_trace": str(input_path),
        "input_deglitched_sha256": sha256_file(input_path),
        "output_zne_trace": str(output_path),
        "output_zne_sha256": sha256_file(output_path),
        "deglitch_metadata_path": str(deglitch_metadata_path) if deglitch_metadata_path.exists() else "",
        "deglitch_metadata_sha256": sha256_file(deglitch_metadata_path) if deglitch_metadata_path.exists() else "",
        "deglitch_run_summary_path": str(deglitch_run_summary_path) if deglitch_run_summary_path and deglitch_run_summary_path.exists() else "",
        "deglitch_run_summary_sha256": (
            sha256_file(deglitch_run_summary_path) if deglitch_run_summary_path and deglitch_run_summary_path.exists() else ""
        ),
    }
    output_path.with_suffix(".rotation.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    logger.info("Wrote %s", output_path)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rotate BHU/BHV/BHW to BHZ/BHN/BHE")
    parser.add_argument("--in-dir", default=str(repo_path("data/deglitched")))
    parser.add_argument("--out-dir", default=str(repo_path("data/processed")))
    parser.add_argument(
        "--allow-deglitch-status",
        action="append",
        default=None,
        help="Allow a deglitch run-summary status. Defaults to requiring mps_ucla_verified for every rotated event.",
    )
    parser.add_argument(
        "--allow-raw-diagnostic",
        action="store_true",
        help="Skip deglitch summary validation for explicit raw-input diagnostic runs.",
    )
    return parser


def parse_args():
    parser = build_arg_parser()
    return parser.parse_args()


def _validate_deglitch_summary(
    in_dir: Path,
    files: list[Path],
    allowed_deglitch_statuses: set[str],
) -> None:
    summary_path = Path(in_dir) / "deglitch_run_summary.json"
    if not summary_path.exists():
        raise FileNotFoundError(f"Missing deglitch run summary: {summary_path}")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("run_status") != "complete":
        raise RuntimeError(f"Deglitch run summary is not complete: {summary_path}")
    statuses = {item["event_id"]: item["overall_status"] for item in summary.get("events", [])}
    expected_ids = set(summary.get("expected_event_ids") or statuses)
    file_ids = {path.stem for path in files}
    if file_ids != expected_ids or set(statuses) != expected_ids:
        raise RuntimeError(
            "Deglitch summary/file event mismatch: "
            f"expected={sorted(expected_ids)}, files={sorted(file_ids)}, summary={sorted(statuses)}"
        )
    missing = [path.stem for path in files if path.stem not in statuses]
    if missing:
        raise RuntimeError(f"Missing deglitch summary rows for: {', '.join(missing)}")
    disallowed = [
        f"{path.stem}={statuses[path.stem]}"
        for path in files
        if statuses[path.stem] not in allowed_deglitch_statuses
    ]
    if disallowed:
        raise RuntimeError(f"Disallowed deglitch statuses: {', '.join(disallowed)}")


def rotate_all(
    in_dir: Path,
    out_dir: Path,
    allowed_deglitch_statuses: set[str] | None = None,
    require_deglitch_summary: bool = True,
) -> int:
    allowed_statuses = validate_deglitch_statuses(allowed_deglitch_statuses)
    files = sorted(Path(in_dir).glob("*.mseed"))
    if not files:
        raise FileNotFoundError(f"No MiniSEED inputs found in {in_dir}")
    deglitch_summary_path = Path(in_dir) / "deglitch_run_summary.json" if require_deglitch_summary else None
    if require_deglitch_summary:
        _validate_deglitch_summary(
            Path(in_dir),
            files,
            allowed_statuses,
        )
    for f in files:
        rotate_to_zne(f, Path(out_dir) / f"{f.stem}_ZNE.mseed", deglitch_run_summary_path=deglitch_summary_path)
    return len(files)


if __name__ == "__main__":
    args = parse_args()
    rotate_all(
        Path(args.in_dir),
        Path(args.out_dir),
        allowed_deglitch_statuses=validate_deglitch_statuses(set(args.allow_deglitch_status or DEFAULT_ALLOWED_DEGLITCH_STATUSES)),
        require_deglitch_summary=not args.allow_raw_diagnostic,
    )
