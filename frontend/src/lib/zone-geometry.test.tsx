/**
 * G-19 — POLIGON GEOMETRIYASINING INVARIANTLARI (05-UI-SPEC §15).
 *
 * =============================================================================
 * NEGA BU DARVOZA BOR: bu funksiyalar noto'g'ri bo'lsa, xato POLIGON
 * GEOMETRIYASIGA yoziladi va u yerdan BILLING'ga o'tadi — jimgina,
 * dalilsiz. Zona bir marta noto'g'ri chizilsa, undan keyin har kuni
 * hisoblanadigan bandlik ham noto'g'ri bo'ladi va buni hech kim sezmaydi:
 * ekranda poligon "chiroyli" ko'rinaveradi.
 * =============================================================================
 *
 * ⚠ FAYL KENGAYTMASI `.tsx` VA BU MAJBURIY: `vitest.config.ts` ning
 *   `include` naqshi `src/**\/*.test.tsx`. `.ts` fayl JIMGINA ishga
 *   tushmasdi va «hammasi yashil» hisoboti yolg'on bo'lardi (03-08 da
 *   o'lchangan holat; `camera-page-state.test.tsx:16-20` naqshi).
 *
 * ⚠ 05-UI-SPEC §6.2 va 05-RESEARCH bu testni
 *   `frontend/scripts/zone-geometry.test.mjs` deb taklif qiladi — u
 *   BAJARILMAYDI (05-PATTERNS M-3): `node --test` TypeScript'ni import
 *   qila olmaydi. §S-13 ning A yo'li tanlandi.
 *
 * ⚠ KUTILGAN NATIJALAR QO'LDA HISOBLANGAN VA LITERAL YOZILGAN (§S-9).
 *   Tekshirilayotgan funksiya kutilgan qiymatni olish uchun HECH QAYERDA
 *   chaqirilmaydi — aks holda test o'z farazining aks-sadosiga aylanardi
 *   va formula noto'g'ri bo'lsa ham yashil qolardi.
 */
import { describe, expect, test } from "vitest";

import {
  MAX_VERTICES_PER_ZONE,
  MIN_VERTICES,
  addVertex,
  centroid,
  deleteVertex,
  denormalize,
  insertMidpoint,
  interpolateRow,
  isSelfIntersecting,
  moveVertex,
  normalize,
  polygonArea,
  translate,
  type Poly,
} from "@/lib/zone-geometry";

/* -------------------------------------------------------------------------- */
/* Fixture'lar — GEOMETRIK FAKT bo'yicha nomlangan (§S-9)                     */
/*                                                                            */
/* ⚠ `polygon_that_catches_the_box()` uslubidagi nom ATAYIN ISHLATILMAYDI:    */
/*   verdikt bo'yicha nomlangan fixture testni tekshirilayotgan qoidaning     */
/*   AKS-SADOSIGA aylantiradi.                                                */
/* -------------------------------------------------------------------------- */

/** Birlik kvadrat, soat miliga TESKARI (ekran koordinatasida). */
const UNIT_SQUARE_CCW: Poly = [
  [0, 0],
  [1, 0],
  [1, 1],
  [0, 1],
];

/** Birlik kvadrat, SOAT MILI bo'yicha — aylanish yo'nalishi teskari. */
const UNIT_SQUARE_CW: Poly = [
  [0, 0],
  [0, 1],
  [1, 1],
  [1, 0],
];

/**
 * «Qum soati»: ikki qarama-qarshi tepa ALMASHTIRILGAN kvadrat.
 * (1,0)→(0,1) qirrasi (1,1)→(0,0) qirrasi bilan (0.5, 0.5) da kesishadi.
 */
const HOURGLASS: Poly = [
  [0, 0],
  [1, 0],
  [0, 1],
  [1, 1],
];

