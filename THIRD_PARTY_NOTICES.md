# 第三方原生库核实记录

维护者已于 2026-10-22 授权公开分发随项目提供的二进制。此授权记录不代表已独立核实上游再分发许可。
当前尚未确认以下二进制的来源版本、完整许可条款及再分发条件，本文及 Python 封装的 MIT 许可证不授予这些文件的额外权利。

| 文件 | 待核实内容 |
| --- | --- |
| WeWorkFinanceSdk.dll / libWeWorkFinanceSdk_C.so | 企业微信官方 SDK 的版本、来源、许可与再分发条件 |
| libcrypto-3-x64.dll / libssl-3-x64.dll | 实际 OpenSSL 版本、对应许可证及声明 |
| libcurl-x64.dll | 实际 curl 版本、构建包含的依赖及许可声明 |
| auditwheel 修复时新增的共享库 | CI 构建日志、wheel 文件清单及对应许可声明 |

官方 SDK 文档入口：https://developer.work.weixin.qq.com/document/path/91774

仍应获取并保留原始许可文本，核实传递依赖，在包中包含必要声明。仅存在本文不表示上游许可核实完成。
Python 封装采用 MIT，许可文本见 LICENSE；此许可不适用于以上第三方二进制。
