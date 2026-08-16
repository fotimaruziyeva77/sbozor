/**
 * ⛔⛔ TARIF DAVRINING YORLIG'I — KELAJAK «HOZIR» DEB YORLIQLANMAYDI.
 *
 * =============================================================================
 * TOPILMA №E (TEST-REPORT 2026-08-15): 2026-09-01 dan kuchga kiradigan
 * 9 000 lik tarif ekranda «Hozircha amalda» deb turgan edi. Ekran
 * KELAJAKNI HOZIR deb ko'rsatardi va bu direktorning NARX qarori:
 * noto'g'ri yorliqlangan davr «bugundan 9 000 olinyapti» degan yolg'onni
 * tug'diradi.
 *
 * Sabab bitta qatorda edi: yorliq sharti `tariff.valid_to === null`.
 * Kelajakdagi qator ham OCHIQ OXIRLI (`valid_to === null`) bo'lgani uchun
 * u ham «hozircha amalda» shoxiga tushardi — ikki BOSHQA holat bitta
 * shartga siqilgandi.
 *
 * =============================================================================
 * ⛔ QAROR SERVERNING `is_past` BAYROG'IDAN — KLIENTDA SANA SOLISHTIRISH YO'Q.
 *
 * Server `is_past` ni `valid_from <= business_today()` deb hisoblaydi
 * (`app/schemas.py`, `business_today()` = Asia/Tashkent biznes-kuni).
 * Ya'ni `is_past === false` ⟺ `valid_from` KELAJAKDA.
 *
 * `new Date()` bilan solishtirish YOZILMAYDI: brauzer mintaqasi
 * servernikidan farq qilishi mumkin va yarim tunda ikki ekran ikki xil
 * yorliq ko'rsatardi — bu loyihada takroran topilgan «ikki haqiqat
 * manbai» sinfi. Shu qarorni MEXANIK qilib qo'yish uchun T1–T4 sof
 * funksiyani SO'ROVSIZ va SANASIZ chaqiradi: ichkariga `new Date()`
 * qo'yilsa, ular kirish ma'lumotisiz javob bera olmasdi.
 * =============================================================================
 */
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { describe, expect, test, vi } from "vitest";

import messages from "../../../messages/uz-Latn.json";
import { TariffRow, tariffRowBadge } from "@/components/tariffs/tariff-list";
import type { TariffItem } from "@/lib/api-types";

const OPEN_ENDED = messages.tariffs.openEnded;

/**
 * `tariffs.startsOn` ning SANASIZ o'zagi — «dan kuchga kiradi».
 *
 * ⛔ Kutilgan matn KATALOGDAN hosila qilinadi, testda QAYTA YOZILMAYDI.
 *
 * ⚠ Sananing O'ZI da'voga KIRMAYDI va bu ataylab: sana formati
 *   («2026 M09 1») BUZUQ — u TEST-REPORT №1 va 8-fazaning bandi. Uni bu
 *   yerda qotirib qo'yish format tuzatilgan kuni bu darvozani YOLG'ON
 *   QIZIL qilardi. Yorliq esa qator davri bilan AYNI formatterdan
 *   foydalanadi, ya'ni ikkisi hech qachon ajralmaydi.
 */
const STARTS_ON_STEM = messages.tariffs.startsOn.replace("{date}", "").trim();

const BASE: TariffItem = {
  id: "11111111-1111-4111-8111-111111111111",
  category_id: "22222222-2222-4222-8222-222222222222",
  category_name: "Sabzavotlar",
  amount_soum: 8_000,
  valid_from: "2026-08-01",
  valid_to: null,
  is_past: true,
};

function renderRow(tariff: TariffItem): ReactNode {
  render(
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      timeZone="Asia/Tashkent"
    >
      <TariffRow
        canManage
        onDelete={vi.fn()}
        onEdit={vi.fn()}
        tariff={tariff}
      />
    </NextIntlClientProvider>,
  );
  return null;
}

/* -------------------------------------------------------------------------- */
/* T1–T4 — SOF QAROR (so'rovsiz, sanasiz)                                     */
/* -------------------------------------------------------------------------- */

describe("`tariffRowBadge()` — yorliq qarori", () => {
  test("T1: hali kuchga kirmagan OCHIQ OXIRLI qator -> `future`", () => {
    /*
     * ⛔ AYNAN SHU HOLAT NUQSONNI TUG'DIRGAN: kelajak qatori ham
     *    `valid_to === null`. Shuning uchun kelajak sharti BIRINCHI
     *    tekshiriladi va tartib `tariffRowBadge()` docstringida yozilgan.
     */
    expect(tariffRowBadge({ is_past: false, valid_to: null })).toBe("future");
  });

  test("T2 (NAZORAT): amaldagi ochiq oxirli qator -> `current`", () => {
    expect(tariffRowBadge({ is_past: true, valid_to: null })).toBe("current");
  });

  test("T3: tugagan davrda yorliq UMUMAN yo'q -> `null`", () => {
    expect(tariffRowBadge({ is_past: true, valid_to: "2026-09-01" })).toBeNull();
  });

  test("T4: `valid_to` ning borligi KELAJAK qarorini bekor qilmaydi", () => {
    /*
     * Ikki kelajak qatori ketma-ket yozilgan holat: birinchisining
     * `valid_to` si ikkinchisining `valid_from` idan hosila bo'ladi,
     * lekin u HAMON kelajakda boshlanadi.
     */
    expect(tariffRowBadge({ is_past: false, valid_to: "2026-10-01" })).toBe(
      "future",
    );
  });
});

/* -------------------------------------------------------------------------- */
/* T5–T6 — RENDER                                                             */
/* -------------------------------------------------------------------------- */

describe("`TariffRow` — yorliq ekranda", () => {
  test("T5: kelajak qatorida «… kuchga kiradi» BOR, «Hozircha amalda» YO'Q", () => {
    renderRow({ ...BASE, is_past: false, valid_from: "2026-09-01" });

    expect(
      screen.getByText(new RegExp(STARTS_ON_STEM, "u")),
    ).toBeInTheDocument();
    /*
     * ⛔ `getByText` NING ANIQ MOSLIGI: davr qatori («… — Hozircha
     *    amalda») butun matni bilan mos kelmaydi, ya'ni bu da'vo AYNAN
     *    YORLIQNI o'lchaydi — topilmaning o'zi ham yorliqda edi.
     */
    expect(screen.queryByText(OPEN_ENDED)).toBeNull();
  });

  test("T6 (NAZORAT): joriy ochiq qatorda «Hozircha amalda» BOR", () => {
    renderRow({ ...BASE, is_past: true, valid_to: null });

    expect(screen.getByText(OPEN_ENDED)).toBeInTheDocument();
    expect(screen.queryByText(new RegExp(STARTS_ON_STEM, "u"))).toBeNull();
  });
});
