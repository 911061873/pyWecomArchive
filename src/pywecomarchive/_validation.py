"""SDK 内部配置、参数约束与调用校验。"""

import ctypes
from collections.abc import Callable
from functools import wraps
from typing import Annotated, ParamSpec, TypeVar, get_type_hints

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    ValidationError,
    field_validator,
    validate_call,
)

from .errors import SdkResponseError

P = ParamSpec("P")
T = TypeVar("T")


def check_c_string(value: str) -> str:
    if "\x00" in value:
        raise ValueError("字符串不能包含空字符")
    try:
        value.encode("utf-8")
    except UnicodeError:
        raise ValueError("字符串不能编码为 UTF-8") from None
    return value


CString = Annotated[str, AfterValidator(check_c_string)]
RequiredString = Annotated[CString, Field(min_length=1)]
Pointer = Annotated[int, Field(gt=0, le=2 ** (ctypes.sizeof(ctypes.c_void_p) * 8) - 1)]
Sequence = Annotated[int, Field(ge=0, le=2**64 - 1)]
Limit = Annotated[int, Field(ge=1, le=1000)]
Length = Annotated[int, Field(ge=0, le=2**31 - 1)]


class SdkConfig(BaseModel):
    """SDK 初始化配置，在加载原生库前严格校验。"""

    model_config = ConfigDict(
        strict=True, extra="forbid", frozen=True, hide_input_in_errors=True
    )

    corpid: bytes = Field(min_length=1, strict=False)
    secret: bytes = Field(min_length=1, strict=False, repr=False)
    proxy: bytes = Field(default=b"", strict=False)
    passwd: bytes = Field(default=b"", strict=False, repr=False)
    timeout: int = Field(default=5, ge=1, le=2**31 - 1)
    library_path: str | None = Field(default=None, min_length=1)

    def __init__(
        self,
        *,
        corpid: str | bytes,
        secret: str | bytes,
        proxy: str | bytes = b"",
        passwd: str | bytes = b"",
        timeout: int = 5,
        library_path: str | None = None,
    ) -> None:
        super().__init__(
            corpid=corpid,
            secret=secret,
            proxy=proxy,
            passwd=passwd,
            timeout=timeout,
            library_path=library_path,
        )

    @field_validator("corpid", "secret", "proxy", "passwd", mode="before")
    @classmethod
    def validate_string_input(cls, value: object) -> str | bytes:
        """仅接受字符串或字节串，由 Pydantic 完成编码转换。"""
        if not isinstance(value, (str, bytes)):
            raise ValueError("参数必须是字符串或字节串")
        return value

    @field_validator("corpid", "secret", "proxy", "passwd")
    @classmethod
    def validate_c_bytes(cls, value: bytes) -> bytes:
        """避免 C 字符串被空字符截断，并确保内容为 UTF-8。"""
        if b"\x00" in value:
            raise ValueError("字符串不能包含空字符")
        try:
            value.decode("utf-8")
        except UnicodeError:
            raise ValueError("字节串必须是有效的 UTF-8") from None
        return value

    @field_validator("library_path")
    @classmethod
    def validate_library_path(cls, value: str | None) -> str | None:
        """库路径保留字符串类型，供 pathlib 使用。"""
        if value is None:
            return None
        return check_c_string(value)


def checked(function: Callable[P, T]) -> Callable[P, T]:
    """严格校验方法输入输出，参数错误直接抛出 Pydantic 验证异常。"""
    config = ConfigDict(
        strict=True, arbitrary_types_allowed=True, hide_input_in_errors=True
    )
    validated = validate_call(config=config)(function)
    return_type = get_type_hints(function, include_extras=True)["return"]
    output = TypeAdapter(
        return_type,
        config=None
        if isinstance(return_type, type) and issubclass(return_type, BaseModel)
        else config,
    )

    @wraps(function)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        result = validated(*args, **kwargs)
        try:
            return output.validate_python(result, strict=True)
        except ValidationError:
            raise SdkResponseError(f"{function.__name__} 返回数据校验失败") from None

    return wrapper
