"""Single-request archive download and manifest-scoped extraction (Colab data path)."""

import hashlib
import urllib.request
import zipfile
from pathlib import Path

ZENODO_URL = "https://zenodo.org/api/records/20066074/files/datasets.zip/content"
ZENODO_BYTES = 1_005_857_218
ZENODO_MD5 = "24960c245a3a21b63be95314cc7467da"
ZENODO_SHA256 = "f4a0409977e0615e34f3cf2b936a5ca9dd3a91b153d239e314334ea40c2537f7"


def download(url: str, dest: Path, expected_bytes: int, expected_md5: str, expected_sha256: str) -> Path:
    dest = Path(dest)
    part = dest.with_name(dest.name + ".part")
    md5, sha, size = hashlib.md5(), hashlib.sha256(), 0
    try:
        with urllib.request.urlopen(url, timeout=120) as response, part.open("wb") as out:
            while chunk := response.read(1 << 20):
                out.write(chunk)
                md5.update(chunk)
                sha.update(chunk)
                size += len(chunk)
    except BaseException:
        part.unlink(missing_ok=True)
        raise
    problems = []
    if size != expected_bytes:
        problems.append(f"bytes {size} != {expected_bytes}")
    if md5.hexdigest() != expected_md5:
        problems.append("md5 mismatch")
    if sha.hexdigest() != expected_sha256:
        problems.append("sha256 mismatch")
    if problems:
        part.unlink(missing_ok=True)
        raise ValueError(f"{url}: " + "; ".join(problems))
    part.replace(dest)
    return dest


def extract_members(archive: Path, manifest: dict, out_root: Path) -> int:
    out_root = Path(out_root).resolve()
    count = 0
    with zipfile.ZipFile(archive) as z:
        for rec in manifest["images"]:
            target = (out_root / rec["relative_path"]).resolve()
            if out_root not in target.parents:
                raise ValueError(f"{rec['relative_path']} escapes {out_root}")
            try:
                data = z.read(rec["archive_member"])
            except KeyError:
                raise KeyError(
                    f"archive member {rec['archive_member']!r} not found in {archive}; "
                    "check the archive prefix (see docs/evaluation-record.md, 'Colab data path')"
                ) from None
            if hashlib.sha256(data).hexdigest() != rec["sha256"]:
                raise ValueError(f"digest mismatch for {rec['archive_member']}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            count += 1
    return count
