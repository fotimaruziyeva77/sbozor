/*
 * =============================================================================
 * PUL VA FOIZ FORMATI — DIZAYN SPETSIFIKATSIYASINING AYNAN O'ZI.
 *
 * Manba: claude.ai/design loyihasi `7bb95baa…`, `Sbozor Direktor.dc.html`
 * ning DCLogic skripti (`group()`, `money()`, `pct()`, `delta()`).
 * MCP orqali o'qildi 2026-08-18.
 *
 * ⛔⛔ NEGA BU FAYL KERAK — IKKI SABAB, IKKALASI HAM O'LCHANGAN.
 *
 * 1. BRAUZER O'ZBEK LOTIN SONINI BUZADI:
 *      new Intl.NumberFormat("uz-Latn").format(12480000)
 *        brauzer -> "12,480,000"   ⛔ VERGUL (CLDR ILDIZ shabloni)
 *        Node    -> "12 480 000"   ✓ uzilmas bo'shliq
 *    `uz-Cyrl` va `ru` da brauzer TO'G'RI ishlaydi — nosozlik faqat
 *    asosiy tilimizda. Sabab `uz-latn-date.ts` dagi bilan bir xil.
 *
 *    ⛔ Bu sanadan QIMMATROQ: bu PUL. Vergul ba'zi konvensiyalarda
 *       KASR belgisi, ya'ni 11 million 11 so'm bo'lib o'qilishi mumkin.
 *
 * 2. DIZAYN QOIDALARI KODDA BO'LISHI KERAK: bir kasr belgisi, `↑ +`/`↓ −`,
 *    «to'liq emas» holati. Ular komponentlarga tarqalsa, ikkinchi kunda
 *    biri ikki kasr belgisi bilan chizardi.
 *
 * ⛔ AJRATGICH `U+00A0` (uzilmas bo'shliq). Dizayn manbasida oddiy
 *    bo'shliq yozilgan — VIZUAL AYNAN BIR XIL, lekin oddiy bo'shliq
 *    raqamni qator oxirida BO'LIB yuborardi. Bu ongli chetlanish.
 *
 * ⛔ MANFIY BELGI `U+2212` (MINUS SIGN), defis EMAS — dizayn shunday
 *    qiladi va u tipografik jihatdan to'g'ri.
 * =============================================================================
 */

import type { useFormatter } from "next-intl";

import { isUzLatn } from "@/lib/uz-latn-date";

/** Uzilmas bo'shliq — modul izohining ajratgich bandi. */
const NBSP = " ";

/** MINUS SIGN — defis emas. */
const MINUS = "−";

/**
 * Butun sonni uch xonalab guruhlaydi: `12480000` -> `12 480 000`.
 *
 * ⛔ Kasr qismi TASHLANADI: bu funksiya PUL VA SANOQ uchun, foizlar
 *    `formatPercent()` dan o'tadi.
 */
export function groupDigits(value: number): string {
  const digits = Math.round(Math.abs(value)).toString();

  let grouped = "";
  for (let index = 0; index < digits.length; index += 1) {
    if (index > 0 && (digits.length - index) % 3 === 0) grouped += NBSP;
    grouped += digits[index];
  }

  return value < 0 ? `${MINUS}${grouped}` : grouped;
}

/**
 * PUL VA SANOQ soni — locale bo'yicha to'g'ri ajratgich bilan.
 *
 * ⚠ Boshqa tillarda `Intl` ISHLATILADI: u yerda brauzer to'g'ri va
 *   ikkinchi implementatsiya faqat drift manbai bo'lardi.
 */
export function formatAmount(
  format: ReturnType<typeof useFormatter>,
  value: number,
  locale: string,
): string {
  if (isUzLatn(locale)) return groupDigits(value);
  return format.number(value);
}

/**
 * Foiz — ⛔ AYNAN BIR kasr belgisi (dizayn `pct()`: `toFixed(1)`).
 *
 * ⛔ Ikkinchi belgi QO'SHILMAYDI: bir kasr belgisi aniqlikning
 *    O'LCHANGAN darajasini bildiradi, ikkitasi o'lchanmaganini da'vo
 *    qilardi.
 */
export function formatPercent(value: number): string {
  return `${value.toFixed(1)}%`;
}

/** `delta()` natijasi — dizayndagi uchta shoxning aynan o'zi. */
export type DeltaView = {
  tone: "muted" | "neutral" | "success" | "danger";
  text: string;
};

