/**
 * ⛔⛔ FAZANING ENG MUHIM TESTI — KO'RLIKNING XULQ DARAJASIDAGI DARVOZASI.
 *
 * =============================================================================
 * ⚠⚠ BU FAYL O'ZI DARVOZA MAYDONIDA. `scripts/blind-payload.test.mjs`
 *    (G-12) `components/blind-audit/**` ning HAMMA kod faylini
 *    skanerlaydi — shu jumladan BU TESTNI. Shuning uchun taqiqlangan
 *    nomlar bu yerda LITERAL yozilmaydi: ular `api-types.ts` dagi
 *    `BLIND_FORBIDDEN_KEYS` reyestridan ITERATSIYA qilinadi.
 *
 *    Muqobil («bitta nomni qo'lda yozish») darvozani O'Z TESTI bilan
 *    qizartirardi va yagona «tuzatish» yo'li darvozani BO'SHATISH
 *    bo'lardi — 05-11 deviatsiya #7 ning aynan sinfi.
 *
 *    Natija rejadagidan KUCHLIROQ: bitta nom emas, REYESTRNING HAMMASI
 *    o'lchanadi, ustiga sxemaning UMUMIY qattiqligi ham.
 * =============================================================================
 *
 * TO'RTTA DA'VO:
 *
 *   G-13   Taqiqlangan kalitli payload PARSE PAYTIDA yiqiladi. G-12
 *          STATIK (kod nima yozilgan), bu esa DINAMIK (kod nima
 *          qiladi): server bir kun maydon qo'shsa, klient DARHOL
 *          qizaradi va maydon jimgina ekranga oqib o'tmaydi.
 *
 *   §7.7   Oshkor ma'lumot FAQAT mutatsiya natijasidan. Kesh grafida u
 *          umuman yo'q — ya'ni uni «oldinroq» ochib ko'rish yo'li ham
 *          yo'q.
 *
 *   D-17.4 Javobdan keyin sessiyada AYNAN BITTA faol boshqaruv qoladi va
 *          u OLDINGA yo'naladi. Orqaga qaytish yo'li ham tugmada, ham
 *          URL'da yo'q.
 *
 *   05-11  Ko'r payloadda `has_active_vendor` YO'Q, ya'ni «sotuvchi
 *          biriktirilgan» qatori bu sessiyada CHIZILMAYDI. Tasodifiy
 *          namunadagi notekis diqqat — o'lchov asbobining O'ZIDAGI
 *          og'ish.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { readFileSync } from "node:fs";
import path from "node:path";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

const apiClientMock = vi.hoisted(() => ({
  apiFetch: vi.fn(),
  apiRequest: vi.fn(),
}));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return {
    ...actual,
    apiFetch: apiClientMock.apiFetch,
    apiRequest: apiClientMock.apiRequest,
  };
});

import messages from "../../../messages/uz-Latn.json";
import { BlindSession } from "@/components/blind-audit/blind-session";
import { ApiError } from "@/lib/api-client";
import { BLIND_FORBIDDEN_KEYS, blindAuditItemSchema } from "@/lib/api-types";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const ASSIGNMENT_ID = "22222222-2222-4222-8222-222222222222";
const SNAPSHOT_ID = "55555555-5555-4555-8555-555555555555";
const STALL_ID = "44444444-4444-4444-8444-444444444444";

/** Serverning HAQIQIY javobi — `BlindItemResponse` ning o'n maydoni. */
const CLEAN_ITEM = {
  assignment_id: ASSIGNMENT_ID,
  snapshot_id: SNAPSHOT_ID,
  stall_id: STALL_ID,
  stall_code: "14-C",
  zone_name: "Sabzavot qatori",
  camera_name: "Kamera 03",
  channel_no: 3,
  business_date: "2026-09-14",
  slot_time: "07:00:00",
  polygon: [
    [0.1, 0.2],
    [0.6, 0.2],
    [0.6, 0.8],
    [0.1, 0.8],
  ],
};

