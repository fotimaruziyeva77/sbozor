/**
 * `/cameras` SAHIFASINING SOF QARORLARI — E-1/E-2 CHEGARASI VA `?run=`.
 *
 * =============================================================================
 * NEGA BU FAYL BOR (03-09 sabotaji S3 ning natijasi):
 *
 *   Qoida `page.tsx` ning ichida yashaganda undan E-1 ning shartini
 *   olib tashlash HECH NARSANI qizartirmagan edi — `typecheck`, `lint`,
 *   `build`, 167 vitest va 86 node testi hammasi yashil qolgan. Ya'ni
 *   rejaning o'z talabi («E-1 va E-2 hech qachon aralashmaydi»)
 *   o'lchanmaydigan da'vo edi.
 *
 *   Bu faylning butun vazifasi — o'sha da'voni O'LCHANADIGAN qilish.
 * =============================================================================
 *
 * ⚠ FAYL KENGAYTMASI `.tsx` VA BU MAJBURIY: `vitest.config.ts` ning
 *   `include` naqshi `src/**\/*.test.tsx`. `.ts` fayl JIMGINA ishga
 *   tushmasdi va «hammasi yashil» hisoboti yolg'on bo'lardi (03-08 da
 *   o'lchangan holat).
 */
import { describe, expect, test } from "vitest";

import {
  cameraEmptyKind,
  isDiscoveryRunId,
} from "@/components/cameras/camera-page-state";

const BASE = {
  archivedOnly: false,
  filtersActive: false,
  hasNvr: false,
  visibleCount: 0,
};

describe("cameraEmptyKind — to'rtta bo'sh holat (UI-SPEC §10.2)", () => {
  test("⚠ E-1 va E-2 HECH QACHON aralashmaydi", () => {
    /*
     * ENG MUHIM ASSERT. Qurilma yo'q holatda E-2 chiqsa, ekranda
     * «Kameralarni topish» tugmasi turardi — mavjud bo'lmagan
     * qurilmani skanerlashga taklif. Aksincha, qurilma bor holatda
     * E-1 chiqsa, admin ikkinchi NVR qo'shishga undalardi.
     */
    expect(cameraEmptyKind({ ...BASE, hasNvr: false })).toBe("no-nvr");
    expect(cameraEmptyKind({ ...BASE, hasNvr: true })).toBe("no-cameras");

    // Filtr yoqilgan bo'lsa ham qurilmasizlik BIRINCHI turadi: keyingi
    // qadam filtrni tozalash emas, NVR ulash.
    expect(
      cameraEmptyKind({
        ...BASE,
        archivedOnly: true,
        filtersActive: true,
        hasNvr: false,
      }),
    ).toBe("no-nvr");
  });

  test("ro'yxat bo'sh emas — hech qanday bo'sh holat yo'q", () => {
    expect(cameraEmptyKind({ ...BASE, visibleCount: 1 })).toBe("none");
    expect(
      cameraEmptyKind({ ...BASE, hasNvr: true, visibleCount: 6 }),
    ).toBe("none");
    // Qurilma yo'q, lekin qator bor (arxivdan qolgan) — baribir «none».
    expect(
      cameraEmptyKind({ ...BASE, hasNvr: false, visibleCount: 3 }),
    ).toBe("none");
  });

  test("E-3 va E-4 ajratiladi va E-4 birinchi turadi", () => {
    expect(
      cameraEmptyKind({ ...BASE, filtersActive: true, hasNvr: true }),
    ).toBe("filtered");

    expect(
      cameraEmptyKind({ ...BASE, archivedOnly: true, hasNvr: true }),
    ).toBe("archived");

    /*
     * «Arxivlanganlarni ko'rsatish» yoqilgan, lekin arxivda hech narsa
     * yo'q — bu E-4 va uning amali YO'Q (checkbox allaqachon ko'rinadi).
     * E-3 bo'lsa «Filtrlarni tozalash» tugmasi chiqib, checkbox
     * belgisini olib tashlashni taklif qilardi — ya'ni foydalanuvchi
     * ATAYLAB yoqqan ko'rinishni bekor qilishni.
     */
    expect(
      cameraEmptyKind({
        ...BASE,
        archivedOnly: true,
        filtersActive: true,
        hasNvr: true,
      }),
    ).toBe("archived");
  });
});

describe("isDiscoveryRunId — `?run=` ning tekshiruvi (§5.4)", () => {
  test.each([
    ["66666666-6666-4666-8666-666666666666", true],
    ["66666666-6666-4666-8666-666666666666".toUpperCase(), true],
    ["", false],
    ["yes", false],
    ["66666666-6666-4666-8666", false],
    ["66666666-6666-4666-8666-66666666666g", false],
    ["<script>alert(1)</script>", false],
  ])("%s -> %s", (value, expected) => {
    expect(isDiscoveryRunId(value)).toBe(expected);
  });
});
