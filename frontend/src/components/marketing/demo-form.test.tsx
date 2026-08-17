/**
 * Demo-forma — 10-04 Task 1 ning sakkiz xulq bandi + B-2 manba quli.
 *
 * O'LCHOV USULI (jsdom cheklovlari — MEROS, o'lchangan):
 *   - Tasdiqlar DOM MATNI, ROLI va ATRIBUTLARI ustida — Tailwind sinfidan
 *     `getComputedStyle` "auto" beradi, sinf nomi tasdiq uchun YAROQSIZ.
 *   - `fetch` har testda ALOHIDA `vi.stubGlobal` bilan tutiladi —
 *     `vitest.setup.ts` ga stub QO'YILMAYDI (teskari shox o'lchanmay qolardi).
 *   - Dwell (mount'dan ≥3s) `vi.useFakeTimers()` + `advanceTimersByTimeAsync`
 *     bilan o'lchanadi: soxta taymer `Date.now` ni ham qamraydi, ya'ni
 *     haqiqiy yuborish testlari OLDIN 3100ms siljitadi — aks holda dwell
 *     darvozasi ularni jim muvaffaqiyatga tushirib yuborardi.
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import type { ReactNode } from "react";

import { act, fireEvent, render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, describe, expect, test, vi } from "vitest";

import messages from "../../../messages/uz-Latn.json";

/*
 * `@/i18n/navigation` jsdom'da Next router kontekstisiz ishlamaydi —
 * `locale-switcher.test.tsx:32-40` bilan AYNI naqsh. Bu yerda faqat `Link`
 * kerak (rozilik yorlig'i ichidagi maxfiylik havolasi) — oddiy <a> yetadi.
 */
