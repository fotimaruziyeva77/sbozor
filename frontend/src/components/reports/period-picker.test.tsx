/**
 * DAVR TANLAGICHI — ⛔ MAKSIMUM KECHA, STANDART OXIRGI 30 KUN (§4.4, G-38(c)(d)).
 *
 * =============================================================================
 * ⛔⛔ 1. SOAT QOTIRILADI — DEVOR SOATIGA BOG'LIQ TEST YOZILMAYDI.
 *
 *   `billing/day-picker.test.tsx` bitta `new Date()` instansiyasini ham
 *   komponentga, ham kutilmaga uzatib bu muammoni yechgan. Bu yerda esa
 *   YETMAYDI: da'volardan biri ⛔ «OYNING 1-KUNI» xulqini o'lchaydi va u
 *   yugurtirilgan kunga bog'liq bo'lsa, test oyiga bir kun boshqa
 *   natija berardi (07 №3 ning aynan takrori). Shuning uchun soat
 *   `vi.setSystemTime` bilan QOTIRILADI va `now` o'sha qotirilgan
 *   lahzadan HOSILA.
 *
 * ⚠ FAQAT `Date` SOXTALASHTIRILADI (`toFake: ["Date"]`): `setTimeout` va
 *   `setInterval` HAQIQIY qoladi, aks holda `waitFor` (nuqs URL yozuvini
 *   kutadi) hech qachon uyg'onmasdi.
 *
 * ⛔ 2. YO'QLIK ⛔ TO'PLAM TENGLIGI bilan o'lchanadi (D-31).
 *
 *   «Bugungi sana DOM'da yo'q» da'vosi bitta qiymatni izlaydigan inkor
 *   matcher bilan yozilsa, u FAQAT o'sha qiymatni ushlardi va yonidagi
 *   ikkinchi sanani ko'rmasdi. Shuning uchun DOM'dagi BARCHA ISO
 *   sanalari yig'iladi va to'plam KUTILGAN ikkilik bilan solishtiriladi.
 *
 * ⛔ 3. KUTILGAN SANALAR SANALADI, LITERAL YOZILMAYDI — ular qotirilgan
 *   soatdan `shiftIsoDay` orqali chiqariladi. Yagona LITERAL sanalar —
 *   teskari oraliq testining KIRISHI, chunki u ataylab hech qaysi
 *   presetga mos KELMASLIGI kerak.
 * =============================================================================
 */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { RenderResult } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { NuqsTestingAdapter } from "nuqs/adapters/testing";
import { afterEach, describe, expect, test, vi } from "vitest";

import messages from "../../../messages/uz-Latn.json";
import { PeriodPicker } from "@/components/reports/period-picker";
import { shiftIsoDay } from "@/components/snapshots/day-picker";

const TIME_ZONE = "Asia/Tashkent";

/** ⚠ Josus TIPLANGAN (`billing/day-picker.test.tsx:62` naqshi). */
type UrlUpdate = { searchParams: URLSearchParams };

/**
 * Soatni qotiradi va o'sha lahzani qaytaradi.
 *
 * ⚠ Vaqt Toshkent yarim kuniga qo'yiladi: yarim tunga yaqin qiymat
 *   UTC↔UTC+5 chegarasida biznes-kunni bir kunga siljitardi va test
 *   O'ZI o'lchayotgan xulqni emas, chegarani o'lchab qolardi.
 */
function freezeClock(dayIso: string): Date {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date(`${dayIso}T12:00:00+05:00`));
  return new Date();
}

afterEach(() => {
  vi.useRealTimers();
});

function renderPicker(searchParams: string, now: Date) {
  const onUrlUpdate = vi.fn<(event: UrlUpdate) => void>();

  const view = render(
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      now={now}
      timeZone={TIME_ZONE}
    >
      <NuqsTestingAdapter onUrlUpdate={onUrlUpdate} searchParams={searchParams}>
        <PeriodPicker />
      </NuqsTestingAdapter>
    </NextIntlClientProvider>,
  );

  return { onUrlUpdate, view };
}

/**
 * DOM'da UCHRAGAN barcha ISO kunlari — maydon qiymatlari VA matn tugunlari.
 *
 * ⛔ Ikkala manba ham kerak: `input.value` `textContent` ga TUSHMAYDI, matn
 *    esa (`reports.periodShown`) maydonlarda yo'q. Bittasi tashlab
 *    ketilsa, da'vo JIMGINA torayardi.
 */
function isoDaysInDom(view: RenderResult): Set<string> {
  const found = new Set<string>();

  for (const input of view.container.querySelectorAll("input")) {
    if (input.value !== "") found.add(input.value);
  }
  for (const hit of (view.container.textContent ?? "").matchAll(
    /\d{4}-\d{2}-\d{2}/gu,
  )) {
    found.add(hit[0]);
  }

  return found;
}

