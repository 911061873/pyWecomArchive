"""验证平台隔离、元数据及 wheel RECORD 的完整性。"""

import base64
import csv
import hashlib
import io
import sys
from email.parser import Parser
from pathlib import Path
from zipfile import ZipFile

from packaging.utils import parse_wheel_filename


def verify(path):
    _, _, _, tags = parse_wheel_filename(path.name)
    assert all(tag.interpreter == "py3" and tag.abi == "none" for tag in tags)
    platforms = {tag.platform for tag in tags}
    if platforms == {"win_amd64"}:
        target, count = "windows/", 4
    elif all("x86_64" in tag for tag in platforms):
        target, count = "linux/x86_64/", 1
    elif all("aarch64" in tag for tag in platforms):
        target, count = "linux/arm64/", 1
    else:
        raise AssertionError(f"平台标签无效：{platforms}")
    with ZipFile(path) as archive:
        names = archive.namelist()
        native = [name for name in names if name.startswith("pywecomarchive/lib/")]
        assert len(native) == count, native
        assert all(name.startswith(f"pywecomarchive/lib/{target}") for name in native)
        assert "pywecomarchive/py.typed" in names
        metadata = Parser().parsestr(
            archive.read(
                next(n for n in names if n.endswith(".dist-info/METADATA"))
            ).decode()
        )
        assert metadata["Name"] == "pywecomarchive"
        assert metadata["Requires-Python"] == ">=3.10"
        assert any(
            "pydantic" in value for value in metadata.get_all("Requires-Dist", [])
        )
        wheel = archive.read(
            next(n for n in names if n.endswith(".dist-info/WHEEL"))
        ).decode()
        assert "Root-Is-Purelib: false" in wheel
        record = next(n for n in names if n.endswith(".dist-info/RECORD"))
        for name, digest, size in csv.reader(
            io.StringIO(archive.read(record).decode())
        ):
            if not digest:
                assert name == record
                continue
            data = archive.read(name)
            algorithm, encoded = digest.split("=", 1)
            assert (
                base64.urlsafe_b64encode(hashlib.new(algorithm, data).digest())
                .rstrip(b"=")
                .decode()
                == encoded
            )
            assert len(data) == int(size)
    print(f"wheel 验证通过：{path.name}")


if __name__ == "__main__":
    paths = [path for pattern in sys.argv[1:] for path in Path().glob(pattern)]
    if not paths:
        raise SystemExit("没有待验证的 wheel")
    for path in paths:
        verify(path)
