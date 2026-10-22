"""底层绑定：加载动态库并声明官方 C ABI，不处理业务数据。"""

import ctypes as ct
import os
import platform
from pathlib import Path

from .errors import SdkLoadError


def default_library() -> Path:
    root = Path(__file__).resolve().parent / "lib"
    machine = platform.machine().lower()
    if platform.system() == "Windows" and machine in {"amd64", "x86_64"}:
        return root / "windows/WeWorkFinanceSdk.dll"
    if platform.system() == "Linux" and machine in {
        "amd64",
        "x86_64",
        "aarch64",
        "arm64",
    }:
        arch = "arm64" if machine in {"aarch64", "arm64"} else "x86_64"
        return root / f"linux/{arch}/libWeWorkFinanceSdk_C.so"
    raise SdkLoadError("当前系统或架构不受本地 SDK 支持")


class NativeBinding:
    """持有动态库与依赖搜索目录，供内部适配层使用。"""

    def __init__(self, library_path: str | None = None) -> None:
        self._directory = None
        try:
            path = (Path(library_path) if library_path else default_library()).resolve()
            if os.name == "nt":
                self._directory = os.add_dll_directory(str(path.parent))
            self.lib = ct.CDLL(str(path))
            self._configure_functions()
        except (OSError, AttributeError):
            self.close()
            raise SdkLoadError("原生 SDK 加载失败，请检查库文件、架构及依赖") from None

    def close(self) -> None:
        if self._directory is not None:
            self._directory.close()
            self._directory = None

    @staticmethod
    def read(pointer: int, length: int) -> bytes:
        return ct.string_at(pointer, length)

    def _configure_functions(self) -> None:
        """显式配置原生函数的参数类型和返回类型。"""
        self.lib.NewSdk.argtypes = []
        self.lib.NewSdk.restype = ct.c_void_p

        self.lib.Init.argtypes = [ct.c_void_p, ct.c_char_p, ct.c_char_p]
        self.lib.Init.restype = ct.c_int

        self.lib.GetChatData.argtypes = [
            ct.c_void_p,
            ct.c_ulonglong,
            ct.c_uint,
            ct.c_char_p,
            ct.c_char_p,
            ct.c_int,
            ct.c_void_p,
        ]
        self.lib.GetChatData.restype = ct.c_int

        self.lib.DecryptData.argtypes = [ct.c_char_p, ct.c_char_p, ct.c_void_p]
        self.lib.DecryptData.restype = ct.c_int

        self.lib.GetMediaData.argtypes = [
            ct.c_void_p,
            ct.c_char_p,
            ct.c_char_p,
            ct.c_char_p,
            ct.c_char_p,
            ct.c_int,
            ct.c_void_p,
        ]
        self.lib.GetMediaData.restype = ct.c_int

        self.lib.DestroySdk.argtypes = [ct.c_void_p]
        self.lib.DestroySdk.restype = None

        self.lib.NewSlice.argtypes = []
        self.lib.NewSlice.restype = ct.c_void_p

        self.lib.FreeSlice.argtypes = [ct.c_void_p]
        self.lib.FreeSlice.restype = None

        self.lib.GetContentFromSlice.argtypes = [ct.c_void_p]
        self.lib.GetContentFromSlice.restype = ct.c_void_p

        self.lib.GetSliceLen.argtypes = [ct.c_void_p]
        self.lib.GetSliceLen.restype = ct.c_int

        self.lib.NewMediaData.argtypes = []
        self.lib.NewMediaData.restype = ct.c_void_p

        self.lib.FreeMediaData.argtypes = [ct.c_void_p]
        self.lib.FreeMediaData.restype = None

        self.lib.GetOutIndexBuf.argtypes = [ct.c_void_p]
        self.lib.GetOutIndexBuf.restype = ct.c_void_p

        self.lib.GetData.argtypes = [ct.c_void_p]
        self.lib.GetData.restype = ct.c_void_p

        self.lib.GetIndexLen.argtypes = [ct.c_void_p]
        self.lib.GetIndexLen.restype = ct.c_int

        self.lib.GetDataLen.argtypes = [ct.c_void_p]
        self.lib.GetDataLen.restype = ct.c_int

        self.lib.IsMediaDataFinish.argtypes = [ct.c_void_p]
        self.lib.IsMediaDataFinish.restype = ct.c_int
