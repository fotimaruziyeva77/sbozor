"""Tiklash mashqi — MEXANIZM qatlami: dump -> TOZA server -> ma'lumot joyida (D-16a).

=============================================================================
⛔⛔ HALOL CHEGARA — BU TEST `restic` NI UMUMAN ISHLATMAYDI.

`restic` binari `tests` image'ida YO'Q, offsite bucket sozlanmagan va
toza SERVER (VPS) ham yo'q. Ya'ni bu fayl AYNAN quyidagi zanjirni
o'lchaydi va boshqa hech nimani:

    pg_dump --format=custom --compress=0  ->  TOZA postgres konteyneri
                                          ->  pg_restore
                                          ->  ma'lumot JOYIDAMI?

⛔ U «OFFSITE REPODAN TIKLANDI» NI O'LCHAMAYDI. Tiklash mashqining
   ikkinchi qatlami — REAL restic repo'sidan, REAL toza serverda —
   `08-HUMAN-UAT.md` ning bandi, EGASI **Ops**, TETIGI **VPS deploy**.
   U CI'da HECH QACHON bajarilmaydi.

⛔ SHUNING UCHUN BU TESTNI «TO'LIQ TIKLASH ISBOTI» DEB ATASH TAQIQLANADI.
   SC#3 ning «kamida bir marta muvaffaqiyatli tiklandi» imzosi AYNAN
   o'sha UAT bandi bilan qo'yiladi; bu yerdagi o'lchov uni
   REGRESSIYADAN QO'RIQLAYDI, O'RNINI BOSMAYDI.

⛔ Mexanizm qatlamining yashilligi bilan haqiqat qatlamining yo'qligini
   yopish — 3- va 5-fazaning darsi (AI-02 ning `Blocked` bo'lish sababi).
=============================================================================

=============================================================================
⛔⛔ IKKINCHI HALOL CHEGARA — «TIKLANDI» ≠ «ILOVA ISHLAY OLADI».

Bu mashq MA'LUMOTNING ko'chishini o'lchaydi, tiklangan bazaning ILOVA
UCHUN TAYYORLIGINI EMAS. Farq O'LCHANDI (08-08, zond bilan):

    manba     : 44 jadval, 83 policy, `sbozor_app` uchun 163 GRANT
    tiklangan : 44 jadval, 83 policy, `sbozor_app` uchun   0 GRANT

Ya'ni `run-backup.sh` ning `--no-privileges` bayrog'i RLS policy'larini
SAQLAYDI (ular imtiyoz emas, alohida obyekt — pastdagi (2) da'vosi shuni
o'lchaydi), lekin GRANT'larni dumpga UMUMAN qo'ymaydi. Tiklangan bazada
ilova roli har so'rovda `permission denied for table` olardi.

⛔ BU YERDA TUZATILMAYDI VA DA'VO QILINMAYDI: `--no-owner --no-privileges`
   08-05 ning ONGLI qarori va u `tests/unit/test_backup_contract.py` da
   QULFLANGAN. Band `deferred-items.md` ga yozilgan; tabiiy egasi —
   08-19 (runbook), chunki tiklash tartibiga «migratsiyalarni qayta
   yugurtirib GRANT'larni tiklash» qadami qo'shilishi kerak.
=============================================================================

=============================================================================
NEGA BITTA TEST, UCHTA EMAS — VA BU T-08-33 NING BEVOSITA NATIJASI.

Uch da'vo (moliyaviy qatorlar, `pg_policies`, `audit_log`) BITTA dump va
BITTA tiklashdan chiqadi. Ularni uch testga bo'lish `restore_target`
fixture'ini (funksiya qamrovi) UCH MARTA ko'tarardi, ya'ni UCHTA
qo'shimcha postgres konteyneri — xost diski 08-08 paytida 93 % to'la
edi va bu narx hech qanday yangi ma'lumot bermasdi: uchala da'vo ham
AYNAN BIR XIL tiklash natijasini o'lchaydi.

⚠ Har da'vo O'Z xabari bilan keladi, ya'ni yiqilgan mashqda QAYSI qatlam
  yo'qolgani darhol ko'rinadi.
=============================================================================

⚠ MARKER `restore`, `slow` EMAS: `slow` «uzoq SIM stsenariylari» deb
  e'lon qilingan va `npm run test:sim*` uni `sim` bilan juftlab
  filtrlaydi. ⛔ `restore` standart `addopts` dan CHIQARILMAGAN — test
  `npm run test` va `npm run gate` da YUGURADI (`pyproject.toml` dagi
  izoh). Marker faqat NARXNI hujjatlaydi.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import psycopg
import pytest
from fixtures.billing_domain import (
    BillingDomainSeed,
    add_daily_charge,
    add_payment,
    billing_domain_before_day_close,
)
from fixtures.nvr_domain import nvr_rows
from fixtures.occupancy_domain import occupancy_rows
from fixtures.restore_drill import RestoreTarget
from fixtures.snapshot_domain import snapshot_rows

from migrations.entities.policies import TENANT_POLICY_SIGNATURE

if TYPE_CHECKING:
    from collections.abc import Iterator

    from fixtures.market_domain import MarketDomainSeed
    from fixtures.two_markets import TwoMarketSeed
    from psycopg import Connection
    from psycopg.rows import TupleRow

pytestmark = [pytest.mark.restore, pytest.mark.usefixtures("migrated")]

DUMP_PATH = "/tmp/sbozor-restore-drill.dump"  # noqa: S108 - efemer konteyner ichida

PG_DUMP_FLAGS = ("--format=custom", "--compress=0", "--no-owner", "--no-privileges")
"""⛔ `run-backup.sh` NING BAYROQLARI BILAN AYNAN BIR XIL.

