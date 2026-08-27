"""W0-3 O'LCHOVI — ko'r audit namunasi kengaytmasiz qayta chiqariladimi.

=============================================================================
BU FAYL BIRORTA XULQNI HIMOYA QILMAYDI — U BITTA QARORNI O'LCHOV BILAN
QULFLAYDI VA O'SHA QARORNING SABABINI SAQLAYDI.

D-17.1 ko'r auditning birinchi strukturaviy himoyasini talab qiladi:
namunani tortgan odam uni QAYTA CHIZA olmasligi kerak. «Tasodifiy» degan
da'vo tekshirilmasa, u da'voligicha qoladi — talab: boshqa odam o'sha
namunani QAYTA CHIQARA olishi va uning tanlanmaganini ko'rishi.

-----------------------------------------------------------------------------
NEGA IKKI SODDA YECHIM RAD ETILDI (`05-RESEARCH.md` §C.8.1):

  * `ORDER BY random() LIMIT n` — QAYTA CHIQARILMAYDI. Namuna tortilgandan
    keyin uni hech kim tekshira olmaydi, ya'ni «xolis tortildi» da'vosi
    tekshiruvsiz qoladi. Xolislik da'vosi uchun bu yetarli emas.

  * `setseed()` bilan urug'ni SAQLASH — yaxshiroq, lekin HAMON YETARLI
    EMAS: urug'ni TANLAGAN odam uni bir necha marta sinab ko'rishi mumkin
    («bu namunada xato ko'p chiqdi, boshqasini tortaman»). Ya'ni qayta
    chiqarilish ta'minlanadi, XOLISLIK esa yo'q — va aynan xolislik bu
    yerdagi savol.

⛔ SHUNING UCHUN YUQORIDAGI IKKI NOM `tests/fixtures/audit_seed_probe.py`
   NING O'ZIDA — IZOHLARDA HAM — YOZILMAYDI, va bu qoida 3-fazada
   o'lchangan: taqiqlangan literalni skanerlanadigan faylning izohiga
   yozish sodda darvozani o'zini o'zi qizartiradigan qiladi, va o'sha
   holatda yagona «tuzatish» yo'li darvozani BO'SHATISH bo'lardi. Sabab
   shu yerda yashaydi, o'lchov esa u yerda.

TANLANGAN YO'L — HOSILA URUG' + DETERMINISTIK HASH TARTIBI:

    urug' = sha256(market_id || business_date || round_no)
    namuna = ORDER BY sha256((id::text || urug')::bytea) LIMIT n

  * urug' TANLANMAYDI — u uchta biznes faktidan hosila, ya'ni «boshqa
    urug' sinab ko'rish» degan harakatning O'ZI yo'q;
  * namuna QAYTA HISOBLANADI — tekshiruvchi uni o'zi torta oladi;
  * doira MUZLATILADI — `audit_rounds` da `frame_size`,
    `frame_predicate_hash`, `drawn_at` saqlanadi (`0018`).
-----------------------------------------------------------------------------
M-1 — VA AYNAN SHU SABABDAN BU FAYL BOR.

`05-RESEARCH.md` §C.8.1 yuqoridagi tartibni `pgcrypto` ning funksiyasi
bilan yozgan. U BUGUN ISHLAMAYDI: `ops/db/init/00-extensions.sql` bazaga
FAQAT `btree_gist` ni o'rnatadi, ya'ni RESEARCH ning so'rovi
`UndefinedFunction` bilan yiqilardi — va buni `0018` yozilgandan KEYIN
bilib olish QAYTA MIGRATSIYA demakdir.

Uch yo'ldan (`05-PATTERNS.md` §3.1) **A tanlandi**: yadro
`sha256(bytea)` (PostgreSQL >= 11). Ya'ni:

    * `ops/db/init/00-extensions.sql` ga YANGI SATR QO'SHILMAYDI;
    * `0018` da `require_extension()` CHAQIRILMAYDI.

⚠ QAROR FIKR EMAS, O'LCHOV: quyidagi to'rt test uni HAQIQIY
  `postgres:18.4` da tasdiqlaydi. Natija `05-05` da
  `migrations/versions/0018_occupancy_domain.py` ning `audit_rounds`
  docstringiga AYNAN shu nomlar bilan ko'chiriladi
  (`AUDIT_SEED_SHA256_SUPPORTED`, `PGCRYPTO_ABSENT`), va o'sha
  migratsiyaning `pgcrypto`siz bazada muvaffaqiyatli o'tishi qarorning
  IKKINCHI, XULQIY tasdig'i bo'ladi.
=============================================================================
"""

from __future__ import annotations

from collections.abc import Iterator
from urllib.parse import quote_plus

