/**
 * ANIQLIK BLOKI — RAQAM KONTEKST BILAN KELADI YOKI UMUMAN KELMAYDI.
 *
 * =============================================================================
 * ⛔ 1. `measured` SERVERNIKI VA KLIENT UNI QAYTA HISOBLAMAYDI.
 *
 *   Eng tabiiy «soddalashtirish» — klientda `n >= 20` deb yozish. U
 *   BUGUN bir xil natija berardi va ertaga chegara o'zgarganda jimgina
 *   ajralib ketardi. Shuning uchun test IKKI YO'NALISHDA ham o'lchaydi:
 *
 *     `n = 50`, `measured = false`  -> foiz YO'Q  (klient `n` ga qaramaydi)
 *     `min_sample = 25`, `n = 22`   -> matn 25 ni aytadi (konstanta
 *                                      klientda YOZILMAGAN)
 *
 * ⛔ 2. NUQTA BAHO ORALIQSIZ CHIZILMAYDI.
 *
 *   `percentView` sof funksiya sifatida sinaladi VA uning DOM'dagi
 *   oqibati ham. Yolg'iz foiz namuna ko'tara olmaydigan aniqlikni
 *   va'da qilardi.
 *
 * ⛔ 3. JAVOBSIZLAR `measured` DAN MUSTAQIL KO'RINADI.
 *
 *   Aynan o'lchanmagan holatda ular YAGONA ma'lumot bo'lib qoladi.
 *
 * ⛔ 4. IKKI XATO UCHUN IKKI XIL JUMLA — LITERAL.
 *
 *   Bitta umumiy jumla ikkalasini «xato» degan bir xil narsaga
 *   aylantirardi, holbuki biri ISHONCH, ikkinchisi PUL.
 *
 * ⛔⛔ 5. ICHKI MOSLIK QATORI YO'Q — VA DA'VO «SO'Z YO'Q» EMAS.
 *
 *   «Falon so'z topilmadi» degan assert komponentda hech qachon
 *   bo'lmagan narsa uchun HAR DOIM yashil bo'lardi. Shuning uchun
 *   o'lchov STRUKTURAVIY: `round-summary.test.tsx` qatorlar
 *   TO'PLAMINI qulflaydi va sxema darajasidagi rad etish
 *   `occupancy-queries.test.tsx` da.
 * =============================================================================
 */
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, test } from "vitest";

import messages from "../../../messages/uz-Latn.json";
import {
  ConfusionMatrix,
  percentView,
} from "@/components/occupancy/confusion-matrix";
import type { AccuracyReport } from "@/lib/api-types";

/** §11.1 ning ISHLANGAN MISOLI — sonlar spetsifikatsiyadan. */
function report(overrides: Partial<AccuracyReport> = {}): AccuracyReport {
  return {
    from_date: "2026-08-16",
    to_date: "2026-09-14",
    drawn: 640,
    answered: 618,
    unanswered: 22,
    dont_know: 6,
    matrix: {
      true_occupied: 401,
      false_occupied: 23,
      false_empty: 38,
      true_empty: 150,
    },
    n: 612,
    measured: true,
    min_sample: 20,
    base_rate: 0.7173,
    correct: { point: 0.9003, lower: 0.874, upper: 0.9219 },
    false_occupied: { point: 0.0542, lower: 0.0364, upper: 0.0799 },
    false_empty: { point: 0.0866, lower: 0.0637, upper: 0.1166 },
    ...overrides,
  };
}

const NOT_MEASURED = {
  measured: false,
  base_rate: null,
  correct: { point: null, lower: null, upper: null },
  false_occupied: { point: null, lower: null, upper: null },
  false_empty: { point: null, lower: null, upper: null },
} satisfies Partial<AccuracyReport>;

function renderMatrix(value: AccuracyReport) {
  return render(
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      timeZone="Asia/Tashkent"
    >
      <ConfusionMatrix report={value} />
    </NextIntlClientProvider>,
  );
}

/* -------------------------------------------------------------------------- */
/* 1. SOF FUNKSIYA                                                            */
/* -------------------------------------------------------------------------- */

