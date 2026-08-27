/**
 * KUNLIK XULOSA — G-8: NOL NATIJA, UNING YO'QLIGI EMAS.
 *
 * =============================================================================
 * BU FAYLNING MARKAZIY DA'VOSI:
 *
 *   OLTALA HISOBLAGICH HAM DOIM RENDER QILINADI — HAMMASI NOL BO'LGANDA HAM.
 *
 *   Vasvasa aniq va u har ko'rikda qaytadi: «nol qatorlarni yashirsak
 *   ekran tozaroq bo'ladi». Bu 3-fazadagi «uch hisoblagich» muammosining
 *   aynan takrori [MEROS: 03-UI-SPEC §6.3]: nol qiymat — NATIJA, uning
 *   yo'qligi emas. «0 ta kadr olinmadi» va «olinmadi hisoblagichi umuman
 *   yo'q» — ikki butunlay boshqa da'vo, va aynan birinchisi bu ekranda
 *   aytilishi kerak.
 *
 *   ⛔ `planned === 0` esa BUTUNLAY BOSHQA hodisa (Z-7): u «hammasi nol»
 *      emas, «bu kun umuman rejalashtirilmagan». Ikkalasini bir xil
 *      ko'rsatish adminni «tizim ishlamayapti» degan xulosaga olib
 *      borardi, shuning uchun u yerda hisoblagichlar UMUMAN
 *      chizilmaydi va «0 / 0» ham chiqmaydi.
 * =============================================================================
 *
 * Qolgan da'volar (§6.3, §12.6):
 *   * `missed > 0` da qo'shimcha jumla va [Muammolilarni ko'rsatish]
 *     havolasi chiqadi — bu G-8 dan MUSTAQIL da'vo;
 *   * xulosa `role="status"`, `alert` EMAS — u hisobot, ogohlantirish emas;
 *   * `archived_present` bayrog'i qatorni yoqadi/o'chiradi.
 *
 * ⚠ MA'LUMOT KESHGA EKILADI, HTTP qatlami mock QILINMAYDI
 *   (`schedule-card.test.tsx:31-36` naqshi): bu yo'l HAQIQIY
 *   `useCaptureDay` ni va HAQIQIY `captureDayKey` fabrikasini ishlatadi.
 *   Kalit bir kun doiralashni yo'qotsa test JIMGINA yashil qolmaydi.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import messages from "../../../messages/uz-Latn.json";
import { DaySummary } from "@/components/snapshots/day-summary";
import type { CaptureDay, CaptureDaySummary } from "@/lib/api-types";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";
import { captureDayKey } from "@/lib/snapshot-queries";

const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const DAY = "2026-09-01";
/** Boshqa kun — poll SHARTI ma'lumotdan hosil bo'ladi, ya'ni o'chadi. */
const TODAY = "2026-09-03";

const COUNT_LABELS = [
  messages.snapshots.countOk,
  messages.snapshots.countDark,
  messages.snapshots.countBlank,
  messages.snapshots.countCorrupt,
  messages.snapshots.countFailed,
  messages.snapshots.countMissed,
];

const EMPTY_NO_PLAN = messages.snapshots.emptyNoPlan;
const SHOW_ISSUES_LINK = messages.snapshots.showIssuesLink;
const ARCHIVED_NOTE = messages.snapshots.archivedNote;

/** ⛔ HAMMASI NOL — G-8 ning kirish qiymati. */
function zeroSummary(
  overrides: Partial<CaptureDaySummary> = {},
): CaptureDaySummary {
  return {
    planned: 7,
    done: 0,
    ok: 0,
    dark: 0,
    blank: 0,
    corrupt: 0,
    failed: 0,
    missed: 0,
    ...overrides,
  };
}

