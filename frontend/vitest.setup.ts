/*
 * Vitest global sozlamasi (01-12).
 *
 * `@testing-library/jest-dom/vitest` — `toBeDisabled()`, `toBeInTheDocument()`
 * kabi DOM matcher'larini vitest'ning `expect` iga QO'SHADI va ayni paytda
 * ularning TypeScript tiplarini ham e'lon qiladi (shuning uchun aynan
 * `/vitest` kirish nuqtasi, `/matchers` emas).
 *
 * `cleanup()` har testdan keyin render qilingan daraxtni DOM'dan olib
 * tashlaydi. Busiz bir fayldagi ikkinchi test birinchisining tugmalarini ham
 * ko'radi va `getAllByRole` sanoqlari jimgina noto'g'ri bo'lib qoladi.
 */
import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => {
  cleanup();
});

/*
 * =============================================================================
 * ⛔⛔ `scrollIntoView` POLIFILI — JSDOM BO'SHLIG'I, MAHSULOT NUQSONI EMAS.
 *
 *   `Element.prototype.scrollIntoView` — brauzerda HAR DOIM mavjud
 *   standart API, jsdom esa uni umuman amalga oshirmagan. Uni
 *   chaqiradigan effekt testda `TypeError` bilan yiqiladi va nosozlik
 *   REACT RENDERIDA ko'rinadi — ya'ni sabab butunlay boshqa joyda
 *   qidiriladi.
 *
 * ⛔ KOMPONENTDA `typeof` QO'RIQCHISI QO'YILMAYDI: brauzerda bu funksiya
 *   har doim bor va qo'riqchi HAQIQIY nosozlikni (masalan noto'g'ri
 *   element tanlangani) jimgina yutib yuborardi. Bo'shliq test
 *   MUHITIDA, shuning uchun tuzatish ham shu yerda.
 *
 * ⚠ `noop` — u ATAYIN hech nima qilmaydi: jsdom joylashuvni umuman
 *   hisoblamaydi, ya'ni «ko'rinadigan joyga surildimi?» degan da'voni bu
 *   yerda o'lchab bo'lmaydi va soxta amalga oshirish soxta ishonch
 *   berardi. Fokus esa HAQIQIY va u o'lchanadi.
 * =============================================================================
 */
if (typeof Element !== "undefined" && !Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = function scrollIntoView(): void {};
}
