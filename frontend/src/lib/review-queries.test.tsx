/**
 * IKKI NAVBATNING SO'ROV QATLAMI VA NAZORATCHINING UYI.
 *
 * =============================================================================
 * ⛔ 1. IKKI MODUL, IKKI PREFIKS — VA BU DARVOZANING ASOSI.
 *
 *   `blind-audit-queries.ts` ALOHIDA fayl, chunki G-12 darvozasi FAYL
 *   TO'PLAMINI skanerlaydi (05-UI-SPEC §5.3). Bu yerda uning IKKINCHI
 *   yarmi o'lchanadi: kalitlar HAQIQATAN ajralganmi. Prefiks bir xil
 *   bo'lsa, ko'r sessiyaning `removeQueries` i noaniq navbatning
 *   holatini ham o'chirardi — ya'ni ajralish shakl emas, XULQ.
 *
 * ⛔ 2. KO'RMASDAN TEKSHIRISH KARTASI DOM TARTIBIDA BIRINCHI.
 *
 *   05-RESEARCH §C.8: kunlik byudjetli navbat vaqt bosimi yaratadi.
 *   Noaniq navbat birinchi bo'lsa, xolis o'lchov kunning oxiriga —
 *   charchagan holatga — surilardi. Tartib O'LCHOV USTUVORLIGINI
 *   ko'rsatadi va shuning uchun u LITERAL test bilan qulflanadi.
 *
 * ⛔ 3. PROGRESS BAR YO'Q (§7.3 [QAROR]).
 *
 *   Bar navbatni TUGATILADIGAN O'YINGA aylantiradi. Shart DOM asosida
 *   o'lchanadi, chunki «biz bar qurmadik» degan da'vo keyingi ijrochiga
 *   ko'rinmaydi — test esa ko'rinadi.
 *
 * ⚠ 4. TIP TIZIMI YOLG'IZ YETARLI EMAS (04-02 da o'lchangan):
 *   `domainKey("blind-audit", "next")` TIP JIHATIDAN YAROQLI va u kalitni
 *   HAMMA bozor uchun bir xil qilardi. Shuning uchun kalit SHAKLI shu
 *   yerda QIYMAT bo'yicha qulflanadi.
 * =============================================================================
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, renderHook, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

const apiClientMock = vi.hoisted(() => ({ apiFetch: vi.fn() }));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiClientMock.apiFetch };
});

import messages from "../../messages/uz-Latn.json";
import ReviewHomePage from "@/app/[locale]/(app)/review/page";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";
import {
  blindBudgetKey,
  blindNextKey,
  blindPrefix,
  useBlindBudget,
  useBlindNext,
} from "@/lib/blind-audit-queries";
import {
  evidenceImageKey,
  reviewBudgetKey,
  uncertainNextKey,
  useAnswerUncertainItem,
  useReviewBudget,
  useUncertainNext,
} from "@/lib/review-queries";

const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const OTHER_MARKET_ID = "99999999-9999-4999-8999-999999999999";
const ASSIGNMENT_ID = "22222222-2222-4222-8222-222222222222";
const SNAPSHOT_ID = "55555555-5555-4555-8555-555555555555";
const DAY = "2026-09-14";

let client: QueryClient;

function seedSession(roles: readonly string[]): void {
  setSession({
    accessToken: "test-access-token",
    principal: {
      userId: "33333333-3333-4333-8333-333333333333",
      phone: "+998900000000",
      fullName: "Test Inspector",
      roles: [...roles],
      marketId: MARKET_ID,
      marketName: "Karmana markaziy bozori",
      isPlatformAdmin: false,
      locale: "uz-Latn",
      mustChangePassword: false,
    },
    markets: [],
  });
}

function wrapper({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={client}>
      <AuthProvider>{children}</AuthProvider>
    </QueryClientProvider>
  );
}

function renderHome() {
  return render(
    <QueryClientProvider client={client}>
      <AuthProvider>
        <NextIntlClientProvider
          locale="uz-Latn"
          messages={messages}
          timeZone="Asia/Tashkent"
        >
          <ReviewHomePage />
        </NextIntlClientProvider>
      </AuthProvider>
    </QueryClientProvider>,
  );
}

function budgetPayload(answered: {
  blind: number;
  blindMax: number;
  uncertain: number;
  uncertainMax: number;
  /*
   * ⚠ `available` — NAVBATDA nechta ish bor; byudjetdan MUSTAQIL (261003).
   *   Standart qiymat ATAYIN musbat: bu faylning qolgan testlari «ish bor,
   *   faqat chegara tugadi» holatini o'lchaydi va nol standart ularni
   *   jimgina «ish yo'q» holatiga aylantirib yuborardi.
   */
  blindAvailable?: number;
  uncertainAvailable?: number;
}) {
  return {
    day: DAY,
    uncertain: {
      answered: answered.uncertain,
      budget: answered.uncertainMax,
      remaining: Math.max(0, answered.uncertainMax - answered.uncertain),
      available: answered.uncertainAvailable ?? 99,
    },
    blind_audit: {
      answered: answered.blind,
      budget: answered.blindMax,
      remaining: Math.max(0, answered.blindMax - answered.blind),
      available: answered.blindAvailable ?? 99,
    },
  };
}

