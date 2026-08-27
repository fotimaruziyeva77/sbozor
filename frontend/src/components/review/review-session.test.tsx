/**
 * Y-2 SESSIYASI — DALIL DARVOZASI, BITTA BAND, BITTA JAVOB.
 *
 * =============================================================================
 * ⛔ 1. RASM YUKLANMASDAN QAROR YOZILMAYDI (§7.4)
 *
 *   Rasm ko'rilmagan qaror — MA'LUMOT EMAS, TAXMIN, va u trening
 *   to'plamiga ham, aniqlik hisobotiga ham KIRADI. Shuning uchun bu
 *   yerda IKKALA yo'nalish ham o'lchanadi: yuklanmaguncha tugmalar
 *   bloklangan VA `onError` dan keyin ham bloklangan bo'lib QOLADI.
 *   Ikkinchisi muhimroq — «xato bo'ldi, mayli, javob beray» eng tabiiy
 *   regressiya.
 *
 * ⛔ 2. BITTA JAVOB = BITTA `mutate` (D-18)
 *
 *   Klaviatura yorlig'ining `repeat` shakli ommaviy tasdiqlashning
 *   KLAVIATURA VARIANTI: tugmani bosib turish o'nlab javob yuborardi va
 *   ular hisobotga «nazoratchi tasdiqladi» bo'lib kirardi.
 *
 * ⛔ 3. G-18(b) — CHECKBOX YO'Q, MUTATSIYA TANASI MASSIV EMAS
 *
 *   Statik darvoza (`zone-copy.test.mjs`) MATNNI to'sadi; bu yerda esa
 *   YUZANING O'ZI o'lchanadi.
 *
 * ⛔ 4. S-7 ≠ S-8
 *
 *   «Navbat bo'sh» (ish tugadi) va «byudjet tugadi» (ish qolgan bo'lishi
 *   mumkin) bir xil ko'rinsa, nazoratchida «hammasi bajarildi» degan
 *   YOLG'ON hosil bo'lardi.
 * =============================================================================
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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
import {
  errorCodeOf,
  ReviewSession,
  sessionState,
} from "@/components/review/review-session";
import { frameState, overlayPoints } from "@/components/review/evidence-frame";
import { ApiError } from "@/lib/api-client";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const ASSIGNMENT_ID = "22222222-2222-4222-8222-222222222222";
const SNAPSHOT_ID = "55555555-5555-4555-8555-555555555555";
const STALL_ID = "44444444-4444-4444-8444-444444444444";

const ITEM = {
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
  ] as const,
  has_active_vendor: true,
};

const BUDGET = {
  day: "2026-09-14",
  uncertain: { answered: 12, budget: 50, remaining: 38 },
  blind_audit: { answered: 7, budget: 30, remaining: 23 },
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

function renderSession(node: ReactNode = <ReviewSession exitHref="/uz/review" />) {
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

/** Navbat + byudjet javoblarini yo'l bo'yicha ajratadi. */
function routeFetch(overrides: {
  next?: () => Promise<unknown>;
  answer?: () => Promise<unknown>;
}) {
  apiClientMock.apiFetch.mockImplementation((path: string) => {
    if (path.startsWith("/review/budget")) return Promise.resolve(BUDGET);
    if (path.endsWith("/answer")) {
      return (
        overrides.answer?.() ??
        Promise.resolve({
          system_answer: "empty",
          human_answer: "occupied",
          matched: false,
          locked: true,
        })
      );
    }
    if (path.startsWith("/review/uncertain/next")) {
      return overrides.next?.() ?? Promise.resolve(ITEM);
    }
    return Promise.reject(new Error(`kutilmagan yo'l: ${path}`));
  });
}

/** Kadr baytlari — `apiRequest` `Response` qaytaradi. */
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

beforeEach(() => {
  vi.resetAllMocks();
  client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  seedSession();
  // jsdom `createObjectURL` ni bilmaydi.
  globalThis.URL.createObjectURL = vi.fn(() => "blob:evidence");
  globalThis.URL.revokeObjectURL = vi.fn();
});

afterEach(() => {
  client.clear();
  clearSession();
});

/* -------------------------------------------------------------------------- */
/* 1. SOF FUNKSIYALAR — DOM'siz                                               */
/* -------------------------------------------------------------------------- */