function makeDay(overrides: Partial<CaptureDay> = {}): CaptureDay {
  return {
    day: DAY,
    summary: zeroSummary(),
    rows: [],
    archived_present: false,
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
function renderSummary(data: CaptureDay): ReturnType<typeof render> {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: Infinity },
      mutations: { retry: false },
    },
  });
  client.setQueryData(captureDayKey(MARKET_ID, DAY), data);

  const tree: ReactElement = (
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      timeZone="Asia/Tashkent"
    >
      <QueryClientProvider client={client}>
        <AuthProvider>
          <DaySummary day={DAY} onShowIssues={() => {}} todayIso={TODAY} />
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
 * ⛔ G-8 — OLTALA HISOBLAGICH NOL BILAN BIRGA
 * ------------------------------------------------------------------------ */

describe("G-8: nol hisoblagichlar", () => {
  test("⛔ hammasi nol bo'lganda ham OLTALA <dt>/<dd> juftligi render bo'ladi", () => {
    const { container } = renderSummary(makeDay());

    expect(container.querySelectorAll("dl dt")).toHaveLength(6);
    expect(container.querySelectorAll("dl dd")).toHaveLength(6);

    // Yorliqlar ham to'liq — «0» yolg'iz eshitilmasin (skrinrider).
    for (const label of COUNT_LABELS) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
  });

  test("nol qiymatning O'ZI ham ekranda — yorliq bilan bog'langan holda", () => {
    const { container } = renderSummary(makeDay());

    const values = [...container.querySelectorAll("dl dd")].map((node) =>
      node.textContent?.trim(),
    );
    expect(values).toEqual(["0", "0", "0", "0", "0", "0"]);
  });

  test("nolmas qiymatlar ham o'z joyida qoladi (nazorat)", () => {
    const { container } = renderSummary(
      makeDay({
        summary: zeroSummary({ planned: 175, done: 173, ok: 168, dark: 3, blank: 1, corrupt: 1, missed: 2 }),
      }),
    );

    const values = [...container.querySelectorAll("dl dd")].map((node) =>
      node.textContent?.trim(),
    );
    expect(values).toEqual(["168", "3", "1", "1", "0", "2"]);
  });
});

/* ---------------------------------------------------------------------------
 * Z-7 — `planned === 0` BUTUNLAY BOSHQA HODISA
 * ------------------------------------------------------------------------ */

describe("Z-7: kunda reja yo'q", () => {
  test("«rejalashtirilmagan» matni chiqadi va hisoblagichlar UMUMAN chizilmaydi", () => {
    const { container } = renderSummary(
      makeDay({ summary: zeroSummary({ planned: 0, done: 0 }) }),
    );

    expect(screen.getByText(EMPTY_NO_PLAN)).toBeInTheDocument();
    expect(container.querySelectorAll("dl dt")).toHaveLength(0);
  });

  test("⛔ «0 / 0 olindi» ko'rsatkichi CHIQMAYDI", () => {
    renderSummary(makeDay({ summary: zeroSummary({ planned: 0, done: 0 }) }));

    expect(document.body.textContent).not.toMatch(/0\s*\/\s*0/u);
  });

  test("`planned > 0` bo'lsa bo'sh holat CHIQMAYDI (nazorat)", () => {
    renderSummary(makeDay());

    expect(screen.queryByText(EMPTY_NO_PLAN)).toBeNull();
    expect(document.body.textContent).toMatch(/0\s*\/\s*7/u);
  });
});

/* ---------------------------------------------------------------------------
 * `missedCallout` — G-8 DAN MUSTAQIL DA'VO
 * ------------------------------------------------------------------------ */

describe("missedCallout", () => {
  test("`missed > 0` da qo'shimcha jumla VA havola chiqadi", () => {
    renderSummary(makeDay({ summary: zeroSummary({ missed: 2, done: 5 }) }));

    const callout = messages.snapshots.missedCallout.replace("{count}", "2");
    expect(screen.getByText(callout)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: SHOW_ISSUES_LINK }),
    ).toBeInTheDocument();
  });

  test("`missed === 0` da callout chizilmaydi", () => {
    renderSummary(makeDay());

    const callout = messages.snapshots.missedCallout.replace("{count}", "0");
    expect(screen.queryByText(callout)).toBeNull();
    expect(screen.queryByRole("button", { name: SHOW_ISSUES_LINK })).toBeNull();
  });
});

/* ---------------------------------------------------------------------------
 * ROL VA ARXIV QATORI (§6.3, §12.6)
 * ------------------------------------------------------------------------ */

describe("xulosaning roli va arxiv qatori", () => {
  test("xulosa `role='status'` — `alert` EMAS (u hisobot)", () => {
    const { container } = renderSummary(makeDay());

    expect(container.querySelector("[role='status']")).not.toBeNull();
    expect(container.querySelector("[role='alert']")).toBeNull();
  });

  test("`archived_present === true` da izoh qatori chiqadi, `false` da yo'q", () => {
    const { unmount } = renderSummary(makeDay({ archived_present: true }));
    expect(screen.getByText(ARCHIVED_NOTE)).toBeInTheDocument();
    unmount();

    renderSummary(makeDay({ archived_present: false }));
    expect(screen.queryByText(ARCHIVED_NOTE)).toBeNull();
  });
});
