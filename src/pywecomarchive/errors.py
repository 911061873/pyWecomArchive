"""SDK 异常，不包含凭据或消息正文。"""

from types import MappingProxyType

# 官方 SDK 错误码：https://developer.work.weixin.qq.com/document/path/91552
SDK_ERROR_MESSAGES = MappingProxyType(
    {
        10000: "请求参数错误",
        10001: "网络请求错误",
        10002: "数据解析失败",
        10003: "系统调用失败",
        10004: "密钥错误加密失败【已废弃】",
        10005: "fileid错误",
        10006: "解密失败",
        10007: "找不到消息加密版本的私钥【已废弃】",
        10008: "DecryptMsg错误",
        10009: "ip非法",
        10010: "请求的数据过期",
        10011: "ssl证书错误",
    }
)


class SdkError(Exception):
    """SDK 错误基类。"""


class SdkResponseError(SdkError):
    """SDK 返回的数据不符合协议。"""


class SdkLoadError(SdkError):
    """无法加载原生 SDK。"""


class SdkClosedError(SdkError):
    """SDK 封装已关闭。"""


class SdkCallError(SdkError):
    """原生函数或业务响应返回非零错误码。"""

    def __init__(self, operation: str, code: int):
        self.operation = operation
        self.code = code
        self.message = SDK_ERROR_MESSAGES.get(code, "未知 SDK 错误")
        super().__init__(
            f"{operation} 调用失败，错误码：{code}，错误信息：{self.message}"
        )


class _KnownSdkCallError(SdkCallError):
    """错误码由具体异常类型固定。"""

    code: int

    def __init__(self, operation: str):
        super().__init__(operation, self.code)


class SdkRequestParameterError(_KnownSdkCallError):
    """请求参数错误（10000）。"""

    code = 10000


class SdkNetworkError(_KnownSdkCallError):
    """网络请求错误（10001）。"""

    code = 10001


class SdkDataParseError(_KnownSdkCallError):
    """数据解析失败（10002）。"""

    code = 10002


class SdkSystemCallError(_KnownSdkCallError):
    """系统调用失败（10003）。"""

    code = 10003


class SdkDeprecated10004Error(_KnownSdkCallError):
    """已废弃的错误码 10004（10004）。"""

    code = 10004


class SdkFileIdError(_KnownSdkCallError):
    """媒体文件 ID 错误（10005）。"""

    code = 10005


class SdkDecryptError(_KnownSdkCallError):
    """解密失败（10006）。"""

    code = 10006


class SdkDeprecated10007Error(_KnownSdkCallError):
    """已废弃的错误码 10007（10007）。"""

    code = 10007


class SdkDecryptMsgError(_KnownSdkCallError):
    """DecryptMsg 错误（10008）。"""

    code = 10008


class SdkInvalidIpError(_KnownSdkCallError):
    """请求出口 IP 不合法（10009）。"""

    code = 10009


class SdkDataExpiredError(_KnownSdkCallError):
    """请求的数据过期（10010）。"""

    code = 10010


class SdkSslCertificateError(_KnownSdkCallError):
    """SSL 证书错误（10011）。"""

    code = 10011


SDK_ERROR_TYPES: MappingProxyType[int, type[_KnownSdkCallError]] = MappingProxyType(
    {
        10000: SdkRequestParameterError,
        10001: SdkNetworkError,
        10002: SdkDataParseError,
        10003: SdkSystemCallError,
        10004: SdkDeprecated10004Error,
        10005: SdkFileIdError,
        10006: SdkDecryptError,
        10007: SdkDeprecated10007Error,
        10008: SdkDecryptMsgError,
        10009: SdkInvalidIpError,
        10010: SdkDataExpiredError,
        10011: SdkSslCertificateError,
    }
)