/** Uch tepa — MIN_VERTICES chegarasidagi poligon. */
const TRIANGLE: Poly = [
  [0.1, 0.1],
  [0.9, 0.1],
  [0.5, 0.9],
];

/** Chuqur nusxa — kirish massivining O'ZGARMAGANINI tekshirish uchun. */
function snapshot(poly: Poly): number[][] {
  return poly.map(([x, y]) => [x, y]);
}

/* -------------------------------------------------------------------------- */
/* 1. normalize / denormalize — AYLANMA YO'QOTISHSIZ                          */
/* -------------------------------------------------------------------------- */

describe("normalize / denormalize (05-UI-SPEC §6.2)", () => {
  test("piksel → 0..1 — qo'lda hisoblangan literal", () => {
    // 640 / 1280 = 0.5 va 360 / 720 = 0.5 — ikkalasi ham aniq.
    expect(normalize([640, 360], 1280, 720)).toEqual([0.5, 0.5]);
    expect(normalize([0, 0], 1280, 720)).toEqual([0, 0]);
    expect(normalize([1280, 720], 1280, 720)).toEqual([1, 1]);
  });

  test("0..1 → piksel — qo'lda hisoblangan literal", () => {
    expect(denormalize([0.5, 0.5], 1280, 720)).toEqual([640, 360]);
    expect(denormalize([0.25, 0.75], 1280, 720)).toEqual([320, 540]);
  });

  test("⚠ AYLANMA YO'QOTISHSIZ — butun pikselda `denormalize(normalize(p)) === p`", () => {
    /*
     * ENG MUHIM ASSERT. Kenglik/balandlik ATAYIN ikkilik kasrga
     * bo'linmaydigan qiymatlar (1279, 719 — tub sonlar emas, lekin 2 ning
     * darajasi ham emas): 437/1279 ikkilik sanoqda aniq ifodalanmaydi,
     * ya'ni qo'pol ko'paytirish 436.99999999999994 berardi.
     *
     * Bu aylanma yo'qotsa, poligon HAR SAFAR ochilib saqlanganda joyidan
     * bir oz siljirdi va bir necha tahrirdan keyin zona rastadan
     * "sirg'alib" chiqardi — hech qanday xato xabarisiz.
     */
    for (const px of [
      [0, 0],
      [1, 1],
      [437, 291],
      [1278, 718],
      [1279, 719],
    ] as const) {
      expect(denormalize(normalize(px, 1279, 719), 1279, 719)).toEqual([
        px[0],
        px[1],
      ]);
    }
  });

  test("kenglik yoki balandlik 0 — `RangeError` (jimgina Infinity EMAS)", () => {
    expect(() => normalize([1, 1], 0, 720)).toThrow(RangeError);
    expect(() => normalize([1, 1], 1280, 0)).toThrow(RangeError);
    expect(() => denormalize([0.5, 0.5], 0, 720)).toThrow(RangeError);
  });
});

/* -------------------------------------------------------------------------- */
/* 2. moveVertex — 0..1 dan TASHQARIGA CHIQMAYDI                              */
/* -------------------------------------------------------------------------- */

describe("moveVertex — clamp(0, 1)", () => {
  test("⚠ kadr tashqarisidagi nuqta 0..1 ga QISILADI", () => {
    /*
     * Kadr tashqarisidagi tepa `cv2.pointPolygonTest` da ANIQLANMAGAN
     * natija beradi (05-RESEARCH §A.5) — ya'ni bandlik qarori
     * tushuntirib bo'lmaydigan holga kelardi.
     *
     * Qo'lda: [1.7, -0.4] → x 1 ga, y 0 ga qisiladi.
     */
    expect(moveVertex(TRIANGLE, 0, [1.7, -0.4])).toEqual([
      [1, 0],
      [0.9, 0.1],
      [0.5, 0.9],
    ]);
  });

  test("chegara ichidagi nuqta O'ZGARISHSIZ qo'yiladi", () => {
    expect(moveVertex(TRIANGLE, 2, [0.42, 0.58])).toEqual([
      [0.1, 0.1],
      [0.9, 0.1],
      [0.42, 0.58],
    ]);
  });

  test("kirish massivi O'ZGARMAYDI", () => {
    const before = snapshot(TRIANGLE);
    moveVertex(TRIANGLE, 0, [1.7, -0.4]);
    expect(snapshot(TRIANGLE)).toEqual(before);
  });

  test("indeks chegaradan tashqarida — RAD ETILADI (throw emas)", () => {
    expect(moveVertex(TRIANGLE, 9, [0.5, 0.5])).toEqual(snapshot(TRIANGLE));
    expect(moveVertex(TRIANGLE, -1, [0.5, 0.5])).toEqual(snapshot(TRIANGLE));
  });
});

