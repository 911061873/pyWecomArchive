"""核实版本及发布前条件；在任何 PyPI 上传之前执行。"""

import os
import re
from pathlib import Path

text = Path("pyproject.toml").read_text(encoding="utf-8")
version = re.search(r'^version = "([^"]+)"', text, re.M).group(1)
tag = os.environ.get("GITHUB_REF_NAME", "")
if tag != f"v{version}":
    raise SystemExit(f"版本标签必须是 v{version}，实际为 {tag!r}")
for flag in ("python-license-confirmed", "third-party-redistribution-confirmed"):
    if not re.search(rf"^{flag}\s*=\s*true\s*$", text, re.M):
        raise SystemExit(f"发布被阻止：尚未确认 {flag}，请完成许可核实及声明")
if not Path("LICENSE").is_file():
    raise SystemExit("发布被阻止：缺少 Python 封装的 LICENSE 文件")
