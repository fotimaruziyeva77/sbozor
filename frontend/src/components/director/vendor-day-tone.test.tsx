/**
 * Sotuvchi tarixidagi kun BELGISI — rang va matn (261006).
 *
 * =============================================================================
 * ⛔⛔ IKKI DA'VO, IKKALASI HAM JIM BUZILADIGAN TURDAN.
 *
 *   1. «KECHIRILGAN» YASHIL BO'LMAYDI. 2026-10-05 da bozorning
 *      1 176 000 so'm qarzi kechirilgan. Agar o'sha kunlar yashil
 *      ko'rinsa, direktor ekranga qarab «pul tushgan» deb o'qiydi —
 *      holbuki kassaga HECH NARSA tushmagan. `debt_settlement` moduli
 *      aynan shuni («soxta to'lov yozilmaydi») rad etgan va bu qaror
 *      ekranda ham saqlanishi kerak.
 *
 *   2. HAR HOLATNING MATNI UCHALA TILDA BOR. Kalit yo'q bo'lsa
 *      `next-intl` ekranga XOM KALITNI chizadi (`director.vaDay_paid`)
 *      va buni faqat foydalanuvchi ko'radi.
 * =============================================================================
 */
import { describe, expect, test } from "vitest";

import { KUN_TONE } from "@/components/director/vendor-days";
import ru from "../../../messages/ru.json";
import uzCyrl from "../../../messages/uz-Cyrl.json";
import uzLatn from "../../../messages/uz-Latn.json";

/** Serverdagi `VendorDayStatus` ning AYNAN nusxasi (`report_repo`). */
const HOLATLAR = ["paid", "partial", "unpaid", "waived", "advance"] as const;

describe("kun belgisi", () => {
  test("⛔ KECHIRILGAN kun YASHIL emas", () => {
    expect(KUN_TONE.waived).not.toBe("success");
  });

  test("⛔ YASHIL faqat haqiqatan TO'LANGAN kunga tegishli", () => {
    /*
     * ASOSIY DA'VO. Birinchi testning o'zi yetmasdi: `waived` ni
     * sariq qilib, `advance` ni yashil qoldirish mumkin edi — va
     * hisobsiz to'lov ham yopilgan patta bo'lib ko'rinardi.
     */
    const yashillar = HOLATLAR.filter((h) => KUN_TONE[h] === "success");
    expect(yashillar).toEqual(["paid"]);
  });

  test("to'lanmagan kun QIZIL", () => {
    expect(KUN_TONE.unpaid).toBe("danger");
  });

  test.each([["uz-Latn", uzLatn], ["uz-Cyrl", uzCyrl], ["ru", ru]])(
    "%s: har holatning matni bor",
    (_nom, xabarlar) => {
      const director = (xabarlar as { director: Record<string, string> }).director;
      for (const holat of HOLATLAR) {
        expect(director[`vaDay_${holat}`], `vaDay_${holat} yo'q`).toBeTruthy();
      }
    },
  );

  test("QUYI CHEGARA: xarita haqiqatan o'qildi", () => {
    // Bo'sh yoki buzilgan import bo'lsa yuqoridagi `.not.toBe` lar
    // TRIVIAL o'tardi.
    expect(Object.keys(KUN_TONE).sort()).toEqual([...HOLATLAR].sort());
  });
});
