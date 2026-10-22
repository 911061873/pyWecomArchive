"""接口适配层的缓冲区管理，所有指针仅供内部使用。"""

from ._native import NativeBinding
from ._validation import Length, Pointer, checked
from .errors import SdkError, SdkResponseError


class NativeBuffers:
    """分配、读取并释放绑定层产生的缓冲区。"""

    def __init__(self, binding: NativeBinding) -> None:
        self._lib = binding.lib

    @checked
    def destroy_sdk(self, sdk: Pointer) -> None:
        """释放 NewSdk 创建的句柄，调用后不得再次使用或释放。"""
        self._lib.DestroySdk(sdk)

    @checked
    def new_slice(self) -> Pointer:
        buffer = self._lib.NewSlice()
        if not buffer:
            raise SdkError("SDK 消息缓冲区分配失败")
        return buffer

    @checked
    def free_slice(self, buffer: Pointer) -> None:
        self._lib.FreeSlice(buffer)

    @checked
    def get_content_from_slice(self, buffer: Pointer) -> bytes:
        return self._read(
            self._lib.GetContentFromSlice(buffer), self._get_slice_len(buffer)
        )

    @checked
    def new_media_data(self) -> Pointer:
        buffer = self._lib.NewMediaData()
        if not buffer:
            raise SdkError("SDK 媒体缓冲区分配失败")
        return buffer

    @checked
    def free_media_data(self, buffer: Pointer) -> None:
        self._lib.FreeMediaData(buffer)

    @checked
    def get_out_index_buf(self, buffer: Pointer) -> str:
        raw = self._read(self._lib.GetOutIndexBuf(buffer), self._get_index_len(buffer))
        try:
            return raw.decode("utf-8")
        except UnicodeError:
            raise SdkResponseError("GetOutIndexBuf 返回无效的 UTF-8 数据") from None

    @checked
    def get_data(self, buffer: Pointer) -> bytes:
        return self._read(self._lib.GetData(buffer), self._get_data_len(buffer))

    @checked
    def is_media_data_finish(self, buffer: Pointer) -> bool:
        finish = self._lib.IsMediaDataFinish(buffer)
        if finish not in (0, 1):
            raise SdkResponseError("IsMediaDataFinish 返回无效的完成标志")
        return bool(finish)

    @checked
    def _get_slice_len(self, buffer: Pointer) -> Length:
        return self._lib.GetSliceLen(buffer)

    @checked
    def _get_index_len(self, buffer: Pointer) -> Length:
        return self._lib.GetIndexLen(buffer)

    @checked
    def _get_data_len(self, buffer: Pointer) -> Length:
        return self._lib.GetDataLen(buffer)

    @staticmethod
    @checked
    def _read(pointer: Pointer | None, length: Length) -> bytes:
        if length < 0 or (length and not pointer):
            raise SdkResponseError("SDK 返回无效的缓冲区")
        if not length:
            return b""
        assert pointer is not None
        return NativeBinding.read(pointer, length)