import psycopg
import pytest
from fixtures.audit_seed_probe import (
    SAMPLE_LIMIT,
    AuditSeedProbe,
    create_audit_seed_probe,
    drop_audit_seed_probe,
    sample_ids,
)
from psycopg import Connection
from psycopg.rows import TupleRow
from sqlalchemy.engine import make_url

pytestmark = pytest.mark.tenancy

# Namuna kirishi — uchalasi ham BIZNES FAKTI, tanlov emas. Qiymatlarning
# O'ZI ahamiyatsiz, QADALGANLIGI ahamiyatli (`frames.py:102-103`).
PROBE_MARKET_ID = "1f0a2b3c-4d5e-4f60-8a9b-0c1d2e3f4a5b"
PROBE_BUSINESS_DATE = "2026-08-08"

EXTENSION_FALLBACK = (
    "ZAXIRA VARIANT (M-1): agar yadro hash funksiyasi ishlamasa, `0018` yo B "
    "yo'liga (kengaytma + `require_extension()` + `00-extensions.sql` ga satr) "
    "yoki C yo'liga (tartibni ilovada hisoblab `IN (...)` bilan tortish) "
    "o'tadi. Ikkalasi ham qimmatroq, shuning uchun o'lchov `0018` YOZILISHIDAN "
    "OLDIN qilinadi. Bu satrni `05-05` o'qiydi."
)


@pytest.fixture
def probe(
    sync_owner_conn: Connection[TupleRow],
    migrated: None,
) -> Iterator[AuditSeedProbe]:
    """Zond jadvali — har testdan keyin tozalanadi.

    DDL `sbozor_owner` bilan bajariladi — `sbozor_app` `public` sxemada
    obyekt yarata olmaydi (T-01-06, `test_billable_anchor_probe.py` bilan
    bir xil).
    """
    created = create_audit_seed_probe(sync_owner_conn)
    try:
        yield created
    finally:
        drop_audit_seed_probe(sync_owner_conn)


@pytest.fixture
def second_owner_conn(owner_url: str, _bootstrap_roles: None) -> Iterator[Connection[TupleRow]]:
    """IKKINCHI, MUSTAQIL `sbozor_owner` sessiyasi.

    ⚠ USIZ 3-FAKTNI UMUMAN O'LCHAB BO'LMAYDI. Bitta ulanishda ikki marta
      tortilgan namuna «bir xil sessiya bir xil javob berdi» dan boshqa
      hech nima isbotlamasdi — reja aynan shuning uchun «IKKI ALOHIDA
      sessiyada» deb yozgan. Qayta chiqarilish da'vosi esa BOSHQA ODAM
      haqida, ya'ni boshqa ulanish, boshqa tranzaksiya, boshqa vaqt.

    `conftest.py::sync_owner_conn` ning DSN qurish shakli AYNAN
    takrorlanadi (u yerdagi yordamchi private).
    """
    url = make_url(owner_url)
    dsn = (
        f"postgresql://{quote_plus(url.username or '')}:{quote_plus(url.password or '')}"
        f"@{url.host}:{url.port}/{url.database}"
    )
    with psycopg.connect(dsn, autocommit=True) as conn:
        yield conn


def test_core_sha256_is_callable_without_any_extension(probe: AuditSeedProbe) -> None:
    """1-FAKT — yadro hash funksiyasi kengaytmasiz chaqiriladi.

    Bu W0-3 ning A yo'lini yashil qiladigan yagona shart. Yiqilsa `0018`
    ning shakli o'zgaradi, shuning uchun natija testning NOMIDA emas,
    assert XABARIDA qoladi: `05-05` uni SUMMARY dan o'qiydi.
    """
    assert probe.AUDIT_SEED_SHA256_SUPPORTED, (
        "yadro `sha256(bytea)` chaqirilmadi "
        f"(PostgreSQL: {probe.SERVER_VERSION}).\n\n"
        f"Xato: {probe.FAILURE}\n\n" + EXTENSION_FALLBACK
    )


