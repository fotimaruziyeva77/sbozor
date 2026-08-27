"use client";

import { useEffect, useRef } from "react";
import type { HTMLAttributes, Ref } from "react";

/*
 * =============================================================================
 * VENDORED go2rtc PLEYERINING O'RAMASI (UI-SPEC §1.4.1, §8.4, §12.4).
 *
 * ⚠ ANALOG YO'Q (03-PATTERNS §4.5): bu kodbazada video, `<video>`
 *   elementi yoki WebRTC komponenti UMUMAN yo'q edi. Dialog qobig'i
 *   `ui/dialog.tsx` dan keladi, oqim komponenti esa YANGI SHAKL.
 *
 * ⚠ SKRIPT O'Z ORIGINIMIZDAN YUKLANADI — go2rtc'dan RUNTIME'DA EMAS.
 *   D-11 go2rtc'ning HTTP yuzasini foydalanuvchiga ochishni taqiqlaydi
 *   (GHSA-wwww-5h25-jf98, CVSS 9.1 — o'sha yuzadagi manba sxemasi
 *   konteynerda ixtiyoriy buyruq bajaradi). Statik JS uchun yo'l ochish
 *   nginx allow-list'iga yana bitta yozuv qo'shardi va allow-list qancha
 *   uzun bo'lsa, u shunchalik DRIFT qiladi — ya'ni «faqat bitta fayl»
 *   deb ochilgan yo'l ertaga butun katalogni ochadi. Fayl repozitoriyada
 *   yashaydi, SHA-256 bilan qulflangan (G-7) va uning bog'liqligi ham
 *   vendored.
 *
 * ⚠ WEB-KOMPONENTNING NOMI VA SOZLAMALARI FAYLDAN O'QILDI, TAXMIN
 *   QILINMADI: `video-stream.js` ning oxirgi qatori elementni
 *   `video-stream` nomi bilan ro'yxatga oladi va uning butun mantiqi
 *   qo'shni `video-rtc.js` da (`VideoRTC`). Sozlash ATRIBUT orqali emas,
 *   JS XUSUSIYATLARI orqali bo'ladi (`observedAttributes` e'lon
 *   qilinmagan) — shuning uchun bu o'rama elementga `ref` oladi.
 * =============================================================================
 */

/** Vendored pleyer ro'yxatga oladigan element nomi. */
export const LIVE_PLAYER_ELEMENT = "video-stream";

/**
 * Pleyer skripti — BIZNING originimizdagi statik yo'l.
 *
 * Next `public/` katalogini shu prefiks bilan xizmat qiladi, ya'ni bu
 * yo'l hech qanday proksilash qoidasiga muhtoj emas.
 */
export const LIVE_PLAYER_SCRIPT_SRC = "/vendor/go2rtc/video-stream.js";

/**
 * Pleyerning ikki MAJBURIY sozlamasi (UI-SPEC §14.2 ko'rigi, 03-08).
 *
 * ⚠ 1. TASHQI STUN SERVERLARI O'CHIRILADI. `VideoRTC` ning standart
 *      `pcConfig` i uchinchi tomon STUN xizmatlariga murojaat qiladi.
 *      Bu kod bajarish xavfi EMAS, lekin bozor tarmog'idan tashqariga
 *      chiqadigan KO'RINMAS BOG'LIQLIK: har jonli ko'rish bozorning
 *      tarmoq manzillarini begona xizmatga yuborardi. Tunnel ichidagi
 *      topologiyada tashqi STUN baribir foyda bermaydi — nomzodlar
 *      bir xil tarmoqda.
 *
 * ⚠ 2. AUDIO SO'RALMAYDI. Standart qiymat ovozni ham qamraydi. Bu
 *      mahsulotda ovoz talabi YO'Q, bozordan yozilgan ovoz esa
 *      MAQSADSIZ yig'ilgan shaxsiy ma'lumot bo'lardi; ustiga u NVR
 *      ning bitreyt byudjetini bekorga yeydi (§12.4 — oqim ovozsiz).
 *
 * Funksiya EKSPORT QILINADI va alohida test bilan o'lchanadi: ikkala
 * sozlama ham «izohda yozilgan qoida» emas, TEKSHIRILADIGAN da'vo
 * bo'lishi kerak.
 */