vi.mock("@/i18n/navigation", () => ({
  Link: ({
    children,
    href,
    ...rest
  }: { children: ReactNode; href: string } & Record<string, unknown>) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

import { DemoForm } from "./demo-form";

const L = messages.landing.form;

/** G-land-1(c) kontrakti: klientga faqat shu IKKI fazoviy nom tushadi. */
const NARROWED_MESSAGES = {
  common: messages.common,
  landing: messages.landing,
};

function renderForm() {
  return render(
    <NextIntlClientProvider locale="uz-Latn" messages={NARROWED_MESSAGES}>
      <DemoForm />
    </NextIntlClientProvider>,
  );
}

/** Minimal javob obyekti — `Response` semantikasiga bog'lanmaymiz. */
function jsonResponse(status: number, body: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

/** Majburiy maydonlarni to'ldiradi va rozilikni belgilaydi. */
function fillValidForm() {
  fireEvent.change(screen.getByLabelText(L.name), {
    target: { value: "Anvar" },
  });
  fireEvent.change(screen.getByLabelText(L.phone), {
    target: { value: "+998 90 123 45 67" },
  });
  fireEvent.change(screen.getByLabelText(L.market), {
    target: { value: "Karmana dehqon bozori" },
  });
  fireEvent.click(screen.getByRole("checkbox"));
}

/** Dwell darvozasidan o'tish — soxta soatni 3s dan nariga siljitadi. */
async function passDwellGate() {
  await vi.advanceTimersByTimeAsync(3100);
}

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe("DemoForm — validatsiya ko'rinadi, tugma jim yopilmaydi", () => {
  test("1: bo'sh forma yuborilganda tugma BOSILADI va mos validatsiya xabarlari EKRANDA", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    renderForm();

    const submit = screen.getByRole("button", { name: L.submit });
    // Tugma domen sharti bilan yopilmagan (G-SUBMIT D-1).
    expect(submit).toBeEnabled();

    await act(async () => {
      fireEvent.click(submit);
    });

    // Bo'sh formaga mos to'rt xabar (phoneInvalid emas — maydon bo'sh).
    expect(screen.getByText(L.validation.nameRequired)).toBeInTheDocument();
    expect(screen.getByText(L.validation.phoneRequired)).toBeInTheDocument();
    expect(screen.getByText(L.validation.marketRequired)).toBeInTheDocument();
    expect(screen.getByText(L.validation.consentRequired)).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();

    // Beshinchi xabar — qisqa telefon `phoneInvalid` beradi (reyestr 5/5).
    fireEvent.change(screen.getByLabelText(L.phone), {
      target: { value: "12345" },
    });
    await act(async () => {
      fireEvent.click(submit);
    });
    expect(screen.getByText(L.validation.phoneInvalid)).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  test("2: rozilik belgilanmagan — tugma bosiladi va consentRequired KO'RINADI (jim disabled emas)", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    renderForm();

    fireEvent.change(screen.getByLabelText(L.name), {
      target: { value: "Anvar" },
    });
    fireEvent.change(screen.getByLabelText(L.phone), {
      target: { value: "+998 90 123 45 67" },
    });
    fireEvent.change(screen.getByLabelText(L.market), {
      target: { value: "Karmana dehqon bozori" },
    });
    // Rozilik ATAYIN belgilanmaydi.

    const submit = screen.getByRole("button", { name: L.submit });
    expect(submit).toBeEnabled();

    await act(async () => {
      fireEvent.click(submit);
    });

    expect(screen.getByText(L.validation.consentRequired)).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  test("3: yuborish davomida tugma disabled + `submitting` matni; yakunda holat tiklanadi", async () => {
    vi.useFakeTimers();
    let resolveFetch!: (value: Response) => void;
    const fetchMock = vi.fn().mockReturnValue(
      new Promise<Response>((resolve) => {
        resolveFetch = resolve;
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    renderForm();
    fillValidForm();
    await passDwellGate();

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: L.submit }));
    });

    // Yuborilmoqda: matn almashgan va FAQAT shu paytda disabled.
    const submitting = screen.getByRole("button", { name: L.submitting });
    expect(submitting).toBeDisabled();

    await act(async () => {
      resolveFetch(jsonResponse(502, { detail: "delivery_failed" }));
    });

    // Xato yakunida holat tiklanadi: tugma yana bosiladigan `submit` matnida.
    expect(screen.getByRole("button", { name: L.submit })).toBeEnabled();
  });
});

describe("DemoForm — natija holatlari", () => {
  test("4: muvaffaqiyatda forma ALMASHTIRILADI — role=status + aria-live=polite bloki", async () => {
    vi.useFakeTimers();
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse(200, { delivered: true }));
    vi.stubGlobal("fetch", fetchMock);
    renderForm();
    fillValidForm();
    await passDwellGate();

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: L.submit }));
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const status = screen.getByRole("status");
    expect(status).toHaveAttribute("aria-live", "polite");
    expect(status).toHaveTextContent(L.success.title);
    // Forma ALMASHTIRILGAN: submit tugmasi endi yo'q.
    expect(
      screen.queryByRole("button", { name: L.submit }),
    ).not.toBeInTheDocument();
  });

  test("5: xatoda forma SAQLANADI, role=alert chiqadi va fokus unga ko'chadi", async () => {
    vi.useFakeTimers();
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse(502, { detail: "delivery_failed" }));
    vi.stubGlobal("fetch", fetchMock);
    renderForm();
    fillValidForm();
    await passDwellGate();

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: L.submit }));
    });

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent(L.error.title);
    // Fokus xato blokiga ko'chgan (§15.6).
    expect(document.activeElement).toBe(alert);
    // Kiritilgan qiymatlar YO'QOLMAGAN.
    expect(screen.getByLabelText(L.name)).toHaveValue("Anvar");
    expect(screen.getByLabelText(L.phone)).toHaveValue("+998 90 123 45 67");
    expect(screen.getByLabelText(L.market)).toHaveValue(
      "Karmana dehqon bozori",
    );
  });

  test("6a: 429 javobi `rateLimited` matnini beradi", async () => {
    vi.useFakeTimers();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse(429, { detail: "rate_limited" })),
    );
    renderForm();
    fillValidForm();
    await passDwellGate();

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: L.submit }));
    });

    expect(screen.getByRole("alert")).toHaveTextContent(L.error.rateLimited);
  });

  test("6b: 502 `delivery_failed` — env telefonisiz `bodyNoPhone`, bo'sh qavs KO'RSATILMAYDI", async () => {
    vi.useFakeTimers();
    vi.stubEnv("NEXT_PUBLIC_CONTACT_PHONE", "");
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(jsonResponse(502, { detail: "delivery_failed" })),
    );
    renderForm();
    fillValidForm();
    await passDwellGate();

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: L.submit }));
    });

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent(L.error.bodyNoPhone);
    // O-06: interpolyatsiya qoldig'i ham, bo'sh qavs ham chiqmaydi.
    expect(alert.textContent).not.toContain("{phone}");
  });

  test("6c: 502 `delivery_failed` — env telefoni BOR bo'lsa `body` telefon bilan", async () => {
    vi.useFakeTimers();
    vi.stubEnv("NEXT_PUBLIC_CONTACT_PHONE", "+998 90 000 00 00");
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(jsonResponse(502, { detail: "delivery_failed" })),
    );
    renderForm();
    fillValidForm();
    await passDwellGate();

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: L.submit }));
    });

    expect(screen.getByRole("alert")).toHaveTextContent("+998 90 000 00 00");
  });
});

