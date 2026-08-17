/**
 * `LocaleSwitcher` — sirg'aluvchi faol indikator shartnomasi (09-06 Task 1,
 * 09-UI-SPEC §12.9).
 *
 * Nima qulflanadi (09-06-PLAN Task 1 `<behavior>`):
 *   1. Uchala tugma BIR XIL kenglik sinfini tashiydi va indikatorning
 *      gorizontal o'rni faol indeksga bog'liq (`--idx` inline o'zgaruvchisi).
 *   2. Indikator FAQAT `transform` bilan siljiydi: inline uslubda
 *      `translateX(calc(var(--idx) * …))`, sinflarda `transition-transform`.
 *      `width` / `left` / `margin` inline uslubda YO'Q — ular hech qachon
 *      animatsiya qilinmaydi (G-motion-3(a) ruhi: layout xossalari 60fps ni
 *      o'ldiradi).
 *   3. `aria-current="true"` faqat faol tugmada; `role="group"` + `aria-label`
 *      saqlanadi; indikator `aria-hidden` bezak va bosishni yutmaydi.
 *   4. Til almashtirish oqimi O'ZGARMAGAN: `router.replace(pathname, {locale})`,
 *      sessiya bo'lsa `PATCH /me`, sessiyasiz faqat URL; faol tilni qayta
 *      bosish — no-op.
 *
 * ⚠ O'LCHOVSIZ IJRO (reja sharti): jsdom `getBoundingClientRect()` uchun 0
 *   qaytaradi — kenglik PIKSELDA o'lchanmaydi. Test sinf tokenlarini va
 *   inline `--idx` / `transform` qiymatlarini o'qiydi (jsdom Tailwind sinfini
 *   KO'RMAYDI, shuning uchun o'rin inline uslubdan o'qiladi).
 *
 * ⚠ Yorliqlar ENDONIM bo'lib qoladi («O'zbekcha»/«Ўзбекча»/«Русский», 01-08
 *   qarori, `api-types.ts::LOCALE_LABELS`) — reja matnidagi «UZ/ЎЗ/RU» mavjud
 *   kontraktga zid va KONTRAKT yutdi (farq SUMMARY'da). Teng kenglik mexanizmi
 *   endonimlarga ham qo'llanadi — kenglik eng uzun yorliqqa yetadigan qilib
 *   tanlangan.
 */
/* DIQQAT: bosish `fireEvent` bilan — loyihada `user-event` ishlatilmaydi. */
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import messagesRu from "../../../messages/ru.json";
import messagesUz from "../../../messages/uz-Latn.json";
import { LocaleSwitcher } from "@/components/shell/locale-switcher";
import { LOCALE_LABELS } from "@/lib/api-types";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

/*
 * `@/i18n/navigation` Next router kontekstiga tayanadi va u jsdom'da yo'q —
 * `app-shell.test.tsx:39-52` bilan AYNI mock shakli.
 */
const navigationMock = vi.hoisted(() => ({
  replace: vi.fn(),
  pathname: "/dashboard",
}));

vi.mock("@/i18n/navigation", () => ({
  useRouter: () => ({ replace: navigationMock.replace }),
  usePathname: () => navigationMock.pathname,
}));

/* `apiFetch` josuslanadi — qolgan eksportlar asl (billing/page.test naqshi). */
const apiClientMock = vi.hoisted(() => ({
  apiFetch: vi.fn(),
}));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiClientMock.apiFetch };
});

/** uz-Latn `common.languageLabel` qiymati — guruh nomi. */
const GROUP_LABEL_UZ = "Til";

function renderSwitcher(locale: "uz-Latn" | "ru" = "uz-Latn"): void {
  render(
    <NextIntlClientProvider
      locale={locale}
      messages={locale === "ru" ? messagesRu : messagesUz}
    >
      <AuthProvider>
        <LocaleSwitcher />
      </AuthProvider>
    </NextIntlClientProvider>,
  );
}

function group(): HTMLElement {
  /*
   * Guruh nomi locale'ga qarab o'zgaradi — `getByRole("group")` nomsiz
   * chaqiriladi va aria-label mavjudligi alohida tekshiriladi.
   */
  return screen.getByRole("group");
}

/** Sirg'aluvchi indikator — `data-active-index` atributi bilan topiladi. */
function indicator(): HTMLElement | null {
  return group().querySelector("[data-active-index]");
}

function seedSession(): void {
  setSession({
    accessToken: "test-access-token",
    principal: {
      userId: "33333333-3333-4333-8333-333333333333",
      phone: "+998901234567",
      fullName: "Test Foydalanuvchi",
      roles: ["director"],
      marketId: "11111111-1111-4111-8111-111111111111",
      marketName: "Karmana markaziy bozori",
      isPlatformAdmin: false,
      locale: "uz-Latn",
      mustChangePassword: false,
    },
    markets: [],
  });
}

