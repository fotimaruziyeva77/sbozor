/*
 * =============================================================================
 * BUGUNGI PUL O'ZI YANGILANADI (261112).
 *
 * Buyurtmachi: «rastalar puli kiritilganda avtomatik yangilansin, hozir o'zim
 * yangilashimga to'g'ri kelyapti». Kassir to'lovni boshqa qurilmada yozadi,
 * panel, plan-xarita va patta hisobi esa sahifa qayta yuklanmaguncha eski
 * raqamni ko'rsatardi.
 *
 * Ilgari bu so'rovlarda taymer ATAYIN yo'q edi: raqam o'qilayotganda jimgina
 * o'zgarmasin. Buyurtmachi teskarisini tanladi. Raqam qachon yangilangani
 * panel sarlavhasidagi «yangilandi» soatida ko'rinib turadi.
 *
 * ⛔ Faqat ko'rinib turgan tabda (`refetchIntervalInBackground: false`) va faqat
 *    bugunni qamragan davrda: yopilgan kunlar o'zgarmaydi, ularni qayta so'rash
 *    serverni bekorga yuklardi.
 * =============================================================================
 */

/** Bugungi pul so'rovlari shu oraliqda qayta so'raladi. */
export const LIVE_REFRESH_MS = 30_000;

/** Bozor kuni — Toshkent vaqtida, `YYYY-MM-DD` (`day-picker.tsx::businessDayIn` bilan bir xil). */
export function marketToday(now: Date = new Date()): string {
  return new Intl.DateTimeFormat("en-CA", {
    day: "2-digit",
    month: "2-digit",
    timeZone: "Asia/Tashkent",
    year: "numeric",
  }).format(now);
}

/** Davr bugunni qamraydimi — qamrasa raqam kun ichida o'zgaradi. */
export function includesMarketToday(to: string, now: Date = new Date()): boolean {
  return to >= marketToday(now);
}
