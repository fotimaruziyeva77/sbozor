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
import { ALERT_TITLE_KEYS, alertDurationParts } from "@/components/snapshots/alert-row";
import type { AlertEvent } from "@/lib/api-types";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";
import { alertsKey } from "@/lib/snapshot-queries";

const MARKET_ID = "11111111-1111-4111-8111-111111111111";

const NOT_NOTIFIED = messages.snapshots.alertNotNotified;
const CAPTURE_STOPPED = messages.snapshots.alertKey.captureStopped;
const SHOW_CLOSED = messages.snapshots.showClosed;

/**
 * Davomiylik qatorining ⛔ O'ZGARMAS qismi — son EMAS.
 *
 * ⛔ Sonni da'voga qo'shish `Intl` ning uzilmas bo'shlig'iga bog'lanib
 *    qolardi (06-fazada o'lchangan sinf); bu yerda o'lchanadigan narsa
 *    esa qatorning MAVJUDLIGI.
 */
const DURATION_PATTERN = new RegExp(
  messages.snapshots.alertDuration.replace("{duration}", "").trim(),
  "u",
);

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

/* ---------------------------------------------------------------------------
 * ⛔ WR-11 — NOMA'LUM `severity` ENG PAST DARAJAGA TUSHIRILMAYDI
 *
 * ⛔⛔ NEGA BU ALOHIDA SINF: eski shakl (`?? SEVERITY_VIEW.info`) noma'lum
 *     darajani ENG ZARARSIZ qiymatga tushirardi. Backend `emergency`
 *     qo'shsa, admin uni ekranda ⛔ «Ma'lumot» ko'k nishoni bilan ko'rardi
 *     va eng shoshilinch signalni ⛔ E'TIBORSIZ qoldirardi.
 *
 * ⛔ Bu faylning O'Z qoidasi (`alert-row.tsx:75-77`) allaqachon shuni
 *    talab qiladi: «XOM KALIT EKRANGA HECH QACHON CHIQMAYDI» — ya'ni
 *    noma'lum qiymat NOMLANGAN zaxira oladi, xom satr ham, eng past
 *    daraja ham EMAS (`case-status-badge.tsx:38-43` naqshi).
 * ------------------------------------------------------------------------ */

describe("⛔ WR-11: noma'lum daraja ZAXIRA yorliq oladi", () => {
  test("⛔ `emergency` -> zaxira yorliq, «Ma'lumot» nishoni EMAS", () => {
    renderList([makeAlert({ severity: "emergency" })]);

    expect(
      screen.getByText(messages.snapshots.severityUnknown),
    ).toBeInTheDocument();

    /* ⛔ ENG PAST DARAJA CHIZILMAYDI — nosozlikning aynan o'zi shu edi. */
    expect(screen.queryByText(messages.snapshots.severity.info)).toBeNull();

    /* ⛔ XOM QIYMAT HAM EKRANDA YO'Q (faylning o'z qoidasi). */
    expect(document.body.textContent).not.toContain("emergency");
  });

  test("uchala MA'LUM daraja O'Z yorlig'ini oladi (nazorat)", () => {
    /*
     * ⛔ NAZORAT MAJBURIY: zaxira yorliqni HAR qatorga chizadigan
     *   regressiya yuqoridagi testni yashil qoldirardi.
     */
    for (const [severity, label] of [
      ["info", messages.snapshots.severity.info],
      ["warning", messages.snapshots.severity.warning],
      ["critical", messages.snapshots.severity.critical],
    ] as const) {
      const view = renderList([makeAlert({ severity })]);

      expect(screen.getByText(label)).toBeInTheDocument();
      expect(
        screen.queryByText(messages.snapshots.severityUnknown),
      ).toBeNull();

      view.unmount();
    }
  });
});

/* ---------------------------------------------------------------------------
 * ⛔ WR-12 — `NaN` EKRANGA CHIQA OLMAYDI
 *
 * `Date.parse` yaroqsiz satrda `NaN` beradi va `Math.max(1, NaN) === NaN`
 * (JS semantikasi), `NaN < 120` esa `false` — ya'ni eski shakl
 * `{ unit: "hour", value: NaN }` qaytarardi va `format.number(NaN, …)`
 * ekranga ⛔ «NaN soat» chizardi. To'qilgan qiymat sinfining aynan o'zi
 * (05-14).
 *
 * ⛔ TUZATISH `0` HAM, «—» HAM YOZMAYDI: o'lchanmagan davomiylik
 *    ⛔ UMUMAN chizilmaydi (D-10).
 * ------------------------------------------------------------------------ */

