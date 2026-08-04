/**
 * JADVAL KARTASI — D-05 NING BUTUN MAZMUNI IKKI QATORNING MAVJUDLIGIDA.
 *
 * =============================================================================
 * BU FAYLNING MARKAZIY DA'VOSI:
 *
 *   «ERTAGA» QATORI DOIM RENDER QILINADI — BUGUNGI BILAN BIR XIL BO'LSA HAM.
 *
 *   Vasvasa aniq va u har bir ko'rikda qaytadi: «ikkalasi bir xil bo'lsa,
 *   nega ikki marta yozamiz?». Javob shundaki, ikki qator BIR XIL
 *   bo'lganda ham AXBOROT tashiydi — u «bugun qanday bo'lsa, ertaga ham
 *   shunday» deydi. Bitta qatorga yig'ilsa, admin jadvalni tahrirlagan
 *   lahzada ekranda HECH NARSA o'zgarmaydi va u «saqlandimi?» degan
 *   savol bilan qoladi. D-05 ning yagona ko'rsatkichi aynan shu ikki
 *   qatorning FARQIDA (SC#1).
 *
 *   Shuning uchun «doim bor» va «farq izohi chiqadi» IKKI MUSTAQIL
 *   da'vo: birinchisini shartga bog'lash ikkinchisini qizartirmaydi va
 *   aksincha. Rejaning sabotaj bandi aynan shu chegarani o'lchaydi.
 * =============================================================================
 *
 * Qolgan uch da'vo (§5.7 va §4.3):
 *   * `differs === true` da farq izohi `role="status"` bilan chiqadi va u
 *     SARIQ MATN emas, sariq TINT ustidagi oddiy matn (§9.2 — o'lchangan
 *     15,64:1; `--color-warning` oq fonda 2,03:1 beradi);
 *   * `camera_manage` yo'q rolda ikkala tugma ham UMUMAN render
 *     qilinmaydi (`aria-disabled` ham emas) — T-04-77;
 *   * `uncovered_days > 0` da bo'shliq ogohlantirishi ko'rinadi, `0` da
 *     komponent umuman chizilmaydi.
 *
 * ⚠ MA'LUMOT KESHGA EKILADI, HTTP qatlami mock QILINMAYDI
 *   (`vendor-list.test.tsx:64-78` naqshi): bu yo'l HAQIQIY
 *   `useScheduleToday` ni va HAQIQIY `scheduleTodayKey` fabrikasini
 *   ishlatadi. Kalit bir kun doiralashni yo'qotsa test JIMGINA yashil
 *   qolmaydi — u yuklanish holatida qotib, qatorlarni topa olmay
 *   yiqiladi.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import messages from "../../../messages/uz-Latn.json";
import { ScheduleCard, formatSlotTime } from "@/components/snapshots/schedule-card";
import type { SnapshotScheduleToday } from "@/lib/api-types";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";
import { scheduleTodayKey } from "@/lib/snapshot-queries";

const MARKET_ID = "11111111-1111-4111-8111-111111111111";

const TOMORROW_LABEL = messages.snapshots.tomorrow;
const TODAY_LABEL = messages.snapshots.today;
const TAKES_EFFECT = messages.snapshots.takesEffectTomorrow;
const EDIT_LABEL = messages.snapshots.editSchedule;
const ADD_SEASONAL_LABEL = messages.snapshots.addSeasonal;
const COVERAGE_TITLE = messages.snapshots.coverageTitle;
const COVERAGE_FIX = messages.snapshots.coverageFix;
const CLOSED_DAYS = messages.snapshots.closedDaysIncluded;

function makeToday(
  overrides: Partial<SnapshotScheduleToday> = {},
): SnapshotScheduleToday {
  return {
    profile: {
      id: "22222222-2222-4222-8222-222222222222",
      name: "Standart",
      starts_on: "2026-08-15",
      ends_on: null,
      mode: "active",
    },
    today: {
      date: "2026-09-01",
      times: ["06:00:00", "06:30:00", "07:00:00"],
    },
    tomorrow: {
      date: "2026-09-02",
      times: ["06:00:00", "06:30:00", "07:00:00"],
    },
    differs: false,
    capture_on_closed_days: false,
    uncovered_days: 0,
    uncovered_horizon_days: 90,
    ...overrides,
  };
}

function seedSession(): void {
  setSession({
    accessToken: "test-access-token",
    principal: {
      userId: "33333333-3333-4333-8333-333333333333",
      phone: "+998900000000",
      fullName: "Test Admin",
      roles: ["market_admin"],
      marketId: MARKET_ID,
      marketName: "Karmana markaziy bozori",
      isPlatformAdmin: false,
      locale: "uz-Latn",
      mustChangePassword: false,
    },
    markets: [],
  });
}

/**
 * `staleTime: Infinity` MAJBURIY: usiz TanStack montajdan keyin ekilgan
 * ma'lumotni «eskirgan» deb bilib, haqiqiy so'rov yuborardi.
 */