const BUDGET = {
  day: "2026-09-14",
  uncertain: { answered: 12, budget: 50, remaining: 38 },
  blind_audit: { answered: 7, budget: 30, remaining: 23 },
};

const REVEAL = {
  system_answer: "empty",
  human_answer: "occupied",
  matched: false,
  locked: true,
};

let client: QueryClient;

function seedSession(): void {
  setSession({
    accessToken: "test-access-token",
    principal: {
      userId: "33333333-3333-4333-8333-333333333333",
      phone: "+998900000000",
      fullName: "Test Inspector",
      roles: ["inspector"],
      marketId: MARKET_ID,
      marketName: "Karmana markaziy bozori",
      isPlatformAdmin: false,
      locale: "uz-Latn",
      mustChangePassword: false,
    },
    markets: [],
  });
}

function renderSession(node: ReactNode = <BlindSession exitHref="/uz/review" />) {
  return render(
    <QueryClientProvider client={client}>
      <AuthProvider>
        <NextIntlClientProvider
          locale="uz-Latn"
          messages={messages}
          timeZone="Asia/Tashkent"
        >
          {node}
        </NextIntlClientProvider>
      </AuthProvider>
    </QueryClientProvider>,
  );
}

function routeFetch(overrides: { next?: () => Promise<unknown> } = {}) {
  apiClientMock.apiFetch.mockImplementation((path: string) => {
    if (path.startsWith("/review/budget")) return Promise.resolve(BUDGET);
    if (path.endsWith("/answer")) return Promise.resolve(REVEAL);
    if (path.startsWith("/review/blind/next")) {
      return overrides.next?.() ?? Promise.resolve(CLEAN_ITEM);
    }
    return Promise.reject(new Error(`kutilmagan yo'l: ${path}`));
  });
}

function imageOk(): void {
  apiClientMock.apiRequest.mockResolvedValue({
    blob: () => Promise.resolve(new Blob(["x"], { type: "image/jpeg" })),
  });
}

