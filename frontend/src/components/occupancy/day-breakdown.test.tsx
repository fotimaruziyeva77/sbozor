/**
 * KUNLIK XULOSA — BESH HISOBLAGICH VA ULARNING QO'SHILMASLIGI.
 *
 * =============================================================================
 * ⛔ 1. NOMUVOFIQLIK DARVOZASI DOM'DAN HOSILA, KODDAN EMAS.
 *
 *   «To'rtta bo'lakning yig'indisi sarlavhadagi rasta soniga teng» degan
 *   da'voni komponent kodini o'qib tekshirib bo'lmaydi — u aynan
 *   RENDERNING xossasi. Shuning uchun test to'rtta `<dd>` ni DOM'dan
 *   o'qiydi, qo'shadi va sarlavhadagi son bilan solishtiradi.
 *
 *   Fixture ATAYIN shunday tanlangan: `default_empty` va `no_coverage`
 *   NOLDAN FARQLI. Agar komponent ularning birortasini `empty` ga
 *   qo'shsa, «Bo'sh» katagi shishadi va yig'indi `stalls` dan OSHADI —
 *   ya'ni D-19 yoki D-22 ning buzilishi ARIFMETIK ravishda ko'rinadi.
 *   Nol fixture'da bu buzilish JIMGINA o'tardi.
 *
 * ⛔ 2. `human_confirmed` YIG'INDIGA KIRMAYDI VA U HAM NOLDAN FARQLI.
 *
 *   Kesishuvchi o'lchamni yig'indiga qo'shish eng tabiiy xato: u ham
 *   «hisoblagich», u ham `<dd>` ichida. Fixture'da u `31` va yig'indi
 *   baribir `stalls` ga teng — ya'ni qo'shilsa test QIZARADI.
 *
 * ⛔ 3. FOIZ BELGISI UMUMAN YO'Q — `textContent` ustidan.
 *
 *   `186 / 300` aniqroq va yaxlitlanmaydi (§11.4 oxirgi qatori). Bu
 *   da'vo faqat matn darajasida yashaydi, ya'ni uni typecheck ham, lint
 *   ham ushlamaydi.
 *
 * ⚠ 4. NOL FIXTURE ALOHIDA TEST: beshala hisoblagich nol bo'lganda ham
 *   render bo'ladi. Bu 1-banddagi fixture bilan BIR XIL emas — u yerda
 *   sonlar noldan farqli va «nol tashlab yuboriladi» xatosi ko'rinmasdi.
 * =============================================================================
 */
import { render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, test } from "vitest";

import messages from "../../../messages/uz-Latn.json";
import { DayBreakdown } from "@/components/occupancy/day-breakdown";
import type { OccupancyDay } from "@/lib/api-types";

const DAY = "2026-09-14";

/** §11.1 ning ISHLANGAN MISOLI — sonlar spetsifikatsiyadan olingan. */
function daySummary(overrides: Partial<OccupancyDay> = {}): OccupancyDay {
  return {
    day: DAY,
    stalls: 300,
    occupied: 186,
    empty: 68,
    default_empty: 4,
    no_coverage: 42,
    human_confirmed: 31,
    items: [],
    ...overrides,
  };
}

function renderBreakdown(
  summary: OccupancyDay,
  options: { canReview?: boolean } = {},
) {
  return render(
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      timeZone="Asia/Tashkent"
    >
      <DayBreakdown
        canReview={options.canReview ?? false}
        onGoToReview={
          /*
           * ⚠ AMAL PROP BO'LIB KELADI: komponent «qayerga» ni bilmaydi va
           *   bilishi ham shart emas. Testda u oddiy tugma — manzil
           *   qurish sahifaning ishi (`localeHref`).
           */
          <button type="button">{messages.occupancy.goToReview}</button>
        }
        summary={summary}
      />
    </NextIntlClientProvider>,
  );
}

/** Yorliq -> son, DOM'dan (`<dt>` ning juftlik `<dd>` si). */
function counterValue(label: string): number {
  const term = screen.getByText(label);
  const row = term.parentElement;
  expect(row).not.toBeNull();
  const value = within(row as HTMLElement).getByText(/^\d+$/u);
  return Number(value.textContent);
}

const LABELS = messages.occupancy;

