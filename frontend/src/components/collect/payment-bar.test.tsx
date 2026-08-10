/**
 * ⛔⛔ G-21 (06-UI-SPEC §8.7) — DUBLIKAT TO'SIQNING MIJOZ YARMI.
 *
 * =============================================================================
 * ⛔ 05-13 O'LCHAGAN NUQSON: uch tez bosish UCHTA so'rov yubordi, chunki
 *   so'rov holatining bayrog'i FAQAT KEYINGI RENDERDA o'zgaradi. Server
 *   kafolati ma'lumotni himoya qildi, LEKIN UI ni to'xtatmadi — kassir
 *   uchun bu «uchta to'lov ketdimi?» degan javobsiz savol edi.
 *
 * ⛔ UCHALA KANAL HAM O'LCHANADI, chunki ular UCH XIL kirish nuqtasi:
 *
 *   (a) barmoq/sichqoncha — uch tez bosish;
 *   (b) klaviatura        — `Enter` ni BOSIB TURISH (`repeat: true`);
 *   (c) xatodan keyin     — `[Qayta yuborish]` AYNI kalit bilan.
 *
 * -----------------------------------------------------------------------
 * ⚠ NEGA (c) VA (d) `CollectSession` ORQALI O'LCHANADI
 * -----------------------------------------------------------------------
 * Idempotentlik kaliti SESSIYA HOLATIDA tug'iladi (§8.7) — tugmada emas.
 * `PaymentBar` ga qotirilgan kalitni prop qilib berib «kalit
 * saqlanadimi?» deb so'rash TAVTOLOGIYA bo'lardi: o'zgarmas propning
 * o'zgarmagani hech nimani isbotlamaydi. Shuning uchun bu ikki kanal
 * kalitning HAQIQIY egasi orqali, xulq bilan o'lchanadi.
 *
 * ⚠ (b) NING NAZORATI ALOHIDA: `repeat: true` ning 0 so'rov berishi
 *   ishlovchi UMUMAN yo'q bo'lganda ham rost bo'lardi. Shuning uchun
 *   yonida «bir marta bosilgan `Enter` BITTA so'rov yuboradi» nazorati
 *   turibdi — usiz bu darvoza bo'sh bo'lardi.
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
import { CollectSession } from "@/components/collect/collect-session";
import { PaymentBar } from "@/components/collect/payment-bar";
import { ApiError } from "@/lib/api-client";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const KEY = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";

const OPEN_SHIFT = {
  id: "22222222-2222-4222-8222-222222222222",
  status: "open",
  opened_at: "2026-09-14T02:00:00Z",
};

const PENDING = {
  stall_code: "14-C",
  service_date: "2026-09-14",
  market_open: true,
  amount_soum: 15_000,
  amount_unavailable_reason: null,
  outstanding_soum: 45_000,
  total_due_soum: 60_000,
};

const WRITTEN = {
  payment_id: "33333333-3333-4333-8333-333333333333",
  stall_code: "14-C",
  service_date: "2026-09-14",
  amount_soum: 15_000,
  kind: "payment",
  method: "cash",
  created_at: "2026-09-14T06:00:00Z",
  reversed: false,
};

let client: QueryClient;

function seedSession(): void {
  setSession({
    accessToken: "test-access-token",
    principal: {
      userId: "44444444-4444-4444-8444-444444444444",
      phone: "+998900000000",
      fullName: "Test Cashier",
      roles: ["cashier"],
      marketId: MARKET_ID,
      marketName: "Karmana markaziy bozori",
      isPlatformAdmin: false,
      locale: "uz-Latn",
      mustChangePassword: false,
    },
    markets: [],
  });
}

function renderTree(node: ReactNode) {
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

function paymentCalls(): [string, { body: Record<string, unknown> }][] {
  return (
    apiClientMock.apiFetch.mock.calls as [
      string,
      { method?: string; body: Record<string, unknown> },
    ][]
  ).filter(
    ([path, options]) => path === "/payments" && options.method === "POST",
  );
}

function confirmButton(): HTMLElement {
  return screen.getByRole("button", { name: messages.collect.confirm });
}

beforeEach(() => {
  vi.resetAllMocks();
  clearSession();
  seedSession();
  client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
});

afterEach(() => {
  client.clear();
  clearSession();
});

/* -------------------------------------------------------------------------- */
/* (a), (b), (e) — QULFNING O'ZI                                              */
/* -------------------------------------------------------------------------- */

