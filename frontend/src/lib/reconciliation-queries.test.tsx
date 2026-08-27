/**
 * `reconciliation-queries.ts` — REYESTR, SXEMA VA KESH SIYOSATI.
 *
 * =============================================================================
 * ⛔ NEGA BU FAYL BOR VA NEGA U KOMPONENT TESTI EMAS.
 *
 * Bu modulning uchta va'dasi RENDERSIZ o'lchanadi va aynan shuning uchun
 * ular bu yerda turadi — komponent testida ular DOM da'volari ostida
 * ko'milib ketardi:
 *
 *   1. Reyestrlar YOPIQ (to'plam tengligi, `other`/`custom` YO'Q);
 *   2. Sxemalar KUTILMAGAN MAYDONDA yiqiladi (`z.strictObject`);
 *   3. Yetkazilganlik keshi `bugun` da IKKALA o'lchamda ham NOL.
 *
 * ⚠ Kalit fabrikalari ham shu yerda: doiralash konvensiyasi
 *   (`["m", marketId, ...]`) 04-10 dan beri butun kodbazada yagona va
 *   uning buzilishi hech qanday ekranni yiqitmaydi — u faqat prefiks
 *   bo'yicha tozalashni JIMGINA o'tkazib yuborardi (07-05 ning topilmasi).
 * =============================================================================
 */
import { describe, expect, test } from "vitest";

import {
  CASE_STATUSES,
  DELIVERY_STATES,
  NOTIFICATION_KINDS,
  SUBJECT_KINDS,
} from "@/lib/api-types";
import {
  CASES_STALE_TIME_MS,
  CASE_PAGE_SIZE,
  DELIVERY_PAGE_SIZE,
  REPORT_STALE_TIME_MS,
  caseListSchema,
  caseRowSchema,
  casesKey,
  deliveryCachePolicy,
  deliveryKey,
  deliveryListSchema,
  isCaseStatus,
  isSubjectKind,
  reportKey,
  reportRowSchema,
  reportSchema,
} from "@/lib/reconciliation-queries";

const MARKET = "3f1c0f2e-0000-4000-8000-000000000001";
const CASE_ID = "3f1c0f2e-0000-4000-8000-000000000002";
const VENDOR_ID = "3f1c0f2e-0000-4000-8000-000000000003";
const SNAPSHOT_ID = "3f1c0f2e-0000-4000-8000-000000000004";

const REPORT_ROW = {
  subject_kind: "occupied_unpaid",
  case_id: CASE_ID,
  status: "new",
  service_date: "2026-08-11",
  stall_code: "14-C",
  vendor_id: VENDOR_ID,
  expected_soum: 30_000,
  paid_soum: 10_000,
  evidence_snapshot_ids: [SNAPSHOT_ID],
};

const CASE_ROW = {
  case_id: CASE_ID,
  subject_kind: "occupied_unpaid",
  anomaly_id: null,
  charge_id: CASE_ID,
  service_date: "2026-08-11",
  status: "new",
  assignee_user_id: null,
  created_at: "2026-08-12T04:25:00Z",
};

/* -------------------------------------------------------------------------- */

describe("reyestrlar — YOPIQ to'plamlar (W0-F8)", () => {
  test("⛔ `CASE_STATUSES` AYNAN to'rt a'zo va `other` YO'Q (D-12)", () => {
    /*
     * ⛔ TO'PLAM TENGLIGI, `not.toContain` EMAS (D-31): «`other` bormi?»
     *   tekshiruvi beshinchi a'zo BOSHQA nom bilan qo'shilganda yashil
     *   qolardi — va aynan o'sha holat aniqlik ulushining maxrajini
     *   ANIQLANMAGAN qilardi (D-13).
     */
    expect(new Set(CASE_STATUSES)).toEqual(
      new Set(["new", "in_review", "justified", "unjustified"]),
    );
    expect(CASE_STATUSES).toHaveLength(4);

    for (const banned of ["other", "custom", "unknown"]) {
      expect(isCaseStatus(banned)).toBe(false);
    }
    expect(isCaseStatus("justified")).toBe(true);
  });

  test("⛔ `DELIVERY_STATES` AYNAN besh a'zo (BOT-04)", () => {
    expect(new Set(DELIVERY_STATES)).toEqual(
      new Set(["pending", "sent", "delivered", "failed", "blocked"]),
    );
    expect(DELIVERY_STATES).toHaveLength(5);
  });

  test("`SUBJECT_KINDS` ikki a'zo; `NOTIFICATION_KINDS` to'rt a'zo", () => {
    expect(new Set(SUBJECT_KINDS)).toEqual(
      new Set(["anomaly", "occupied_unpaid"]),
    );
    expect(new Set(NOTIFICATION_KINDS)).toEqual(
      new Set([
        "payment_receipt",
        "overdue_reminder",
        "digest_morning",
        "digest_evening",
      ]),
    );
    expect(isSubjectKind("occupied_unpaid")).toBe(true);
    expect(isSubjectKind("no_coverage_stall")).toBe(false);
  });
});