describe("besh hisoblagich", () => {
  test("beshalasi ham render bo'ladi — HAMMASI NOL bo'lganda ham", () => {
    renderBreakdown(
      daySummary({
        stalls: 0,
        occupied: 0,
        empty: 0,
        default_empty: 0,
        no_coverage: 0,
        human_confirmed: 0,
      }),
    );

    /*
     * ⚠ SAHIFA `stalls === 0` da E-6 ni CHIZADI (O-3) — bu test esa
     *   KOMPONENTNI to'g'ridan-to'g'ri chaqiradi va u boshqa da'vo:
     *   «nol qiymatli hisoblagich TASHLAB YUBORILMAYDI».
     */
    for (const label of [
      LABELS.occupied,
      LABELS.empty,
      LABELS.defaultEmpty,
      LABELS.noCoverage,
      LABELS.humanConfirmed,
    ]) {
      expect(counterValue(label)).toBe(0);
    }
  });

  test("⛔ `Qamrov yo'q` va `Ko'rilmagani uchun bo'sh` — ALOHIDA `<dt>`", () => {
    renderBreakdown(daySummary());

    /*
     * D-19 va D-22 ning eng tabiiy buzilishi — ikkalasini «Bo'sh» ga
     * qo'shib, yorliqni umuman chizmaslik. Literal yorliq testi buni
     * BEVOSITA o'lchaydi.
     */
    expect(counterValue(LABELS.defaultEmpty)).toBe(4);
    expect(counterValue(LABELS.noCoverage)).toBe(42);
    expect(counterValue(LABELS.empty)).toBe(68);
  });

  test("⛔ to'rt bo'lakning DOM'dagi yig'indisi sarlavhadagi rasta soniga TENG", () => {
    renderBreakdown(daySummary());

    const sum =
      counterValue(LABELS.occupied) +
      counterValue(LABELS.empty) +
      counterValue(LABELS.defaultEmpty) +
      counterValue(LABELS.noCoverage);

    expect(sum).toBe(300);
    expect(screen.getByText("Rasta 300 ta")).toBeTruthy();

    /*
     * ⛔ KESISHUVCHI O'LCHAM YIG'INDIGA KIRMAYDI: u noldan farqli, ya'ni
     *    qo'shilganda yuqoridagi tenglik BUZILARDI.
     */
    expect(counterValue(LABELS.humanConfirmed)).toBe(31);
    expect(sum + counterValue(LABELS.humanConfirmed)).not.toBe(300);
  });

  test("⛔ render qilingan matnda FOIZ belgisi UMUMAN yo'q", () => {
    const { container } = renderBreakdown(daySummary());
    expect(container.textContent ?? "").not.toContain("%");
  });

  test("⛔ hisoblagichlar ro'yxatida progress bar ham, diagramma ham yo'q", () => {
    /*
     * §3.5 va §7.3: bar hisobotni «to'ldiriladigan» narsaga aylantiradi.
     * Da'vo DOM asosida, chunki «biz qurmadik» keyingi ijrochiga
     * ko'rinmaydi.
     */
    const { container } = renderBreakdown(daySummary());
    expect(container.querySelector("progress")).toBeNull();
    expect(container.querySelector("[role='progressbar']")).toBeNull();
    expect(container.querySelector("svg[class*='recharts']")).toBeNull();
  });
});

describe("D-19 jumlasi", () => {
  test("`default_empty > 0` bo'lsa OQIBAT jumlasi majburiy", () => {
    renderBreakdown(daySummary(), { canReview: true });

    expect(
      screen.getByText(
        "4 ta rasta ko'rilmadi va bo'sh deb hisoblandi. Ular uchun patta yozilmadi.",
      ),
    ).toBeTruthy();
    expect(screen.getByText(LABELS.goToReview)).toBeTruthy();
  });

  test("`default_empty === 0` bo'lsa jumla YO'Q, hisoblagich esa BOR", () => {
    renderBreakdown(daySummary({ default_empty: 0, stalls: 296 }));

    expect(screen.queryByText(/ko'rilmadi va bo'sh deb hisoblandi/u)).toBeNull();
    expect(counterValue(LABELS.defaultEmpty)).toBe(0);
  });

  test("⛔ huquq yo'q bo'lsa jumla QOLADI, amal esa YO'Q", () => {
    /*
     * Jumla FAKT aytadi va u huquqdan mustaqil; amal esa nazoratchining
     * yuzasiga olib boradi va `occupancy_review` siz u ochilmaydi.
     */
    renderBreakdown(daySummary(), { canReview: false });

    expect(
      screen.getByText(
        "4 ta rasta ko'rilmadi va bo'sh deb hisoblandi. Ular uchun patta yozilmadi.",
      ),
    ).toBeTruthy();
    expect(screen.queryByText(LABELS.goToReview)).toBeNull();
  });
});

describe("6-faza bilan chalkashish to'sig'i (T-05-72)", () => {
  test("«patta alohida qoidaga ko'ra» jumlasi SHARTSIZ chiziladi", () => {
    renderBreakdown(daySummary({ default_empty: 0 }));
    expect(screen.getByText(LABELS.notBillingYet)).toBeTruthy();
  });

  test("⛔ xulosada summa yoki tarif ma'nosidagi so'z YO'Q", () => {
    const { container } = renderBreakdown(daySummary());
    const text = (container.textContent ?? "").toLowerCase();

    /*
     * ⚠ «patta» SO'ZI BU YERDA QONUNIY va u ikki jumlada bor: «patta
     *   yozilmadi» (D-19 ning oqibati) va «patta hisobi alohida qoidaga
     *   ko'ra yuritiladi» (T-05-72 ning to'sig'i). Taqiqlangani —
     *   SUMMA: so'm, tarif, qarz.
     */
    for (const forbidden of ["so'm", "som", "tarif", "qarz", "summa"]) {
      expect(text).not.toContain(forbidden);
    }
  });
});