/* -------------------------------------------------------------------------- */
/* 3. deleteVertex — 3 tepada O'ZGARISHSIZ (THROW EMAS)                       */
/* -------------------------------------------------------------------------- */

describe("deleteVertex — MIN_VERTICES himoyasi", () => {
  test("⚠ 3 tepada THROW QILMAYDI va o'sha uzunlikni qaytaradi", () => {
    /*
     * Funksiya himoyaning IKKINCHI qatlami, birinchisi emas: UI tugmani
     * `aria-disabled` bilan to'sadi (05-UI-SPEC §6.5). Bu yerda `throw`
     * bo'lsa, klaviatura yorlig'i (`Delete`) butun muharrirni yiqitardi.
     */
    expect(TRIANGLE).toHaveLength(MIN_VERTICES);

    const result = deleteVertex(TRIANGLE, 1);

    expect(result).toHaveLength(3);
    expect(result).toEqual([
      [0.1, 0.1],
      [0.9, 0.1],
      [0.5, 0.9],
    ]);
  });

  test("4 tepada tepa haqiqatan o'chiriladi — qo'lda hisoblangan literal", () => {
    // UNIT_SQUARE_CCW dan 1-indeksni ([1, 0]) olib tashlash.
    expect(deleteVertex(UNIT_SQUARE_CCW, 1)).toEqual([
      [0, 0],
      [1, 1],
      [0, 1],
    ]);
  });

  test("kirish massivi O'ZGARMAYDI", () => {
    const before = snapshot(UNIT_SQUARE_CCW);
    deleteVertex(UNIT_SQUARE_CCW, 1);
    expect(snapshot(UNIT_SQUARE_CCW)).toEqual(before);
  });
});

/* -------------------------------------------------------------------------- */
/* 4. addVertex / insertMidpoint                                              */
/* -------------------------------------------------------------------------- */

describe("addVertex — `index` dan KEYIN qo'yadi", () => {
  test("uzunlik +1 va yangi tepa aynan `index + 1` da", () => {
    expect(addVertex(TRIANGLE, 0, [0.5, 0.05])).toEqual([
      [0.1, 0.1],
      [0.5, 0.05],
      [0.9, 0.1],
      [0.5, 0.9],
    ]);
  });

  test("yangi tepa ham 0..1 ga QISILADI", () => {
    expect(addVertex(TRIANGLE, 2, [-3, 4])).toEqual([
      [0.1, 0.1],
      [0.9, 0.1],
      [0.5, 0.9],
      [0, 1],
    ]);
  });

  test("⚠ MAX_VERTICES_PER_ZONE da RAD ETILADI (T-05-12)", () => {
    /*
     * Chegarasiz poligon `jsonb` hajmini va har `pointermove` ning
     * narxini o'stiradi — 05-UI-SPEC §6.5 va T-05-12. Klientdagi
     * chegara QULAYLIK; ishonch manbai serverdagi `Settings`.
     */
    const maxed: Poly = Array.from(
      { length: MAX_VERTICES_PER_ZONE },
      (_unused, i) => [i / 100, 0.5] as const,
    );

    expect(maxed).toHaveLength(12);
    expect(addVertex(maxed, 0, [0.5, 0.5])).toHaveLength(12);
    expect(insertMidpoint(maxed, 0)).toHaveLength(12);
  });
});

