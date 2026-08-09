"""`occupancy_events` va `zone_reviews` O'ZGARMASLIGI — xulq bo'yicha isbot (D-12).

=============================================================================
NEGA BU FAYL `test_audit_immutable.py` DAN BOSHQACHA YOZILADI.

`audit_log` da o'zgarmaslik TO'RT QATLAMDA yashaydi va ularning ikkitasi
JIMGINA ishlaydi: egaga qarshi `UPDATE`/`DELETE` xato TASHLAMAYDI, ular
`UPDATE 0` qaytaradi (chunki `audit_log` da UPDATE/DELETE uchun policy
YO'Q). Shuning uchun u yerda `pytest.raises` ATAYIN ishlatilmaydi.

Bu yerda TESKARI: kafolat TRIGGER bilan qo'yilgan, ya'ni u BALAND OVOZDA
ishlaydi — har qanday rol uchun `RAISE EXCEPTION`. Ikkala jadvalda ham
`owner_bootstrap` policy'si bor (`FOR ALL ... USING (true)`), ya'ni ega
qatorlarni KO'RADI va uni to'xtatadigan yagona narsa — qo'riqchi.
Aynan shuning uchun testlar `sbozor_owner` bilan yoziladi: `sbozor_app`
bilan sinash ZAIFROQ bo'lardi (RLS qatorni yashirsa urinish 0 qatorga
tegib, jimgina "muvaffaqiyatli" tugardi va biz butunlay boshqa mexanizmni
o'lchagan bo'lardik — `test_market_delete_guard.py::
test_active_market_cannot_be_deleted_by_raw_sql` da o'rnatilgan qoida).
=============================================================================

TO'RT DA'VO VA HAR BIRI ALOHIDA BUZILISHI MUMKIN:

  1. `UPDATE` rad etiladi — javobni MOSLASHTIRISH yo'li yopiq;
  2. `DELETE` rad etiladi — noqulay dalilni YO'Q QILISH yo'li yopiq;
  3. `INSERT` O'TADI — qo'riqchi hamma narsani bloklamaydi (NAZORAT HOLATI,
     usiz "hech nima yozilmayapti" ni "o'zgarmaslik ishlayapti" dan ajratib
     bo'lmasdi);
  4. Rad etilgan `UPDATE` `audit_log` ga qator QOLDIRMAYDI — Postgres ning
     trigger tartibi (`BEFORE` `AFTER` dan oldin) shuni beradi va rad
     etilgan urinish "o'zgardi" deb yozilmasin.

BESHINCHI DA'VO — QORALAMA ISTISNOSI FAQAT `DELETE` GA TEGISHLI:
qoralama bozorda ham `UPDATE` rad etiladi. Bu `tariff_past_immutable()`
dan farqli (u istisnoni IKKALA amalga ham beradi) va farq o'lchanadi.

=============================================================================
FAYLNING IKKINCHI YARMI — D-17 NING QOLGAN IKKI STRUKTURAVIY HIMOYASI.

O'zgarmaslik (D-17.4) ko'r auditning BESH himoyasidan biri
(`05-PATTERNS.md` §S-6) va qolgan ikkitasi AYNAN shu sinfda: ular ham
«DB rad etadi» shaklida ishlaydi, ilova qatlamining odob-axloqiga
tayanmaydi va ular ham SXEMADA yashaydi. Shuning uchun ular shu yerda,
yonma-yon o'lchanadi:

  * D-17.3 — «ko'r audit, lekin javob ko'rsatilgan» qatori YOZIB
    BO'LMAYDI (`CHECK`), VA uni `queue_kind` nusxasini yolg'on yozib
    chetlab o'tish ham MUMKIN EMAS (kompozit FK langari);
  * BIR HODISA — BIR NAVBAT: ikkinchi topshiriq `UNIQUE` bilan rad
    etiladi, ya'ni bitta zona nazoratchiga ikki marta ko'rinmaydi va
    uning ikkinchi javobi aniqlik hisobotiga ikkinchi marta kirmaydi.

Ularning SXEMADAGI shakli `tests/tenancy/test_occupancy_domain_meta.py`
da qulflangan; bu yerda XULQ o'lchanadi va ikkalasi ham kerak.
=============================================================================
"""

