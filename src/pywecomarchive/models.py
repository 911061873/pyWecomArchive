import json
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    TypeAdapter,
    ValidationError,
    model_validator,
)

from .errors import SdkResponseError

UInt32 = Annotated[int, Field(ge=0, le=2**32 - 1)]
UInt64 = Annotated[int, Field(ge=0, le=2**64 - 1)]
Timestamp = Annotated[int, Field(ge=0)]


def check_integer(value: Any) -> int:
    # Pydantic 的整数 Literal 会匹配 True/1.0，需要先检查实际类型。
    if type(value) is not int:
        raise ValueError("枚举值必须是整数")
    return value


class ArchiveModel(BaseModel):
    """严格校验已知字段，保留官方后续新增的字段。"""

    model_config = ConfigDict(
        strict=True,
        extra="allow",
        populate_by_name=True,
        serialize_by_alias=True,
        hide_input_in_errors=True,
    )


class TextContent(ArchiveModel):
    content: str


class MarkdownContent(TextContent):
    """机器人发出的 Markdown 正文，协议字段与文本正文相同。"""


class ImageContent(ArchiveModel):
    md5sum: str
    filesize: UInt32
    sdkfileid: str


class RevokeContent(ArchiveModel):
    pre_msgid: str


class AgreeContent(ArchiveModel):
    userid: str
    agree_time: Timestamp


class DisagreeContent(ArchiveModel):
    userid: str
    disagree_time: Timestamp


class VoiceContent(ArchiveModel):
    md5sum: str
    voice_size: UInt32
    play_length: UInt32
    sdkfileid: str


class VideoContent(ImageContent):
    play_length: UInt32


class CardContent(ArchiveModel):
    corpname: str
    userid: str


class LocationContent(ArchiveModel):
    longitude: Annotated[float, Field(ge=-180, le=180, allow_inf_nan=False)]
    latitude: Annotated[float, Field(ge=-90, le=90, allow_inf_nan=False)]
    address: str
    title: str
    zoom: UInt32


class EmotionContent(ArchiveModel):
    type: Annotated[Literal[1, 2], BeforeValidator(check_integer)]
    width: UInt32
    height: UInt32
    imagesize: UInt32
    md5sum: str
    sdkfileid: str


class FileContent(ImageContent):
    filename: str
    fileext: str


class LinkContent(ArchiveModel):
    title: str
    description: str
    link_url: str
    image_url: str


class WeappContent(ArchiveModel):
    title: str
    description: str
    username: str
    displayname: str
    appid: str | None = None
    pagepath: str | None = None


class EncodedContent(ArchiveModel):
    """保留协议中的 JSON 字符串，可通过 parse_content() 访问内容模型。"""

    content: str

    def _content_type(self) -> str:
        raise NotImplementedError

    def parse_content(self) -> ArchiveModel | dict[str, Any]:
        try:
            value = json.loads(self.content)
            if not isinstance(value, dict):
                raise ValueError("子消息内容必须是对象")
            model = _CONTENT_MODELS.get(self._content_type())
            return model.model_validate(value) if model is not None else value
        except (ValueError, TypeError, RecursionError):
            raise SdkResponseError("子消息 JSON 或字段校验失败") from None

    @model_validator(mode="after")
    def validate_content(self):
        try:
            self.parse_content()
        except SdkResponseError:
            raise ValueError("子消息内容校验失败") from None
        return self


class MixedItem(EncodedContent):
    type: str

    def _content_type(self) -> str:
        return self.type


class ChatRecordItem(EncodedContent):
    type: str
    msgtime: Timestamp = Field(description="子消息发送时间，UTC 时间戳，单位秒")
    from_chatroom: bool

    def _content_type(self) -> str:
        return _CHAT_RECORD_TYPES.get(self.type, self.type)


class NoteItem(EncodedContent):
    msg_type: str

    def _content_type(self) -> str:
        return self.msg_type


class ChatRecordContent(ArchiveModel):
    title: str
    item: list[ChatRecordItem]


class TodoContent(ArchiveModel):
    title: str
    content: str


