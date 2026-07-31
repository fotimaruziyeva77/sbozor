"use client";

import type { ReactNode } from "react";
import { AlertCircle } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";

import { StallStatusBadge } from "@/components/stalls/stall-list";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import type { StallDetail } from "@/lib/api-types";
import { marketErrorMessageKey } from "@/lib/market-errors";
import { useStallQuery } from "@/lib/market-queries";

/*
 * =============================================================================
 * Rasta kartasi — BITTA modal `<Dialog>`, tanlangan ID sahifa holatida
 * (UI-SPEC §7.6).
 *
 * RAD ETILGAN MUQOBILLAR:
 *   har katakka o'z suzuvchi     -> 1000 ta Radix portali; zich gridda
 *   oynachasi                       pozitsiyalash ekran chekkasiga urilardi.
 *                                   (Radix'ning o'sha primitivi NOMI bu
 *                                   yerda literal yozilmaydi — taqiq
 *                                   mexanik grep darvozasi bilan
 *                                   qulflangan, kodbaza konvensiyasi.)
 *   yon panel (drawer)           -> yangi layout primitivi; <=768px da
 *                                   gridni siqib qo'yardi;
 *   qator ichida kengayish       -> `auto-fill` tartibini yorib yuborardi;
 *   alohida marshrut `/stalls/id`-> xaritadagi skroll pozitsiyasi yo'qolardi.
 *
 * ⚠ TANLANGAN ID KATAKNING PROPIGA TUSHMAYDI (Pitfall 8). U sahifa
 * holatida yashaydi va faqat SHU dialog uni o'qiydi — aks holda har
 * bosishda 1000 katak qayta render bo'lardi. Qo'shimcha foyda: katak qayta
 * render bo'lmagani uchun dialog yopilganda fokus AYNAN bosilgan katakka
 * qaytadi (trigger DOM'da qolgan).
 * =============================================================================
 */

export type StallCardProps = {
  stallId: string | null;
  onClose: () => void;
  /**
   * 6–7 fazalar: dalil-rasm galereyasi shu yerga tushadi. 2-fazada
   * `undefined` — galereya, lightbox va rasm yuklash bu fazada
   * QURILMAYDI (Scope Fence). Bitta prop, nol infratuzilma.
   */
  children?: ReactNode;
  /**
   * `stall_manage` huquqi. Amal tugmalari faqat shu bilan render qilinadi
   * — bu UI KO'ZGUSI, xavfsizlik chegarasi EMAS (T-02-109).
   */
  canManage?: boolean;
  /** Berilmasa "Tahrirlash" tugmasi render qilinmaydi. */
  onEdit?: (stallId: string) => void;
};

export function StallCardDialog({
  canManage = false,
  children,
  onClose,
  onEdit,
  stallId,
}: StallCardProps) {
  const t = useTranslations();
  const stallQuery = useStallQuery(stallId);
  const stall = stallQuery.data;

  return (
    <Dialog.Root
      onOpenChange={(next) => {
        if (!next) onClose();
      }}
      open={stallId !== null}
    >
      {/*
       * `sheetOnMobile` — `<640px` da pastki varaq (§7.6). Faqat CSS:
       * ikkinchi komponent ham, ikkinchi bog'liqlik ham qo'shilmaydi.
       */}
      <Dialog.Content
        description={t("stalls.cardHint")}
        sheetOnMobile
        size="lg"
        srOnlyDescription
        title={
          <span className="flex flex-wrap items-center gap-3">
            {/* D-16: rasta raqami DB kontenti — tarjima qilinmaydi. */}
            <span className="font-mono text-xl tabular-nums">
              {stall?.code ?? ""}
            </span>
            {stall ? <StallStatusBadge status={stall.status} /> : null}
          </span>
        }
      >
        {stallQuery.isPending ? (
          <div aria-busy="true" className="flex flex-col gap-2" role="status">
            <span className="sr-only">{t("common.loading")}</span>
            <Skeleton className="h-5 w-2/3" />
            <Skeleton className="h-24 rounded-lg" />
          </div>
        ) : null}

        {stallQuery.isError ? (
          <p
            className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
            role="alert"
          >
            {t(marketErrorMessageKey(stallQuery.error))}
          </p>
        ) : null}

        {stall ? (
          <StallCardBody canManage={canManage} onEdit={onEdit} stall={stall} />
        ) : null}

        {children}
      </Dialog.Content>
    </Dialog.Root>
  );
}

