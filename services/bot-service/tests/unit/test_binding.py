"""BOT-01 — uch darvoza va TERILGAN RAQAMNING STRUKTURAVIY YO'QLIGI (D-24).

=============================================================================
⛔⛔ UCH RAD ETISH — UCH ALOHIDA TEST, BITTA PARAMETRLASHTIRILGAN TEST EMAS.

Parametrlashtirilgan yagona test uchala holatni ham BITTA da'vo bilan
o'lchardi va bittasi olib tashlanganda qolgan ikkitasi uni «qoplab»
turardi — chiqishda esa faqat bitta nom qizarardi. Uch alohida test
nosozlikni AYNAN nomlaydi: `07-VALIDATION.md` ning Test Map i ham
shuni talab qiladi.

=============================================================================
⛔ HAR RAD ETISHDA `core.resolve` CHAQIRUVLARI SONI — NOL.

«Javob neytral edi» tekshiruvi bu da'voni ALMASHTIRMAYDI: chaqiruv
qilingan va javob baribir neytral bo'lgan holat ham mavjud, lekin u
`core-api` da rate-limit sanagichini oshirardi — ya'ni begona kontakt
bilan yuborilgan oqim HAQIQIY sotuvchini o'z akkauntidan bloklab
qo'ya olardi.
"""

from __future__ import annotations

import ast
import inspect
import textwrap
from typing import TYPE_CHECKING, Any, Final

import pytest
from aiogram.enums import ChatType
from fixtures.core_double import MARKET_ID, VENDOR_ID, CoreDouble
from fixtures.telegram import make_bot, make_contact, make_message, sent_texts

from app.core_client import ResolveResult, VendorRef
from app.handlers.binding import on_contact
from app.i18n import get_i18n

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from aiogram import Router
    from aiogram.dispatcher.event.handler import HandlerObject
    from aiogram.utils.i18n import I18n

PHONE_TOKENS: Final = ("phone", "raqam", "998")
"""Telefon o'qishning izlari — ⛔ ro'yxat EMAS, PREDIKAT uchun tokenlar.

⚠ `998` ham kiritilgan: mamlakat kodi bo'yicha regeks yozish terilgan
  raqamni o'qishning eng ehtimolli shakli.
"""

MIN_MESSAGE_HANDLERS: Final = 5
"""⛔ QUYI CHEGARA (§S-10): dispatcher bo'sh bo'lsa quyidagi sikl JIMGINA
yashil bo'lardi. Bugun: `/start`, `/help`, `contact`, `debt`,
`payments`, `more` — oltita."""


@pytest.fixture
def locale() -> Iterator[I18n]:
    """`_()` uchun gettext konteksti — ishlab chiqarishda buni middleware qiladi."""
    engine = get_i18n()
    with engine.context(), engine.use_locale("uz_Latn"):
        yield engine


def neutral_text() -> str:
    return get_i18n().gettext("bot.binding.neutral", locale="uz_Latn")


# ---------------------------------------------------------------------------
# ⛔ UCH DARVOZA — UCH ALOHIDA TEST
# ---------------------------------------------------------------------------


async def test_contact_without_user_id_is_rejected(locale: I18n) -> None:
    """1-darvoza: `user_id is None` — vCard/qo'lda qo'shilgan kontakt.

    Telegram bunday kontaktni HECH KIM bilan bog'lamagan, ya'ni raqam
    kimningdir ekani TASDIQLANMAGAN.
    """
    bot, session = make_bot()
    core = CoreDouble()
    message = make_message(contact=make_contact(user_id=None)).as_(bot)

    await on_contact(message, core=core)

    assert core.resolve_calls == []
    assert sent_texts(session) == [neutral_text()]


async def test_contact_of_another_user_is_rejected(locale: I18n) -> None:
    """2-darvoza: BOSHQA odamning kontakti — D-24 aynan shu yo'lni yopadi.

    Telegram klientida begona kontaktni ulashish ODDIY AMAL; bu darvoza
    bo'lmasa u begona sotuvchining qarzini ochardi.
    """
    bot, session = make_bot()
    core = CoreDouble()
    message = make_message(contact=make_contact(user_id=999), user_id=777).as_(bot)

    await on_contact(message, core=core)

    assert core.resolve_calls == []
    assert sent_texts(session) == [neutral_text()]


async def test_contact_from_group_chat_is_rejected(locale: I18n) -> None:
    """3-darvoza: guruh chati — kim o'qishi nazorat qilinmaydi."""
    bot, session = make_bot()
    core = CoreDouble()
    message = make_message(contact=make_contact(user_id=777), chat_type=ChatType.GROUP).as_(bot)

    await on_contact(message, core=core)

    assert core.resolve_calls == []
    assert sent_texts(session) == [neutral_text()]


# ---------------------------------------------------------------------------
# ⛔ D-26(a) — IKKI SHOX, BIR MATN
# ---------------------------------------------------------------------------


async def test_no_match_and_multiple_matches_render_the_same_text(locale: I18n) -> None:
    """⛔ Ikki javob uchun bot matni BAYT-BAYT bir xil.

    Farqli matn reyestrni tashqaridan tekshirish oracle'i bo'lardi:
    begona odam raqamlarni sinab, kim sotuvchi ekanini aniqlay olardi.
    """
    texts: list[str] = []
    for status in ("no_match", "multiple_matches"):
        bot, session = make_bot()
        core = CoreDouble(resolve_result=ResolveResult(status=status, vendor=None))
        message = make_message(contact=make_contact(user_id=777)).as_(bot)

        await on_contact(message, core=core)

        assert len(core.resolve_calls) == 1
        texts.extend(sent_texts(session))

    first, second = texts
    assert first == second
    # Nazorat: matn HAQIQATAN chizildi (bo'sh satrlar ham «teng» bo'lardi).
    assert first == neutral_text()
    assert first != ""


