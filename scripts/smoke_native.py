"""实际加载原生库并创建、销毁句柄，不调用企业网络 API。"""

from pywecomarchive._native import NativeBinding

binding = NativeBinding()
try:
    handle = binding.lib.NewSdk()
    if not handle:
        raise RuntimeError("NewSdk 未返回有效句柄")
    binding.lib.DestroySdk(handle)
finally:
    binding.close()
print("原生 SDK 加载与句柄创建、释放通过")
