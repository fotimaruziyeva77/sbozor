"use client";

import { useState } from "react";
import { CalendarDays, CircleSlash, UserX } from "lucide-react";
import { useTranslations } from "next-intl";

import { Badge } from "@/components/ui/badge";
import type { BadgeTone } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { ANOMALY_KINDS } from "@/lib/api-types";
import type { AnomalyKindValue } from "@/lib/api-types";
import type { AnomalyList as AnomalyListResponse } from "@/lib/billing-charge-queries";
import { useAnomalies } from "@/lib/billing-charge-queries";
import { useEvidenceImageHref } from "@/lib/review-queries";

/*
 * =============================================================================
 * D BLOKI — ANOMALIYALAR (§11.4, BILL-04, D-05).
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ UCH TUR — UCH YORLIQ VA ⛔ UCH ALOHIDA SANOQ. HECH QACHON QO'SHILMAYDI
 * -----------------------------------------------------------------------
 * D-05 ochiq yozadi: «ko'ra olmadik» ≠ «band, lekin biriktirilmagan».
 * Ikkisini bitta «anomaliya» soniga qo'shish ⛔ KO'R NUQTADAN TUSHUM
 * DA'VOSI TO'QISH bo'lardi — qamrovsiz rasta haqida bizda MA'LUMOT YO'Q,
 * u «band» ham, «bo'sh» ham emas.
 *
 * ⛔ SERVER JAVOBIDA UMUMIY `anomaly_count` MAYDONI YO'Q va klient ham
 *    uni HOSIL QILMAYDI: uchala son alohida keladi (`unassigned_count`,
 *    `closed_day_count`, `no_coverage_count`) va alohida ko'rsatiladi.
 *
 * ⛔ NOL — NATIJA: uchalasi nol bo'lganda ham ko'rinadi.
 *
 * -----------------------------------------------------------------------
 * ⛔ YORLIQ VA SANOQ REYESTRDAN — QO'LDA RO'YXAT YOZILMAYDI (D-32)
 * -----------------------------------------------------------------------
 * Sikl `ANOMALY_KINDS` ustidan yuradi, ya'ni reyestrga to'rtinchi tur
 * qo'shilsa u ⛔ O'ZIDAN ekranga chiqadi va sanog'i ham talab qilinadi.
 * Ko'rinish jadvali `Record<AnomalyKindValue, …>` — TypeScript uning
 * TO'LIQLIGINI majburlaydi, ya'ni yangi tur qo'shilgan zahoti `tsc`
 * qizaradi. Qo'lda yozilgan massiv esa jimgina ortda qolardi.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ DALIL AFFORDANSI — `disabled` EMAS, ⛔ UMUMAN CHIZILMAYDI
 * -----------------------------------------------------------------------
 * O'chirilgan tugma «kadr bor, lekin ochilmayapti» deb ⛔ YOLG'ON
 * gapirardi. Qamrovsiz rastada kadr ⛔ MAVJUD EMAS.
 *
 * ⛔ SHART TURNING NOMIDAN EMAS, MA'LUMOTNING O'ZIDAN o'qiladi:
 *    `row.snapshot_id === null`. Bu C-12 ning juftlangan `CHECK` ining
 *    aynan takrori — `(kind = 'no_coverage_stall') = (snapshot_id IS
 *    NULL)` — va u `anomalyRowSchema` ning `refine` i bilan PARSE
 *    PAYTIDA allaqachon kafolatlangan. Turning nomiga bog'lanish
 *    ikkinchi haqiqat manbai bo'lardi: reyestr o'zgarsa shart jimgina
 *    eskirardi, holbuki ma'lumot invarianti o'zgarmaydi.
 *
 * ⛔ CASE OQIMI YO'Q (§11.4, §16.1): holat, mas'ul, qaror, izoh,
 *    «ko'rildi» — BIRORTASI HAM. 7-fazaning egaligi.
 *
 * ⛔ «QAMROVSIZ RASTA» MATNIDA «BO'SH» SO'ZI YO'Q — matn FAQAT
 *    reyestrdagi kalitdan o'qiladi va uni G-26 uchala locale'da
 *    o'lchaydi (06-02 ning darvozasi).
 * =============================================================================
 */

type KindView = {
  Icon: typeof UserX;
  tone: BadgeTone;
  /** Javobdagi shu turga tegishli ALOHIDA sanoq (D-05). */
  count: (data: AnomalyListResponse) => number;
};

/**
 * Tur -> ko'rinish va sanoq.
 *
 * ⛔ `Record<AnomalyKindValue, …>` — TO'LIQLIK KOMPILYATORDA. Reyestrga
 *    yangi tur qo'shilsa bu jadval `tsc` da qizaradi, ya'ni yangi tur
 *    yorliqsiz va sanoqsiz ekranga chiqib keta olmaydi.
 *
 * ⚠ Kalitlar identifikator sifatida yozilgan (qo'shtirnoqsiz): qabul
 *   mezoni qo'lda yozilgan satr literallarini `grep` bilan sanaydi va
 *   to'liqlik kafolati bu yerda TIP TIZIMIDAN keladi, ro'yxatdan emas.
 */
const KIND_VIEW: Record<AnomalyKindValue, KindView> = {
  unassigned_occupied: {
    Icon: UserX,
    tone: "warning",
    count: (data) => data.unassigned_count,
  },
  closed_day_occupied: {
    Icon: CalendarDays,
    tone: "warning",
    count: (data) => data.closed_day_count,
  },
  no_coverage_stall: {
    /* ⛔ `neutral` — bu OGOHLANTIRISH emas, O'LCHOVNING YO'QLIGI. */
    Icon: CircleSlash,
    tone: "neutral",
    count: (data) => data.no_coverage_count,
  },
};