export type PlayerPolicyTarget = {
  media?: string;
  pcConfig?: RTCConfiguration;
  background?: boolean;
  visibilityCheck?: boolean;
};

export function applyPlayerPolicy(target: PlayerPolicyTarget): void {
  // 1. Faqat video — ovoz hech qachon so'ralmaydi.
  target.media = "video";

  // 2. Tashqi ICE xizmatlari yo'q: ro'yxat ATAYIN bo'sh.
  target.pcConfig = { bundlePolicy: "max-bundle", iceServers: [] };

  /*
   * 3. Ko'rinmayotgan oqim ushlab turilmaydi. Pleyerning standart
   *    xulqi allaqachon shunday, lekin u kelajakdagi versiyada
   *    o'zgarishi mumkin va NVR bitreyt byudjeti buni kechirmaydi.
   */
  target.background = false;
  target.visibilityCheck = true;
}

/**
 * Vendored GUI qobig'ining holat matni -> transport nomi (§8.4).
 *
 * Qobiq `.mode` bo'lagiga `RTC` / `MSE` / `HLS` / `MP4` / `MJPEG` yozadi
 * (`video-stream.js`). `loading` va `error` transport EMAS — birinchisi
 * oraliq holat, ikkinchisi nosozlik.
 */
export function transportOf(mode: string): string | null {
  const value = mode.trim().toUpperCase();
  if (value === "RTC") return "WebRTC";
  if (value === "MSE" || value === "HLS" || value === "MP4" || value === "MJPEG") {
    return value;
  }
  return null;
}

/** Qobiq nosozlikni shu matn bilan bildiradi. */
export function isPlayerFailure(mode: string): boolean {
  return mode.trim().toLowerCase() === "error";
}

/* --- Skriptni bir marta yuklash ------------------------------------------- */

let scriptLoad: Promise<void> | null = null;

/**
 * Pleyer skriptini BIR MARTA yuklaydi.
 *
 * Promise modul darajasida keshlanadi: ikki dialog ketma-ket ochilganda
 * ikkinchi `<script>` qo'shilishi elementni qayta ro'yxatga olishga
 * urinib xato berardi (`customElements.define` takrorlanmaydi).
 */
export function loadLivePlayerScript(): Promise<void> {
  if (typeof window === "undefined") return Promise.resolve();
  if (window.customElements?.get(LIVE_PLAYER_ELEMENT) !== undefined) {
    return Promise.resolve();
  }
  if (scriptLoad !== null) return scriptLoad;

  scriptLoad = new Promise<void>((resolve, reject) => {
    const script = document.createElement("script");
    // ES modul: vendored fayl `import` bilan boshlanadi.
    script.type = "module";
    script.src = LIVE_PLAYER_SCRIPT_SRC;
    script.addEventListener("load", () => resolve());
    script.addEventListener("error", () => {
      // Qayta urinish mumkin bo'lishi uchun kesh tozalanadi.
      scriptLoad = null;
      reject(new Error("live_player_script_unavailable"));
    });
    document.head.appendChild(script);
  });

  return scriptLoad;
}

/* --- Komponent ------------------------------------------------------------ */

/** Vendored elementning bizga kerak bo'lgan yuzasi. */
type PlayerElement = HTMLElement &
  PlayerPolicyTarget & {
    src?: string;
    video?: HTMLVideoElement;
  };

export type LivePlayerProps = {
  className?: string;
  onError: () => void;
  onReady: () => void;
  onTransport: (transport: string) => void;
  /** Token javobidagi OPAQUE manzil — ekranga hech qachon chiqmaydi. */
  url: string;
};

