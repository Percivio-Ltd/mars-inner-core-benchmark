#!/usr/bin/env python
"""P0-EARTH-CTRL acquisition per countersigned PREREG (SHA 9c539050...95fc1) §3 and §11.
Catalog-only steps first (query, selection, contamination screen), then waveform download with
dated + SHA-256 manifest. Frozen floors; no discretionary choices."""
from __future__ import annotations

import csv
import hashlib
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from obspy import UTCDateTime
from obspy.geodetics import locations2degrees
from obspy.taup import TauPyModel

ROOT = Path("/Users/artuskg/marsquake_runs/20260801_earth_ctrl")
CAT = ROOT / "catalog"
RAW = ROOT / "data" / "raw"
STA_LAT, STA_LON = 34.94591, -106.4572
USGS = "https://earthquake.usgs.gov/fdsnws/event/1/query"
MODEL = TauPyModel(model="ak135")


def now_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def fetch(url, dest: Path):
    req = urllib.request.Request(url, headers={"User-Agent": "marsquake-p0-earth-ctrl/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    dest.write_bytes(data)
    return data


def main():
    CAT.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    manifest = []

    # --- 1. frozen selection query (PREREG 3.1) ---
    params = dict(format="geojson", starttime="2000-01-01T00:00:00", endtime="2026-01-01T00:00:00",
                  latitude=STA_LAT, longitude=STA_LON, minradius=25.0, maxradius=35.0,
                  mindepth=10, maxdepth=70, minmagnitude=6.0, orderby="magnitude", limit=200)
    url = USGS + "?" + urllib.parse.urlencode(params)
    raw = fetch(url, CAT / "selection_query.geojson")
    manifest.append(dict(item="selection_query", url=url, date=now_utc(),
                         sha256=sha256_bytes(raw), path="catalog/selection_query.geojson"))
    feats = json.loads(raw)["features"]
    # rank by preferred magnitude desc, tie earlier origin; top 40
    feats.sort(key=lambda f: (-f["properties"]["mag"], f["properties"]["time"]))
    top = feats[:40]

    events = []
    for f in top:
        lon, lat, depth = f["geometry"]["coordinates"]
        origin = UTCDateTime(f["properties"]["time"] / 1000.0)
        dist = float(locations2degrees(lat, lon, STA_LAT, STA_LON))
        arrs = MODEL.get_travel_times(source_depth_in_km=max(depth, 0.0),
                                      distance_in_degree=dist, phase_list=["P", "p"])
        if not arrs:
            continue
        t_p_abs = origin + arrs[0].time
        events.append(dict(event_id=f["id"], mag=f["properties"]["mag"],
                           mag_type=f["properties"]["magType"], place=f["properties"]["place"],
                           origin=str(origin), lat=lat, lon=lon, depth_km=depth,
                           distance_deg=round(dist, 4), t_p_abs=str(t_p_abs),
                           p_travel_s=round(arrs[0].time, 2)))

    # --- 2. contamination screen (PREREG 3.4), catalog-only ---
    screened = []
    screen_log = []
    for ev in events:
        tp = UTCDateTime(ev["t_p_abs"])
        # (a) global M>=6.0 with origin in [tp-2700, tp+1300]
        pa = dict(format="geojson", starttime=str(tp - 2700), endtime=str(tp + 1300),
                  minmagnitude=6.0)
        ua = USGS + "?" + urllib.parse.urlencode(pa)
        da = json.loads(fetch(ua, CAT / "tmp_screen.json"))
        hits_a = [g["id"] for g in da["features"] if g["id"] != ev["event_id"]]
        time.sleep(0.3)
        # (b) M>=5.0 within 15 deg of epicenter, origin in [tp-300, tp+1300]
        pb = dict(format="geojson", starttime=str(tp - 300), endtime=str(tp + 1300),
                  minmagnitude=5.0, latitude=ev["lat"], longitude=ev["lon"], maxradius=15.0)
        ub = USGS + "?" + urllib.parse.urlencode(pb)
        db = json.loads(fetch(ub, CAT / "tmp_screen.json"))
        hits_b = [g["id"] for g in db["features"] if g["id"] != ev["event_id"]]
        time.sleep(0.3)
        excluded = bool(hits_a or hits_b)
        screen_log.append(dict(event_id=ev["event_id"], date=now_utc(),
                               global_m6_hits=hits_a, regional_m5_hits=hits_b,
                               excluded=excluded))
        if not excluded:
            screened.append(ev)
    (CAT / "tmp_screen.json").unlink(missing_ok=True)
    (CAT / "contamination_screen.json").write_text(json.dumps(screen_log, indent=2))
    manifest.append(dict(item="contamination_screen", url="(per-event queries; see file)",
                         date=now_utc(),
                         sha256=sha256_bytes((CAT / "contamination_screen.json").read_bytes()),
                         path="catalog/contamination_screen.json"))

    with open(CAT / "event_selection.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(events[0].keys()) + ["passed_screen"])
        w.writeheader()
        passed = {e["event_id"] for e in screened}
        for ev in events:
            ev2 = dict(ev)
            ev2["passed_screen"] = ev["event_id"] in passed
            w.writerow(ev2)

    # --- 3. waveform download (PREREG 3.1 source ranking, 11) ---
    from obspy.clients.fdsn import Client
    client = Client("IRIS")
    n_ok = 0
    for ev in screened:
        tp = UTCDateTime(ev["t_p_abs"])
        dest = RAW / f"{ev['event_id']}.mseed"
        try:
            st = client.get_waveforms("IU", "ANMO", "00", "BHZ", tp - 300, tp + 1500)
        except Exception as e:
            manifest.append(dict(item=f"waveform:{ev['event_id']}", url="FDSN IRIS dataselect",
                                 date=now_utc(), sha256="", path=f"FAILED: {e}"))
            continue
        st.write(str(dest), format="MSEED")
        manifest.append(dict(item=f"waveform:{ev['event_id']}",
                             url=f"FDSN IU.ANMO.00.BHZ {tp-300}..{tp+1500}",
                             date=now_utc(), sha256=sha256_bytes(dest.read_bytes()),
                             path=f"data/raw/{ev['event_id']}.mseed"))
        n_ok += 1
        time.sleep(0.2)

    with open(CAT / "data_manifest.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["item", "url", "date", "sha256", "path"])
        w.writeheader()
        for row in manifest:
            w.writerow(row)

    print(f"selected={len(events)} passed_screen={len(screened)} downloaded={n_ok}")


if __name__ == "__main__":
    main()
