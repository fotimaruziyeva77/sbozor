/**
 * RAD ETISH EKRANI — CHIQISH YO'LI BOR (Topilma №K).
 *
 * =============================================================================
 * BU FAYLNING MARKAZIY DA'VOSI:
 *
 *   «RUXSAT YO'Q» BOSHI BERK KO'CHA EMAS.
 *
 *   Nazoratchi yettita URL'da bir xil yalang'och qatorni ko'rgan: bitta
 *   jumla, na sabab, na chiqish yo'li. Navigatsiya yon panelda qolgan
 *   bo'lsa ham, foydalanuvchi «endi nima?» savoliga javob topmagan.
 *   Endi ekranda uchta narsa bor: nima bo'ldi, nega, va qayerga borish
 *   mumkin.
 *
 * ⛔⛔ IKKINCHI, YASHIRIN DA'VO — VA U SHU FAYLNING MAVJUDLIGIDA:
 *
 *   BU TEST HECH NIMANI MOCK QILMAYDI.
 *
 *   Router konteksti ham, `next/navigation` ham, `apiFetch` ham
 *   mock qilinmaydi. Agar `ForbiddenNotice` `@/i18n/navigation` dan
 *   `Link` olsa, `next-intl/navigation` -> `next/navigation` zanjiri
 *   vitest ostida YECHILMAYDI va bu fayl «0 test» bilan yiqilardi —
 *   ya'ni import qarori shu yerda MEXANIK ravishda o'lchanadi, izohda
 *   emas. O'lchangan sabab: `camera-row.tsx:61-94` (o'sha zanjir bir
 *   marta TO'RTTA test faylini yiqitib, 27 testni yo'qotgan).
 *
 *   Xuddi shu sabab bu komponentni RENDER QILADIGAN 20 ta sahifaning
 *   testlarini ham qutqaradi — jumladan `billing/page.test.tsx` ning
 *   `errors.forbidden` asserti.
 *
 * ⚠ PREFIKS XARITASI TESTGA NUSXA KO'CHIRILMAYDI: kutilgan qiymat
 *   `routing.localePrefix` dan HOSILA qilinadi. Bitta langar literal
 *   (`/uz/dashboard`) esa NAZORAT sifatida qoladi — usiz bo'sh xarita
 *   ustidagi hosila o'z-o'ziga teng bo'lib jimgina yashil qolardi.
 * =============================================================================
 */
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, test } from "vitest";

import ruMessages from "../../../messages/ru.json";
import cyrlMessages from "../../../messages/uz-Cyrl.json";
import messages from "../../../messages/uz-Latn.json";
import { ForbiddenNotice } from "@/components/auth/forbidden-notice";
import { routing } from "@/i18n/routing";

type Catalog = typeof messages;
/** `routing.locales` ning a'zosi — ro'yxat testda QAYTA YOZILMAYDI. */
type AppLocale = (typeof routing.locales)[number];

const CATALOGS: Readonly<Record<AppLocale, Catalog>> = {
  "uz-Latn": messages,
  "uz-Cyrl": cyrlMessages as unknown as Catalog,
  ru: ruMessages as unknown as Catalog,
};

function renderNotice(locale: AppLocale): void {
  render(
    <NextIntlClientProvider
      locale={locale}
      messages={CATALOGS[locale]}
      timeZone="Asia/Tashkent"
    >
      <ForbiddenNotice />
    </NextIntlClientProvider>,
  );
}

/** Kutilgan prefiks — `routing` KONFIGURATSIYASIDAN, nusxadan emas. */
function expectedPrefix(locale: AppLocale): string {
  const config = routing.localePrefix;
  const prefixes: Partial<Record<string, string>> =
    typeof config === "object" && "prefixes" in config
      ? (config.prefixes ?? {})
      : {};
  return prefixes[locale] ?? `/${locale}`;
}

describe("rad etish ekranining mazmuni", () => {
  test("`role=\"alert\"` ichida rad etish matni O'Z elementida", () => {
    renderNotice("uz-Latn");

    const alert = screen.getByRole("alert");
    /*
     * ⛔ MATN ALOHIDA ELEMENTDA: uni tushuntirish bilan bitta `<p>` ga
     *    qo'shish `billing/page.test.tsx:587` dagi mavjud
     *    `getByText(messages.errors.forbidden)` assertini qizartirardi.
     */
    const line = screen.getByText(messages.errors.forbidden);
    expect(alert).toContainElement(line);
    expect(line).not.toBe(alert);
  });

  test("bir jumlali tushuntirish ko'rinadi", () => {
    renderNotice("uz-Latn");

    expect(
      screen.getByText(messages.errors.forbiddenHint),
    ).toBeInTheDocument();
  });

  test("«Boshqaruv paneliga qaytish» havolasi bor va u `/dashboard` ga", () => {
    renderNotice("uz-Latn");

    const link = screen.getByRole("link", {
      name: messages.errors.backToDashboard,
    });
    // NAZORAT LANGARI — bo'sh prefiks xaritasi ustidagi hosila
    // o'z-o'ziga teng bo'lib jimgina yashil qolardi.
    expect(link).toHaveAttribute("href", "/uz/dashboard");
  });
});

describe("locale prefiksi", () => {
  test("nazorat: uchala locale ham `routing` da e'lon qilingan", () => {
    expect([...routing.locales].sort()).toEqual(
      Object.keys(CATALOGS).sort(),
    );
  });

  test.each(routing.locales)("`%s` -> o'z prefiksi", (locale) => {
    renderNotice(locale);

    const link = screen.getByRole("link", {
      name: CATALOGS[locale].errors.backToDashboard,
    });
    expect(link).toHaveAttribute(
      "href",
      `${expectedPrefix(locale)}/dashboard`,
    );
  });
});
