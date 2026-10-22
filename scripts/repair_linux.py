"""让 auditwheel 根据真实 ELF 符号要求确定并修复 manylinux wheel。"""

import re
import subprocess
from pathlib import Path

for wheel in Path("dist").glob("*.whl"):
    result = subprocess.check_output(["auditwheel", "show", str(wheel)], text=True)
    print(result)
    tag = re.search(r"manylinux_\d+_\d+_(?:x86_64|aarch64)", result)
    if tag is None:
        raise SystemExit("auditwheel 未提供可用的 manylinux 标签，停止构建")
    subprocess.run(
        ["auditwheel", "repair", "--plat", tag.group(), "-w", "wheelhouse", str(wheel)],
        check=True,
    )
