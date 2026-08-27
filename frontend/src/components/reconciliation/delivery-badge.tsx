"use client";

import { Check, Clock, Link2Off, Send, TriangleAlert } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useTranslations } from "next-intl";

import { Badge } from "@/components/ui/badge";
import type { BadgeTone } from "@/components/ui/badge";
import type { DeliveryStateValue } from "@/lib/api-types";
import { isDeliveryState } from "@/lib/reconciliation-queries";

/*
 * =============================================================================
 * XABAR YETKAZILISHI — 5 HOLAT, ⛔ 3 KANAL (WCAG 1.4.1).
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 1. MATN ⛔ ISBOTLANGANDAN ORTIQ DA'VO QILMAYDI
 * -----------------------------------------------------------------------
 * Bot API ning `sendMessage` javobi — `Message` obyekti (`message_id`,
 * `date`). ⛔ Yetkazilganlik yoki o'qilganlik KVITANSIYASI ⛔ UMUMAN
 * YO'Q. Ya'ni tizim bilishi mumkin bo'lgan yagona fakt: «Telegram
 * **200** qaytardi va `message_id` berdi».
 *
 * Shuning uchun matn ⛔ **«Telegram qabul qildi»** ma'nosini beradi va
 * uchta narsani ⛔ **DEMAYDI**:
 *
 *   «o'qildi» / «ko'rildi»  — bu ⛔ QABUL QILUVCHI haqidagi da'vo;
 *   yolg'iz «yetkazildi»     — ⛔ U HAM isbotlanmagan (Telegram
 *                              tasdiqlamaydi), faqat zaifroq shakli;
 *   ⛔ IKKI BELGILI IKONKA   — quyida, 2-band.
 *
 * ⛔ Nizoda (D-02) oshirilgan da'vo tizimni ⛔ ISBOTLAB BO'LMAYDIGAN
 *    gapga majburlardi va sotuvchi oldida uni ⛔ DALILSIZ qoldirardi.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 2. IKKI BELGILI TASDIQ IKONKASI ⛔ TAQIQLANADI
 * -----------------------------------------------------------------------
 * U — messenjerlarning ⛔ UNIVERSAL «O'QILDI» GLIFI. Matn rost gapirib
 * turib ⛔ IKONKA YOLG'ON GAPIRARDI, va ikonka kanali WCAG 1.4.1
 * bo'yicha matn bilan ⛔ TENG OG'IRLIKDA o'qiladi — ya'ni foydalanuvchi
 * matnni umuman o'qimasdan «o'qildi» degan xulosaga kelardi.
 *
 * ⛔ `delivered` uchun ⛔ BITTA belgi ishlatiladi va taqiq mexanik skan
 *    bilan o'lchanadi. ⚠ Taqiqlangan komponentning NOMI bu izohda
 *    LITERAL yozilmaydi — skan izohni koddan ajratsa ham, nusxa
 *    darvozani o'ziga qarshi qo'yish odati kodbazada ATAYIN rad etilgan
 *    (`badge.tsx:24-26` konvensiyasi).
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 3. `blocked` — MA'LUMOT, XATO ⛔ EMAS (D-22)
 * -----------------------------------------------------------------------
 * Sotuvchining botni bloklashi — uning ⛔ HUQUQI va u ⛔ QARZ UNDIRISH
 * JARAYONINING BIR QISMI, bozorning nosozligi emas. Shuning uchun:
 *
 *   ⛔ `tone="neutral"` — ⛔ `danger` EMAS: qizil rang direktorni
 *      «tizim buzildi» deb o'ylashga majburlardi va u ⛔ NOTO'G'RI
 *      ODAMGA (dasturchiga) murojaat qilardi, holbuki yagona foydali
 *      qadam — sotuvchi bilan BOSHQA YO'L bilan bog'lanish;
 *   ⛔ `role="alert"` ⛔ YO'Q — skrinrider foydalanuvchisiga uni
 *      SHOSHILINCH xato sifatida e'lon qilardi.
 *
 * ⛔ To'liq jumla va keyingi qadam — `delivery-list.tsx` da (yolg'iz
 *    nishon «texnik nosozlik» deb o'qilardi).
 *
 * -----------------------------------------------------------------------
 * ⛔ 4. NOMA'LUM QIYMAT YASHIRILMAYDI, ZAXIRA YORLIQ OLADI (04-10 darsi)
 * -----------------------------------------------------------------------
 * Sxema reyestr bilan qulflanmagan, ya'ni backend oltinchi a'zo qo'shsa
 * u BU YERGA yetib keladi. Qatorni chizmaslik uni ro'yxatdan JIMGINA
 * yo'qotardi — «bugun 12 ta xabar» degan YOLG'ON son qolardi.
 * =============================================================================
 */

type DeliveryView = { tone: BadgeTone; Icon: LucideIcon };

/**
 * Holat -> ko'rinish. ⛔ `Record<DeliveryStateValue, …>` ATAYIN: reyestrga
 * yangi a'zo qo'shilsa bu jadval `tsc` da qizaradi, ya'ni yangi holat
 * yorliqsiz va ikonkasiz ekranga chiqib keta olmaydi.
 */
const DELIVERY_VIEW: Record<DeliveryStateValue, DeliveryView> = {
  /* Qator yozilgan, urinish hali QILINMAGAN. */
  pending: { tone: "muted", Icon: Clock },
  /* Ijara olingan, HTTP so'rov YO'LDA. */
  sent: { tone: "neutral", Icon: Send },
  /*
   * ⛔ BITTA belgi (yuqoridagi 2-band). `success` — bu fazadagi
   *   `--color-success` ning YAGONA qonuniy joyi (§13.1).
   */
  delivered: { tone: "success", Icon: Check },
  /* Urinishlar tugadi yoki qayta urinib bo'lmaydigan xato. */
  failed: { tone: "danger", Icon: TriangleAlert },
  /* ⛔ `neutral` — D-22 (yuqoridagi 3-band). `danger` MUZOKARASIZ TAQIQ. */
  blocked: { tone: "neutral", Icon: Link2Off },
};

export type DeliveryBadgeProps = {
  /** Xom qiymat — reyestrda bo'lmasligi MUMKIN. */
  status: string;
};

export function DeliveryBadge({ status }: DeliveryBadgeProps) {
  const t = useTranslations();

  if (!isDeliveryState(status)) {
    /* Zaxira: qator ro'yxatda qoladi, yorlig'i esa hali tarjima qilinmagan. */
    return <Badge tone="muted">{t("recon.deliveryState.unknown")}</Badge>;
  }

  const view = DELIVERY_VIEW[status];

  return (
    <Badge className="gap-1" tone={view.tone}>
      <view.Icon aria-hidden="true" className="size-3" />
      {t(`recon.deliveryState.${status}`)}
    </Badge>
  );
}
