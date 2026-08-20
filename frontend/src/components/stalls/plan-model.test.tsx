/**
 * QO'LDA CHIZILGAN PLAN — MODEL DARVOZALARI (260820).
 *
 * =============================================================================
 * ⛔⛔ BU FAYL CHIZMANI YO'QOTISHDAN QO'RIQLAYDI.
 *
 *   Chizma — odamning QO'L MEHNATI: 300 rastali bozorda uni bir marta
 *   chizish soatlab vaqt oladi. Shuning uchun bu yerdagi har bir da'vo
 *   bitta savolga javob beradi: «shu qadam chizmaning bir qismini
 *   jimgina yo'qotadimi?»
 *
 *   Yo'qotishning uch yo'li qulflangan:
 *     1. Panjaradan tashqarida qolgan rasta (ko'rinmaydi, o'chirilmaydi);
 *     2. Ustma-ust qo'yilgan ikki rasta (bittasi ko'zdan g'oyib bo'ladi);
 *     3. Farqga tushmay qolgan o'zgarish (saqlangandek ko'rinadi).
 * =============================================================================
 */
import { describe, expect, test } from "vitest";

import {
  GROW_STEP,
  MIN_COLS,
  MIN_ROWS,
  cellsBetween,
  clearSequence,
  clearSpot,
  gridSize,
  isEmptyDiff,
  occupancyOf,
  placeSequence,
  placeStall,
  placementFromZones,
  planDiff,
  queueOf,
} from "@/components/stalls/plan-model";
import type { MapZone } from "@/lib/api-types";

function cell(
  id: string,
  code: string,
  plan: { x: number; y: number } | null = null,
) {
  return {
    id,
    code,
    status: "active" as const,
    has_vendor: true,
    plan_x: plan?.x ?? null,
    plan_y: plan?.y ?? null,
  };
}

const ZONES: MapZone[] = [
  {
    id: "11111111-1111-4111-8111-111111111111",
    name: "Meva-sabzavot",
    cells: [cell("s1", "2", { x: 3, y: 1 }), cell("s2", "10")],
  },
  {
    id: "22222222-2222-4222-8222-222222222222",
    name: "Go'sht",
    cells: [cell("s3", "100"), cell("s4", "7", { x: 0, y: 0 })],
  },
];

describe("placementFromZones", () => {
  test("faqat koordinatasi BOR rasta chizmaga kiradi", () => {
    expect(placementFromZones(ZONES)).toEqual({
      s1: { x: 3, y: 1 },
      s4: { x: 0, y: 0 },
    });
  });

  test("⭐ (0,0) — HAQIQIY joy, «chizilmagan» EMAS", () => {
    /*
     * ⛔ `if (!cell.plan_x)` yozilsa chap-yuqori burchakdagi rasta
     *    har yuklashda chizmadan tushib ketardi.
     */
    expect(placementFromZones(ZONES).s4).toEqual({ x: 0, y: 0 });
  });

  test("yarim koordinata — chizilmagan deb qabul qilinadi", () => {
    const broken: MapZone[] = [
      {
        id: ZONES[0]!.id,
        name: "X",
        cells: [{ ...cell("s9", "9"), plan_x: 4, plan_y: null }],
      },
    ];
    expect(placementFromZones(broken)).toEqual({});
  });
});

describe("gridSize", () => {
  test("bo'sh chizma — eng kichik panjara", () => {
    expect(gridSize({})).toEqual({ cols: MIN_COLS, rows: MIN_ROWS });
  });

  test("⭐ PANJARA CHIZMANI O'Z ICHIGA OLADI — chekkadagi rasta ko'rinadi", () => {
    /*
     * ⛔⛔ Eng muhim da'vo: `x: 40` dagi rasta 12 ustunli panjarada
     *     EKRANDAN CHIQIB KETARDI — odam uni ko'rmaydi, o'chira olmaydi,
     *     lekin u bazada turibdi.
     */
    const size = gridSize({ far: { x: 40, y: 25 } });
    expect(size.cols).toBeGreaterThan(40);
    expect(size.rows).toBeGreaterThan(25);
  });

  test("kengaytirish qo'shiladi", () => {
    expect(gridSize({}, GROW_STEP, 0)).toEqual({
      cols: MIN_COLS + GROW_STEP,
      rows: MIN_ROWS,
    });
  });

  test("panjara sxema chegarasidan OSHMAYDI", () => {
    /* ⛔ 1000 dan katta indeks serverda 422 bilan qaytardi. */
    const size = gridSize({ edge: { x: 999, y: 999 } }, 100, 100);
    expect(size.cols).toBe(1000);
    expect(size.rows).toBe(1000);
  });
});

