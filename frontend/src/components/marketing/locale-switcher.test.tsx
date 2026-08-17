/**
 * Anonim marketing til almashtirgichi — B-1/B-2 ning bevosita o'lchovi (10-03).
 *
 * NEGA AYNAN SHU SHAKL (10-RESEARCH B-1, yechim C):
 *   - Sessiya provayderi (`AuthProvider`) bu faylda ATAYIN YO'Q — komponent
 *     usiz render bo'lishi SHART. Aks holda `next build` SSG prerender'da
 *     yiqiladi (run-time flake emas, build xatosi).
 *   - Provayderga AYNAN ikki fazoviy nom uzatiladi (`common` + `landing`) —
 *     `(marketing)/layout.tsx` klientga shu ikkitasini beradi (G-land-1(c))
 *     va test kontrakti bilan bir xil bo'lishi kerak.
 *
 * B-2 REGRESSIYA QULFI: oxirgi test modul MANBASINI matn sifatida skanerlaydi
 * (jsdom emas) — zod grafini tortadigan modullarning nomi manbada UMUMAN
 * uchramasligi kerak (import ham, izoh ham). Shu sababdan komponent izohlari
 * o'sha modullarni nomlamaydi — bu ataylab.
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { fireEvent, render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, test, vi } from "vitest";

import messages from "../../../messages/uz-Latn.json";
import { MarketingLocaleSwitcher } from "./locale-switcher";

/*
 * `useRouter`/`usePathname` jsdom'da Next router kontekstisiz ishlamaydi —
 * `(app)/layout.test.tsx:42-50` bilan AYNI naqsh. `vi.hoisted` mock'ning
 * ko'tarilishidan oldin obyekt mavjudligini kafolatlaydi.
 */
const navigationMock = vi.hoisted(() => ({
  replace: vi.fn(),
  pathname: "/",
}));

vi.mock("@/i18n/navigation", () => ({
  useRouter: () => ({ replace: navigationMock.replace }),
  usePathname: () => navigationMock.pathname,
}));

/** G-land-1(c) kontrakti: klientga faqat shu IKKI fazoviy nom tushadi. */
const NARROWED_MESSAGES = {
  common: messages.common,
  landing: messages.landing,
};

function renderSwitcher(locale = "uz-Latn"): void {
  render(
    <NextIntlClientProvider locale={locale} messages={NARROWED_MESSAGES}>
      <MarketingLocaleSwitcher />
    </NextIntlClientProvider>,
  );
}

describe("MarketingLocaleSwitcher — anonim til almashtirgich (B-1/B-2)", () => {
  test("B-1: sessiya provayderisiz render bo'ladi — throw YO'Q", () => {
    // `render` throw qilsa test o'zi qizaradi; qo'shimcha assert komponent
    // haqiqatan chizilganini isbotlaydi (bo'sh render ham throw emas edi).
    renderSwitcher();
    expect(
      screen.getByRole("group", { name: messages.common.languageLabel }),
    ).toBeInTheDocument();
  });

  test("uchta til tugmasi ko'rinadi va faol til belgilangan", () => {
    renderSwitcher("uz-Latn");

    const buttons = screen.getAllByRole("button");
    expect(buttons).toHaveLength(3);

    // Endonimlar — tarjima qilinmaydi (§9.2), uchala tilda bir xil ko'rinadi.
    expect(screen.getByRole("button", { name: "O'zbekcha" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ўзбекча" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Русский" })).toBeInTheDocument();

    // Faol til `aria-current` bilan belgilanadi — vizual indikator emas,
    // semantik atribut o'lchanadi (jsdom'da uslub qiymatlari yaroqsiz).
    expect(
      screen.getByRole("button", { name: "O'zbekcha" }),
    ).toHaveAttribute("aria-current", "true");
    expect(
      screen.getByRole("button", { name: "Русский" }),
    ).not.toHaveAttribute("aria-current");
  });

  test("uz-Cyrl tugmasi bosilganda router.replace joriy pathname va {locale:'uz-Cyrl'} bilan chaqiriladi", () => {
    navigationMock.replace.mockClear();
    navigationMock.pathname = "/";
    renderSwitcher("uz-Latn");

    fireEvent.click(screen.getByRole("button", { name: "Ўзбекча" }));

    expect(navigationMock.replace).toHaveBeenCalledTimes(1);
    expect(navigationMock.replace).toHaveBeenCalledWith("/", {
      locale: "uz-Cyrl",
    });
  });

  test("faol tilni qayta bosish navigatsiya qilmaydi", () => {
    navigationMock.replace.mockClear();
    renderSwitcher("uz-Latn");

    fireEvent.click(screen.getByRole("button", { name: "O'zbekcha" }));

    expect(navigationMock.replace).not.toHaveBeenCalled();
  });

  test("B-2 QULFI: manbada zod grafini tortadigan importlar YO'Q, navigatsiya faqat @/i18n/navigation dan", () => {
    const source = readFileSync(
      fileURLToPath(new URL("./locale-switcher.tsx", import.meta.url)),
      "utf8",
    );

    /*
     * Taqiqlangan modul nomlari BUTUN manba bo'ylab qidiriladi (import
     * satri bilan cheklanmaydi): izohda ham uchramasin — kelajakda
     * "izohdagi nom import bo'lib qaytdi" sinfidagi regressiya bitta
     * satr skani bilan ushlansin.
     */
    const forbidden = ["api-client", "api-types", "auth-store", "next/navigation"];
    for (const token of forbidden) {
      expect(source, `taqiqlangan token manbada: ${token}`).not.toContain(
        token,
      );
    }

    // Ijobiy tomon: navigatsiya AYNAN locale'ni biladigan o'ramdan olinadi.
    expect(source).toContain('from "@/i18n/navigation"');
  });
});
