import { describe, expect, test } from "vitest";

import { includesMarketToday, marketToday } from "@/lib/live-refresh";

describe("bugungi pul o'zi yangilanadi (261112)", () => {
  test("bozor kuni Toshkent vaqtida: UTC 20:30 — Toshkentda ertangi kun", () => {
    expect(marketToday(new Date("2026-11-11T20:30:00Z"))).toBe("2026-11-12");
  });

  test("bugunni qamragan davr yangilanadi, yopilgan davr yo'q", () => {
    const now = new Date("2026-11-12T07:00:00Z");
    expect(includesMarketToday("2026-11-12", now)).toBe(true);
    expect(includesMarketToday("2026-11-11", now)).toBe(false);
  });
});
