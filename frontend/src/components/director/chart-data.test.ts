/**
 * PANEL GRAFIKLARINING SOF HISOBLARI (261016).
 *
 * ⛔ Bu fayl «grafik nimani chizadi» degan qarorlarni React'siz o'lchaydi:
 *    sanoq, maxraj, ulush va guruhlash. Pul bu yerda QAYTA HISOBLANMAYDI —
 *    testlar ham buni tasdiqlaydi (qiymatlar o'zgarishsiz o'tadi).
 */
import { describe, expect, test } from "vitest";

import {
  STALL_DAY_ORDER,
  captureBuckets,
  compactSoum,
  countStallDays,
  expectedStalls,
  methodShares,
  topDebtors,
  zoneDayRows,
} from "./chart-data";
import { buildTrendPoints, trendSeries } from "./revenue-trend";
import type { MapDayRow, MapDayState } from "@/lib/map-day-queries";
import type { ReceivablesReportRow } from "@/lib/api-types";

const UNITS = { thousand: "ming", million: "mln", billion: "mlrd" };

let seq = 0;
function stallRow(state: MapDayState, stallId?: string): MapDayRow {
  seq += 1;
  return {
    stall_id: stallId ?? `00000000-0000-4000-8000-${String(seq).padStart(12, "0")}`,
    state,
    amount_soum: state === "no_billing" ? null : 4000,
    unavailable_reason: null,
    paid_soum: state === "paid" ? 4000 : 0,
    remaining_soum: state === "no_billing" ? null : state === "paid" ? 0 : 4000,
    open_case_id: null,
    open_case_service_date: null,
  };
}

function debtor(
  vendorId: string | null,
  outstanding: number,
  name: string | null = `Sotuvchi ${vendorId ?? ""}`,
): ReceivablesReportRow {
  return {
    vendor_id: vendorId,
    vendor_name: name,
    stall_codes: ["3"],
    outstanding_soum: outstanding,
    oldest_debt_date: "2026-10-10",
  };
}

describe("compactSoum — o'q yorlig'i", () => {
  test("ming / mln / mlrd va kasr VERGUL bilan", () => {
    expect(compactSoum(0, UNITS)).toBe("0");
    expect(compactSoum(950, UNITS)).toBe("950");
    expect(compactSoum(6_000, UNITS)).toBe("6 ming");
    expect(compactSoum(1_250_000, UNITS)).toBe("1,3 mln");
    expect(compactSoum(2_000_000, UNITS)).toBe("2 mln");
    expect(compactSoum(24_180_000, UNITS)).toBe("24 mln");
    expect(compactSoum(3_400_000_000, UNITS)).toBe("3,4 mlrd");
  });

  test("manfiy qiymat belgisi bilan — avans yashirilmaydi", () => {
    expect(compactSoum(-1_500_000, UNITS)).toBe("−1,5 mln");
  });
});

describe("rastalar holati — sanoq va maxraj", () => {
  test("har qator BIR MARTA sanaladi, oltala holat kalit sifatida bor", () => {
    const counts = countStallDays([
      stallRow("paid"),
      stallRow("paid"),
      stallRow("due"),
      stallRow("mismatch"),
      stallRow("free"),
      stallRow("no_billing"),
      stallRow("fair"),
    ]);

    expect(counts).toEqual({
      paid: 2,
      due: 1,
      mismatch: 1,
      free: 1,
      no_billing: 1,
      fair: 1,
    });
    expect(Object.keys(counts).sort()).toEqual([...STALL_DAY_ORDER].sort());
  });

  test("maxraj — faqat patta KUTILGAN rastalar (yarmarka/sotuvchisiz/hisobsiz emas)", () => {
    const counts = countStallDays([
      stallRow("paid"),
      stallRow("due"),
      stallRow("mismatch"),
      stallRow("free"),
      stallRow("free"),
      stallRow("fair"),
      stallRow("no_billing"),
    ]);

    expect(expectedStalls(counts)).toBe(3);
  });

  test("sariq yashil va qizil ORASIDA — rang ko'rligi uchun tartib", () => {
    expect(STALL_DAY_ORDER.indexOf("mismatch")).toBe(
      STALL_DAY_ORDER.indexOf("paid") + 1,
    );
    expect(STALL_DAY_ORDER.indexOf("due")).toBe(
      STALL_DAY_ORDER.indexOf("mismatch") + 1,
    );
  });

  test("zona kesimi: holati kelmagan katak SANALMAYDI, bo'sh zona chiqmaydi", () => {
    const a1 = "10000000-0000-4000-8000-000000000001";
    const a2 = "10000000-0000-4000-8000-000000000002";
    const b1 = "10000000-0000-4000-8000-000000000003";
    const unknown = "10000000-0000-4000-8000-000000000004";
    const byStallId = new Map<string, MapDayRow>([
      [a1, stallRow("paid", a1)],
      [a2, stallRow("due", a2)],
      [b1, stallRow("paid", b1)],
    ]);
    const cell = (id: string) => ({
      id,
      code: id.slice(-1),
      status: "active" as const,
      has_vendor: true,
      plan_x: null,
      plan_y: null,
    });

    const rows = zoneDayRows(
      [
        { id: "z-a", name: "Oziq-ovqat", cells: [cell(a1), cell(a2), cell(unknown)] },
        { id: "z-b", name: "Kiyim", cells: [cell(b1)] },
        { id: "z-c", name: "Bo'sh", cells: [cell(unknown)] },
      ],
      byStallId,
    );

    expect(rows.map((row) => row.name)).toEqual(["Oziq-ovqat", "Kiyim"]);
    expect(rows[0]?.counts.paid).toBe(1);
    expect(rows[0]?.counts.due).toBe(1);
    expect(expectedStalls(rows[0]!.counts)).toBe(2);
  });
});

