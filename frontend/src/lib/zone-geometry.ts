/*
 * =============================================================================
 * KAMERA ZONALARINING SOF GEOMETRIYASI — DOM YO'Q, React YO'Q, `window` YO'Q.
 *
 * Koordinatalar NORMALANGAN (0..1) va shu holda saqlanadi (D-07): kamera
 * qayta kashf qilinganda yoki ruxsati o'zgarganda poligonlar omon qoladi.
 * Piksellarga o'tish faqat render chegarasida, `denormalize` bilan bo'ladi.
 *
 * -----------------------------------------------------------------------
 * QAROR 1 — NEGA GEOMETRIYA RENDER QATLAMIDA YASHAMAYDI (D-05)
 * -----------------------------------------------------------------------
 * Muharrir SVG bilan quriladi, canvas kutubxonasi bilan emas. Sabab
 * O'LCHANGAN, did emas: 2-faza canvasni `stall-map.tsx:22-37` da rad etgan
 * (1000 element memo bilan ~4 ms), va hal qiluvchi omil TEST — `vitest` +
 * `jsdom` da canvas YO'Q, Playwright esa loyihada yo'q va 8-fazaga
 * qoldirilgan. Ya'ni canvas'ni sinaydigan ikkinchi yo'l ham yo'q edi.
 *
 * ⚠ CHIQISH YO'LI OCHIQ va uning TETIGI O'LCHOV:
 *     50+ poligonli kamerada tepani sudrash `pointermove` ishlovchisi
 *     >16 ms olsa, render qatlami Konva'ga almashtiriladi.
 *   Almashish FAQAT `zone-canvas.tsx` ni o'zgartiradi, chunki geometriya
 *   shu yerda — sof funksiyalarda — yashaydi.
 *   ⚠ Bu UAT BANDI, DARVOZA EMAS: qiymat brauzer va qurilmaga bog'liq,
 *   ya'ni uni CI'da o'lchash yolg'on signal berardi (05-UI-SPEC §6.1).
 *
 * -----------------------------------------------------------------------
 * QAROR 2 — TEST NEGA `scripts/*.test.mjs` DA EMAS (M-3 / M-2)
 * -----------------------------------------------------------------------
 * 05-UI-SPEC §6.2 va 05-RESEARCH bu modulning juftini
 * `frontend/scripts/zone-geometry.test.mjs` deb taklif qiladi. U
 * BAJARILMAYDI: `node --test` TypeScript'ni import qila olmaydi. Shuning
 * uchun test `vitest` ostida va kengaytmasi AYNAN `.test.tsx` (M-2) —
 * `vitest.config.ts` ning `include` naqshi `src/**\/*.test.tsx`, ya'ni
 * `.ts` test fayli JIMGINA o'tkazib yuborilardi va «hammasi yashil»
 * hisoboti yolg'on bo'lardi (3-fazada o'lchangan holat).
 *
 * -----------------------------------------------------------------------
 * QAROR 3 — `isSelfIntersecting` SAQLASH DARVOZASI (T-05-11)
 * -----------------------------------------------------------------------
 * O'zi bilan kesishgan poligon zona kutubxonasida (`supervision`,
 * `cv2.pointPolygonTest` ustida) ANIQLANMAGAN natija beradi — ya'ni
 * JIMGINA NOTO'G'RI HISOB: xato xabari yo'q, poligon ekranda ko'rinadi,
 * lekin bandlik boshqa maydondan o'lchanadi va u bevosita billing'ga
 * o'tadi.
 * ⚠ BU YERDAGI TEKSHIRUV — QULAYLIK, XAVFSIZLIK CHEGARASI EMAS. Ishonch
 *   manbai SERVERDA (05-06). Klient tekshiruvi adminga xatoni darhol
 *   ko'rsatadi, lekin uni chetlab o'tish mumkin.
 *
 * -----------------------------------------------------------------------
 * HAVOLA / RAD ETISH KONTRAKTI
 * -----------------------------------------------------------------------
 * ⚠ HAMMA AMAL IMMUTABLE: kirish massivi HECH QACHON o'zgartirilmaydi.
 *   Undo/redo steki NUSXA emas, HAVOLA ro'yxati (05-UI-SPEC §6.2).
 *
 *   BAJARILGAN amal  -> YANGI massiv;
 *   RAD ETILGAN amal -> AYNAN O'SHA havola.
 *
 *   Ikkinchisi ataylab: rad etilgan amal yangi massiv qaytarsa, undo
 *   stekiga bir xil holatning ikkinchi nusxasi tushardi va `Ctrl+Z`
 *   «hech nima qilmaydigan» qadamni bosib o'tishga majbur qilardi.
 *   Chaqiruvchi buni `Object.is(prev, next)` bilan bir bosqichda ajratadi.
 * =============================================================================
 */