from __future__ import annotations

from uuid import UUID

import psycopg
import pytest
from fixtures.market_domain import MarketDomainSeed
from fixtures.nvr_domain import nvr_rows
from fixtures.occupancy_domain import MODEL_VERSION, OccupancyDomainSeed, occupancy_rows
from fixtures.snapshot_domain import snapshot_rows
from fixtures.two_markets import TwoMarketSeed
from psycopg import Connection
from psycopg.rows import TupleRow

SET_MARKET = "SELECT set_config('app.market_id', %s, false)"

AUDIT_COUNT = "SELECT count(*) FROM audit_log WHERE table_name = %s"

SECOND_MODEL_VERSION = f"{MODEL_VERSION}-v2"
"""Nazorat `INSERT` i uchun IKKINCHI model nomi.

`UNIQUE (market_id, snapshot_id, camera_zone_id, model_version)` aynan shu
holatni ruxsat etadi va bu tasodif emas — «qayta ishlash YANGI QATOR»
qoidasining (D-12, §E.15) bevosita natijasi. Ya'ni nazorat holati bir
vaqtda ikkinchi da'voni ham o'lchaydi: raqobatlashuvchi verdikt yozish
YO'LI OCHIQ.
"""


def _rows(conn: Connection[TupleRow], sql: str, params: tuple[object, ...]) -> int:
    row = conn.execute(sql, params).fetchone()
    assert row is not None
    return int(row[0])


def _insert_second_verdict(conn: Connection[TupleRow], occupancy: OccupancyDomainSeed) -> None:
    """Mavjud kadr+zona uchun IKKINCHI model verdiktini yozadi (nazorat holati)."""
    a = occupancy.market_a
    row = conn.execute(
        "SELECT snapshot_id, camera_zone_id, business_date, slot_time, zone_version "
        "FROM occupancy_events WHERE id = %s",
        (str(a.occupied_event_id),),
    ).fetchone()
    assert row is not None, "seed hodisasi topilmadi"
    conn.execute(
        "INSERT INTO occupancy_events "
        "(market_id, snapshot_id, camera_zone_id, business_date, slot_time, "
        " verdict, confidence, model_version, thresholds_version, zone_version) "
        "VALUES (%s, %s, %s, %s, %s, 'empty', 0.7100, %s, 1, %s)",
        (
            str(a.market_id),
            str(row[0]),
            str(row[1]),
            row[2],
            row[3],
            SECOND_MODEL_VERSION,
            row[4],
        ),
    )


def _set_market_active(conn: Connection[TupleRow], market_id: UUID, *, active: bool) -> None:
    conn.execute("UPDATE markets SET is_active = %s WHERE id = %s", (active, str(market_id)))


