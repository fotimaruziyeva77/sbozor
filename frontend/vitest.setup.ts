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