describe("sof funksiyalar", () => {
  test("`frameState` tartibi: xato -> yuklanmoqda -> tayyor", () => {
    expect(
      frameState({
        isPending: true,
        isError: true,
        imageLoaded: false,
        imageFailed: false,
      }),
    ).toBe("failed");
    expect(
      frameState({
        isPending: false,
        isError: false,
        imageLoaded: false,
        imageFailed: true,
      }),
    ).toBe("failed");
    expect(
      frameState({
        isPending: true,
        isError: false,
        imageLoaded: false,
        imageFailed: false,
      }),
    ).toBe("loading");
    /* ⛔ Baytlar kelgan, LEKIN brauzer hali chizmagan — hali TAYYOR EMAS. */
    expect(
      frameState({
        isPending: false,
        isError: false,
        imageLoaded: false,
        imageFailed: false,
      }),
    ).toBe("loading");
    expect(
      frameState({
        isPending: false,
        isError: false,
        imageLoaded: true,
        imageFailed: false,
      }),
    ).toBe("ready");
  });

  test("`sessionState` uch xato kodini UCH XIL holatga ajratadi", () => {
    const base = { hasItem: false, isPending: false, isError: true };
    expect(sessionState({ ...base, errorCode: "review_queue_empty" })).toBe(
      "queue-empty",
    );
    expect(sessionState({ ...base, errorCode: "review_budget_exhausted" })).toBe(
      "budget-exhausted",
    );
    expect(sessionState({ ...base, errorCode: "review_sample_not_drawn" })).toBe(
      "sample-not-drawn",
    );
    expect(sessionState({ ...base, errorCode: "something_else" })).toBe("error");
    expect(sessionState({ ...base, errorCode: null })).toBe("error");
  });

  test("⛔ band EKRANDA qoladi — fon xatosi uni yo'qotmaydi", () => {
    expect(
      sessionState({
        hasItem: true,
        isPending: false,
        isError: true,
        errorCode: "review_queue_empty",
      }),
    ).toBe("ready");
  });

  test("`overlayPoints` normalangan koordinatani 1000 lik birlikka ko'chiradi", () => {
    expect(
      overlayPoints([
        [0, 0],
        [0.5, 0.25],
        [1, 1],
      ]),
    ).toBe("0,0 500,250 1000,1000");
  });

  test("`errorCodeOf` faqat `ApiError` dan kod oladi", () => {
    expect(errorCodeOf(new ApiError(409, "review_queue_empty"))).toBe(
      "review_queue_empty",
    );
    expect(errorCodeOf(new Error("boom"))).toBeNull();
    expect(errorCodeOf(null)).toBeNull();
  });
});

/* -------------------------------------------------------------------------- */
/* 2. DALIL DARVOZASI                                                         */
/* -------------------------------------------------------------------------- */

describe("⛔ dalil rasmi — qarorning DARVOZASI", () => {
  test("rasm `onLoad` bo'lmaguncha uchala tugma `aria-disabled`", async () => {
    routeFetch({});
    imageOk();
    renderSession();

    await screen.findByText(/14-C/);
    for (const button of answerButtons()) {
      expect(button).toHaveAttribute("aria-disabled", "true");
    }

    // `onLoad` -> darvoza ochiladi.
    fireEvent.load(await screen.findByRole("img"));
    await waitFor(() => {
      for (const button of answerButtons()) {
        expect(button).not.toHaveAttribute("aria-disabled");
      }
    });
  });

  test("⛔ `onError` dan KEYIN ham `aria-disabled` bo'lib QOLADI", async () => {
    routeFetch({});
    imageOk();
    renderSession();

    const image = await screen.findByRole("img");
    fireEvent.load(image);
    await waitFor(() =>
      expect(answerButtons()[0]).not.toHaveAttribute("aria-disabled"),
    );

    fireEvent.error(image);
    await waitFor(() => {
      for (const button of answerButtons()) {
        expect(button).toHaveAttribute("aria-disabled", "true");
      }
    });
    expect(screen.getByText(messages.review.imageUnavailable)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: messages.review.imageRetry }),
    ).toBeInTheDocument();
  });

  test("bloklangan tugma bosilsa SABAB e'lon qilinadi, javob KETMAYDI", async () => {
    routeFetch({});
    imageOk();
    renderSession();

    await screen.findByText(/14-C/);
    fireEvent.click(answerButtons()[0]);

    expect(await screen.findByText(messages.review.imageRequired)).toBeInTheDocument();
    for (const [path] of apiClientMock.apiFetch.mock.calls as [string][]) {
      expect(path.endsWith("/answer")).toBe(false);
    }
  });

  test("kadr baytlari FAQAT proxy orqali — havola ulashilmaydi", async () => {
    routeFetch({});
    imageOk();
    renderSession();

    await screen.findByRole("img");
    expect(apiClientMock.apiRequest).toHaveBeenCalledWith(
      `/snapshots/${SNAPSHOT_ID}/image`,
    );
    const image = screen.getByRole("img");
    expect(image.getAttribute("src")).toBe("blob:evidence");
    expect(image).not.toHaveAttribute("crossorigin");
  });
});

