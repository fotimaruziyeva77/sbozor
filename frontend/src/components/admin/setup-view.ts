import type { SetupStatusResponse } from "@/lib/api-types";

/*
 * =============================================================================
 * BOZOR ADMINI PANELINING HISOBLARI — SOF FUNKSIYALAR, JSX YO'Q.
 *
 * ⛔⛔ NEGA ALOHIDA FAYL: bu yerdagi har bir son EKRANDA hokim yoki
 *     tekshiruvchi ko'radigan da'vo bo'ladi. Ular JSX ichida yozilsa
 *     faqat brauzerda tekshirilardi; alohida sof funksiya sifatida
 *     ular test bilan qulflanadi va MANBASI bitta.
 *
 * ⛔⛔ HAMMA SON BITTA SO'ROVDAN: `GET /markets/{id}/setup-status`.
 *     Yangi «admin summary» endpointi YOZILMAYDI — u ustaning
 *     sanoqlaridan bir kun jimgina ajralib ketardigan ikkinchi haqiqat
 *     manbai bo'lardi (`market-status-card.tsx` da o'rnatilgan qaror).
 *
 * ⛔⛔ TO'QILGAN KO'RSATKICH YO'Q. Stitch maketida «12 rasta —
 *     sotuvchi biriktirilmagan band rasta» katagi bor va u CHIROYLI,
 *     lekin bizda bu son uchun YIG'MA manba yo'q: `GET /stalls`
 *     kursor bilan sahifalanadi, ya'ni uni bilish uchun 1000 rastani
 *     tortib olish kerak bo'lardi. Shuning uchun u kartani chizmaymiz
 *     — server yig'masi qo'shilgach qo'shiladi. Bo'sh joy soxta
 *     sondan yaxshi (D-10).
 * =============================================================================
 */

/** Ekranda ko'rsatiladigan bitta sozlash qadami. */
export type SetupStep = {
  /** `admin.steps.*` tarjima kaliti. */
  key: "zones" | "stalls" | "categories" | "tariffs" | "vendors" | "calendar" | "cameras";
  /** Bajarilganmi — halqa foizining asosi. */
  done: boolean;
  /** «6 / 6» ko'rinishidagi sanoq; bo'lmasa `null` (kalendar — ha/yo'q). */
  count: number | null;
  total: number | null;
  href: "/map" | "/stalls" | "/tariffs" | "/vendors" | "/calendar" | "/cameras";
};

/**
 * Yetti qadam — ustaning tartibi bilan BIR XIL (`wizard-steps.ts`).
 *
 * ⛔ Tartib tasodifiy emas: bozor shu ketma-ketlikda quriladi (zona ->
 *    rasta -> toifa -> tarif -> sotuvchi -> ish kuni -> kamera) va
 *    panel ustaning davomi bo'lib o'qilishi kerak, undan boshqa
 *    hikoya aytmasligi.
 */
export function setupSteps(status: SetupStatusResponse): SetupStep[] {
  return [
    {
      key: "zones",
      done: status.zones > 0,
      count: status.zones,
      total: null,
      href: "/map",
    },
    {
      key: "stalls",
      done: status.stalls > 0,
      count: status.stalls,
      total: null,
      href: "/stalls",
    },
    {
      key: "categories",
      done: status.categories > 0,
      count: status.categories,
      total: null,
      href: "/tariffs",
    },
    {
      /*
       * ⛔ «Tarif» qadami TOIFA bo'yicha o'lchanadi, rasta bo'yicha
       *    emas: narx toifaga qo'yiladi, rasta esa toifaga tegishli
       *    bo'ladi. Ikkalasini aralashtirish «6/6 tarif bor, lekin
       *    16 rastaga patta hisoblanmayapti» degan chalkashlikni
       *    beradi — shuning uchun rasta tomoni ALOHIDA qadam.
       */
      key: "tariffs",
      done:
        status.categories_total > 0 &&
        status.tariffs_covered >= status.categories_total,
      count: status.tariffs_covered,
      total: status.categories_total,
      href: "/tariffs",
    },
    {
      key: "vendors",
      done: status.vendors > 0,
      count: status.vendors,
      total: null,
      href: "/vendors",
    },
    {
      key: "calendar",
      done: status.calendar_configured,
      count: null,
      total: null,
      href: "/calendar",
    },
    {
      key: "cameras",
      done: status.cameras > 0,
      count: status.cameras,
      total: null,
      href: "/cameras",
    },
  ];
}

/** Bajarilgan qadamlar ulushi — 0..100 oralig'ida BUTUN son. */
export function setupPercent(steps: readonly SetupStep[]): number {
  if (steps.length === 0) return 0;
  const done = steps.filter((step) => step.done).length;
  return Math.round((done / steps.length) * 100);
}

/** Diqqat talab qiladigan bitta band. */
export type Attention = {
  /** `admin.attention.*` tarjima kaliti. */
  key: "stallsWithoutCategory" | "categoriesWithoutTariff" | "noCameras" | "noCalendar";
  /** Sarlavhadagi son; `null` bo'lsa yorliq sonsiz o'qiladi. */
  count: number | null;
  tone: "warning" | "danger";
  href: "/stalls" | "/tariffs" | "/cameras" | "/calendar";
};

/**
 * Diqqat ro'yxati — FAQAT haqiqiy yig'ma bor bandlar.
 *
 * ⛔ Ohang tanlovi ma'noli, bezak emas:
 *    `danger`  — PUL YO'QOLADI (tarifsiz rastaga patta hisoblanmaydi;
 *                ish kuni belgilanmasa kunlik hisob umuman yurmaydi);
 *    `warning` — o'lchov to'liq emas, lekin pul oqmayapti (kamera yo'q).
 *
 *    Bu farq qat'iy: hamma narsani qizil qilish qizilni ma'nosiz
 *    qiladi va haqiqiy pul yo'qotishi ko'zga tashlanmay qoladi.
 */
export function attentionItems(status: SetupStatusResponse): Attention[] {
  const items: Attention[] = [];

  const stallsWithoutCategory = Math.max(
    0,
    status.stalls - status.stalls_with_category,
  );
  if (stallsWithoutCategory > 0) {
    items.push({
      key: "stallsWithoutCategory",
      count: stallsWithoutCategory,
      tone: "danger",
      href: "/stalls",
    });
  }

  const categoriesWithoutTariff = Math.max(
    0,
    status.categories_total - status.tariffs_covered,
  );
  if (categoriesWithoutTariff > 0) {
    items.push({
      key: "categoriesWithoutTariff",
      count: categoriesWithoutTariff,
      tone: "danger",
      href: "/tariffs",
    });
  }

  if (!status.calendar_configured) {
    items.push({ key: "noCalendar", count: null, tone: "danger", href: "/calendar" });
  }

  if (status.cameras === 0) {
    items.push({ key: "noCameras", count: null, tone: "warning", href: "/cameras" });
  }

  return items;
}
