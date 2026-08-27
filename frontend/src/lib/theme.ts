"use client";

import { useSyncExternalStore } from "react";

/*
 * =============================================================================
 * TEMA QATLAMI — DOM haqiqat manbai, React nusxa EMAS (09-UI-SPEC §11.2).
 *
 * Uch tema: `light` (iliq baza) / `dark` (06:00 smenalar) / `sun` (kassir
 * ochiq havoda). ⛔ To'rtinchisi YO'Q, `auto` YO'Q — qurilma taxminlari
 * jimgina noto'g'ri natija beradi (D-15 falsafasi: brauzer tili ham hech
 * qachon so'ralmaydi).
 *
 * MANBA TARTIBI:
 *   1. `<head>` dagi bloklovchi inline skript (`[locale]/layout.tsx`)
 *      `localStorage["sbozor-theme"]` ni React'dan OLDIN `data-theme` ga
 *      ko'chiradi — FOUC yo'q.
 *   2. Bu modul FAQAT `document.documentElement.dataset.theme` ni o'qiydi —
 *      `localStorage` o'qish manbai EMAS, yozish nishoni xolos. DOM'ni
 *      yagona manba qilish 08-fazaning «ikkinchi haqiqat manbai» darsiga
 *      mos: atribut DevTools'dan o'zgartirilsa ham React ko'radi.
 *
 * ⛔ SERVERGA HECH QACHON YOZILMAYDI: tema — QURILMA xossasi (bitta kassir
 *    kunduzi telefonda, kechqurun ofis kompyuterida), til esa ODAMNIKI va
 *    profilda (D-15). `apiFetch` bu modulga import qilinmaydi.
 *
 * ⛔ `next-themes` QO'SHILMAYDI (G-motion-3(d) paket reyestri uni mexanik
 *    taqiqlaydi) — butun ehtiyoj: 1 atribut + 1 kalit + 1 obuna.
 *
 * Naqsh manbai: `components/stalls/stall-map.tsx:40-69` (`useIsDesktop`) —
 * DOM/brauzer TASHQI TIZIM bo'lgani uchun `useSyncExternalStore`; farq:
 * `matchMedia` o'rniga atribut, shuning uchun obuna `MutationObserver`.
 * =============================================================================
 */

/** ⛔ YOPIQ reyestr — G-motion-4(d) uch manbadan to'plam tengligini o'lchaydi. */
export const THEMES = ["light", "dark", "sun"] as const;

export type Theme = (typeof THEMES)[number];

/** `localStorage` kaliti — `<head>` skripti bilan BITTA literal (§11.2). */
export const THEME_STORAGE_KEY = "sbozor-theme";

function isTheme(value: unknown): value is Theme {
  return (THEMES as readonly unknown[]).includes(value);
}

/**
 * Joriy tema — DOM atributidan, reyestr validatsiyasi bilan.
 *
 * Noma'lum qiymat (qo'lda buzilgan atribut) va SSR — ikkalasi ham `light`:
 * bu HTML'dagi `data-theme="light"` standarti bilan AYNAN mos, ya'ni
 * gidratatsiya nomuvofiqligi tug'ilmaydi (T-09-01: ixtiyoriy satr temaga
 * aylana olmaydi).
 */
export function readTheme(): Theme {
  if (typeof document === "undefined") return "light";
  const value = document.documentElement.dataset.theme;
  return isTheme(value) ? value : "light";
}

/**
 * Temani almashtiradi: DOM atributi (ko'rinish) + `localStorage` (saqlash).
 *
 * ⛔ `localStorage` bloklangan brauzerda (privacy rejimi, korporativ siyosat)
 * istisno OTMAYDI: ekran baribir almashadi, faqat tanlov keyingi sessiyada
 * tiklanmaydi — bu bezak darajasidagi yo'qotish, oqim to'xtamaydi.
 */
export function setTheme(next: Theme): void {
  document.documentElement.dataset.theme = next;
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, next);
  } catch {
    // Saqlash imkonsiz — jim davom etamiz (yuqoridagi izoh).
  }
}

function subscribeToTheme(onChange: () => void): () => void {
  const observer = new MutationObserver(onChange);
  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["data-theme"],
  });
  return () => observer.disconnect();
}

/**
 * Joriy temaga REAKTIV obuna.
 *
 * ⛔ Hook DOM'dan O'QIYDI, o'z `useState` nusxasini YARATMAYDI — aks holda
 * tugma «yoqilgan» ko'rinib, ekran o'zgarmasdi (SPEC §11.2 uchinchi qator).
 * `getServerSnapshot` — `"light"`, HTML standarti bilan mos.
 */
export function useTheme(): Theme {
  return useSyncExternalStore(subscribeToTheme, readTheme, () => "light");
}