def test_occupancy_event_cannot_be_updated_or_deleted(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    migrated: None,
) -> None:
    """AI javobi TAHRIRLANMAYDI va O'CHIRILMAYDI (D-12, T-05-17).

    =========================================================================
    Model bergan verdikt — O'LCHOVNING KIRISHI. Uni tahrirlash mumkin bo'lsa
    «model qanchalik to'g'ri edi?» savoliga javob beradigan yagona ma'lumot
    yo'qolardi va aniqlik hisoboti o'z natijasini o'zi yozardi.

    Xato xabarida `TG_OP` BO'LISHI tekshiriladi: ikki xil urinish ikki xil
    tahdid modelidan keladi (`UPDATE` natijani MOSLASHTIRADI, `DELETE`
    noqulay dalilni YO'Q QILADI) va log'da ular ajralib turishi kerak.
    =========================================================================
    """
    with (
        nvr_rows(sync_owner_conn, two_markets) as nvr,
        snapshot_rows(sync_owner_conn, nvr) as snaps,
        occupancy_rows(sync_owner_conn, two_markets, market_domain, snaps) as occupancy,
    ):
        event_id = str(occupancy.market_a.occupied_event_id)

        with pytest.raises(psycopg.errors.RaiseException) as update_error:
            sync_owner_conn.execute(
                "UPDATE occupancy_events SET verdict = 'empty' WHERE id = %s", (event_id,)
            )
        assert "append-only" in str(update_error.value)
        assert "UPDATE" in str(update_error.value), (
            f"xato xabarida `TG_OP` yo'q: {update_error.value!r} — ikki xil "
            "urinishni log'da ajratib bo'lmasdi"
        )

        with pytest.raises(psycopg.errors.RaiseException) as delete_error:
            sync_owner_conn.execute("DELETE FROM occupancy_events WHERE id = %s", (event_id,))
        assert "DELETE" in str(delete_error.value)

        # HOLAT O'ZGARMAGANINI ALOHIDA o'lchash: istisno ko'tarilib, qator
        # baribir o'zgargan bo'lishi mumkin edi (trigger `AFTER` bo'lib
        # qolgan taqdirda).
        row = sync_owner_conn.execute(
            "SELECT verdict FROM occupancy_events WHERE id = %s", (event_id,)
        ).fetchone()
        assert row is not None and row[0] == "occupied", (
            f"hodisa qatori o'zgardi yoki o'chdi ({row}) — qo'riqchi `BEFORE` "
            "emas, `AFTER` bo'lib qolgan bo'lishi mumkin"
        )


def test_zone_review_cannot_be_updated_or_deleted(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    migrated: None,
) -> None:
    """Nazoratchi javobi OSHKOR QILINGANDAN KEYIN ham qulflangan (D-17.4).

    Ko'r auditda nazoratchi javob berganidan KEYIN AI javobi ko'rsatiladi.
    Javob o'sha paytda tahrirlanishi mumkin bo'lsa xolis o'lchov ma'nosini
    BUTUNLAY yo'qotardi — «to'g'rilash mumkin bo'lgan o'lchov o'lchov emas».
    Nosozlik jimgina bo'lardi: hamma qator to'g'ri ko'rinardi va aniqlik
    foizi o'z-o'zidan o'sardi.
    """
    with (
        nvr_rows(sync_owner_conn, two_markets) as nvr,
        snapshot_rows(sync_owner_conn, nvr) as snaps,
        occupancy_rows(sync_owner_conn, two_markets, market_domain, snaps) as occupancy,
    ):
        review_id = str(occupancy.market_a.blind_review_id)

        with pytest.raises(psycopg.errors.RaiseException) as update_error:
            sync_owner_conn.execute(
                "UPDATE zone_reviews SET human_verdict = 'empty' WHERE id = %s", (review_id,)
            )
        assert "append-only" in str(update_error.value)
        assert "UPDATE" in str(update_error.value)

        with pytest.raises(psycopg.errors.RaiseException) as delete_error:
            sync_owner_conn.execute("DELETE FROM zone_reviews WHERE id = %s", (review_id,))
        assert "DELETE" in str(delete_error.value)

        row = sync_owner_conn.execute(
            "SELECT human_verdict FROM zone_reviews WHERE id = %s", (review_id,)
        ).fetchone()
        assert row is not None and row[0] == "occupied", (
            f"javob qatori o'zgardi yoki o'chdi ({row})"
        )