describe("insertMidpoint — qirraning AYNAN o'rtasi", () => {
  test("qirra 0 ning o'rtasi — qo'lda hisoblangan literal", () => {
    // [0,0] va [1,0] orasidagi o'rta nuqta: ((0+1)/2, (0+0)/2) = (0.5, 0).
    expect(insertMidpoint(UNIT_SQUARE_CCW, 0)).toEqual([
      [0, 0],
      [0.5, 0],
      [1, 0],
      [1, 1],
      [0, 1],
    ]);
  });

  test("OXIRGI qirra yopiluvchi — [0,1] dan [0,0] ga", () => {
    // ((0+0)/2, (1+0)/2) = (0, 0.5), va u massivning oxiriga qo'yiladi.
    expect(insertMidpoint(UNIT_SQUARE_CCW, 3)).toEqual([
      [0, 0],
      [1, 0],
      [1, 1],
      [0, 1],
      [0, 0.5],
    ]);
  });

  test("uzunlik AYNAN +1", () => {
    expect(insertMidpoint(TRIANGLE, 1)).toHaveLength(TRIANGLE.length + 1);
  });
});

/* -------------------------------------------------------------------------- */
/* 5. translate                                                               */
/* -------------------------------------------------------------------------- */

describe("translate — nusxalash va siljitish", () => {
  test("oddiy siljish — qo'lda hisoblangan literal", () => {
    const box: Poly = [
      [0.1, 0.1],
      [0.3, 0.1],
      [0.3, 0.3],
      [0.1, 0.3],
    ];

    const moved = translate(box, 0.2, 0.1);

    // Qo'lda: har x ga +0.2, har y ga +0.1.
    expect(moved[0][0]).toBeCloseTo(0.3, 10);
    expect(moved[0][1]).toBeCloseTo(0.2, 10);
    expect(moved[2][0]).toBeCloseTo(0.5, 10);
    expect(moved[2][1]).toBeCloseTo(0.4, 10);
  });

  test("⚠ chegaraga urilganda SHAKL SAQLANADI — poligon deformatsiya BO'LMAYDI", () => {
    /*
     * Har tepani ALOHIDA qisish poligonni jimgina EZARDI: o'ng tomoni
     * 1 da to'planib, chap tomoni joyida qolardi va zona endi rastani
     * emas, boshqa shaklni o'lchardi. Shuning uchun qisiladigan narsa
     * tepa emas, SILJISH MIQDORI.
     *
     * Qo'lda: maxX = 0.3, ya'ni ruxsat etilgan eng katta dx = 1 - 0.3 = 0.7.
     * So'ralgan 0.9 → 0.7 ga qisiladi. Kenglik 0.2 bo'lib QOLADI.
     */
    const box: Poly = [
      [0.1, 0.1],
      [0.3, 0.1],
      [0.3, 0.3],
      [0.1, 0.3],
    ];

    const moved = translate(box, 0.9, 0);

    expect(moved[0][0]).toBeCloseTo(0.8, 10);
    expect(moved[1][0]).toBeCloseTo(1, 10);
    expect(moved[2][0]).toBeCloseTo(1, 10);
    expect(moved[3][0]).toBeCloseTo(0.8, 10);

    // Kenglik o'zgarmadi — bu shakl saqlanganining O'LCHOVI.
    expect(moved[1][0] - moved[0][0]).toBeCloseTo(0.2, 10);
    // y umuman tegilmadi.
    expect(moved[0][1]).toBeCloseTo(0.1, 10);
  });

  test("hamma tepa 0..1 ichida qoladi", () => {
    const moved = translate(TRIANGLE, -5, 5);

    for (const [x, y] of moved) {
      expect(x).toBeGreaterThanOrEqual(0);
      expect(x).toBeLessThanOrEqual(1);
      expect(y).toBeGreaterThanOrEqual(0);
      expect(y).toBeLessThanOrEqual(1);
    }
  });
});

