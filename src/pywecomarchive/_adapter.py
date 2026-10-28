"""接口适配：校验参数、转换编码、处理错误并管理原生资源。"""

import json
from types import TracebackType
from typing import Any

from pydantic import TypeAdapter, ValidationError

from ._buffers import NativeBuffers
from ._native import NativeBinding
from ._validation import (
    CString,
    Limit,
    Pointer,
    RequiredString,
    SdkConfig,
    Sequence,
    checked,
)
from .errors import (
    SDK_ERROR_TYPES,
    SdkBusinessError,
    SdkCallError,
    SdkClosedError,
    SdkError,
    SdkResponseError,
)
from .models import ChatDataResponse, MediaData

_POINTER_ADAPTER = TypeAdapter(Pointer)


class SdkAdapter:
    """返回 Python 数据，并在内部管理 SDK 句柄和原生缓冲区。"""

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
        config = SdkConfig(
            corpid=corpid,
            secret=secret,
            proxy=proxy,
            passwd=passwd,
            timeout=timeout,
            library_path=library_path,
        )
        self._config = config
        self._binding = NativeBinding(config.library_path)
        self._lib = self._binding.lib
        self._utils = NativeBuffers(self._binding)
        self._closed = False
        self._handle = None
        try:
            self._handle = _POINTER_ADAPTER.validate_python(
                self._lib.NewSdk(), strict=True
            )
            self._check(
                "Init", self._lib.Init(self._handle, config.corpid, config.secret)
            )
        except ValidationError:
            self.close()
            raise SdkError("SDK 句柄分配失败") from None
        except BaseException:
            self.close()
            raise

    def _ensure_open(self) -> None:
        if self._closed:
            raise SdkClosedError("SDK 已经关闭")

    @staticmethod
    def _check(operation: str, code: int | None) -> None:
        if type(code) is not int:
            raise SdkResponseError(f"{operation} 返回无效的 SDK 错误码")
        if code == 0:
            return
        error_type = SDK_ERROR_TYPES.get(code)
        if error_type is not None:
            raise error_type(operation)
        raise SdkCallError(operation, code)

    @staticmethod
    def _parse_json(raw: bytes, operation: str) -> dict[str, Any]:
        try:
            result = json.loads(raw)
        except (ValueError, UnicodeError):
            raise SdkResponseError(f"{operation} 返回无效的 JSON 数据") from None
        if not isinstance(result, dict):
            raise SdkResponseError(f"{operation} 返回的 JSON 必须是对象")
        return result

    @checked
    def get_chat_data(self, seq: Sequence = 0, limit: Limit = 1000) -> ChatDataResponse:
        """拉取一批加密消息，校验后返回响应模型。"""
        self._ensure_open()
        buffer = self._utils.new_slice()
        try:
            self._check(
                "GetChatData",
                self._lib.GetChatData(
                    self._handle,
                    seq,
                    limit,
                    self._config.proxy,
                    self._config.passwd,
                    self._config.timeout,
                    buffer,
                ),
            )
            result = self._parse_json(
                self._utils.get_content_from_slice(buffer), "GetChatData"
            )
            code = result.get("errcode", None)
            if type(code) is not int:
                raise SdkResponseError("GetChatData 返回无效的业务错误码")
            if code != 0:
                raise SdkBusinessError("GetChatData", code, result.get("errmsg"))
            try:
                return ChatDataResponse.model_validate(result)
            except ValidationError:
                raise SdkResponseError("GetChatData 返回数据校验失败") from None
        finally:
            self._utils.free_slice(buffer)

    @checked
    def decrypt_data(
        self, encrypt_key: RequiredString, encrypt_msg: RequiredString
    ) -> dict[str, Any]:
        """使用已解开的消息密钥解密，直接返回消息 JSON 对象。"""
        self._ensure_open()
        buffer = self._utils.new_slice()
        try:
            self._check(
                "DecryptData",
                self._lib.DecryptData(
                    encrypt_key.encode(), encrypt_msg.encode(), buffer
                ),
            )
            return self._parse_json(
                self._utils.get_content_from_slice(buffer), "DecryptData"
            )
        finally:
            self._utils.free_slice(buffer)

    @checked
    def get_media_data(
        self, sdkfileid: RequiredString, indexbuf: CString = ""
    ) -> MediaData:
        """拉取一块媒体，返回内容、下一块索引和完成状态。"""
        self._ensure_open()
        buffer = self._utils.new_media_data()
        try:
            self._check(
                "GetMediaData",
                self._lib.GetMediaData(
                    self._handle,
                    indexbuf.encode(),
                    sdkfileid.encode(),
                    self._config.proxy,
                    self._config.passwd,
                    self._config.timeout,
                    buffer,
                ),
            )
            return MediaData(
                data=self._utils.get_data(buffer),
                indexbuf=self._utils.get_out_index_buf(buffer),
                is_finish=self._utils.is_media_data_finish(buffer),
            )
        finally:
            self._utils.free_media_data(buffer)

    def __enter__(self) -> "SdkAdapter":
        """进入上下文，在退出时释放 SDK 句柄。"""
        self._ensure_open()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """退出时关闭封装，保留代码块内抛出的异常。"""
        self.close()

    def close(self) -> None:
        """销毁 SDK 句柄并关闭库搜索目录。"""
        if getattr(self, "_closed", False):
            return
        self._closed = True
        handle = getattr(self, "_handle", None)
        self._handle = None
        try:
            if handle is not None:
                self._utils.destroy_sdk(handle)
        finally:
            binding = getattr(self, "_binding", None)
            if binding is not None:
                binding.close()

    def __del__(self) -> None:
        self.close()