def test_insert_still_works(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    migrated: None,
) -> None:
    """NAZORAT HOLATI: qo'riqchi HAMMA NARSANI bloklamaydi.

    =========================================================================
    ⚠ BU TEST BO'LMASA YUQORIDAGI IKKALASI HAM «hech nima yozilmayapti» ni
    «o'zgarmaslik ishlayapti» dan AJRATA OLMASDI. `BEFORE INSERT OR UPDATE
    OR DELETE` deb yozilgan qo'riqchi ikkala testni ham yashil qoldirardi,
    lekin butun quvurni jimgina o'ldirardi: 05-08 birorta hodisa yoza
    olmasdi va nosozlik faqat kunlik hisobot bo'sh chiqqanda ko'rinardi.

    Nazorat holati bir vaqtda IKKINCHI da'voni ham o'lchaydi: `INSERT`
    AYNAN o'sha kadr va o'sha zona uchun, LEKIN boshqa `model_version`
    bilan bajariladi — ya'ni «qayta ishlash YANGI QATOR» yo'li (D-12,
    §E.15) haqiqatan ochiq.
    =========================================================================
    """
    with (
        nvr_rows(sync_owner_conn, two_markets) as nvr,
        snapshot_rows(sync_owner_conn, nvr) as snaps,
        occupancy_rows(sync_owner_conn, two_markets, market_domain, snaps) as occupancy,
    ):
        before = _rows(
            sync_owner_conn,
            "SELECT count(*) FROM occupancy_events WHERE market_id = %s",
            (str(occupancy.market_a.market_id),),
        )

        _insert_second_verdict(sync_owner_conn, occupancy)

        after = _rows(
            sync_owner_conn,
            "SELECT count(*) FROM occupancy_events WHERE market_id = %s",
            (str(occupancy.market_a.market_id),),
        )
        assert after == before + 1, (
            f"nazorat `INSERT` i o'tmadi ({before} -> {after}) — qo'riqchi "
            "`INSERT` ni ham bloklayapti va butun bandlik quvuri o'lik"
        )


def test_rejected_update_leaves_no_audit_row(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    migrated: None,
) -> None:
    """Rad etilgan `UPDATE` `audit_log` ga qator QOLDIRMAYDI (trigger tartibi).

    =========================================================================
    `zone_reviews` DA IKKALA TRIGGER HAM BOR: audit (`AFTER`) va o'zgarmaslik
    (`BEFORE`). Postgres qoidasi (`helpers.py::attach_immutability_trigger`)
    aynan kerakli natijani beradi — `BEFORE` `AFTER` dan oldin yuradi, ya'ni
    rad etilgan urinish auditga TUSHMAYDI.

    Nega bu muhim: audit jurnali «kim nimani o'zgartirdi» savoliga javob
    beradi. Rad etilgan urinish yozilsa jurnal HECH QACHON SODIR BO'LMAGAN
    o'zgarishlarni ko'rsatardi va nazoratchining javobi «tahrirlangan»
    bo'lib ko'rinardi — ya'ni audit dalilning O'ZINI shubhaga qo'yardi.

    ⚠ SANOQ TENANT KONTEKSTI OSTIDA o'qiladi: `audit_read` policy'si
    tenant-scoped va u jadval EGASIGA ham qo'llanadi (FORCE). Kontekstsiz
    sanoq har ikkala o'lchovda ham 0 bo'lardi va test «o'zgarmadi» degan
    BO'SH da'voni isbotlagan bo'lardi.
    =========================================================================
    """
    with (
        nvr_rows(sync_owner_conn, two_markets) as nvr,
        snapshot_rows(sync_owner_conn, nvr) as snaps,
        occupancy_rows(sync_owner_conn, two_markets, market_domain, snaps) as occupancy,
    ):
        market_id = str(occupancy.market_a.market_id)
        sync_owner_conn.execute(SET_MARKET, (market_id,))

        before = _rows(sync_owner_conn, AUDIT_COUNT, ("zone_reviews",))
        assert before > 0, (
            "`zone_reviews` uchun audit qatori umuman yo'q — seed `INSERT` i "
            "auditga tushmagan, ya'ni bu test hech nimani o'lchamaydi"
        )

        with pytest.raises(psycopg.errors.RaiseException):
            sync_owner_conn.execute(
                "UPDATE zone_reviews SET human_verdict = 'empty' WHERE id = %s",
                (str(occupancy.market_a.blind_review_id),),
            )

        after = _rows(sync_owner_conn, AUDIT_COUNT, ("zone_reviews",))
        assert after == before, (
            f"rad etilgan `UPDATE` dan keyin audit qatorlari {before} -> {after} "
            "bo'ldi — qo'riqchi `AFTER` bo'lib qolgan yoki audit triggeri "
            "undan OLDIN ishlagan"
        )