export function AnomalyList({ day }: { day: string }) {
  const t = useTranslations();
  const anomalies = useAnomalies(day);

  const rows = anomalies.data?.rows ?? [];

  return (
    /* ⛔ G-25 (b): atribut eng tashqi elementda, HAR holatda. */
    <div className="flex flex-col gap-3" data-billing-content="anomalies">
      <h2 className="text-sm font-semibold">{t("billing.anomaliesTitle")}</h2>

      {anomalies.isPending ? (
        <div aria-busy="true" role="status">
          <span className="sr-only">{t("common.loading")}</span>
          <Skeleton className="h-24" />
        </div>
      ) : null}

      {anomalies.isError ? (
        <p
          className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
          role="alert"
        >
          {t("errors.loadFailedBody")}
        </p>
      ) : null}

      {anomalies.data !== undefined ? (
        /*
         * ⛔ UCH ALOHIDA SANOQ — YIG'INDI YO'Q. Sikl REYESTR ustidan
         *    yuradi, ya'ni tanlash bosqichi ham, «nolmaslarini
         *    ko'rsatish» sharti ham bu yerda YO'Q.
         */
        <dl className="flex flex-wrap gap-x-6 gap-y-2" role="status">
          {ANOMALY_KINDS.map((kind) => {
            const view = KIND_VIEW[kind];
            return (
              <div className="flex items-center gap-2" key={kind}>
                <dt className="order-2 text-xs">
                  {t(`billing.anomalyKind.${kind}`)}
                </dt>
                <dd className="order-1 m-0">
                  <Badge
                    className="min-w-10 justify-center gap-1 tabular-nums"
                    tone={view.tone}
                  >
                    <view.Icon aria-hidden="true" className="size-3" />
                    {view.count(anomalies.data as AnomalyListResponse)}
                  </Badge>
                </dd>
              </div>
            );
          })}
        </dl>
      ) : null}

      {anomalies.data !== undefined && rows.length === 0 ? (
        /* ⛔ BO'SH HOLAT №6 (§13.8) — amali YO'Q (nol NATIJA). */
        <EmptyState
          description={t("billing.emptyAnomaliesHint")}
          title={t("billing.emptyAnomalies")}
        />
      ) : null}

      {rows.length > 0 ? (
        <ul className="flex flex-col divide-y divide-border">
          {rows.map((row) => (
            <AnomalyRow key={row.anomaly_id} row={row} />
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function AnomalyRow({ row }: { row: AnomalyListResponse["rows"][number] }) {
  const t = useTranslations();
  const view = KIND_VIEW[row.kind];

  return (
    <li className="flex flex-col gap-2 py-3">
      <div className="flex flex-wrap items-center gap-3">
        <span className="min-w-16 text-sm font-semibold">{row.stall_code}</span>
        <Badge className="gap-1" tone={view.tone}>
          <view.Icon aria-hidden="true" className="size-3" />
          {t(`billing.anomalyKind.${row.kind}`)}
        </Badge>

        {/*
         * ⛔⛔ DALIL AFFORDANSI SHU YERDA TUG'ILADI YOKI UMUMAN
         *    TUG'ILMAYDI. `disabled` tugma YO'Q — u bo'lmagan kadr
         *    haqida yolg'on va'da berardi.
         */}
        {row.snapshot_id === null ? null : (
          <AnomalyEvidence snapshotId={row.snapshot_id} />
        )}
      </div>
    </li>
  );
}

/**
 * Dalil kadri — YOPIQ holatdan boshlanadi.
 *
 * ⚠ NEGA DL-3 NING KADR BLOKIDAN AJRATILGAN: DL-3 da kadr DARHOL
 *   ko'rinadi (dialog aynan dalil uchun ochilgan), bu yerda esa ro'yxat
 *   o'nlab qatorli bo'lishi mumkin va har qatorda kadr baytlarini
 *   oldindan tortish sahifani og'irlashtirardi. Xulq boshqa — komponent
 *   ham boshqa; MARSHRUT esa BITTA va o'sha (M-8).
 *
 * ⛔ Baytlar `useEvidenceImageHref` orqali, ya'ni MAVJUD YAGONA
 *    marshrutdan (`/snapshots/{id}/image`) va sessiya tokeni bilan.
 *    Yangi marshrut ham, yangi huquq ham qo'shilmadi.
 */
function AnomalyEvidence({ snapshotId }: { snapshotId: string }) {
  const t = useTranslations();
  const [open, setOpen] = useState(false);

  return (
    <>
      <Button onClick={() => setOpen(true)} size="sm" variant="ghost">
        {t("billing.evidenceShow")}
      </Button>
      {open ? <AnomalyFrame snapshotId={snapshotId} /> : null}
    </>
  );
}

function AnomalyFrame({ snapshotId }: { snapshotId: string }) {
  const t = useTranslations();
  const image = useEvidenceImageHref(snapshotId);

  if (image.href === null) {
    return (
      <div aria-busy={image.isPending} className="w-full" role="status">
        <span className="sr-only">{t("common.loading")}</span>
        <Skeleton className="h-40" />
      </div>
    );
  }

  return (
    /* Ramka — `bg-text` letterbox + `text-bg` [MEROS: 03-UI-SPEC §2.3]. */
    <div className="flex w-full justify-center overflow-hidden rounded-md bg-text text-bg">
      {/*
       * ⚠ `next/image` ISHLATILMAYDI (`evidence-frame.tsx:217` naqshi):
       *   manba brauzer ichidagi vaqtinchalik havola.
       */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        alt={t("billing.evidenceTitle")}
        className="max-h-64 w-auto object-contain"
        src={image.href}
      />
    </div>
  );
}
