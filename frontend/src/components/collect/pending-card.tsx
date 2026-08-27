"use client";

import { useId, type Ref } from "react";
import { CalendarDays, Check, Clock, DoorClosed, PiggyBank, Tent, Wrench } from "lucide-react";
import { useFormatter, useLocale, useTranslations } from "next-intl";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { StallStatusValue } from "@/lib/api-types";
import { cn } from "@/lib/cn";
import { billingErrorView } from "@/lib/billing-errors";
import type { PendingStall } from "@/lib/billing-pending-queries";
import { formatAmount } from "@/lib/format-number";

/*
 * =============================================================================
 * Y-2 (RASTA KESIMI) — KUTILAYOTGAN PATTA (UI-SPEC §9.2–§9.4).
 *
 * ⛔⛔ PROYEKSIYA — KVITANSIYA EMAS, VA BU YETTI KANALDA AYTILADI (§9.3).
 *
 *   Bu komponent 1–5-kanallarni tashiydi: sariq lenta, `Clock` ikonkasi,
 *   «Kutilayotgan patta» sarlavhasi, TO'LIQ JUMLA («hisob hali
 *   yozilmagan») va — eng kuchlisi — yozilgan hisobning identifikatori
 *   BU YERDA UMUMAN MAVJUD EMAS. U yashirilmagan: proyeksiya payloadida
 *   bunday maydonning O'ZI yo'q (D-17), ya'ni uni ko'rsatish
 *   KOMPILYATSIYA XATOSI bo'lardi.
 *
 * ⛔ `[Dalilni ko'rish]` YO'Q (6-kanal): dalil kunlik hisobda tug'iladi va
 *    kassir hukm chiqarmaydi — u pul yig'adi. Kadrni bu yuzaga qo'yish
 *    kassirga `camera_view` berishni yoki `require_any_permission()` ning
 *    yopiq to'plamini kengaytirishni talab qilardi [O'LCHANDI: M-8].
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ §9.4 — ESKI SUMMA YANGI RASTA OSTIDA KO'RINMAYDI (2-QATLAM)
 * -----------------------------------------------------------------------
 * Kassir `14-C` ni terdi (15 000), keyin `15-A` ni terdi va BIR ZUMGA
 * `15-A` kodi ostida 15 000 ko'rindi — u shu paytda [Naqd] va
 * [Tasdiqlash] ni bosdi. To'g'ridan-to'g'ri noto'g'ri pul yig'ish.
 *
 * Uch qatlamning IKKINCHISI shu faylda va u KESH SIYOSATIDAN MUSTAQIL:
 * summa FAQAT `pending.stall_code === enteredCode` bo'lganda chiziladi,
 * aks holda `Skeleton`. Ya'ni kalitni server javobining O'ZI tasdiqlaydi.
 * `gcTime` bir kun oshirilsa ham bu qatlam tirik qoladi.
 *
 * -----------------------------------------------------------------------
 * ⛔ YO'Q SUMMANI KO'RINADIGAN QIL, TAXMIN QILMA (D-20, §9.4)
 * -----------------------------------------------------------------------
 * «Taxminiy summa» ham, «oxirgi ma'lum summa» ham KO'RSATILMAYDI. Yo'q
 * summa — yo'q summa, va uning NOMLANGAN sababi bor.
 *
 * ⛔ Yig'indi ham SERVERDAN (`total_due_soum`): `bugungi + qarz` ni
 *    klientda qo'shish D-20 ni BITTA AMAL bilan buzardi va
 *    `[Qarzni ham olish]` aynan shu amalga eng qulay joy edi.
 *
 * -----------------------------------------------------------------------
 * ⛔ `onRequestOverride` — IXTIYORIY, VA PROP BERILMASA TUGMA CHIZILMAYDI
 * -----------------------------------------------------------------------
 * ⛔ `disabled` tugma EMAS. 05-14 ning darsi: yo'l bermagan affordans
 *    CHIZILMAYDI. O'chirilgan tugma «bor, lekin ishlamayapti» deb YOLG'ON
 *    gapirardi va kassir uni bosib turib, oqim to'xtaganini o'ylardi.
 *
 * ⚠ Prop ixtiyoriy, chunki DL-1 dialogi KEYINGI taskda tug'iladi. Oldindan
 *   majburiy qilinsa, bu fayl o'z darvozasida (typecheck) yiqilardi yoki
 *   ijrochi murojaatni olib tashlab yashil bo'lardi — va uni hech kim
 *   qaytarib qo'ymasdi.
 *
 * ⛔ ISM VA ALOQA MA'LUMOTI YO'Q (C-10, §5.5) — kassirda sotuvchi
 *    ma'lumotini o'qish huquqi umuman yo'q, ya'ni taqiq HUQUQ darajasida.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ RASTA KONTEKSTI KO'RINADI, LEKIN TO'LOVNI BLOKLAMAYDI
 *     (quick 260816-75c, Topilma №L)
 * -----------------------------------------------------------------------
 * Kartada ikki mustaqil ogohlantirish bloki bor: reyestr holati
 * (`stall_status !== "active"`) va biriktirish yo'qligi
 * (`vendor_assigned === false`). ⛔ ULAR BIR XIL EMAS — SERVER ULARGA
 *    BOSHQACHA JAVOB BERADI, VA UI SHU FARQNI TAKRORLAYDI.
 *
 * ⛔⛔ `stall_status` — SHUNCHAKI XABAR, TUGMANI O'CHIRISH TAQIQLANADI.
 *     Bu jumla atayin aynan shunday yozilgan, chunki keyingi ijrochi
 *     uchun «ogohlantirish bor ekan, tasdiqni bloklaylik» qadami TABIIY
 *     ko'rinadi. Sabab BIZNESNIKI: ta'mirdagi rasta savdo qilsa patta
 *     TO'LAYDI — bu qaror `billing_repo._market_projection()`
 *     docstringida yozilgan va kunlik hisob `status` ustuni bo'yicha
 *     FILTRLANMAYDI. Server bunday to'lovni O'TKAZADI.
 *
 * ⛔⛔ `vendor_assigned === false` — TASDIQ TO'SILADI (Topilma №1,
 *     260818). Server bu holatni 409 `stall_not_assigned` bilan RAD
 *     ETADI, ya'ni to'siq UI niki emas, SERVERNIKI va UI uni faqat
 *     ko'zguda ko'rsatadi. To'siqning o'zi `payment-bar.tsx` da
 *     (`vendorAssigned` propi) — bu karta ogohlantirish MATNINI beradi.
 *
 * ⚠ NEGA OLDIN XABAR EDI VA NEGA O'ZGARDI: `billing_repo` docstringi
 *   maydon «kassir rad javobini [Tasdiqlash] dan KEYIN emas, OLDIN
 *   olsin» deb chiqarilganini aytadi. Brauzerda o'lchandi — passiv
 *   xabar buni BAJARMAYDI: kassir baribir bosadi va rad javobini
 *   bosgandan KEYIN oladi. Maqsad o'zgargani yo'q, vositasi o'zgardi.
 *
 * ⚠ C-10 CHEGARASI SAQLANADI: bu bloklarda sotuvchi ISMI ham, telefoni
 *   ham YO'Q — faqat biriktirish YO'QLIGI aytiladi.
 * =============================================================================
 */