/** Normalangan nuqta — ikkala komponent ham 0..1. */
export type Pt = readonly [number, number];

/** Poligon — normalangan tepalarning tartiblangan ro'yxati. */
export type Poly = readonly Pt[];

/* -------------------------------------------------------------------------- */
/* Chegaralar (05-UI-SPEC §6.5)                                               */
/*                                                                            */
/* ⚠ HAR BIRINING SERVERDA JUFTI BOR va SERVERDAGISI ISHONCH MANBAI:          */
/*   `MIN_VERTICES`          -> DB `CHECK (jsonb_array_length(polygon) >= 3)`  */
/*   `MAX_VERTICES_PER_ZONE` -> core-api `Settings` (05-06)                    */
/*   `MAX_ZONES_PER_CAMERA`  -> core-api `Settings` (05-06)                    */
/*   Bu yerdagi qiymatlar QULAYLIK uchun: admin chegaraga urilganini darhol    */
/*   ko'radi. Ular XAVFSIZLIK chegarasi EMAS (02-UI-SPEC §12.3 merosi).        */
/* -------------------------------------------------------------------------- */

/** Poligonning ta'rifi — undan kam tepa yuza hosil qilmaydi. */
export const MIN_VERTICES = 3;

/**
 * Rasta amalda to'rtburchak; 12 — saxiy zaxira.
 *
 * Undan yuqorisi `jsonb` hajmini va har `pointermove` ning narxini
 * o'stiradi, aniqlik esa QO'SHMAYDI (T-05-12).
 */
export const MAX_VERTICES_PER_ZONE = 12;

/**
 * Kutilgan qiymat 10–40; 60 — zaxira.
 *
 * ⚠ U D-05 ning o'lchov tetigidan (50+ poligon) YUQORI, ya'ni chegaraga
 *   yaqinlashgan kamera Konva savolini ham ko'taradi (05-UI-SPEC §6.5).
 */
export const MAX_ZONES_PER_CAMERA = 60;

/** Undo steki sessiyaga bog'liq va saqlanmaydi; immutable poligonlar arzon. */
export const UNDO_DEPTH = 50;

/**
 * Nolga tenglik chegarasi orientatsiya testida.
 *
 * Koordinatalar 0..1 da, ya'ni tipik kesma-kesishuv determinanti 1e-3
 * atrofida. 1e-12 — «haqiqiy nol» va «suzuvchi nuqta shovqini» orasidagi
 * xavfsiz oraliq: undan kichigi kollinear tepalarni o'tkazib yuborardi,
 * kattasi esa yonma-yon rastalarni kesishgan deb e'lon qilardi.
 */
const EPS = 1e-12;

/* -------------------------------------------------------------------------- */
/* Ichki yordamchilar                                                         */
/* -------------------------------------------------------------------------- */

function clamp01(value: number): number {
  if (Number.isNaN(value)) {
    throw new RangeError("zone-geometry: koordinata NaN");
  }
  return Math.min(1, Math.max(0, value));
}

function clampPt(pt: Pt): Pt {
  return [clamp01(pt[0]), clamp01(pt[1])];
}

function assertPositiveExtent(w: number, h: number): void {
  if (!Number.isFinite(w) || !Number.isFinite(h) || w <= 0 || h <= 0) {
    throw new RangeError(
      `zone-geometry: kadr o'lchami musbat bo'lishi SHART (olindi: ${w}x${h}). ` +
        "Nol kenglik jimgina Infinity koordinata yasab, poligonni butunlay yo'qotardi.",
    );
  }
}

function isVertexIndex(poly: Poly, index: number): boolean {
  return Number.isInteger(index) && index >= 0 && index < poly.length;
}

