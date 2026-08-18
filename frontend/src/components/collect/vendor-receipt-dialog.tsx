"use client";

import { useFormatter, useLocale, useTranslations } from "next-intl";

import { Dialog } from "@/components/ui/dialog";
import { formatAmount } from "@/lib/format-number";
import type { PaymentRecord } from "@/lib/payment-queries";

/*
 * SOTUVCHIGA KO'RSATILADIGAN TASDIQ (K-3, «Sbozor Kassir» dizayni).
 *
 * ⛔ Nima uchun bor: sotuvchi naqd pul beradi va qo'lida HECH NIMA
 *    qolmaydi — chek yo'q, kvitansiya raqami yo'q, avtomatik xabar ham
 *    yuborilmaydi. «Men to'lagandim» degan bahsda kassirning so'ziga
 *    qarshi sotuvchining so'zi turadi — mahsulot esa aynan shu bahsni
 *    yo'q qilish uchun qurilgan.
 *
 * ⛔ Nima QILMAYDI: bu chek EMAS va kvitansiya raqami EMAS. U hech qayerga
 *    yozilmaydi, hech nima yubormaydi — u shunchaki YOZILGAN yozuvni
 *    uzoqdan o'qiladigan qilib ko'rsatadi. Shuning uchun bu yerda yangi
 *    ma'lumot yo'q: hammasi `record` ning o'zidan.
 *
 * ⛔ O'lchamlar: rasta va summa eng katta — telefon sotuvchiga BURIB
 *    ko'rsatiladi, ya'ni matn qo'l uzunligidan o'qilishi kerak.
 */
export type VendorReceiptDialogProps = {
  record: PaymentRecord;
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

export function VendorReceiptDialog({
  record,
  open,
  onOpenChange,
}: VendorReceiptDialogProps) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();

  return (
    <Dialog.Root onOpenChange={onOpenChange} open={open}>
      <Dialog.Content
        description={t("collect.showVendorBody")}
        sheetOnMobile
        size="sm"
        title={t("collect.showVendor")}
      >
        <div className="flex flex-col items-center gap-2 py-2 text-center">
          <p className="text-2xl font-semibold tracking-tight">
            {record.stall_code}
          </p>
          <p
            className="collect-vendor-amount font-mono font-semibold tracking-tight tabular-nums"
            data-numeric
          >
            {formatAmount(format, record.amount_soum, locale)} {t("collect.amountUnit")}
          </p>
          <p className="text-sm text-text-muted">
            {record.method === "cash"
              ? t("collect.methodCash")
              : t("collect.methodTerminal")}
            {" · "}
            <time dateTime={record.created_at}>
              {format.dateTime(new Date(record.created_at), {
                timeStyle: "short",
              })}
            </time>
          </p>
        </div>
        <Dialog.Footer>
          <Dialog.Close asChild>
            <button
              className="min-h-11 cursor-pointer rounded-md border border-border px-6 text-sm font-semibold text-text"
              type="button"
            >
              {t("common.close")}
            </button>
          </Dialog.Close>
        </Dialog.Footer>
      </Dialog.Content>
    </Dialog.Root>
  );
}