def test_extension_hash_function_is_absent(probe: AuditSeedProbe) -> None:
    """2-FAKT — NAZORAT HOLATI: kengaytmaning funksiyasi bazada YO'Q.

    ⚠ USIZ 1-FAKT MA'NOSIZ BO'LARDI. Agar kengaytma bazada JIMGINA
      mavjud bo'lsa, «kengaytmasiz ishlaydi» degan xulosa TEKSHIRILMAGAN
      qolardi: hash funksiyasi ishlagan bo'lardi, lekin sabab yadro emas,
      o'sha kengaytma bo'lishi mumkin edi. Bu nazorat holati o'sha yolg'on
      xulosani ajratadi — `test_billable_anchor_probe.py::
      test_generated_stored_column_can_be_unique` bilan bir xil vazifa.

    ⚠ TESKARI YO'NALISH HAM MA'NOLI: kelajakda kimdir
      `00-extensions.sql` ga kengaytma qo'shsa, bu test QIZARADI va qaror
      (A yo'lida qolish yoki B ga o'tish) ATAYIN qayta ko'riladi —
      jimgina siljish yo'q.
    """
    assert probe.PGCRYPTO_ABSENT, (
        "kengaytmaning hash funksiyasi bazada MAVJUD — ya'ni "
        "`00-extensions.sql` o'zgargan yoki baza boshqa yo'l bilan "
        "tayyorlangan. W0-3 ning A yo'li (yadro `sha256`) hamon to'g'ri "
        "bo'lishi mumkin, lekin endi u O'LCHANMAGAN: qarorni ATAYIN qayta "
        "ko'ring (`05-PATTERNS.md` §3.1, uch yo'l)."
    )


def test_same_derived_seed_draws_the_same_sample_in_two_sessions(
    probe: AuditSeedProbe,
    second_owner_conn: Connection[TupleRow],
) -> None:
    """3-FAKT — bir xil uchlik IKKI ALOHIDA SESSIYADA aynan bir xil namuna.

    ⚠ KUTILGAN ID TO'PLAMI BU YERDA HISOBLANIB OLINMAYDI (§S-9). Test
      faqat IKKI CHAQIRUV TENGligini o'lchaydi. Kutilgan to'plamni testda
      qayta hisoblash `ORDER BY` ifodasini testga KO'CHIRISH demakdir —
      va o'shanda test o'z farazining aks-sadosiga aylanardi: ifoda
      noto'g'ri bo'lsa ikkala tomon ham BIRGA noto'g'ri bo'lardi va test
      YASHIL qolardi.

    Tartib ham solishtiriladi (ro'yxat, to'plam emas): «bir xil beshta
    kadr, lekin boshqa navbatda» holati ham qayta chiqarilishning
    buzilishi bo'lardi.
    """
    first = sample_ids(
        probe.conn,
        market_id=PROBE_MARKET_ID,
        business_date=PROBE_BUSINESS_DATE,
        round_no=1,
    )
    second = sample_ids(
        second_owner_conn,
        market_id=PROBE_MARKET_ID,
        business_date=PROBE_BUSINESS_DATE,
        round_no=1,
    )

    # QUYI CHEGARA: bo'sh jadvalda ikkala ro'yxat ham `[]` bo'lardi va
    # tenglik JIMGINA o'tardi (`test_runtime_deps.py:291-302` naqshi).
    assert len(first) == SAMPLE_LIMIT, (
        f"namuna {len(first)} ta kadr qaytardi, kutilgani {SAMPLE_LIMIT} — zond "
        "jadvali to'ldirilmagan, ya'ni quyidagi tenglik hech nimani o'lchamasdi."
    )

    assert first == second, (
        "bir xil hosila urug' IKKI SESSIYADA BOSHQA namuna berdi — namuna "
        "qayta chiqarilmaydi, ya'ni D-17.1 ning himoyasi yo'q.\n"
        f"  1-sessiya: {first}\n"
        f"  2-sessiya: {second}"
    )


def test_a_different_round_number_draws_a_different_sample(probe: AuditSeedProbe) -> None:
    """4-FAKT — NAZORAT HOLATI: tur raqami o'zgarsa namuna ham o'zgaradi.

    ⚠ USIZ 3-FAKT YOLG'ON-YASHIL BERARDI. `ORDER BY` ifodasi urug'ni
      umuman e'tiborga olmasa (masalan `s.value` tushib qolsa), namuna
      HAR DOIM bir xil bo'lardi va 3-fakt mukammal yashil turardi —
      «qayta chiqariladi» degan xulosa esa aslida «urug' ishlamaydi»
      degani bo'lardi.

    Bu tekshiruv ehtimolga tayanmaydi: zond jadvalida 40 kadr bor va ID
    lar QADALGAN, ya'ni natija har yugurishda AYNAN bir xil (`frames.py`
    MAJBURIYAT 2).
    """
    first_round = sample_ids(
        probe.conn,
        market_id=PROBE_MARKET_ID,
        business_date=PROBE_BUSINESS_DATE,
        round_no=1,
    )
    second_round = sample_ids(
        probe.conn,
        market_id=PROBE_MARKET_ID,
        business_date=PROBE_BUSINESS_DATE,
        round_no=2,
    )

    assert set(first_round) != set(second_round), (
        "ikki xil tur AYNI namunani berdi — urug' tartibga TA'SIR "
        "QILMAYAPTI, ya'ni `ORDER BY` ifodasi uni e'tiborga olmayapti "
        f"(ikkala tur ham: {first_round})."
    )
