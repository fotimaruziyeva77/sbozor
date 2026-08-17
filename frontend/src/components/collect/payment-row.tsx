"use client";

import { Banknote, CircleCheckBig, CreditCard, Undo2 } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { PaymentMethodValue } from "@/lib/api-types";
import { cn } from "@/lib/cn";
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
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ IKKI SHOX, BITTA BOOL EMAS (Topilma №M, quick 260816-75c)
 * -----------------------------------------------------------------------
 * Bu yerda ilgari bitta qator turardi:
 *
 *     const undone = record.reversed || record.kind === "reversal";
 *
 * `||` ikki BOSHQA hodisani bitta bool'ga siqardi va ma'lumot AYNAN
 * o'sha qatorda yo'qolardi — bekordan keyin ro'yxatda ikkita bir xil
 * ko'rinishli qator qolardi va «qaysi biri nima?» savoli javobsiz edi.
 * Endi qaror UCH HOLATLI (`rowKind()`) va har holat O'Z MATNI bilan
 * chiziladi: rang ham, chiziq ham YOLG'IZ signal emas (§12.4).
 *
 * ⛔ SABAB-KOD QATORDA KO'RSATILMAYDI VA BU UNUTILGAN EMAS:
 *    `paymentResponseSchema` sakkiz kalitli va unda `reason_code` YO'Q.
 *    Uni chizish `/payments` javob SHAKLINI o'zgartirishni talab
 *    qilardi — bu vazifaning chegarasidan tashqarida.
 * =============================================================================
 */

const METHOD_LABEL: Record<
  PaymentMethodValue,
  "collect.methodCash" | "collect.methodTerminal"
> = {
  cash: "collect.methodCash",
  terminal: "collect.methodTerminal",
};

/** Qatorning UCH holatidan biri — ⛔ ikkitasi bitta bool'ga siqilmaydi. */
export type PaymentRowKind = "reversal" | "reversed-payment" | "payment";

/**
 * Qator qaysi HODISANI ifodalaydi.
 *
 * `"reversal"`          — bekor qilish YOZUVI (yangi qator, manfiy kredit);
 * `"reversed-payment"`  — bekor qilingan ASL to'lov (eski qator, o'zgarmagan);
 * `"payment"`           — oddiy to'lov.
 *
 * ⚠ Tartib ahamiyatli: bekor hodisasining o'zida `reversed` bayrog'i
 *   ma'nosiz (uni bekor qilib bo'lmaydi), shuning uchun `kind` BIRINCHI
 *   tekshiriladi.
 */
export function rowKind(
  record: Pick<PaymentRecord, "kind" | "reversed">,
): PaymentRowKind {
  if (record.kind === "reversal") return "reversal";
  if (record.reversed) return "reversed-payment";
  return "payment";
}

export type PaymentRowProps = {
  record: PaymentRecord;
  /** ⛔ IXTIYORIY: berilmasa affordans UMUMAN chizilmaydi. */
  onRequestReverse?: () => void;
};

export function PaymentRow({ record, onRequestReverse }: PaymentRowProps) {
  const t = useTranslations();
  const format = useFormatter();

  const kind = rowKind(record);
  /* ⚠ Shart MANTIQAN o'zgarmadi — endi u UCH HOLATLI qarordan o'qiladi. */
  const canReverse = onRequestReverse !== undefined && kind === "payment";

  /*
   * ⛔ BELGI KO'RINISHDA TUG'ILADI, USTUNDA EMAS. Bu yangi qaror emas —
   *    `billing_repo._SIGNED_PAYMENT_EXPR` ning UI yarmi: «ustun har
   *    doim MUSBAT, belgi KO'RINISHDA» (C-5). `payments.amount_soum` da
   *    `CHECK (> 0)` bor, ya'ni manfiy summa DB'da ifodalab bo'lmaydi.
   */
  const signedAmount =
    kind === "reversal" ? -record.amount_soum : record.amount_soum;

  return (
    /*
     * --- 5-QADAM (09-UI-SPEC §8.1): YANGI QATOR QO'NADI — 800ms ----------
     *
     * ⛔ `.motion-row-land` SHARTSIZ va bu MEXANIK jihatdan to'g'ri: CSS
     *    animatsiyasi element DOM'ga QO'SHILGANDA BIR marta o'ynaydi,
     *    qayta render'da EMAS — ya'ni `useEffect`, taymer yoki holat
     *    KERAK EMAS (G-motion-2(d) ruhi). Yangi to'lov ro'yxatga
     *    kirganda qatori «qo'nadi»; sahifa ochilishida mavjud qatorlar
     *    ham bir marta kirish sifatida qo'nadi — reja buni qabul qilgan.
     *    Reduced-motion'da global blok (G-motion-1(a)) 0.01ms ga
     *    tushiradi: qator fon rangisiz, DARHOL joyida (§8.4).
     *
     * ⛔ Davomiylik (800ms) va ranglar `globals.css::landin` da —
     *    komponentda TAKRORLANMAYDI (G-motion-3(b,c)).
     */
    <li className="motion-row-land flex flex-wrap items-center justify-between gap-3 rounded-md border border-border bg-surface px-4 py-3">
      <div className="flex min-w-0 flex-col gap-1">
        <div className="flex items-center gap-2">
          {/* ⛔ Rasta raqami `font-mono` EMAS (§7.2) — u odam yorlig'i. */}
          <span className="text-sm font-semibold text-text">
            {record.stall_code}
          </span>
          {/*
            * ⛔ Bekor qilingan ASL qatorda summa CHIZILADI va xiralashadi.
            *    Chiziq/rang YOLG'IZ signal EMAS — yonidagi yorliq matni
            *    («Bekor qilingan») allaqachon shu faktni aytadi (§12.4);
            *    chiziq esa uni bir qarashda ko'rinadigan qiladi.
            */}
          <span
            className={cn(
              "font-mono text-sm tabular-nums",
              kind === "reversed-payment"
                ? "text-text-muted line-through"
                : "text-text",
            )}
          >
            {format.number(signedAmount)} {t("collect.amountUnit")}
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
        {/*
         * ⛔ Rang YAGONA signal emas: badge doim MATN tashiydi (§12.4).
         *    Va endi UCH holat UCHTA BOSHQA matn beradi — «bekor
         *    hodisasi» bilan «bekor qilingan to'lov» bir xil so'z bilan
         *    yorliqlanmaydi.
         */}
        {kind === "reversal" ? (
          <Badge className="gap-1" tone="muted">
            <Undo2 aria-hidden="true" className="size-3" />
            {t("collect.reversalEntry")}
          </Badge>
        ) : kind === "reversed-payment" ? (
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