/**
 * Rasta holati -> i18n kaliti. ⛔ DINAMIK KALIT (`t(\`stalls.status.${x}\`)`)
 * ISHLATILMAYDI — u typecheck'da yiqiladi va `next-intl` kalitni statik
 * bilmay qoladi. Naqsh `payment-row.tsx::METHOD_LABEL` bilan AYNI.
 */
const STALL_STATUS_LABEL: Record<
  StallStatusValue,
  | "stalls.status.active"
  | "stalls.status.maintenance"
  | "stalls.status.closed"
  | "stalls.status.fair"
> = {
  active: "stalls.status.active",
  maintenance: "stalls.status.maintenance",
  closed: "stalls.status.closed",
  fair: "stalls.status.fair",
};

export type PendingCardProps = {
  /** Kassir KIRITGAN kod — moslik sharti shunga qarshi tekshiriladi. */
  enteredCode: string;
  /** Server proyeksiyasi; hali kelmagan bo'lsa `null`. */
  pending: PendingStall | null;
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
  /** Hozir yuboriladigan summa — sessiya holatida (DL-1 uni o'zgartiradi). */
  chosenAmount: number | null;
  /** `[Qarzni ham olish]` — SERVER bergan yig'indi bilan chaqiriladi. */
  onCollectDebt: (amount: number) => void;
  /**
   * Tarozi belgisi YOQILGANMI (0027) — ⛔ STANDART `true`.
   *
   * Holat SESSIYADA yashaydi, bu komponentda EMAS: undan `chosenAmount`
   * hosila bo'ladi va o'sha qiymat idempotentlik kaliti urug'iga kiradi
   * (§8.7). Kartada saqlansa kalit belgidan xabarsiz qolardi va belgi
   * almashganda ESKI kalit bilan BOSHQA summa yuborilardi — server buni
   * `409 idempotency_key_reused` bilan rad etardi.
   */
  feeIncluded: boolean;
  onFeeIncludedChange: (next: boolean) => void;
  /** ⛔ IXTIYORIY: berilmasa `[Summani o'zgartirish]` UMUMAN chizilmaydi. */
  onRequestOverride?: () => void;
  /**
   * 4-qadam FLIP MANBAI (09-04): «Kutilayotgan patta» summa elementi.
   *
   * ⚠ Prop kontrakti shu bitta ixtiyoriy ref bilan KENGAYDI (sabab
   *   SUMMARY'da): uchish manbai shu komponent ICHIDA yashaydi, sessiya
   *   esa unga DOM so'rovisiz yetishi kerak. Berilmasa hech nima
   *   o'zgarmaydi — xulqqa tegmaydigan sof ilgak.
   */
  amountRef?: Ref<HTMLParagraphElement>;
};

