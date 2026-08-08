/*
 * =============================================================================
 * NISBAT UCHUN ISHONCH ORALIG'I — WILSON SCORE (05-UI-SPEC §11.5).
 *
 * Wilson score oralig'i ishlatiladi, chunki u KICHIK `n` va CHETDAGI `p`
 * da ham to'g'ri qoplama beradi (05-RESEARCH §C.8.4). Bu loyihada ikkala
 * shart ham normal holat, istisno emas:
 *
 *   - `n` kichik: ko'r audit byudjeti kuniga 30 band (D-13), ya'ni
 *     birinchi hisobot 20–30 javob ustida chiziladi;
 *   - `p` chetda: kutilgan aniqlik 0,9 dan yuqori, ya'ni nuqta baho
 *     doim 1 ga yaqin turadi.
 *
 * Oraliq nuqta bahoning atrofida SIMMETRIK EMAS va bu xususiyat — uning
 * butun foydasi: chegaralar [0, 1] dan chiqmaydi va `p = 0` yoki `p = 1`
 * da ham oraliq KENGLIKKA EGA bo'lib qoladi. «Aniqlik 100 %, oraliq
 * 100–100 %» degan yolg'on qat'iylik shu bilan struktura darajasida
 * imkonsiz bo'ladi.
 *
 * ⚠ RAD ETILGAN MUQOBILNING NOMI VA SABABI SHU FAYLDA EMAS —
 *   `wilson.test.tsx` ning modul docstringida (03-07 qoidasi).
 *
 * -----------------------------------------------------------------------
 * NEGA STATISTIKA KUTUBXONASI QO'SHILMAYDI
 * -----------------------------------------------------------------------
 * Kerak bo'lgan narsa — BITTA formula, o'n qatorlik arifmetika. Paket
 * qo'shish uchta narxni olib kelardi: bundl hajmi, yangi tranzitiv
 * bog'liqlik daraxti va yangilanish yuki — hech biri bitta formulaga
 * arzimaydi. Formulaning to'g'riligi paketning obro'si bilan emas,
 * `wilson.test.tsx` dagi QO'LDA HISOBLANGAN nazorat qiymatlari bilan
 * ta'minlanadi.
 * =============================================================================
 */

/**
 * Nisbat va uning ishonch oralig'i.
 *
 * Namuna bo'sh bo'lganda uchala maydon ham `null` — «hali o'lchanmadi»
 * va «nolga teng» bir xil ko'rinmasligi uchun.
 */
export type ProportionInterval = {
  /** Kuzatilgan ulush (`successes / n`), oraliqning markazi EMAS. */
  point: number | null;
  /** Quyi chegara, [0, 1] ichida. */
  lower: number | null;
  /** Yuqori chegara, [0, 1] ichida. */
  upper: number | null;
};

/**
 * 95 % ishonch darajasiga mos standart normal kvantil.
 *
 * Sozlama sifatida ochiq qoldirilgan (masalan 90 % uchun 1,645), lekin
 * hisobotda BITTA daraja ishlatiladi: ikki xil kenglikdagi oraliqni bir
 * jadvalda ko'rsatish ularni solishtirib bo'lmaydigan qilardi.
 */
const Z_95 = 1.96;

/**
 * Foiz UMUMAN chizilmaydigan quyi chegara (05-UI-SPEC §8.4 O-4, §11.5).
 *
 * ⚠ Chegara «endi raqam ISHONCHLI» degani EMAS — u «endi raqam
 *   KO'RSATILADI» degani. `n = 20` da oraliq hamon ~±13 f.p. keng va
 *   buni `wilson.test.tsx` o'lchab qo'ygan.
 *
 * Nega umuman chegara bor: `n < 20` da oraliq shu qadar kengki, foiz
 * ma'lumot emas, SHOVQIN uzatadi — «94 %» ko'rgan direktor uni o'lchov
 * deb o'qirdi. Nega aynan 20: birinchi kunning oxirida (30 band/kun)
 * direktor NIMADIR ko'rishi kerak, aks holda «tizim ishlamayapti»
 * degan xulosa chiqarardi.
 */
export const MIN_SAMPLE_FOR_PERCENT = 20;

function assertCount(value: number, name: string): void {
  if (!Number.isInteger(value) || value < 0) {
    throw new RangeError(
      `wilson: \`${name}\` manfiy bo'lmagan BUTUN son bo'lishi SHART (olindi: ${value})`,
    );
  }
}

/**
 * Wilson score oralig'i.
 *
 * @param successes — «muvaffaqiyat» sanog'i (masalan to'g'ri verdiktlar)
 * @param n — namuna hajmi
 * @param z — standart normal kvantil; standart 95 %
 *
 * ⚠ TEKSHIRUVLAR TARTIBI KONTRAKTNING BIR QISMI:
 *
 *   1. shakl (butun, manfiy emas)  -> `RangeError`
 *   2. `n === 0`                   -> uchala maydon `null`
 *   3. `successes > n`             -> `RangeError`
 *
 *   2-qadam 3-dan OLDIN turadi va bu ataylab: namuna bo'sh bo'lganda
 *   `successes` ning qiymati umuman ma'noga ega emas, ya'ni uni xato
 *   deb e'lon qilish chaqiruvchini mavjud bo'lmagan nosozlikni
 *   tuzatishga yuborardi.
 *
 *   3-qadam esa JIMGINA TO'G'RILANMAYDI: `successes` ni `n` ga qisish
 *   «aniqlik 100 %» degan hisobot chiqarardi — nosozlik eng ishonarli
 *   ko'rinishda yashirinardi.
 */
export function wilsonInterval(
  successes: number,
  n: number,
  z: number = Z_95,
): ProportionInterval {
  assertCount(successes, "successes");
  assertCount(n, "n");

  if (n === 0) {
    return { point: null, lower: null, upper: null };
  }

  if (successes > n) {
    throw new RangeError(
      `wilson: \`successes\` (${successes}) \`n\` (${n}) dan katta bo'lolmaydi`,
    );
  }

  if (!Number.isFinite(z) || z <= 0) {
    throw new RangeError(`wilson: \`z\` musbat va chekli bo'lishi SHART (${z})`);
  }

  const p = successes / n;
  const z2 = z * z;
  const denominator = 1 + z2 / n;

  const center = (p + z2 / (2 * n)) / denominator;
  const halfWidth =
    (z * Math.sqrt((p * (1 - p)) / n + z2 / (4 * n * n))) / denominator;

  /*
   * Qisish suzuvchi nuqta shovqini uchun: formula matematik jihatdan
   * [0, 1] dan chiqmaydi, lekin `p = 0` da `center - halfWidth` amalda
   * -1e-17 beradi va u ekranda «-0,0 %» bo'lib ko'rinardi.
   */
  return {
    point: p,
    lower: Math.max(0, center - halfWidth),
    upper: Math.min(1, center + halfWidth),
  };
}