function StallCardBody({
  canManage,
  onEdit,
  stall,
}: {
  canManage: boolean;
  onEdit?: (stallId: string) => void;
  stall: StallDetail;
}) {
  const t = useTranslations();
  const tStatus = useTranslations("stalls.status");
  const format = useFormatter();

  const categoryLabel = stall.category_name ?? t("stalls.categoryUnset");

  return (
    <div className="flex flex-col gap-4">
      {/* D-16: toifa va zona nomi DB kontenti — tarjima qilinmaydi. */}
      <p className="text-sm text-text-muted">
        {categoryLabel} · {stall.zone_name}
      </p>

      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
        <dt className="text-text-muted">{t("stalls.categoryLabel")}</dt>
        <dd className="font-semibold">{categoryLabel}</dd>

        <dt className="text-text-muted">{t("stalls.tariffLabel")}</dt>
        <dd className="font-semibold tabular-nums">
          {stall.tariff_soum === null ? (
            /*
             * ⚠ "Tarif belgilanmagan" MAJBURIY va OGOHLANTIRISH uslubida
             * ko'rinadi (D-08 fail-closed): tarifsiz rasta kunlik patta
             * hisobiga umuman tushmaydi va 6-fazada anomaliyaga aylanadi,
             * ya'ni bu HAQIQIY NOSOZLIK. Kamera bo'limidan farqli o'laroq
             * bu yerda qizil uslub TO'G'RI.
             *
             * Rang yagona signal emas: yonida ikonka va matn turadi
             * (WCAG 1.4.1).
             */
            <span className="flex items-center gap-2 text-danger-text">
              <AlertCircle aria-hidden="true" className="size-4 shrink-0" />
              {t("stalls.noTariff")}
            </span>
          ) : (
            format.number(stall.tariff_soum, {
              style: "currency",
              currency: "UZS",
              maximumFractionDigits: 0,
            })
          )}
        </dd>

        <dt className="text-text-muted">{t("stalls.vendorLabel")}</dt>
        {/*
         * Sotuvchisiz rasta — ANOMALIYA, lekin NOSOZLIK EMAS (D-11): bozor
         * bo'sh rasta bilan ham normal ishlaydi. Shuning uchun uslub
         * neytral, ogohlantirish emas.
         *
         * D-16: sotuvchi ismi DB kontenti — tarjima qilinmaydi.
         */}
        <dd className={stall.vendor_name === null ? "text-text-muted" : "font-semibold"}>
          {stall.vendor_name ?? t("stalls.noVendor")}
        </dd>

        {stall.phone === null ? null : (
          <>
            <dt className="text-text-muted">{t("stalls.phoneLabel")}</dt>
            {/*
             * Telefon MASKALANMAYDI (§8.6): server raqamni allaqachon
             * yuborgan va uni klientda yulduzcha bilan yopish xavfsizlik
             * teatri bo'lardi. `GET /vendors` audit bildirishi bu yerda
             * TAKRORLANMAYDI — karta bitta rasta konteksti.
             */}
            <dd className="font-semibold tabular-nums">
              <a className="underline underline-offset-2" href={`tel:${stall.phone}`}>
                {stall.phone}
              </a>
            </dd>
          </>
        )}

        <dt className="text-text-muted">{t("stalls.statusLabel")}</dt>
        <dd className="font-semibold">{tStatus(stall.status)}</dd>
      </dl>

      {canManage && onEdit ? (
        <Dialog.Footer>
          <Button
            className="sm:flex-1"
            onClick={() => onEdit(stall.id)}
            size="lg"
          >
            {t("stalls.edit")}
          </Button>
        </Dialog.Footer>
      ) : null}
    </div>
  );
}
