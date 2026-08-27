/**
 * Import xato ekranining REGRESSIYA darvozasi (UI-SPEC §8.5 C1, D-14).
 *
 * NEGA AYNAN SHU OLTI DA'VO — har biri BOSHQA nosozlik sinfini yopadi va
 * hech biri typecheck, lint yoki build bilan ushlanmaydi:
 *
 *   1. "HECH NARSA SAQLANMADI" DOIM BIRINCHI. D-14 all-or-nothing ni
 *      foydalanuvchiga aytadigan YAGONA jumla. Uni "ortiqcha" deb olib
 *      tashlash yoki ro'yxat ostiga surish admin uchun eng qimmat
 *      oqibatga olib boradi: u qisman yozuvdan qo'rqib bazani qo'lda
 *      tekshira boshlaydi.
 *
 *   2. GURUHLASH RO'YXATDAN YUQORIDA. 300 qator o'qilmaydi, uch jumla
 *      o'qiladi. Guruhlar ostga tushib qolsa ekranning eng qimmatli
 *      qismi ko'rinmay qoladi.
 *
 *   3. FAQAT 50 QATOR (T-02-122). 300 `<li>` — brauzer uchun ham,
 *      skrinrider uchun ham foydasiz yuk.
 *
 *   4. QOLGAN SANOQ KO'RSATILADI. Usiz 3-qoida jimgina MA'LUMOT
 *      YO'QOTISHGA aylanadi: admin 250 ta xatoni umuman ko'rmasdi.
 *
 *   5. SHOSHILINCH E'LON ROLI AYNAN BITTA. Har qatorga qo'yilsa
 *      skrinrider 50 marta uzilardi.
 *
 *   6. QATOR FORMATI `{row}-qator: {matn}` — CONTEXT `<specifics>` da
 *      so'zma-so'z talab qilingan.
 *
 * DIQQAT: `fireEvent` ishlatiladi, `@testing-library/user-event` EMAS
 * (01-12 qarori). Bu fayl faqat RENDER natijasini o'lchaydi.
 */
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactElement } from "react";
import { describe, expect, test } from "vitest";

import messages from "../../../messages/uz-Latn.json";
import { ImportErrors } from "@/components/import/import-errors";
import type { ImportErrorItem } from "@/lib/api-types";

/**
 * 300 xato: 210 ta zona + 78 ta takroriy kod + 12 ta telefon.
 *
 * Sanoqlar `error_counts` dan keladi, `errors` esa SERVERDA cheklangan
 * NAMUNA — shuning uchun bu yerda ular ATAYIN mos kelmaydi: fixture 300
 * ta element beradi, lekin haqiqiy javobda ham namuna kichikroq bo'lishi
 * mumkin va komponent ikkalasini ham to'g'ri talqin qilishi kerak.
 */
const ERROR_COUNTS = {
  zone_not_found: 210,
  duplicate_code_in_file: 78,
  invalid_phone: 12,
} as const;

const TOTAL = 300;

function buildErrors(): readonly ImportErrorItem[] {
  const items: ImportErrorItem[] = [];
  for (let index = 0; index < 210; index += 1) {
    items.push({
      row: index + 2,
      code: "zone_not_found",
      message: `'Sabzavot' zonasi topilmadi (${index})`,
    });
  }
  for (let index = 0; index < 78; index += 1) {
    items.push({
      row: 212 + index,
      code: "duplicate_code_in_file",
      message: "Rasta raqami takrorlangan",
    });
  }
  for (let index = 0; index < 12; index += 1) {
    items.push({
      row: 290 + index,
      code: "invalid_phone",
      message: "Telefon raqami noto'g'ri",
    });
  }
  return items;
}

/**
 * Ekranda IKKITA ro'yxat bor: guruhlar (`<ul>`) va qatorlar (`<ol>`).
 *
 * Ularni tegi bo'yicha ajratish MAJBURIY — `getByRole("list")` ikkalasini
 * ham topadi va "bittasini" so'ragan test noaniqlik bilan yiqiladi. Bu
 * ajratmaning O'ZI ham kontrakt: 7-qoida qator ro'yxatini AYNAN `<ol>`
 * qilib belgilaydi (tartib ma'noli).
 */