describe("G-21: `useRef` qulfi", () => {
  function renderBar(method: "cash" | null) {
    return renderTree(
      <PaymentBar
        amountSoum={PENDING.amount_soum}
        idempotencyKey={KEY}
        method={method}
        onMethodChange={vi.fn()}
        onWritten={vi.fn()}
        stallCode={PENDING.stall_code}
      />,
    );
  }

  test("⛔ (a) UCH TEZ BOSISH -> `apiFetch(\"/payments\")` AYNAN 1 marta", async () => {
    apiClientMock.apiFetch.mockResolvedValue(WRITTEN);
    renderBar("cash");

    const confirm = confirmButton();
    fireEvent.click(confirm);
    fireEvent.click(confirm);
    fireEvent.click(confirm);

    await waitFor(() => expect(paymentCalls().length).toBeGreaterThan(0));
    expect(paymentCalls()).toHaveLength(1);
  });

  test("⛔ (b) `Enter` BOSIB TURISH (`repeat: true`) -> 0 so'rov", async () => {
    apiClientMock.apiFetch.mockResolvedValue(WRITTEN);
    renderBar("cash");

    const confirm = confirmButton();
    fireEvent.keyDown(confirm, { key: "Enter", repeat: true });
    fireEvent.keyDown(confirm, { key: "Enter", repeat: true });
    fireEvent.keyDown(confirm, { key: "Enter", repeat: true });

    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(paymentCalls()).toHaveLength(0);
  });

  test("(b) NAZORAT — bir marta bosilgan `Enter` BITTA so'rov yuboradi", async () => {
    /*
     * ⛔ Usiz yuqoridagi «0 so'rov» da'vosi ishlovchi UMUMAN yo'q bo'lgan
     *    holatda ham rost bo'lardi va darvoza bo'sh qolardi.
     */
    apiClientMock.apiFetch.mockResolvedValue(WRITTEN);
    renderBar("cash");

    fireEvent.keyDown(confirmButton(), { key: "Enter" });

    await waitFor(() => expect(paymentCalls()).toHaveLength(1));
  });

  test("⛔ (e) to'lov turi tanlanmasa tasdiq `aria-disabled` va so'rov YO'Q", async () => {
    apiClientMock.apiFetch.mockResolvedValue(WRITTEN);
    const { container } = renderBar(null);

    const confirm = confirmButton();
    expect(confirm).toHaveAttribute("aria-disabled", "true");
    /* ⛔ `disabled` atributi YO'Q — u fokusni ham, e'lonni ham o'ldirardi. */
    expect(container.querySelectorAll("button[disabled]")).toHaveLength(0);

    fireEvent.click(confirm);
    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(paymentCalls()).toHaveLength(0);
  });

  test("⛔ ommaviy amal yuzasi NOL: `radio`, ko'p tanlov yo'q (§15.4)", () => {
    const { container } = renderBar("cash");

    const inputs = Array.from(container.querySelectorAll("input"));
    expect(new Set(inputs.map((el) => el.type))).toEqual(new Set(["radio"]));
    expect(inputs).toHaveLength(2);
  });
});

/* -------------------------------------------------------------------------- */
/* (c), (d) — KALIT HAYOT DAVRI (egasi: `CollectSession`)                     */
/* -------------------------------------------------------------------------- */