/* -------------------------------------------------------------------------- */
/* 3. BITTA JAVOB = BITTA `mutate`                                            */
/* -------------------------------------------------------------------------- */

describe("⛔ bitta javob = bitta so'rov (D-18)", () => {
  async function readyFrame(): Promise<void> {
    routeFetch({});
    imageOk();
    renderSession();
    fireEvent.load(await screen.findByRole("img"));
    await waitFor(() =>
      expect(answerButtons()[0]).not.toHaveAttribute("aria-disabled"),
    );
  }

  function answerCalls(): [string, { body: unknown }][] {
    return (
      apiClientMock.apiFetch.mock.calls as [string, { body: unknown }][]
    ).filter(([path]) => path.endsWith("/answer"));
  }

  test("bosish AYNAN bitta javob yuboradi", async () => {
    await readyFrame();
    fireEvent.click(answerButtons()[0]);

    await waitFor(() => expect(answerCalls()).toHaveLength(1));
    const [path, options] = answerCalls()[0];
    expect(path).toBe(`/review/${ASSIGNMENT_ID}/answer`);
    expect(Array.isArray(options.body)).toBe(false);
  });

  test("⛔ `keydown` `repeat: true` HECH NIMA yubormaydi", async () => {
    await readyFrame();

    fireEvent.keyDown(window, { key: "1", repeat: true });
    fireEvent.keyDown(window, { key: "1", repeat: true });
    fireEvent.keyDown(window, { key: "1", repeat: true });

    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(answerCalls()).toHaveLength(0);
  });

  test("klaviatura yorlig'i `1` bitta javob yuboradi", async () => {
    await readyFrame();
    fireEvent.keyDown(window, { key: "1" });

    await waitFor(() => expect(answerCalls()).toHaveLength(1));
  });

  test("javob yuborilayotganda ikkinchi bosish YANGI so'rov qilmaydi", async () => {
    await readyFrame();

    fireEvent.click(answerButtons()[0]);
    fireEvent.click(answerButtons()[1]);
    fireEvent.click(answerButtons()[2]);

    await waitFor(() => expect(answerCalls().length).toBeGreaterThan(0));
    expect(answerCalls()).toHaveLength(1);
  });

  test("⛔ tez ketma-ket UCH YORLIQ ham BITTA javob yuboradi", async () => {
    /*
     * Klaviatura yo'li — tugma bosishning EGIZAGI, lekin BOSHQA kirish
     * nuqtasi: yorliq ishlovchisi `blocked` ni RENDER PAYTIDAGI qiymatdan
     * o'qiydi, ya'ni bir hodisa oqimidagi uch bosish uchalasi ham eski
     * qiymatni ko'rardi. Qulf `useRef` da va u renderni kutmaydi.
     */
    await readyFrame();

    fireEvent.keyDown(window, { key: "1" });
    fireEvent.keyDown(window, { key: "2" });
    fireEvent.keyDown(window, { key: "3" });

    await waitFor(() => expect(answerCalls().length).toBeGreaterThan(0));
    expect(answerCalls()).toHaveLength(1);
  });

  test("javobdan keyin tizim javobi ko'rinadi (§7.1 — javobdan KEYIN)", async () => {
    await readyFrame();
    fireEvent.click(answerButtons()[0]);

    expect(await screen.findByText(messages.review.answersDiffer)).toBeInTheDocument();
    expect(screen.getByText(/Sizning javobingiz/)).toBeInTheDocument();
    expect(screen.getByText(/Tizim javobi/)).toBeInTheDocument();
  });

  test("⛔ tizim javobi javobdan OLDIN EKRANDA YO'Q", async () => {
    await readyFrame();
    expect(screen.queryByText(/Tizim javobi/)).not.toBeInTheDocument();
    expect(screen.queryByText(messages.review.answersMatch)).not.toBeInTheDocument();
    expect(screen.queryByText(messages.review.answersDiffer)).not.toBeInTheDocument();
  });
});

