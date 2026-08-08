/**
 * W0-F3 — WILSON SCORE ORALIG'I (05-UI-SPEC §11.5).
 *
 * =============================================================================
 * RAD ETILGAN MUQOBIL VA UNING SABABI — SHU FAYLDA, `wilson.ts` DA EMAS.
 *
 *   Rad etilgan formula: normal-approximation oralig'i, ya'ni odatiy
 *   `p ± 1.96·√(p(1−p)/n)` — «Wald» oralig'i.
 *
 *   Nega rad etildi (05-RESEARCH §C.8.4): kichik `n` va chetdagi `p` da
 *   u ISHONCHSIZ. Ikkita xulqiy oqibati bor va IKKALASI HAM pastda
 *   O'LCHANADI, ya'ni almashtirish jimgina o'tolmaydi:
 *     1. `p = 0` yoki `p = 1` da uning kengligi AYNAN NOL bo'ladi —
 *        «aniqlik 100 %, ishonch oralig'i 100–100 %» degan yolg'on
 *        qat'iylik. Birinchi kunning kichik namunasida bu AYNAN yuz
 *        beradi;
 *     2. u nuqta bahoning ATROFIDA SIMMETRIK, ya'ni 0 dan kichik yoki
 *        1 dan katta chegara chiqaradi.
 *
 *   ⚠ NOM `wilson.ts` GA YOZILMAYDI (03-07 qoidasi): skanerlanadigan
 *     faylning izohida taqiqlangan token yozilsa, sodda darvoza o'zini
 *     o'zi qizartiradi. `wilson.ts` faqat IJOBIY shaklda yozilgan.
 * =============================================================================
 *
 * ⚠ FAYL KENGAYTMASI `.tsx` VA BU MAJBURIY (M-2): `vitest.config.ts` ning
 *   `include` naqshi `src/**\/*.test.tsx`; `.ts` fayl JIMGINA o'tkazib
 *   yuborilardi.
 *
 * ⚠ KUTILGAN QIYMATLAR QO'LDA HISOBLANGAN VA LITERAL YOZILGAN (§S-9).
 *   `wilsonInterval` ularni olish uchun HECH QAYERDA chaqirilmaydi.
 */
import { describe, expect, test } from "vitest";

import { MIN_SAMPLE_FOR_PERCENT, wilsonInterval } from "@/lib/wilson";

/**
 * Tolerans — AYNAN `1e-3`.
 *
 * ⚠ `toBeCloseTo(x, 3)` ATAYIN ISHLATILMAYDI: uning haqiqiy chegarasi
 *   `0,5·10⁻³`, ya'ni ikki barobar tor. Qo'lda yozilgan uch xonali
 *   literal (0,825) haqiqiy qiymatdan (0,825633) 6,3·10⁻⁴ uzoq, ya'ni
 *   `toBeCloseTo` bu qatorni YIQITARDI va keyingi ijrochi «literalni
 *   aniqroq yozib qo'yaman» deb o'lchovni yashirardi.
 */
const TOLERANCE = 1e-3;

function expectNear(actual: number | null, expected: number): void {
  expect(actual).not.toBeNull();
  expect(Math.abs((actual as number) - expected)).toBeLessThanOrEqual(
    TOLERANCE,
  );
}