/** Standart davr — `to` = kecha, `from` = kecha − 29 (§4.4). */
function defaultRange(todayIso: string): { from: string; to: string } {
  const to = shiftIsoDay(todayIso, -1);
  return { from: shiftIsoDay(to, -29), to };
}

/**
 * Tanlagich chizgan BARCHA matn paragraflari.
 *
 * ⛔ G-38(d) YO'QLIKNI shu to'plamning TENGLIGI bilan o'lchaydi, bitta
 *    satrni izlaydigan inkor matcher bilan EMAS (D-31): inkor matcher
 *    faqat O'SHA satrni ushlardi va yonida paydo bo'lgan ikkinchi,
 *    boshqacha formatlangan davr jumlasini KO'RMASDI.
 */
function paragraphsIn(view: RenderResult): Set<string> {
  return new Set(
    [...view.container.querySelectorAll("p")].map(
      (node) => node.textContent ?? "",
    ),
  );
}

/* -------------------------------------------------------------------------- */
/* (a) G-38(c) — MAKSIMUM ATRIBUTI KECHAGA TENG                               */
/* -------------------------------------------------------------------------- */

describe("⛔ G-38(c): yuqori chegara — KECHA", () => {
  test("ikkala sana maydonining `max` atributi KECHAGI kunga teng", () => {
    const today = "2026-08-16";
    const now = freezeClock(today);
    const yesterday = shiftIsoDay(today, -1);

    renderPicker("", now);

    const from = screen.getByLabelText(
      messages.reports.periodFrom,
    ) as HTMLInputElement;
    const to = screen.getByLabelText(
      messages.reports.periodTo,
    ) as HTMLInputElement;

    /*
     * ⛔ IKKI ALOHIDA DA'VO va ikkalasi ham kerak (billing testining
     *   qoidasi): (a) qiymat AYNAN kecha; (b) qiymat BUGUNGA teng emas —
     *   regressiya aynan shu shaklda keladi, chunki 4 va 5-fazadagi
     *   ikkala tanlagichning ham `max` i BUGUN va ularni «qayta
     *   ishlatish» juda tabiiy ko'rinadi.
     */
    expect(from.getAttribute("max")).toBe(yesterday);
    expect(to.getAttribute("max")).toBe(yesterday);
    expect(to.getAttribute("max") === today).toBe(false);
  });
});

/* -------------------------------------------------------------------------- */
/* (b) G-38(c) — `?to=<bugun>` STANDARTGA TUSHADI                             */
/* -------------------------------------------------------------------------- */

describe("⛔ G-38(c): bugungi sana yuzaga CHIQMAYDI", () => {
  test("`?to=<bugun>` standartga tushadi — DOM'dagi sanalar to'plami STANDART", () => {
    const today = "2026-08-16";
    const now = freezeClock(today);
    const expected = defaultRange(today);

    /*
     * ⛔⛔ `from` HAM UZATILADI VA U YAROQLI — bu band O'LCHOV BILAN
     *    qo'shilgan. Yolg'iz `?to=<bugun>` bilan chaqirilganda oraliq
     *    `from` NING YO'QLIGI tufayli standartga tushardi, ya'ni test
     *    «kelajakdagi `to` rad etiladi» ni EMAS, «yarim oraliq rad
     *    etiladi» ni o'lchardi. O'lchandi: chegara filtri olib
     *    tashlanganda test YASHIL qolgan.
     */
    const validFrom = shiftIsoDay(today, -10);
    const { view } = renderPicker(`?from=${validFrom}&to=${today}`, now);

    /*
     * ⛔ TO'PLAM TENGLIGI: bugungi sana DOM'ning HECH QAYERIDA yo'q —
     *   na maydonda, na `reports.periodShown` matnida. Bu «kam
     *   ko'rsatilgan raqam faylga tushib tarqalishi» ning (T-08-37)
     *   birinchi qatlami.
     */
    expect(isoDaysInDom(view)).toEqual(new Set([expected.from, expected.to]));
  });
});

/* -------------------------------------------------------------------------- */
/* (c) TESKARI ORALIQ — ⛔ ALMASHTIRILMAYDI, standartga tushadi                */
/* -------------------------------------------------------------------------- */

