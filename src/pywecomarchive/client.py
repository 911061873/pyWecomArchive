"""业务 API：调用方只需传入和接收 Python 数据。"""

from collections.abc import Iterator
from types import TracebackType
from typing import TypeVar, overload

from pydantic import TypeAdapter, ValidationError

from ._adapter import SdkAdapter
from .errors import SdkResponseError
from .models import ArchiveMessage, ChatDataResponse, MediaData, message_adapter

T = TypeVar("T")


class WecomArchiveSdk:
    """同步会话存档客户端；支持显式关闭与上下文管理。"""

    def __init__(
        self,
        corpid: str,
        secret: str,
        *,
        proxy: str = "",
        passwd: str = "",
        timeout: int = 5,
        library_path: str | None = None,
    ) -> None:
        self._adapter = SdkAdapter(
            corpid,
            secret,
            proxy=proxy,
            passwd=passwd,
            timeout=timeout,
            library_path=library_path,
        )

    def get_chat_data(self, seq: int = 0, limit: int = 1000) -> ChatDataResponse:
        """拉取一批加密消息，返回支持属性访问的响应模型。"""
        return self._adapter.get_chat_data(seq, limit)

    @overload
    def decrypt_data(self, encrypt_key: str, encrypt_msg: str) -> ArchiveMessage: ...

    @overload
    def decrypt_data(
        self, encrypt_key: str, encrypt_msg: str, *, adapter: TypeAdapter[T]
    ) -> T: ...

    def decrypt_data(
        self,
        encrypt_key: str,
        encrypt_msg: str,
        *,
        adapter: TypeAdapter[T] | None = None,
    ) -> ArchiveMessage | T:
        """解密并校验消息；默认使用内置模型，也可传入自定义 TypeAdapter。"""
        value = self._adapter.decrypt_data(encrypt_key, encrypt_msg)
        try:
            if adapter is None:
                return message_adapter.validate_python(value, strict=True)
            return adapter.validate_python(value, strict=True)
        except ValidationError:
            raise SdkResponseError("解密后的消息格式校验失败") from None

    def get_media_data(self, sdkfileid: str, indexbuf: str = "") -> MediaData:
        """拉取媒体分块，用返回的 indexbuf 继续获取后续内容。"""
        return self._adapter.get_media_data(sdkfileid, indexbuf)

    def iter_media_data(
        self, sdkfileid: str, indexbuf: str = ""
    ) -> Iterator[MediaData]:
        """从指定索引逐块下载，首次迭代时校验参数并发起请求。

        每次返回完整的 MediaData，包含可用于断点续传的下一块索引。
        调用失败直接抛出异常；停止迭代不会关闭客户端。
        """
        while True:
            chunk = self.get_media_data(sdkfileid, indexbuf)
            if not chunk.is_finish and (
                not chunk.indexbuf or chunk.indexbuf == indexbuf
            ):
                raise SdkResponseError("GetMediaData 未完成但续传索引为空或未前进")
            yield chunk
            if chunk.is_finish:
                return
            indexbuf = chunk.indexbuf

    def close(self) -> None:
        """释放原生资源，可重复调用。"""
        self._adapter.close()

    def __enter__(self) -> "WecomArchiveSdk":
        self._adapter.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