beforeEach(() => {
  vi.clearAllMocks();
  apiClientMock.apiFetch.mockResolvedValue({ locale: "ru" });
});

afterEach(() => {
  cleanup();
  clearSession();
});

describe("LocaleSwitcher — sirg'aluvchi indikator (§12.9)", () => {
  test("uchala tugma BIR XIL kenglik sinfini tashiydi", () => {
    renderSwitcher();

    const buttons = screen.getAllByRole("button");
    expect(buttons).toHaveLength(3);

    const widthTokens = buttons.map((button) => {
      const match = /\bw-\d+\b/u.exec(button.className);
      return match?.[0] ?? null;
    });

    // Har tugmada kenglik sinfi BOR va uchalasi bir xil qiymat.
    expect(widthTokens[0]).not.toBeNull();
    expect(new Set(widthTokens).size).toBe(1);
  });

  test("indikator mavjud, aria-hidden bezak va bosishni yutmaydi", () => {
    renderSwitcher();

    const slider = indicator();
    expect(slider).not.toBeNull();
    expect(slider?.getAttribute("aria-hidden")).toBe("true");
    expect(slider?.className).toContain("pointer-events-none");
    // Indikator kengligi tugmalar bilan bir xil sinf oilasidan.
    expect(slider?.className).toMatch(/\bw-\d+\b/u);
  });

  test("indikator o'rni faol indeksga bog'liq: uz-Latn -> 0", () => {
    renderSwitcher("uz-Latn");

    const slider = indicator();
    expect(slider?.getAttribute("data-active-index")).toBe("0");
    expect(slider?.style.getPropertyValue("--idx")).toBe("0");
  });

  test("indikator o'rni faol indeksga bog'liq: ru -> 2", () => {
    renderSwitcher("ru");

    const slider = indicator();
    expect(slider?.getAttribute("data-active-index")).toBe("2");
    expect(slider?.style.getPropertyValue("--idx")).toBe("2");
  });

  test("siljish FAQAT transform: translateX(var(--idx)…), width/left/margin inline uslubda YO'Q", () => {
    renderSwitcher();

    const slider = indicator();
    expect(slider).not.toBeNull();
    if (slider === null) return;

    // Harakat mexanizmi — transform, indeks esa CSS o'zgaruvchisida.
    expect(slider.style.transform).toContain("translateX");
    expect(slider.style.transform).toContain("var(--idx)");

    // Layout xossalari inline uslubda umuman yozilmaydi (animatsiya u
    // yoqda tursin): faqat `--idx` va `transform` ruxsat etilgan.
    expect(slider.style.width).toBe("");
    expect(slider.style.left).toBe("");
    expect(slider.style.margin).toBe("");

    // Tranzitsiya sinfi transform BILAN chegaralangan; sehrli son yo'q.
    expect(slider.className).toContain("transition-transform");
    expect(slider.className).not.toContain("transition-[");
    expect(slider.className).not.toMatch(/duration-\d/u);
  });

  test("aria-current='true' FAQAT faol tugmada; role=group + aria-label saqlanadi", () => {
    renderSwitcher();

    const container = group();
    expect(container.getAttribute("aria-label")).toBe(GROUP_LABEL_UZ);

    const current = screen
      .getAllByRole("button")
      .filter((button) => button.getAttribute("aria-current") === "true");
    expect(current).toHaveLength(1);
    expect(current[0]?.textContent).toBe(LOCALE_LABELS["uz-Latn"]);
  });

  test("til almashtirish oqimi O'ZGARMAGAN: replace + sessiyada PATCH /me", () => {
    seedSession();
    renderSwitcher("uz-Latn");

    fireEvent.click(screen.getByRole("button", { name: LOCALE_LABELS.ru }));

    expect(navigationMock.replace).toHaveBeenCalledWith("/dashboard", {
      locale: "ru",
    });
    expect(apiClientMock.apiFetch).toHaveBeenCalledWith(
      "/me",
      expect.objectContaining({
        method: "PATCH",
        body: { locale: "ru" },
      }),
    );
  });

  test("sessiyasiz (login sahifasi) faqat URL almashadi — PATCH ketmaydi", () => {
    clearSession();
    renderSwitcher("uz-Latn");

    fireEvent.click(screen.getByRole("button", { name: LOCALE_LABELS.ru }));

    expect(navigationMock.replace).toHaveBeenCalledWith("/dashboard", {
      locale: "ru",
    });
    expect(apiClientMock.apiFetch).not.toHaveBeenCalled();
  });

  test("faol tilni qayta bosish — no-op (replace ham, PATCH ham yo'q)", () => {
    seedSession();
    renderSwitcher("uz-Latn");

    fireEvent.click(
      screen.getByRole("button", { name: LOCALE_LABELS["uz-Latn"] }),
    );

    expect(navigationMock.replace).not.toHaveBeenCalled();
    expect(apiClientMock.apiFetch).not.toHaveBeenCalled();
  });
});
