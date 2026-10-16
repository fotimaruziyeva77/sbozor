/**
 * TUSHUM KALENDARI (261016) — kunlar bir qarashda.
 *
 * ⛔ Bu fayl uch narsani o'lchaydi: kun TO'G'RI hafta kuniga tushadimi,
 *    holat belgilari serverning ishorasidan chiqadimi (klient ayirmaydi),
 *    va kun bosilganda uchala son serverdan kelganicha ko'rinadimi.
 */
import { fireEvent, render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, test } from "vitest";

import messages from "../../../messages/uz-Latn.json";
import {
  RevenueCalendar,
  calendarWeeks,
  heatLevel,
  thousands,
} from "@/components/reports/revenue-calendar";
import type { RevenueReportRow } from "@/lib/api-types";

const R = messages.reports;

function row(
  day: string,
  collected: number,
  charged: number,
  diff: number,
): RevenueReportRow {
  return {
    business_date: day,
    collected_soum: collected,
    charged_soum: charged,
    diff_soum: diff,
  };
}

/* 2026-10-01 — payshanba. */
const ROWS: RevenueReportRow[] = [
  row("2026-10-01", 1_200_000, 1_300_000, -100_000),
  row("2026-10-02", 1_500_000, 1_300_000, 200_000),
  row("2026-10-03", 900_000, 0, 900_000),
  row("2026-10-04", 0, 0, 0),
  row("2026-10-05", 600, 0, 600),
];

function renderCalendar(rows: readonly RevenueReportRow[] = ROWS) {
  return render(
    <NextIntlClientProvider locale="uz-Latn" messages={messages} timeZone="Asia/Tashkent">
      <RevenueCalendar rows={rows} />
    </NextIntlClientProvider>,
  );
}

describe("kalendar to'ri", () => {
  test("birinchi kun o'z hafta kuniga tushadi, hafta dushanbadan boshlanadi", () => {
    const weeks = calendarWeeks(ROWS);

    /* 1-oktabr payshanba: dushanba–chorshanba bo'sh, payshanba — 4-ustun. */
    expect(weeks[0]?.map((cell) => cell.iso)).toEqual([
      "2026-09-28",
      "2026-09-29",
      "2026-09-30",
      "2026-10-01",
      "2026-10-02",
      "2026-10-03",
      "2026-10-04",
    ]);
    expect(weeks[0]?.slice(0, 3).every((cell) => cell.row === null)).toBe(true);
    expect(weeks[0]?.[3]?.row?.business_date).toBe("2026-10-01");
    /* 5-oktabr dushanba — ikkinchi hafta, oxiri yakshanba bilan to'ladi. */
    expect(weeks).toHaveLength(2);
    expect(weeks[1]?.[6]?.iso).toBe("2026-10-11");
  });

  test("bo'sh davr — bo'sh to'r", () => {
    expect(calendarWeeks([])).toEqual([]);
  });

  test("fon to'qligi: pul yo'q yoki manfiy — 0, eng katta kun — 4", () => {
    expect(heatLevel(0, 1_500_000)).toBe(0);
    expect(heatLevel(-22_000, 1_500_000)).toBe(0);
    expect(heatLevel(1_500_000, 1_500_000)).toBe(4);
    expect(heatLevel(1, 1_500_000)).toBe(1);
    expect(heatLevel(800_000, 1_600_000)).toBe(2);
  });

  test("katakdagi yozuv — ming so'mda, mingdan kichigi «<1»", () => {
    expect(thousands(1_133_000)).toBe("1 133");
    expect(thousands(22_000)).toBe("22");
    expect(thousands(600)).toBe("<1");
    expect(thousands(0)).toBe("0");
    expect(thousands(-22_000)).toBe("−22");
  });
});

describe("kalendar yuzasi", () => {
  test("holat belgilari serverning ishorasidan: kam yig'ilgan va hisobsiz kunlar", () => {
    renderCalendar();

    const group = screen.getByRole("group", { name: R.calLabel });
    const buttons = within(group).getAllByRole("button");
    expect(buttons).toHaveLength(ROWS.length);

    /* 1-oktabr: farq manfiy — «hisobdan kam yig'ilgan». */
    expect(buttons[0]?.getAttribute("aria-label")).toContain(R.calShort);
    /* 2-oktabr: ortiqcha — belgi YO'Q (yashil ham emas). */
    expect(buttons[1]?.getAttribute("aria-label")).not.toContain(R.calShort);
    expect(buttons[1]?.querySelector(".rev-cal-dot")).toBeNull();
    /* 3-oktabr: pul bor, patta hisoblanmagan. */
    expect(buttons[2]?.getAttribute("aria-label")).toContain(R.calUncharged);
    /* 4-oktabr: pul ham, hisob ham yo'q — belgi yo'q. */
    expect(buttons[3]?.querySelector(".rev-cal-dot")).toBeNull();

    expect(screen.getByText("Hisobdan kam yig'ilgan kunlar: 1")).toBeInTheDocument();
    expect(screen.getByText("patta hisoblanmagan kunlar: 2")).toBeInTheDocument();
  });

  test("standart holatda OXIRGI kun tanlangan, bosilgan kun tafsiloti ochiladi", () => {
    renderCalendar();

    const group = screen.getByRole("group", { name: R.calLabel });
    const buttons = within(group).getAllByRole("button");
    expect(buttons[buttons.length - 1]).toHaveAttribute("aria-pressed", "true");

    fireEvent.click(buttons[0] as HTMLElement);

    expect(buttons[0]).toHaveAttribute("aria-pressed", "true");
    /* Uchala son serverdan kelganicha — farq ayirilmaydi, o'qiladi. */
    expect(screen.getByText("1 200 000 so'm")).toBeInTheDocument();
    expect(screen.getByText("1 300 000 so'm")).toBeInTheDocument();
    const diff = screen.getByText("−100 000 so'm");
    expect(diff.className).toContain("text-danger-text");
  });
});