describe("DemoForm — anti-spam shoxlari (ikkalasi ham jim)", () => {
  test("7: honeypot to'ldirilgan bo'lsa `fetch` UMUMAN chaqirilmaydi", async () => {
    vi.useFakeTimers();
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const { container } = renderForm();
    fillValidForm();
    await passDwellGate();

    const honeypot = container.querySelector('input[name="website"]');
    expect(honeypot).not.toBeNull();
    fireEvent.change(honeypot as HTMLInputElement, {
      target: { value: "https://spam.example" },
    });

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: L.submit }));
    });

    expect(fetchMock).not.toHaveBeenCalled();
    // Jim muvaffaqiyat — bot farqni javobdan o'qiy olmaydi.
    expect(screen.getByRole("status")).toHaveTextContent(L.success.title);
  });

  test("8: mount'dan 3s O'TMASDAN yuborilsa `fetch` chaqirilmaydi va xato KO'RSATILMAYDI", async () => {
    vi.useFakeTimers();
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    renderForm();
    fillValidForm();
    // Dwell ATAYIN o'tkazilmaydi — soat siljimaydi (delta 0ms < 3000ms).

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: L.submit }));
    });

    expect(fetchMock).not.toHaveBeenCalled();
    // Xato YO'Q — mexanizm oshkor bo'lmaydi; jim muvaffaqiyat shakli.
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(L.success.title);
  });
});

describe("DemoForm — B-2 manba quli (69 KB gzip grafi qaytmasin)", () => {
  test("manbada og'ir modul importlari YO'Q; yo'l literal; arzon zod BOR", () => {
    // Vitest `frontend/` ildizidan yuguradi — `process.cwd()` barqaror
    // (locale-switcher.test.tsx bilan AYNI naqsh).
    const formSource = readFileSync(
      path.join(process.cwd(), "src", "components", "marketing", "demo-form.tsx"),
      "utf8",
    );
    const errorsSource = readFileSync(
      path.join(process.cwd(), "src", "lib", "demo-errors.ts"),
      "utf8",
    );

    /*
     * Taqiqlangan modul nomlari BUTUN manba bo'ylab (izohda ham) —
     * "izohdagi nom import bo'lib qaytdi" regressiyasi satr skani bilan
     * ushlansin. Shuning uchun komponent izohlari u modullarni nomlamaydi.
     */
    const forbidden = ["api-client", "api-types", "auth-store", "next/navigation"];
    for (const token of forbidden) {
      expect(formSource, `taqiqlangan token demo-form.tsx da: ${token}`).not.toContain(token);
      expect(errorsSource, `taqiqlangan token demo-errors.ts da: ${token}`).not.toContain(token);
    }

    // Yo'l — LITERAL konstanta (modul importi emas).
    expect(formSource).toContain("/api/v1/public/demo-requests");

    // Arzon chunk ruxsat etilgan: forma zod'ni O'ZI import qiladi...
    expect(formSource).toContain('from "zod"');
    // ...ko'zgu moduli esa MUTLAQO zod'siz (import satri yo'q).
    expect(errorsSource).not.toContain('from "zod"');

    // Navigatsiya faqat locale'ni biladigan o'ramdan.
    expect(formSource).toContain('from "@/i18n/navigation"');
  });
});