describe("percentView — nuqta baho ORALIQSIZ chiqmaydi", () => {
  test("uchala chegara ham bo'lsa foizga aylantiriladi", () => {
    const view = percentView({ point: 0.9, lower: 0.87, upper: 0.92 });

    /*
     * ⚠ `toBeCloseTo`, `toEqual` EMAS: `0.87 * 100` ikkilik suzuvchi
     *   nuqtada aniq 87 bo'lmasligi mumkin. Aniq qiymatga bog'lanish
     *   testni MIQYOS emas, ARIFMETIKA xossasiga bog'lardi.
     */
    expect(view?.point).toBeCloseTo(90, 9);
    expect(view?.lower).toBeCloseTo(87, 9);
    expect(view?.upper).toBeCloseTo(92, 9);
  });

  test("⛔ birorta chegara `null` bo'lsa natija ham `null`", () => {
    expect(percentView({ point: 0.9, lower: null, upper: 0.92 })).toBeNull();
    expect(percentView({ point: 0.9, lower: 0.87, upper: null })).toBeNull();
    expect(percentView({ point: null, lower: 0.87, upper: 0.92 })).toBeNull();
  });

  test("⚠ funksiya BO'LMAYDI — u faqat miqyosni o'zgartiradi", () => {
    /*
     * Nazorat: kirish `p` bilan chiqish `point` ORASIDA 100 dan boshqa
     * hech qanday munosabat yo'q. Agar bu yerda `successes / n` paydo
     * bo'lsa, u serverdan MUSTAQIL ikkinchi javob bo'lardi.
     */
    const view = percentView({ point: 0.0542, lower: 0.0364, upper: 0.0799 });
    expect(view?.point).toBeCloseTo(5.42, 6);
  });
});

/* -------------------------------------------------------------------------- */
/* 2. O'LCHANGAN HOLAT                                                        */
/* -------------------------------------------------------------------------- */

describe("matritsa o'lchangan holatda", () => {
  test("to'rt katak, `n` va bazaviy ulush render bo'ladi", () => {
    renderMatrix(report());

    for (const value of ["401", "23", "38", "150"]) {
      expect(screen.getByText(value)).toBeTruthy();
    }
    expect(screen.getByText(/n=612/u)).toBeTruthy();
    expect(screen.getByText("Rastalarning 71,7 % i band edi")).toBeTruthy();
  });

  test("uch oraliq ham chiqadi va foizlar SERVER qiymatidan", () => {
    renderMatrix(report());

    expect(screen.getByText("To'g'ri: 90,0 % (87,4 – 92,2)")).toBeTruthy();
    expect(screen.getByText("Band deb xato: 5,4 % (3,6 – 8,0)")).toBeTruthy();
    expect(screen.getByText("Bo'sh deb xato: 8,7 % (6,4 – 11,7)")).toBeTruthy();
  });

  test("⛔ ikki xato uchun IKKI XIL jumla", () => {
    renderMatrix(report());

    const disputeRisk = screen.getByText(
      "Sotuvchidan nohaq patta so'ralishi mumkin — nizo xavfi.",
    );
    const lostPatta = screen.getByText("Band rastadan patta yig'ilmay qoladi.");

    expect(disputeRisk.textContent).not.toBe(lostPatta.textContent);
  });

  test("⛔ oraliq yo'q bo'lsa nuqta baho ham chizilmaydi", () => {
    renderMatrix(
      report({ correct: { point: 0.9003, lower: null, upper: null } }),
    );

    expect(screen.queryByText(/To'g'ri:/u)).toBeNull();
    /* Nazorat: qolgan ikkitasi joyida. */
    expect(screen.getByText(/Band deb xato:/u)).toBeTruthy();
  });

  test("semantika NATIVE jadval — `<caption>`, `col` va `row` sarlavhalari", () => {
    const { container } = renderMatrix(report());

    expect(container.querySelector("table > caption")).not.toBeNull();
    expect(container.querySelectorAll("th[scope='col']").length).toBe(2);
    expect(container.querySelectorAll("th[scope='row']").length).toBe(2);
  });
});

/* -------------------------------------------------------------------------- */
/* 3. O'LCHANMAGAN HOLAT (O-4)                                                */
/* -------------------------------------------------------------------------- */

