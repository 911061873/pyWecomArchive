"""保证未完成许可确认或版本不匹配时不能发布。"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/check_release.py"


@pytest.mark.parametrize(
    ("tag", "python_license", "third_party", "license_file", "expected"),
    [
        ("v0.2.0", True, True, True, "版本标签"),
        ("v0.1.0", False, False, False, "python-license-confirmed"),
        ("v0.1.0", True, False, True, "third-party-redistribution-confirmed"),
        ("v0.1.0", True, True, False, "LICENSE"),
        ("v0.1.0", True, True, True, None),
    ],
)
def test_release_gate(
    tmp_path, tag, python_license, third_party, license_file, expected
):
    (tmp_path / "pyproject.toml").write_text(
        'version = "0.1.0"\n'
        f"python-license-confirmed = {str(python_license).lower()}\n"
        f"third-party-redistribution-confirmed = {str(third_party).lower()}\n",
        encoding="utf-8",
    )
    if license_file:
        (tmp_path / "LICENSE").write_text("测试占位，不授予许可", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=tmp_path,
        env={**os.environ, "GITHUB_REF_NAME": tag, "PYTHONUTF8": "1"},
        capture_output=True,
        encoding="utf-8",
    )
    if expected:
        assert result.returncode != 0
        assert expected in result.stderr
    else:
        assert result.returncode == 0, result.stderr
