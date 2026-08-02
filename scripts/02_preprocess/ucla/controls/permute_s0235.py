#!/usr/bin/env python3
"""Rotate S0235b channels U->V->W while retaining target channel labels."""

from __future__ import annotations

import argparse
from pathlib import Path

from obspy import Stream, read


def one_trace(stream: Stream, channel: str):
    selected = stream.select(network="XB", station="ELYSE", location="02", channel=channel)
    if len(selected) != 1:
        raise SystemExit(f"expected one 02:{channel} trace, got {len(selected)}")
    return selected[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite {args.output}")

    source = read(str(args.input))
    by_channel = {channel: one_trace(source, channel) for channel in ("BHU", "BHV", "BHW")}
    rotation = {"BHU": "BHW", "BHV": "BHU", "BHW": "BHV"}
    output = Stream()
    for target_channel in ("BHU", "BHV", "BHW"):
        trace = by_channel[rotation[target_channel]].copy()
        trace.stats.channel = target_channel
        output.append(trace)
    output.write(str(args.output), format="MSEED", encoding="STEIM2", reclen=4096)
    print(f"PERMUTATION-WRITTEN: U<-W V<-U W<-V output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