export function PendingCard({
  enteredCode,
  pending,
  isLoading,
  isError,
  onRetry,
  chosenAmount,
  onCollectDebt,
  onRequestOverride,
  amountRef,
  feeIncluded,
  onFeeIncludedChange,
}: PendingCardProps) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();

  /* ⛔ §9.4, 2-QATLAM — javobning O'ZI kiritilgan kodni tasdiqlaydi. */
  const matched = pending !== null && pending.stall_code === enteredCode;

  const money = (value: number) =>
    `${formatAmount(format, value, locale)} ${t("collect.amountUnit")}`;

  return (
    <Card className="relative border-l-4 border-l-warning">
      {/*
        * --- 3-QADAM (09-UI-SPEC §8.1): YASHIL HALQA PULSI — 300ms --------
        *
        * ⛔ BIR MARTA: `.motion-ring-pulse` CSS animatsiyasi element DOM'ga
        *    QO'SHILGANDA o'ynaydi (`both` — oxirida opacity 0) va qayta
        *    render uni qayta boshlamaydi. Cheksiz pulsatsiya YO'Q (§4.4).
        *
        * ⚠ «Muvaffaqiyat lahzasi» BU KOMPONENT UCHUN — server proyeksiyani
        *   tasdiqlagan payt (`matched` false→true, ya'ni shu mount).
        *   To'lov muvaffaqiyati lahzasida esa 6-qadam (M-9) kartani AYNAN
        *   o'sha flush'da unmount qiladi — u lahzani bu daraxt hech qachon
        *   chizmaydi; sabab SUMMARY'da, mavjud kontrakt (M-9) yutdi.
        *
        * ⛔ `aria-hidden` + `pointer-events-none` — halqa bezak, bosishni
        *    yutmaydi (T-09-05 bilan bir sinf).
        */}
      {matched ? (
        <span
          aria-hidden="true"
          /*
           * ⛔ `inset-0`, `-inset-0.5` EMAS (K-01 auditi).
           *
           *   Manfiy inset halqani kartadan 2px chetga chiqarardi va
           *   BUTUN SAHIFA gorizontal scroll oladi (o'lchandi:
           *   clientWidth 1135 · scrollWidth 1146). Telefonda bu
           *   sahifani yon tomonga surib yuboradi — kassir yuzasida
           *   bu qimmat nuqson.
           *
           * ⚠ VIZUAL YO'QOTISH YO'Q: halqa `border-2` bilan chiziladi
           *   va `inset-0` da u kartaning O'Z konturi ustiga tushadi —
           *   pulse baribir ko'rinadi.
           */
          className="motion-ring-pulse pointer-events-none absolute inset-0 rounded-lg border-2 border-success"
        />
      ) : null}
      {/* --- 1 va 2-kanal: lenta + ikonka ------------------------------- */}
      <div className="flex items-center gap-2 rounded-t-md bg-warning/20 px-5 py-3">
        <Clock aria-hidden="true" className="size-5 shrink-0 text-text" />
        {/* --- 3-kanal: sarlavha --------------------------------------- */}
        <p className="text-lg font-semibold leading-snug text-text">
          {t("collect.pendingTitle")}
        </p>
      </div>

      <CardContent className="flex flex-col gap-3 pt-4">
        {/* --- 4-kanal: TO'LIQ JUMLA, qisqartma emas -------------------- */}
        <p className="text-sm text-text-muted">{t("collect.pendingNotice")}</p>

        {isError ? (
          /*
           * ⛔ SO'ROV XATOSIDA SUMMA UMUMAN CHIZILMAYDI (§9.4 jadvali).
           *    Oxirgi ma'lum qiymatni ko'rsatish eng jozibali va eng
           *    xavfli yo'l edi: kassir uni BUGUNGI summa deb o'qirdi.
           */
          <div className="flex flex-col items-start gap-2" role="alert">
            <p className="text-sm font-semibold text-danger-text">
              {t("errors.loadFailedTitle")}
            </p>
            <Button onClick={onRetry} size="sm" variant="secondary">
              {t("common.retry")}
            </Button>
          </div>
        ) : !matched ? (
          /*
           * ⛔ MOS KELMAGAN JAVOB — SKELETON. Bu `isLoading` ning
           *    ko'rinishi emas: javob KELGAN, lekin u BOSHQA rastaniki.
           *    Ikkalasi bir xil ko'rinadi va bu ATAYIN — kassir uchun
           *    farqi yo'q, ikkalasida ham «hali summa yo'q».
           */
          <div aria-busy="true" role="status">
            <span className="sr-only">{t("common.loading")}</span>
            {/*
              * ⛔ G-motion-7(c) GEOMETRIYA JUFTLIGI: `h-11` (44px) —
              *    `text-display` ning qator qutisi (40px × 1.1). `h-9`
              *    qolganda skeleton kontentga almashganda karta 8px
              *    sakrardi — CLS ning aynan sababi (09-RESEARCH Tuzoq 10).
              */}
            <Skeleton className="h-11 w-40" />
          </div>
        ) : (
          <PendingBody
            amountRef={amountRef}
            chosenAmount={chosenAmount}
            feeIncluded={feeIncluded}
            money={money}
            onCollectDebt={onCollectDebt}
            onFeeIncludedChange={onFeeIncludedChange}
            pending={pending}
          />
        )}

        {/*
         * ⛔ AFFORDANS FAQAT PROP BERILGANDA CHIZILADI (yuqoridagi blok).
         *    `variant="ghost"` — §12.3: aksent FAQAT tasdiqlash tugmasida.
         */}
        {onRequestOverride !== undefined && matched ? (
          <Button
            className="self-start"
            onClick={onRequestOverride}
            size="sm"
            variant="ghost"
          >
            {t("collect.override")}
          </Button>
        ) : null}
      </CardContent>

      {/*
       * §14.5, 1-hudud: qidiruv natijasi e'lon qilinadi. Yangi tarjima
       * kaliti QO'SHILMAYDI (copy 06-02 ning egaligida) — mavjud yorliq
       * va kod birga o'qiladi.
       */}
      {matched ? (
        <p className="sr-only" role="status">
          {t("collect.stallLabel")}: {pending.stall_code}
        </p>
      ) : null}

      {isLoading ? <span className="sr-only">{t("common.loading")}</span> : null}
    </Card>
  );
}

