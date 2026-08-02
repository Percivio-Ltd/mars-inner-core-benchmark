from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
import zipfile
from pathlib import Path
from urllib.request import urlopen, Request

import numpy as np

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.shared import append_manifest_entry, repo_path, sha256_file

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


DATASET_PID = "doi:10.18715/IPGP.2021.kpmqrnz8"
BASE_URL = "https://dataverse.ipgp.fr/api/datasets/:persistentId/"


def query_dataset(pid: str) -> dict:
    url = f"{BASE_URL}?persistentId={pid}"
    with urlopen(url, timeout=120) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if payload.get("status") != "OK":
        raise RuntimeError(f"Dataverse query failed: {payload}")
    return payload["data"]["latestVersion"]


def download_file(file_id: str, dest: Path) -> Path:
    url = f"https://dataverse.ipgp.fr/api/access/datafile/{file_id}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = Request(url, headers={"User-Agent": "mars-ic-pipeline"})
    with urlopen(req, timeout=180) as resp:
        with dest.open("wb") as f:
            shutil.copyfileobj(resp, f)
    return dest


def append_downloaded_file_entry(manifest_path: Path, dataset_pid: str, dest: Path, source: str) -> None:
    append_manifest_entry(
        manifest_path,
        {
            "type": "model_file",
            "dataset_pid": dataset_pid,
            "path": str(dest.relative_to(repo_path("."))),
            "name": dest.name,
            "sha256": sha256_file(dest),
            "source": source,
        },
    )


def pick_representative_models(model_dir: Path):
    nd_files = sorted(model_dir.glob("*.nd"))
    if not nd_files:
        raise RuntimeError(f"No .nd files found under {model_dir}")

    lower = [f for f in nd_files if any(k in f.name.lower() for k in ["lower", "min"])]
    mean = [f for f in nd_files if "mean" in f.name.lower()]
    upper = [f for f in nd_files if any(k in f.name.lower() for k in ["upper", "max"])]

    selected = {}
    if lower:
        selected["lower"] = lower[0]
    if mean:
        selected["mean"] = mean[0]
    if upper:
        selected["upper"] = upper[0]

    if len(selected) == 3:
        return selected, "filename-pattern"

    def mean_vp_in_outer_core(path: Path) -> float:
        lines = [ln.strip() for ln in path.read_text(errors="ignore").splitlines()]
        vals = []
        section = "mantle"
        for ln in lines:
            if not ln or ln.startswith("#"):
                continue
            low = ln.lower().strip()
            if low in {"mantle", "outer-core", "inner-core"}:
                section = low
                continue
            if section != "outer-core":
                continue
            parts = ln.split()
            if len(parts) < 2:
                continue
            try:
                depth = float(parts[0])
                vp = float(parts[1])
            except ValueError:
                continue
            if 1550.0 <= depth <= 1800.0:
                vals.append(vp)
        return float(np.mean(vals)) if vals else float("nan")

    if len(selected) < 3:
        metrics = {f: mean_vp_in_outer_core(f) for f in nd_files}
        ranked = sorted(nd_files, key=lambda f: metrics[f])
        if len(ranked) < 3:
            raise RuntimeError("Unable to rank models for representative selection")
        selected.setdefault("lower", ranked[int(max(0, int(0.025 * len(ranked)) - 1))])
        selected.setdefault("mean", ranked[len(ranked) // 2])
        selected.setdefault("upper", ranked[int(min(len(ranked) - 1, int(0.975 * len(ranked))))])
        return selected, "percentile-ranking"
    raise RuntimeError("Could not select representative models")


def append_extracted_file_entries(manifest_path: Path, dataset_pid: str, root: Path) -> None:
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        append_manifest_entry(
            manifest_path,
            {
                "type": "model_extracted",
                "dataset_pid": dataset_pid,
                "path": str(path.relative_to(repo_path("."))),
                "sha256": sha256_file(path),
            },
        )


def download_ak_models(manifest_path: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    version = query_dataset(DATASET_PID)
    files = version["files"]
    if not files:
        raise RuntimeError("No files returned by IPGP API")

    zip_candidates = [f for f in files if str(f["dataFile"]["filename"]).lower().endswith(".zip")]
    archive_path = None
    extract_dir = out_dir / "ak_subset_raw"

    if zip_candidates:
        archive_file = zip_candidates[0]["dataFile"]
        file_id = archive_file["id"]
        archive_name = archive_file["filename"]

        archive_path = out_dir / archive_name
        download_file(file_id, archive_path)
        logger.info("Downloaded %s", archive_name)
        append_downloaded_file_entry(
            manifest_path,
            DATASET_PID,
            archive_path,
            f"dataverse file id {file_id}",
        )

        if extract_dir.exists():
            shutil.rmtree(extract_dir)
        extract_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive_path, "r") as zf:
            zf.extractall(extract_dir)
    else:
        if extract_dir.exists():
            shutil.rmtree(extract_dir)
        extract_dir.mkdir(parents=True, exist_ok=True)
        direct_nds = [rec["dataFile"] for rec in files if str(rec["dataFile"]["filename"]).lower().endswith(".nd")]
        if not direct_nds:
            raise RuntimeError("No zip archive or direct .nd files found for AK_subset dataset")
        for file_rec in direct_nds:
            dest = extract_dir / str(file_rec["filename"])
            download_file(str(file_rec["id"]), dest)
            logger.info("Downloaded %s", dest.name)
            append_downloaded_file_entry(
                manifest_path,
                DATASET_PID,
                dest,
                f"dataverse file id {file_rec['id']}",
            )

    selected, criterion = pick_representative_models(extract_dir)
    ref_dir = out_dir.parent / "reference"
    ref_dir.mkdir(parents=True, exist_ok=True)
    for key, src in selected.items():
        dst = ref_dir / f"AK_{key}.nd"
        dst.write_bytes(src.read_bytes())

    append_extracted_file_entries(manifest_path, DATASET_PID, extract_dir)
    append_extracted_file_entries(manifest_path, DATASET_PID, ref_dir)
    payload = {
        "type": "model_archive",
        "dataset_pid": DATASET_PID,
        "dataset_name": "ak_subset",
        "selection_criterion": criterion,
        "representative_models": {
            "lower": str((ref_dir / "AK_lower.nd").relative_to(repo_path("."))),
            "mean": str((ref_dir / "AK_mean.nd").relative_to(repo_path("."))),
            "upper": str((ref_dir / "AK_upper.nd").relative_to(repo_path("."))),
        },
    }
    if archive_path is not None:
        payload.update(
            {
                "archive_file": archive_path.name,
                "archive_path": str(archive_path.relative_to(repo_path("."))),
                "archive_sha256": sha256_file(archive_path),
            }
        )
    else:
        payload["archive_file"] = None
        payload["archive_path"] = None
    append_manifest_entry(manifest_path, payload)


def parse_args():
    parser = argparse.ArgumentParser(description="Download AK_subset model set")
    parser.add_argument(
        "--manifest",
        default=str(repo_path("manifest/data_manifest.json")),
    )
    parser.add_argument(
        "--out-dir",
        default=str(repo_path("data/models/ak_subset")),
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    download_ak_models(Path(args.manifest), Path(args.out_dir))