describe("G-21: idempotentlik kalitining hayot davri (§8.7)", () => {
  /** Yo'l bo'yicha javob; `POST /payments` uchun navbat beriladi. */
  function routeFetch(postAnswers: (() => Promise<unknown>)[]) {
    let index = 0;
    apiClientMock.apiFetch.mockImplementation(
      (path: string, options?: { method?: string }) => {
        if (path === "/shifts/open") return Promise.resolve(OPEN_SHIFT);
        if (path.startsWith("/billing/pending?stall_code=")) {
          return Promise.resolve(PENDING);
        }
        if (path === "/payments" && options?.method === "POST") {
          const answer = postAnswers[Math.min(index, postAnswers.length - 1)];
          index += 1;
          return answer();
        }
        return Promise.reject(new Error(`mock'lanmagan yo'l: ${path}`));
      },
    );
  }

  /** Rasta kodini kiritib, `cash` ni tanlaydi — tasdiqni BOSMAYDI. */
  async function reachConfirm(container: HTMLElement) {
    await waitFor(() => {
      expect(
        container.querySelector('input[data-collect-step="stall"]'),
      ).not.toBeNull();
    });

    const input = container.querySelector<HTMLInputElement>(
      'input[data-collect-step="stall"]',
    );
    if (input === null) throw new Error("qidiruv maydoni topilmadi");
    fireEvent.change(input, { target: { value: PENDING.stall_code } });
    fireEvent.keyDown(input, { key: "Enter" });

    await waitFor(() => {
      expect(
        container.querySelector('[data-collect-step="method"]'),
      ).not.toBeNull();
    });

    const radio = container.querySelector<HTMLInputElement>(
      '[data-collect-option="method"]',
    );
    if (radio === null) throw new Error("to'lov turi topilmadi");
    fireEvent.click(radio);

    await waitFor(() => {
      expect(
        container.querySelector('[data-collect-step="confirm"]'),
      ).not.toBeNull();
    });
  }

  test("⛔ (c) 5xx dan keyin `[Qayta yuborish]` -> 2-chi so'rov, AYNI kalit", async () => {
    routeFetch([
      () => Promise.reject(new ApiError(500, "internal_error")),
      () => Promise.resolve(WRITTEN),
    ]);
    const { container } = renderTree(
      <CollectSession shiftHref="/uz/collect/shift" />,
    );

    await reachConfirm(container);
    fireEvent.click(confirmButton());

    /* Xato bloki `[Qayta yuborish]` bilan chiqadi (§14.5, 4-hudud). */
    const retry = await screen.findByRole("button", {
      name: messages.collect.retry,
    });
    expect(paymentCalls()).toHaveLength(1);

    fireEvent.click(retry);
    await waitFor(() => expect(paymentCalls()).toHaveLength(2));

    const [first, second] = paymentCalls();
    /* ⛔ AYNI KALIT: server o'sha to'lovni 200 bilan qaytaradi. */
    expect(second[1].body.idempotency_key).toBe(first[1].body.idempotency_key);
    expect(typeof first[1].body.idempotency_key).toBe("string");
  });

  test("⛔ (d) summa o'zgargach kalit BOSHQA bo'ladi (Pitfall 4)", async () => {
    routeFetch([
      () => Promise.reject(new ApiError(500, "internal_error")),
      () => Promise.resolve(WRITTEN),
    ]);
    const { container } = renderTree(
      <CollectSession shiftHref="/uz/collect/shift" />,
    );

    await reachConfirm(container);
    fireEvent.click(confirmButton());
    await waitFor(() => expect(paymentCalls()).toHaveLength(1));

    /*
     * ⛔ Summa o'zgaradi (bu yerda `[Qarzni ham olish]` orqali — 06-11
     *    T2 da mavjud yagona yo'l; DL-1 ham AYNI urug'ni o'zgartiradi).
     *    Server imzosi summani ham o'z ichiga oladi, ya'ni ESKI kalit
     *    bilan yuborish `409 idempotency_key_reused` berardi.
     */
    fireEvent.click(
      screen.getByRole("button", {
        name: new RegExp(messages.collect.withDebt),
      }),
    );

    await waitFor(() => {
      expect(
        container.querySelector('[data-collect-step="confirm"]'),
      ).not.toBeNull();
    });
    fireEvent.click(confirmButton());
    await waitFor(() => expect(paymentCalls()).toHaveLength(2));

    const [first, second] = paymentCalls();
    expect(second[1].body.idempotency_key).not.toBe(
      first[1].body.idempotency_key,
    );
    /* ⛔ Yangi summa ham SERVER bergan qiymatdan — klientda qo'shilmagan. */
    expect(second[1].body.amount_soum).toBe(PENDING.total_due_soum);
  });
});
