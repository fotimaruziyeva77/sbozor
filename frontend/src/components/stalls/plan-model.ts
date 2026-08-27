import type { MapZone } from "@/lib/api-types";

/*
 * =============================================================================
 * QO'LDA CHIZILGAN PLAN — SOF MODEL, JSX YO'Q (260820).
 *
 * ⛔⛔ NEGA UMUMAN QO'LDA CHIZISH BOR.
 *
 *     Sxematik xarita (`stall-map.tsx`) rastalarni zona bo'yicha guruhlab
 *     kod tartibida bir tekis panjaraga teradi. U HAR DOIM ishlaydi va
 *     hech qanday sozlash talab qilmaydi — lekin u bozorning HAQIQIY
 *     shaklini ko'rsatmaydi. Nazoratchi «A qatorining oxiri» deganda
 *     sxematik xaritada hech narsa ko'rmaydi.
 *
 *     Shuning uchun chizma IXTIYORIY QATLAM: koordinata qo'yilmagan
 *     bozor sxematik ko'rinishda ishlashda davom etadi va hech qachon
 *     «avval chizing» degan devorga urilmaydi (D-16 bilan bir xil
 *     falsafa — kamera ham hech narsani to'smaydi).
 *
 * =============================================================================
 * ⛔⛔ NEGA SOF FUNKSIYA VA NEGA ALOHIDA FAYL.
 *
 *     Chizma tahriri — HOLAT MASHINASI: qo'yish, ko'chirish, o'chirish,
 *     bekor qilish, va oxirida SERVERGA YUBORILADIGAN FARQ. Bularning
 *     har biri komponent ichida yozilsa faqat brauzerda tekshirilardi.
 *     Bu yerda ular test bilan qulflanadi.
 *
 * ⛔ KOORDINATA — PANJARA INDEKSI, PIKSEL EMAS. Piksel saqlash ekran
 *   o'lchamiga bog'lab qo'yardi: telefonda chizilgan plan monitorda
 *   siljib ketardi. Indeks esa qanday ko'rsatilishidan MUSTAQIL.
 * =============================================================================
 */

/** Bitta rastaning chizmadagi o'rni — panjara indeksi (0-dan). */
export type PlanSpot = { x: number; y: number };

/** Butun chizma: `stall_id` -> o'rin. Joylashtirilmagan rasta bu yerda YO'Q. */
export type Placement = Readonly<Record<string, PlanSpot>>;

/**
 * Panjaraning eng katta o'lchami — 0026 migratsiyasining CHECK chegarasi.
 *
 * ⛔ Bu son shu yerda TAKRORLANADI (sxemada ham bor) va bu ataylab:
 *    klient chegaradan chiqqan qiymatni YUBORMASLIGI kerak, aks holda
 *    odam 500 xatosini ko'rardi. Sxemadagisi esa xom SQL yo'lini yopadi.
 */
export const PLAN_MAX = 1000;

/** Bo'sh chizmada ko'rsatiladigan panjara — telefon ekraniga sig'adi. */
export const MIN_COLS = 12;
export const MIN_ROWS = 8;

/** Panjara kengaytmasi — bitta bosishda qo'shiladigan ustun/qator soni. */
export const GROW_STEP = 4;

/** `x`/`y` juftligini katak kalitiga aylantiradi (`Map` uchun). */
export function spotKey(x: number, y: number): string {
  return `${x}:${y}`;
}

/**
 * Server javobidan boshlang'ich chizmani yig'adi.
 *
 * ⛔ `plan_x`/`plan_y` NULL bo'lgan rasta ro'yxatga KIRMAYDI — u
 *    «hali chizilmagan». `0` bilan almashtirish hamma chizilmagan
 *    rastani chap-yuqori burchakka bosib qo'yardi.
 *
 * ⚠ IKKALASI ham bo'lishi shart: sxemada `(plan_x IS NULL) = (plan_y IS
 *   NULL)` konstrayti bor, lekin klient unga ISHONMAYDI — yarim
 *   koordinata kelsa u shunchaki chizilmagan deb qabul qilinadi.
 */
export function placementFromZones(zones: readonly MapZone[]): Placement {
  const placement: Record<string, PlanSpot> = {};
  for (const zone of zones) {
    for (const cell of zone.cells) {
      if (cell.plan_x === null || cell.plan_y === null) continue;
      placement[cell.id] = { x: cell.plan_x, y: cell.plan_y };
    }
  }
  return placement;
}

/** Bitta katakda turgan rastani topish uchun teskari indeks. */
export function occupancyOf(placement: Placement): ReadonlyMap<string, string> {
  const byCell = new Map<string, string>();
  for (const [stallId, spot] of Object.entries(placement)) {
    byCell.set(spotKey(spot.x, spot.y), stallId);
  }
  return byCell;
}