/** `o -> a` va `o -> b` vektorlarining ko'paytmasi (ishorasi burilish tomoni). */
function cross(o: Pt, a: Pt, b: Pt): number {
  return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
}

/** Burilish ishorasi: -1, 0 yoki 1 (`EPS` bilan). */
function orientation(o: Pt, a: Pt, b: Pt): number {
  const value = cross(o, a, b);
  if (Math.abs(value) < EPS) {
    return 0;
  }
  return value > 0 ? 1 : -1;
}

/** `q` kollinear `p`–`r` kesmasining ICHIDA (yoki uchida) turibdimi. */
function onSegment(p: Pt, q: Pt, r: Pt): boolean {
  return (
    q[0] <= Math.max(p[0], r[0]) + EPS &&
    q[0] >= Math.min(p[0], r[0]) - EPS &&
    q[1] <= Math.max(p[1], r[1]) + EPS &&
    q[1] >= Math.min(p[1], r[1]) - EPS
  );
}

/**
 * Ikki kesma kesishadimi — TEGIB O'TISH HAM KESISHISH deb sanaladi.
 *
 * ⚠ Bu faqat QO'SHNI BO'LMAGAN qirralarga qo'llanadi. Qo'shni qirralar
 *   ta'rifi bo'yicha bitta tepani baham ko'radi, ya'ni bu yerda ular
 *   HAR DOIM «kesishgan» chiqardi.
 */
function segmentsIntersect(p1: Pt, q1: Pt, p2: Pt, q2: Pt): boolean {
  const o1 = orientation(p1, q1, p2);
  const o2 = orientation(p1, q1, q2);
  const o3 = orientation(p2, q2, p1);
  const o4 = orientation(p2, q2, q1);

  // Umumiy holat — haqiqiy kesib o'tish.
  if (o1 !== o2 && o3 !== o4) {
    return true;
  }

  // Kollinear holatlar: tepa boshqa qirraning USTIDA turibdi.
  if (o1 === 0 && onSegment(p1, p2, q1)) return true;
  if (o2 === 0 && onSegment(p1, q2, q1)) return true;
  if (o3 === 0 && onSegment(p2, p1, q2)) return true;
  if (o4 === 0 && onSegment(p2, q1, q2)) return true;

  return false;
}

/**
 * Bitta tepani baham ko'radigan ikki qirra USTMA-UST TUSHGANMI.
 *
 * `shared` — umumiy tepa, `a` va `b` — qolgan uchlari. Agar uchalasi
 * kollinear bo'lsa VA `a` bilan `b` `shared` dan BIR TOMONGA ketsa,
 * ikkinchi qirra birinchisining ustidan qaytib o'tadi («nina»). Bu
 * poligonni nol kenglikli tilim bilan qoldiradi va zona kutubxonasi
 * uni ham aniqlanmagan holda qayta ishlaydi.
 */
function isSpike(shared: Pt, a: Pt, b: Pt): boolean {
  if (orientation(shared, a, b) !== 0) {
    return false;
  }
  const dot =
    (a[0] - shared[0]) * (b[0] - shared[0]) +
    (a[1] - shared[1]) * (b[1] - shared[1]);
  return dot > EPS;
}

/* -------------------------------------------------------------------------- */
/* 1–2. Koordinata konversiyasi                                               */
/* -------------------------------------------------------------------------- */

/**
 * Piksel → 0..1.
 *
 * Qisish YO'Q va bu ataylab: `normalize` — SOF konversiya. Kadr
 * tashqarisidagi nuqtani qisish `moveVertex` ning ishi, chunki faqat
 * o'sha yerda «bu tepa poligonga kiryapti» degan ma'no bor.
 */
export function normalize(px: Pt, w: number, h: number): Pt {
  assertPositiveExtent(w, h);
  return [px[0] / w, px[1] / h];
}

/**
 * 0..1 → piksel, BUTUN songa yaxlitlangan.
 *
 * ⚠ YAXLITLASH — AYLANMA YO'QOTISHSIZLIGINING SHARTI, bezak emas:
 *   `denormalize(normalize(p, w, h), w, h) === p` faqat shunda butun
 *   pikselda bajariladi. Yaxlitlashsiz 437/1279*1279 = 436.99999999999994
 *   bo'lardi, ya'ni poligon HAR SAFAR ochilib saqlanganda joyidan bir oz
 *   siljib, bir necha tahrirdan keyin rastadan «sirg'alib» chiqardi —
 *   hech qanday xato xabarisiz.
 *
 * ⚠ Zoom bunga bog'liq EMAS: masshtab SVG `viewBox` transformida, ya'ni
 *   yaxlitlash render aniqligini kamaytirmaydi.
 */