/* -------------------------------------------------------------------------- */

describe("sxemalar — `z.strictObject` (yuza JIMGINA kengaya olmaydi)", () => {
  test("hisobot qatori — toza javob o'tadi", () => {
    expect(reportRowSchema.parse(REPORT_ROW).stall_code).toBe("14-C");
  });

  test("⛔ `anomaly` qatorida kutilgan summa `null` — va u NOLGA aylanmaydi", () => {
    /*
     * ⛔ Biriktirilmagan zonaning tarifi BILINMAYDI. Nol yozish «bu
     *   savdodan hech nima kutilmagan» degan YOLG'ON da'vo bo'lardi va
     *   yig'indi KAM KO'RSATILGAN YO'QOTISH bilan tugardi (§8.2).
     */
    const parsed = reportRowSchema.parse({
      ...REPORT_ROW,
      subject_kind: "anomaly",
      case_id: null,
      status: null,
      vendor_id: null,
      expected_soum: null,
      paid_soum: null,
    });

    expect(parsed.expected_soum).toBeNull();
    expect(parsed.paid_soum).toBeNull();
  });

  test("⛔ KUTILMAGAN MAYDON kelganda HAR sxema yiqiladi", () => {
    /*
     * ⛔ Bu `extra="forbid"` ning KLIENT TOMONIDAGI jufti, o'rnini
     *   bosuvchisi EMAS: bittasini olib tashlash ikkinchisini ochmaydi.
     *   Serverga bitta shaxsiy maydon qo'shilsa, ekran uni JIMGINA
     *   chizib yuborish o'rniga PARSE paytida to'xtaydi.
     */
    expect(() =>
      reportRowSchema.parse({ ...REPORT_ROW, vendor_label: "Anvar" }),
    ).toThrow();

    expect(() =>
      reportSchema.parse({
        day: "2026-08-11",
        rows: [],
        unpaid_count: 0,
        unregistered_count: 0,
        unpaid_expected_soum: 0,
        /* ⛔ Birlashtirilgan jami — server qo'shsa ham klient RAD ETADI. */
        total_discrepancies: 0,
      }),
    ).toThrow();

    expect(() => caseRowSchema.parse({ ...CASE_ROW, extra: 1 })).toThrow();

    expect(() =>
      caseListSchema.parse({
        day: "2026-08-11",
        rows: [CASE_ROW],
        new_count: 1,
        in_review_count: 0,
        justified_count: 0,
        unjustified_count: 0,
        next_cursor: null,
        grand_total: 1,
      }),
    ).toThrow();
  });

  test("⛔ NOMA'LUM holat sxemani YIQITMAYDI (04-10 darsi)", () => {
    /*
     * ⛔ Sxema reyestr bilan QULFLANMAGAN va bu qaror: qulflangan
     *   sxemada backendning bitta yangi a'zosi butun hisobotni parse
     *   chegarasida yiqitardi va direktor eng yuqori ustuvorlikdagi
     *   yuzada BO'SH SAHIFA ko'rardi. Yopiqlik KO'RINISHDA majburlanadi.
     */
    const parsed = caseRowSchema.parse({ ...CASE_ROW, status: "escalated" });

    expect(parsed.status).toBe("escalated");
    expect(isCaseStatus(parsed.status)).toBe(false);
  });

  test("envelope to'rt sanoq bilan keladi (nol bo'lganda ham)", () => {
    const parsed = caseListSchema.parse({
      day: "2026-08-11",
      rows: [],
      new_count: 0,
      in_review_count: 0,
      justified_count: 0,
      unjustified_count: 0,
      next_cursor: null,
    });

    expect(parsed.new_count).toBe(0);
    expect(parsed.next_cursor).toBeNull();
  });
});

/* -------------------------------------------------------------------------- */

