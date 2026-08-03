"""core-api konfiguratsiyasi — 12-faktor uslubida, muhit o'zgaruvchilaridan.

Sirlar (JWT_SECRET, DB parollari) HECH QACHON kodda yoki repoda saqlanmaydi —
ular faqat muhitdan keladi (`.env` gitignore'da, `.env.example` da faqat
kalit nomlari).
"""

from __future__ import annotations

from functools import lru_cache

from cryptography.fernet import Fernet
from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# PyJWT 2.11+ HS256 uchun kalit uzunligini majburiy tekshiradi
# (RFC 7518 §3.2: kalit >= hash chiqishi = 256 bit = 32 bayt).
MIN_JWT_SECRET_BYTES = 32


class Settings(BaseSettings):
    """core-api ish vaqti sozlamalari."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Ma'lumotlar bazasi ---
    # ILOVA roli (sbozor_app): NOSUPERUSER + NOBYPASSRLS.
    # Bu yerga `postgres` superuseri berilsa tenant izolyatsiyasi butunlay
    # yo'qoladi va hech bir test buni ko'rsatmaydi.
    database_url: str
    # DDL egasi (sbozor_owner) — faqat Alembic `migrate` jobida ishlatiladi.
    migration_database_url: str = ""

    # --- Kesh / navbat ---
    valkey_url: str

    # --- Auth ---
    jwt_secret: str
    jwt_issuer: str = "sbozor"
    jwt_audience: str = "sbozor-api"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30
    # Dev'da HTTP -> false; prod'da (TLS ortida) true bo'lishi SHART.
    cookie_secure: bool = False

    # --- Excel import chegaralari (02-12, A7) ---
    #
    # Chegaralar SOZLANADIGAN, chunki A7 ning o'zi ularni taxmin deb
    # belgilaydi: "1000 rastadan kattaroq bozor kelganda chegaraga
    # urilinadi (sozlanadigan qilinsin)". Standart qiymatlar
    # `app/services/xlsx_reader.py` dagi modul konstantalari bilan AYNAN
    # bir xil va o'sha yerda `test_default_limits_match_the_documented_
    # values` bilan qulflangan — ya'ni bittasini o'zgartirish ikkinchisini
    # jimgina eskirtira olmaydi.
    #
    # Ikkita hajm chegarasi MUSTAQIL va ikkalasi ham majburiy:
    # `import_max_upload_bytes` — tarmoqdan kelgan XOM bayt (`.xlsx` = ZIP),
    # `import_max_uncompressed_bytes` — o'sha ZIP OCHILGANDAGI hajmi.
    # 1 MB fayl 10 GB ga ochilishi mumkin, ya'ni birinchisi ikkinchisidan
    # hech qanday himoya bermaydi (T-02-88).
    import_max_upload_bytes: int = 5 * 1024 * 1024
    import_max_uncompressed_bytes: int = 50 * 1024 * 1024
    import_max_rows: int = 5_000
    import_max_cols: int = 32
    import_max_sheets: int = 8
    import_max_zip_entries: int = 200

    # Xodimlar rosteri (02-24, MARKET-07) — `import_max_rows` DAN ALOHIDA
    # va ATAYIN ancha tor. Ikki mustaqil sabab:
    #
    #   1. HAJM: xodimlar ro'yxati o'nlab kishilik (Karmanada ~10–30),
    #      rastalar ro'yxati esa mingtacha. Bitta chegara ikkalasiga ham
    #      to'g'ri kelmaydi.
    #   2. NARX VA YUZA: har qator Argon2id hash'lash talab qiladi (CPU
    #      bo'yicha ATAYIN qimmat) va har qator platformadagi telefon
    #      band-emasligini oshkor qiladi (T-02-181). 5000 qatorli fayl
    #      butun ishchini bloklab, bir so'rovda 5000 raqamni sanab
    #      chiqish imkonini berardi.
    import_max_staff_rows: int = 200

    # --- NVR rekvizitlari (03-04, SC#4) ---
    #
    # Shifr kaliti `JWT_SECRET` DAN ALOHIDA va bu ATAYIN — ikki xil xavf
    # modeli. JWT kaliti almashtirilsa sessiyalar tushadi (arzon, o'z-o'zidan
    # tuzaladi); shifr kaliti almashtirilsa MA'LUMOT YO'QOLADI (qimmat,
    # tuzalmaydi). Bitta sirdan ikkalasiga foydalanish birinchisining
    # arzon rotatsiyasini ikkinchisining qimmat rotatsiyasiga bog'lab
    # qo'yardi.
    #
    # STANDART QIYMAT YO'Q va bu ham ATAYIN: bo'sh standart bilan ilova
    # shifrlashsiz KO'TARILARDI va xato faqat birinchi rekvizit yozilganda
    # ko'rinardi (T-03-22 aynan shu xulqni rad etadi).
    #
    # ⚠ TIP `SecretStr`, ODDIY `str` EMAS — va bu O'LCHANGAN qaror.
    #   `BaseSettings` ning `repr` i BARCHA maydonlarni chop etadi, Sentry
    #   esa istisno paytida LOKAL O'ZGARUVCHILARNI yig'adi. `lifespan` da
    #   `settings` aynan lokal o'zgaruvchi (`main.py:99`), ya'ni ilova
    #   ko'tarilayotganda yuz bergan har qanday istisno butun shifr kalitini
    #   Sentry'ga yuborardi. Kalit oshkor bo'lsa BARCHA NVR parollari —
    #   o'tmishdagilari ham — ochiladi, ya'ni bu yagona eng qimmat sir.
    #   `SecretStr` uni `repr` da `**********` ga aylantiradi
    #   (`03-RESEARCH.md` C.10 ni ichki qiymatlar uchun aynan shu tavsiya).
    #   Qiymatga borish faqat `.get_secret_value()` orqali — ya'ni chegara
    #   grep bilan topiladigan va ko'zga tashlanadigan bo'ladi.
    nvr_credential_key: SecretStr
    # Iste'foga chiqqan kalitlar, VERGUL bilan ajratilgan (ixtiyoriy).
    # Rotatsiya hali bo'lmagan o'rnatmada bo'sh — majburiy qilinsa har bir
    # yangi o'rnatma soxta qiymat yozishga majbur bo'lardi.
    # Semantikasi: `app/security/secrets.py::build_cipher` — birinchi kalit
    # YOZADI, hammasi O'QIYDI. Tip yuqoridagi bilan bir xil sababdan
    # `SecretStr`: bu ham AYNAN o'sha kalit materiali.
    nvr_credential_keys_retired: SecretStr = SecretStr("")

    # --- Kuzatuv ---
    sentry_dsn: str = ""
    log_level: str = "info"

    @field_validator("nvr_credential_key")
    @classmethod
    def _validate_nvr_credential_key(cls, value: SecretStr) -> SecretStr:
        """Kalit formatini ISHGA TUSHISHDA tekshiradi (`_validate_jwt_secret` naqshi).

        Noto'g'ri kalit bilan ilova ko'tarilib, birinchi kamera qo'shilganda
        yiqilishi eng yomon variant bo'lardi: xato NVR bilan bog'liqday
        ko'rinardi va operator tarmoqni, parolni va NVR ni tekshirib
        vaqt yo'qotardi.

        Xato matni kalitning O'ZINI TAKRORLAMAYDI — faqat format talabi va
        hosil qilish buyrug'i beriladi.

        ⚠ O'LCHANGAN CHEKLOV, YASHIRILMAYDI: pydantic ning O'ZI
          `ValidationError.__str__` ga `input_value=...` ni qo'shadi, ya'ni
          RAD ETILGAN qiymat baribir xabarga tushadi. Bu bizning matnimizga
          bog'liq emas va uni yozib bo'lmaydi: `SecretStr` ham, `mode=
          "after"` model validatori ham buni to'sib qololmadi (ikkalasi ham
          empirik sinaldi — pydantic XOM kiritmani chop etadi). Xuddi shu
          xulq `_validate_jwt_secret` da ham bor, ya'ni bu shu maydon
          kiritgan yangi teshik emas.
          Amaliy oqibati TOR: chop etiladigan qiymat ta'rifi bo'yicha
          ISHLAMAYDIGAN kalit va bu yo'l faqat ilova ko'tarilmaganda ochiladi
          (Sentry hali sozlanmagan — `main.py` uni sozlamalardan KEYIN
          ishga tushiradi, ya'ni xabar faqat konteyner stderr'iga boradi).
          `SecretStr` esa MUVAFFAQIYATLI ko'tarilgan holatdagi ancha kengroq
          yo'lni — `repr(settings)` va Sentry ning lokal o'zgaruvchilar
          yig'ishini — yopadi.
        """
        try:
            Fernet(value.get_secret_value().encode())
        except (ValueError, TypeError) as exc:
            raise ValueError(
                "NVR_CREDENTIAL_KEY — Fernet kaliti bo'lishi kerak "
                "(base64url, 32 bayt). Hosil qilish: "
                'python -c "from cryptography.fernet import Fernet;'
                'print(Fernet.generate_key().decode())"'
            ) from exc
        return value

    @field_validator("jwt_secret")
    @classmethod
    def _validate_jwt_secret(cls, value: str) -> str:
        if len(value.encode("utf-8")) < MIN_JWT_SECRET_BYTES:
            raise ValueError(
                f"JWT_SECRET kamida {MIN_JWT_SECRET_BYTES} bayt bo'lishi kerak. "
                'Hosil qilish: python -c "import secrets;print(secrets.token_urlsafe(48))"'
            )
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Sozlamalarni bir marta o'qiydi va keshlaydi."""
    # mypy majburiy maydonlarni argument sifatida kutadi, lekin pydantic-settings
    # ularni MUHITDAN to'ldiradi (pydantic mypy plagini atayin yoqilmagan).
    # Yetishmayotgan qiymat ish vaqtida `ValidationError` beradi — bu kutilgan xulq.
    return Settings()  # type: ignore[call-arg]