describe("queueOf", () => {
  test("chizilmaganlar SERVER tartibida, zona nomi bilan", () => {
    expect(queueOf(ZONES, placementFromZones(ZONES))).toEqual([
      { id: "s2", code: "10", zoneName: "Meva-sabzavot" },
      { id: "s3", code: "100", zoneName: "Go'sht" },
    ]);
  });

  test("hammasi chizilgan — navbat bo'sh", () => {
    const all = { s1: { x: 0, y: 0 }, s2: { x: 1, y: 0 }, s3: { x: 2, y: 0 }, s4: { x: 3, y: 0 } };
    expect(queueOf(ZONES, all)).toEqual([]);
  });
});

describe("placeStall", () => {
  test("bo'sh katakka qo'yiladi", () => {
    expect(placeStall({}, "s1", 2, 3)).toEqual({ s1: { x: 2, y: 3 } });
  });

  test("⭐ BAND katak RAD ETILADI — ustma-ust rasta bo'lmaydi", () => {
    const before = { s1: { x: 2, y: 3 } };
    expect(placeStall(before, "s2", 2, 3)).toBe(before);
  });

  test("O'SHA rastani O'SHA katakka qayta qo'yish — zararsiz", () => {
    /*
     * ⛔ Surish paytida `pointerover` bir katakda BIR NECHA marta
     *    ishlaydi; bu holat rad etilsa rasta jimgina yo'qolardi.
     */
    const before = { s1: { x: 2, y: 3 } };
    expect(placeStall(before, "s1", 2, 3)).toBe(before);
  });

  test("ko'chirish — eski katak BO'SHAYDI", () => {
    const after = placeStall({ s1: { x: 2, y: 3 } }, "s1", 5, 5);
    expect(after).toEqual({ s1: { x: 5, y: 5 } });
    expect(occupancyOf(after).get("2:3")).toBeUndefined();
  });

  test("chegaradan tashqari — o'zgarishsiz qaytadi", () => {
    const before = {};
    expect(placeStall(before, "s1", 1000, 0)).toBe(before);
    expect(placeStall(before, "s1", -1, 0)).toBe(before);
  });
});

describe("clearSpot", () => {
  test("katakdagi rasta chizmadan chiqadi", () => {
    expect(clearSpot({ s1: { x: 2, y: 3 } }, 2, 3)).toEqual({});
  });

  test("bo'sh katakni o'chirish — zararsiz", () => {
    const before = { s1: { x: 2, y: 3 } };
    expect(clearSpot(before, 9, 9)).toBe(before);
  });

  test("o'chirilgan rasta NAVBATGA qaytadi", () => {
    const after = clearSpot(placementFromZones(ZONES), 3, 1);
    expect(queueOf(ZONES, after).map((item) => item.id)).toContain("s1");
  });
});

describe("planDiff", () => {
  test("yangi qo'yilgan rasta `placed` ga tushadi", () => {
    const diff = planDiff({}, { s1: { x: 1, y: 2 } });
    expect(diff.placed).toEqual([{ stall_id: "s1", plan_x: 1, plan_y: 2 }]);
    expect(diff.cleared).toEqual([]);
  });

  test("⭐ O'ZGARMAGAN rasta farqga TUSHMAYDI", () => {
    /*
     * ⛔⛔ Bu tejamkorlik emas: har «Saqlash» butun chizmani yuborsa
     *     audit jurnaliga 1000 ta soxta «o'zgardi» yozuvi tushardi.
     */
    const same = { s1: { x: 1, y: 2 }, s2: { x: 3, y: 4 } };
    expect(planDiff(same, { ...same })).toEqual({ placed: [], cleared: [] });
  });

  test("ko'chirilgan rasta `placed` ga tushadi, `cleared` ga EMAS", () => {
    /*
     * ⛔ Ko'chirishni «o'chirish + qo'yish» deb yuborish serverda
     *    ikki `UPDATE` va auditda IKKI yozuv qoldirardi.
     */
    const diff = planDiff({ s1: { x: 1, y: 1 } }, { s1: { x: 9, y: 9 } });
    expect(diff.placed).toEqual([{ stall_id: "s1", plan_x: 9, plan_y: 9 }]);
    expect(diff.cleared).toEqual([]);
  });

  test("olib tashlangan rasta `cleared` ga tushadi", () => {
    expect(planDiff({ s1: { x: 1, y: 1 } }, {})).toEqual({
      placed: [],
      cleared: ["s1"],
    });
  });

  test("bir tanada — qo'yish VA o'chirish", () => {
    const diff = planDiff({ s1: { x: 1, y: 1 } }, { s2: { x: 2, y: 2 } });
    expect(diff.placed).toEqual([{ stall_id: "s2", plan_x: 2, plan_y: 2 }]);
    expect(diff.cleared).toEqual(["s1"]);
  });
});