def test_draft_market_exception_covers_delete_only(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    migrated: None,
) -> None:
    """QORALAMA ISTISNOSI FAQAT `DELETE` GA TEGISHLI — `UPDATE` baribir rad etiladi.

    =========================================================================
    ⚠ BU TEST ISTISNONING CHEGARASINI O'LCHAYDI VA U `tariff_past_immutable()`
    DAN FARQ QILADIGAN YAGONA JOY.

    `tariffs` qo'riqchisi qoralama bozorni IKKALA amaldan ham (`UPDATE` va
    `DELETE`) ozod qiladi. Bu yerda istisno FAQAT `DELETE` ga berilgan va
    sabab aniq: istisno `market_delete_draft()` kaskadi UCHUN mavjud
    (`0019`), tahrirlash uchun emas. Istisnoni `UPDATE` ga ham kengaytirish
    D-12 ni qoralama bozorlarda jimgina bo'shatardi va kelajakda kimdir
    «test bozorida javobni to'g'rilash» yo'lini shu yerdan ochardi.

    `DELETE` ning qoralamada O'TISHI alohida o'lchanadi —
    `test_market_delete_guard.py::test_draft_market_deletion_covers_the_
    occupancy_domain` da, funksiyani HAQIQATAN chaqirib.
    =========================================================================
    """
    with (
        nvr_rows(sync_owner_conn, two_markets) as nvr,
        snapshot_rows(sync_owner_conn, nvr) as snaps,
        occupancy_rows(sync_owner_conn, two_markets, market_domain, snaps) as occupancy,
    ):
        market_id = occupancy.market_a.market_id
        event_id = str(occupancy.market_a.occupied_event_id)

        _set_market_active(sync_owner_conn, market_id, active=False)
        try:
            with pytest.raises(psycopg.errors.RaiseException) as error:
                sync_owner_conn.execute(
                    "UPDATE occupancy_events SET verdict = 'empty' WHERE id = %s", (event_id,)
                )
            assert "append-only" in str(error.value)
            assert "UPDATE" in str(error.value)
        finally:
            # Bozor FAOL holatga qaytariladi: tozalash uni baribir qoralamaga
            # tushiradi, lekin bu yerda holatni ATAYIN tiklaymiz — testlar
            # bir-birining yon ta'sirini meros qilib olmasin.
            _set_market_active(sync_owner_conn, market_id, active=True)


# ===========================================================================
# D-17 NING QOLGAN IKKI STRUKTURAVIY HIMOYASI (fayl docstringining oxiri)
# ===========================================================================


