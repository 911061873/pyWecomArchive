# pywecomarchive

[![PyPI](https://img.shields.io/pypi/v/pywecomarchive)](https://pypi.org/project/pywecomarchive/)
[![CI](https://github.com/911061873/pyWecomArchive/actions/workflows/release.yml/badge.svg)](https://github.com/911061873/pyWecomArchive/actions/workflows/release.yml)

企业微信会话内容存档 SDK 的 Python 封装，提供同步的消息拉取、消息解密和媒体下载接口。安装包内置对应平台的原生 SDK，返回结果使用 Pydantic 模型，可直接通过属性访问。

## 安装

```bash
pip install pywecomarchive
```

使用 uv：

```bash
uv add pywecomarchive
```

要求 **Python >=3.10**，运行时依赖 Pydantic 2。

| 系统 | 架构 | 支持情况 |
| --- | --- | --- |
| Windows | x64 / AMD64 | 内置 SDK 及所需 DLL |
| Linux（glibc >=2.17） | x86_64 | 提供 manylinux wheel |
| Linux（glibc >=2.17） | ARM64 / AArch64 | 提供 manylinux wheel |

暂不支持 macOS、Windows ARM64、32 位系统和 Alpine Linux / musl。Python 3.10–3.15 已纳入 CI 测试。

## 快速开始

使用前，在企业微信管理后台开通并配置会话内容存档，准备企业 ID、会话内容存档 Secret，并配置实际请求出口的可信 IP。消息解密还需要企业配置的 RSA 私钥。

通过环境变量提供凭据：

```python
import os

from pywecomarchive import WecomArchiveSdk


def create_sdk() -> WecomArchiveSdk:
    return WecomArchiveSdk(
        corpid=os.environ["WECOM_CORPID"],
        secret=os.environ["WECOM_ARCHIVE_SECRET"],
        timeout=5,
    )


with create_sdk() as sdk:
    response = sdk.get_chat_data(seq=0, limit=1000)
    for record in response.chatdata:
        print(record.seq, record.msgid, record.publickey_ver)
```

`get_chat_data()` 返回加密记录。处理成功后保存对应的 `record.seq`，下一次拉取时将已处理的序号传入 `seq`；首次拉取可使用 `0`，每批最多拉取 `1000` 条。

以下示例复用上面的 `create_sdk()`。建议通过 `with` 管理客户端，退出代码块时自动释放原生 SDK 资源。

## 消息解密

解密分为两步：

1. 根据记录的 `publickey_ver` 选择企业 RSA 私钥，解开 `encrypt_random_key`，得到消息密钥。
2. 将消息密钥和 `encrypt_chat_msg` 传给 `decrypt_data()`。

本包提供第二步。RSA 私钥管理与密钥解开操作由调用方实现，不会自动读取私钥。

```python
from pywecomarchive.models import TextMessage


def decrypt_message(encrypt_key: str, encrypt_chat_msg: str):
    # encrypt_key 是调用方使用企业私钥解开的消息密钥。
    with create_sdk() as sdk:
        return sdk.decrypt_data(encrypt_key, encrypt_chat_msg)
```

默认返回按消息类型解析的模型。例如文本消息为 `TextMessage`，可通过 `message.text.content` 访问正文，通过 `message.sender` 访问协议中的 `from` 字段。

消息模型定义在 `pywecomarchive.models` 中，可用 `model_dump()` 转成字典；需要协议字段名时使用 `model_dump(by_alias=True)`。

需要自定义解密结果时，可传入 Pydantic `TypeAdapter`：

```python
from pydantic import BaseModel, TypeAdapter


class CustomMessage(BaseModel):
    msgid: str
    msgtype: str


def decrypt_custom(encrypt_key: str, encrypt_chat_msg: str) -> CustomMessage:
    with create_sdk() as sdk:
        return sdk.decrypt_data(
            encrypt_key,
            encrypt_chat_msg,
            adapter=TypeAdapter(CustomMessage),
        )
```

## 媒体下载

从解密后的图片、文件等消息中取得 `sdkfileid`，逐块写入文件：

```python
from pathlib import Path


def download_media(sdkfileid: str, destination: Path) -> None:
    with create_sdk() as sdk, destination.open("wb") as output:
        for chunk in sdk.iter_media_data(sdkfileid):
            output.write(chunk.data)
```

每个分块都是 `MediaData`，包含以下字段：

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `data` | `bytes` | 当前分块内容 |
| `indexbuf` | `str` | 下一个分块的续传索引 |
| `is_finish` | `bool` | 是否已下载完成 |

需要自行控制下载进度时，调用 `get_media_data(sdkfileid, indexbuf="")`。每次成功保存分块后记录返回的 `indexbuf`，下次传入该值继续下载；续传时应保留已下载的文件内容。也可将续传索引传给 `iter_media_data()`。

## 客户端配置

```python
sdk = WecomArchiveSdk(
    corpid="企业 ID",
    secret="会话内容存档 Secret",
    proxy="",
    passwd="",
    timeout=5,
    library_path=None,
)
try:
    response = sdk.get_chat_data()
finally:
    sdk.close()
```

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `corpid` | 必填 | 企业 ID |
| `secret` | 必填 | 会话内容存档 Secret |
| `proxy` | `""` | 传给官方 SDK 的代理地址，留空表示不使用代理 |
| `passwd` | `""` | 代理认证信息，格式为 `用户名:密码` |
| `timeout` | `5` | 原生请求超时，单位为秒，必须为正整数 |
| `library_path` | `None` | 自定义 SDK 库文件路径；默认使用包内对应平台的库 |

`library_path` 应指向 DLL 或 `.so` 文件，建议使用绝对路径；自定义库的架构和依赖需要与运行环境匹配。

客户端为同步接口，调用会阻塞当前线程。同一实例不应跨线程并发调用，也不应在调用进行中关闭；需要并行处理时使用独立实例。`close()` 可重复调用，停止媒体迭代不会自动关闭客户端。

## 异常处理

```python
from pydantic import ValidationError

from pywecomarchive import SdkCallError, SdkError

try:
    with create_sdk() as sdk:
        response = sdk.get_chat_data(seq=0, limit=1000)
except ValidationError:
    # 检查初始化参数或方法参数。
    raise
except SdkCallError as exc:
    print(exc.operation, exc.code, exc.message)
except SdkError:
    # 处理加载失败、客户端已关闭、响应格式错误等情况。
    raise
```

| 异常 | 含义 |
| --- | --- |
| `ValidationError` | Pydantic 参数校验失败 |
| `SdkLoadError` | 原生 SDK 加载失败或平台不受支持 |
| `SdkCallError` | 原生 SDK 调用返回非零错误码 |
| `SdkBusinessError` | SDK 调用成功，但业务响应的 `errcode` 非零；保留服务端 `errmsg` |
| `SdkResponseError` | 响应内容、消息模型或媒体续传索引不符合预期 |
| `SdkClosedError` | 客户端关闭后继续调用 |

SDK 已知错误码还对应 `SdkCallError` 的具体子类，例如 `SdkNetworkError`、`SdkInvalidIpError`。除 `ValidationError` 外，上表异常均继承自 `SdkError`。

## 开发与发布

```bash
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv build --wheel
uv run python scripts/verify_wheel.py 'dist/*.whl'
uv run twine check --strict dist/*
uv run python scripts/smoke_native.py
```

本地仅构建当前受支持平台的 wheel。Linux 还需执行 `uv sync --locked --group linux` 和 `uv run --no-sync python scripts/repair_linux.py`，检查修复后的 `wheelhouse/*.whl`。

发布流程：

1. 普通提交和 PR 运行 Python 版本矩阵测试及三平台构建。
2. 修改 `pyproject.toml` 中的版本，提交并推送对应的轻量标签 `v<版本>`，触发 `release.yml` 上传 TestPyPI。
3. 三个平台从 TestPyPI 下载文件，核对 SHA256，在独立环境安装并运行测试。
4. TestPyPI 验证通过后，手动运行 `publish-pypi.yml`，输入测试发布的 Actions 运行 ID，将同一批 wheel 发布到正式 PyPI。

两个索引均使用 Trusted Publishing，分别绑定 `release.yml` / `testpypi` 和 `publish-pypi.yml` / `pypi`。正式发布复用原始产物，不重新构建；推送标签不会直接发布到正式 PyPI。

CI 验证模型、接口、资源释放和原生库加载；真实企业环境中的会话拉取、解密与媒体下载需要调用方自行验证。

## 许可证与相关链接

Python 封装采用 [MIT](LICENSE)。附带的企业微信 SDK、DLL 及其他第三方库遵循各自条款，相关状态见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

- [PyPI](https://pypi.org/project/pywecomarchive/)
- [TestPyPI](https://test.pypi.org/project/pywecomarchive/)
- [GitHub 仓库](https://github.com/911061873/pyWecomArchive)
- [问题反馈](https://github.com/911061873/pyWecomArchive/issues)
- [企业微信会话内容存档文档](https://developer.work.weixin.qq.com/document/path/91774)