function answerButtons(): HTMLElement[] {
  return [
    screen.getByRole("button", { name: /Band$/ }),
    screen.getByRole("button", { name: /Bo'sh$/ }),
    screen.getByRole("button", { name: /Aniq ayta olmayman$/ }),
  ];
}

async function readyFrame(): Promise<HTMLElement> {
  routeFetch();
  imageOk();
  const { container } = renderSession();
  fireEvent.load(await screen.findByRole("img"));
  await waitFor(() =>
    expect(answerButtons()[0]).not.toHaveAttribute("aria-disabled"),
  );
  return container;
}

beforeEach(() => {
  vi.resetAllMocks();
  client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  seedSession();
  globalThis.URL.createObjectURL = vi.fn(() => "blob:evidence");
  globalThis.URL.revokeObjectURL = vi.fn();
});

afterEach(() => {
  client.clear();
  clearSession();
});

/* -------------------------------------------------------------------------- */
/* G-13 — SXEMANING QATTIQLIGI (XULQ DARAJASI)                                */
/* -------------------------------------------------------------------------- */

describe("⛔⛔ G-13: taqiqlangan kalitli payload PARSE PAYTIDA yiqiladi", () => {
  test("reyestr QISQARTIRILMAGAN (§S-10 quyi chegarasi)", () => {
    /*
     * Usiz reyestr bo'shatilsa quyidagi sikl BO'SH TO'PLAM ustida
     * aylanib, abadiy yashil qolardi — ya'ni «darvoza bor» degan yolg'on
     * da'vo. Chegara `blind-payload.test.mjs::MIN_FORBIDDEN_NAMES` bilan
     * bir xil mantiqda QUYI: yangi nom qo'shilganda bu son o'zgarmaydi.
     */
    expect(BLIND_FORBIDDEN_KEYS.length).toBeGreaterThanOrEqual(13);
    expect(new Set(BLIND_FORBIDDEN_KEYS).size).toBe(
      BLIND_FORBIDDEN_KEYS.length,
    );
  });

  test("toza payload PARSE BO'LADI (nazorat)", () => {
    /*
     * ⛔ SALBIY NAZORAT MAJBURIY: sxema HAMMA NARSANI rad etsa,
     *   quyidagi ijobiy testlar ham yashil bo'lardi va darvoza
     *   «ishlayapti» deb ko'rinardi. Bu 05-06 S4 va 05-09 S4 ning
     *   aynan sinfi — trivial qanoatlanish.
     */
    expect(() => blindAuditItemSchema.parse(CLEAN_ITEM)).not.toThrow();
    expect(Object.keys(blindAuditItemSchema.parse(CLEAN_ITEM))).toHaveLength(10);
  });

  test("REYESTRDAGI HAR BIR nom payloadga qo'shilsa `parse` THROW qiladi", () => {
    for (const key of BLIND_FORBIDDEN_KEYS) {
      expect(() =>
        blindAuditItemSchema.parse({ ...CLEAN_ITEM, [key]: "x" }),
      ).toThrow();
    }
  });

  test("⚠ REYESTRDA YO'Q ortiqcha maydon ham THROW qiladi", () => {
    /*
     * `z.strictObject` reyestrni BILMAYDI — u ORTIQCHA maydonni rad
     * etadi. Ya'ni himoya ro'yxatga bog'liq emas: ertaga serverga
     * `risk_score` qo'shilsa ham klient darhol qizaradi.
     *
     * ⛔ `has_active_vendor` HAM SHU YERDA (05-11 qarori): noaniq
     *    navbatda u BOR, ko'r payloadda esa YO'Q.
     */
    expect(() =>
      blindAuditItemSchema.parse({ ...CLEAN_ITEM, risk_score: 0.9 }),
    ).toThrow();
    expect(() =>
      blindAuditItemSchema.parse({ ...CLEAN_ITEM, has_active_vendor: true }),
    ).toThrow();
  });
});

/* -------------------------------------------------------------------------- */
/* §7.7 — OSHKOR MA'LUMOT FAQAT MUTATSIYADAN                                  */
/* -------------------------------------------------------------------------- */

describe("⛔ oshkor ma'lumot kesh grafiga TUSHMAYDI", () => {
  test("`reveal-panel.tsx` da `useQuery` YO'Q — u `useMutation` natijasini oladi", () => {
    /*
     * STATIK shart, lekin u AYNAN SHU YERDA yashaydi: `blind-payload.
     * test.mjs` taqiqlangan NOMLARNI skanerlaydi, `useQuery` esa
     * taqiqlangan nom emas — u taqiqlangan MANBA. Ikkinchi so'rov
     * qatlami oshkor ma'lumotni kesh grafiga olib kirardi va uni
     * DevTools bilan javobdan OLDIN ochish mumkin bo'lardi.
     */
    const source = readFileSync(
      path.join(import.meta.dirname, "reveal-panel.tsx"),
      "utf8",
    );
    expect(source.includes("useQuery")).toBe(false);
    expect(source.includes("apiFetch")).toBe(false);
    // Nazorat: skaner haqiqatan FAYLNI o'qidi.
    expect(source.includes("RevealPanel")).toBe(true);
  });

  test("javobdan OLDIN oshkor panel RENDER BO'LMAYDI", async () => {
    await readyFrame();

    /*
     * ⚠ AYNAN MOS KELISH: `/Tizim javobi/` regexi LENTANING «Tizim
     *   javobini ko'rmaysiz» jumlasini ham ushlab, testni YOLG'ON
     *   qizartirardi — va uni «tuzatgan» ijrochi aynan ko'rlikni
     *   tushuntiruvchi jumlani o'chirgan bo'lardi (G-15 dagi `ъ`
     *   diskriminatorining aynan sinfi).
     */
    expect(screen.queryByText(messages.review.systemAnswer)).not.toBeInTheDocument();
    expect(screen.queryByText(messages.review.answersMatch)).not.toBeInTheDocument();
    expect(screen.queryByText(messages.review.answersDiffer)).not.toBeInTheDocument();
    expect(screen.queryByText(messages.review.answerLocked)).not.toBeInTheDocument();
  });

  test("javobdan keyin ham oshkor ma'lumot KESHDA TOPILMAYDI", async () => {
    await readyFrame();
    fireEvent.click(answerButtons()[0]);
    await screen.findByText(messages.review.answersDiffer);

    /*
     * Butun kesh grafi rekursiv skanerlanadi: oshkor javobning birorta
     * maydoni birorta kesh yozuvida bo'lmasligi SHART.
     */
    const dump = JSON.stringify(
      client.getQueryCache().getAll().map((query) => query.state.data),
    );
    expect(dump.includes("system_answer")).toBe(false);
    expect(dump.includes("matched")).toBe(false);
  });

  test("oshkor ma'lumotni beradigan `GET` so'rovi YUBORILMAYDI", async () => {
    await readyFrame();
    fireEvent.click(answerButtons()[0]);
    await screen.findByText(messages.review.answersDiffer);

    const paths = (apiClientMock.apiFetch.mock.calls as [string][]).map(
      ([p]) => p,
    );
    for (const p of paths) {
      const isKnown =
        p.startsWith("/review/blind/next") ||
        p.startsWith("/review/budget") ||
        p.endsWith("/answer");
      expect(isKnown).toBe(true);
    }
  });
});

/* -------------------------------------------------------------------------- */
/* D-17.4 — OLDINGA-FAQAT                                                     */
/* -------------------------------------------------------------------------- */

describe("⛔ javob O'ZGARMAS — sessiya OLDINGA-FAQAT", () => {
  test("javobdan keyin uchala tugma `aria-disabled`", async () => {
    await readyFrame();
    fireEvent.click(answerButtons()[0]);
    await screen.findByText(messages.review.answersDiffer);

    for (const button of answerButtons()) {
      expect(button).toHaveAttribute("aria-disabled", "true");
    }
  });

  test("⛔ javobdan keyin AYNAN BITTA faol boshqaruv qoladi", async () => {
    /*
     * DOM asosidagi TO'LIQ o'lchov: «orqaga qaytaruvchi tugma
     * qurmadik» degan da'vo keyingi ijrochiga ko'rinmaydi, bu son esa
     * ko'rinadi. Yagona faol tugma OLDINGA yo'naladi.
     *
     * ⚠ Yaqinlashtirish tugmasi ham javobdan keyin OLIB TASHLANADI
     *   (`evidence-frame.tsx::showZoom`): qaror allaqachon o'zgarmas,
     *   ya'ni kadrni qayta ochish faqat qayta o'ylashni taklif qilardi.
     */
    const container = await readyFrame();

    /* Nazorat: javobdan OLDIN faol tugmalar bir nechta (uch javob + …). */
    const before = container.querySelectorAll(
      'button:not([aria-disabled="true"])',
    );
    expect(before.length).toBeGreaterThan(1);

    fireEvent.click(answerButtons()[0]);
    await screen.findByText(messages.review.answersDiffer);

    const after = container.querySelectorAll(
      'button:not([aria-disabled="true"])',
    );
    expect(after).toHaveLength(1);
    expect(after[0]).toHaveTextContent(messages.review.next);
  });

  test("lentada «o'zgartirib bo'lmaydi» matni DOIM turadi (G-14d)", async () => {
    await readyFrame();
    expect(screen.getByText(messages.review.blindBanner)).toBeInTheDocument();

    fireEvent.click(answerButtons()[0]);
    await screen.findByText(messages.review.answersDiffer);
    expect(screen.getByText(messages.review.blindBanner)).toBeInTheDocument();
  });

  test("javob yozilgach ikkinchi urinish YANGI so'rov qilmaydi", async () => {
    await readyFrame();
    fireEvent.click(answerButtons()[0]);
    await screen.findByText(messages.review.answersDiffer);

    fireEvent.click(answerButtons()[1]);
    fireEvent.keyDown(window, { key: "3" });
    await new Promise((resolve) => setTimeout(resolve, 20));

    const answers = (apiClientMock.apiFetch.mock.calls as [string][]).filter(
      ([p]) => p.endsWith("/answer"),
    );
    expect(answers).toHaveLength(1);
  });

  test("tez ketma-ket uch bosish ham BITTA javob yuboradi", async () => {
    await readyFrame();

    fireEvent.click(answerButtons()[0]);
    fireEvent.click(answerButtons()[1]);
    fireEvent.click(answerButtons()[2]);

    await waitFor(() =>
      expect(
        (apiClientMock.apiFetch.mock.calls as [string][]).filter(([p]) =>
          p.endsWith("/answer"),
        ).length,
      ).toBe(1),
    );
  });
});

/* -------------------------------------------------------------------------- */
/* 05-11 — KO'R PAYLOADDA SOTUVCHI QATORI YO'Q                                */
/* -------------------------------------------------------------------------- */

describe("⛔ xolislik — sessiya diqqatni NOTEKIS taqsimlamaydi", () => {
  test("«sotuvchi biriktirilgan» qatori CHIZILMAYDI", async () => {
    await readyFrame();
    expect(
      screen.queryByText(messages.review.vendorAttached),
    ).not.toBeInTheDocument();
  });

  test("uch kanal: `<h1>`, doimiy lenta va marshrut", async () => {
    await readyFrame();

    const heading = screen.getByRole("heading", { level: 1 });
    expect(heading).toHaveTextContent(messages.review.blindTitle);
    expect(screen.getByText(messages.review.blindBanner)).toBeInTheDocument();
    /* Lenta OGOHLANTIRISH emas — u `role="alert"` OLMAYDI (§13.6). */
    expect(screen.queryAllByRole("alert")).toHaveLength(0);
  });
});

/* -------------------------------------------------------------------------- */
/* BO'SHLIKNING IKKI SABABI                                                   */
/* -------------------------------------------------------------------------- */

describe("bo'shlikning IKKI sababi ikki xil ekran beradi", () => {
  test("S-7 — namuna tugadi", async () => {
    routeFetch({
      next: () => Promise.reject(new ApiError(409, "review_queue_empty")),
    });
    renderSession();

    expect(await screen.findByText(messages.review.emptyBlindDone)).toBeInTheDocument();
    expect(
      screen.queryByText(messages.review.emptySampleNotDrawn),
    ).not.toBeInTheDocument();
  });

  test("⛔ S-9 — namuna HALI TANLANMAGAN, va «hozir tanla» tugmasi YO'Q", async () => {
    routeFetch({
      next: () => Promise.reject(new ApiError(409, "review_sample_not_drawn")),
    });
    const { container } = renderSession();

    expect(
      await screen.findByText(messages.review.emptySampleNotDrawn),
    ).toBeInTheDocument();
    expect(
      screen.queryByText(messages.review.emptyBlindDone),
    ).not.toBeInTheDocument();
    /* Bo'sh holatda birorta AMAL tugmasi yo'q. */
    expect(container.querySelectorAll("button")).toHaveLength(0);
  });

  test("S-8 — byudjet tugadi, «Yana ko'rish» YO'Q", async () => {
    routeFetch({
      next: () => Promise.reject(new ApiError(409, "review_budget_exhausted")),
    });
    const { container } = renderSession();

    expect(await screen.findByText(messages.review.emptyBudget)).toBeInTheDocument();
    expect(container.querySelectorAll("button")).toHaveLength(0);
  });
});