/* -------------------------------------------------------------------------- */
/* 6. isSelfIntersecting — SAQLASH DARVOZASI                                  */
/* -------------------------------------------------------------------------- */

describe("isSelfIntersecting — saqlash darvozasi (T-05-11)", () => {
  test("⚠ SALBIY NAZORAT: «soat mili» to'rtburchak — `false`", () => {
    /*
     * Salbiy nazorat MAJBURIY: `return true` deb yozilgan buzuq
     * implementatsiya faqat ijobiy holat bilan ham yashil qolardi va
     * natijada HAR QANDAY poligonni saqlash bloklanardi.
     */
    expect(isSelfIntersecting(UNIT_SQUARE_CW)).toBe(false);
  });

  test("salbiy nazorat: soat miliga TESKARI to'rtburchak ham `false`", () => {
    // Aylanish yo'nalishi kesishishga aloqasi YO'Q.
    expect(isSelfIntersecting(UNIT_SQUARE_CCW)).toBe(false);
  });

  test("salbiy nazorat: uchburchak va botiq (konkav) beshburchak — `false`", () => {
    expect(isSelfIntersecting(TRIANGLE)).toBe(false);

    // «L» shakli — botiq, lekin kesishmagan.
    expect(
      isSelfIntersecting([
        [0, 0],
        [1, 0],
        [1, 0.4],
        [0.4, 0.4],
        [0.4, 1],
        [0, 1],
      ]),
    ).toBe(false);
  });

  test("⚠ IJOBIY NAZORAT: «qum soati» — `true`", () => {
    /*
     * O'zi bilan kesishgan poligon `supervision.PolygonZone` da
     * ANIQLANMAGAN natija beradi (05-RESEARCH §A.5) — ya'ni JIMGINA
     * NOTO'G'RI HISOB. Shuning uchun bu saqlashni to'sadi.
     */
    expect(isSelfIntersecting(HOURGLASS)).toBe(true);
  });

  test("ijobiy nazorat: tepasi o'z qirrasiga qaytgan «bant»", () => {
    expect(
      isSelfIntersecting([
        [0, 0],
        [1, 1],
        [1, 0],
        [0, 1],
      ]),
    ).toBe(true);
  });
});

/* -------------------------------------------------------------------------- */
/* 7. polygonArea / centroid                                                  */
/* -------------------------------------------------------------------------- */

describe("polygonArea va centroid", () => {
  test("birlik kvadratning yuzasi AYNAN 1", () => {
    expect(polygonArea(UNIT_SQUARE_CCW)).toBe(1);
  });

  test("yuza aylanish yo'nalishidan MUSTAQIL (modul qiymat)", () => {
    expect(polygonArea(UNIT_SQUARE_CW)).toBe(1);
  });

  test("uchburchakning yuzasi — qo'lda hisoblangan", () => {
    /*
     * Asos = 0.9 - 0.1 = 0.8; balandlik = 0.9 - 0.1 = 0.8.
     * Yuza = (0.8 * 0.8) / 2 = 0.32.
     */
    expect(polygonArea(TRIANGLE)).toBeCloseTo(0.32, 10);
  });

  test("birlik kvadratning markazi AYNAN [0.5, 0.5]", () => {
    expect(centroid(UNIT_SQUARE_CCW)).toEqual([0.5, 0.5]);
  });

  test("markaz — YUZA bo'yicha o'rtacha, tepalar o'rtachasi EMAS", () => {
    /*
     * ⚠ FARQNI KO'RSATADIGAN FIXTURE. Kvadratning pastki qirrasiga
     * QO'SHIMCHA tepa qo'yilgan: tepalar o'rtachasi shu qo'shimcha tepa
     * tomon SILJIYDI, yuza bo'yicha markaz esa joyida QOLADI.
     *
     * Tepalar: (0,0), (0.5,0), (1,0), (1,1), (0,1) — beshta.
     * Sodda o'rtacha:  x = 2.5/5 = 0.5;  y = 2/5 = 0.4   ← NOTO'G'RI
     * Yuza markazi:    x = 0.5;          y = 0.5         ← TO'G'RI
     */
    const withExtraVertex: Poly = [
      [0, 0],
      [0.5, 0],
      [1, 0],
      [1, 1],
      [0, 1],
    ];

    const [cx, cy] = centroid(withExtraVertex);

    expect(cx).toBeCloseTo(0.5, 10);
    expect(cy).toBeCloseTo(0.5, 10);
    expect(cy).not.toBeCloseTo(0.4, 3);
  });
});