export function denormalize(pt: Pt, w: number, h: number): Pt {
  assertPositiveExtent(w, h);
  return [Math.round(pt[0] * w), Math.round(pt[1] * h)];
}

/* -------------------------------------------------------------------------- */
/* 3–5. Tepalar ustida amallar                                                */
/* -------------------------------------------------------------------------- */

/**
 * `index` dan KEYIN yangi tepa qo'yadi.
 *
 * `MAX_VERTICES_PER_ZONE` ga yetgan poligon — RAD ETILADI (T-05-12).
 */
export function addVertex(poly: Poly, index: number, pt: Pt): Poly {
  if (!isVertexIndex(poly, index) || poly.length >= MAX_VERTICES_PER_ZONE) {
    return poly;
  }
  const next = poly.slice();
  next.splice(index + 1, 0, clampPt(pt));
  return next;
}

/**
 * Tepani ko'chiradi, 0..1 ga QISIB.
 *
 * Kadr tashqarisidagi tepa `cv2.pointPolygonTest` da aniqlanmagan natija
 * beradi (05-RESEARCH §A.5) — ya'ni bandlik qarori tushuntirib
 * bo'lmaydigan holga kelardi.
 */
export function moveVertex(poly: Poly, index: number, pt: Pt): Poly {
  if (!isVertexIndex(poly, index)) {
    return poly;
  }
  const next = poly.slice();
  next[index] = clampPt(pt);
  return next;
}

/**
 * Tepani o'chiradi. `MIN_VERTICES` da O'ZGARISHSIZ qaytaradi — `throw` EMAS.
 *
 * ⚠ Funksiya himoyaning IKKINCHI qatlami, birinchisi emas: UI tugmani
 *   `aria-disabled` bilan to'sadi (05-UI-SPEC §6.5). Bu yerda `throw`
 *   bo'lsa, `Delete` klaviatura yorlig'i butun muharrirni yiqitardi.
 */
export function deleteVertex(poly: Poly, index: number): Poly {
  if (!isVertexIndex(poly, index) || poly.length <= MIN_VERTICES) {
    return poly;
  }
  const next = poly.slice();
  next.splice(index, 1);
  return next;
}

/**
 * `edgeIndex` qirrasining AYNAN o'rtasiga tepa qo'yadi.
 *
 * Qirra `edgeIndex` tepasidan keyingisiga boradi; oxirgi qirra yopiluvchi,
 * ya'ni oxirgi tepadan birinchisiga.
 */
export function insertMidpoint(poly: Poly, edgeIndex: number): Poly {
  if (!isVertexIndex(poly, edgeIndex) || poly.length >= MAX_VERTICES_PER_ZONE) {
    return poly;
  }
  const a = poly[edgeIndex];
  const b = poly[(edgeIndex + 1) % poly.length];
  const next = poly.slice();
  next.splice(edgeIndex + 1, 0, [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2]);
  return next;
}

/**
 * Butun poligonni siljitadi (nusxalash va sudrash uchun).
 *
 * ⚠ QISILADIGAN NARSA — TEPA EMAS, SILJISH MIQDORI. Har tepani alohida
 *   `clamp(0,1)` qilish poligonni JIMGINA EZARDI: chegaraga urilgan
 *   tomoni to'planib, qarama-qarshisi joyida qolardi va zona endi
 *   rastani emas, boshqa shaklni o'lchardi. Shakl saqlanishi — bu
 *   funksiyaning butun mazmuni.
 */