class VoteContent(ArchiveModel):
    votetitle: str
    voteitem: list[str]
    votetype: Annotated[Literal[101, 102], BeforeValidator(check_integer)]
    voteid: str


class CollectDetail(ArchiveModel):
    id: UInt64
    ques: str
    type: Literal["Text", "Number", "Date", "Time"]


class CollectContent(ArchiveModel):
    room_name: str
    creator: str
    create_time: str
    title: str
    details: list[CollectDetail]


class RedpacketContent(ArchiveModel):
    type: Annotated[Literal[1, 2, 3], BeforeValidator(check_integer)]
    wish: str
    totalcnt: UInt32
    totalamount: UInt32


class ExternalRedpacketContent(ArchiveModel):
    type: Annotated[Literal[1, 2], BeforeValidator(check_integer)]
    wish: str
    totalcnt: UInt32
    totalamount: UInt32


class MeetingContent(ArchiveModel):
    topic: str
    starttime: Timestamp = Field(description="会议开始时间，UTC 时间戳，单位秒")
    endtime: Timestamp | Literal[""] | None = Field(
        default=None, description="会议结束时间，UTC 时间戳，单位秒；快速会议可为空"
    )
    address: str | None = None
    remarks: str | None = None
    meetingid: UInt64


class MeetingNotificationContent(ArchiveModel):
    """会议控制内容；字段表写作 meetingid，JSON 示例实际使用 meeting_id。"""

    meeting_id: UInt64
    notification_type: Annotated[Literal[1, 2], BeforeValidator(check_integer)]
    content: str


class DocContent(ArchiveModel):
    title: str
    doc_creator: str
    link_url: str


class NewsItem(ArchiveModel):
    title: str
    description: str
    url: str
    picurl: str


class NewsContent(ArchiveModel):
    item: list[NewsItem]


class CalendarContent(ArchiveModel):
    title: str
    creatorname: str
    attendeename: list[str]
    starttime: Timestamp
    endtime: Timestamp
    place: str
    remarks: str


class MixedContent(ArchiveModel):
    item: list[MixedItem]


class DemoFileData(ArchiveModel):
    filename: str
    demooperator: str
    starttime: UInt32
    endtime: UInt32


class ShareScreenData(ArchiveModel):
    share: str
    starttime: UInt32
    endtime: UInt32


class MeetingVoiceCallContent(ArchiveModel):
    endtime: UInt32
    sdkfileid: str
    demofiledata: list[DemoFileData] = Field(default_factory=list)
    sharescreendata: list[ShareScreenData] = Field(default_factory=list)


class VoipDocShareContent(ArchiveModel):
    filename: str
    md5sum: str
    filesize: UInt64
    sdkfileid: str


class SphfeedContent(ArchiveModel):
    feed_type: Annotated[Literal[2, 4, 9], BeforeValidator(check_integer)]
    sph_name: str
    feed_desc: str


class VoipTextContent(ArchiveModel):
    callduration: UInt32
    invitetype: Annotated[Literal[1, 2, 3, 4], BeforeValidator(check_integer)]


class QydiskFileContent(ArchiveModel):
    filename: str
    url: str


class SolitaireContent(ArchiveModel):
    solitaire_type: Annotated[Literal[101, 102], BeforeValidator(check_integer)]
    solitaire_content: str


class NoteContent(ArchiveModel):
    """笔记正文；字段表写作 item，JSON 示例实际使用 items。"""

    items: list[NoteItem]


class MessageBase(ArchiveModel):
    msgid: str
    action: Literal["send", "recall"]
    sender: str = Field(alias="from")
    tolist: list[str]
    msgtime: Timestamp = Field(description="消息发送时间，UTC 时间戳，单位毫秒")


class RoomMessage(MessageBase):
    roomid: str


class TextMessage(RoomMessage):
    msgtype: Literal["text"]
    text: TextContent


class ImageMessage(RoomMessage):
    msgtype: Literal["image"]
    image: ImageContent


class RevokeMessage(RoomMessage):
    msgtype: Literal["revoke"]
    revoke: RevokeContent


class AgreeMessage(RoomMessage):
    msgtype: Literal["agree"]
    agree: AgreeContent