describe("⛔ teskari oraliq JIMGINA standartga tushadi", () => {
  test("`?from=2026-09-30&to=2026-09-01` → standart; so'ralgan qiymatlar DOM'da YO'Q", () => {
    const today = "2026-08-16";
    const now = freezeClock(today);
    const expected = defaultRange(today);

    /*
     * ⚠ KIRISH LITERAL va bu ATAYIN: qiymatlar qotirilgan kundan
     *   hosila bo'lsa, ular tasodifan biror presetning oralig'iga MOS
     *   kelib qolishi mumkin edi — o'shanda test o'zi o'lchamoqchi
     *   bo'lgan «teskari» yo'lni umuman bosib o'tmasdi.
     */
    const { view } = renderPicker("?from=2026-09-30&to=2026-09-01", now);

    /* ⛔ ALMASHTIRISH YO'Q: `2026-09-01`/`2026-09-30` to'plamda ko'rinmaydi. */
    expect(isoDaysInDom(view)).toEqual(new Set([expected.from, expected.to]));
  });
});

/* -------------------------------------------------------------------------- */
/* (d) G-38(d) — `thisMonth` OYNING 1-KUNIDA NOMLANGAN HOLAT BERADI           */
/* -------------------------------------------------------------------------- */

describe("⛔ G-38(d): `thisMonth` oyning 1-kunida", () => {
  test("NAZORAT — oddiy kunda `thisMonth` DAVR JUMLASINI chizadi", () => {
    /*
     * ⛔ BU NAZORAT BUSIZ QUYIDAGI DA'VO KO'R BO'LARDI: tanlagich davr
     *   jumlasini UMUMAN chizmasa ham, «jumla yo'q» asserti yashil
     *   qolardi. Farq shu ikki testning O'LCHANGAN qarama-qarshiligidan
     *   chiqadi.
     */
    const now = freezeClock("2026-08-16");
    const { view } = renderPicker("", now);

    fireEvent.change(screen.getByLabelText(messages.reports.presetLabel), {
      target: { value: "thisMonth" },
    });

    expect(paragraphsIn(view)).toEqual(
      new Set([messages.reports.maxDayHint, "2026-08-01 — 2026-08-15"]),
    );
  });

  test("⛔ oyning 1-kunida DAVR JUMLASI yo'q, «hali yopilgan kun yo'q» BOR", () => {
    /*
     * ⛔ 1-KUNDA `thisMonth` = {bugun, kecha}, ya'ni oraliq BO'SH. Bu
     *   holat `lastMonth` ga ⛔ TUSHIRILMAYDI va jimgina ham
     *   o'zgarmaydi: jimgina boshqa oyni ko'rsatish direktorga
     *   ⛔ NOTO'G'RI OYNING raqamini berardi va u buni sezmasdi.
     */
    const now = freezeClock("2026-09-01");
    const { view } = renderPicker("", now);

    fireEvent.change(screen.getByLabelText(messages.reports.presetLabel), {
      target: { value: "thisMonth" },
    });

    /*
     * ⛔ TO'PLAM TENGLIGI bir vaqtda IKKI da'voni bajaradi:
     *   • `reports.periodShown` (`2026-09-01 — 2026-08-31`) DOM'da YO'Q;
     *   • bo'sh holat 5 (§14.7) BOR va u chegara sababini takrorlaydi.
     */
    expect(paragraphsIn(view)).toEqual(
      new Set([messages.reports.emptyMonth, messages.reports.maxDayHint]),
    );
  });
});

/* -------------------------------------------------------------------------- */
/* (e) STANDART DAVRDA URL'GA PARAMETR YOZILMAYDI                             */
/* -------------------------------------------------------------------------- */

describe("URL — standart parametrsiz, tanlov esa yoziladi", () => {
  test("⛔ standart davr URL'ga YOZILMAYDI, lekin preset tanlovi YOZILADI", async () => {
    const today = "2026-08-16";
    const now = freezeClock(today);

    const { onUrlUpdate } = renderPicker("", now);

    /* Render — foydalanuvchi hech nima tanlamadi, URL tegilmaydi. */
    expect(onUrlUpdate.mock.calls.length).toBe(0);

    /*
     * ⛔ IKKINCHI, QONUNIY O'ZGARISH MEXANIZMNING TIRIKLIGINI isbotlaydi
     *   (billing testining o'lchangan darsi): yolg'iz «0 chaqiruv»
     *   da'vosi «bu tanlagich hech qachon URL yozmaydi» holatida ham
     *   yashil qolardi.
     */
    fireEvent.change(screen.getByLabelText(messages.reports.presetLabel), {
      target: { value: "yesterday" },
    });

    await waitFor(() => expect(onUrlUpdate.mock.calls.length).toBe(1));

    const written = onUrlUpdate.mock.calls[0][0].searchParams;
    const yesterday = shiftIsoDay(today, -1);
    expect(written.get("from")).toBe(yesterday);
    expect(written.get("to")).toBe(yesterday);
  });
});
