"use client";

import { useEffect } from "react";

/*
 * =============================================================================
 * SILLIQ ANKER SILJISHI — «juda tez va qo'pol» ning tuzatmasi (260819).
 *
 * ⛔⛔ MUAMMO FOYDALANUVCHIDAN KELDI: «menudagi linklar ustiga bosilsa
 *     juda ham tez va qo'pol bormoqda ko'rsatilgan joyga».
 *
 *     Sabab MEXANIK va u brauzerda: `scroll-behavior: smooth` ning
 *     davomiyligi MASOFAGA BOG'LIQ EMAS — Chrome uni ~500ms qilib
 *     belgilaydi. «Muammo» ga 1000px siljish yoqimli chiqadi, «Demo» ga
 *     3500px siljish esa o'sha 500ms ichida sahifani ko'z ilg'amas
 *     tezlikda uchirib yuboradi. Aynan shu «qo'pollik» sezilgan.
 *
 *     Shuning uchun siljishni O'ZIMIZ chizamiz: davomiylik masofadan
 *     hisoblanadi (450…1100ms) va egri chiziq ikki tomondan yumshoq
 *     (`easeInOutCubic`) — boshlanishi ham, tugashi ham silliq.
 *
 * ⛔ DELEGATSIYA, har havolaga `onClick` EMAS. Sababi ikkita:
 *   1. Menyu (`nav-menu.tsx`) SERVER COMPONENT bo'lib qoladi — u LCP
 *      yo'lida va uni klientga bog'lash SC#5 xavfini tug'dirardi.
 *   2. Sahifada ankerlar menyudan TASHQARIDA ham bor («Demo so'rang»
 *      tugmasi, futer havolalari). Delegatsiya hammasini bir joyda
 *      qamrab oladi — kelajakda qo'shilgani ham o'zidan ishlaydi.
 *
 * ⛔ `prefers-reduced-motion` — UMUMAN ARALASHMAYMIZ: hodisa to'xtatilmaydi
 *    va brauzer o'zining darhol sakrashini qiladi. Global CSS bloki
 *    `scroll-behavior: auto !important` ni allaqachon o'rnatgan; bu yerda
 *    rAF bilan «sekin» qilish o'sha talabni BUZGAN bo'lardi.
 *
 * ⛔ FOKUS KO'CHIRILADI (§15.7 ruhida): siljish tugagach nishon element
 *    fokus oladi, aks holda klaviatura foydalanuvchisi vizual jihatdan
 *    yangi bo'limda, tab-tartibida esa hali eski joyda qolardi. `tabindex`
 *    vaqtinchalik qo'yiladi va olib tashlanadi — DOM'da iz qolmaydi.
 *
 * ⛔ TARIX YOZUVI `pushState` bilan: «orqaga» tugmasi oldingi bo'limga
 *    qaytaradi. `location.hash = …` ISHLATILMAYDI — u brauzerning O'Z
 *    sakrashini qo'zg'atib, endigina chizgan animatsiyamizni bekor qilardi.
 * =============================================================================
 */

/** Boshi ham, oxiri ham yumshoq — uzoq masofada eng tinch his beradi. */
function easeInOutCubic(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2;
}

/** Sarlavha balandligi + nafas oladigan bo'shliq (px). */
const ANCHOR_OFFSET = 24;

export function SmoothAnchor() {
  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
    let frame = 0;

    function onClick(event: MouseEvent) {
      // Modifikatorli bosish — yangi oyna/tab; aralashmaymiz.
      if (
        event.defaultPrevented ||
        event.button !== 0 ||
        event.metaKey ||
        event.ctrlKey ||
        event.shiftKey ||
        event.altKey
      ) {
        return;
      }
      const link = (event.target as Element | null)?.closest?.("a");
      if (!(link instanceof HTMLAnchorElement) || link.target === "_blank") {
        return;
      }
      const href = link.getAttribute("href");
      if (!href || !href.startsWith("#") || href === "#") return;

      const target = document.getElementById(href.slice(1));
      if (!target) return;

      // Harakat kamaytirilgan bo'lsa — brauzerning o'z xatti-harakati.
      if (reduced.matches) return;

      event.preventDefault();

      const start = window.scrollY;
      const max = document.documentElement.scrollHeight - window.innerHeight;
      const end = Math.min(
        max,
        Math.max(0, start + target.getBoundingClientRect().top - ANCHOR_OFFSET),
      );
      const delta = end - start;

      const settle = () => {
        history.pushState(null, "", href);
        // Fokusni ko'chirish — `preventScroll` busiz brauzer yana sakrardi.
        const hadTabIndex = target.hasAttribute("tabindex");
        if (!hadTabIndex) target.setAttribute("tabindex", "-1");
        target.focus({ preventScroll: true });
        if (!hadTabIndex) target.removeAttribute("tabindex");
      };

      if (Math.abs(delta) < 2) {
        settle();
        return;
      }

      /*
       * ⛔ Davomiylik MASOFADAN — bu butun tuzatmaning mag'zi. 450ms
       *    qisqa siljish uchun, 1100ms esa sahifa bo'yi uchun. Oraliq
       *    chiziqli: har 1000px ≈ +300ms.
       */
      const duration = Math.min(1100, Math.max(450, Math.abs(delta) * 0.3));
      const began = performance.now();

      cancelAnimationFrame(frame);
      const step = (now: number) => {
        const progress = Math.min(1, (now - began) / duration);
        window.scrollTo(0, start + delta * easeInOutCubic(progress));
        if (progress < 1) {
          frame = requestAnimationFrame(step);
        } else {
          settle();
        }
      };
      frame = requestAnimationFrame(step);
    }

    document.addEventListener("click", onClick);
    return () => {
      cancelAnimationFrame(frame);
      document.removeEventListener("click", onClick);
    };
  }, []);

  return null;
}