function listByTag(tag: "UL" | "OL"): HTMLElement {
  const found = screen
    .getAllByRole("list")
    .find((node) => node.tagName === tag);
  if (found === undefined) throw new Error(`Ro'yxat topilmadi: ${tag}`);
  return found;
}

function renderErrors(
  errors: readonly ImportErrorItem[],
  counts: Readonly<Record<string, number>>,
): ReturnType<typeof render> {
  const tree: ReactElement = (
    <NextIntlClientProvider locale="uz-Latn" messages={messages}>
      <ImportErrors errorCounts={counts} errors={errors} />
    </NextIntlClientProvider>
  );
  return render(tree);
}

describe("Import xatolari — 300 xato muammosi (§8.5 C1)", () => {
  test("«Hech narsa saqlanmadi» jumlasi DOIM birinchi — bitta xatoda ham", () => {
    renderErrors(
      [{ row: 2, code: "empty_code", message: "Rasta raqami yo'q" }],
      { empty_code: 1 },
    );

    const sentence = screen.getByText(messages.import.nothingSaved);
    expect(sentence).toBeInTheDocument();

    /*
     * "Birinchi" — DOM tartibida ham birinchi: jumla xatolar ro'yxatidan
     * OLDIN kelishi shart, aks holda admin uni umuman ko'rmasdi.
     */
    const position = sentence.compareDocumentPosition(listByTag("OL"));
    expect(position & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  test("xatolar KOD bo'yicha guruhlanadi va guruhlar ro'yxatdan yuqorida", () => {
    renderErrors(buildErrors(), ERROR_COUNTS);

    // Guruh matni tarjimadan keladi, xom koddan emas.
    const group = screen.getByText(messages.import.errors.zone_not_found);
    expect(group).toBeInTheDocument();
    expect(screen.getByText("210 ta")).toBeInTheDocument();
    expect(screen.getByText("78 ta")).toBeInTheDocument();

    // Guruhlar `<ul>` da, qatorlar `<ol>` da — guruh YUQORIDA turadi.
    const position = listByTag("UL").compareDocumentPosition(listByTag("OL"));
    expect(position & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  test("300 xatodan DOM'ga faqat 50 qator tushadi", () => {
    renderErrors(buildErrors(), ERROR_COUNTS);

    // Qatorlar `<ol>` da; guruh `<ul>` i alohida ro'yxat.
    expect(listByTag("OL").querySelectorAll("li")).toHaveLength(50);
  });

  test("qolgan xatolar soni ko'rsatiladi", () => {
    renderErrors(buildErrors(), ERROR_COUNTS);

    // 300 - 50 = 250 — sanoq `error_counts` dan, `errors.length` dan emas.
    expect(screen.getByText(`Yana ${TOTAL - 50} ta xato bor`)).toBeInTheDocument();
  });

  test("shoshilinch e'lon roli AYNAN bitta — sarlavhada", () => {
    renderErrors(buildErrors(), ERROR_COUNTS);

    const alerts = document.querySelectorAll("[role='alert']");
    expect(alerts).toHaveLength(1);
    expect(alerts[0].tagName).toBe("H3");
    expect(alerts[0].textContent).toContain("300");
  });

  test("qator formati AYNAN `{row}-qator: {matn}`", () => {
    renderErrors(buildErrors(), ERROR_COUNTS);

    /*
     * Birinchi xato 2-qatorda. Matn SERVERNING `message` i emas, `code`
     * ning TARJIMASI: server matni faqat uz-Latn va uni ekranga chiqarish
     * rus tilidagi adminni tarjimasiz qoldirardi (aniq qiymat esa
     * yuklanadigan `.xlsx` da qoladi).
     */
    const expected = `2-qator: ${messages.import.errors.zone_not_found}`;
    expect(screen.getByText(expected)).toBeInTheDocument();
  });
});
