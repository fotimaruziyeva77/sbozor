/**
 * =============================================================================
 * `LossCalc` — RAQAM ANIMATSIYASINING XULQ KONTRAKTI (260819).
 *
 * ⛔⛔ BU TEST BITTA O'LCHANGAN NOSOZLIK SABABLI YOZILDI.
 *
 *     Birinchi tahrirda ko'rsatiladigan qiymat `useState` da yashardi va
 *     uni FAQAT `requestAnimationFrame` yangilardi. Xromda tekshirilganda
 *     ma'lum bo'ldi: brauzer kadr chizmaydigan holatda (yorliq fonda,
 *     oyna yashiringan) rAF UMUMAN yugurmaydi — va raqam mount
 *     paytidagi qiymatda MUZLAB qolardi. Slayder surilardi, hisob
 *     o'zgarardi, ekrandagi son esa eski bo'lib qolaverardi.
 *
 *     Ya'ni «chiroyli animatsiya» mahsulotning O'ZINI buzardi: bu
 *     seksiyaning butun ma'nosi — javobga qarab o'zgaradigan raqam.
 *
 * ⛔ Shuning uchun ikkita band ALOHIDA o'lchanadi:
 *
 *   (a) rAF BIR MARTA HAM yugurmasa ham qiymat TO'G'RI bo'ladi —
 *       React haqiqatni chizadi, animatsiya esa ustidan yozadi.
 *       ⛔ SABOTAJ: `useState` sxemasi qaytarilsa bu band QIZARADI.
 *
 *   (b) rAF yugursa — oxirgi qiymatga QO'NADI (yo'lda qolib ketmaydi).
 *
 * ⛔ `matchMedia` stubi HAR TESTDA ALOHIDA (`reveal.test.tsx` darsi):
 *    global stub reduced-motion'ning ikkala shoxini bir holatga
 *    yopishtirib qo'yardi.
 * =============================================================================
 */
