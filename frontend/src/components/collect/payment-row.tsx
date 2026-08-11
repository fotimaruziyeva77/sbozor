"use client";

import { Banknote, CircleCheckBig, CreditCard, Undo2 } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { PaymentMethodValue } from "@/lib/api-types";
import type { PaymentRecord } from "@/lib/payment-queries";

/*
 * =============================================================================
 * YOZILGAN TO'LOV QATORI (UI-SPEC §8.8, §12.4, C-10, D-23).
 *
 * ⛔⛔ JAMI / YIG'INDI — HECH QANDAY SHAKLDA YO'Q.
 *
 *   Bu §10.3 dagi ko'r naqd deklaratsiyasining IKKINCHI YARMI. Kassir
 *   o'zi yozgan to'lovlarni ko'rishi KERAK (bekor qilish uchun), lekin
 *   agar u smenasining hamma to'lovini ko'rsa, ularni QO'SHIB tizim
 *   summasini chiqarib olardi — ya'ni ko'rlik ARIFMETIKA BILAN
 *   buzilardi.
 *
 *   ⛔ Mexanizm ikki tomondan: (1) oyna SERVERDA qat'iy (oxirgi beshta,
 *      `limit`/`offset`/`cursor` parametri YO'Q) va (2) bu faylda
 *      yig'uvchi amal UMUMAN yozilmaydi. Ikkinchisi statik darvoza bilan
 *      o'lchanadi.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ §8.8 FLAG'INING YOPILISHI — TO'LOV TURI IKKI KANALDA
 * -----------------------------------------------------------------------
 * UI-SPEC §8.8 to'lov turini «ikonka» deb yozib, ochiq FLAG qoldirgan
 * edi. ⛔ QAROR: ikonka YOLG'IZ qolmaydi — yonida KO'RINADIGAN MATN
 * turadi («Naqd» / «Terminal», `text-xs`).
 *
 * ⛔ `aria-label` YETARLI DEB QABUL QILINMAYDI, va sabab WCAG 1.4.1 ning
 *    matnida: to'lov turi — bu HOLAT emas, MA'LUMOT. Nizoda kassir va
 *    sotuvchi ekranga BIRGA qaraydi; ko'zi ojiz bo'lmagan foydalanuvchi
 *    uchun `aria-label` mavjud emas, ya'ni «naqd deb yozilganmi yoki
 *    terminal deb?» degan savol ikonkaning shakliga bog'lanib qolardi.
 *    Ikkita kul rang ikonka esa quyoshda telefonda deyarli ajralmaydi.
 *
 * -----------------------------------------------------------------------
 * ⛔ BEKOR QILISH — YAGONA AMAL (D-23)
 * -----------------------------------------------------------------------
 * Tuzatuvchi va o'chiruvchi amallar UMUMAN yozilmaydi: `payments`
 * append-only va serverda ularning marshruti ham yo'q. Bekor qilish esa
 * YANGI QATOR yozadi; eski qator o'zgarmaydi va ekranda `tone="muted"`
 * bo'lib qoladi.
 *
 * ⛔ Affordans FAQAT haqiqiy to'lov qatorida va FAQAT hali bekor
 *    qilinmagan bo'lsa chiziladi — `disabled` holida turmaydi (05-14
 *    darsi: yo'l bermagan affordans CHIZILMAYDI).
 *
 * ⚠ Kassir FAQAT o'z ochiq smenasidagi to'lovni bekor qiladi (§16.1);
 *   eski to'lov yuzasi 6-fazada qurilmaydi — na marshruti, na egasi bor.
 *
 * ⛔ SOTUVCHI ISMI VA ALOQA MA'LUMOTI YO'Q (C-10, §5.5): kassirda ularni
 *    o'qish huquqi umuman yo'q, ya'ni taqiq HUQUQ darajasida.
 * =============================================================================
 */

const METHOD_LABEL: Record<
  PaymentMethodValue,
  "collect.methodCash" | "collect.methodTerminal"
> = {
  cash: "collect.methodCash",
  terminal: "collect.methodTerminal",
};

export type PaymentRowProps = {
  record: PaymentRecord;
  /** ⛔ IXTIYORIY: berilmasa affordans UMUMAN chizilmaydi. */
  onRequestReverse?: () => void;
};

export function PaymentRow({ record, onRequestReverse }: PaymentRowProps) {
  const t = useTranslations();
  const format = useFormatter();

  const undone = record.reversed || record.kind === "reversal";
  const canReverse =
    onRequestReverse !== undefined && record.kind === "payment" && !undone;

  return (
    <li className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-border bg-surface px-4 py-3">
      <div className="flex min-w-0 flex-col gap-1">
        <div className="flex items-center gap-2">
          {/* ⛔ Rasta raqami `font-mono` EMAS (§7.2) — u odam yorlig'i. */}
          <span className="text-sm font-semibold text-text">
            {record.stall_code}
          </span>
          <span className="font-mono text-sm tabular-nums text-text">
            {format.number(record.amount_soum)} {t("collect.amountUnit")}
          </span>
        </div>

        <div className="flex items-center gap-2 text-xs text-text-muted">
          {/* ⛔ IKKI KANAL: ikonka VA ko'rinadigan matn (WCAG 1.4.1). */}
          {record.method === "cash" ? (
            <Banknote aria-hidden="true" className="size-3" />
          ) : (
            <CreditCard aria-hidden="true" className="size-3" />
          )}
          <span>{t(METHOD_LABEL[record.method])}</span>
          <span aria-hidden="true">·</span>
          <time dateTime={record.created_at}>
            {format.dateTime(new Date(record.created_at), {
              timeStyle: "short",
            })}
          </time>
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-2">
        {/* ⛔ Rang YAGONA signal emas: badge doim MATN tashiydi (§12.4). */}
        {undone ? (
          <Badge className="gap-1" tone="muted">
            <Undo2 aria-hidden="true" className="size-3" />
            {t("collect.reversed")}
          </Badge>
        ) : (
          <Badge className="gap-1" tone="success">
            <CircleCheckBig aria-hidden="true" className="size-3" />
            {t("collect.written")}
          </Badge>
        )}

        {canReverse ? (
          <Button onClick={onRequestReverse} size="sm" variant="ghost">
            {t("collect.reverse")}
          </Button>
        ) : null}
      </div>
    </li>
  );
}