function renderCard(
  data: SnapshotScheduleToday,
  options: { canManage?: boolean } = {},
): ReturnType<typeof render> {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: Infinity },
      mutations: { retry: false },
    },
  });
  client.setQueryData(scheduleTodayKey(MARKET_ID), data);

  const tree: ReactElement = (
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      timeZone="Asia/Tashkent"
    >
      <QueryClientProvider client={client}>
        <AuthProvider>
          <ScheduleCard canManage={options.canManage ?? true} />
        </AuthProvider>
      </QueryClientProvider>
    </NextIntlClientProvider>
  );

  return render(tree);
}

beforeEach(() => {
  vi.resetAllMocks();
  clearSession();
  seedSession();
});

afterEach(() => {
  clearSession();
});

/* ---------------------------------------------------------------------------
 * ⛔ MARKAZIY DA'VO — «ERTAGA» QATORI DOIM BOR (D-05)
 * ------------------------------------------------------------------------ */

describe("«Bugun» va «Ertaga» qatorlari", () => {
  test("⛔ «Ertaga» qatori `differs === false` da HAM render qilinadi", () => {
    renderCard(makeToday({ differs: false }));

    expect(screen.getByText(TODAY_LABEL)).toBeInTheDocument();
    expect(screen.getByText(TOMORROW_LABEL)).toBeInTheDocument();
  });

  test("ikkala qator ham o'z vaqtlarini `HH:mm` va `font-mono` bilan beradi", () => {
    renderCard(
      makeToday({
        differs: true,
        tomorrow: { date: "2026-09-02", times: ["07:00:00", "15:00:00"] },
      }),
    );

    // `06:00:00` -> `06:00`: xom javob o'zgartirilmaydi, format CHIZISH
    // joyida qisqartiriladi (§13.4).
    expect(formatSlotTime("06:00:00")).toBe("06:00");
    expect(formatSlotTime("15:00")).toBe("15:00");

    const first = screen.getAllByText("06:00")[0];
    expect(first).toHaveClass("font-mono");
    expect(screen.getByText("15:00")).toBeInTheDocument();
  });

  test("vaqtlar soni ikkala kun uchun ALOHIDA ko'rsatiladi", () => {
    renderCard(
      makeToday({
        differs: true,
        today: { date: "2026-09-01", times: ["06:00:00", "06:30:00", "07:00:00"] },
        tomorrow: { date: "2026-09-02", times: ["07:00:00", "15:00:00"] },
      }),
    );

    const three = messages.snapshots.timesCount.replace("{count}", "3");
    const two = messages.snapshots.timesCount.replace("{count}", "2");

    expect(screen.getByText(three)).toBeInTheDocument();
    expect(screen.getByText(two)).toBeInTheDocument();
  });
});

/* ---------------------------------------------------------------------------
 * FARQ IZOHI — MUSTAQIL DA'VO (§4.3, §9.2)
 * ------------------------------------------------------------------------ */

describe("D-05 farq izohi", () => {
  test("`differs === true` da izoh chiqadi va u `role='status'`", () => {
    renderCard(makeToday({ differs: true }));

    const note = screen.getByText(TAKES_EFFECT);
    expect(note).toBeInTheDocument();
    expect(note.closest("[role='status']")).not.toBeNull();
  });

  test("izoh SARIQ MATN emas — sariq TINT ustidagi oddiy matn (§9.2)", () => {
    const { container } = renderCard(makeToday({ differs: true }));

    const note = screen.getByText(TAKES_EFFECT).closest("[role='status']");
    expect(note).toHaveClass("bg-warning/20");
    expect(note).toHaveClass("text-text");

    // `--color-warning` oq fonda 2,03:1 — matn rangi sifatida FALOKAT.
    expect(container.querySelector(".text-warning")).toBeNull();
  });

  test("`differs === false` da izoh UMUMAN chizilmaydi", () => {
    renderCard(makeToday({ differs: false }));

    expect(screen.queryByText(TAKES_EFFECT)).toBeNull();
  });
});

