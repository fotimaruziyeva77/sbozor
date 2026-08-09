"use client";

import { useTranslations } from "next-intl";

import { StallStatusBadge } from "@/components/occupancy/stall-day-list";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import type { OccupancyStallItem } from "@/lib/api-types";

/*
 * =============================================================================
 * DL-5 — RASTA-KUN TAFSILOTI (§11.7).
 *
 * ⛔⛔ ⚠ SPEK «HAR VAQT UCHUN BITTA QATOR» SO'RAYDI VA U BUGUN
 *     QURILMAYDI — SABAB O'LCHANGAN, TANLOV EMAS.
 *
 *     §11.7 DL-5 ni «kun davomidagi har vaqt uchun bitta qator: vaqt ·
 *     kamera · natija · manba, har qatordan dalil kadri ochiladi» deb
 *     ta'riflaydi. Bunday ma'lumotni beradigan MARSHRUT YO'Q:
 *     `GET /occupancy` bitta rasta uchun AYNAN yetti maydon qaytaradi
 *     (`OccupancyStallItem`) va ular ichida na slot vaqti, na kamera,
 *     na kadr identifikatori bor. 05-12 ning repozitoriysida ham
 *     bunday metod yozilmagan.
 *
 *     Uch variant ko'rildi:
 *       (a) slot qatorlarini KLIENTDA to'qib chiqarish — soxta
 *           ma'lumot, ya'ni eng yomon shakldagi stub;
 *       (b) «tez orada» degan bo'sh jadval chizish — placeholder, u
 *           ham va'da beradi va bajarmaydi;
 *       (c) FAQAT O'LCHANGANINI ko'rsatish.
 *
 *     (c) tanlandi. Dialog rastaning kun bo'yicha HUKMINI, uning
 *     MANBASINI va slot arifmetikasini beradi — to'rttasi ham serverdan
 *     keladi va hech biri to'qilmagan. Yetishmayotgan yuza SUMMARY da
 *     va `deferred-items.md` da ochiq yozilgan (yangi marshrut — Rule 4,
 *     bu rejaning fayl to'plami FAQAT `frontend/`).
 *
 * ⛔ DALIL KADRI BU YERDA OCHILMAYDI: uni ochish uchun `snapshot_id`
 *    kerak va u javobda YO'Q. «Yuklab olish»/«ulashish» yo'li ham yo'q
 *    (T-05-71) — u umuman qurilmagan.
 *
 * ⛔ TIZIM JAVOBI KO'RSATILADI VA BU ANKOR XAVFI EMAS: bu `report_view`
 *    yuzasi, nazoratchining yuzasi emas. Direktor yorliq ishlab
 *    chiqarmaydi, ya'ni §7.1 ning ankorlash qoidasi bu yerga tegishli
 *    emas.
 *
 * ⛔ PATTA/SUMMA YO'Q — 6-faza (§16.1). Dialogda `occupancy.notBillingYet`
 *    jumlasi bor va u T-05-72 ning to'sig'i.
 * =============================================================================
 */

/**
 * Kun hukmining MANBASI — SOF FUNKSIYA (§S-13).
 *
 * =========================================================================
 * ⛔ `no_coverage` UCHUN MANBA `null` — «Tizim» EMAS, «Ko'rilmadi» ham EMAS.
 *
 *    Qamrovsiz rastada HUKM UMUMAN YO'Q: birorta kamera uni ko'rmagan,
 *    ya'ni na tizim, na nazoratchi bir narsa aytgan. «Tizim» yozish
 *    bo'lmagan javobni bor qilardi; «Ko'rilmadi» esa D-19 ning
 *    (nazoratchi ulgurmadi) signalini D-22 ga (kamera ko'rmaydi)
 *    aralashtirardi — ikkalasi butunlay boshqa nosozlik va boshqa
 *    tuzatish.
 *
 *    Shu sababdan qator UMUMAN chizilmaydi. Bu `round-summary.tsx`
 *    dagi «`null` -> qator yo'q» qoidasining aynan o'zi.
 *
 * ⚠ TARTIB MAJBURIY: `no_coverage` BIRINCHI tekshiriladi. `human` ni
 *   oldinga qo'yish sxema bo'yicha bugun farq bermaydi (qamrovsiz slot
 *   `resolution_source = 'no_coverage'` oladi), lekin da'vo SXEMAGA
 *   emas, o'z mantig'iga tayanishi kerak — 05-12 ning sabotaj J darsi.
 * =========================================================================
 */
export function stallSource(
  item: OccupancyStallItem,
): "system" | "human" | "not_reviewed" | null {
  if (item.status === "no_coverage") return null;
  if (item.human_confirmed) return "human";
  if (item.status === "default_empty") return "not_reviewed";
  return "system";
}

const SOURCE_LABEL = {
  system: "occupancy.sourceSystem",
  human: "occupancy.sourceHuman",
  not_reviewed: "occupancy.sourceNotReviewed",
} as const;

export function StallDetailDialog({
  item,
  onOpenChange,
}: {
  /** `null` — dialog yopiq. */
  item: OccupancyStallItem | null;
  onOpenChange: (open: boolean) => void;
}) {
  const t = useTranslations();
  const source = item === null ? null : stallSource(item);

  return (
    <Dialog.Root onOpenChange={onOpenChange} open={item !== null}>
      {item === null ? null : (
        <Dialog.Content
          description={item.zone_name}
          sheetOnMobile
          size="lg"
          title={t("occupancy.detailTitle", { code: item.stall_code })}
        >
          <dl className="flex flex-col gap-3">
            <Row label={t("occupancy.detailZone")}>
              <span className="text-sm">{item.zone_name}</span>
            </Row>

            <Row label={t("occupancy.detailStatus")}>
              <StallStatusBadge status={item.status} />
            </Row>

            {/*
             * ⛔ MANBA QATORI FAQAT HUKM BO'LGANDA (yuqoridagi
             *    `stallSource` izohi). Qamrovsiz rastada u chizilmaydi.
             */}
            {source === null ? null : (
              <Row label={t("occupancy.resolutionSource")}>
                <span className="text-sm">{t(SOURCE_LABEL[source])}</span>
              </Row>
            )}

            {/*
             * ⛔ NISBAT, FOIZ EMAS: `3 / 7` yaxlitlanmaydi. Bu son
             *    «kun davomida kamida bir marta band ko'rindi» degan
             *    hukmning ARIFMETIK asosi.
             */}
            <Row label={t("occupancy.detailSlots")}>
              <span className="font-mono text-sm tabular-nums">
                {t("occupancy.slotsLine", {
                  occupied: item.occupied_slots,
                  total: item.slots,
                })}
              </span>
            </Row>
          </dl>

          {item.status === "no_coverage" ? (
            <p className="text-xs text-text-muted">
              {t("occupancy.noCoverageWhy")}
            </p>
          ) : null}

          {/* ⛔ 6-faza bilan chalkashishning to'sig'i (T-05-72). */}
          <p className="text-xs text-text-muted">
            {t("occupancy.notBillingYet")}
          </p>

          <Dialog.Footer>
            <Dialog.Close asChild>
              <Button variant="secondary">{t("common.close")}</Button>
            </Dialog.Close>
          </Dialog.Footer>
        </Dialog.Content>
      )}
    </Dialog.Root>
  );
}

/** Yorliq va qiymat DASTURIY jihatdan bog'langan (`<dt>`/`<dd>`). */
function Row({
  children,
  label,
}: {
  children: React.ReactNode;
  label: string;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <dt className="min-w-40 text-xs text-text-muted">{label}</dt>
      <dd className="m-0">{children}</dd>
    </div>
  );
}
