# pywecomarchive

企业微信会话内容存档 SDK 的同步 Python 封装，提供消息拉取、消息解密和媒体分块下载，使用 Pydantic 模型返回结构化数据。

Python 封装采用 MIT。发布顺序为 TestPyPI 测试后再手动发布正式 PyPI；第三方二进制许可状态见文末说明。

## 安装与平台

正式发布后可安装：

```bash
pip install pywecomarchive
# 或
uv add pywecomarchive
```

要求 Python >=3.10。分别提供 Windows x64、Linux x86_64 和 Linux ARM64 wheel，各自包含所需原生 SDK。
Linux 的最低 glibc 要求以 Actions 中 auditwheel 输出及最终 wheel 的 manylinux 标签为准。
暂不支持 macOS、Windows ARM64、32 位系统和 Alpine/musl；默认通过 wheel 分发，不提供需要用户编译原生 SDK 的安装流程。

## 使用

```python
import os
from pywecomarchive import WecomArchiveSdk

with WecomArchiveSdk(
    corpid=os.environ["WECOM_CORPID"],
    secret=os.environ["WECOM_ARCHIVE_SECRET"],
) as sdk:
    response = sdk.get_chat_data(seq=0, limit=1000)
    for record in response.chatdata:
        # 将 record.seq 持久化，用于下一批拉取。
        # 按 record.publickey_ver 选择企业私钥，使用 RSA 解开
        # record.encrypt_random_key，得到 encrypt_key 后：
        # message = sdk.decrypt_data(encrypt_key, record.encrypt_chat_msg)
        pass
```

`decrypt_data()` 接收已解开的消息密钥，不自动执行 RSA 私钥解密。默认返回内置消息模型，也支持通过 `adapter=` 传入 Pydantic `TypeAdapter`。

```python
from pathlib import Path
from pywecomarchive import WecomArchiveSdk

# 使用自行获取的 SDK 时指定绝对路径，仍需匹配当前系统与架构。
sdk = WecomArchiveSdk(
    "企业 ID", "存档 Secret", library_path=str(Path("SDK路径").resolve())
)
try:
    with open("media.bin", "wb") as output:
        for chunk in sdk.iter_media_data("媒体 sdkfileid"):
            output.write(chunk.data)
finally:
    sdk.close()
```

`get_media_data()` 返回 `data`、`indexbuf`、`is_finish`，可保存 `indexbuf` 断点续传。
`close()` 可重复调用；建议使用上下文管理器。同一实例不要跨线程并发调用，当前封装不承诺并发安全。
SDK 业务错误通过 `SdkCallError` 及其子类报告，加载错误为 `SdkLoadError`，响应格式错误为 `SdkResponseError`。
真实请求需要配置企业会话存档权限及可信出口 IP；不要在日志中记录凭据、私钥、解密密钥或会话正文。

## 本地开发与验证

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

wheel 仅为当前受支持平台构建；Linux 还需执行 `uv sync --locked --group linux` 和 `uv run --no-sync python scripts/repair_linux.py`，验证修复后的 `wheelhouse/*.whl`。
mock 测试验证接口和资源释放；原生冒烟仅验证加载及句柄创建、释放，不证明真实会话拉取、解密、下载成功。

## GitHub Actions 与发布

目标仓库：<https://github.com/911061873/pyWecomArchive>。
工作流文件为 `.github/workflows/release.yml`。普通分支提交、PR 及手动触发运行 Python 3.10–3.15 测试与三平台构建，上传 wheel 供检查。
Linux 任务输出 ELF 依赖与符号版本，再使用 auditwheel 检测并修复依赖。不能修复、不能加载或缺少平台产物时停止发布。

首次发布前：

1. 在 GitHub 创建 `testpypi` 和 `pypi` environments，按需设置审批及允许发布的标签规则。
2. 登录 [TestPyPI](https://test.pypi.org/manage/account/publishing/)，创建 Pending Publisher：项目名 `pywecomarchive`、Owner `911061873`、Repository `pyWecomArchive`、Workflow `release.yml`、Environment `testpypi`。
3. 正式发布前，在 [PyPI](https://pypi.org/manage/account/publishing/) 创建另一个 Pending Publisher：项目名、Owner、Repository 相同，Workflow 改为 `publish-pypi.yml`、Environment 为 `pypi`。两个站点账号及信任配置互相独立，均不需要 token。
4. 确认名称仍可注册，更新项目版本并提交。推送轻量版本标签，例如 `v0.1.0`。

标签触发后，所有测试和三平台构建通过，版本与许可确认检查通过，才通过 OIDC 上传 TestPyPI。
后续三个平台分别从 TestPyPI 下载自己的 wheel，与构建产物逐文件核对 SHA256，再在独立环境安装并运行原生冒烟及测试。依赖仅从正式 PyPI 获取，避免混合索引解析依赖。

TestPyPI 验证成功后，在 GitHub Actions 手动运行 `publish-pypi.yml`，输入该次 `release.yml` 的运行 ID（运行页面 URL 中的数字）。
流程核对来源运行、标签提交和三个平台测试结果，重新核对 TestPyPI 文件 SHA256，然后将同一批 wheel 上传正式 PyPI，不重新构建。
因此，推送标签不会自动发布到正式 PyPI。构建产物须仍在 GitHub Actions 保留期内；过期后需要使用新版本重新测试发布。
同一版本文件不能覆盖；失败时先检查已上传文件，再决定重试或使用新版本，不自动跳过已有文件。
正式发布后检查 PyPI 文件列表包含三个平台，并在各目标平台用独立环境从 PyPI 安装，重复原生冒烟验证。

## 许可状态

Python 封装采用 [MIT](LICENSE)。维护者已授权分发项目现有二进制，但其上游许可并未独立核实；没有许可声明本身不等于授予再分发许可。
附带 SDK、DLL 及修复 wheel 时加入的共享库不适用本项目 MIT 许可证，详细状态见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