describe("⛔ WR-12: o'lchanmagan davomiylik CHIZILMAYDI", () => {
  test("sof funksiya yaroqsiz satrda `null` qaytaradi", () => {
    expect(alertDurationParts("bekor", "2026-09-01T03:00:00Z")).toBeNull();
    expect(alertDurationParts("2026-09-01T02:00:00Z", "bekor")).toBeNull();
  });

  test("⛔ yaroqsiz `resolved_at` -> «NaN» ham, davomiylik qatori ham YO'Q", () => {
    const { container } = renderList(
      [makeAlert({ resolved_at: "bekor-sana" })],
      { closed: true },
    );

    /* Qator haqiqatan chizilgan — aks holda da'vo BO'SH DOM ustida bo'lardi. */
    expect(screen.getByText(CAPTURE_STOPPED)).toBeInTheDocument();

    const text = container.textContent ?? "";
    /*
     * ⛔ IKKALA SHAKL HAM: `Intl` `NaN` ni LOCALE'GA tarjima qiladi
     *   (uz-Latn da «son emas»), ya'ni yolg'iz ASCII `NaN` da'vosi
     *   o'zbek ekranida ⛔ HECH NIMA o'lchamasdi — nosozlik yashil
     *   darvoza ostida o'tib ketardi (o'lchandi: RED bosqichida ekranda
     *   aynan «son emas soat davom etdi» chizilgan edi).
     */
    expect(text).not.toContain("NaN");
    expect(text.toLowerCase()).not.toContain("son emas");
    expect(text).not.toContain("Invalid");
    /* ⛔ «—» ham, yalang'och `0` ham to'qilmaydi. */
    expect(text).not.toContain("—");
    expect(
      screen.queryByText(DURATION_PATTERN),
    ).toBeNull();
  });

  test("yaroqli `resolved_at` da davomiylik CHIZILADI (nazorat)", () => {
    /*
     * ⛔ NAZORAT MAJBURIY: davomiylik qatorini BUTUNLAY o'chirgan
     *   regressiya yuqoridagi testni yashil qoldirardi.
     */
    renderList([makeAlert({ resolved_at: "2026-09-01T03:02:00Z" })], {
      closed: true,
    });

    expect(screen.getByText(DURATION_PATTERN)).toBeInTheDocument();
  });
});

/* ---------------------------------------------------------------------------
 * ⛔ 07 `deferred-items.md` №1 QO'SHIMCHASI — REYESTR RENDER HOLIDA
 *
 * ⛔⛔ G-36 (`snapshot-copy.test.mjs`) matn MAVJUDLIGINI qo'riqlaydi,
 *     ⛔ CHIZILISHINI emas — bu BOSHQA sinf. Kalit reyestrda va uchala
 *     locale'da bo'la turib, `AlertRow` uni chizmasligi mumkin (masalan
 *     xarita ikkinchi joyda takrorlanib ajralib ketsa). O'shanda G-36
 *     yashil qolardi, ekranda esa «Kutilmagan xato» turardi.
 *
 * ⛔ RO'YXAT QO'LDA YOZILMAYDI — ⛔ REYESTRDAN ITERATSIYA (05-13 darsi):
 *    qo'lda ro'yxat o'n yettinchi a'zo qo'shilganda JIMGINA eskirardi va
 *    darvoza «hammasi chizildi» deb yolg'on gapirardi.
 * ------------------------------------------------------------------------ */

/** 07-14 (D-17) da qo'shilgan to'rtlik — ⛔ QAMROV nazorati, render ro'yxati EMAS. */
const PHASE_07_14_KEYS = [
  "outbox_stale",
  "reconciliation_stale",
  "digest_stale",
  "overdue_stale",
] as const;

/** `"snapshots.alertKey.captureStopped"` -> o'sha kalitning uz-Latn matni. */
function messageAt(trail: string): string {
  const value = trail
    .split(".")
    .reduce<unknown>(
      (node, step) => (node as Record<string, unknown>)[step],
      messages,
    );
  if (typeof value !== "string") throw new Error(`matn topilmadi: ${trail}`);
  return value;
}

describe("⛔ ogohlantirish reyestri RENDER holida o'lchanadi", () => {
  test("07-14 ning to'rt kaliti REYESTRDA bor (qamrov nazorati)", () => {
    /*
     * ⛔ Bu test to'rttani CHIZMAYDI — u quyidagi ITERATSIYA ularni
     *   qamrab olishini kafolatlaydi. Reyestrdan biri tushib qolsa,
     *   iteratsiya uni jimgina o'tkazib yuborardi.
     */
    for (const key of PHASE_07_14_KEYS) {
      expect(Object.keys(ALERT_TITLE_KEYS)).toContain(key);
    }
  });

  test("⛔ HAR reyestr a'zosi O'Z sarlavhasi bilan chiziladi", () => {
    const entries = Object.entries(ALERT_TITLE_KEYS);

    /* ⛔ Bo'sh reyestr ustida sikl jimgina yashil bo'lardi. */
    expect(entries.length).toBeGreaterThanOrEqual(PHASE_07_14_KEYS.length);

    const { container } = renderList(
      entries.map(([alertKey], index) =>
        makeAlert({
          alert_key: alertKey,
          id: `44444444-4444-4444-8444-${String(index).padStart(12, "0")}`,
        }),
      ),
    );

    for (const [, trail] of entries) {
      expect(screen.getByText(messageAt(trail))).toBeInTheDocument();
    }

    /* ⛔ ZAXIRA YORLIQ 0 MARTA: reyestr a'zosi unga TUSHMASLIGI kerak. */
    expect(
      container.textContent?.includes(messages.errors.generic),
    ).toBe(false);
  });

  test("⛔ REYESTRDAN TASHQARIDAGI kalit zaxira yorliqni oladi (nazorat)", () => {
    /*
     * ⛔ Usiz yuqoridagi «zaxira 0 marta» da'vosi zaxira YO'LI butunlay
     *   buzilgan holatda ham yashil bo'lardi.
     */
    renderList([makeAlert({ alert_key: "sabotage_probe" })]);

    expect(screen.getByText(messages.errors.generic)).toBeInTheDocument();
  });
});