export function translate(poly: Poly, dx: number, dy: number): Poly {
  if (poly.length === 0) {
    return poly;
  }

  let minX = Number.POSITIVE_INFINITY;
  let maxX = Number.NEGATIVE_INFINITY;
  let minY = Number.POSITIVE_INFINITY;
  let maxY = Number.NEGATIVE_INFINITY;

  for (const [x, y] of poly) {
    minX = Math.min(minX, x);
    maxX = Math.max(maxX, x);
    minY = Math.min(minY, y);
    maxY = Math.max(maxY, y);
  }

  // Poligon 0..1 dan kengroq bo'lsa (buzilgan kirish) siljitishga joy yo'q.
  const cdx = maxX - minX > 1 ? 0 : Math.min(1 - maxX, Math.max(-minX, dx));
  const cdy = maxY - minY > 1 ? 0 : Math.min(1 - maxY, Math.max(-minY, dy));

  if (cdx === 0 && cdy === 0) {
    return poly;
  }

  return poly.map(([x, y]): Pt => [clamp01(x + cdx), clamp01(y + cdy)]);
}

/* -------------------------------------------------------------------------- */
/* 6. Saqlash darvozasi                                                       */
/* -------------------------------------------------------------------------- */

/**
 * Poligon o'zi bilan kesishadimi (QAROR 3 — saqlash darvozasi).
 *
 * Qo'shni bo'lmagan har qirra jufti tekshiriladi; qo'shni juftlar esa
 * faqat «nina» (ustma-ust tushish) uchun. Tegib o'tish ham kesishish deb
 * sanaladi: qirraning ustida turgan tepa ham zona kutubxonasi uchun
 * aniqlanmagan holat.
 */
export function isSelfIntersecting(poly: Poly): boolean {
  const n = poly.length;

  // Uchdan kam tepa poligon EMAS — bu holatni `MIN_VERTICES` hal qiladi
  // va uni bu yerda «kesishgan» deb e'lon qilish xato sababini yashirardi.
  if (n < MIN_VERTICES) {
    return false;
  }

  for (let i = 0; i < n; i += 1) {
    const a1 = poly[i];
    const a2 = poly[(i + 1) % n];

    for (let j = i + 1; j < n; j += 1) {
      const b1 = poly[j];
      const b2 = poly[(j + 1) % n];

      const adjacent = j === i + 1 || (i === 0 && j === n - 1);

      if (adjacent) {
        // Umumiy tepa: `i`+1 juftida `a2`, yopiluvchi juftda `a1`.
        const shared = j === i + 1 ? a2 : a1;
        const other1 = j === i + 1 ? a1 : a2;
        const other2 = j === i + 1 ? b2 : b1;

        if (isSpike(shared, other1, other2)) {
          return true;
        }
        continue;
      }

      if (segmentsIntersect(a1, a2, b1, b2)) {
        return true;
      }
    }
  }

  return false;
}

/* -------------------------------------------------------------------------- */
/* 7–8. O'lchovlar                                                            */
/* -------------------------------------------------------------------------- */

/**
 * Poligon yuzasi 0..1 kvadratida (shnurbog'ich formulasi).
 *
 * Modul qiymat: yuza aylanish yo'nalishidan MUSTAQIL — admin poligonni
 * qaysi tomonga chizgani hisobga aloqador emas.
 */
export function polygonArea(poly: Poly): number {
  const n = poly.length;
  if (n < MIN_VERTICES) {
    return 0;
  }

  let twiceArea = 0;
  for (let i = 0; i < n; i += 1) {
    const [x1, y1] = poly[i];
    const [x2, y2] = poly[(i + 1) % n];
    twiceArea += x1 * y2 - x2 * y1;
  }

  return Math.abs(twiceArea) / 2;
}

/**
 * Poligonning markazi — yorliq qo'yiladigan joy.
 *
 * ⚠ YUZA BO'YICHA markaz, TEPALAR O'RTACHASI EMAS. Farq real: qirraga
 *   qo'shimcha tepa qo'yilsa (`insertMidpoint` buni tez-tez qiladi),
 *   tepalar o'rtachasi o'sha qirra tomon siljib, yorliq poligonning
 *   chetiga chiqib ketardi.
 *
 * Nol yuzali (kollinear) poligonda formula 0/0 berardi, shuning uchun
 * unda tepalar o'rtachasiga qaytiladi.
 */
