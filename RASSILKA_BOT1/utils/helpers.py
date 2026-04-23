from __future__ import annotations

from aiogram.types import Message


SUPPORTED_CONTENT_TYPES = {
    "text",
    "photo",
    "video",
    "document",
    "voice",
    "audio",
    "video_note",
}


def detect_content_type(message: Message) -> str:
    if message.text:
        return "text"
    if message.photo:
        return "photo"
    if message.video:
        return "video"
    if message.document:
        return "document"
    if message.voice:
        return "voice"
    if message.audio:
        return "audio"
    if message.video_note:
        return "video_note"
    return "unsupported"


def extract_text_preview(message: Message) -> str:
    if message.text:
        return message.text
    if message.caption:
        return message.caption
    return ""