/* -------------------------------------------------------------------------- */
/* 4. G-18(b) — YUZADA OMMAVIY AMAL YO'Q                                      */
/* -------------------------------------------------------------------------- */

describe("⛔ G-18(b): ommaviy amal yuzasi YO'Q", () => {
  test("DOM'da `input[type=checkbox]` topilmaydi", async () => {
    routeFetch({});
    imageOk();
    const { container } = renderSession();
    await screen.findByText(/14-C/);

    expect(container.querySelectorAll('input[type="checkbox"]')).toHaveLength(0);
    /* Bir ekranda AYNAN bitta band: bitta rasta qatori, bitta kadr. */
    expect(container.querySelectorAll("[data-testid='evidence-frame']")).toHaveLength(1);
  });

  test("⛔ byudjet ko'rsatkichi PROGRESS BAR emas", async () => {
    routeFetch({});
    imageOk();
    const { container } = renderSession();
    await screen.findByText(/14-C/);

    expect(container.querySelector("progress")).toBeNull();
    expect(screen.queryAllByRole("progressbar")).toHaveLength(0);
    expect(screen.getByText("Bugun: 12 / 50")).toBeInTheDocument();
  });
});

/* -------------------------------------------------------------------------- */
/* 5. S-7 ≠ S-8                                                               */
/* -------------------------------------------------------------------------- */

describe("⛔ S-7 va S-8 BOSHQA narsani aytadi", () => {
  test("S-7 «navbat bo'sh» — ish tugadi", async () => {
    routeFetch({
      next: () => Promise.reject(new ApiError(409, "review_queue_empty")),
    });
    renderSession();

    expect(await screen.findByText(messages.review.emptyUncertain)).toBeInTheDocument();
    expect(screen.queryByText(messages.review.emptyBudget)).not.toBeInTheDocument();
  });

  test("S-8 «byudjet tugadi» — BOSHQA matn va «Yana ko'rish» YO'Q", async () => {
    routeFetch({
      next: () => Promise.reject(new ApiError(409, "review_budget_exhausted")),
    });
    renderSession();

    expect(await screen.findByText(messages.review.emptyBudget)).toBeInTheDocument();
    expect(screen.getByText("50 / 50. Ertaga davom etadi.")).toBeInTheDocument();
    expect(screen.queryByText(messages.review.emptyUncertain)).not.toBeInTheDocument();
    /* ⛔ Bo'sh holatda birorta AMAL tugmasi yo'q — faqat [Chiqish] havolasi. */
    expect(screen.queryAllByRole("button")).toHaveLength(0);
  });
});

/* -------------------------------------------------------------------------- */
/* 6. SESSIYADAN CHIQISH (§7.8)                                               */
/* -------------------------------------------------------------------------- */

describe("sessiyadan chiqish", () => {
  test("javobsiz band bo'lsa DL-4 ochiladi va fokus [Bekor qilish] da", async () => {
    routeFetch({});
    imageOk();
    renderSession();
    await screen.findByText(/14-C/);

    fireEvent.click(screen.getByRole("button", { name: messages.review.exit }));

    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText(messages.review.exitBody)).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByRole("button", { name: messages.common.cancel })).toHaveFocus(),
    );
  });

  test("javob berilgan bo'lsa chiqish TASDIQSIZ havola bo'ladi", async () => {
    routeFetch({});
    imageOk();
    renderSession();
    fireEvent.load(await screen.findByRole("img"));
    await waitFor(() =>
      expect(answerButtons()[0]).not.toHaveAttribute("aria-disabled"),
    );
    fireEvent.click(answerButtons()[0]);
    await screen.findByText(messages.review.answersDiffer);

    const exit = screen.getByRole("link", { name: messages.review.exit });
    expect(exit).toHaveAttribute("href", "/uz/review");
  });
});
