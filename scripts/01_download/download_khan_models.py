from __future__ import annotations

import argparse
import json
import logging
import re
import shutil
import sys
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.shared import append_manifest_entry, repo_path, sha256_file

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DATASET_PID = "doi:10.18715/IPGP.2023.llxn7e6d"
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
    req = Request(url, headers={"User-Agent": "mars-ic-pipeline"})
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(req, timeout=180) as resp:
        with dest.open("wb") as f:
            shutil.copyfileobj(resp, f)
    return dest


def identify_variant(readme_text: str):
    mapping = {}
    if re.search(r"MSL_ETH", readme_text, flags=re.IGNORECASE):
        mapping["MSL_ETH"] = [p for p in re.findall(r"[A-Za-z0-9_]+\.nd", readme_text, flags=0) if "eth" in p.lower()]
    if re.search(r"MSL_IPGP", readme_text, flags=re.IGNORECASE):
        mapping["MSL_IPGP"] = [p for p in re.findall(r"[A-Za-z0-9_]+\.nd", readme_text, flags=0) if "ipgp" in p.lower()]
    return mapping


def _is_generated_taup_cache_file(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    if len(rel.parts) < 2 or rel.parts[-2] != "LSL_Models_TauP":
        return False
    if path.name.endswith(".npz.lock"):
        return True
    elif path.name.endswith(".npz.invalid"):
        return True
    elif path.suffix.lower() == ".npz":
        model_stem = path.stem
    else:
        return False
    return path.with_name(f"{model_stem}.nd").exists()


def append_extracted_file_entries(manifest_path: Path, dataset_pid: str, root: Path) -> None:
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        if path.suffix.lower() == ".zip" or _is_generated_taup_cache_file(path, root):
            continue
        append_manifest_entry(
            manifest_path,
            {
                "type": "model_extracted",
                "dataset_pid": dataset_pid,
                "path": str(path.relative_to(repo_path("."))),
                "sha256": sha256_file(path),
            },
        )


def download_khan_models(manifest_path: Path, out_root: Path) -> None:
    out_root.mkdir(parents=True, exist_ok=True)
    version = query_dataset(DATASET_PID)
    files = version["files"]
    if not files:
        raise RuntimeError("No files returned by IPGP API")

    downloaded = []
    readme_path = None
    for rec in files:
        file_rec = rec["dataFile"]
        name = str(file_rec["filename"])
        file_id = str(file_rec["id"])
        dest = out_root / name
        download_file(file_id, dest)
        downloaded.append(dest)
        logger.info("Downloaded %s", name)
        append_manifest_entry(
            manifest_path,
            {
                "type": "model_file",
                "dataset_pid": DATASET_PID,
                "path": str(dest.relative_to(repo_path("."))),
                "name": name,
                "sha256": sha256_file(dest),
                "source": f"dataverse file id {file_id}",
            },
        )
        if name.lower() == "readme.txt":
            readme_path = dest

    for archive in [p for p in downloaded if p.suffix.lower() == ".zip"]:
        with zipfile.ZipFile(archive, "r") as zf:
            zf.extractall(out_root)

    append_extracted_file_entries(manifest_path, DATASET_PID, out_root)

    mapping = {}
    if readme_path and readme_path.exists():
        mapping = identify_variant(readme_path.read_text(errors="ignore"))

    append_manifest_entry(
        manifest_path,
        {
            "type": "model_mapping",
            "dataset_pid": DATASET_PID,
            "mapping": mapping or {"status": "unresolved"},
            "all_files": [str(p) for p in downloaded],
        },
    )


def parse_args():
    parser = argparse.ArgumentParser(description="Download Khan et al. 2023 MSL model set")
    parser.add_argument(
        "--manifest",
        default=str(repo_path("manifest/data_manifest.json")),
    )
    parser.add_argument(
        "--out-dir",
        default=str(repo_path("data/models/khan2023")),
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    download_khan_models(Path(args.manifest), Path(args.out_dir))