class DisagreeMessage(RoomMessage):
    msgtype: Literal["disagree"]
    disagree: DisagreeContent


class VoiceMessage(RoomMessage):
    msgtype: Literal["voice"]
    voice: VoiceContent


class VideoMessage(RoomMessage):
    msgtype: Literal["video"]
    video: VideoContent


class CardMessage(RoomMessage):
    msgtype: Literal["card"]
    card: CardContent


class LocationMessage(RoomMessage):
    msgtype: Literal["location"]
    location: LocationContent


class EmotionMessage(RoomMessage):
    msgtype: Literal["emotion"]
    emotion: EmotionContent


class FileMessage(RoomMessage):
    msgtype: Literal["file"]
    file: FileContent


class LinkMessage(RoomMessage):
    msgtype: Literal["link"]
    link: LinkContent


class WeappMessage(RoomMessage):
    msgtype: Literal["weapp"]
    weapp: WeappContent


class ChatRecordMessage(RoomMessage):
    msgtype: Literal["chatrecord"]
    chatrecord: ChatRecordContent


class TodoMessage(RoomMessage):
    msgtype: Literal["todo"]
    todo: TodoContent


class VoteMessage(RoomMessage):
    msgtype: Literal["vote"]
    vote: VoteContent


class CollectMessage(RoomMessage):
    msgtype: Literal["collect"]
    collect: CollectContent


class RedpacketMessage(RoomMessage):
    msgtype: Literal["redpacket"]
    redpacket: RedpacketContent


class ExternalRedpacketMessage(RoomMessage):
    """互通红包；msgtype 为 external_redpacket，正文字段仍为 redpacket。"""

    msgtype: Literal["external_redpacket"]
    redpacket: ExternalRedpacketContent


class MeetingMessage(RoomMessage):
    msgtype: Literal["meeting"]
    meeting: MeetingContent


class MeetingNotificationMessage(RoomMessage):
    msgtype: Literal["meeting_notification"]
    info: MeetingNotificationContent
    time: str | None = Field(
        default=None, description="示例中的格式化时间，形如 2023-11-24 16:52:38:880"
    )


class DocMessage(RoomMessage):
    msgtype: Literal["docmsg"]
    doc: DocContent


class MarkdownMessage(RoomMessage):
    msgtype: Literal["markdown"]
    info: MarkdownContent


class NewsMessage(RoomMessage):
    msgtype: Literal["news"]
    info: NewsContent


class CalendarMessage(RoomMessage):
    msgtype: Literal["calendar"]
    calendar: CalendarContent


class MixedMessage(RoomMessage):
    msgtype: Literal["mixed"]
    mixed: MixedContent


class MeetingVoiceCallMessage(MessageBase):
    msgtype: Literal["meeting_voice_call"]
    meeting_voice_call: MeetingVoiceCallContent
    voiceid: str


class VoipDocShareMessage(MessageBase):
    msgtype: Literal["voip_doc_share"]
    voip_doc_share: VoipDocShareContent
    voipid: str


class SphfeedMessage(RoomMessage):
    msgtype: Literal["sphfeed"]
    sphfeed: SphfeedContent


class VoipTextMessage(RoomMessage):
    msgtype: Literal["voiptext"]
    info: VoipTextContent


class QydiskFileMessage(RoomMessage):
    msgtype: Literal["qydiskfile"]
    info: QydiskFileContent


class SolitaireMessage(RoomMessage):
    msgtype: Literal["solitaire"]
    info: SolitaireContent


class NoteMessage(RoomMessage):
    msgtype: Literal["note"]
    info: NoteContent


class SwitchMessage(ArchiveModel):
    """切换企业日志，独立于包含 msgtype 的普通消息结构。"""

    msgid: str
    action: Literal["switch"]
    time: Timestamp = Field(description="切换企业时间，UTC 时间戳，单位毫秒")
    user: str