describe("kesh — kalitlar doiralangan, yetkazilganlik `bugun` da JONLI", () => {
  test("har kalit `[\"m\", marketId, ...]` prefiksi ostida (04-10)", () => {
    for (const key of [
      reportKey(MARKET, "2026-08-11"),
      casesKey(MARKET, "2026-08-11"),
      deliveryKey(MARKET, "2026-08-11"),
    ]) {
      expect(key[0]).toBe("m");
      expect(key[1]).toBe(MARKET);
    }

    /* Kun kalitning bir qismi — boshqa kun BOSHQA zanjir. */
    expect(casesKey(MARKET, "2026-08-12")).not.toEqual(
      casesKey(MARKET, "2026-08-11"),
    );
  });

  test("⛔ KURSOR KALITNING BIR QISMI EMAS — sahifalar BITTA zanjirda (B-6)", () => {
    /*
     * ⛔ AVVAL kursor kalitda edi va aynan shu `useInfiniteQuery` bilan
     *   TO'QNASHADI: TanStack sahifalarni BITTA kalit ostida `pages[]`
     *   bo'lib saqlaydi. Kursor kalitga qo'shilsa, ikkinchi sahifa YANGI
     *   zanjir boshlardi va birinchisi YO'QOLARDI — «Yana yuklash» 50
     *   qatorni boshqa 20 taga ALMASHTIRARDI.
     *
     * ⛔ DA'VO KALITNING UZUNLIGI USTIDAN: uchinchi argument qo'shilsa
     *   (nomi qanday bo'lishidan qat'i nazar) bu tenglik QIZARADI.
     */
    expect(casesKey(MARKET, "2026-08-11")).toEqual([
      "m",
      MARKET,
      "recon-cases",
      "2026-08-11",
    ]);
  });

  test("⛔ sahifa o'lchamlari SERVER chegarasining ko'zgusi (B-6)", () => {
    /*
     * ⛔ Server ikkala marshrutda ham `le=…PAGE_SIZE` bilan CHEGARALAYDI:
     *   kattaroq qiymat `422` bilan qaytardi, ya'ni ro'yxat UMUMAN
     *   yuklanmasdi. Konstanta o'sha chegaraning ko'zgusi bo'lib qoladi.
     */
    expect(CASE_PAGE_SIZE).toBe(50);
    expect(DELIVERY_PAGE_SIZE).toBe(50);
  });

  test("⛔ IKKALA envelope ham `next_cursor` ni PARSE qiladi (sahifalash tirik)", () => {
    /*
     * ⛔ `next_cursor` — ATAYIN UNUMSIZ SATR: klient uni PARSE QILMAYDI
     *   (T-07-123) va serverga o'zgarishsiz qaytaradi. Sxema uni faqat
     *   «satr yoki `null`» sifatida biladi.
     */
    const cases = caseListSchema.parse({
      day: "2026-08-11",
      rows: [],
      new_count: 0,
      in_review_count: 0,
      justified_count: 0,
      unjustified_count: 0,
      next_cursor: "2026-08-12T04:25:00+00:00|" + CASE_ID,
    });
    expect(cases.next_cursor).toContain(CASE_ID);

    const delivery = deliveryListSchema.parse({
      day: "2026-08-11",
      rows: [],
      pending_count: 0,
      sent_count: 0,
      delivered_count: 0,
      failed_count: 0,
      blocked_count: 0,
      next_cursor: "2026-08-12T09:15:00+00:00|" + CASE_ID,
    });
    expect(delivery.next_cursor).toContain(CASE_ID);
  });

  test("⛔ `bugun` da yetkazilganlik keshi IKKALA o'lchamda ham NOL", () => {
    /*
     * ⛔ `staleTime: 0` YETARLI EMAS. `gcTime` musbat qolsa, blok qayta
     *   chizilganda TanStack avval KESHDAGI eski javobni ko'rsatadi va
     *   ekranda «hali yuborilmadi» turadi — direktor uni HOZIRGI holat
     *   deb o'qirdi va «xabar kelmadi» nizosi (D-02) tizimning O'ZIDAN
     *   tug'ilardi.
     */
    expect(deliveryCachePolicy(true)).toEqual({ staleTime: 0, gcTime: 0 });
  });

  test("o'tgan kunning yetkazilganligi O'ZGARMAS — kesh musbat", () => {
    const past = deliveryCachePolicy(false);

    expect(past.staleTime).toBeGreaterThan(0);
    expect(past.gcTime).toBeGreaterThan(0);
  });

  test("hisobot navbatdan SEKINROQ eskiradi (D-07)", () => {
    /*
     * Yozilgan hisob o'zgarmas, navbat esa kun ichida o'zgaradi (holat,
     * mas'ul). Teskari nisbat ekranda eskirgan NAVBATNI qoldirardi.
     */
    expect(REPORT_STALE_TIME_MS).toBeGreaterThan(CASES_STALE_TIME_MS);
  });
});
