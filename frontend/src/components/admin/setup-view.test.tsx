/**
 * SOZLASH HISOBLARI — KAMERASIZ BOZOR TO'LIQ TAYYOR (260820).
 *
 * =============================================================================
 * ⛔⛔ BU TEST MAHSULOT QARORINI QULFLAYDI.
 *
 *   Pilot bozor kameralarni keyinroq (MikroTik orqali) ulaydi va shu
 *   vaqtgacha tizim to'liq ishlashi kerak: patta yig'ish, qarz,
 *   hisobot — hammasi kamerasiz yuradi. D-16 ga ko'ra kamera
 *   faollashtirishni HECH QACHON to'smaydi.
 *
 *   Shunga qaramay panel «86% tayyor» deb turardi — ya'ni to'liq
 *   ishlayotgan bozorni CHALA deb ko'rsatardi, har kuni.
 *
 *   Endi foiz faqat MAJBURIY qadamlardan hisoblanadi. Kamera
 *   ro'yxatda qoladi (ko'rinadi, unutilmaydi), lekin darajani
 *   pasaytirmaydi.
 * =============================================================================
 */
import { describe, expect, test } from "vitest";

import {
  attentionItems,
  setupPercent,
  setupSteps,
} from "@/components/admin/setup-view";
import type { SetupStatusResponse } from "@/lib/api-types";

/** To'liq sozlangan bozor — kamera bundan MUSTASNO. */
const COMPLETE: SetupStatusResponse = {
  zones: 2,
  categories: 2,
  tariffs_covered: 2,
  categories_total: 2,
  stalls: 41,
  stalls_with_category: 41,
  vendors: 26,
  calendar_configured: true,
  cameras: 0,
  can_activate: true,
  blocking: [],
};

describe("setupPercent", () => {
  test("⭐ KAMERASIZ, lekin qolgani to'liq bozor — 100%", () => {
    expect(setupPercent(setupSteps(COMPLETE))).toBe(100);
  });

  test("kamera ulangach ham 100% — daraja PASAYMAYDI va oshmaydi", () => {
    expect(setupPercent(setupSteps({ ...COMPLETE, cameras: 6 }))).toBe(100);
  });

  test("majburiy qadam chala bo'lsa foiz tushadi", () => {
    /* Olti majburiydan bittasi (ish kunlari) bajarilmagan -> 5/6. */
    const percent = setupPercent(
      setupSteps({ ...COMPLETE, calendar_configured: false }),
    );
    expect(percent).toBe(83);
  });

  test("bo'm-bo'sh bozor — 0%", () => {
    const empty: SetupStatusResponse = {
      ...COMPLETE,
      zones: 0,
      categories: 0,
      categories_total: 0,
      tariffs_covered: 0,
      stalls: 0,
      stalls_with_category: 0,
      vendors: 0,
      calendar_configured: false,
    };
    expect(setupPercent(setupSteps(empty))).toBe(0);
  });
});

describe("setupSteps", () => {
  test("kamera IXTIYORIY deb belgilangan, qolgan oltitasi majburiy", () => {
    const steps = setupSteps(COMPLETE);
    const optional = steps.filter((step) => step.optional === true);

    expect(optional).toHaveLength(1);
    expect(optional[0]?.key).toBe("cameras");
    expect(steps).toHaveLength(7);
  });

  test("kamera ro'yxatdan YO'QOLMAYDI — u ko'rinib turadi", () => {
    /*
     * ⛔ «Ixtiyoriy» degani «yashiringan» EMAS: kamera ulanmagani
     *    ko'rinib turishi kerak, aks holda uni unutib qo'yish oson.
     */
    expect(setupSteps(COMPLETE).map((step) => step.key)).toContain("cameras");
  });
});

describe("attentionItems", () => {
  test("⭐ KAMERASIZ bozorda DIQQAT ro'yxati BO'SH", () => {
    /*
     * ⛔ Har kuni ko'rinadigan va hech qachon hal qilinmaydigan
     *    ogohlantirish ogohlantirishning O'ZINI qadrsizlantiradi.
     */
    expect(attentionItems(COMPLETE)).toEqual([]);
  });

  test("HAQIQIY muammo esa ko'rinadi — tarifsiz rasta", () => {
    const items = attentionItems({ ...COMPLETE, stalls_with_category: 25 });

    expect(items).toHaveLength(1);
    expect(items[0]?.key).toBe("stallsWithoutCategory");
    expect(items[0]?.count).toBe(16);
    /* Pul yo'qoladi -> `danger`, `warning` emas. */
    expect(items[0]?.tone).toBe("danger");
  });

  test("ish kunlari belgilanmasa — kunlik hisob yurmaydi, qizil", () => {
    const items = attentionItems({ ...COMPLETE, calendar_configured: false });

    expect(items.map((item) => item.key)).toEqual(["noCalendar"]);
    expect(items[0]?.tone).toBe("danger");
  });
});
