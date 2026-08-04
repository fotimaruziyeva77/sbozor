/**
 * OGOHLANTIRISH ZONASI — G-3: DALIL-KADR BU YERGA HECH QACHON KIRMAYDI.
 *
 * =============================================================================
 * BU FAYLNING MARKAZIY DA'VOSI:
 *
 *   ⛔ OGOHLANTIRISH QATORIDA RASM, THUMBNAIL VA KADR HAVOLASI YO'Q (D-19).
 *
 *   Bu D-19 ning IKKINCHI mustaqil qulfi. Birinchisi — `snapshot-copy.
 *   test.mjs` dagi matn darvozasi: u `alert-list.tsx` va `alert-row.tsx`
 *   fayllarida taqiqlangan tokenlarni qidiradi. Ikkalasi BOSHQA narsani
 *   o'lchaydi va biri ikkinchisining o'rnini bosmaydi:
 *
 *     matn darvozasi -> «bu ikki faylda hech qachon yozilmagan»
 *     bu test       -> «RENDER natijasida tasvir elementi yo'q»
 *
 *   Ya'ni rasm uchinchi komponent orqali kelib qolsa (`AlertRow` ichiga
 *   yangi bola qo'shilsa) matn darvozasi uni KO'RMAYDI, bu test esa
 *   ko'radi. Rejaning sabotaj bandi aynan shu ikkilikni o'lchaydi.
 * =============================================================================
 *
 * Qolgan da'volar (§6.7, §12.6, D-22):
 *   * `occurrences > 1` da takror soni KO'RINADI — guruhlash ma'lumot
 *     yashirish bo'lib ko'rinmasligi kerak;
 *   * `notified_at === null` qatori YASHIRILMAYDI — «alert bor deb
 *     o'ylash» yolg'onining yagona qarshi dalili;
 *   * zona `alert` e'lon rolini OLMAYDI — u holat, hodisa emas;
 *   * yopish/bostirish tugmasi UMUMAN qurilmaydi;
 *   * Z-3: ochiq ogohlantirish yo'q bo'lsa zona render qilinmaydi.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import messages from "../../../messages/uz-Latn.json";
import { AlertList } from "@/components/snapshots/alert-list";
import type { AlertEvent } from "@/lib/api-types";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";
import { alertsKey } from "@/lib/snapshot-queries";

const MARKET_ID = "11111111-1111-4111-8111-111111111111";

const NOT_NOTIFIED = messages.snapshots.alertNotNotified;
const CAPTURE_STOPPED = messages.snapshots.alertKey.captureStopped;
const SHOW_CLOSED = messages.snapshots.showClosed;

function makeAlert(overrides: Partial<AlertEvent> = {}): AlertEvent {
  return {
    id: "44444444-4444-4444-8444-444444444444",
    alert_key: "capture_stopped",
    severity: "critical",
    subject_id: null,
    first_seen_at: "2026-09-01T02:02:00Z",
    last_seen_at: "2026-09-01T02:35:00Z",
    occurrences: 1,
    notified_at: "2026-09-01T02:05:00Z",
    resolved_at: null,
    detail: {},
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

function renderList(
  items: readonly AlertEvent[],
  options: { closed?: boolean } = {},
): ReturnType<typeof render> {
  const closed = options.closed ?? false;
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: Infinity },
      mutations: { retry: false },
    },
  });
  client.setQueryData(alertsKey(MARKET_ID, closed), { items: [...items] });

  const tree: ReactElement = (
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      now={new Date("2026-09-01T02:38:00Z")}
      timeZone="Asia/Tashkent"
    >
      <QueryClientProvider client={client}>
        <AuthProvider>
          <AlertList closed={closed} onClosedChange={() => {}} poll={false} />
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
 * ⛔ G-3 — DALIL-KADR YO'Q (D-19)
 * ------------------------------------------------------------------------ */

