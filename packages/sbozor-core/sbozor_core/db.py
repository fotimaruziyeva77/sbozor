"""Async SQLAlchemy engine va sessiya fabrikalari.

Bu modul ATAYIN global `SessionLocal` YARATMAYDI. Engine — resurs (ulanish
puli, fon vazifalari), shuning uchun uni servis o'z `lifespan` ida quradi va
o'sha yerda `await engine.dispose()` bilan yopadi. Modul darajasidagi global
engine import paytida pul ochib qo'yadi, test izolyatsiyasini buzadi va
`sbozor_core` ni "biznes logikasiz infra" bo'lishdan chiqaradi.

Ulanish rolining o'zi ham xavfsizlik qarori: `DATABASE_URL` da HAR DOIM
`sbozor_app` (NOSUPERUSER, NOBYPASSRLS) bo'lishi kerak. Superuser bilan
ulanilsa `FORCE ROW LEVEL SECURITY` ham to'xtata olmaydi va tenant
izolyatsiyasi butunlay yo'qoladi (Pitfall 2).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

__all__ = ["make_engine", "make_sessionmaker"]


def make_engine(url: str, **kw: Any) -> AsyncEngine:
    """Async engine quradi (`postgresql+asyncpg://...`).

    `pool_pre_ping` standart bo'yicha yoqiladi: uzoq turgan ulanish DB qayta
    ishga tushgandan keyin "o'lik" bo'lib qoladi va birinchi so'rov
    `ConnectionDoesNotExistError` bilan yiqiladi. Chaqiruvchi uni (va boshqa
    pul sozlamalarini) `**kw` orqali bekor qila oladi — shuning uchun
    `setdefault`, to'g'ridan-to'g'ri argument emas.
    """
    kw.setdefault("pool_pre_ping", True)
    return create_async_engine(url, **kw)


def make_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Sessiya fabrikasini quradi.

    `expire_on_commit=False` — commit'dan keyin ORM obyektlari yaroqli
    qoladi. Aks holda javob serializatsiyasi (commit'dan KEYIN bo'ladi) har
    bir maydon uchun yangi SELECT chiqaradi va u tranzaksiya tashqarisida,
    ya'ni tenant GUC'lari allaqachon bo'shagan holatda ketadi.
    """
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