beforeEach(() => {
  vi.resetAllMocks();
  client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  seedSession(["inspector"]);
});

afterEach(() => {
  client.clear();
  clearSession();
});

/* -------------------------------------------------------------------------- */
/* 1. KESH KALITLARI                                                          */
/* -------------------------------------------------------------------------- */

describe("kesh kalitlari tug'ilishidanoq doiralangan", () => {
  test("noaniq navbat kalitlari bozor identifikatorini olib yuradi", () => {
    /*
     * ⚠ REJANING QABUL MEZONI «birinchi element `m1`» deydi; `domainKey`
     *   ning HAQIQIY shakli esa `["m", marketId, …]` (05-09 deviatsiya
     *   #14 dagi bilan aynan bir xil aniqlik). Mezonning NIYATI — kalit
     *   tug'ilishidanoq doiralangan — to'liq bajarilgan va u shu yerda
     *   ikkala element bo'yicha ham qulflanadi.
     */
    expect(uncertainNextKey("m1")).toEqual(["m", "m1", "review-uncertain", "next"]);
    expect(reviewBudgetKey("m1", DAY)).toEqual([
      "m",
      "m1",
      "review-budget",
      DAY,
    ]);
    expect(evidenceImageKey("m1", SNAPSHOT_ID)).toEqual([
      "m",
      "m1",
      "review-evidence",
      SNAPSHOT_ID,
    ]);
  });

  test("⛔ ko'r audit kalitlari ALOHIDA prefiksda", () => {
    expect(blindNextKey("m1")).toEqual(["m", "m1", "blind-audit", "next"]);
    expect(blindBudgetKey("m1", DAY)).toEqual([
      "m",
      "m1",
      "blind-audit",
      "budget",
      DAY,
    ]);
    expect(blindPrefix("m1")).toEqual(["m", "m1", "blind-audit"]);
  });

  test("⛔ ko'r prefiks noaniq navbat kalitlarini QAMRAMAYDI", () => {
    /*
     * TanStack kalitni PREFIKS bo'yicha solishtiradi. Agar ikkala navbat
     * bir prefiksda yashasa, ko'r sessiyaning `removeQueries` i noaniq
     * navbatning bandini ham o'chirardi va nazoratchi boshqa sessiyada
     * ko'rib turgan bandini YO'QOTARDI. Bu — ikki modulning XULQDAGI
     * farqi, shakldagi emas.
     */
    const prefix = blindPrefix("m1") as readonly unknown[];
    const uncertain = uncertainNextKey("m1") as readonly unknown[];
    const budget = reviewBudgetKey("m1", DAY) as readonly unknown[];

    const startsWith = (key: readonly unknown[]) =>
      prefix.every((part, index) => key[index] === part);

    expect(startsWith(uncertain)).toBe(false);
    expect(startsWith(budget)).toBe(false);
    // Nazorat: o'z kalitlarini esa QAMRAYDI.
    expect(startsWith(blindNextKey("m1") as readonly unknown[])).toBe(true);
    expect(startsWith(blindBudgetKey("m1", DAY) as readonly unknown[])).toBe(
      true,
    );
  });

  test("kalitlar bozorlar bo'yicha AJRALADI", () => {
    expect(uncertainNextKey(MARKET_ID)).not.toEqual(
      uncertainNextKey(OTHER_MARKET_ID),
    );
    expect(blindNextKey(MARKET_ID)).not.toEqual(blindNextKey(OTHER_MARKET_ID));
  });
});

/* -------------------------------------------------------------------------- */
/* 2. POLL YO'Q (§8.5)                                                        */
/* -------------------------------------------------------------------------- */