describe("`measured === false` — BIRORTA foiz chizilmaydi", () => {
  test("`n = 19` da matritsa O'RNIGA matn va `%` belgisi UMUMAN yo'q", () => {
    const { container } = renderMatrix(
      report({ ...NOT_MEASURED, n: 19, drawn: 25, answered: 19, unanswered: 6 }),
    );

    expect(
      screen.getByText(
        "Aniqlik hali o'lchanmadi — kamida 20 ta javob kerak. Hozircha: 19.",
      ),
    ).toBeTruthy();
    expect(container.querySelector("table")).toBeNull();
    expect(container.textContent ?? "").not.toContain("%");
  });

  test("⛔ chegara SERVERDAN — klientda 20 yozilmagan", () => {
    /*
     * `min_sample = 25` da matn 25 ni aytishi SHART. Klient
     * `MIN_SAMPLE_FOR_PERCENT` ni o'zi yozgan bo'lsa, bu test qizaradi.
     */
    renderMatrix(report({ ...NOT_MEASURED, min_sample: 25, n: 22 }));

    expect(
      screen.getByText(
        "Aniqlik hali o'lchanmadi — kamida 25 ta javob kerak. Hozircha: 22.",
      ),
    ).toBeTruthy();
  });

  test("⛔ `n` katta bo'lsa ham `measured === false` foizni CHIZDIRMAYDI", () => {
    /*
     * Klient `n >= min_sample` deb qayta hisoblasa, bu holatda foiz
     * chizilardi — ya'ni sabotaj aynan shu yerda qizaradi.
     */
    const { container } = renderMatrix(
      report({ ...NOT_MEASURED, n: 50, min_sample: 20 }),
    );

    expect(container.textContent ?? "").not.toContain("%");
    expect(container.querySelector("table")).toBeNull();
  });
});

/* -------------------------------------------------------------------------- */
/* 4. NAMUNANING HALOLLIGI                                                    */
/* -------------------------------------------------------------------------- */

describe("javobsizlar namunadan CHIQMAYDI", () => {
  test("javobsiz va «aniq ayta olmadi» sonlari o'lchangan holatda ko'rinadi", () => {
    renderMatrix(report());
    expect(
      screen.getByText(
        "Namunaga tushdi: 640 · Javob berildi: 618 · Javobsiz: 22 · Aniq ayta olmadi: 6",
      ),
    ).toBeTruthy();
  });

  test("⛔ O'LCHANMAGAN holatda ham ko'rinadi — u yerda YAGONA ma'lumot", () => {
    renderMatrix(
      report({ ...NOT_MEASURED, drawn: 25, answered: 19, unanswered: 6, dont_know: 1, n: 18 }),
    );
    expect(
      screen.getByText(
        "Namunaga tushdi: 25 · Javob berildi: 19 · Javobsiz: 6 · Aniq ayta olmadi: 1",
      ),
    ).toBeTruthy();
  });

  test("javobsiz bo'lsa namunaning TO'LIQ EMASLIGI ochiq aytiladi", () => {
    renderMatrix(report());
    expect(
      screen.getByText(
        "22 ta band javobsiz qoldi — bu son namunaning to'liq emasligini bildiradi.",
      ),
    ).toBeTruthy();
  });

  test("javobsiz nol bo'lsa ogohlantirish jumlasi YO'Q, son esa BOR", () => {
    renderMatrix(report({ unanswered: 0 }));

    expect(screen.queryByText(/namunaning to'liq emasligini/u)).toBeNull();
    expect(screen.getByText(/Javobsiz: 0/u)).toBeTruthy();
  });
});

/* -------------------------------------------------------------------------- */
/* 5. QURILMAGAN BOSHQARUVLAR                                                 */
/* -------------------------------------------------------------------------- */

describe("aralashtiradigan yoki qayta tortadigan boshqaruv YO'Q", () => {
  test("⛔ davr tanlagichi ham, `eval`/`train` filtri ham yo'q", () => {
    /*
     * D-14: hisobot FAQAT ko'r namunaning `eval` qismidan chiqadi.
     * Har qanday tanlagich — davr, navbat turi, maqsad — o'sha
     * bo'linishni aralashtirish yo'lini ochardi.
     */
    const { container } = renderMatrix(report());

    expect(container.querySelector("select")).toBeNull();
    expect(container.querySelector("input")).toBeNull();
    expect(container.querySelector("button")).toBeNull();
  });

  test("⛔ diagramma yo'q — sonlar MATN sifatida", () => {
    const { container } = renderMatrix(report());
    expect(container.querySelector("[class*='recharts']")).toBeNull();
    expect(container.querySelector("canvas")).toBeNull();
  });

  test("sarlavha namunaning MANBASINI aniq aytadi", () => {
    renderMatrix(report());
    expect(
      screen.getByText(/Ko'rmasdan tekshirish namunasidan/u),
    ).toBeTruthy();
  });
});
