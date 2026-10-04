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
  captureStale,
  frameFallbackKey,
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

/*
 * ===========================================================================
 * `captureStale` — «ONLAYN» YASHILINING YOLG'ONINI YOPADI (261004).
 *
 * Jonli bazada o'lchandi (Karmana):
 *
 *     192.168.1.245   status=online   last_seen=10-04 12:42
 *                     OXIRGI KADR     08-29 13:00   (jami 8 ta kadr)
 *     qolgan 15 tasi  oxirgi kadr     10-04 12:00   (261-269 ta kadr)
 *
 * Ya'ni bitta kamera 36 kundan beri DALIL yig'magan va panel uni yashil
 * ko'rsatgan. `last_seen_at` ni KASHFIYOT suradi (qurilma tarmoqda javob
 * berdi), kadr olish emas — shuning uchun u hech qachon qizarmasdi.
 * ===========================================================================
 */
describe("captureStale — kamera kadr bermay qo'yganmi", () => {
  const YANGI = "2026-10-04T12:00:00Z";

  test("⛔ KARMANA HOLATI: 36 kun orqada qolgan kamera ESKIRGAN", () => {
    expect(captureStale("2026-08-29T13:00:00Z", YANGI)).toBe(true);
  });

  test("boshqalar bilan birga kadr bergan kamera eskirmagan", () => {
    expect(captureStale(YANGI, YANGI)).toBe(false);
  });

  test("⚠ BIR NECHA SOAT ORQADA QOLISH ESKIRISH EMAS — jadval oynasi", () => {
    /*
     * Karmanada jadval 06:00-13:00. Kechqurun BARCHA kameraning oxirgi
     * kadri bir necha soat eski bo'ladi va bu NORMAL. Mutlaq chegara
     * («6 soatdan eski bo'lsa») har kuni butun flotni sariq qilardi.
     */
    expect(captureStale("2026-10-04T06:00:00Z", YANGI)).toBe(false);
    expect(captureStale("2026-10-03T13:00:00Z", YANGI)).toBe(false);
  });

  test("⛔ boshqalarda kadr BOR, bunda UMUMAN yo'q -> eskirgan", () => {
    expect(captureStale(null, YANGI)).toBe(true);
  });

  test("⛔ BOZORDA UMUMAN KADR YO'Q BO'LSA — HECH KIM aybdor emas", () => {
    /*
     * Yangi obyekt yoki agent hali ulanmagan holat. Bu yerda butun
     * ro'yxatni sariq qilish operatorni mavjud bo'lmagan nosozlikni
     * qidirishga yuborardi.
     */
    expect(captureStale(null, null)).toBe(false);
    expect(captureStale("2026-01-01T00:00:00Z", null)).toBe(false);
  });
});

/*
 * ===========================================================================
 * `frameFallbackKey` — BIR SAHIFANING IKKI KO'RINISHI ZID BO'LMAYDI (261004).
 *
 * Jonli serverda o'lchandi: kameralar sahifasining RO'YXAT ko'rinishi 16
 * kamerani «Onlayn · oxirgi ko'rilgan: hozirgina» deb, KATAK ko'rinishi esa
 * O'SHA 16 tasini «Qayta ulanmoqda…» deb ko'rsatardi.
 *
 * Sabab: katakcha kadr havolasi yo'qligining UCHALA sababini bitta matn
 * bilan atardi — holbuki u paytda jonli urinish allaqachon tugagan va
 * katakcha hech narsaga ULANMAYOTGAN edi.
 * ===========================================================================
 */
describe("frameFallbackKey — kadr o'rniga nima yoziladi", () => {
  const KADR = "11111111-1111-4111-8111-111111111111";

  test("⛔ kadr UMUMAN yo'q — yuklanmoqda holatida ham", () => {
    // Yuklanadigan narsaning O'ZI yo'q, ya'ni «yuklanmoqda» yolg'on.
    expect(
      frameFallbackKey({ snapshotId: null, isPending: true, isError: false }),
    ).toBe("wallNoFrame");
  });

  test("kadr yuklanayotganda — «yuklanmoqda»", () => {
    expect(
      frameFallbackKey({ snapshotId: KADR, isPending: true, isError: false }),
    ).toBe("wallFrameLoading");
  });

  test("kadr ochilmaganda — «ochilmadi»", () => {
    expect(
      frameFallbackKey({ snapshotId: KADR, isPending: false, isError: true }),
    ).toBe("wallFrameFailed");
  });

  test("⚠ XATO yuklanishdan USTUN", () => {
    // Ikkalasi ham rost bo'lsa, odamga kerakligi — nima NOTO'G'RI ketgani.
    expect(
      frameFallbackKey({ snapshotId: KADR, isPending: true, isError: true }),
    ).toBe("wallFrameFailed");
  });

  test("⛔ HECH QACHON «qayta ulanmoqda» QAYTARMAYDI", () => {
    /*
     * ASOSIY DA'VO. Bu funksiya chaqirilganda jonli urinish tugagan;
     * «qayta ulanmoqda» aynan shu yerda yolg'on edi va ro'yxat bilan
     * zid holat tug'dirardi.
     */
    const hammasi = [null, KADR].flatMap((snapshotId) =>
      [true, false].flatMap((isPending) =>
        [true, false].map((isError) =>
          frameFallbackKey({ snapshotId, isPending, isError }),
        ),
      ),
    );
    expect(hammasi).toHaveLength(8);
    expect(hammasi).not.toContain("wallReconnecting");
    expect(new Set(hammasi)).toEqual(
      new Set(["wallNoFrame", "wallFrameLoading", "wallFrameFailed"]),
    );
  });
});