describe("isEmptyDiff", () => {
  test("o'zgarishsiz — `true`, ya'ni «Saqlash» o'chiq turadi", () => {
    expect(isEmptyDiff({ placed: [], cleared: [] })).toBe(true);
  });

  test("faqat o'chirish ham O'ZGARISH", () => {
    /* ⛔ `placed.length === 0` bilan tekshirish o'chirishni yutardi. */
    expect(isEmptyDiff({ placed: [], cleared: ["s1"] })).toBe(false);
  });
});

describe("cellsBetween", () => {
  test("⭐ QATOR BO'YLAB — oradagi HAMMA katak, `from` KIRMAYDI", () => {
    /*
     * ⛔⛔ Bu 260820 da Chromeda o'lchangan NUQSONNING darvozasi: tez
     *     surishda brauzer 1, 3 va 10-ustunlarni bergan, oradagilarini
     *     UMUMAN bermagan. Natijada qatorda teshik qolib, navbat
     *     siljigani uchun keyingi rastalar ham noto'g'ri joyga tushardi.
     */
    expect(cellsBetween({ x: 0, y: 3 }, { x: 4, y: 3 })).toEqual([
      { x: 1, y: 3 },
      { x: 2, y: 3 },
      { x: 3, y: 3 },
      { x: 4, y: 3 },
    ]);
  });

  test("teskari yo'nalish ham to'ldiriladi", () => {
    expect(cellsBetween({ x: 3, y: 0 }, { x: 1, y: 0 })).toEqual([
      { x: 2, y: 0 },
      { x: 1, y: 0 },
    ]);
  });

  test("ustun bo'ylab", () => {
    expect(cellsBetween({ x: 2, y: 0 }, { x: 2, y: 2 })).toEqual([
      { x: 2, y: 1 },
      { x: 2, y: 2 },
    ]);
  });

  test("⛔ DIAGONAL TAXMIN QILINMAYDI — faqat oxirgi katak", () => {
    /*
     * Qiya surishda oraliqni to'ldirish odam CHIZMAGAN rastalarni
     * qo'yardi. «Qator chizish» har doim to'g'ri chiziq.
     */
    expect(cellsBetween({ x: 0, y: 0 }, { x: 3, y: 2 })).toEqual([
      { x: 3, y: 2 },
    ]);
  });

  test("bir joyda qolish — bo'sh yo'l", () => {
    expect(cellsBetween({ x: 1, y: 1 }, { x: 1, y: 1 })).toEqual([]);
  });
});

describe("placeSequence", () => {
  test("navbat kataklar bo'ylab ketma-ket to'kiladi", () => {
    const after = placeSequence({}, ["a", "b", "c"], [
      { x: 0, y: 0 },
      { x: 1, y: 0 },
      { x: 2, y: 0 },
    ]);
    expect(after).toEqual({
      a: { x: 0, y: 0 },
      b: { x: 1, y: 0 },
      c: { x: 2, y: 0 },
    });
  });

  test("⭐ BAND KATAK NAVBATNI SILJITMAYDI — u chetlab o'tiladi", () => {
    /*
     * ⛔⛔ Aks holda bitta band katak butun qatorni bir pog'ona surib
     *     yuborardi va odam buni faqat oxirida, hamma kod noto'g'ri
     *     joyda turganda ko'rardi.
     */
    const after = placeSequence({ x1: { x: 1, y: 0 } }, ["a", "b"], [
      { x: 0, y: 0 },
      { x: 1, y: 0 },
      { x: 2, y: 0 },
    ]);
    expect(after).toEqual({
      x1: { x: 1, y: 0 },
      a: { x: 0, y: 0 },
      b: { x: 2, y: 0 },
    });
  });

  test("navbat tugasa qolgan kataklar BO'SH qoladi", () => {
    const after = placeSequence({}, ["a"], [
      { x: 0, y: 0 },
      { x: 1, y: 0 },
    ]);
    expect(after).toEqual({ a: { x: 0, y: 0 } });
  });

  test("bo'sh navbat — chizma o'zgarmaydi", () => {
    const before = { a: { x: 0, y: 0 } };
    expect(placeSequence(before, [], [{ x: 5, y: 5 }])).toBe(before);
  });
});

describe("clearSequence", () => {
  test("yo'ldagi hamma rasta chizmadan chiqadi", () => {
    const before = {
      a: { x: 0, y: 0 },
      b: { x: 1, y: 0 },
      c: { x: 5, y: 5 },
    };
    expect(
      clearSequence(before, [
        { x: 0, y: 0 },
        { x: 1, y: 0 },
      ]),
    ).toEqual({ c: { x: 5, y: 5 } });
  });

  test("bo'sh kataklar yo'lda uchrasa — zararsiz", () => {
    const before = { a: { x: 2, y: 0 } };
    expect(
      clearSequence(before, [
        { x: 0, y: 0 },
        { x: 1, y: 0 },
      ]),
    ).toBe(before);
  });
});
