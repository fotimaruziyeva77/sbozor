"use client";

import { CalendarPlus, Pencil, UserMinus, UserRound } from "lucide-react";
import { useTranslations } from "next-intl";

import { VendorDaysRecent } from "@/components/director/vendor-days";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import type { AssignmentMode } from "@/components/vendors/assignment-dialog";
import type { VendorListItem } from "@/lib/api-types";

/*
 * =============================================================================
 * SOTUVCHI PANELI — ro'yxatda sotuvchi BOSILGANDA ochiladi (261006).
 *
 * ⛔ NEGA KERAK BO'LDI: foydalanuvchi «sotuvchilar qismi ishlatishga
 *    noqulay» dedi. Ro'yxatda sotuvchini bosish HECH NARSA qilmasdi, amallar
 *    «…» menyusi ostida yashirin edi, to'lov tarixi esa kartaning ichida
 *    cho'zilib ochilardi. Endi bitta joy: aloqa, rastalar, amallar va tarix.
 *
 * ⚠ AMAL TUGMASI PANELNI YOPADI va o'sha dialogni ochadi (`vendor-list.tsx`
 *   holati). Dialog ustiga dialog qo'yilmaydi: ikki qatlamli fokus
 *   tuzog'i klaviatura bilan ishlashni chalkashtirardi.
 *
 * ⚠ TARIX `report_view` BILAN: u moliyaviy hisobot yo'li
 *   (`GET /reports/vendor-history`). Huquqsiz rolga so'rov yuborilmaydi —
 *   o'rniga NIMA uchun ko'rinmasligi bir jumla bilan aytiladi, aks holda
 *   foydalanuvchi bo'sh joyni «xato» deb o'qirdi.
 * =============================================================================
 */
export function VendorPanel({
  canManage,
  canSeeHistory,
  onAssign,
  onEdit,
  onOpenChange,
  vendor,
}: {
  canManage: boolean;
  canSeeHistory: boolean;
  onAssign: (mode: AssignmentMode) => void;
  onEdit: () => void;
  onOpenChange: (open: boolean) => void;
  vendor: VendorListItem;
}) {
  const t = useTranslations();

  return (
    <Dialog.Root onOpenChange={onOpenChange} open>
      <Dialog.Content
        description={t("vendors.panelHint")}
        icon={UserRound}
        sheetOnMobile
        size="lg"
        title={vendor.full_name}
      >
        <div className="flex flex-col gap-2">
          {/* §8.6: telefon MASKALANMAYDI — admin shu yerdan qo'ng'iroq qiladi. */}
          <a
            className="w-fit text-accent-text underline-offset-2 hover:underline"
            href={`tel:${vendor.phone}`}
          >
            {vendor.phone}
          </a>
          <div className="flex flex-wrap items-center gap-1">
            <span className="text-sm text-text-muted">
              {t("vendors.stallCount", { count: vendor.stall_count })}
            </span>
            {vendor.stall_codes.map((code) => (
              <Badge className="font-mono tabular-nums" key={code}>
                {code}
              </Badge>
            ))}
          </div>
        </div>

        {canManage ? (
          <div className="flex flex-wrap gap-2">
            <Button onClick={onEdit} size="sm" variant="secondary">
              <Pencil aria-hidden="true" />
              {t("vendors.edit")}
            </Button>
            <Button
              onClick={() => onAssign("open")}
              size="sm"
              variant="secondary"
            >
              <CalendarPlus aria-hidden="true" />
              {t("vendors.assignStall")}
            </Button>
            {vendor.stall_count > 0 ? (
              <Button
                onClick={() => onAssign("close")}
                size="sm"
                variant="secondary"
              >
                <UserMinus aria-hidden="true" />
                {t("vendors.closeAssignment")}
              </Button>
            ) : null}
          </div>
        ) : null}

        <section className="flex flex-col gap-2 border-t border-border pt-4">
          <h3 className="text-sm font-semibold">{t("vendors.paymentHistory")}</h3>
          {canSeeHistory ? (
            <VendorDaysRecent vendorId={vendor.id} />
          ) : (
            <p className="text-sm text-text-muted">
              {t("vendors.paymentHistoryNoAccess")}
            </p>
          )}
        </section>
      </Dialog.Content>
    </Dialog.Root>
  );
}