describe("⛔ navbat SO'ROV BO'YICHA yuriydi — poll yo'q", () => {
  test("band va byudjet so'rovlarida `refetchInterval` sozlanmagan", async () => {
    apiClientMock.apiFetch.mockResolvedValue(
      budgetPayload({ blind: 0, blindMax: 30, uncertain: 0, uncertainMax: 50 }),
    );

    const { result } = renderHook(() => useReviewBudget(DAY), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    /*
     * ⚠ TIP QO'LDA OCHILADI: `QueryOptions` bu observer-darajasidagi
     *   maydonni e'lon qilmaydi (`camera-zone-queries.test.tsx:255`
     *   dagi bilan aynan bir xil holat).
     */
    const cached = client.getQueryCache().getAll();
    expect(cached.length).toBeGreaterThan(0);
    for (const query of cached) {
      const options = query.options as { refetchInterval?: unknown };
      expect(options.refetchInterval).toBeUndefined();
    }
  });
});

/* -------------------------------------------------------------------------- */
/* 2b. KO'R SO'ROVLAR XOTIRADA QOLMAYDI (§14.3, 4-qatlam)                     */
/* -------------------------------------------------------------------------- */

describe("⛔ ko'r so'rovlar keshda YASHAMAYDI", () => {
  test("`gcTime` va `staleTime` IKKALASI ham NOL", async () => {
    /*
     * =====================================================================
     * ⚠⚠ BU TEST SABOTAJ O'LCHOVIDAN KEYIN QO'SHILDI — VA SABAB MUHIM.
     *
     * `removeQueries` -> `invalidateQueries` sabotaji `blind-session.
     * test.tsx` ning O'N SAKKIZTA testini ham YASHIL qoldirdi va faqat
     * STATIK darvoza (G-14b) qizardi. Sabab strukturaviy: oshkor
     * ma'lumot keshga UMUMAN tushmaydi (u mutatsiya natijasi), ya'ni
     * kesh skani ikki chaqiruvni AJRATA OLMAYDI. `invalidate` keshda
     * qoldiradigan narsa — BAND payloadi — esa `gcTime: 0` tufayli
     * kuzatuvchi uzilishi bilan baribir o'chadi.
     *
     * Ya'ni bugungi kafolat JUFTLIKDAN chiqadi: `gcTime: 0` OYNANI
     * yopadi, `removeQueries` esa DARHOL tozalaydi. Statik darvoza
     * ikkinchisini qo'riqlaydi; bu test BIRINCHISINI — ya'ni
     * `gcTime` bir kun oshirilsa, `removeQueries` ning ma'nosi
     * qaytadi va darvoza yolg'iz qolmaydi.
     *
     * Bu 05-10 sabotaj D ning aynan sinfi: da'vo O'LCHANADIGAN farqdan
     * chiqishi kerak, kodning shaklidan emas.
     * =====================================================================
     */
    apiClientMock.apiFetch.mockResolvedValue(
      budgetPayload({ blind: 7, blindMax: 30, uncertain: 0, uncertainMax: 50 }),
    );

    renderHook(
      () => {
        useBlindNext();
        return useBlindBudget(DAY);
      },
      { wrapper },
    );

    await waitFor(() =>
      expect(client.getQueryCache().getAll().length).toBeGreaterThanOrEqual(2),
    );

    const blind = client
      .getQueryCache()
      .getAll()
      .filter((query) => query.queryKey[2] === "blind-audit");

    expect(blind.length).toBeGreaterThanOrEqual(2);
    for (const query of blind) {
      const options = query.options as {
        gcTime?: unknown;
        staleTime?: unknown;
      };
      expect(options.gcTime).toBe(0);
      expect(options.staleTime).toBe(0);
    }
  });
});

/* -------------------------------------------------------------------------- */
/* 3. JAVOB — BITTA BAND, BITTA SO'ROV (D-18)                                 */
/* -------------------------------------------------------------------------- */

describe("⛔ javob tanasi MASSIV EMAS (D-18)", () => {
  test("mutatsiya AYNAN bitta maydonli obyekt yuboradi", async () => {
    apiClientMock.apiFetch.mockResolvedValue({
      system_answer: "empty",
      human_answer: "occupied",
      matched: false,
      locked: true,
    });

    const { result } = renderHook(() => useAnswerUncertainItem(DAY), {
      wrapper,
    });

    await result.current.mutateAsync({
      assignmentId: ASSIGNMENT_ID,
      answer: "occupied",
    });

    const [path, options] = apiClientMock.apiFetch.mock.calls[0] as [
      string,
      { method: string; body: unknown },
    ];
    expect(path).toBe(`/review/${ASSIGNMENT_ID}/answer`);
    expect(options.method).toBe("POST");
    expect(Array.isArray(options.body)).toBe(false);
    expect(Object.keys(options.body as Record<string, unknown>)).toHaveLength(1);
  });

  test("navbat so'rovi 409 da QAYTA URINMAYDI", async () => {
    /*
     * Bo'sh navbat va tugagan byudjet 409 bilan keladi va ular NORMAL
     * holatlar. Qayta urinish ularni «xato» ga aylantirib, ekranni uch
     * marta qayta yuklardi va nazoratchi sababni ko'rmasdi.
     */
    apiClientMock.apiFetch.mockRejectedValue(new Error("conflict"));

    const { result } = renderHook(() => useUncertainNext(), { wrapper });
    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(apiClientMock.apiFetch).toHaveBeenCalledTimes(1);
  });
});

/* -------------------------------------------------------------------------- */
/* 4. NAZORATCHINING UYI (§7.2)                                               */
/* -------------------------------------------------------------------------- */

describe("`/review` uyi", () => {
  test("⛔ ko'rmasdan tekshirish kartasi DOM tartibida BIRINCHI", async () => {
    apiClientMock.apiFetch.mockResolvedValue(
      budgetPayload({ blind: 7, blindMax: 30, uncertain: 12, uncertainMax: 50 }),
    );

    renderHome();

    const headings = await screen.findAllByRole("heading", { level: 2 });
    expect(headings.map((node) => node.textContent)).toEqual([
      messages.review.blindTitle,
      messages.review.uncertainTitle,
    ]);
  });

  test("ikkala karta ham DOIM ko'rinadi — byudjet tugaganda ham", async () => {
    apiClientMock.apiFetch.mockResolvedValue(
      budgetPayload({
        blind: 30,
        blindMax: 30,
        uncertain: 50,
        uncertainMax: 50,
      }),
    );

    renderHome();

    expect(await screen.findAllByRole("heading", { level: 2 })).toHaveLength(2);
    // Tugagan karta FAKTNI o'zgartiradi, ekran tuzilishini emas.
    expect(screen.getAllByText(messages.review.budgetDone)).toHaveLength(2);
    for (const link of screen.getAllByText(messages.review.startBlind)) {
      expect(link).toHaveAttribute("aria-disabled", "true");
      expect(link).not.toHaveAttribute("href");
    }
  });

  /*
   * ========================================================================
   * ⛔⛔ BO'SH NAVBAT — BYUDJET TUGAGANIDAN BOSHQA HOLAT (261003).
   *
   * Jonli bazada o'lchandi: `blind_audit` navbatida 0 ta band bor va HECH
   * QACHON bo'lmagan (namuna CV'siz tortilmaydi), `uncertain` da esa
   * 2614 ta band kutyapti va BIRORTASIGA javob berilmagan.
   *
   * Ilgari ikkala holat ham `0 / 30` bo'lib bir xil chizilardi va tugma
   * FAOL turardi — nazoratchi birinchi kartani bosib bo'sh ekranga
   * tushardi, 2614 ta haqiqiy ish esa pastda ko'rinmay qolardi.
   * ========================================================================
   */
  test("⛔ navbat BO'SH bo'lsa tugma bosilmaydi va sabab yoziladi", async () => {
    apiClientMock.apiFetch.mockResolvedValue(
      budgetPayload({
        blind: 0,
        blindMax: 30,
        blindAvailable: 0,
        uncertain: 0,
        uncertainMax: 50,
        uncertainAvailable: 2614,
      }),
    );

    renderHome();

    // Ko'r audit: ish yo'q — nishon, sabab va O'LIK tugma.
    expect(await screen.findByText(messages.review.queueEmpty)).toBeInTheDocument();
    expect(screen.getByText(messages.review.blindEmptyNote)).toBeInTheDocument();

    const blind = screen.getByText(messages.review.startBlind);
    expect(blind).toHaveAttribute("aria-disabled", "true");
    expect(blind).not.toHaveAttribute("href");

    // ⛔ ASOSIY DA'VO: ikkinchi navbat SHU PAYTDA ishlaydi. Usiz test
    //    «hammasi o'chdi» holatini ham qanoatlantirardi.
    const uncertain = screen.getByText(messages.review.continueUncertain);
    expect(uncertain).not.toHaveAttribute("aria-disabled");
    expect(uncertain).toHaveAttribute("href");
  });

  test("navbat hajmi EKRANDA — byudjetdan alohida son", async () => {
    apiClientMock.apiFetch.mockResolvedValue(
      budgetPayload({
        blind: 0,
        blindMax: 30,
        blindAvailable: 0,
        uncertain: 0,
        uncertainMax: 50,
        uncertainAvailable: 2614,
      }),
    );

    renderHome();

    // 2614 — navbat; 50 — kunlik chegara. Ikkalasi AYRIM ko'rinadi.
    expect(
      await screen.findByText(
        messages.review.waiting.replace("{count}", "2614"),
      ),
    ).toBeInTheDocument();
  });

  test("⛔ byudjet ko'rsatkichi PROGRESS BAR emas", async () => {
    apiClientMock.apiFetch.mockResolvedValue(
      budgetPayload({ blind: 7, blindMax: 30, uncertain: 12, uncertainMax: 50 }),
    );

    const { container } = renderHome();
    await screen.findAllByRole("heading", { level: 2 });

    expect(container.querySelector("progress")).toBeNull();
    expect(screen.queryAllByRole("progressbar")).toHaveLength(0);
    // Hisoblagich esa BOR va u FAKTNI aytadi.
    expect(screen.getByText("Bugun: 7 / 30")).toBeInTheDocument();
    expect(screen.getByText("Bugun: 12 / 50")).toBeInTheDocument();
  });

  test("⛔ uy sahifasida CHECKBOX ham, ommaviy amal ham YO'Q (D-18)", async () => {
    apiClientMock.apiFetch.mockResolvedValue(
      budgetPayload({ blind: 7, blindMax: 30, uncertain: 12, uncertainMax: 50 }),
    );

    const { container } = renderHome();
    await screen.findAllByRole("heading", { level: 2 });

    expect(container.querySelectorAll('input[type="checkbox"]')).toHaveLength(0);
  });

  test("huquqsiz sessiyada so'rov UMUMAN ketmaydi", () => {
    seedSession(["cashier"]);
    renderHome();

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(apiClientMock.apiFetch).not.toHaveBeenCalled();
  });
});

/* -------------------------------------------------------------------------- */
/* 5. D-19 ILGAGI — NOL NATIJA, YO'QLIK ESA JIM                               */
/* -------------------------------------------------------------------------- */

describe("oxirgi qator (D-19 ilgagi)", () => {
  test("⛔ `default_empty === 0` bo'lganda ham RENDER bo'ladi", async () => {
    /*
     * NOL — NATIJA («kecha hamma rasta ko'rildi»), ma'lumotning yo'qligi
     * emas. Qatorni nolda yashirish adminning savolini javobsiz
     * qoldirardi (05-09 dagi S5 sabotajining aynan sinfi).
     */
    apiClientMock.apiFetch.mockImplementation((path: string) =>
      path.startsWith("/occupancy")
        ? Promise.resolve({ default_empty: 0 })
        : Promise.resolve(
            budgetPayload({
              blind: 7,
              blindMax: 30,
              uncertain: 12,
              uncertainMax: 50,
            }),
          ),
    );

    seedSession(["inspector", "market_admin"]);
    renderHome();

    expect(
      await screen.findByText(/Kecha: 0 ta rasta/, { exact: false }),
    ).toBeInTheDocument();
  });

  test("nolsiz qiymat ham AYNAN o'qiladi (trivial qanoatlanish emas)", async () => {
    apiClientMock.apiFetch.mockImplementation((path: string) =>
      path.startsWith("/occupancy")
        ? Promise.resolve({ default_empty: 4 })
        : Promise.resolve(
            budgetPayload({
              blind: 7,
              blindMax: 30,
              uncertain: 12,
              uncertainMax: 50,
            }),
          ),
    );

    seedSession(["inspector", "market_admin"]);
    renderHome();

    expect(
      await screen.findByText(/Kecha: 4 ta rasta/, { exact: false }),
    ).toBeInTheDocument();
  });

  test("⛔ `report_view` YO'Q bo'lsa qator CHIZILMAYDI va so'rov ham ketmaydi", async () => {
    /*
     * ⚠⚠ SOF `inspector` — bu sahifaning YAGONA egasi (§4.6) va unda
     *    `report_view` YO'Q. Nol yozib qo'yish «kecha hamma rasta
     *    ko'rildi» degan YOLG'ONNI aytardi. O'lchanmagan raqam ko'rilgan
     *    zahoti o'lchangan deb o'qiladi (T-05-04).
     */
    apiClientMock.apiFetch.mockResolvedValue(
      budgetPayload({ blind: 7, blindMax: 30, uncertain: 12, uncertainMax: 50 }),
    );

    renderHome();
    await screen.findAllByRole("heading", { level: 2 });

    expect(screen.queryByText(/Kecha:/)).not.toBeInTheDocument();
    for (const [path] of apiClientMock.apiFetch.mock.calls as [string][]) {
      expect(path.startsWith("/occupancy")).toBe(false);
    }
  });
});
