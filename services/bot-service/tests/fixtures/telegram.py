"""Tarmoqqa CHIQMAYDIGAN Telegram uskunasi (`MockedBot` ning o'rnini bosuvchi).

=============================================================================
⛔⛔ NEGA `aiogram.test_utils.mocked_bot.MockedBot` ISHLATILMADI — O'LCHANGAN
   FAKT, TAXMIN EMAS.

Reja `MockedBot` ni ko'rsatgan edi. `aiogram 3.30.0` ning CHOP ETILGAN
g'ildiragida `aiogram/test_utils/` katalogi ⛔ **UMUMAN YO'Q** (o'lchandi:
`ls /opt/venv/lib/python3.13/site-packages/aiogram/test_utils/` ->
«No such file or directory»). U aiogram'ning O'Z test to'plamida
(GitHub repo) yashaydi va paketga kirmaydi.

Shuning uchun uskuna shu yerda AYNI SHAKLDA qayta qurildi: `BaseSession`
ning uch abstrakt metodi bajariladi, `make_request` esa so'rovni
RO'YXATGA yozadi va tayyor natijani qaytaradi. ⛔ Soket OCHILMAYDI —
`make_request` ning tanasida tarmoq chaqiruvi umuman yo'q, ya'ni
«tarmoqqa chiqmaydi» da'vosi STRUKTURAVIY.

=============================================================================
⚠ NEGA HANDLERGA `Message` OBYEKTI KERAK, SOXTA OBYEKT EMAS.

`message.answer(...)` `Message` modelining metodi va u `bot` kontekstiga
tayanadi. Soxta obyekt (`SimpleNamespace`) bilan test handlerning
imzosini emas, o'z uydirmasini o'lchardi: `message.chat.type` ni satr
sifatida berib, `ChatType.PRIVATE` bilan solishtiruvni jimgina noto'g'ri
qilib qo'yish oson. Haqiqiy pydantic modeli bu yo'lni yopadi.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.enums import ChatType
from aiogram.methods import SendMessage
from aiogram.types import Chat, Contact, Message, User

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from aiogram.methods import TelegramMethod

TEST_TOKEN = "123456:TEST-TOKEN-NOT-REAL"
"""⚠ USKUNA, SIR EMAS — `compose.yaml` dagi `bot-tests` standarti bilan
AYNI. Shakl `<raqamlar>:<sir>` bo'lishi SHART: `Bot(...)` konstruktori
`validate_token()` chaqiradi va boshqa shakl `TokenValidationError`
beradi (07-01 da o'lchangan)."""


class RecordingSession(BaseSession):
    """So'rovlarni YOZIB OLADIGAN sessiya — ⛔ tarmoqqa chiqmaydi."""

    def __init__(self) -> None:
        super().__init__()
        self.requests: list[TelegramMethod[Any]] = []

    async def close(self) -> None:
        """Yopiladigan resurs yo'q."""

    async def make_request(
        self,
        bot: Bot,
        method: TelegramMethod[Any],
        # ⚠ `ASYNC109` (`asyncio.timeout` ishlatilsin) BU YERDA ISHLAMAYDI:
        #   imzo `BaseSession` ning ABSTRAKT metodidan meros va uni
        #   o'zgartirish sinfni aiogram uchun yaroqsiz qilardi. Parametr
        #   bu uskunada UMUMAN o'qilmaydi — soket ochilmaydi.
        timeout: int | None = None,  # noqa: ASYNC109
    ) -> Any:
        """So'rovni ro'yxatga qo'yadi va soxta `Message` qaytaradi."""
        self.requests.append(method)
        return make_message(text=getattr(method, "text", ""))

    async def stream_content(
        self,
        url: str,
        headers: dict[str, Any] | None = None,
        timeout: int = 30,  # noqa: ASYNC109 — yuqoridagi bilan bir xil sabab
        chunk_size: int = 65536,
        raise_for_status: bool = True,
    ) -> AsyncGenerator[bytes]:
        """Fayl oqimi bu testlarda ishlatilmaydi."""
        yield b""


def make_bot() -> tuple[Bot, RecordingSession]:
    """Yozib oluvchi sessiya bilan `Bot` — ikkalasi ham qaytariladi."""
    session = RecordingSession()
    return Bot(token=TEST_TOKEN, session=session), session


def make_user(user_id: int = 777, language_code: str = "uz") -> User:
    return User(id=user_id, is_bot=False, first_name="Sotuvchi", language_code=language_code)


def make_message(
    *,
    text: str | None = None,
    contact: Contact | None = None,
    user_id: int = 777,
    chat_type: ChatType = ChatType.PRIVATE,
    language_code: str = "uz",
) -> Message:
    """Bitta xabar — chat TURI ham argument (guruh darvozasi uchun)."""
    return Message(
        message_id=1,
        date=datetime(2026, 8, 12, tzinfo=UTC),
        chat=Chat(id=user_id if chat_type == ChatType.PRIVATE else -100, type=chat_type),
        from_user=make_user(user_id, language_code),
        text=text,
        contact=contact,
    )


def make_contact(*, phone_number: str = "+998901234567", user_id: int | None = 777) -> Contact:
    """⚠ `user_id` IXTIYORIY — bu Bot API ning haqiqiy shakli (Pitfall 8)."""
    return Contact(phone_number=phone_number, first_name="Sotuvchi", user_id=user_id)


def sent_texts(session: RecordingSession) -> list[str]:
    """Yuborilgan xabarlarning MATNI — darvozalar shu ro'yxatni o'lchaydi."""
    return [request.text for request in session.requests if isinstance(request, SendMessage)]
