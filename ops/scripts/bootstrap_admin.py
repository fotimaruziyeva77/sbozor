"""BIRINCHI PLATFORMA ADMINI — deploy'ning yagona qo'lda qadami.

=============================================================================
⛔⛔ NEGA BU SKRIPT BOR (260818, deploy tekshiruvi).

`DEPLOY-SUBDOMAIN.md` «platforma admini ilovadan yaratiladi» der edi, lekin
bunday yo'l QURILMAGAN:

  * `POST /api/v1/users` `USER_MANAGE` talab qiladi — ya'ni ALLAQACHON
    kirgan foydalanuvchi kerak;
  * `UserRepository.create_user()` `is_platform_admin=False` ni QOTIRIB
    yozadi (`user_repo.py`), ya'ni API orqali platforma admini UMUMAN
    tug'ilmaydi;
  * `users` jadvali ilova rolidan REVOKE qilingan (`0001_identity.py`).

Natijada yangi serverga deploy qilingach HECH KIM kira olmasdi va nosozlik
aynan eng yomon paytda — mijoz oldida — chiqardi.

⛔ Shuning uchun birinchi hisob DDL EGASI roli bilan, `auth_create_user`
   SECURITY DEFINER funksiyasi orqali yaratiladi. Bu funksiya
   `must_change_password = true` ni LITERAL yozadi, ya'ni bu yerda
   berilgan parol BIR MARTALIK: birinchi kirishda almashtiriladi.

=============================================================================
⛔ NEGA `argon2` XESHI SHU YERDA HISOBLANADI, SQL'DA EMAS.

Postgres'da Argon2 yo'q. Xesh `sbozor_core.security.hash_password()` bilan
hisoblanadi — ya'ni AYNAN ilova ishlatadigan funksiya. Ikkinchi xeshlash
yo'li yozilsa, u bir kun ilovanikidan ajralib ketardi va parol jimgina
ishlamay qo'yardi.

=============================================================================
ISHLATILISHI (repo ildizidan, serverda):

    docker compose --profile migrate run --rm \\
      -e BOOTSTRAP_PHONE=+998901234567 \\
      -e BOOTSTRAP_NAME="Ism Familiya" \\
      -e BOOTSTRAP_PASSWORD='bir-martalik-parol' \\
      migrate python ops/scripts/bootstrap_admin.py

⛔ Parol buyruq tarixida qoladi — shuning uchun u BIR MARTALIK va birinchi
   kirishda almashtiriladi. Doimiy parolni bu yerga YOZMANG.
"""

from __future__ import annotations

import asyncio
import os
import sys

import phonenumbers
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from sbozor_core.security import hash_password

MIN_PASSWORD_LEN = 10


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if value == "":
        sys.exit(f"⛔ {name} berilmagan — modul boshidagi misolga qarang.")
    return value


def _normalize_phone(raw: str) -> str:
    """⛔ AYNAN ilova qoidasi: E.164, aks holda ikki xil yozuv paydo bo'lardi.

    `auth.py` login'da telefonni shu kutubxona bilan normallashtiradi. Bu
    yerda boshqacha saqlansa, yaratilgan hisob bilan KIRIB BO'LMASDI —
    va sabab hech qayerda ko'rinmasdi.
    """
    try:
        parsed = phonenumbers.parse(raw, "UZ")
    except phonenumbers.NumberParseException:
        sys.exit(f"⛔ Telefon o'qilmadi: {raw}")
    if not phonenumbers.is_valid_number(parsed):
        sys.exit(f"⛔ Telefon yaroqsiz: {raw}")
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


async def main() -> None:
    phone = _normalize_phone(_require("BOOTSTRAP_PHONE"))
    full_name = _require("BOOTSTRAP_NAME")
    password = _require("BOOTSTRAP_PASSWORD")
    locale = os.environ.get("BOOTSTRAP_LOCALE", "uz-Latn").strip() or "uz-Latn"

    if len(password) < MIN_PASSWORD_LEN:
        sys.exit(f"⛔ Parol kamida {MIN_PASSWORD_LEN} belgi bo'lsin (schemas.py qoidasi).")

    url = _require("MIGRATION_DATABASE_URL")
    engine = create_async_engine(url, echo=False)

    try:
        async with engine.begin() as conn:
            """
            ⛔ IDEMPOTENT: `auth_create_user` telefon band bo'lsa `NULL`
               qaytaradi (`ON CONFLICT DO NOTHING`). Skriptni ikki marta
               yurgizish MAVJUD hisobning parolini ALMASHTIRMAYDI — aks
               holda tasodifiy takroriy ishga tushirish ishlab turgan
               tizimdan odamni chiqarib yuborardi.
            """
            row = await conn.execute(
                text(
                    "SELECT auth_create_user(:phone, :hash, :name, :locale, true) AS id",
                ),
                {
                    "phone": phone,
                    "hash": hash_password(password),
                    "name": full_name,
                    "locale": locale,
                },
            )
            created = row.scalar_one_or_none()

            if created is None:
                existing = await conn.execute(
                    text(
                        "SELECT id, is_platform_admin FROM users WHERE phone_e164 = :phone",
                    ),
                    {"phone": phone},
                )
                found = existing.one_or_none()
                if found is None:
                    sys.exit("⛔ Hisob yaratilmadi va topilmadi ham — DB holatini tekshiring.")
                print(
                    f"Bu telefon allaqachon band: {phone} "
                    f"(platforma admini: {found.is_platform_admin}). Hech nima o'zgartirilmadi.",
                )
                return

            print(f"Platforma admini yaratildi: {phone}")
            print(f"  id: {created}")
            print("  ⛔ Parol BIR MARTALIK — birinchi kirishda almashtiriladi.")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