/* ---------------------------------------------------------------------------
 * RBAC KO'ZGUSI — T-04-77
 * ------------------------------------------------------------------------ */

describe("`camera_manage` ko'zgusi", () => {
  test("huquq yo'q bo'lsa ikkala tugma ham UMUMAN render qilinmaydi", () => {
    renderCard(makeToday(), { canManage: false });

    // Rol bo'yicha ham, MATN bo'yicha ham: `aria-disabled` tugma rol
    // qidiruvidan o'tib ketardi, ya'ni ikkala tekshiruv ham kerak.
    expect(screen.queryByRole("button", { name: EDIT_LABEL })).toBeNull();
    expect(screen.queryByRole("button", { name: ADD_SEASONAL_LABEL })).toBeNull();
    expect(document.body.textContent).not.toContain(EDIT_LABEL);
    expect(document.body.textContent).not.toContain(ADD_SEASONAL_LABEL);
  });

  test("huquq bor bo'lsa ikkalasi ham IKKILAMCHI tugma bo'lib chiqadi (§9.3)", () => {
    renderCard(makeToday(), { canManage: true });

    const edit = screen.getByRole("button", { name: EDIT_LABEL });
    const add = screen.getByRole("button", { name: ADD_SEASONAL_LABEL });

    // ⛔ Sahifaning O'ZIDA aksent fonli tugma YO'Q — bu kuzatuv sahifasi.
    for (const button of [edit, add]) {
      expect(button).not.toHaveClass("bg-accent");
      expect(button).not.toBeDisabled();
    }
  });
});

/* ---------------------------------------------------------------------------
 * QOPLANMAGAN KUN — JIM MA'LUMOT YO'QOTISH EMAS (§10.5)
 * ------------------------------------------------------------------------ */

describe("qoplanmagan kun ogohlantirishi", () => {
  test("`uncovered_days > 0` da sabab VA tuzatish yo'li ko'rinadi", () => {
    renderCard(makeToday({ uncovered_days: 3, uncovered_horizon_days: 90 }));

    expect(screen.getByText(COVERAGE_TITLE)).toBeInTheDocument();
    expect(screen.getByText(COVERAGE_FIX)).toBeInTheDocument();

    // Sanoq ham, oyna ham matnda: «3 kun qoplanmagan» jumlasi qaysi oyna
    // ustida aytilganini bilmasa ma'nosiz bo'lardi.
    const body = messages.snapshots.coverageBody
      .replace("{horizon}", "90")
      .replace("{count}", "3");
    expect(screen.getByText(body)).toBeInTheDocument();
  });

  test("`uncovered_days === 0` da ogohlantirish UMUMAN chizilmaydi", () => {
    renderCard(makeToday({ uncovered_days: 0 }));

    expect(screen.queryByText(COVERAGE_TITLE)).toBeNull();
  });
});

/* ---------------------------------------------------------------------------
 * YOPIQ KUN QATORI — O'QISH UCHUN (D-10, §4.3)
 * ------------------------------------------------------------------------ */

describe("yopiq kun qatori", () => {
  test("`capture_on_closed_days === true` da qator bor va u TUGMA EMAS", () => {
    renderCard(makeToday({ capture_on_closed_days: true }));

    const row = screen.getByText(CLOSED_DAYS);
    expect(row).toBeInTheDocument();
    // D-10 ni UI'dan yoqib-o'chirish 2-fazaning egaligida (§16.2).
    expect(row.closest("button")).toBeNull();
    expect(row.closest("label")).toBeNull();
  });

  test("`false` bo'lsa qator chizilmaydi", () => {
    renderCard(makeToday({ capture_on_closed_days: false }));

    expect(screen.queryByText(CLOSED_DAYS)).toBeNull();
  });
});
