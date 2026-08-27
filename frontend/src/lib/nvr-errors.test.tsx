/**
 * Xato taksonomiyasi va AUTH-XATO QULFI (UI-SPEC §7.3, §4.4).
 *
 * NEGA BU FAYL: `nvr-errors.ts` bitta jadval bo'lib ko'rinadi va uni
 * "aniq to'g'ri" deb o'tkazib yuborish oson. Lekin jadvalning uchta
 * ustuni UI'da UCH BOSHQA qarorni boshqaradi va ularning ikkitasi
 * xavfsizlik/ishonchlilik oqibatiga ega:
 *
 *   `retrySafe: false` -> tugma RENDER QILINMAYDI. Noto'g'ri `true`
 *     admin uchun "yana bosing" taklifiga aylanadi va NVR hisobi
 *     ~5 urinishdan keyin 30 daqiqaga qulflanadi (D-03).
 *
 *   `authLocking: true` -> ikkala tugma bloklanadi. Noto'g'ri `false`
 *     o'sha qulflanishning ikkinchi yo'li.
 *
 * `tone` esa faqat ko'rinish, lekin u ham `danger`/`warning` chegarasini
 * qulflaydi: "sozlamada tuzatiladi" xatosini qizil ko'rsatish adminni
 * qo'ng'iroq qilishga majburlardi.
 *
 * Backend bilan TO'LIQLIK darvozasi bu yerda EMAS — u
 * `scripts/error-codes.test.mjs` (G-1/G-2) da, chunki u backend faylini
 * o'qiydi va vitest muhitida bu keraksiz bog'lanish bo'lardi.
 */
import { act, renderHook } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import {
  AUTH_LOCKING_CODES,
  ERROR_DETAIL_KEYS,
  MAX_RAW_DETAIL_CHARS,
  NVR_ERROR_CODES,
  isNvrErrorCode,
  nvrErrorView,
  pickErrorDetail,
  rawDetailText,
} from "@/lib/nvr-errors";
import { useNvrAuthLock } from "@/lib/use-nvr-auth-lock";

describe("nvrErrorView — UI-SPEC §7.3 jadvali", () => {
  test("rekvizit xatosi: danger + retry YO'Q + qulf", () => {
    const view = nvrErrorView("nvr_bad_credentials");

    expect(view).not.toBeNull();
    expect(view?.tone).toBe("danger");
    expect(view?.retrySafe).toBe(false);
    expect(view?.authLocking).toBe(true);
  });

  test("soat farqi: warning + retry XAVFSIZ + qulf yo'q", () => {
    const view = nvrErrorView("nvr_clock_drift");

    expect(view?.tone).toBe("warning");
    expect(view?.retrySafe).toBe(true);
    expect(view?.authLocking).toBe(false);
  });

  test("sessiya limiti: warning + retry xavfsiz", () => {
    const view = nvrErrorView("nvr_stream_limit");

    expect(view?.tone).toBe("warning");
    expect(view?.retrySafe).toBe(true);
  });

  test("qo'llab-quvvatlanmaydigan qurilma: retry MA'NOSIZ", () => {
    // `authLocking` YO'Q, lekin `retrySafe` ham `false` — ikkisi
    // MUSTAQIL: bu yerda qayta urinish hech narsani o'zgartirmaydi.
    const view = nvrErrorView("device_not_supported");

    expect(view?.retrySafe).toBe(false);
    expect(view?.authLocking).toBe(false);
  });

  test("har kod uchun sabab VA tuzatish kaliti qaytariladi (D-02)", () => {
    for (const code of NVR_ERROR_CODES) {
      const view = nvrErrorView(code);

      expect(view?.causeKey).toBe(`cameras.errorCause.${code}`);
      expect(view?.fixKey).toBe(`cameras.errorFix.${code}`);
    }
    // Nazorat: bo'sh ro'yxat ustidagi sikl ham yashil bo'lardi.
    expect(NVR_ERROR_CODES.length).toBe(12);
  });

  test("noma'lum kod `null` qaytaradi — chaqiruvchi errors.generic ga tushadi", () => {
    expect(nvrErrorView("nvr_something_new")).toBeNull();
    expect(nvrErrorView(null)).toBeNull();
    expect(nvrErrorView(undefined)).toBeNull();
    expect(isNvrErrorCode("nvr_something_new")).toBe(false);
  });

  test("AUTH_LOCKING_CODES aynan uchta va jadvaldan HOSIL bo'ladi", () => {
    expect([...AUTH_LOCKING_CODES].sort()).toEqual([
      "nvr_account_locked",
      "nvr_bad_credentials",
      "nvr_user_no_permission",
    ]);
  });
});

