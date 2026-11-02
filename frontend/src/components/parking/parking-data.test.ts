/**
 * Avtoturargoh hisobotining sof yordamchilari — React'siz.
 *
 * Da'volar: raqam faqat TANILGAN shaklda bo'linadi; qidiruv kirill
 * harflarini ham topadi; jurnal eng yangisidan boshlanadi va filtrlar
 * holatlarni to'g'ri guruhlaydi; galereyaga faqat kadri bor seans tushadi.
 */
import { describe, expect, test } from "vitest";

import {
  barWidth,
  durationParts,
  filterJournal,
  hourLabel,
  journalCounts,
  looksLikePlate,
  normalizePlateQuery,
  peakHour,
  recentWithPhotos,
  sessionStatus,
  shareOf,
  splitUzPlate,
} from "@/components/parking/parking-data";
import type { EdgeParkingReportSession } from "@/lib/api-types";

function session(
  id: string,
  over: Partial<EdgeParkingReportSession> = {},
): EdgeParkingReportSession {
  return {
    session_id: id,
    plate: null,
    entered_at: null,
    exited_at: null,
    duration_minutes: null,
    amount_soum: 0,
    method: null,
    reason: null,
    entry_file_id: null,
    opened_at_exit: false,
    ...over,
  };
}

describe("davlat raqami", () => {
  test("jismoniy shaxs va yuridik shaxs raqamlari katakchalarga bo'linadi", () => {
    expect(splitUzPlate("01A123BC")).toEqual({ region: "01", body: "A 123 BC" });
    expect(splitUzPlate("85123ABC")).toEqual({ region: "85", body: "123 ABC" });
  });

  test("tanilmagan shakl bo'linmaydi — o'qilgan matn o'zgartirilmaydi", () => {
    expect(splitUzPlate("KZ777AAA02")).toBeNull();
    expect(splitUzPlate("01A12BC")).toBeNull();
  });

  test("qidiruv: bo'shliq, chiziqcha, kichik harf va kirill harflari", () => {
    expect(normalizePlateQuery(" 01 a-123 ")).toBe("01A123");
    expect(normalizePlateQuery("01А123ВС")).toBe("01A123BC");
  });
});

describe("vaqt", () => {
  test("daqiqa kun/soat/daqiqaga bo'linadi; manfiy nolga tushadi", () => {
    expect(durationParts(70)).toEqual({ days: 0, hours: 1, minutes: 10 });
    expect(durationParts(1500)).toEqual({ days: 1, hours: 1, minutes: 0 });
    expect(durationParts(-5)).toEqual({ days: 0, hours: 0, minutes: 0 });
  });

  test("soat yorlig'i va 23 dan keyingi soat", () => {
    expect(hourLabel(8)).toBe("08:00");
    expect(hourLabel(24)).toBe("00:00");
  });

  test("eng gavjum soat — teng bo'lsa ertarog'i; kirish yo'q bo'lsa null", () => {
    const hours = [
      { hour: 7, entries: 3, exits: 0 },
      { hour: 8, entries: 5, exits: 1 },
      { hour: 9, entries: 5, exits: 2 },
    ];
    expect(peakHour(hours)?.hour).toBe(8);
    expect(peakHour([{ hour: 0, entries: 0, exits: 4 }])).toBeNull();
  });
});

describe("seanslar", () => {
  const rows = [
    session("a", { plate: "01A111AA", entered_at: "2026-11-01T03:00:00Z" }),
    session("b", {
      plate: "01B222BB",
      entered_at: "2026-11-01T04:00:00Z",
      exited_at: "2026-11-01T05:00:00Z",
      reason: "paid",
      amount_soum: 4000,
      entry_file_id: "f".repeat(64),
    }),
    session("c", {
      plate: "01C333CC",
      entered_at: "2026-11-01T05:00:00Z",
      exited_at: "2026-11-01T05:10:00Z",
      reason: "exempt",
      entry_file_id: "e".repeat(64),
    }),
    session("d", { exited_at: "2026-11-01T02:00:00Z", reason: "towed" }),
    session("e", {
      plate: "01B999BB",
      entered_at: "2026-11-01T06:00:00Z",
      exited_at: "2026-11-01T06:30:00Z",
      reason: "manual",
    }),
  ];

  test("holat: chiqishsiz — ichkarida, noma'lum sabab — boshqa", () => {
    expect(rows.map(sessionStatus)).toEqual(["open", "paid", "exempt", "other", "manual"]);
  });

  test("jurnal eng yangisidan boshlanadi va raqam qismi bo'yicha qidiradi", () => {
    expect(filterJournal(rows, "", "all").map((row) => row.session_id)).toEqual([
      "e",
      "c",
      "b",
      "a",
      "d",
    ]);
    expect(filterJournal(rows, "01b", "all").map((row) => row.session_id)).toEqual(["e", "b"]);
  });

  test("«Bepul» filtri imtiyozlilarni ham, «To'langan» onlaynni ham qamraydi", () => {
    expect(filterJournal(rows, "", "free").map((row) => row.session_id)).toEqual(["c"]);
    expect(filterJournal(rows, "", "paid").map((row) => row.session_id)).toEqual(["b"]);
    expect(journalCounts(rows)).toEqual({ all: 5, open: 1, paid: 1, free: 1, manual: 1 });
  });

  test("galereya — faqat kadri borlar, eng yangisi oldin, chegara bilan", () => {
    expect(recentWithPhotos(rows, 8).map((row) => row.session_id)).toEqual(["c", "b"]);
    expect(recentWithPhotos(rows, 1).map((row) => row.session_id)).toEqual(["c"]);
  });

  test("chiqishda ro'yxatga olingan seans galereyaga tushmaydi — kadri chiqishdan", () => {
    const atExit = session("x", {
      plate: "85W523OA",
      entered_at: "2026-11-01T07:00:00Z",
      exited_at: "2026-11-01T07:00:00Z",
      duration_minutes: 0,
      reason: "paid",
      entry_file_id: "a".repeat(64),
      opened_at_exit: true,
    });
    expect(recentWithPhotos([...rows, atExit], 8).map((row) => row.session_id)).toEqual([
      "c",
      "b",
    ]);
  });

  test("raqam emas — kameraning matni", () => {
    expect(looksLikePlate("UNKNOWN")).toBe(false);
    expect(looksLikePlate("269PA")).toBe(true);
  });
});

describe("ustunlar", () => {
  test("eni eng kattasiga nisbatan; kichik qiymat ko'rinadi, nol — nol", () => {
    expect(barWidth(50, 100)).toBe(50);
    expect(barWidth(1, 1000)).toBe(2);
    expect(barWidth(0, 100)).toBe(0);
  });

  test("ulush — umumiy nol bo'lsa null", () => {
    expect(shareOf(1, 4)).toBe(25);
    expect(shareOf(0, 0)).toBeNull();
  });
});