Farq qilsa mashq MAHSULOT zaxirasidan BOSHQA shakldagi dumpni tiklardi
va «tiklanadi» da'vosi haqiqiy zaxiraga UMUMAN tegishli bo'lmasdi.

⚠ `--compress=0` — 08-05 ning qarori (siqilgan oqim restic dedup'ini
  o'ldiradi). Bu yerda u NARX emas, MOSLIK uchun: dump shakli bir xil
  bo'lishi kerak.
"""

FINANCIAL_TABLES = ("daily_charges", "payments")
"""FOUND-07 matnidagi «moliyaviy qatorlar» — pul yozuvlari."""

_COUNT = "SELECT count(*) FROM {table}"
_TENANT_POLICIES = (
    "SELECT count(*) FROM pg_policies WHERE schemaname = 'public' AND policyname = %s"
)
_SERVER_MAJOR = "SELECT current_setting('server_version_num')::int / 10000"


class Env:
    """Seed + testda tug'ilgan pul yozuvlari."""

    __slots__ = ("billing", "charge_id", "payment_id")

    def __init__(self, billing: BillingDomainSeed, charge_id: object, payment_id: object) -> None:
        self.billing = billing
        self.charge_id = charge_id
        self.payment_id = payment_id


@pytest.fixture
def env(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
) -> Iterator[Env]:
    """Billing zanjiri + AYNAN BITTA hisob va AYNAN BITTA to'lov.

    =====================================================================
    ⛔ QATORLAR TESTNING O'ZI TOMONIDAN YOZILADI — VA USIZ MASHQ BO'SH
       ROST BO'LARDI.

    «Manba bilan tiklangan sanoq TENG» da'vosi 0 == 0 holatida ham
    yashil bo'ladi. Ya'ni moliyaviy jadvallar bo'sh bo'lgan yugurishda
    test hech nimani o'lchamasdi va majburiy sabotaj (`TRUNCATE`) ham
    hech nimani o'zgartirmasdi — kesiladigan qator yo'q edi.

    Shuning uchun mashq QUYI CHEGARA bilan keladi (pastdagi
    `assert source[table] > 0`) va qatorlarni seed EMAS, test yozadi:
    seed ularni bir kun yozishdan to'xtasa chegara SHU YERDA qizaradi.
    =====================================================================

    ⚠ `billing_domain_before_day_close` VARIANTI: `day_close` yugurtirish
      mashqqa hech nima qo'shmasdi (biz sxema+ma'lumotning KO'CHISHINI
      o'lchayapmiz, hisoblash mantig'ini emas) va har yugurishga narx
      qo'shardi.
    """
    with (
        nvr_rows(sync_owner_conn, two_markets) as nvr,
        snapshot_rows(sync_owner_conn, nvr) as snaps,
        occupancy_rows(sync_owner_conn, two_markets, market_domain, snaps) as occupancy,
        billing_domain_before_day_close(
            sync_owner_conn, two_markets, market_domain, occupancy
        ) as billing,
    ):
        live = billing.market_a
        stall_id = live.stall_with_one_ai_occupied_slot
        assert stall_id is not None, "nazorat: seedda hisob yoziladigan rasta yo'q"

        charge_id, service_date = add_daily_charge(
            sync_owner_conn,
            market_id=live.market_id,
            stall_id=stall_id,
            vendor_id=live.vendor_id,
            tariff_id=live.tariff_id,
        )
        payment_id = add_payment(
            sync_owner_conn,
            market_id=live.market_id,
            stall_id=stall_id,
            vendor_id=live.vendor_id,
            cashier_id=live.cashier_id,
            shift_id=live.open_shift_id,
            service_date=service_date,
        )
        yield Env(billing, charge_id, payment_id)


def _counts(conn: Connection[TupleRow]) -> dict[str, int]:
    """Uchala jadvalning qator soni — ⛔ SUPERUSER ULANISHIDA.

    ⚠ `audit_log` ning `audit_read` policy'si tenant-scoped va u EGAGA
      ham qo'llanadi (`FORCE`), ya'ni kontekstsiz oddiy rol 0 qator
      ko'rardi va «audit jurnali kesilmagan» da'vosi IKKALA tomonda ham
      BO'SH ROST bo'lardi (`test_billing_immutable.py` da o'lchangan
      tuzoq). Superuser RLS'ni chetlab o'tadi va ikkala tomonda ham
      HAQIQIY sanoqni beradi.
    """
    counts: dict[str, int] = {}
    for table in (*FINANCIAL_TABLES, "audit_log"):
        # Jadval nomlari shu moduldagi SOBIT kortejdan keladi — tashqi
        # kirish emas (`billing_domain.py::CLEANUP_ORDER` bilan bir xil naqsh).
        row = conn.execute(_COUNT.format(table=table)).fetchone()  # noqa: S608
        assert row is not None
        counts[table] = int(row[0])
    return counts


def _scalar(conn: Connection[TupleRow], sql: str, params: tuple[object, ...] = ()) -> int:
    row = conn.execute(sql, params).fetchone()
    assert row is not None
    return int(row[0])


def test_a_custom_format_dump_restores_onto_a_clean_server(
    env: Env,
    source_dsn: str,
    restore_target: RestoreTarget,
) -> None:
    """Dump toza serverga tiklanadi va UCH QATLAM ham joyida qoladi.

    =====================================================================
    UCH DA'VO — UCHALASI HAM FOUND-07 MATNIDAN.

      (1) moliyaviy qatorlar (`daily_charges`, `payments`) sanog'i TENG;
      (2) tenant RLS policy'lari TIKLANDI (`pg_policies`);
      (3) audit jurnali KESILMAGAN (`audit_log` sanog'i teng).

    ⛔ (2) ENG QIMMATI VA U T-08-31: tiklangan bazada tenant
       izolyatsiyasi yo'qolsa HAMMA BOZOR bir-birini ko'radi. RLS
       policy'lari `--no-privileges` bilan CHIQARILMAYDI (ular
       imtiyoz emas, alohida obyekt) — lekin bu FARAZ emas, shu yerda
       o'lchanadigan fakt.
    =====================================================================
    """
    with (
        psycopg.connect(source_dsn, autocommit=True) as source,
        psycopg.connect(restore_target.dsn, autocommit=True) as restored,
    ):
        # ⛔ MAJOR VERSIYA TENGLIGI — `pg_restore` ning shartsiz talabi.
        #   Tengsizlikda nosozlik sirli bo'lardi; bu yerda u NOMMA-NOM.
        source_major = _scalar(source, _SERVER_MAJOR)
        target_major = _scalar(restored, _SERVER_MAJOR)
        assert source_major == target_major, (
            f"manba PG {source_major}, toza server PG {target_major} — "
            "`conftest.POSTGRES_IMAGE` va `conftest.RESTORE_TARGET_IMAGE` AJRALGAN"
        )

        before = _counts(source)

        # QUYI CHEGARA — modul/`env` docstringidagi sabab.
        for table in FINANCIAL_TABLES:
            assert before[table] > 0, (
                f"nazorat: manbada `{table}` BO'SH — «sanoq teng» da'vosi 0 == 0 "
                "bo'lib, sabotaj ham hech nimani kesa olmasdi"
            )
        assert before["audit_log"] > 0, "nazorat: manbada `audit_log` bo'sh"

        restore_target.run(
            "pg_dump", *PG_DUMP_FLAGS, f"--file={DUMP_PATH}", f"--dbname={source_dsn}"
        )
        restore_target.run(
            "pg_restore",
            "--no-owner",
            "--no-privileges",
            f"--dbname={restore_target.internal_dsn}",
            DUMP_PATH,
        )

        after = _counts(restored)
        tenant_policies = _scalar(restored, _TENANT_POLICIES, (TENANT_POLICY_SIGNATURE,))

    # --- (1) moliyaviy qatorlar -----------------------------------------
    for table in FINANCIAL_TABLES:
        assert after[table] == before[table], (
            f"`{table}`: manbada {before[table]}, tiklangan bazada {after[table]} — "
            "pul yozuvlari zaxiradan TO'LIQ tiklanmadi"
        )

    # --- (2) tenant izolyatsiyasi (T-08-31) ------------------------------
    assert tenant_policies > 0, (
        f"tiklangan bazada `{TENANT_POLICY_SIGNATURE}` policy'si YO'Q — "
        "RLS dumpda saqlanmagan va tiklangan platformada HAR BOZOR "
        "boshqasining ma'lumotini ko'rardi (T-08-31)"
    )

    # --- (3) audit jurnali ----------------------------------------------
    assert after["audit_log"] == before["audit_log"], (
        f"`audit_log`: manbada {before['audit_log']}, tiklangan bazada "
        f"{after['audit_log']} — audit jurnali tiklashda KESILGAN"
    )
