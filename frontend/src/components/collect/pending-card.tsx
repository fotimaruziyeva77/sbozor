"use client";

import { CalendarDays, Clock, PiggyBank } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { billingErrorView } from "@/lib/billing-errors";
import type { PendingStall } from "@/lib/billing-pending-queries";

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
 * =============================================================================
 */

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
  /** ⛔ IXTIYORIY: berilmasa `[Summani o'zgartirish]` UMUMAN chizilmaydi. */
  onRequestOverride?: () => void;
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
}: PendingCardProps) {
  const t = useTranslations();
  const format = useFormatter();

  /* ⛔ §9.4, 2-QATLAM — javobning O'ZI kiritilgan kodni tasdiqlaydi. */
  const matched = pending !== null && pending.stall_code === enteredCode;

  const money = (value: number) =>
    `${format.number(value)} ${t("collect.amountUnit")}`;

  return (
    <Card className="border-l-4 border-l-warning">
      {/* --- 1 va 2-kanal: lenta + ikonka ------------------------------- */}
      <div className="flex items-center gap-2 rounded-t-md bg-warning/20 px-5 py-3">
        <Clock aria-hidden="true" className="size-4 shrink-0 text-text" />
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
            <Skeleton className="h-9 w-40" />
          </div>
        ) : (
          <PendingBody
            chosenAmount={chosenAmount}
            money={money}
            onCollectDebt={onCollectDebt}
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
  chosenAmount,
  money,
  onCollectDebt,
  pending,
}: {
  chosenAmount: number | null;
  money: (value: number) => string;
  onCollectDebt: (amount: number) => void;
  pending: PendingStall;
}) {
  const t = useTranslations();

  const payable = chosenAmount ?? pending.amount_soum;
  const debt = pending.outstanding_soum;
  const missingView =
    pending.amount_unavailable_reason === null
      ? null
      : billingErrorView(pending.amount_unavailable_reason);

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
         * ⛔ DISPLAY ROLI — 24px + 600 + `font-mono` (§7.1, §7.2).
         *    Beshinchi tipografiya roli QO'SHILMAYDI: 32px panjarada
         *    bo'lsa ham yangi rol bo'lardi va keyingi fazada «katta
         *    raqam» uslubiga aylanib ketardi.
         */
        <p className="font-mono text-2xl leading-tight font-semibold tracking-tight tabular-nums">
          <span className="sr-only">{t("collect.todayAmount")}: </span>
          {money(payable)}
        </p>
      )}

      {/*
       * ⛔ NOMLANGAN SABAB (§9.4). Yopiq kun — NORMAL kalendar holati,
       *    shuning uchun sariq tint va `role="alert"` YO'Q; tarif esa
       *    ma'lumot nuqsoni va u boshqa ekranda tuzatiladi.
       */}
      {pending.amount_unavailable_reason === "market_closed" ? (
        <div className="flex items-start gap-2 rounded-sm bg-warning/20 px-3 py-2 text-text">
          <CalendarDays aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
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

      {/* --- Eski qarz va avans ---------------------------------------- */}
      {debt < 0 ? (
        /*
         * ⛔ ORTIQCHA TO'LOV BLOKLANMAYDI (06-RESEARCH A4): bloklash
         *    kassirni pulni UMUMAN yozmaslikka majburlardi. U avans
         *    bo'lib ko'rinadi va uch kanalda aytiladi.
         */
        <Badge className="self-start gap-1" tone="success">
          <PiggyBank aria-hidden="true" className="size-3" />
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