describe("eng katta qarzdorlar", () => {
  test("faqat MUSBAT qoldiq — avans qarzdor bo'lib ko'rinmaydi", () => {
    const rows = topDebtors(
      [debtor("a", 10_000), debtor("b", -40_000), debtor("c", 0)],
      6,
    );

    expect(rows.map((row) => row.vendor_id)).toEqual(["a"]);
  });

  test("katta qarz birinchi, teng qarzda tartib barqaror, chegara ishlaydi", () => {
    const source = [
      debtor("b", 20_000),
      debtor("a", 20_000),
      debtor("c", 90_000),
      debtor("d", 5_000),
    ];

    const rows = topDebtors(source, 3);

    expect(rows.map((row) => row.vendor_id)).toEqual(["c", "a", "b"]);
    /* Serverning ro'yxati o'zgarmaydi — `sort` nusxada. */
    expect(source.map((row) => row.vendor_id)).toEqual(["b", "a", "c", "d"]);
  });
});

describe("to'lov turlari — ulush", () => {
  test("ikki musbat qism — foizlar yig'indisi 100", () => {
    const shares = methodShares(31_400, 17_200);

    expect(shares).not.toBeNull();
    expect((shares?.cash ?? 0) + (shares?.terminal ?? 0)).toBeCloseTo(100);
    expect(shares?.cash).toBeCloseTo(64.6, 1);
  });

  test("Payme uchinchi qism — uchala foiz yig'indisi 100 (0035)", () => {
    const shares = methodShares(30_000, 10_000, 10_000);

    expect(shares?.payme).toBeCloseTo(20);
    expect((shares?.cash ?? 0) + (shares?.terminal ?? 0) + (shares?.payme ?? 0)).toBeCloseTo(100);
    expect(methodShares(0, 0, 22_000)?.payme).toBeCloseTo(100);
    expect(methodShares(10_000, 0, -22_000)).toBeNull();
  });

  test("pul yo'q yoki qism MANFIY (storno) — ulush CHIZILMAYDI", () => {
    expect(methodShares(0, 0)).toBeNull();
    expect(methodShares(12_000, -4_000)).toBeNull();
    expect(methodShares(-1, 0)).toBeNull();
  });
});

describe("kamera kadrlari — to'rt guruh", () => {
  test("yaroqli · sifatsiz · olinmadi · navbatda", () => {
    expect(
      captureBuckets({
        planned: 128,
        done: 100,
        ok: 90,
        dark: 6,
        blank: 3,
        corrupt: 1,
        failed: 4,
        missed: 8,
      }),
    ).toEqual({ ok: 90, poor: 10, lost: 12, pending: 16, planned: 128 });
  });

  test("navbatdagi qism hech qachon MANFIY emas", () => {
    expect(
      captureBuckets({
        planned: 4,
        done: 4,
        ok: 4,
        dark: 0,
        blank: 0,
        corrupt: 0,
        failed: 1,
        missed: 0,
      }).pending,
    ).toBe(0);
  });
});

describe("tushum trendi — nuqtalar va uzuq dum", () => {
  const rows = Array.from({ length: 10 }, (_, index) => {
    const day = String(index + 1).padStart(2, "0");
    return {
      business_date: `2026-10-${day}`,
      collected_soum: 1_000 * (index + 1),
      charged_soum: 2_000,
    };
  });

  test("kunlik kesim: server qatori BEVOSITA nuqta, dum yo'q", () => {
    const points = buildTrendPoints(rows, "7");

    expect(points).toHaveLength(10);
    expect(points[0]).toMatchObject({
      label: "01.10",
      collected: 1_000,
      charged: 2_000,
      partial: false,
    });
    const series = trendSeries(points);
    expect(series.every((point) => point.collectedTail === null)).toBe(true);
    expect(series.every((point) => point.collectedSolid !== null)).toBe(true);
  });

  test("haftalik kesim: yig'indi kunlardan, OXIRGI hafta tugamagan", () => {
    const points = buildTrendPoints(rows, "12h");

    /* 2026-10-01 — payshanba: 1–4 (W40), 5–10 (W41). */
    expect(points.map((point) => point.label)).toEqual(["01.10", "05.10"]);
    expect(points[0]).toMatchObject({
      from: "2026-10-01",
      to: "2026-10-04",
      collected: 10_000,
      charged: 8_000,
      partial: false,
    });
    expect(points[1]?.partial).toBe(true);
  });

  test("dum oxirgi IKKI nuqtadan, to'liq qismda tugamagan nuqta `null`", () => {
    const points = buildTrendPoints(rows, "12h");
    const series = trendSeries(points);

    expect(series[0]?.collectedSolid).toBe(10_000);
    expect(series[1]?.collectedSolid).toBeNull();
    expect(series[0]?.collectedTail).toBe(10_000);
    expect(series[1]?.collectedTail).toBe(points[1]?.collected);
  });
});