import { act, fireEvent, render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import messages from "../../../messages/uz-Latn.json";

import { LossCalc } from "./loss-calc";

/** G-land-1(c) kontrakti: klientga faqat shu IKKI fazoviy nom tushadi. */
const NARROWED_MESSAGES = {
  common: messages.common,
  landing: messages.landing,
};

/** Sahna qiymatlari — komponentning o'z konstantalari bilan AYNI. */
const DEFAULT_STALLS = 500;
const FEE = 8000;
const UNPAID_SHARE = 0.05;
const WORKDAYS = 26;
const MONTHS = 12;

function yearlyFor(stalls: number): number {
  return Math.round(stalls * UNPAID_SHARE) * FEE * WORKDAYS * MONTHS;
}

/** 62400000 → «62 400 000» (komponentdagi `formatSum` bilan AYNI qoida). */
function grouped(value: number): string {
  return String(value).replace(/\B(?=(?:\d{3})+(?!\d))/gu, " ");
}

function stubMatchMedia(reduce: boolean): void {
  vi.stubGlobal("matchMedia", (query: string) => ({
    addEventListener() {},
    addListener() {},
    dispatchEvent: () => false,
    matches: reduce && query.includes("reduce"),
    media: query,
    onchange: null,
    removeEventListener() {},
    removeListener() {},
  }));
}

/**
 * rAF ni QO'LGA OLADI: callback'lar navbatda yig'iladi va faqat
 * `flushFrames()` chaqirilganda otiladi. Chaqirilmasa — rAF hech qachon
 * yugurmagan brauzerning aynan o'zi (band (a) ning sahnasi).
 */
const frames: FrameRequestCallback[] = [];
let clock = 0;

function stubRaf(): void {
  vi.stubGlobal("requestAnimationFrame", (callback: FrameRequestCallback) => {
    frames.push(callback);
    return frames.length;
  });
  vi.stubGlobal("cancelAnimationFrame", () => {});
}

/** Navbatdagi kadrlarni `advanceMs` vaqt o'tgan deb hisoblab otadi. */
function flushFrames(advanceMs: number): void {
  clock += advanceMs;
  const pending = frames.splice(0, frames.length);
  act(() => {
    for (const callback of pending) callback(clock);
  });
}

function renderCalc() {
  return render(
    <NextIntlClientProvider locale="uz-Latn" messages={NARROWED_MESSAGES}>
      <LossCalc />
    </NextIntlClientProvider>,
  );
}

/** Slayderni `value` ga suradi (React `onChange` orqali). */
function moveSlider(value: number): void {
  const slider = screen.getByLabelText(messages.landing.calc.q1.title, {
    selector: "input",
  });
  fireEvent.change(slider, { target: { value: String(value) } });
}

beforeEach(() => {
  frames.length = 0;
  clock = 0;
  stubMatchMedia(false);
  stubRaf();
  vi.spyOn(performance, "now").mockImplementation(() => clock);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("LossCalc — raqam animatsiyasi (260819)", () => {
  test("boshlang'ich qiymat darhol to'g'ri (rAF hali yugurmagan)", () => {
    renderCalc();
    expect(screen.getByTestId("loss-calc-yearly")).toHaveTextContent(
      grouped(yearlyFor(DEFAULT_STALLS)),
    );
  });

  test("(a) ⛔ rAF BIR MARTA HAM yugurmasa ham qiymat TO'G'RI — muzlash yo'q", () => {
    renderCalc();
    moveSlider(1200);

    /*
     * ⛔ `flushFrames` ATAYIN CHAQIRILMAYDI: bu — kadr chizilmayotgan
     *    brauzer. Eski (`useState`) sxemada bu yerda 500 rastaning
     *    summasi qolib ketardi va aynan shu nosozlik edi.
     */
    expect(frames.length).toBeGreaterThan(0);
    expect(screen.getByTestId("loss-calc-yearly")).toHaveTextContent(
      grouped(yearlyFor(1200)),
    );
  });

  test("(b) rAF yugursa — oxirgi qiymatga QO'NADI", () => {
    renderCalc();
    moveSlider(900);

    // Butun davomiylikdan uzunroq — o'tish tugagan bo'lishi shart.
    flushFrames(600);
    flushFrames(16);

    expect(screen.getByTestId("loss-calc-yearly")).toHaveTextContent(
      grouped(yearlyFor(900)),
    );
  });

  test("harakat kamaytirilganda rAF UMUMAN so'ralmaydi", () => {
    vi.unstubAllGlobals();
    stubMatchMedia(true);
    stubRaf();
    renderCalc();
    frames.length = 0;

    moveSlider(1500);

    expect(frames).toHaveLength(0);
    expect(screen.getByTestId("loss-calc-yearly")).toHaveTextContent(
      grouped(yearlyFor(1500)),
    );
  });
});

/*
 * ⛔⛔ OYLIK SATR — SON EKRANDA BORMI (2026-09-24).
 *
 *     `t.rich` ning `{amount}` ARGUMENTIGA funksiya berilgan edi. next-intl
 *     funksiyani faqat TEG uchun chaqiradi, argumentga esa funksiyaning
 *     O'ZINI qo'yadi: React uni chiza olmaydi (stderr'da «Functions are
 *     not valid as a React child») va satr «Oyiga ~ so‘m» bo'lib, SONSIZ
 *     chiqardi. Yuqoridagi testlar faqat yillik tugunni o'lchagani uchun
 *     bu hech qachon qizarmagan.
 */
describe("LossCalc — oylik satr (2026-09-24)", () => {
  test("oylik yo'qotish soni satrda ko'rinadi", () => {
    renderCalc();

    expect(screen.getByTestId("loss-calc-monthly")).toHaveTextContent(
      grouped(yearlyFor(DEFAULT_STALLS) / MONTHS),
    );
  });

  test("slayder surilganda oylik son ham yangilanadi (rAF yugurmasa ham)", () => {
    renderCalc();
    moveSlider(1200);

    expect(screen.getByTestId("loss-calc-monthly")).toHaveTextContent(
      grouped(yearlyFor(1200) / MONTHS),
    );
  });
});