/**
 * Panjara o'lchami — CHIZMANI O'Z ICHIGA OLADI, undan kichik BO'LMAYDI.
 *
 * ⛔⛔ Bu funksiya ma'lumot YO'QOLISHINING oldini oladi. Agar panjara
 *     har doim `MIN_COLS` bo'lsa, kengroq bozorda chizilgan rasta
 *     ekrandan CHIQIB KETARDI: odam uni ko'rmaydi, o'chira olmaydi,
 *     lekin u bazada turibdi va hisobotda paydo bo'ladi.
 *
 *     Shuning uchun o'lcham har doim eng chekkadagi rastadan KATTA.
 */
export function gridSize(
  placement: Placement,
  extraCols = 0,
  extraRows = 0,
): { cols: number; rows: number } {
  let maxX = -1;
  let maxY = -1;
  for (const spot of Object.values(placement)) {
    if (spot.x > maxX) maxX = spot.x;
    if (spot.y > maxY) maxY = spot.y;
  }
  return {
    cols: Math.min(PLAN_MAX, Math.max(MIN_COLS, maxX + 2) + extraCols),
    rows: Math.min(PLAN_MAX, Math.max(MIN_ROWS, maxY + 2) + extraRows),
  };
}

/** Navbatdagi bitta rasta — chap paneldagi yorliq. */
export type QueueItem = { id: string; code: string; zoneName: string };

/**
 * Hali chizilmagan rastalar — SERVER TARTIBIDA.
 *
 * ⛔ Klient QAYTA SARALAMAYDI (UI-SPEC §7.3): server `code_sort` bilan
 *    inson-raqamli tartib beradi (2 < 10 < 100) va uni JS'ning
 *    `localeCompare` i bilan qayta qurish uchala tilda boshqa natija
 *    berardi. «Navbatdagi rasta» tushunchasi esa aynan shu tartibga
 *    tayanadi — u ko'z bilan ko'rinadigan ro'yxat bilan BIR XIL
 *    bo'lishi shart.
 */
export function queueOf(
  zones: readonly MapZone[],
  placement: Placement,
): QueueItem[] {
  const queue: QueueItem[] = [];
  for (const zone of zones) {
    for (const cell of zone.cells) {
      if (placement[cell.id] !== undefined) continue;
      queue.push({ id: cell.id, code: cell.code, zoneName: zone.name });
    }
  }
  return queue;
}

/** Serverga yuboriladigan farq. */
export type PlanDiff = {
  placed: { stall_id: string; plan_x: number; plan_y: number }[];
  cleared: string[];
};

/**
 * BOSHLANG'ICH va JORIY chizma orasidagi farq.
 *
 * =============================================================================
 * ⛔⛔ FAQAT O'ZGARGANI YUBORILADI VA BU SHUNCHAKI TEJAMKORLIK EMAS.
 *
 *     1000 rastali bozorda butun chizmani har «Saqlash» da yuborish
 *     har bir qatorning `updated_at` ini yangilardi — ya'ni audit
 *     jurnalida 1000 ta «o'zgardi» yozuvi paydo bo'lardi, aslida bitta
 *     rasta surilgan bo'lsa ham. Bu jurnalni o'qib bo'lmas qilardi.
 *
 * ⛔ AYNI JOYGA QAYTA QO'YISH — O'ZGARISH EMAS. Odam rastani olib,
 *   yana o'sha katakka qo'yishi mumkin; bu serverga BORMAYDI.
 * =============================================================================
 */
export function planDiff(original: Placement, current: Placement): PlanDiff {
  const placed: PlanDiff["placed"] = [];
  for (const [stallId, spot] of Object.entries(current)) {
    const before = original[stallId];
    if (before !== undefined && before.x === spot.x && before.y === spot.y) {
      continue;
    }
    placed.push({ stall_id: stallId, plan_x: spot.x, plan_y: spot.y });
  }

  const cleared: string[] = [];
  for (const stallId of Object.keys(original)) {
    if (current[stallId] === undefined) cleared.push(stallId);
  }

  return { placed, cleared };
}

/** Farq bo'shmi — «Saqlash» tugmasini o'chirish uchun. */
export function isEmptyDiff(diff: PlanDiff): boolean {
  return diff.placed.length === 0 && diff.cleared.length === 0;
}

