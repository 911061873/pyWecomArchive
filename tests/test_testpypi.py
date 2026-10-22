"""离线验证 TestPyPI 文件来源及哈希检查，不访问索引。"""

import hashlib
import io
import json
import runpy
from pathlib import Path

import pytest

MODULE = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "scripts/download_testpypi.py")
)
download = MODULE["download"]


@pytest.mark.parametrize("failure", [None, "metadata", "download", "host"])
def test_download_requires_identical_content(tmp_path, monkeypatch, failure):
    expected = tmp_path / "expected"
    expected.mkdir()
    name = "pywecomarchive-0.1.0-py3-none-win_amd64.whl"
    payload = b"wheel test content"
    (expected / name).write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    files = {
        "urls": [
            {
                "filename": name,
                "digests": {"sha256": "wrong" if failure == "metadata" else digest},
                "url": "https://untrusted.invalid/a.whl"
                if failure == "host"
                else "https://test-files.pythonhosted.org/a.whl",
            }
        ]
    }

    def urlopen(url, **kwargs):
        if url.endswith("/json"):
            return io.BytesIO(json.dumps(files).encode())
        return io.BytesIO(b"tampered" if failure == "download" else payload)

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    output = tmp_path / "output"
    if failure:
        with pytest.raises(RuntimeError):
            download(expected, output, "0.1.0")
        assert not (output / name).exists()
    else:
        download(expected, output, "0.1.0")
        assert (output / name).read_bytes() == payload


def test_promote_requires_all_platforms(tmp_path):
    (tmp_path / "unexpected.whl").write_bytes(b"wheel")
    with pytest.raises(RuntimeError, match="数量"):
        download(tmp_path, tmp_path / "output", "0.1.0", require_all=True)
