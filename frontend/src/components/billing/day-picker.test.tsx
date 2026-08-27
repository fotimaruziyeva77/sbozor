/**
 * Y-4 NING KUN TANLAGICHI — STANDARTI KECHA, MAKSIMUMI BUGUN (§11.1, C-3).
 *
 * =============================================================================
 * ⛔⛔ 1. KUTILGAN SANA ⛔ SANALADI, LITERAL YOZILMAYDI.
 *
 *   `expect(input.value).toBe("2026-08-10")` bugun yashil, ertaga qizil
 *   bo'lardi — ya'ni test o'zi o'lchayotgan xulqni emas, YUGURTIRILGAN
 *   KUNNI o'lchardi. Shuning uchun `now` TESTDA tug'iladi (`new Date()`)
 *   va AYNI o'sha instansiya `NextIntlClientProvider` ga `now` bo'lib
 *   uzatiladi. Komponent ham, kutilma ham ⛔ BITTA lahzadan hosila —
 *   yarim tunda ham ajralib keta olmaydi.
 *
 * ⛔ 2. DA'VO «KECHA» NI «BUGUN» DAN AJRATADI.
 *
 *   Standart tanlovni `todayIso` ga qaytarish — bu fazadagi ENG
 *   EHTIMOLLI regressiya (4-fazadagi `useDaySelection()` aynan shunday
 *   ishlaydi va uni «qayta ishlatish» juda tabiiy ko'rinadi). O'shanda
 *   sahifa HAR DOIM bo'sh ochilardi (C-3: hisob D+1 04:10 da tug'iladi)
 *   va direktor «tizim ishlamayapti» degan xulosaga kelardi. Da'vo shu
 *   IKKI qiymatning FARQIDAN chiqadi, «bo'sh emas» dan emas.
 *
 * ⛔ 3. KELAJAK RAD ETILADI — VA RAD ETISH O'LCHANADI.
 *
 *   `max` atributi YOLG'IZ YETARLI EMAS: u brauzer maslahatidan iborat
 *   va DevTools bilan olib tashlanadi. Shuning uchun `onChange` filtri
 *   ALOHIDA o'lchanadi — `?day=` URL'ga ⛔ UMUMAN YOZILMAYDI va maydon
 *   `aria-invalid` oladi.
 *
 * ⛔ 4. D-31: YO'QLIK ⛔ TO'PLAM TENGLIGI yoki aniq qiymat bilan
 *   o'lchanadi — bitta nomni izlaydigan inkor matcher ISHLATILMAYDI. U
 *   faqat O'SHA nomni ushlardi va yonidagi yangi tugmani ko'rmasdi.
 *   ⚠ Taqiqlangan matcher nomi bu izohda LITERAL yozilmaydi: qabul
 *   mezoni uni `grep` bilan sanaydi va izoh darvozani o'ziga qarshi
 *   qo'yardi (`badge.tsx:24-26` ning kodbaza konvensiyasi).
 * =============================================================================
 */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { NuqsTestingAdapter } from "nuqs/adapters/testing";
import { describe, expect, test, vi } from "vitest";

import messages from "../../../messages/uz-Latn.json";
import { BillingDayPicker } from "@/components/billing/day-picker";
import {
  businessDayIn,
  shiftIsoDay,
} from "@/components/snapshots/day-picker";

const TIME_ZONE = "Asia/Tashkent";

/*
 * ⛔ YAGONA LAHZA — komponentga ham, kutilmaga ham AYNAN shu instansiya.
 *   Literal sana YO'Q: `TODAY` va `YESTERDAY` undan HOSILA.
 */
const NOW = new Date();
const TODAY = businessDayIn(TIME_ZONE, NOW);
const YESTERDAY = shiftIsoDay(TODAY, -1);
const TOMORROW = shiftIsoDay(TODAY, 1);

/** ⚠ Josus TIPLANGAN: `mock.calls` dan `searchParams` ni `any` siz o'qish uchun. */
type UrlUpdate = { searchParams: URLSearchParams };

function renderPicker(searchParams: string) {
  const onUrlUpdate = vi.fn<(event: UrlUpdate) => void>();

  render(
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      now={NOW}
      timeZone={TIME_ZONE}
    >
      <NuqsTestingAdapter onUrlUpdate={onUrlUpdate} searchParams={searchParams}>
        <BillingDayPicker />
      </NuqsTestingAdapter>
    </NextIntlClientProvider>,
  );

  return {
    input: screen.getByLabelText(messages.billing.dayLabel) as HTMLInputElement,
    onUrlUpdate,
  };
}