export function centroid(poly: Poly): Pt {
  const n = poly.length;

  if (n === 0) {
    return [0, 0];
  }

  const meanOfVertices = (): Pt => {
    let sx = 0;
    let sy = 0;
    for (const [x, y] of poly) {
      sx += x;
      sy += y;
    }
    return [sx / n, sy / n];
  };

  if (n < MIN_VERTICES) {
    return meanOfVertices();
  }

  let twiceArea = 0;
  let cx = 0;
  let cy = 0;

  for (let i = 0; i < n; i += 1) {
    const [x1, y1] = poly[i];
    const [x2, y2] = poly[(i + 1) % n];
    const step = x1 * y2 - x2 * y1;
    twiceArea += step;
    cx += (x1 + x2) * step;
    cy += (y1 + y2) * step;
  }

  if (Math.abs(twiceArea) < EPS) {
    return meanOfVertices();
  }

  return [cx / (3 * twiceArea), cy / (3 * twiceArea)];
}

/* -------------------------------------------------------------------------- */
/* 9. Qator yordamchisi (05-UI-SPEC §6.7)                                     */
/* -------------------------------------------------------------------------- */

/**
 * `first` va `last` orasiga AYNAN `n` ta oraliq poligon yasaydi.
 *
 * Bu 300–1000 rasta uchun chizish vaqtini ~2–5 soatdan ~0,5–1 soatga
 * tushiradigan yordamchi: qatorda 10–20 rasta bo'lsa, admin ikkitasini
 * chizadi va qolganini shu funksiya to'ldiradi.
 *
 * ⚠ SOF CHIZIQLI — HECH QANDAY CV DA'VOSI YO'Q. Tepama-tepa `lerp`,
 *   `t = k/(n+1)`, `k = 1..n`. Kadrdan rastalarni «avtomatik ajratish»
 *   ATAYIN qurilmaydi (05-UI-SPEC §16.2): u real bozor kadrida
 *   ishlamaydi va ishlamaganini sezish qiyin.
 *
 * ⚠ TEPA SONI TENG BO'LMASA — `[]`. «Eng yaqin tepani topish» ni o'ylab
 *   topish mumkin edi; u ba'zan ishlab, ba'zan aralashib ketgan poligon
 *   chizardi va admin buni FAQAT kadrga qarab sezardi.
 *
 * Natija `first` va `last` ni O'Z ICHIGA OLMAYDI — ular allaqachon
 * chizilgan; qaytarilsa qatorda ustma-ust tushgan ikki zona paydo
 * bo'lardi va D-20 («birortasi band desa band») ularni ikki marta
 * sanardi.
 */
export function interpolateRow(first: Poly, last: Poly, n: number): Poly[] {
  if (first.length !== last.length || first.length === 0) {
    return [];
  }
  if (!Number.isInteger(n) || n <= 0) {
    return [];
  }

  const out: Poly[] = [];

  for (let k = 1; k <= n; k += 1) {
    const t = k / (n + 1);
    out.push(
      first.map((pt, i): Pt => {
        const target = last[i];
        return [
          clamp01(pt[0] + (target[0] - pt[0]) * t),
          clamp01(pt[1] + (target[1] - pt[1]) * t),
        ];
      }),
    );
  }

  return out;
}

/**
 * Yorliq qo'yish uchun ko'pburchak MARKAZI — chegaralovchi to'rtburchakdan.
 *
 * ⛔ TEPALAR O'RTACHASI EMAS, va bu ataylab: bitta tomonda tepalar zich
 *    bo'lsa o'rtacha o'sha tomonga tortiladi va rasta raqami chekkaga
 *    chiqib qolardi. Rasta amalda to'rtburchak (§6.5), unda ikkala
 *    usul ham bir xil natija beradi — farq faqat qo'lda tahrirlangan
 *    murakkab shaklda ko'rinadi va u yerda bbox markazi barqarorroq.
 *
 * ⚠ `null` — bo'sh ko'pburchak. Nol qaytarish `(0,0)` ga, ya'ni kadrning
 *   chap-yuqori burchagiga yorliq qo'yardi va u «shu yerda zona bor»
 *   degan yolg'on signal bo'lardi.
 */
export function centroidOf(poly: Poly): Pt | null {
  if (poly.length === 0) return null;
  let minX = poly[0]![0];
  let maxX = poly[0]![0];
  let minY = poly[0]![1];
  let maxY = poly[0]![1];
  for (const [x, y] of poly) {
    if (x < minX) minX = x;
    if (x > maxX) maxX = x;
    if (y < minY) minY = y;
    if (y > maxY) maxY = y;
  }
  return [(minX + maxX) / 2, (minY + maxY) / 2];
}
