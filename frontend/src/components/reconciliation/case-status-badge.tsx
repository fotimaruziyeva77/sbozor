"use client";

import { CircleCheckBig, CircleSlash, Inbox, Timer } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useTranslations } from "next-intl";

import { Badge } from "@/components/ui/badge";
import type { BadgeTone } from "@/components/ui/badge";
import type { CaseStatusValue } from "@/lib/api-types";
import { isCaseStatus } from "@/lib/reconciliation-queries";

/*
 * =============================================================================
 * NOMUVOFIQLIK HOLATI — 4 A'ZO, ⛔ 3 KANAL (WCAG 1.4.1).
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ NEGA «ASOSLI» = `danger` VA `success` ⛔ EMAS
 * -----------------------------------------------------------------------
 * «Asosli» degani — nomuvofiqlik ⛔ ROST CHIQDI, ya'ni bozor ⛔ PUL
 * YO'QOTGAN. `success` uni «yaxshi natija» qilib ko'rsatardi va direktor
 * ro'yxatni ⛔ TESKARI o'qirdi: eng ko'p yashil qator turgan kun eng
 * YOMON kun bo'lardi.
 *
 * «Asossiz» esa `muted` — «hech narsa bo'lmagan», e'tibor talab
 * qilmaydi. ⛔ Ikkalasi ham «hal qilingan», lekin ma'nosi ⛔
 * QARAMA-QARSHI; bir xil ko'rinsa aniqlik ulushining butun mazmuni
 * yo'qolardi.
 *
 * -----------------------------------------------------------------------
 * ⛔ EKRAN MATNIDA «case» SO'ZI YO'Q
 * -----------------------------------------------------------------------
 * Transliterator lotin akronimini kirillcha o'zak bilan ARALASHTIRIB
 * yuboradi (aralash alifbo — `i18n:check` uni qizartiradi) va u so'z
 * mahalliy foydalanuvchi uchun begona. Kodda va bazada nom O'Z JOYIDA
 * QOLADI; ekranda — «nomuvofiqlik».
 *
 * -----------------------------------------------------------------------
 * ⛔ NOMA'LUM QIYMAT YASHIRILMAYDI, ZAXIRA YORLIQ OLADI (04-10 darsi)
 * -----------------------------------------------------------------------
 * Sxema reyestr bilan qulflanmagan, ya'ni backend beshinchi a'zo
 * qo'shsa u BU YERGA yetib keladi. Qatorni chizmaslik uni ro'yxatdan
 * JIMGINA yo'qotardi — hisobotda «bugun 3 ta nomuvofiqlik» degan
 * YOLG'ON son qolardi.
 * =============================================================================
 */

type StatusView = { tone: BadgeTone; Icon: LucideIcon };

/**
 * Holat -> ko'rinish. ⛔ `Record<CaseStatusValue, …>` ATAYIN: reyestrga
 * yangi a'zo qo'shilsa bu jadval `tsc` da qizaradi, ya'ni yangi holat
 * yorliqsiz va ikonkasiz ekranga chiqib keta olmaydi.
 */
const STATUS_VIEW: Record<CaseStatusValue, StatusView> = {
  new: { tone: "accent", Icon: Inbox },
  in_review: { tone: "warning", Icon: Timer },
  /* ⛔ `danger` — «asosli» degani bozor PUL YO'QOTGAN (yuqoriga qarang). */
  justified: { tone: "danger", Icon: CircleCheckBig },
  unjustified: { tone: "muted", Icon: CircleSlash },
};

export type CaseStatusBadgeProps = {
  /** Xom qiymat — reyestrda bo'lmasligi MUMKIN. */
  status: string | null;
};

export function CaseStatusBadge({ status }: CaseStatusBadgeProps) {
  const t = useTranslations();

  /*
   * ⛔ `null` = case HALI OCHILMAGAN. Bu «noma'lum holat» EMAS: navbat
   *   `recon.open` cron'ida va `overdue_days` chegarasi bilan tug'iladi,
   *   ya'ni chegaradan oldingi qator ATAYIN navbatsiz turadi va unda
   *   ⛔ AMAL YO'Q. Qo'lda «ochish» chegarani aylanib o'tardi.
   */
  if (status === null) {
    return <Badge tone="muted">{t("recon.caseUnqueued")}</Badge>;
  }

  if (!isCaseStatus(status)) {
    /* Zaxira: son ro'yxatda qoladi, yorlig'i esa hali tarjima qilinmagan. */
    return <Badge tone="muted">{t("recon.caseStatus.unknown")}</Badge>;
  }

  const view = STATUS_VIEW[status];

  return (
    <Badge className="gap-1" tone={view.tone}>
      <view.Icon aria-hidden="true" className="size-3" />
      {t(`recon.caseStatus.${status}`)}
    </Badge>
  );
}