def test_blind_audit_row_cannot_show_the_ai_verdict(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    migrated: None,
) -> None:
    """`queue_kind='blind_audit'` + `shown_ai_verdict=true` -> `CheckViolation` (D-17.3).

    =========================================================================
    ANKORLASH — KO'R AUDITNING ENG JIM NOSOZLIGI.

    Nazoratchiga AI javobi ko'rsatilsa, uning javobi model bilan rozi
    bo'lish tomon SILJIYDI (anchoring). O'shanda aniqlik hisoboti modelni
    emas, MODELNING O'ZINI TASDIQLAGAN insonni o'lchardi va foiz sun'iy
    o'sardi — hech qanday xato, hech qanday alert, hamma qator "to'g'ri".

    `CHECK` bu holatni IFODALAB BO'LMAYDIGAN qiladi: yozib bo'lmaydigan
    holatni "unutish" ham mumkin emas. Klient qatlami (`AnswerRequest` da
    maydonning O'ZI e'lon qilinmagan, 05-10) — BIRINCHI qatlam; bu —
    IKKINCHI va u kod qatlami buzilgan taqdirda ham turadi (T-05-44).
    =========================================================================
    """
    with (
        nvr_rows(sync_owner_conn, two_markets) as nvr,
        snapshot_rows(sync_owner_conn, nvr) as snaps,
        occupancy_rows(sync_owner_conn, two_markets, market_domain, snaps) as occupancy,
    ):
        b = occupancy.market_b
        # B bozorining ko'r audit topshirig'i JAVOBSIZ, ya'ni unga javob
        # yozish `uq_zone_reviews_review_assignment_id` ni buzmaydi va biz
        # AYNAN `CHECK` ni o'lchaymiz.
        assignment_id = _unanswered_blind_assignment(sync_owner_conn, b.market_id)

        with pytest.raises(psycopg.errors.CheckViolation) as error:
            sync_owner_conn.execute(
                "INSERT INTO zone_reviews "
                "(market_id, review_assignment_id, queue_kind, shown_ai_verdict, "
                " human_verdict, reviewer_id) "
                "VALUES (%s, %s, 'blind_audit', true, 'occupied', %s)",
                (
                    str(b.market_id),
                    str(assignment_id),
                    str(two_markets.market_b.admin_user_id),
                ),
            )
        assert error.value.sqlstate == "23514", (
            f"kutilgan `23514` (check_violation), olindi {error.value.sqlstate}"
        )


def test_lying_queue_kind_copy_is_rejected(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    migrated: None,
) -> None:
    """`queue_kind` NUSXASINI YOLG'ON yozib `CHECK` ni chetlab o'tib bo'lmaydi.

    =========================================================================
    ⚠ YUQORIDAGI TEST YOLG'IZ O'ZI YETARLI EMAS VA SABAB TUZILMAVIY.

    `CHECK` boshqa jadvalni o'qiy olmaydi, ya'ni D-17.3 sharti
    `zone_reviews` dagi DENORMALIZATSIYA qilingan `queue_kind` ga tayanadi.
    Ko'r audit topshirig'iga `queue_kind = 'uncertain'` deb javob yozish
    shartni YOLG'ONGA aylantirardi va `shown_ai_verdict = true` bemalol
    o'tardi — ya'ni kafolat BITTA `INSERT` bilan chetlab o'tilardi.

    Kompozit FK `(review_assignment_id, queue_kind)` ni
    `review_assignments (id, queue_kind)` langariga qadaydi: nusxa
    manbadan FARQ QILA OLMAYDI. Bu 4-fazadagi `uq_snapshots_billable_anchor`
    naqshining aynan takrori — denormalizatsiya haqiqat chegarasini
    bo'shatish uchun bahona emas.
    =========================================================================
    """
    with (
        nvr_rows(sync_owner_conn, two_markets) as nvr,
        snapshot_rows(sync_owner_conn, nvr) as snaps,
        occupancy_rows(sync_owner_conn, two_markets, market_domain, snaps) as occupancy,
    ):
        b = occupancy.market_b
        assignment_id = _unanswered_blind_assignment(sync_owner_conn, b.market_id)

        with pytest.raises(psycopg.errors.ForeignKeyViolation) as error:
            sync_owner_conn.execute(
                "INSERT INTO zone_reviews "
                "(market_id, review_assignment_id, queue_kind, shown_ai_verdict, "
                " human_verdict, reviewer_id) "
                "VALUES (%s, %s, 'uncertain', true, 'occupied', %s)",
                (
                    str(b.market_id),
                    str(assignment_id),
                    str(two_markets.market_b.admin_user_id),
                ),
            )
        assert error.value.sqlstate == "23503"
        assert "queue_kind_anchor" in str(error.value), (
            f"xato boshqa chet el kalitidan keldi: {error.value!r} — langar "
            "emas, boshqa konstrayt ishlagan bo'lishi mumkin"
        )


