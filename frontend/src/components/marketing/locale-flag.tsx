import type { MarketingLocale } from "@/components/marketing/locale-switcher";

/*
 * =============================================================================
 * TIL BAYROG'I — TANLANGAN TILGA QARAB O'ZGARADI (260819, ikkinchi tahrir).
 *
 * ⛔⛔ AVVALGI QAROR BEKOR QILINDI. Birinchi tahrirda bayroq BITTA edi va
 *     guruhning o'zida turardi; izohda «bayroq — DAVLAT belgisi, TIL
 *     belgisi emas, shuning uchun rus tili yonida rus bayrog'i xato
 *     bo'lardi» deb yozilgandi.
 *
 *     Foydalanuvchi buni sinab ko'rib RAD ETDI: «rus tanlansa bayroq
 *     o'zgarmayapti». Ya'ni tashrifchi bayroqni TIL ko'rsatkichi deb
 *     o'qiydi — u nazariy jihatdan qanday bo'lishidan qat'i nazar.
 *     Foydalanuvchi tajribasi nazariyadan ustun turadi.
 *
 * ⛔ EMOJI EMAS, INLINE SVG: Windows mintaqaviy indikator juftliklarini
 *    (`🇺🇿`, `🇷🇺`) bayroq qilib CHIZMAYDI — o'rniga «uz», «ru» yozuvi
 *    chiqadi. Bu Xromda o'lchandi, taxmin emas.
 *
 * ⛔ QATLAMLAR TARTIBI MUHIM (O'zbekiston): har `rect` o'zidan
 *    oldingisining ustki qismini yopadi va ochiq qolgan tasma qizil
 *    chiziqni beradi (12 → 8.1 → 7.9 → 3.9 → 3.8). Tartib buzilsa
 *    bayroq ham buziladi.
 *
 * ⛔ 12 ta yulduz ATAYIN yo'q: 24px kenglikda ular yarim pikseldan
 *    kichik bo'lib, faqat loyqalik qo'shardi. Yarim oy qoladi — u shu
 *    o'lchamda ham taniladi.
 * =============================================================================
 */

/** Bayroq — bitta uy: `uz-Cyrl` ham o'zbek bayrog'ini oladi. */
export function LocaleFlag({
  className,
  locale,
}: {
  className?: string;
  locale: MarketingLocale;
}) {
  const shared = {
    "aria-hidden": "true",
    className,
    focusable: "false",
    viewBox: "0 0 24 12",
    xmlns: "http://www.w3.org/2000/svg",
  } as const;

  if (locale === "ru") {
    return (
      <svg {...shared}>
        <rect fill="#FFFFFF" height="12" width="24" />
        <rect fill="#0039A6" height="8" width="24" y="4" />
        <rect fill="#D52B1E" height="4" width="24" y="8" />
      </svg>
    );
  }

  return (
    <svg {...shared}>
      <rect fill="#1EB53A" height="12" width="24" />
      <rect fill="#CE1126" height="8.1" width="24" />
      <rect fill="#FFFFFF" height="7.9" width="24" />
      <rect fill="#CE1126" height="3.9" width="24" />
      <rect fill="#0099B5" height="3.8" width="24" />
      <circle cx="4.1" cy="1.9" fill="#FFFFFF" r="1.25" />
      <circle cx="4.85" cy="1.9" fill="#0099B5" r="1.25" />
    </svg>
  );
}