describe("wilsonInterval — qo'lda hisoblangan nazorat", () => {
  test("⚠ `wilsonInterval(90, 100)` — literal 0,825 va 0,945", () => {
    /*
     * QO'LDA HISOB (z = 1,96; z² = 3,8416):
     *   maxraj = 1 + z²/n = 1 + 0,038416                  = 1,038416
     *   markaz = (0,9 + 0,019208) / 1,038416              = 0,885202
     *   ildiz  = √(0,9·0,1/100 + 3,8416/40000)
     *          = √(0,0009 + 0,00009604) = √0,00099604     = 0,0315601
     *   yarim  = 1,96 · 0,0315601 / 1,038416              = 0,0595694
     *   quyi   = 0,885202 − 0,059569                      = 0,825633
     *   yuqori = 0,885202 + 0,059569                      = 0,944771
     */
    const result = wilsonInterval(90, 100);

    expectNear(result.lower, 0.825);
    expectNear(result.upper, 0.945);
  });

  test("⚠ `point` — KUZATILGAN ulush, oraliqning O'RTASI EMAS", () => {
    /*
     * ENG MUHIM ASSERT VA U IKKI ISHNI BIRDAN QILADI.
     *
     * (a) Sarlavhadagi raqam O'LCHANGAN qiymat bo'lishi SHART: 90/100 =
     *     0,9. Oraliqning markazi (0,885202) — QISQARTIRILGAN baho, va
     *     uni ekranga chiqarish direktorga boshqa raqam ko'rsatardi.
     *
     * (b) Oraliq nuqta bahoning atrofida SIMMETRIK EMAS — bu tanlangan
     *     formulaning belgisi. Rad etilgan muqobilda o'rta AYNAN 0,9 ga
     *     teng bo'lardi (0,9 ± 0,0588), ya'ni bu qator uni BEVOSITA
     *     ajratadi.
     */
    const result = wilsonInterval(90, 100);

    expectNear(result.point, 0.9);

    const midpoint = ((result.lower as number) + (result.upper as number)) / 2;
    expectNear(midpoint, 0.885);
    expect(Math.abs(midpoint - 0.9)).toBeGreaterThan(0.01);
  });

  test("30 tadan 26 tasi — kunlik byudjet o'lchamidagi namuna (D-13)", () => {
    /*
     * D-13: kunlik ko'r audit byudjeti 30 band. Bir kunlik namunaning
     * oralig'i QANCHALIK KENG ekanini shu qator ko'rsatadi: 0,70–0,95,
     * ya'ni ~±12 f.p. Oylik ±2–3 f.p. uchun ~900 javob kerak.
     *   maxraj = 1 + 3,8416/30                            = 1,128053
     *   markaz = (0,866667 + 0,064027) / 1,128053         = 0,825044
     *   yarim  = 0,121861
     */
    const result = wilsonInterval(26, 30);

    expectNear(result.lower, 0.703);
    expectNear(result.upper, 0.947);
  });
});

describe("chetki holatlar — `p = 0` va `p = 1`", () => {
  test("⚠ `p = 0` — oraliq [0,1] ichida va KENGLIKKA EGA", () => {
    /*
     * Rad etilgan muqobil bu yerda AYNAN NOL kenglik berardi ([0, 0]) —
     * «bo'sh deb xato bo'lish ehtimoli 0 %, ishonch oralig'i 0–0 %».
     * Nazoratchi atigi 10 ta javob bergan bo'lsa, bunday da'voga asos
     * YO'Q.
     *
     * Qo'lda: maxraj = 1,38416; markaz = 0,19208/1,38416 = 0,138770;
     *         yarim  = 1,96·√(0 + 3,8416/400)/1,38416    = 0,138770.
     */
    const result = wilsonInterval(0, 10);

    expect(result.point).toBe(0);
    expect(result.lower).toBe(0);
    expectNear(result.upper, 0.278);
    expect(result.upper as number).toBeGreaterThan(result.lower as number);
  });

  test("⚠ `p = 1` — oraliq [0,1] ichida va KENGLIKKA EGA", () => {
    // Qo'lda: markaz = 1,19208/1,38416 = 0,861230; yarim = 0,138770.
    const result = wilsonInterval(10, 10);

    expect(result.point).toBe(1);
    expectNear(result.lower, 0.722);
    expect(result.upper).toBe(1);
    expect(result.upper as number).toBeGreaterThan(result.lower as number);
  });

  test("chegaralar HECH QACHON [0,1] dan chiqmaydi va kenglik nol EMAS", () => {
    /*
     * Sanab chiqilgan domen: n = 1..40 ning har bir `s` qiymati. Bu
     * «omadli fixture» yo'lini yopadi — chetki holat tanlab olinmaydi,
     * hammasi tekshiriladi.
     */
    for (let n = 1; n <= 40; n += 1) {
      for (let s = 0; s <= n; s += 1) {
        const { lower, upper } = wilsonInterval(s, n);

        if (lower === null || upper === null) {
          throw new Error(`n=${n} s=${s}: kutilmagan null`);
        }
        if (lower < 0 || upper > 1 || upper <= lower) {
          throw new Error(`n=${n} s=${s}: oraliq [${lower}, ${upper}] yaroqsiz`);
        }
      }
    }
  });
});