/* -------------------------------------------------------------------------- */
/* 1. STANDART — KECHA                                                        */
/* -------------------------------------------------------------------------- */

describe("standart kun — ⛔ KECHA, bugun EMAS (C-3)", () => {
  test("⛔ `?day=` bo'lmaganda tanlagich KECHAGI kunni ko'rsatadi", () => {
    const { input } = renderPicker("");

    /*
     * ⛔ IKKI ALOHIDA DA'VO va ikkalasi ham kerak:
     *   (a) qiymat AYNAN kecha;
     *   (b) qiymat bugunga TENG EMAS — regressiya aynan shu shaklda
     *       keladi (`useDaySelection()` ni qayta ishlatish).
     */
    expect(input.value).toBe(YESTERDAY);
    expect(input.value === TODAY).toBe(false);
  });

  test("⛔ standart URL'ga YOZILMAYDI — toza havola o'z-o'zidan yangilanadi", () => {
    const { onUrlUpdate } = renderPicker("");

    /* Faqat render — foydalanuvchi hech nima tanlamadi, URL tegilmaydi. */
    expect(onUrlUpdate.mock.calls.length).toBe(0);
  });
});

/* -------------------------------------------------------------------------- */
/* 2. MAVJUD `?day=` — STANDART UNI USTIDAN YOZMAYDI                          */
/* -------------------------------------------------------------------------- */

describe("mavjud `?day=` o'qiladi", () => {
  test("URL'dagi o'tmish kuni tanlagichga TUSHADI", () => {
    const past = shiftIsoDay(TODAY, -5);
    const { input } = renderPicker(`?day=${past}`);

    expect(input.value).toBe(past);
  });

  test("⛔ `day = bugun` QONUNIY — u maksimum, taqiq emas", () => {
    const { input } = renderPicker(`?day=${TODAY}`);

    expect(input.value).toBe(TODAY);
  });

  test("yaroqsiz `?day=` JIMGINA standartga tushadi (xato ko'rsatilmaydi)", () => {
    const { input } = renderPicker("?day=2026-02-30");

    expect(input.value).toBe(YESTERDAY);
  });
});

/* -------------------------------------------------------------------------- */
/* 3. MAKSIMUM — BUGUN, IKKI QATLAMDA                                         */
/* -------------------------------------------------------------------------- */

describe("⛔ kelajakdagi kun tanlanmaydi", () => {
  test("`max` atributi BUGUNGI ISO sanaga teng", () => {
    const { input } = renderPicker("");

    expect(input.getAttribute("max")).toBe(TODAY);
  });

  test("⛔ ertangi kun RAD ETILADI — maydon darhol `aria-invalid` oladi", () => {
    const { input } = renderPicker("");

    fireEvent.change(input, { target: { value: TOMORROW } });

    expect(input.getAttribute("aria-invalid")).toBe("true");
  });

  test("⛔ ertangi kun URL'GA UMUMAN YOZILMAYDI — yozilganlar to'plami TENGLIGI", async () => {
    const past = shiftIsoDay(TODAY, -3);
    const { input, onUrlUpdate } = renderPicker("");

    /*
     * ⛔ IKKI O'ZGARISH BITTA TESTDA va bu ATAYIN. Yolg'iz «kelajakdan
     *   keyin 0 chaqiruv» da'vosi ⛔ BLIND edi: u «bu tanlagich hech
     *   qachon URL yozmaydi» holatida ham yashil qolardi. Ikkinchi,
     *   QONUNIY o'zgarish mexanizmning TIRIKLIGINI isbotlaydi — ya'ni
     *   birinchi qiymatning yo'qligi endi O'LCHANGAN farq.
     */
    fireEvent.change(input, { target: { value: TOMORROW } });
    fireEvent.change(input, { target: { value: past } });

    await waitFor(() => expect(onUrlUpdate.mock.calls.length).toBe(1));

    const written = new Set(
      onUrlUpdate.mock.calls.map((call) => call[0].searchParams.get("day")),
    );
    /* ⛔ TO'PLAM TENGLIGI (D-31): `TOMORROW` bu to'plamda YO'Q. */
    expect(written).toEqual(new Set([past]));
  });

  test("o'tmish kuni QABUL QILINADI — URL yoziladi va maydon yaroqli", async () => {
    const past = shiftIsoDay(TODAY, -5);
    const { input, onUrlUpdate } = renderPicker("");

    fireEvent.change(input, { target: { value: past } });

    await waitFor(() => expect(onUrlUpdate.mock.calls.length).toBe(1));
    expect(onUrlUpdate.mock.calls[0][0].searchParams.get("day")).toBe(past);
    expect(input.getAttribute("aria-invalid")).toBe("false");
  });
});
