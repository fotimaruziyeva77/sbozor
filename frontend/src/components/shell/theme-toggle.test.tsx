/**
 * `ThemeToggle` + `lib/theme.ts` — tema qatlamining xulq shartnomasi (09-03).
 *
 * Nima qulflanadi (09-03-PLAN Task 2 `<behavior>`):
 *   1. Reyestr AYNAN uch a'zo: `light` / `dark` / `sun` — to'rtinchisi yo'q,
 *      `auto` yo'q (09-UI-SPEC §11.1 — yopiq reyestr).
 *   2. `readTheme()` DOM atributidan o'qiydi (`documentElement.dataset.theme`);
 *      noma'lum qiymatda `light` qaytaradi — `localStorage` dagi ixtiyoriy
 *      satr temaga aylana OLMAYDI (T-09-01 mitigatsiyasi).
 *   3. `setTheme(next)` DOM atributini VA `localStorage["sbozor-theme"]` ni
 *      yozadi; `localStorage` bloklangan brauzerda istisno OTMAYDI (ekran
 *      baribir almashadi, faqat tanlov saqlanmaydi).
 *   4. `ThemeToggle` — `LocaleSwitcher` naqshi: `role="group"` + `aria-label`,
 *      faol tugmada `aria-current="true"`.
 *   5. Tugma bosilganda `data-theme` o'zgaradi va faol indikator yangi
 *      tugmaga KO'CHADI — hook DOM'dan o'qiydi, o'z nusxasini yaratmaydi
 *      (aks holda tugma «yoqilgan» ko'rinib, ekran o'zgarmasdi).
 *   6. Tema o'zgarishida toast CHIQMAYDI (09-UI-SPEC §15) — natija
 *      ekranning o'zida ko'rinadi.
 *
 * DIQQAT: tema — QURILMA xossasi (D-15 farqi: til — profilda). Serverga
 * yozuv YO'Q — bu testda tarmoq mock'i yo'qligi ham o'sha shartnomaning
 * bir qismi: `ThemeToggle` `apiFetch` import qilsa, jsdom'da fetch yo'qligi
 * uni shu yerda fosh qilardi.
 */
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import messages from "../../../messages/uz-Latn.json";
import { ThemeToggle } from "@/components/shell/theme-toggle";
import { readTheme, setTheme, THEME_STORAGE_KEY, THEMES } from "@/lib/theme";

/*
 * Sonner josuslanadi, chaqirilmasligi o'lchanadi: kimdir keyin
 * `toast.success("...")` qo'shsa, bu mock uni USHLAYDI (6-shart).
 */
const toastSpy = vi.hoisted(() => ({
  success: vi.fn(),
  error: vi.fn(),
  info: vi.fn(),
}));
vi.mock("sonner", () => ({ toast: toastSpy }));

/** uz-Latn yorliqlar — test AYNAN shu katalogni yuklaydi (SPEC §14.1). */
const LABEL_GROUP = "Ko'rinish";
const LABEL_LIGHT = "Yorug'";
const LABEL_DARK = "Tungi";
const LABEL_SUN = "Quyosh ostida";

function renderToggle(): void {
  render(
    <NextIntlClientProvider locale="uz-Latn" messages={messages}>
      <ThemeToggle />
    </NextIntlClientProvider>,
  );
}

/** Faol (aria-current="true") tugmaning matni. */
function activeButtonName(): string | null {
  const group = screen.getByRole("group", { name: LABEL_GROUP });
  const active = group.querySelector('[aria-current="true"]');
  return active?.textContent ?? null;
}

beforeEach(() => {
  vi.resetAllMocks();
});

afterEach(() => {
  cleanup();
  /*
   * Har testdan keyin DOM atributi VA saqlangan tanlov tozalanadi —
   * `documentElement` jsdom'da testlar orasida SAQLANIB QOLADI va tozalovsiz
   * bir testning temasi keyingisiga sizib o'tardi (09-03-PLAN Task 2 sharti).
   */
  delete document.documentElement.dataset.theme;
  window.localStorage.clear();
});