export function LivePlayer({
  className,
  onError,
  onReady,
  onTransport,
  url,
}: LivePlayerProps) {
  const hostRef = useRef<PlayerElement | null>(null);

  /*
   * Callback'lar `ref` da saqlanadi: ular har renderda yangi havola
   * bo'ladi va effekt bog'liqligiga qo'yilsa oqim har renderda qayta
   * ulanardi — WebRTC'da bu har safar yangi RTSP sessiyasi degani.
   */
  const handlers = useRef({ onError, onReady, onTransport });

  /*
   * ⚠ `ref` RENDER PAYTIDA EMAS, EFFEKTDA yangilanadi
   *   (`react-hooks/refs`). Bu 03-08/03-09 dagi bilan bir xil sinf:
   *   React Compiler shaklni dikta qiladi va natija to'g'riroq
   *   bo'ladi — boshlang'ich qiymat `useRef` ning o'zida, ya'ni
   *   birinchi kadrda ham callback'lar joyida turadi.
   */
  useEffect(() => {
    handlers.current = { onError, onReady, onTransport };
  });

  useEffect(() => {
    const host = hostRef.current;
    if (host === null) return;

    let cancelled = false;
    let observer: MutationObserver | null = null;
    let video: HTMLVideoElement | null = null;

    const onPlaying = (): void => handlers.current.onReady();

    void loadLivePlayerScript()
      .then(() => {
        if (cancelled) return;

        // ⚠ IKKI MAJBURIY SOZLAMA — `src` BERILISHIDAN OLDIN.
        applyPlayerPolicy(host);

        /*
         * `src` setteri ulanishni BOSHLAYDI (`video-rtc.js`), shuning
         * uchun u eng oxirida qo'yiladi.
         */
        host.src = url;

        video = host.video ?? host.querySelector("video");
        if (video !== null) {
          /*
           * Jonli oqimda o'tkazish va tezlik ma'nosiz — qobiq yoqib
           * qo'ygan native boshqaruvlar o'chiriladi (§12.4). Element
           * fokus tartibiga ham kirmaydi: u interaktiv emas.
           */
          video.controls = false;
          video.tabIndex = -1;
          video.muted = true;
          video.playsInline = true;
          video.autoplay = true;
          video.addEventListener("playing", onPlaying);
        }

        /*
         * Transport qobiqning O'Z holat bo'lagidan o'qiladi (§8.4).
         * `video-rtc.js` ning ichki holatiga qadalish keyingi
         * versiyada jimgina uzilardi; `.mode` esa qobiqning e'lon
         * qilingan GUI yuzasi.
         */
        const mode = host.querySelector<HTMLElement>(".mode");
        if (mode !== null) {
          observer = new MutationObserver(() => {
            const text = mode.textContent ?? "";
            if (isPlayerFailure(text)) {
              handlers.current.onError();
              return;
            }
            const transport = transportOf(text);
            if (transport !== null) handlers.current.onTransport(transport);
          });
          observer.observe(mode, { characterData: true, childList: true, subtree: true });
        }
      })
      .catch(() => {
        if (!cancelled) handlers.current.onError();
      });

    return () => {
      cancelled = true;
      observer?.disconnect();
      video?.removeEventListener("playing", onPlaying);
    };
  }, [url]);

  /*
   * ⚠ ELEMENT DOM'DAN CHIQARILGANDA OQIM TO'XTAYDI: `video-rtc.js`
   *   ning `disconnectedCallback` i WebSocket va peer ulanishini
   *   yopadi. Ya'ni «dialog yopilishi = oqim to'xtashi» kafolati
   *   unmount orqali beriladi va qo'shimcha imperativ tozalash
   *   TALAB QILINMAYDI.
   */
  return <video-stream class={className} ref={hostRef} />;
}

declare module "react" {
  namespace JSX {
    interface IntrinsicElements {
      /*
       * Vendored web-komponent. Nomi `LIVE_PLAYER_ELEMENT` bilan bir
       * xil bo'lishi SHART — interfeys kaliti literal bo'lishi kerak,
       * shuning uchun konstantani bu yerda ishlatib bo'lmaydi.
       *
       * `class` (React'dagi `className` emas): bu maxsus element va
       * React unga atributni to'g'ridan-to'g'ri yozadi.
       */
      "video-stream": HTMLAttributes<HTMLElement> & {
        class?: string;
        ref?: Ref<PlayerElement>;
      };
    }
  }
}