describe("chaqiruvchi xatolari", () => {
  test("⚠ `n = 0` — uchala maydon `null` (throw EMAS, 0 ham EMAS)", () => {
    /*
     * «Hali namuna yo'q» — bu XATO EMAS, u birinchi kunning normal
     * holati. `0` qaytarish «aniqlik nolga teng» degan yolg'on
     * ko'rsatkich yasardi; `throw` esa hisobot sahifasini yiqitardi.
     *
     * ⚠ TARTIB AHAMIYATLI: `n === 0` tekshiruvi `successes > n` dan
     *   OLDIN turadi. Namuna bo'sh bo'lganda `successes` ning qiymati
     *   umuman ma'noga ega emas, ya'ni uni xato deb e'lon qilish
     *   chaqiruvchini mavjud bo'lmagan nosozlikni tuzatishga yuborardi.
     */
    expect(wilsonInterval(0, 0)).toEqual({
      point: null,
      lower: null,
      upper: null,
    });
    expect(wilsonInterval(5, 0)).toEqual({
      point: null,
      lower: null,
      upper: null,
    });
  });

  test("⚠ `successes > n` — `RangeError` (jimgina to'g'rilanmaydi)", () => {
    /*
     * Bu chaqiruvchining xatosi va u JIMGINA to'g'rilanmaydi: `s` ni `n`
     * ga qisish «aniqlik 100 %» degan hisobot chiqarardi, ya'ni nosozlik
     * eng ishonarli ko'rinishda yashirinardi.
     */
    expect(() => wilsonInterval(11, 10)).toThrow(RangeError);
    expect(() => wilsonInterval(1, -1)).toThrow(RangeError);
    expect(() => wilsonInterval(-1, 10)).toThrow(RangeError);
  });

  test("butun bo'lmagan yoki chekli bo'lmagan kirish — `RangeError`", () => {
    expect(() => wilsonInterval(1.5, 10)).toThrow(RangeError);
    expect(() => wilsonInterval(1, 10.5)).toThrow(RangeError);
    expect(() => wilsonInterval(Number.NaN, 10)).toThrow(RangeError);
    expect(() => wilsonInterval(1, Number.POSITIVE_INFINITY)).toThrow(
      RangeError,
    );
  });
});

describe("MIN_SAMPLE_FOR_PERCENT (O-05)", () => {
  test("qiymati AYNAN 20 va u eksport qilingan", () => {
    /*
     * `n < 20` da BIRORTA FOIZ CHIZILMAYDI (05-UI-SPEC §8.4 O-4, §11.5).
     * Chegara shu modulda yashaydi, chunki uni tanlash sababi ham shu
     * yerda: oraliq kengligi «hali o'lchanmadi» ni O'ZI aytadi, lekin
     * direktor birinchi kunning oxirida NIMADIR ko'rishi kerak.
     */
    expect(MIN_SAMPLE_FOR_PERCENT).toBe(20);
  });

  test("chegaradagi namunaning oralig'i hamon ±13 f.p. dan KENG", () => {
    /*
     * Chegara «endi raqam ISHONCHLI» degani EMAS — u faqat «endi raqam
     * KO'RSATILADI» degani. Bu qator farqni o'lchab qo'yadi, ya'ni
     * kelajakda kimdir 20 ni «yetarli namuna» deb o'qimaydi.
     *
     * n = 20, s = 18 → qo'lda:
     *   maxraj = 1 + 3,8416/20                       = 1,19208
     *   markaz = (0,9 + 3,8416/40) / 1,19208
     *          = (0,9 + 0,09604) / 1,19208           = 0,835548
     *   yarim  = 1,96·√(0,9·0,1/20 + 3,8416/1600) / 1,19208
     *          = 1,96·√(0,0045 + 0,0024010) / 1,19208
     *          = 1,96·0,0830723 / 1,19208            = 0,136586
     *   quyi   = 0,698962      yuqori = 0,972134
     */
    const result = wilsonInterval(18, MIN_SAMPLE_FOR_PERCENT);

    expectNear(result.lower, 0.699);
    expectNear(result.upper, 0.972);
    expect((result.upper as number) - (result.lower as number)).toBeGreaterThan(
      0.26,
    );
  });
});
