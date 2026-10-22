"""为 ctypes 预编译库构建平台 wheel，不绑定 CPython ABI。"""

import platform
from pathlib import Path

from setuptools import Distribution, setup
from setuptools.command.bdist_wheel import bdist_wheel
from setuptools.command.build_py import build_py


def native_target():
    system, machine = platform.system(), platform.machine().lower()
    if system == "Windows" and machine in {"amd64", "x86_64"}:
        return "windows", "win_amd64"
    if system == "Linux":
        if machine in {"amd64", "x86_64"}:
            return "linux/x86_64", "linux_x86_64"
        if machine in {"arm64", "aarch64"}:
            return "linux/arm64", "linux_aarch64"
    raise RuntimeError("只支持 Windows x64、Linux x86_64 和 Linux ARM64")


class BinaryDistribution(Distribution):
    def has_ext_modules(self):
        return True


class PlatformBuild(build_py):
    def find_data_files(self, package, src_dir):
        files = super().find_data_files(package, src_dir)
        target, _ = native_target()
        root = Path(src_dir)
        return [
            file
            for file in files
            if not Path(file).relative_to(root).as_posix().startswith("lib/")
            or Path(file).relative_to(root).as_posix().startswith(f"lib/{target}/")
        ]


class PlatformWheel(bdist_wheel):
    def finalize_options(self):
        super().finalize_options()
        self.root_is_pure = False

    def get_tag(self):
        return "py3", "none", native_target()[1]


setup(
    distclass=BinaryDistribution,
    cmdclass={"build_py": PlatformBuild, "bdist_wheel": PlatformWheel},
)
