/**
 * ⛔⛔ WR-04 — PUL KIRITISHNING YAGONA QOIDASI (`parseSoumInput`).
 *
 * =============================================================================
 * ⛔ 1. NEGA BU TEST BOR.
 *
 *   6-fazada pul kiritadigan IKKI maydon bor va ular IKKI BOSHQA qoida
 *   bilan o'qilardi:
 *
 *     ko'r deklaratsiya (§10.2)  -> `/^\d+$/`      — qat'iy
 *     chetlanish summasi (DL-1)  -> `Number(raw)`  — BO'SH
 *
 *   Ikkinchisi `"1e5"` ni 100 000, `"0x10"` ni 16, `"+15000"` ni 15 000
 *   deb o'qirdi. Va aynan u D-19 bo'yicha kassir IXTIYORIY summani
 *   nomlashi mumkin bo'lgan YAGONA joy edi — ya'ni eng bo'sh qoida eng
 *   qimmat joyda turardi.
 *
 * ⛔ 2. DA'VO IKKALA CHAQIRUVCHIDAN HAM O'TADI, FAQAT SOF FUNKSIYADAN
 *      EMAS.
 *
 *   `parseDeclaredSoum()` va `ReasonDialog` ning `parseAmount()` i
 *   endi bitta manbadan o'tadi. Faqat `parseSoumInput()` ni sinash
 *   «ikkalasi HAM shundan o'tadimi?» savolini javobsiz qoldirardi —
 *   shuning uchun eksport qilingan o'ram ham AYNI jadval bilan
 *   o'lchanadi.
 *
 * ⛔ 3. YAGONA FARQ — `min`, VA U HAM O'LCHANADI: deklaratsiyada NOL
 *      ruxsat (§10.2 — butun smenasi terminal bo'lgan kun REAL holat),
 *      to'lov summasida esa RAD (`payments.amount_soum > 0`).
 * =============================================================================
 */
import { describe, expect, test } from "vitest";

import { parseSoumInput } from "@/lib/api-types";
import { parseDeclaredSoum } from "@/components/collect/shift-close-form";

/**
 * ⛔ RAD ETILISHI SHART BO'LGAN KIRISHLAR — har biri SABAB bilan.
 *
 * Ro'yxat `Number()` ning aynan qabul qiladigan shakllarini o'z ichiga
 * oladi: usiz test eski qoida bilan ham yashil qolardi.
 */
const REJECTED: readonly (readonly [string, string])[] = [
  ["", "bo'sh maydon — «hali qiymat yo'q»"],
  ["   ", "faqat bo'shliq"],
  ["-5000", "manfiy — filtrlab tashlash TAQIQ, rad etiladi"],
  ["+15000", "⛔ `Number()` buni 15000 deb o'qirdi"],
  ["1e5", "⛔ `Number()` buni 100000 deb o'qirdi"],
  ["0x10", "⛔ `Number()` buni 16 deb o'qirdi"],
  ["15 000", "ichki bo'shliq — formatlangan matn, kiritish emas"],
  ["15000.5", "kasr — so'm BUTUN"],
  ["15,000", "vergul"],
  ["1_000", "pastki chiziq"],
  ["abc", "harf"],
  ["Infinity", "⛔ `Number()` buni cheksizlik deb o'qirdi"],
  ["NaN", "so'z"],
];

describe("WR-04: `parseSoumInput` — pul kiritishning YAGONA qoidasi", () => {
  test.each(REJECTED)("⛔ %j RAD ETILADI (%s)", (raw) => {
    expect(parseSoumInput(raw, { min: 0 })).toBeNull();
    expect(parseSoumInput(raw, { min: 1 })).toBeNull();
    /* ⛔ O'RAM HAM: qoida chaqiruvchida chetlab o'tilmaydi. */
    expect(parseDeclaredSoum(raw)).toBeNull();
  });

  test("faqat raqamli satr QABUL QILINADI", () => {
    expect(parseSoumInput("15000", { min: 1 })).toBe(15_000);
    expect(parseSoumInput("0015000", { min: 1 })).toBe(15_000);
    expect(parseDeclaredSoum("980000")).toBe(980_000);
  });

  /*
   * ⛔ CHETDAGI BO'SHLIQ — QABUL QILINADI VA BU ONGLI, `Number()` NING
   *   MEROSI EMAS. Qat'iy o'qish qoidasi BOSHIDANOQ `raw.trim()` bilan
   *   boshlanadi (`parseDeclaredSoum` ning asl shakli): mobil
   *   klaviaturada tasodifiy probel odatiy va u BOSHQA sonni
   *   bildirmaydi. Rad etiladigan shakllar — qiymatni O'ZGARTIRADIGAN
   *   shakllar (`1e5`, `0x10`, `+`, kasr).
   *
   * ⚠ ICHKI bo'shliq esa yuqoridagi ro'yxatda RAD ETILADI: `"15 000"`
   *   formatlangan MATN va uni qabul qilish «foydalanuvchi nimani
   *   terganini taxmin qilish» bo'lardi.
   */
  test("chetdagi bo'shliq QABUL QILINADI (qat'iylik qiymatga tegishli)", () => {
    expect(parseSoumInput(" 15000 ", { min: 1 })).toBe(15_000);
    expect(parseDeclaredSoum(" 15000 ")).toBe(15_000);
  });

  test("⛔ NOL — IKKI CHAQIRUV ORASIDAGI YAGONA FARQ", () => {
    /* §10.2: butun smenasi terminal bo'lgan kun REAL holat. */
    expect(parseSoumInput("0", { min: 0 })).toBe(0);
    expect(parseDeclaredSoum("0")).toBe(0);
    /* `payments.amount_soum > 0` — nol to'lov qatori IFODALAB BO'LMAYDI. */
    expect(parseSoumInput("0", { min: 1 })).toBeNull();
  });

  test("⛔ 2^53 dan oshgan son RAD ETILADI, yaxlitlanmaydi", () => {
    const overflow = String(Number.MAX_SAFE_INTEGER) + "0";

    expect(parseSoumInput(overflow, { min: 0 })).toBeNull();
    expect(parseDeclaredSoum(overflow)).toBeNull();
    expect(parseSoumInput(String(Number.MAX_SAFE_INTEGER), { min: 0 })).toBe(
      Number.MAX_SAFE_INTEGER,
    );
  });
});