async def test_valid_contact_calls_resolve_once(locale: I18n) -> None:
    """To'g'ri kontakt: AYNAN BIR chaqiruv, tasdiq matni va menyu."""
    bot, session = make_bot()
    core = CoreDouble(
        resolve_result=ResolveResult(
            status="bound",
            vendor=VendorRef(market_id=MARKET_ID, vendor_id=VENDOR_ID),
        )
    )
    message = make_message(contact=make_contact(user_id=777)).as_(bot)

    await on_contact(message, core=core)

    assert len(core.resolve_calls) == 1
    assert core.resolve_calls[0]["telegram_user_id"] == 777
    (text,) = sent_texts(session)
    assert text == get_i18n().gettext("bot.binding.ok", locale="uz_Latn")
    assert text != neutral_text()


async def test_a_core_failure_shows_a_retry_text_not_the_exception(locale: I18n) -> None:
    """⛔ Nosozlikda foydalanuvchi ISTISNO MATNINI ko'rmaydi (D-04)."""
    from app.core_client import CoreApiError

    bot, session = make_bot()
    core = CoreDouble(
        raises=CoreApiError(operation="resolve", error_type="ConnectError", status=None)
    )
    message = make_message(contact=make_contact(user_id=777)).as_(bot)

    await on_contact(message, core=core)

    (text,) = sent_texts(session)
    assert text == get_i18n().gettext("bot.error.retry", locale="uz_Latn")
    assert "ConnectError" not in text
    assert "core-api" not in text


# ---------------------------------------------------------------------------
# ⛔ TERILGAN RAQAM HANDLERI — YO'QLIK STRUKTURA SIFATIDA O'LCHANADI
# ---------------------------------------------------------------------------


def _executable_source(func: Callable[..., Any]) -> str:
    """Manbani `ast` orqali qayta quradi — izoh va docstring TASHLANADI.

    ⛔ GREP EMAS: bu moduldagi handlerlar taqiqni O'Z docstringlarida
       tushuntiradi va sodda matn qidiruvi ularni buzilish deb
       o'qirdi (07-01 ning Sabotaj 1 darsi — o'shanda `init_sentry`
       darvozasi aynan shu sababdan bo'sh bo'lib chiqqan edi).
    """
    tree = ast.parse(textwrap.dedent(inspect.getsource(func)))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Module | ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            continue
        body = node.body
        if (
            body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            node.body = body[1:] or [ast.Pass()]
    return ast.unparse(tree)


def _magic_attribute_names(filter_object: Any) -> set[str]:
    """`F.contact` -> `{"contact"}`; `F.text.in_(...)` -> `{"text"}`.

    ⚠ `repr(MagicFilter)` FOYDASIZ (o'lchandi: `<... object at 0x...>`),
      shuning uchun amallar zanjiri o'qiladi.
    """
    magic = getattr(filter_object, "magic", None)
    if magic is None:
        return set()
    names: set[str] = set()
    for operation in getattr(magic, "_operations", ()):
        name = getattr(operation, "name", None)
        if isinstance(name, str):
            names.add(name)
    return names


def _all_message_handlers(router: Router) -> list[HandlerObject]:
    """Dispatcher va uning BARCHA ichki routerlaridagi xabar handlerlari."""
    found = list(router.message.handlers)
    for sub_router in router.sub_routers:
        found.extend(_all_message_handlers(sub_router))
    return found


def test_the_handler_registry_is_not_empty() -> None:
    """⛔ QUYI CHEGARA: quyidagi darvoza bo'sh to'plam ustida ishlamasin."""
    from app.main import dp

    handlers = _all_message_handlers(dp)
    assert len(handlers) >= MIN_MESSAGE_HANDLERS, [h.callback.__name__ for h in handlers]
    contact_handlers = [
        handler
        for handler in handlers
        if any("contact" in _magic_attribute_names(f) for f in handler.filters or ())
    ]
    # Ijobiy nazorat: `F.contact` filtri HAQIQATAN topiladi — aks holda
    # quyidagi «istisno» bandi hech qachon ishlamas va darvoza
    # `on_contact` ning O'ZINI qizartirardi.
    assert len(contact_handlers) == 1, contact_handlers


def test_typed_phone_number_is_not_handled() -> None:
    """⛔ `F.contact` DAN BOSHQA telefon o'qiydigan handler YO'Q (D-24).

    Yo'qlik BUTUN dispatcher bo'yicha o'lchanadi, `binding.py` bo'yicha
    emas: handler boshqa modulga yozilsa ham darvoza uni ko'radi.
    """
    from app.main import dp

    offenders: list[str] = []
    for handler in _all_message_handlers(dp):
        names: set[str] = set()
        for filter_object in handler.filters or ():
            names |= _magic_attribute_names(filter_object)
        if "contact" in names:
            continue
        source = _executable_source(handler.callback).lower()
        for token in PHONE_TOKENS:
            if token in source:
                offenders.append(f"{handler.callback.__name__} -> «{token}»")

    assert offenders == [], (
        "⛔ D-24 buzildi — `F.contact` siz handler telefon o'qiyapti:\n  "
        + "\n  ".join(offenders)
        + "\n  Terilgan raqam foydalanuvchining DA'VOSI; `contact` esa "
        "Telegram O'ZI kafolatlagan yagona narsa."
    )
