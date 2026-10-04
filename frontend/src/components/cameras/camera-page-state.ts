/*
 * =============================================================================
 * `/cameras` SAHIFASINING SOF QARORLARI.
 *
 * NEGA ALOHIDA MODUL — O'LCHOV BILAN TOPILDI (03-09 sabotaji S3):
 *
 *   Bu qarorlar dastlab `page.tsx` ning ichida, eksport qilinmagan
 *   funksiyalar edi. Sabotaj `cameraEmptyKind` dan E-1 ning shartini
 *   olib tashladi — ya'ni «NVR umuman yo'q» holatida ekranda
 *   «Kameralarni topish» tugmasi chiqadigan qildi (mavjud bo'lmagan
 *   qurilmani skanerlashga taklif). Natija: `typecheck`, `lint`,
 *   `build`, 167 vitest va 86 node testi — HAMMASI YASHIL qoldi.
 *
 *   Ya'ni rejaning O'Z talabi («E-1 va E-2 hech qachon aralashmaydi»)
 *   hech qanday mexanizm bilan qamralmagan edi. Marshrut faylining
 *   ichidagi funksiyani test qilib bo'lmaydi: Next 16 marshrut
 *   fayllarining eksportlarini tekshiradi va tanilmagan eksportni rad
 *   etadi.
 *
 * ⚠ SHUNING UCHUN QOIDA SOF FUNKSIYA BO'LIB SHU YERDA YASHAYDI va
 *   `camera-page-state.test.tsx` uni AYNAN o'lchaydi. 03-10 filtr
 *   qatorini qo'shganda `filtersActive`/`archivedOnly` shu yerda
 *   to'ladi — qaror ikkinchi joyga ko'chmaydi.
 * =============================================================================
 */

/** To'rtta bo'sh holat + «bo'sh emas» (UI-SPEC §10.2). */
export type CameraEmptyKind =
  | "none"
  | "no-nvr"
  | "no-cameras"
  | "filtered"
  | "archived";

export type CameraEmptyInput = {
  /** «Arxivlanganlarni ko'rsatish» yoqilganmi (03-10). */
  archivedOnly: boolean;
  /** Birorta filtr qo'yilganmi (03-10). */
  filtersActive: boolean;
  /** Bozorda saqlangan NVR qurilmasi bormi. */
  hasNvr: boolean;
  /** Ro'yxatda ko'rinadigan kameralar soni. */
  visibleCount: number;
};

/**
 * Qaysi bo'sh holat ko'rsatiladi (UI-SPEC §10.2).
 *
 * ⚠ E-1 VA E-2 STRUKTURAVIY RAVISHDA ARALASHA OLMAYDI: birinchisining
 *   sharti `!hasNvr`, ikkinchisiniki esa undan KEYIN keladi, ya'ni
 *   `hasNvr === true` bo'lgandagina. Ikkalasini ikki joyda alohida
 *   `if` bilan hal qilish aynan «qurilma yo'q, lekin “Kameralarni
 *   topish” tugmasi turibdi» holatini tug'dirardi — admin mavjud
 *   bo'lmagan qurilmani skanerlashga taklif qilinardi.
 *
 * ⚠ TARTIB — QARORNING O'ZI, tasodifiy emas:
 *     1. ro'yxat bo'sh emas          -> hech qanday bo'sh holat yo'q;
 *     2. qurilma yo'q                -> E-1 (keyingi qadam: NVR ulash);
 *     3. faqat arxiv ko'rsatilyapti  -> E-4 (amal yo'q — checkbox bor);
 *     4. filtr qo'yilgan             -> E-3 (keyingi qadam: tozalash);
 *     5. qolgan holat                -> E-2 (keyingi qadam: skanerlash).
 *   Har birining KEYINGI QADAMI boshqa va aynan shu sababdan ular
 *   bitta «bo'sh» holatga yig'ilmaydi.
 */
export function cameraEmptyKind(input: CameraEmptyInput): CameraEmptyKind {
  if (input.visibleCount > 0) return "none";
  if (!input.hasNvr) return "no-nvr";
  if (input.archivedOnly) return "archived";
  if (input.filtersActive) return "filtered";
  return "no-cameras";
}

/**
 * `?run=` qiymati kashfiyot yugurishining identifikatorimi (§5.4).
 *
 * ⚠ YAROQSIZ QIYMAT XATO EMAS. Chaqiruvchi uni JIMGINA tozalaydi:
 *   eski havolani ochish yoki qo'lda yozilgan parametr nosozlik emas
 *   va xato bloki adminni mavjud bo'lmagan muammoni qidirishga majbur
 *   qilardi.
 */
export function isDiscoveryRunId(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/iu.test(
    value,
  );
}

/**
 * Bitta kundan ortiq ORQADA QOLISH — «kadr kelmayapti» deyish uchun chegara.
 *
 * ⛔ CHEGARA MUTLAQ EMAS, NISBIY (261004). «Oxirgi kadr 6 soatdan eski
 *    bo'lsa» degan qoida Karmanada (06:00-13:00 jadval) har kuni
 *    kechqurun BUTUN flotni sariq qilib qo'yardi — kechki slot yo'q,
 *    demak kadr ham yo'q, va bu NORMAL. Shuning uchun o'lchov boshqa
 *    kameralar bilan solishtiriladi: ular kadr berib turganda bu
 *    bermayotgan bo'lsa — muammo kamerada, jadvalda emas.
 */
const KECHIKISH_MS = 24 * 60 * 60 * 1000;

/**
 * Kamera kadr bermay qo'yganmi — BOSHQA kameralarga nisbatan.
 *
 * ⛔ `newest === null` DA HAR DOIM `false`: bozorda umuman kadr yo'q bo'lsa
 *    (yangi obyekt, agent hali ulanmagan) hech kimni ayblash mumkin emas —
 *    va o'shanda butun ro'yxatni sariq qilish operatorni mavjud bo'lmagan
 *    nosozlikni qidirishga yuborardi.
 */
export function captureStale(
  lastCaptureAt: string | null,
  newest: string | null,
): boolean {
  if (newest === null) return false;
  // Kadri UMUMAN yo'q, boshqalarda esa bor -> shubhasiz muammo.
  if (lastCaptureAt === null) return true;
  return (
    new Date(newest).getTime() - new Date(lastCaptureAt).getTime() >
    KECHIKISH_MS
  );
}