TypedMessage = Annotated[
    TextMessage
    | ImageMessage
    | RevokeMessage
    | AgreeMessage
    | DisagreeMessage
    | VoiceMessage
    | VideoMessage
    | CardMessage
    | LocationMessage
    | EmotionMessage
    | FileMessage
    | LinkMessage
    | WeappMessage
    | ChatRecordMessage
    | TodoMessage
    | VoteMessage
    | CollectMessage
    | RedpacketMessage
    | ExternalRedpacketMessage
    | MeetingMessage
    | MeetingNotificationMessage
    | DocMessage
    | MarkdownMessage
    | NewsMessage
    | CalendarMessage
    | MixedMessage
    | MeetingVoiceCallMessage
    | VoipDocShareMessage
    | SphfeedMessage
    | VoipTextMessage
    | QydiskFileMessage
    | SolitaireMessage
    | NoteMessage,
    Field(discriminator="msgtype"),
]
ArchiveMessage = TypedMessage | SwitchMessage
# 普通消息按 msgtype 判别；切换企业日志没有 msgtype，作为独立联合分支。
message_adapter = TypeAdapter(ArchiveMessage)

_CONTENT_MODELS: dict[str, type[ArchiveModel]] = {
    "text": TextContent,
    "image": ImageContent,
    "revoke": RevokeContent,
    "agree": AgreeContent,
    "disagree": DisagreeContent,
    "voice": VoiceContent,
    "video": VideoContent,
    "card": CardContent,
    "location": LocationContent,
    "emotion": EmotionContent,
    "file": FileContent,
    "link": LinkContent,
    "weapp": WeappContent,
    "chatrecord": ChatRecordContent,
    "todo": TodoContent,
    "vote": VoteContent,
    "collect": CollectContent,
    "redpacket": RedpacketContent,
    "external_redpacket": ExternalRedpacketContent,
    "meeting": MeetingContent,
    "meeting_notification": MeetingNotificationContent,
    "docmsg": DocContent,
    "markdown": MarkdownContent,
    "news": NewsContent,
    "calendar": CalendarContent,
    "mixed": MixedContent,
    "meeting_voice_call": MeetingVoiceCallContent,
    "voip_doc_share": VoipDocShareContent,
    "sphfeed": SphfeedContent,
    "voiptext": VoipTextContent,
    "qydiskfile": QydiskFileContent,
    "solitaire": SolitaireContent,
    "note": NoteContent,
}
_CHAT_RECORD_TYPES = {
    "ChatRecordText": "text",
    "ChatRecordFile": "file",
    "ChatRecordImage": "image",
    "ChatRecordVideo": "video",
    "ChatRecordLink": "link",
    "ChatRecordLocation": "location",
    "ChatRecordMixed": "mixed",
}


def parse_message(value: dict[str, Any] | str | bytes) -> ArchiveMessage:
    """解析解密后的消息，按 action/msgtype 返回具体模型；失败抛出自定义异常。"""
    try:
        if isinstance(value, (str, bytes)):
            return message_adapter.validate_json(value, strict=True)
        return message_adapter.validate_python(value, strict=True)
    except (ValidationError, ValueError, TypeError, RecursionError):
        raise SdkResponseError("会话存档消息类型、JSON 或字段校验失败") from None


class MediaData(BaseModel):
    """一块媒体数据；未完成时用 indexbuf 继续拉取。"""

    model_config = ConfigDict(strict=True, frozen=True)

    data: bytes
    indexbuf: str
    is_finish: bool


class EncryptedChatData(BaseModel):
    """一条加密会话记录，解密前保留密钥版本及密文。"""

    model_config = ConfigDict(
        strict=True, frozen=True, extra="allow", hide_input_in_errors=True
    )

    seq: UInt64
    msgid: str
    publickey_ver: Annotated[int, Field(ge=1)]
    encrypt_random_key: str = Field(repr=False)
    encrypt_chat_msg: str = Field(repr=False)


class Response(BaseModel):
    """业务响应基类，统一通用状态字段与响应校验配置。"""

    model_config = ConfigDict(
        strict=True, frozen=True, extra="allow", hide_input_in_errors=True
    )

    errcode: int
    errmsg: str


class ChatDataResponse(Response):
    """拉取会话记录的响应，chatdata 中每一项均为模型对象。"""

    chatdata: list[EncryptedChatData]