describe("lib/theme.ts — reyestr, o'qish, yozish", () => {
  test("THEMES reyestri AYNAN uch a'zo: light, dark, sun (auto YO'Q)", () => {
    expect([...THEMES]).toEqual(["light", "dark", "sun"]);
  });

  test("readTheme() DOM atributidan o'qiydi", () => {
    document.documentElement.dataset.theme = "sun";
    expect(readTheme()).toBe("sun");
  });

  test("readTheme() noma'lum qiymatda 'light' qaytaradi (reyestr validatsiyasi)", () => {
    document.documentElement.dataset.theme = "hacker-theme";
    expect(readTheme()).toBe("light");
  });

  test("readTheme() atribut umuman yo'q bo'lsa 'light'", () => {
    expect(readTheme()).toBe("light");
  });

  test("setTheme('dark') DOM atributini VA localStorage'ni yozadi", () => {
    setTheme("dark");
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
  });

  test("localStorage bloklangan bo'lsa setTheme istisno OTMAYDI, ekran baribir almashadi", () => {
    const blocked = vi
      .spyOn(Storage.prototype, "setItem")
      .mockImplementation(() => {
        throw new Error("localStorage bloklangan (privacy rejimi)");
      });

    expect(() => setTheme("sun")).not.toThrow();
    // Saqlash yiqildi, lekin DOM (ya'ni ko'rinish) BARIBIR almashdi.
    expect(document.documentElement.dataset.theme).toBe("sun");

    blocked.mockRestore();
  });
});

describe("ThemeToggle — LocaleSwitcher naqshidagi uch tugmali guruh", () => {
  test("uchta tugma, konteynerda role=group va aria-label", () => {
    renderToggle();

    const group = screen.getByRole("group", { name: LABEL_GROUP });
    expect(group).toBeInTheDocument();
    expect(screen.getByRole("button", { name: LABEL_LIGHT })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: LABEL_DARK })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: LABEL_SUN })).toBeInTheDocument();
  });

  test("standart holatda faol tugma — Yorug' (aria-current='true')", () => {
    renderToggle();
    expect(activeButtonName()).toBe(LABEL_LIGHT);
  });

  test("Tungi bosilganda data-theme='dark' bo'ladi va indikator KO'CHADI", async () => {
    const user = userEvent.setup();
    renderToggle();

    await user.click(screen.getByRole("button", { name: LABEL_DARK }));

    expect(document.documentElement.dataset.theme).toBe("dark");
    // Hook DOM'dan o'qiydi (MutationObserver mikrotaskda) — kutish shart.
    await waitFor(() => {
      expect(activeButtonName()).toBe(LABEL_DARK);
    });
  });

  test("tanlov localStorage['sbozor-theme'] ga yoziladi", async () => {
    const user = userEvent.setup();
    renderToggle();

    await user.click(screen.getByRole("button", { name: LABEL_SUN }));

    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("sun");
  });

  test("tashqi data-theme o'zgarishi ham tugmada aks etadi (DOM — yagona haqiqat manbai)", async () => {
    renderToggle();

    // DevTools yoki kelajakdagi ikkinchi iste'molchi atributni to'g'ridan
    // to'g'ri o'zgartirdi — React nusxasi bo'lsa, tugma eskirgan qolardi.
    document.documentElement.dataset.theme = "sun";

    await waitFor(() => {
      expect(activeButtonName()).toBe(LABEL_SUN);
    });
  });

  test("tema o'zgarishida toast CHIQMAYDI", async () => {
    const user = userEvent.setup();
    renderToggle();

    await user.click(screen.getByRole("button", { name: LABEL_DARK }));
    await waitFor(() => {
      expect(activeButtonName()).toBe(LABEL_DARK);
    });

    expect(toastSpy.success).not.toHaveBeenCalled();
    expect(toastSpy.error).not.toHaveBeenCalled();
    expect(toastSpy.info).not.toHaveBeenCalled();
  });
});