/* -------------------------------------------------------------------------- */
/* 8. interpolateRow — §6.7 qator yordamchisi                                 */
/* -------------------------------------------------------------------------- */

describe("interpolateRow — qator yordamchisi (05-UI-SPEC §6.7)", () => {
  /** Qatorning BIRINCHI rastasi — kengligi 0.2. */
  const FIRST: Poly = [
    [0, 0],
    [0.2, 0],
    [0.2, 0.2],
    [0, 0.2],
  ];

  /** Qatorning OXIRGI rastasi — o'sha kenglik, o'ngga siljigan. */
  const LAST: Poly = [
    [0.8, 0],
    [1, 0],
    [1, 0.2],
    [0.8, 0.2],
  ];

  test("⚠ tepa soni TENG BO'LMASA — `[]` (jimgina yarim natija EMAS)", () => {
    /*
     * Tepama-tepa `lerp` faqat tepalar juftlashganda ma'noga ega.
     * Juftlanmagan holatda "eng yaqin tepani topish" ni o'ylab topish
     * mumkin edi — u ba'zan ishlab, ba'zan aralashib ketgan poligon
     * chizardi va admin buni FAQAT kadrga qarab sezardi.
     */
    expect(interpolateRow(TRIANGLE, LAST, 3)).toEqual([]);
    expect(interpolateRow(FIRST, TRIANGLE, 3)).toEqual([]);
  });

  test("tepa soni teng — AYNAN `n` ta poligon", () => {
    expect(interpolateRow(FIRST, LAST, 1)).toHaveLength(1);
    expect(interpolateRow(FIRST, LAST, 3)).toHaveLength(3);
    expect(interpolateRow(FIRST, LAST, 8)).toHaveLength(8);
  });

  test("`n = 1` — AYNAN o'rtadagi poligon, qo'lda hisoblangan literal", () => {
    /*
     * n = 1 → yagona oraliq t = 1/(1+1) = 0.5.
     * x: (0 + 0.8)/2 = 0.4;  (0.2 + 1)/2 = 0.6.  y umuman o'zgarmaydi.
     */
    const [middle] = interpolateRow(FIRST, LAST, 1);

    expect(middle[0][0]).toBeCloseTo(0.4, 10);
    expect(middle[0][1]).toBeCloseTo(0, 10);
    expect(middle[1][0]).toBeCloseTo(0.6, 10);
    expect(middle[2][0]).toBeCloseTo(0.6, 10);
    expect(middle[2][1]).toBeCloseTo(0.2, 10);
    expect(middle[3][0]).toBeCloseTo(0.4, 10);
  });

  test("`n = 3` — t = 0.25 / 0.5 / 0.75, qo'lda hisoblangan literal", () => {
    /*
     * t_k = k/(n+1), k = 1..3 → 0.25, 0.5, 0.75.
     * Birinchi tepaning x i: 0 + (0.8 - 0)*t → 0.2, 0.4, 0.6.
     */
    const row = interpolateRow(FIRST, LAST, 3);

    expect(row[0][0][0]).toBeCloseTo(0.2, 10);
    expect(row[1][0][0]).toBeCloseTo(0.4, 10);
    expect(row[2][0][0]).toBeCloseTo(0.6, 10);
  });

  test("natija BIRINCHI va OXIRGI poligonni O'Z ICHIGA OLMAYDI", () => {
    /*
     * Ular admin tomonidan allaqachon chizilgan. Qaytarilsa, qatorda
     * ustma-ust tushgan IKKI zona paydo bo'lardi va D-20 («birortasi
     * band desa band») ularni ikki marta sanardi.
     */
    const row = interpolateRow(FIRST, LAST, 3);

    for (const poly of row) {
      expect(poly[0][0]).toBeGreaterThan(0);
      expect(poly[0][0]).toBeLessThan(0.8);
    }
  });

  test("`n <= 0` — `[]`", () => {
    expect(interpolateRow(FIRST, LAST, 0)).toEqual([]);
    expect(interpolateRow(FIRST, LAST, -2)).toEqual([]);
  });
});

