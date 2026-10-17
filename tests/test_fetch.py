import hashlib
import io
import zipfile
from pathlib import Path

import pytest

from rice_pest_detector import fetch


def _zip(members: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data in members.items():
            z.writestr(name, data)
    return buf.getvalue()


def test_download_verifies_and_removes_partial_on_mismatch(tmp_path: Path, monkeypatch):
    payload = b"archive-bytes"
    monkeypatch.setattr(fetch.urllib.request, "urlopen", lambda *a, **k: io.BytesIO(payload))
    good = fetch.download("https://x", tmp_path / "a.zip", len(payload),
                          hashlib.md5(payload).hexdigest(), hashlib.sha256(payload).hexdigest())
    assert good.read_bytes() == payload
    with pytest.raises(ValueError, match="sha256"):
        fetch.download("https://x", tmp_path / "b.zip", len(payload), hashlib.md5(payload).hexdigest(), "0" * 64)
    assert not (tmp_path / "b.zip").exists() and not (tmp_path / "b.zip.part").exists()


def test_download_removes_partial_on_mid_stream_error(tmp_path: Path, monkeypatch):
    class Broken:
        def __init__(self):
            self.calls = 0

        def read(self, n):
            self.calls += 1
            if self.calls > 1:
                raise ConnectionError("dropped")
            return b"abcd"

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(fetch.urllib.request, "urlopen", lambda *a, **k: Broken())
    with pytest.raises(ConnectionError):
        fetch.download("https://x", tmp_path / "c.zip", 100, "0" * 32, "0" * 64)
    assert not (tmp_path / "c.zip").exists() and not (tmp_path / "c.zip.part").exists()


def test_extract_members_names_missing_member(tmp_path: Path):
    archive = tmp_path / "d.zip"
    archive.write_bytes(_zip({"other/x.jpg": b"x"}))
    manifest = {"images": [{"archive_member": "datasets/x.jpg", "relative_path": "x.jpg",
                            "sha256": hashlib.sha256(b"x").hexdigest()}]}
    with pytest.raises(KeyError, match="datasets/x.jpg.*archive prefix"):
        fetch.extract_members(archive, manifest, tmp_path / "out")


def test_extract_members_checks_digest_and_skips_others(tmp_path: Path):
    data = b"jpegbytes"
    archive = tmp_path / "d.zip"
    archive.write_bytes(_zip({"datasets/02/a.jpg": data, "datasets/02/other.jpg": b"x"}))
    manifest = {"images": [{"archive_member": "datasets/02/a.jpg", "relative_path": "02/a.jpg",
                            "sha256": hashlib.sha256(data).hexdigest()}]}
    assert fetch.extract_members(archive, manifest, tmp_path / "out") == 1
    assert not (tmp_path / "out" / "02" / "other.jpg").exists()
    manifest["images"][0]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="a.jpg"):
        fetch.extract_members(archive, manifest, tmp_path / "out2")


def test_extract_members_rejects_path_traversal(tmp_path: Path):
    archive = tmp_path / "d.zip"
    archive.write_bytes(_zip({"datasets/x.jpg": b"x"}))
    manifest = {"images": [{"archive_member": "datasets/x.jpg", "relative_path": "../escape.jpg",
                            "sha256": hashlib.sha256(b"x").hexdigest()}]}
    with pytest.raises(ValueError, match="escapes"):
        fetch.extract_members(archive, manifest, tmp_path / "out")