/**
 * Ikki davr farqi — dizayn `delta(cur, prev, goodIsUp)` ning ko'chirmasi.
 *
 * ⛔ UCH SHOX VA HAR BIRI MA'NOLI:
 *
 *   1. `bothClosed === false` -> «to'liq emas». Tugamagan davr uchun foiz
 *      HISOBLANMAYDI (dizayn 12-bo'limining taqiqi). Bu eng muhim shox:
 *      usiz avgustning 18-kuni butun avgust bilan solishtirilardi va
 *      raqam har kuni «pasayish» ko'rsatardi.
 *   2. |farq| < 0.05% -> «0.0% o'zgarishsiz», NEUTRAL. Nol o'zgarish
 *      yaxshi ham, yomon ham emas — rang bermaydi.
 *   3. Aks holda yo'nalish `goodIsUp` ga bog'liq: tushum o'sishi YAXSHI,
 *      qarz o'sishi YOMON. Ya'ni rang FAKTGA emas, MA'NOGA bog'lanadi.
 *
 * ⛔ `previous === 0` da foiz MA'NOSIZ (har qanday son cheksiz foizga
 *    o'sadi) — `null` qaytadi va chaqiruvchi hech nima chizmaydi.
 */
export function deltaView(
  current: number,
  previous: number,
  options: {
    goodIsUp: boolean;
    bothClosed: boolean;
    /*
     * 2026-08-26 tarjima tuzatishi: ikki maxsus shoxning matni QATTIQ
     * o'zbekcha edi va rus/kirill ekranga ham o'zbekcha chiqardi.
     * Bu funksiya hook chaqira olmaydi — tarjima CHAQIRUVCHIDAN keladi
     * (`common.deltaNotComplete` / `common.deltaNoChange`), va parametr
     * MAJBURIY: ixtiyoriy bo'lsa eski chaqiruvchi nuqsonni saqlab qolardi.
     */
    notCompleteText: string;
    noChangeText: string;
  },
): DeltaView | null {
  if (!options.bothClosed) return { tone: "muted", text: options.notCompleteText };
  if (previous === 0) return null;

  const percent = ((current - previous) / previous) * 100;
  if (Math.abs(percent) < 0.05) {
    return { tone: "neutral", text: options.noChangeText };
  }

  const up = percent > 0;
  const good = options.goodIsUp ? up : !up;

  return {
    tone: good ? "success" : "danger",
    text: `${up ? "↑ +" : `↓ ${MINUS}`}${Math.abs(percent).toFixed(1)}%`,
  };
}

/**
 * Pul birligining yozuvi — locale bo'yicha (2026-08-26 tarjima tuzatishi).
 *
 * ⛔ AVVAL «so'm» QATTIQ YOZILGAN EDI va ruscha/kirillcha ekranda ham
 *    lotincha «so'm» chiqardi (jonli ko'rildi — «0 so'm» ruscha panelda).
 *    Lug'at SHU MODULDA: bu fayl allaqachon locale'ga xos formatlash
 *    hokimiyati (uz-Latn guruhlash istisnosi bilan), va `formatSoum`
 *    hook chaqira olmaydigan joylardan ham ishlatiladi.
 *
 * ⚠ Qiymatlar `*.amountUnit` message-kalitlari bilan BIR XIL turishi
 *    kerak (glossariy) — o'zgartirilsa ikkalasini birga o'zgartiring.
 */
const SOUM_BY_LOCALE: Record<string, string> = {
  "uz-Cyrl": "сўм",
  ru: "сум",
};

/**
 * PUL + BIRLIK bitta satrda: `12 480 000 so'm` / `12 480 000 сум`.
 *
 * ⛔⛔ NEGA ALOHIDA FUNKSIYA — JSX BO'SHLIQNI YUTADI.
 *
 * `{amount} so'm` shaklida yozilganda JSX ifoda bilan matn orasidagi
 * YANGI QATORNI olib tashlaydi va ekranda `24 000so'm` chiqadi. Bu
 * uch marta takrorlandi (260818–19, brauzerda ko'rildi) va har safar
 * `{" "}` bilan yamaldi.
 *
 * ⛔ Endi birlik SATR ICHIDA qo'shiladi — JSX u yerga umuman tegmaydi.
 */
export function formatSoum(
  format: ReturnType<typeof useFormatter>,
  value: number,
  locale: string,
): string {
  const unit = SOUM_BY_LOCALE[locale] ?? "so'm";
  return `${formatAmount(format, value, locale)} ${unit}`;
}