/* --- Summa bloki ----------------------------------------------------------- */

function PendingBody({
  amountRef,
  chosenAmount,
  feeIncluded,
  money,
  onCollectDebt,
  onFeeIncludedChange,
  pending,
}: {
  amountRef?: Ref<HTMLParagraphElement>;
  chosenAmount: number | null;
  feeIncluded: boolean;
  money: (value: number) => string;
  onCollectDebt: (amount: number) => void;
  onFeeIncludedChange: (next: boolean) => void;
  pending: PendingStall;
}) {
  const t = useTranslations();
  const feeHintId = useId();

  const payable = chosenAmount ?? pending.amount_soum;
  const debt = pending.outstanding_soum;
  const missingView =
    pending.amount_unavailable_reason === null
      ? null
      : billingErrorView(pending.amount_unavailable_reason);
  /*
   * MA'MURIYAT QARORI sabablari — bitta banner, uch holat (2026-08-25:
   * yopiq/ta'mirda ham yarmarka sinfiga qo'shildi). Ikonka sababga mos,
   * ohang esa uchalasida `neutral` (hech nima buzilmagan).
   */
  const adminReason =
    pending.amount_unavailable_reason === "fair_stall" ||
    pending.amount_unavailable_reason === "stall_closed" ||
    pending.amount_unavailable_reason === "stall_maintenance"
      ? pending.amount_unavailable_reason
      : null;
  const fairView = adminReason === null ? null : billingErrorView(adminReason);
  const AdminIcon =
    adminReason === "stall_closed"
      ? DoorClosed
      : adminReason === "stall_maintenance"
        ? Wrench
        : Tent;
  /*
   * ⛔ SUBMIT'DAGI 409 MATNINING AYNAN O'ZI — reyestrdan olinadi, qo'lda
   *    yozilmaydi. `missingView` bilan bir naqsh, bir sabab.
   */
  const notAssignedView = pending.vendor_assigned
    ? null
    : billingErrorView("stall_not_assigned");

  return (
    <div className="flex flex-col gap-3">
      {/*
       * ⛔ RASTA RAQAMI `font-mono` EMAS (§7.2): u DB kontenti va odam
       *    o'qiydigan yorliq, tik solishtiriladigan texnik qiymat emas.
       */}
      <p className="text-sm text-text">
        <span className="text-text-muted">{t("collect.stallLabel")}: </span>
        {pending.stall_code}
      </p>

      {payable === null ? null : (
        /*
         * ⛔ DISPLAY-XL ROLI — 40px / 1.1 + 600 + `font-mono` (09-UI-SPEC
         *    §7.1, L-9). Beshinchi tipografiya roli 09-fazada RASMAN
         *    OCHILDI va u YOPIQ REYESTR bilan qulflangan — AYNAN IKKI joy:
         *    (1) shu summa, (2) `headline-card` faqat `unit === "soum"`
         *    shoxida. G-motion-7(b) buni ≤2 mahsulot fayli deb o'lchaydi.
         *
         * ⚠ IZOH 09-04 DA YANGILANDI: eski matn («24px…, beshinchi rol
         *   QO'SHILMAYDI») 6-faza qarorini aytardi va 09-UI-SPEC §7.1
         *   ostida ESKIRGAN edi — eskirgan izoh keyingi ijrochiga yolg'on
         *   gapiradi. Satr balandligi `text-display` tokenining o'zidan
         *   (`--text-display--line-height: 1.1`) — `leading-*` utilitasi
         *   ORTIQCHA va yozilmaydi.
         */
        <p
          className="font-mono text-display font-semibold tracking-tight tabular-nums"
          ref={amountRef}
        >
          <span className="sr-only">{t("collect.todayAmount")}: </span>
          {money(payable)}
        </p>
      )}

      {/*
       * ============================================================
       * ⛔⛔ TAROZI BELGISI (0027) — MAJBURIY TO'LOVNING KASSIR YUZASI.
       * ============================================================
       *
       * Buyurtmachi qarori: «standart quyilgan belgilansa rastani puliga
       * qushiladi; agar belgilanmasa faqat rastani pulini tulasa tarozi
       * puli qoldi deb chiqadi».
       *
       * ⛔ NEGA CHECKBOX, IKKI TUGMA EMAS: kassir kuniga 300–1000 marta
       *    to'lov yozadi va ULARNING DEYARLI HAMMASI tarozi bilan.
       *    Ikki tugma («Tarozi bilan» / «Tarozisiz») har to'lovga BITTA
       *    TANLOV qo'shardi — ya'ni D-18 ning ≤3 bosish sanog'i 4 ga
       *    chiqardi. Belgi esa ALLAQACHON to'g'ri holatda turadi:
       *    odatiy yo'lda kassir unga UMUMAN tegmaydi.
       *
       * ⛔ BLOK FAQAT `fee_amount_soum > 0` BO'LGANDA CHIZILADI. Nol
       *    qiymat «bu bozorda tarozi olinmaydi» degani va o'chirilgan
       *    belgini ko'rsatish kassirga MAVJUD BO'LMAGAN tanlovni taklif
       *    qilardi.
       *
       * ⛔ `paid`/`due` RANGI YO'Q: bu tanlov, holat emas. Semantik
       *    ranglar faqat ma'no uchun (masterplan §1.1).
       *
       * ⚠ NISHON 56px (`min-h-14`): kassir buni bozor ichida, bir qo'lda,
       *   ehtimol qo'lqopda bosadi. 44px minimal, bu esa ONGLI ravishda
       *   kattaroq — u ekrandagi IKKINCHI eng muhim nishon (birinchisi
       *   tasdiqlash tugmasi).
       */}
      {pending.fee_amount_soum !== null && pending.fee_amount_soum > 0 ? (
        <div className="flex flex-col gap-2">
          {/*
           * ⛔ TAQSIMOT KO'RINADI: kassir «40 000 qayerdan chiqdi?»
           *    degan savolga ekrandan javob topadi. Sotuvchi ham shu
           *    ekranni ko'radi — nomsiz qo'shimcha nizo generatori.
           */}
          <p className="flex items-baseline justify-between gap-3 text-sm">
            <span className="text-text-muted">{t("collect.stallLine")}</span>
            <span className="font-mono tabular-nums text-text">
              {money(pending.stall_amount_soum ?? 0)}
            </span>
          </p>

          {/*
           * ⛔⛔ `role="switch"` — CHECKBOX EMAS, VA BU FARQ MEXANIK
           *     DARVOZA BILAN MAJBURLANGAN (`collect-surface.test.mjs`
           *     ning `BULK_ACTION_TOKENS` reyestri).
           *
           *   Darvoza kassir yuzasida `type="checkbox"` ni TAQIQLAYDI va
           *   sabab yozilgan: «Hammasini to'lash» bir bosishda 50 rastani
           *   to'langan deb belgilardi va natijasi PUL YOZUVI bo'lardi.
           *
           *   Bu belgi ommaviy tanlov EMAS — u BITTA to'lovning ikki
           *   holatli o'zgartkichi. Ya'ni darvozaning MAQSADI buzilmaydi.
           *   Lekin uni «bu holat boshqacha» deb chetlab o'tish
           *   detektorni bo'shatardi: keyingi ijrochi haqiqiy ommaviy
           *   checkbox qo'shganda darvoza jim qolardi.
           *
           *   Shuning uchun yechim BOSHQA BOSHQARUV: `switch` semantik
           *   jihatdan ham to'g'riroq (u tanlov emas, YOQIQ/O'CHIQ) va
           *   ekran o'quvchisi uni aynan shunday o'qiydi.
           */}
          <button
            aria-checked={feeIncluded}
            aria-describedby={feeHintId}
            className={cn(
              "flex min-h-14 w-full cursor-pointer items-center gap-3 rounded-md border px-4 py-2 text-left transition-colors",
              feeIncluded
                ? "border-accent/40 bg-accent/8"
                : "border-border bg-surface-muted",
            )}
            onClick={() => onFeeIncludedChange(!feeIncluded)}
            role="switch"
            type="button"
          >
            {/*
             * ⛔ NISHON — 28px doira, `size-4` ikonkalardan ATAYIN KATTA:
             *    u kassir bosadigan yuza va uning holati bir metrdan
             *    ko'rinishi kerak (foydalanuvchi topilmasi: «iconlar juda
             *    kichin»).
             */}
            <span
              aria-hidden="true"
              className={cn(
                "flex size-7 shrink-0 items-center justify-center rounded-md border-2 transition-colors",
                feeIncluded
                  ? "border-accent bg-accent text-accent-fg"
                  : "border-border-ui bg-surface",
              )}
            >
              {feeIncluded ? <Check className="size-5" strokeWidth={3} /> : null}
            </span>
            <span className="flex min-w-0 flex-1 flex-col gap-0.5">
              <span className="flex items-baseline justify-between gap-3">
                {/*
                 * ⛔ NOM SERVERDAN (`fee_label`) — TARJIMA QILINMAYDI.
                 *    U bozor kiritgan matn: har bozor xizmatini o'z nomi
                 *    bilan ataydi va uni i18n kalitiga aylantirish
                 *    «Tarozi xizmati» ni HAMMA bozorga majburlardi.
                 */}
                <span className="truncate text-sm font-semibold text-text">
                  {pending.fee_label}
                </span>
                <span className="shrink-0 font-mono tabular-nums text-sm font-semibold text-text">
                  +{money(pending.fee_amount_soum)}
                </span>
              </span>
              <span className="text-sm text-text-muted" id={feeHintId}>
                {feeIncluded
                  ? t("collect.feeIncludeHint")
                  : t("collect.feeLeftUnpaid")}
              </span>
            </span>
          </button>
        </div>
      ) : null}

      {/*
       * ⛔ NOMLANGAN SABAB (§9.4). Yopiq kun — NORMAL kalendar holati,
       *    shuning uchun sariq tint va `role="alert"` YO'Q; tarif esa
       *    ma'lumot nuqsoni va u boshqa ekranda tuzatiladi.
       */}
      {/*
       * ⛔ YARMARKA (0028) -- teal blok, `role="alert"` YO'Q: bu QAROR,
       *    nosozlik emas. Matn reyestrdan (`billingErrorView`), qo'lda
       *    yozilmaydi -- submit'dagi 422 bilan AYNI so'zlar.
       */}
      {adminReason !== null && fairView !== null ? (
        <div className="flex flex-col gap-1 rounded-sm bg-info/15 px-3 py-2">
          <p className="flex items-center gap-2 text-sm font-semibold text-info-text">
            <AdminIcon aria-hidden="true" className="size-5 shrink-0" />
            {t(fairView.causeKey)}
          </p>
          <p className="text-sm text-text">{t(fairView.fixKey)}</p>
        </div>
      ) : null}

      {pending.amount_unavailable_reason === "market_closed" ? (
        <div className="flex items-start gap-2 rounded-sm bg-warning/20 px-3 py-2 text-text">
          <CalendarDays aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
          <p className="text-sm">{t("collect.marketClosed")}</p>
        </div>
      ) : null}

      {pending.amount_unavailable_reason === "tariff_missing" &&
      missingView !== null ? (
        <div
          className="flex flex-col gap-1 rounded-sm bg-danger/10 px-3 py-2"
          role="alert"
        >
          <p className="text-sm font-semibold text-danger-text">
            {t(missingView.causeKey)}
          </p>
          <p className="text-sm text-text">{t(missingView.fixKey)}</p>
        </div>
      ) : null}

      {/*
       * --- (a) REYESTR HOLATI ----------------------------------------
       *
       * ⛔ `role="alert"` YO'Q (§14.5): bir vaqtda ikkitadan ko'p `alert`
       *    chizilmaydi va bu NORMAL reyestr holati, NOSOZLIK emas.
       *    `market_closed` bloki bilan AYNI naqsh, faqat ikonka boshqa
       *    (`CalendarDays` o'shaniki, takrorlanmaydi).
       *
       * ⛔ MATN «hisob yozilmaydi» DEMAYDI va ayta ham olmaydi: kunlik
       *    hisob holat ustuni bo'yicha filtrlanmaydi. Bunday da'vo
       *    `is_billable` ni SO'Z BILAN qaytarib keltirardi.
       */}
      {pending.stall_status !== "active" ? (
        <div className="flex items-start gap-2 rounded-sm bg-warning/20 px-3 py-2 text-text">
          <Wrench aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
          <p className="text-sm">
            {t("collect.stallStatusNotice", {
              status: t(STALL_STATUS_LABEL[pending.stall_status]),
            })}
          </p>
        </div>
      ) : null}

      {/*
       * --- (b) BIRIKTIRISH YO'Q --------------------------------------
       *
       * ⛔ MANBA — `billingErrorView("stall_not_assigned")`, ya'ni
       *    submit'dagi 409 matnining AYNAN O'ZI. Yangi copy kaliti
       *    YOZILMAYDI: ikki xil so'z kassirga ikki xil nosozlik bo'lib
       *    ko'rinardi va u «qaysi biri rost?» degan savolga qolardi.
       *
       * ⛔ Blok (a) DAN MUSTAQIL: ikkalasi birga chizilishi mumkin —
       *    ular boshqa-boshqa savolga javob beradi.
       */}
      {notAssignedView === null ? null : (
        <div
          className="flex flex-col gap-1 rounded-sm bg-danger/10 px-3 py-2"
          role="alert"
        >
          <p className="text-sm font-semibold text-danger-text">
            {t(notAssignedView.causeKey)}
          </p>
          <p className="text-sm text-text">{t(notAssignedView.fixKey)}</p>
        </div>
      )}

      {/* --- Eski qarz va avans ---------------------------------------- */}
      {debt < 0 ? (
        /*
         * ⛔ ORTIQCHA TO'LOV BLOKLANMAYDI (06-RESEARCH A4): bloklash
         *    kassirni pulni UMUMAN yozmaslikka majburlardi. U avans
         *    bo'lib ko'rinadi va uch kanalda aytiladi.
         */
        <Badge className="self-start gap-1" tone="success">
          <PiggyBank aria-hidden="true" className="size-4" />
          {t("collect.advance")}
        </Badge>
      ) : debt === 0 ? (
        <p className="text-xs text-text-muted">{t("collect.noDebt")}</p>
      ) : (
        <div className="flex flex-wrap items-center gap-3">
          <p className="text-sm text-text">
            <span className="text-text-muted">{t("collect.oldDebt")}: </span>
            <span className="font-mono tabular-nums">{money(debt)}</span>
          </p>
          {/*
           * ⛔ YIG'INDI SERVERDAN (§9.6). Klient `bugungi + qarz` ni
           *    HISOBLAMAYDI — bu tugma D-20 ni buzishning eng qisqa yo'li
           *    edi va shuning uchun qiymat payloadda TAYYOR keladi.
           *
           * ⛔ Standart — BUGUNGI patta, yig'indi emas: aks holda 45 000
           *    qarzi bor sotuvchi bugungi 15 000 ni ≤3 bosishda to'lay
           *    olmasdi va kassir istisno yo'liga (DL-1) majbur bo'lardi.
           */}
          <Button
            onClick={() => onCollectDebt(pending.total_due_soum)}
            size="sm"
            variant="secondary"
          >
            {t("collect.withDebt")}
            <span className="font-mono tabular-nums">
              {money(pending.total_due_soum)}
            </span>
          </Button>
        </div>
      )}
    </div>
  );
}
