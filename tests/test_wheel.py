"""回归覆盖 auditwheel 修复后新增的 ZIP 目录条目。"""

import base64
import hashlib
import runpy
from pathlib import Path
from zipfile import ZipFile

import pytest

verify = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "scripts/verify_wheel.py")
)["verify"]


@pytest.mark.parametrize("directories", [False, True])
def test_repaired_wheel_directory_entries(tmp_path, directories):
    path = tmp_path / "pywecomarchive-0.1.0-py3-none-manylinux_2_17_x86_64.whl"
    info = "pywecomarchive-0.1.0.dist-info"
    files = {
        "pywecomarchive/py.typed": b"",
        "pywecomarchive/lib/linux/x86_64/libWeWorkFinanceSdk_C.so": b"test binary",
        f"{info}/METADATA": b"Metadata-Version: 2.4\nName: pywecomarchive\nVersion: 0.1.0\nRequires-Python: >=3.10\nRequires-Dist: pydantic>=2.11\n",
        f"{info}/WHEEL": b"Wheel-Version: 1.0\nRoot-Is-Purelib: false\nTag: py3-none-manylinux_2_17_x86_64\n",
    }
    record = []
    with ZipFile(path, "w") as archive:
        if directories:
            for directory in (
                "pywecomarchive/lib/",
                "pywecomarchive/lib/linux/",
                "pywecomarchive/lib/linux/x86_64/",
            ):
                archive.writestr(directory, b"")
        for name, data in files.items():
            archive.writestr(name, data)
            digest = (
                base64.urlsafe_b64encode(hashlib.sha256(data).digest())
                .rstrip(b"=")
                .decode()
            )
            record.append(f"{name},sha256={digest},{len(data)}")
        record.append(f"{info}/RECORD,,")
        archive.writestr(f"{info}/RECORD", "\n".join(record))
    verify(path)