describe("error_detail — UI FAQAT ruxsat etilgan kalitlarni chizadi (§7.4)", () => {
  test("noma'lum kalit tashlanadi, ma'lumi qoladi", () => {
    const picked = pickErrorDetail({
      drift_seconds: 312,
      unlock_at: "2026-08-03T10:00:00Z",
      // Backend buni yozmaydi (`NvrError` konstruktori rad etadi), lekin
      // UI baribir ko'r-ko'rona chizmasligi kerak — T-02-99 ning takrori.
      password: "hunter2",
      internal_sql: "SELECT 1",
    });

    expect(picked).toEqual({
      drift_seconds: 312,
      unlock_at: "2026-08-03T10:00:00Z",
    });
    expect(Object.keys(picked)).not.toContain("password");
  });

  test("`null` detali bo'sh obyekt beradi", () => {
    expect(pickErrorDetail(null)).toEqual({});
    expect(pickErrorDetail(undefined)).toEqual({});
  });

  test("ro'yxat backenddagi bilan bir xil sakkizta kalit", () => {
    expect(ERROR_DETAIL_KEYS.length).toBe(8);
  });
});

describe("rawDetailText — `<details>` mazmuni", () => {
  test("xom javob yo'q bo'lsa `null` — bo'sh <details> chizilmaydi", () => {
    expect(rawDetailText(null)).toBeNull();
    expect(rawDetailText({ drift_seconds: 1 })).toBeNull();
    expect(rawDetailText({ raw: "" })).toBeNull();
  });

  test("uzun javob 2000 belgidan kesiladi", () => {
    const long = "x".repeat(MAX_RAW_DETAIL_CHARS + 500);
    const out = rawDetailText({ raw: long });

    expect(out).not.toBeNull();
    expect(out).toHaveLength(MAX_RAW_DETAIL_CHARS + 1); // + kesish belgisi
    expect(out?.endsWith("…")).toBe(true);
  });
});

/*
 * =============================================================================
 * AUTH QULFI — UI-SPEC §4.4.
 *
 * Har da'vo AYNAN bitta rad etilgan muqobilga mos keladi: vaqt bo'yicha
 * ochilish, tugma bilan ochilish va "rekvizitga tegish" (qiymat
 * o'zgarmasdan). Uchalasi ham qulflanishni QAYTA TUG'DIRADIGAN yo'l.
 * =============================================================================
 */
describe("useNvrAuthLock — qulf faqat rekvizit qiymati o'zgarganda ochiladi", () => {
  test("auth-qulflovchi kod qulfni yoqadi", () => {
    const { result } = renderHook(() => useNvrAuthLock());

    expect(result.current.authLocked).toBe(false);
    act(() => result.current.lock("nvr_bad_credentials"));

    expect(result.current.authLocked).toBe(true);
    expect(result.current.lockedCode).toBe("nvr_bad_credentials");
  });

  test("qulflamaydigan kod e'tiborsiz qoldiriladi", () => {
    const { result } = renderHook(() => useNvrAuthLock());

    act(() => result.current.lock("nvr_clock_drift"));
    act(() => result.current.lock("noma'lum_kod"));
    act(() => result.current.lock(null));

    expect(result.current.authLocked).toBe(false);
  });

  test("rekvizit qiymati o'zgarganda ochiladi", () => {
    const { result } = renderHook(() => useNvrAuthLock());

    act(() => result.current.lock("nvr_bad_credentials"));
    act(() => result.current.unlockOnCredentialChange());

    expect(result.current.authLocked).toBe(false);
  });

  test("`nvr_account_locked` da IKKALA shart ham talab qilinadi", () => {
    const { result } = renderHook(() => useNvrAuthLock());

    const future = new Date(Date.now() + 30 * 60_000).toISOString();
    act(() => result.current.lock("nvr_account_locked", { unlock_at: future }));

    // Rekvizit o'zgardi, LEKIN qulf muddati o'tmagan -> qulf turadi.
    act(() => result.current.unlockOnCredentialChange());
    expect(result.current.authLocked).toBe(true);
    expect(result.current.unlockAt).toBe(future);

    // Muddat o'tgan holat: endi rekvizit o'zgarishi qulfni ochadi.
    const past = new Date(Date.now() - 60_000).toISOString();
    act(() => result.current.lock("nvr_account_locked", { unlock_at: past }));
    act(() => result.current.unlockOnCredentialChange());
    expect(result.current.authLocked).toBe(false);
  });

  test("buzuq `unlock_at` qulfni OCHMAYDI (fail-closed)", () => {
    const { result } = renderHook(() => useNvrAuthLock());

    act(() =>
      result.current.lock("nvr_account_locked", { unlock_at: "ertaga" }),
    );
    act(() => result.current.unlockOnCredentialChange());

    expect(result.current.authLocked).toBe(true);
  });

  test("`reset()` yangi forma uchun qulfni tozalaydi", () => {
    const { result } = renderHook(() => useNvrAuthLock());

    act(() => result.current.lock("nvr_user_no_permission"));
    act(() => result.current.reset());

    expect(result.current.authLocked).toBe(false);
    expect(result.current.lockedCode).toBeNull();
  });
});
