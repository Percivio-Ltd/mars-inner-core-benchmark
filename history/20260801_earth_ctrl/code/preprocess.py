#!/usr/bin/env python
"""P0-EARTH-CTRL preprocessing per countersigned PREREG §3.5/§5.
Per event: merge segments -> gap mask; linear-interp gaps <=2 s (invalid in mask), zeros longer;
bandpass 0.2-0.8 Hz 4-corner zero-phase at native rate; Lanczos (a=20) to 20 Hz for 40-Hz epochs
with conservative mask AND; nearest-sample zero-padded cut [-100, +1300] s rel predicted P
(verbatim _cut_with_zero_padding semantics); mechanical QC; A'/C' z-score + envelope via the
verbatim module functions. No visual review; no SNR gate."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
from obspy import read, UTCDateTime

sys.path.insert(0, str(Path(__file__).resolve().parent))
from earth_kernel import normalize_variant

ROOT = Path("/Users/artuskg/marsquake_runs/20260801_earth_ctrl")
RAW, PROC, CAT = ROOT / "data" / "raw", ROOT / "data" / "proc", ROOT / "catalog"
PRE_S, POST_S = 100.0, 1300.0
SR = 20.0
NPTS = int(round((PRE_S + POST_S) * SR))  # 28000
A_WIN = (81.67, 281.67)   # frozen A' (T_pred(PcP) +/- 100)
C_WIN = (-100.0, 1300.0)  # frozen C'


def continuous_native(st):
    """Merge stream to one continuous native-rate array + validity mask; gaps <=2 s linearly
    interpolated (invalid), longer gaps zero (invalid)."""
    st = st.select(channel="BHZ").sort(["starttime"])
    if not st:
        raise ValueError("no BHZ")
    sr = float(st[0].stats.sampling_rate)
    for tr in st:
        if float(tr.stats.sampling_rate) != sr:
            raise ValueError("mixed sample rates in one event window")
    t0 = st[0].stats.starttime
    t1 = max(tr.stats.endtime for tr in st)
    n = int(round((t1 - t0) * sr)) + 1
    data = np.zeros(n, dtype=np.float64)
    valid = np.zeros(n, dtype=bool)
    for tr in st:
        i0 = int(round((tr.stats.starttime - t0) * sr))
        seg = np.asarray(tr.data, dtype=np.float64)
        data[i0:i0 + len(seg)] = seg
        valid[i0:i0 + len(seg)] = True
    # linear interpolation across short gaps (samples stay invalid)
    inv_runs = []
    i = 0
    while i < n:
        if not valid[i]:
            j = i
            while j < n and not valid[j]:
                j += 1
            inv_runs.append((i, j))
            i = j
        else:
            i += 1
    for lo, hi in inv_runs:
        if lo == 0 or hi == n:
            continue
        if (hi - lo) / sr <= 2.0:
            data[lo:hi] = np.interp(np.arange(lo, hi), [lo - 1, hi], [data[lo - 1], data[hi]])
    return data, valid, sr, t0


def cut_zero_padded(data, valid, sr_native, t0, t_p, sr_out=SR):
    """Nearest-sample zero-padded cut, verbatim semantics of align_and_cut._cut_with_zero_padding
    applied to data and mask on the (possibly resampled) 20-Hz grid."""
    target_start = t_p - PRE_S
    src_start = int(round((target_start - t0) * sr_out))
    src_end = src_start + NPTS
    out = np.zeros(NPTS, dtype=np.float64)
    vout = np.zeros(NPTS, dtype=bool)
    src_lo, src_hi = max(0, src_start), min(len(data), src_end)
    if src_hi > src_lo:
        dst_lo = src_lo - src_start
        dst_hi = dst_lo + (src_hi - src_lo)
        out[dst_lo:dst_hi] = data[src_lo:src_hi]
        vout[dst_lo:dst_hi] = valid[src_lo:src_hi]
    return out, vout


def main():
    PROC.mkdir(parents=True, exist_ok=True)
    sel = {r["event_id"]: r for r in csv.DictReader(open(CAT / "event_selection.csv"))
           if r["passed_screen"] == "True"}
    time_axis = np.arange(NPTS, dtype=np.float64) / SR - PRE_S  # verbatim _relative_time_axis
    np.save(PROC / "time_axis.npy", time_axis)
    qc_rows = []
    for eid, row in sorted(sel.items(), key=lambda kv: -float(kv[1]["mag"])):
        path = RAW / f"{eid}.mseed"
        rec = dict(event_id=eid, mag=row["mag"], distance_deg=row["distance_deg"],
                   depth_km=row["depth_km"], origin=row["origin"])
        if not path.exists():
            rec.update(qc="excluded", reason="no_download")
            qc_rows.append(rec)
            continue
        st = read(str(path))
        try:
            data, valid, sr_native, t0 = continuous_native(st)
        except ValueError as e:
            rec.update(qc="excluded", reason=str(e))
            qc_rows.append(rec)
            continue
        t_p = UTCDateTime(row["t_p_abs"])
        rec["native_sr"] = sr_native

        # raw-count QC on the coverage span [P-200, P+1300] at native rate
        c0 = int(round(((t_p - 200.0) - t0) * sr_native))
        c1 = int(round(((t_p + 1300.0) - t0) * sr_native))
        c0c, c1c = max(0, c0), min(len(data), c1)
        span_valid = np.zeros(c1 - c0, dtype=bool)
        span_data = np.zeros(c1 - c0, dtype=np.float64)
        if c1c > c0c:
            span_valid[c0c - c0:c1c - c0] = valid[c0c:c1c]
            span_data[c0c - c0:c1c - c0] = data[c0c:c1c]
        missing_frac = 1.0 - span_valid.mean()
        rec["missing_frac"] = round(float(missing_frac), 4)
        sv = span_data[span_valid]
        if sv.size < 2 or float(np.var(sv)) == 0.0:
            rec.update(qc="excluded", reason="flatline_or_empty")
            qc_rows.append(rec)
            continue
        ident = float(np.mean(np.diff(sv) == 0.0))
        rec["flatline_frac"] = round(ident, 4)
        p2p = float(np.max(sv) - np.min(sv))
        clip_frac = float(np.mean(sv == np.min(sv)) + np.mean(sv == np.max(sv)))
        rec["clip_frac"] = round(clip_frac, 4)
        if missing_frac > 0.10:
            rec.update(qc="excluded", reason="coverage")
        elif ident >= 0.98:
            rec.update(qc="excluded", reason="flatline")
        elif clip_frac > 0.05 and p2p >= 100.0:
            rec.update(qc="excluded", reason="clipping")
        else:
            rec["qc"] = "ok"

        if rec.get("qc") != "ok":
            qc_rows.append(rec)
            continue

        # filter at native rate on the gap-filled array
        from obspy import Trace
        tr = Trace(data=data.copy(), header=dict(sampling_rate=sr_native, starttime=t0,
                                                 network="IU", station="ANMO", channel="BHZ"))
        tr.filter("bandpass", freqmin=0.2, freqmax=0.8, corners=4, zerophase=True)
        fdata = np.asarray(tr.data, dtype=np.float64)
        fvalid, f_sr, f_t0 = valid, sr_native, t0

        if sr_native != SR:  # D-ADAPT-E3: Lanczos a=20 to 20 Hz after filtering
            tr2 = Trace(data=fdata.copy(), header=dict(sampling_rate=sr_native, starttime=t0))
            tr2.interpolate(sampling_rate=SR, method="lanczos", a=20)
            fdata = np.asarray(tr2.data, dtype=np.float64)
            f_t0 = tr2.stats.starttime
            dec = int(round(sr_native / SR))
            nlow = len(fdata)
            fvalid = np.ones(nlow, dtype=bool)
            for k in range(nlow):
                j0 = k * dec
                fvalid[k] = bool(np.all(valid[j0:min(j0 + dec, len(valid))])) if j0 < len(valid) else False
            f_sr = SR

        cut, cvalid = cut_zero_padded(fdata, fvalid, f_sr, f_t0, t_p)
        rec["cut_valid_frac"] = round(float(cvalid.mean()), 4)

        for label, (v0, v1) in (("A", A_WIN), ("C", C_WIN)):
            normed, env, env_valid = normalize_variant(cut, cvalid, time_axis, v0, v1, SR)
            np.save(PROC / f"{eid}_{label}_envelope.npy", env.astype(np.float32))
            np.save(PROC / f"{eid}_{label}_envelope_valid.npy", env_valid)
        np.save(PROC / f"{eid}_cut_valid.npy", cvalid)
        qc_rows.append(rec)

    with open(PROC / "qc_table.csv", "w", newline="") as f:
        fields = ["event_id", "mag", "distance_deg", "depth_km", "origin", "native_sr",
                  "missing_frac", "flatline_frac", "clip_frac", "cut_valid_frac", "qc", "reason"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in qc_rows:
            w.writerow({k: r.get(k, "") for k in fields})
    n_ok = sum(1 for r in qc_rows if r.get("qc") == "ok")
    print(f"qc_ok={n_ok} of {len(qc_rows)}")


if __name__ == "__main__":
    main()