/**
 * Rastani katakka qo'yadi — BAND katakka qo'yilmaydi.
 *
 * ⛔⛔ IKKI RASTA BITTA KATAKDA TURA OLMAYDI. Bu texnik cheklov emas —
 *     chizma JISMONIY joyni anglatadi va ikkita ustma-ust rasta chizmani
 *     yolg'onga aylantirardi: ekranda bittasi ko'rinardi, ikkinchisi
 *     esa «chizilgan» hisoblanib ko'zdan G'OYIB bo'lardi.
 *
 * ⛔ O'SHA rastani O'SHA katakka qayta qo'yish — RUXSAT (o'zgarishsiz
 *   qaytadi), aks holda surish paytidagi takroriy `pointerover` hodisasi
 *   rastani jimgina yo'qotardi.
 */
export function placeStall(
  placement: Placement,
  stallId: string,
  x: number,
  y: number,
): Placement {
  if (x < 0 || y < 0 || x >= PLAN_MAX || y >= PLAN_MAX) return placement;

  const occupant = occupancyOf(placement).get(spotKey(x, y));
  if (occupant !== undefined && occupant !== stallId) return placement;

  const before = placement[stallId];
  if (before !== undefined && before.x === x && before.y === y) return placement;

  return { ...placement, [stallId]: { x, y } };
}

/** Rastani chizmadan chiqaradi — u navbatga QAYTADI, yo'qolmaydi. */
export function clearSpot(placement: Placement, x: number, y: number): Placement {
  const occupant = occupancyOf(placement).get(spotKey(x, y));
  if (occupant === undefined) return placement;

  const next = { ...placement };
  delete next[occupant];
  return next;
}

/**
 * Ikki katak ORASIDAGI yo'l — `from` KIRMAYDI, `to` KIRADI.
 *
 * =============================================================================
 * ⛔⛔ NEGA BU KERAK: TEZ SURISH KATAKLARNI TASHLAB KETADI.
 *
 *     `pointerenter` faqat kursor HAQIQATAN tekkan katakda ishlaydi.
 *     Odam qatorni tez chizganda brauzer oraliq nuqtalarni umuman
 *     bermaydi — 260820 da Chromeda o'lchandi: bitta surishda 1, 3 va
 *     10-ustunlar to'ldi, oradagilari BO'SH qoldi.
 *
 *     Natija shunchaki «sekinroq chizing» emas edi: qatorda TESHIK
 *     qolardi va navbat siljib ketgani uchun keyingi rastalar HAM
 *     noto'g'ri katakka tushardi. Ya'ni tez harakat chizmani jimgina
 *     buzardi.
 *
 * ⛔ DIAGONAL — TAXMIN QILINMAYDI: qiya surishda faqat `to` qaytadi.
 *   Ikki nuqta orasini diagonal bilan to'ldirish odam CHIZMAGAN
 *   rastalarni qo'yardi — «qator chizish» esa har doim to'g'ri
 *   chiziq bo'ylab boradi.
 * =============================================================================
 */
export function cellsBetween(from: PlanSpot, to: PlanSpot): PlanSpot[] {
  if (from.x === to.x && from.y === to.y) return [];

  const path: PlanSpot[] = [];
  if (from.y === to.y) {
    const step = to.x > from.x ? 1 : -1;
    for (let x = from.x + step; x !== to.x + step; x += step) {
      path.push({ x, y: to.y });
    }
    return path;
  }
  if (from.x === to.x) {
    const step = to.y > from.y ? 1 : -1;
    for (let y = from.y + step; y !== to.y + step; y += step) {
      path.push({ x: to.x, y });
    }
    return path;
  }
  return [to];
}

/**
 * Navbatni kataklar bo'ylab KETMA-KET to'kadi.
 *
 * ⛔⛔ BAND KATAK NAVBATNI SILJITMAYDI. Yo'lda allaqachon qo'yilgan
 *     rasta uchrasa, u CHETLAB o'tiladi va navbatdagi rasta KEYINGI
 *     bo'sh katakka tushadi. Aks holda bitta band katak butun
 *     qatorni bir pog'ona surib yuborardi — odam esa buni faqat
 *     oxirida, hamma kod noto'g'ri joyda turganda ko'rardi.
 */
export function placeSequence(
  placement: Placement,
  stallIds: readonly string[],
  spots: readonly PlanSpot[],
): Placement {
  let next = placement;
  let index = 0;
  for (const spot of spots) {
    if (index >= stallIds.length) break;
    const before = next;
    next = placeStall(next, stallIds[index]!, spot.x, spot.y);
    if (next !== before) index += 1;
  }
  return next;
}

/** Yo'ldagi barcha katakni chizmadan chiqaradi (o'chirgich surilganda). */
export function clearSequence(
  placement: Placement,
  spots: readonly PlanSpot[],
): Placement {
  let next = placement;
  for (const spot of spots) next = clearSpot(next, spot.x, spot.y);
  return next;
}
