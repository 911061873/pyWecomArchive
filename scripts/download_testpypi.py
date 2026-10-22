"""从 TestPyPI 下载与指定构建产物完全一致的 wheel，避免重新构建或混用索引。"""

import argparse
import hashlib
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse


def download(expected, output, version, require_all=False):
    wheels = sorted(expected.glob("*.whl"))
    if len(wheels) != (3 if require_all else 1):
        raise RuntimeError("构建产物数量不符合预期")
    if require_all and not all(
        any(platform in wheel.name for wheel in wheels)
        for platform in ("win_amd64", "x86_64", "aarch64")
    ):
        raise RuntimeError("缺少目标平台产物")
    endpoint = f"https://test.pypi.org/pypi/pywecomarchive/{version}/json"
    for attempt in range(12):
        try:
            with urllib.request.urlopen(endpoint, timeout=20) as response:
                files = {item["filename"]: item for item in json.load(response)["urls"]}
            if all(wheel.name in files for wheel in wheels):
                break
        except urllib.error.URLError:
            if attempt == 11:
                raise
        if attempt == 11:
            raise RuntimeError("TestPyPI 未及时提供完整文件列表")
        time.sleep(5)
    output.mkdir(parents=True, exist_ok=True)
    for wheel in wheels:
        item = files[wheel.name]
        expected_hash = hashlib.sha256(wheel.read_bytes()).hexdigest()
        if item["digests"]["sha256"] != expected_hash:
            raise RuntimeError(f"TestPyPI 文件与构建产物不一致：{wheel.name}")
        parsed = urlparse(item["url"])
        if parsed.scheme != "https" or parsed.hostname not in {
            "test-files.pythonhosted.org",
            "files.pythonhosted.org",
        }:
            raise RuntimeError("TestPyPI 返回了非预期下载地址")
        with urllib.request.urlopen(item["url"], timeout=120) as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest() != expected_hash:
            raise RuntimeError(f"下载文件哈希不匹配：{wheel.name}")
        (output / wheel.name).write_bytes(data)
        print(f"TestPyPI 下载及 SHA256 验证通过：{wheel.name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    version = re.search(
        r'^version = "([^"]+)"',
        Path("pyproject.toml").read_text(encoding="utf-8"),
        re.MULTILINE,
    ).group(1)
    download(Path("expected"), Path("test-wheel"), version, args.all)