def test_one_event_cannot_get_a_second_assignment(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    migrated: None,
) -> None:
    """Bir hodisa ikki navbatda bo'la olmaydi -> `UniqueViolation` (§S-6).

    =========================================================================
    POYGA DB'GA TOPSHIRILGAN (`nvr_repo.py:509-517` naqshi).

    Ko'r audit tortish (`audit_draw`) va noaniq navbat qurish IKKI ALOHIDA
    job va ular bir vaqtda ishlashi mumkin. «Avval tekshir, keyin yoz»
    ikkalasiga ham bo'sh holatni ko'rsatardi va bitta hodisa uchun IKKITA
    yozuv tug'ilardi — nazoratchi bir zonani ikki marta ko'rardi va uning
    ikkinchi javobi aniqlik hisobotiga IKKINCHI marta kirardi.

    ⚠ TARTIB MAJBURIY (§C.8.3): avval ko'r audit namunasi tortiladi, KEYIN
    noaniq navbat quriladi. Teskari tartibda bu `UNIQUE` audit doirasidan
    «noaniq» larni chiqarib tashlardi va o'lchangan aniqlik sun'iy
    ko'tarilardi.
    =========================================================================
    """
    with (
        nvr_rows(sync_owner_conn, two_markets) as nvr,
        snapshot_rows(sync_owner_conn, nvr) as snaps,
        occupancy_rows(sync_owner_conn, two_markets, market_domain, snaps) as occupancy,
    ):
        a = occupancy.market_a

        with pytest.raises(psycopg.errors.UniqueViolation) as error:
            sync_owner_conn.execute(
                "INSERT INTO review_assignments "
                "(market_id, occupancy_event_id, audit_round_id, queue_kind, purpose) "
                "VALUES (%s, %s, NULL, 'uncertain', 'train')",
                (str(a.market_id), str(a.occupied_event_id)),
            )
        assert error.value.sqlstate == "23505"
        assert "occupancy_event_id" in str(error.value), (
            f"xato boshqa noyoblik konstraytidan keldi: {error.value!r}"
        )


def _unanswered_blind_assignment(conn: Connection[TupleRow], market_id: UUID) -> UUID:
    """Javobi HALI yozilmagan ko'r audit topshirig'i.

    Seed B bozorida javob yozadi, shuning uchun bu yordamchi YANGI hodisa
    va YANGI topshiriq quradi — mavjudini qayta ishlatish
    `uq_zone_reviews_review_assignment_id` ga urilib, biz o'lchamoqchi
    bo'lgan konstrayt o'rniga BOSHQASINI o'lchagan bo'lardik.
    """
    row = conn.execute(
        "SELECT snapshot_id, camera_zone_id, business_date, slot_time, zone_version, "
        "       (SELECT id FROM audit_rounds WHERE market_id = %s LIMIT 1) "
        "FROM occupancy_events WHERE market_id = %s LIMIT 1",
        (str(market_id), str(market_id)),
    ).fetchone()
    assert row is not None, "B bozorida bandlik hodisasi yo'q"

    event_row = conn.execute(
        "INSERT INTO occupancy_events "
        "(market_id, snapshot_id, camera_zone_id, business_date, slot_time, "
        " verdict, confidence, model_version, thresholds_version, zone_version) "
        "VALUES (%s, %s, %s, %s, %s, 'uncertain', 0.5000, %s, 1, %s) RETURNING id",
        (
            str(market_id),
            str(row[0]),
            str(row[1]),
            row[2],
            row[3],
            f"{MODEL_VERSION}-probe",
            row[4],
        ),
    ).fetchone()
    assert event_row is not None

    assignment_row = conn.execute(
        "INSERT INTO review_assignments "
        "(market_id, occupancy_event_id, audit_round_id, queue_kind, purpose) "
        "VALUES (%s, %s, %s, 'blind_audit', 'train') RETURNING id",
        (str(market_id), str(event_row[0]), str(row[5])),
    ).fetchone()
    assert assignment_row is not None
    assignment_id: UUID = assignment_row[0]
    return assignment_id
