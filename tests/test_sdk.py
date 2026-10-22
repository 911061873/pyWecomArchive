"""用可控原生替身验证业务路径和资源生命周期，不访问企业 API。"""

import ctypes
import json
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from pywecomarchive import SdkClosedError, SdkResponseError, WecomArchiveSdk
from pywecomarchive._buffers import NativeBuffers
from pywecomarchive.errors import SdkCallError, SdkError
from pywecomarchive.models import parse_message


@pytest.fixture
def native(monkeypatch):
    binding = MagicMock()
    binding.lib.NewSdk.return_value = 123
    binding.lib.Init.return_value = 0
    binding.lib.NewSlice.return_value = 456
    binding.lib.NewMediaData.return_value = 789
    binding.lib.GetChatData.return_value = 0
    binding.lib.DecryptData.return_value = 0
    binding.lib.GetMediaData.return_value = 0
    binding.lib.IsMediaDataFinish.return_value = 1
    binding.lib.GetDataLen.return_value = 0
    binding.lib.GetIndexLen.return_value = 0
    binding.lib.GetData.return_value = None
    binding.lib.GetOutIndexBuf.return_value = None
    payload = {"errcode": 0, "errmsg": "ok", "chatdata": []}

    def content(self, buffer):
        return json.dumps(payload).encode()

    monkeypatch.setattr("pywecomarchive._adapter.NativeBinding", lambda _: binding)
    monkeypatch.setattr(NativeBuffers, "get_content_from_slice", content)
    return binding, payload


def test_public_exports():
    import pywecomarchive

    for name in pywecomarchive.__all__:
        assert getattr(pywecomarchive, name) is not None


def test_chat_response_and_context_cleanup(native):
    binding, payload = native
    payload["chatdata"] = [
        {
            "seq": 7,
            "msgid": "m",
            "publickey_ver": 1,
            "encrypt_random_key": "k",
            "encrypt_chat_msg": "c",
        }
    ]
    with WecomArchiveSdk("corp", "secret") as sdk:
        assert sdk.get_chat_data().chatdata[0].seq == 7
    sdk.close()
    binding.lib.FreeSlice.assert_called_once_with(456)
    binding.lib.DestroySdk.assert_called_once_with(123)
    binding.close.assert_called_once()
    with pytest.raises(SdkClosedError):
        sdk.get_chat_data()


@pytest.mark.parametrize("failure", ["native", "json", "schema"])
def test_chat_failure_releases_buffer(native, failure):
    binding, payload = native
    if failure == "native":
        binding.lib.GetChatData.return_value = 9999
    elif failure == "json":
        payload["errcode"] = "invalid"
    else:
        payload["chatdata"] = "invalid"
    with WecomArchiveSdk("corp", "secret") as sdk:
        with pytest.raises((SdkCallError, SdkResponseError)):
            sdk.get_chat_data()
    binding.lib.FreeSlice.assert_called_once_with(456)


def test_init_failure_destroys_handle(native):
    binding, _ = native
    binding.lib.Init.return_value = 9999
    with pytest.raises(SdkCallError):
        WecomArchiveSdk("corp", "secret")
    binding.lib.DestroySdk.assert_called_once_with(123)
    binding.close.assert_called_once()


def test_null_handle_closes_binding(native):
    binding, _ = native
    binding.lib.NewSdk.return_value = None
    with pytest.raises(SdkError):
        WecomArchiveSdk("corp", "secret")
    binding.lib.DestroySdk.assert_not_called()
    binding.close.assert_called_once()


@pytest.mark.parametrize("kwargs", [{"limit": 0}, {"seq": -1}, {"seq": True}])
def test_invalid_parameters_do_not_call_native(native, kwargs):
    binding, _ = native
    with WecomArchiveSdk("corp", "secret") as sdk:
        with pytest.raises((ValidationError, SdkResponseError)):
            sdk.get_chat_data(**kwargs)
    binding.lib.GetChatData.assert_not_called()
    binding.lib.NewSlice.assert_not_called()


def test_media_and_error_cleanup(native):
    binding, _ = native
    with WecomArchiveSdk("corp", "secret") as sdk:
        (chunk,) = sdk.iter_media_data("file")
        assert chunk.data == b"" and chunk.is_finish
        binding.lib.GetMediaData.return_value = 9999
        with pytest.raises(SdkCallError):
            sdk.get_media_data("file")
    assert binding.lib.FreeMediaData.call_count == 2


def test_media_stalled_index(native):
    binding, _ = native
    binding.lib.IsMediaDataFinish.return_value = 0
    with WecomArchiveSdk("corp", "secret") as sdk:
        with pytest.raises(SdkResponseError, match="续传索引"):
            list(sdk.iter_media_data("file"))
    binding.lib.FreeMediaData.assert_called_once_with(789)


def test_decrypt_and_model_validation(native):
    binding, payload = native
    payload.clear()
    payload.update(
        action="send",
        msgid="m",
        msgtime=1,
        msgtype="text",
        from_="user",
        tolist=["other"],
        roomid="",
        text={"content": "你好"},
    )
    payload["from"] = payload.pop("from_")
    with WecomArchiveSdk("corp", "secret") as sdk:
        assert sdk.decrypt_data("key", "cipher").text.content == "你好"
        payload["text"] = {"content": 123}
        with pytest.raises(SdkResponseError):
            sdk.decrypt_data("key", "cipher")
    assert binding.lib.FreeSlice.call_count == 2


def test_explicit_length_preserves_nul():
    from pywecomarchive._native import NativeBinding

    buffer = ctypes.create_string_buffer(b"a\x00b")
    assert NativeBinding.read(ctypes.addressof(buffer), 3) == b"a\x00b"


def test_invalid_message_rejected():
    with pytest.raises(SdkResponseError):
        parse_message(b"not json")