/* -------------------------------------------------------------------------- */
/* 9. IMMUTABILLIK — undo/redo stekining sharti                               */
/* -------------------------------------------------------------------------- */

describe("immutabillik (05-UI-SPEC §6.2)", () => {
  /*
   * Undo/redo steki NUSXA emas, HAVOLA ro'yxati (05-UI-SPEC §6.2). Ya'ni
   * bitta funksiya kirishni joyida o'zgartirsa, stekdagi BARCHA oldingi
   * holatlar ham o'zgarardi va «bekor qilish» hech nimani qaytarmasdi.
   */
  const BASE: Poly = [
    [0.2, 0.2],
    [0.8, 0.2],
    [0.8, 0.8],
    [0.2, 0.8],
  ];

  const MUTATING: ReadonlyArray<readonly [string, (poly: Poly) => Poly]> = [
    ["addVertex", (poly) => addVertex(poly, 0, [0.5, 0.1])],
    ["moveVertex", (poly) => moveVertex(poly, 0, [0.3, 0.3])],
    ["deleteVertex", (poly) => deleteVertex(poly, 0)],
    ["insertMidpoint", (poly) => insertMidpoint(poly, 0)],
    ["translate", (poly) => translate(poly, 0.05, 0.05)],
  ];

  for (const [name, apply] of MUTATING) {
    test(`\`${name}\` YANGI massiv qaytaradi va kirishga tegmaydi`, () => {
      const before = snapshot(BASE);
      const result = apply(BASE);

      expect(Object.is(BASE, result)).toBe(false);
      expect(snapshot(BASE)).toEqual(before);
    });
  }

  test("o'qish funksiyalari kirishga tegmaydi", () => {
    const before = snapshot(BASE);

    isSelfIntersecting(BASE);
    polygonArea(BASE);
    centroid(BASE);
    interpolateRow(BASE, BASE, 2);

    expect(snapshot(BASE)).toEqual(before);
  });

  test("⚠ RAD ETILGAN amal AYNAN O'SHA havolani qaytaradi", () => {
    /*
     * Bu immutabillikka ZID EMAS, uning ikkinchi yarmi: amal
     * BAJARILMAGANDA yangi massiv qaytarish undo stekiga bir xil
     * holatning ikkinchi nusxasini qo'shardi va `Ctrl+Z` «hech nima
     * qilmaydigan» qadamni bosib o'tishga majbur qilardi.
     *
     * Chaqiruvchi buni `Object.is` bilan bir bosqichda tekshiradi.
     */
    expect(Object.is(TRIANGLE, deleteVertex(TRIANGLE, 0))).toBe(true);
    expect(Object.is(BASE, moveVertex(BASE, 99, [0.5, 0.5]))).toBe(true);
    expect(Object.is(BASE, translate(BASE, 0, 0))).toBe(true);
  });
});