describe("G-3: ogohlantirishda dalil-kadr yo'q", () => {
  test("⛔ RENDER natijasida birorta tasvir elementi yo'q", () => {
    const { container } = renderList([
      makeAlert({ detail: { camera_count: 22, error_code: "capture_timeout" } }),
    ]);

    // Qator haqiqatan chizilganini avval tasdiqlaymiz — aks holda
    // «tasvir yo'q» da'vosi BO'SH DOM ustida jimgina yashil bo'lardi.
    expect(screen.getByText(CAPTURE_STOPPED)).toBeInTheDocument();

    expect(container.querySelectorAll("img")).toHaveLength(0);
    expect(container.querySelectorAll("picture")).toHaveLength(0);
    expect(container.querySelectorAll("[style*='background-image']")).toHaveLength(0);
  });

  test("⛔ birorta havola kadrga OLIB BORMAYDI", () => {
    const { container } = renderList([makeAlert()]);

    const targets = [...container.querySelectorAll("a")].map((node) =>
      node.getAttribute("href"),
    );
    for (const href of targets) {
      expect(href ?? "").not.toContain("/snapshots/");
      expect(href ?? "").not.toContain("/image");
    }
  });
});

/* ---------------------------------------------------------------------------
 * D-22 — GURUHLASH MA'LUMOT YASHIRISH EMAS
 * ------------------------------------------------------------------------ */

describe("takrorlar soni", () => {
  test("`occurrences > 1` da takror soni ko'rinadi", () => {
    renderList([makeAlert({ occurrences: 47 })]);

    const repeated = messages.snapshots.alertRepeated.replace("{count}", "47");
    expect(screen.getByText(repeated)).toBeInTheDocument();
  });

  test("`occurrences === 1` da qator chizilmaydi (nazorat)", () => {
    renderList([makeAlert({ occurrences: 1 })]);

    const repeated = messages.snapshots.alertRepeated.replace("{count}", "1");
    expect(screen.queryByText(repeated)).toBeNull();
  });
});

/* ---------------------------------------------------------------------------
 * ⛔ `notified_at === null` — QATOR YASHIRILMAYDI
 * ------------------------------------------------------------------------ */

describe("Telegram xabarining holati", () => {
  test("⛔ `notified_at === null` da «yuborilmadi» qatori CHIQADI", () => {
    renderList([makeAlert({ notified_at: null })]);

    const row = screen.getByText(NOT_NOTIFIED);
    expect(row).toBeInTheDocument();
    // Sabab `title` da — «nega yuborilmadi?» javobsiz qolmaydi.
    expect(row).toHaveAttribute("title", messages.snapshots.alertNotNotifiedWhy);
  });

  test("`notified_at` bor bo'lsa yuborilgan vaqti ko'rinadi (nazorat)", () => {
    renderList([makeAlert({ notified_at: "2026-09-01T02:05:00Z" })]);

    expect(screen.queryByText(NOT_NOTIFIED)).toBeNull();
    expect(document.body.textContent).toContain("Telegram");
  });
});

/* ---------------------------------------------------------------------------
 * ZONANING SEMANTIKASI VA AMALLARI (§6.7, §12.6)
 * ------------------------------------------------------------------------ */

describe("zonaning semantikasi", () => {
  test("⛔ zona e'lon rolini OLMAYDI — u holat, hodisa emas", () => {
    const { container } = renderList([makeAlert()]);

    expect(container.querySelector("[role='alert']")).toBeNull();
    expect(container.querySelector("ul")).not.toBeNull();
  });

  test("⛔ yopish/bostirish tugmasi UMUMAN yo'q", () => {
    renderList([makeAlert(), makeAlert({ id: "55555555-5555-4555-8555-555555555555" })]);

    // Zonada BIRORTA tugma yo'q: yagona boshqaruv — ko'rsatish filtri
    // (checkbox), va u tugma emas.
    expect(screen.queryAllByRole("button")).toHaveLength(0);
    expect(screen.getByLabelText(SHOW_CLOSED)).toBeInTheDocument();
  });

  test("⛔ Z-3 — ochiq ogohlantirish yo'q bo'lsa zona UMUMAN render qilinmaydi", () => {
    const { container } = renderList([]);

    expect(container).toBeEmptyDOMElement();
  });

  test("Z-4 — `closed` yoqilgan, lekin tarix bo'sh: zona chiziladi va bo'sh holat chiqadi", () => {
    renderList([], { closed: true });

    expect(
      screen.getByText(messages.snapshots.emptyClosedAlerts),
    ).toBeInTheDocument();
    expect(screen.getByLabelText(SHOW_CLOSED)).toBeInTheDocument();
  });
});
