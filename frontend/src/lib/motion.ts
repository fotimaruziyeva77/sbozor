/*
 * =============================================================================
 * HARAKAT IMKONIYATINI O'QISH — BIR MARTALIK, OBUNA EMAS (09-UI-SPEC §8.4).
 *
 * Naqsh manbai: `components/stalls/stall-map.tsx:46,56` (matchMedia guard'i) —
 * ixtiro emas. LEKIN standart ATAYLAB TESKARI va bu ko'r nusxa emas:
 *
 *   `stall-map` fail-OPEN (`true`)  — «API yo'q -> hamma zona OCHIQ qolsin»,
 *                                     chunki u KONTENT ko'rinishini boshqaradi
 *                                     va yashirish yo'qotish bo'lardi;
 *   `motion`    fail-…OFF (`false`) — «API yo'q -> CHEKLOV YO'Q», chunki bu
 *                                     funksiya HARAKATNI TO'SUVCHI afzallikni
 *                                     o'qiydi: mavjud bo'lmagan media-API
 *                                     foydalanuvchi afzalligi EMAS, ya'ni
 *                                     animatsiya odatdagidek o'ynayveradi.
 *
 * ⛔ `subscribeToDesktop`/`addEventListener` qismi KO'CHIRILMAGAN: bu BIR
 *    MARTALIK o'qish, obuna emas. Afzallik odatda sessiya davomida
 *    o'zgarmaydi; har chaqiruvda yangidan o'qiladi (hodisa bo'lganda keyingi
 *    to'lov allaqachon yangi qiymatni ko'radi). `useSyncExternalStore`
 *    qatlami kerak bo'lsa — u alohida hook bo'lib tug'iladi, bu funksiya
 *    o'sha kunda ham SOF O'QISH bo'lib qoladi.
 *
 * ⛔ jsdom 30.0.1 da `window.matchMedia` UMUMAN YO'Q [O'LCHANDI, 09-RESEARCH
 *    Tuzoq 1] — guard'siz har chaqiruv `TypeError` otardi va testda buning
 *    sababi «animatsiya» deb noto'g'ri o'qilardi. Guard MAJBURIY.
 * =============================================================================
 */

/**
 * Foydalanuvchi «harakatni kamaytirish»ni so'raganmi — bir martalik o'qish.
 *
 * `true` FAQAT brauzer buni ochiq aytganda: `window` yo'q (SSR) yoki
 * `matchMedia` funksiya bo'lmasa (jsdom, eski muhit) — `false`, ya'ni
 * «cheklov yo'q» deb o'qiladi (sabab modul sarlavhasida).
 */
export function prefersReducedMotion(): boolean {
  if (typeof window === "undefined") return false;
  if (typeof window.matchMedia !== "function") return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}
