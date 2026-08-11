"use client";

import type { ReactNode } from "react";
import { Clock } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useMarketPending } from "@/lib/billing-pending-queries";

/*
 * =============================================================================
 * B BLOKI — ⛔ KUTILAYOTGAN PATTA (PROYEKSIYA), BOZOR KESIMI (§9.5, D-17).
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ G-25 (b) NING YARMI SHU FAYLDA — VA SABAB O'LCHANGAN
 * -----------------------------------------------------------------------
 * Komponentning ENG TASHQI elementi `data-billing-content="pending"`
 * chiqaradi va ⛔ BU ATRIBUTNI FAQAT SHU KOMPONENT YOZADI —
 * `billing/page.tsx` uni HECH QACHON yozmaydi (T3 da `grep` bilan `0`).
 *
 * ⛔ NEGA ATRIBUT SAHIFADA EMAS, RO'YXATDA. G-25 ning ESKI shakli faqat
 *    `data-billing-block` o'ramining ATRIBUT QIYMATLARI to'plamini
 *    da'vo qilardi — ya'ni uni bo'sh `<div data-billing-block="pending" />`
 *    ⛔ MUKAMMAL qondirardi. Natijada BILL-05 direktor ekranida
 *    ⛔ UMUMAN CHIZILMAGAN holda darvoza, task VA faza ⛔ YASHIL
 *    qaytardi (05-15 ning S-D sinfi). Atribut ro'yxatning O'ZIDA
 *    bo'lgani uchun endi «o'ram bor, mazmun yo'q» holati ⛔ IFODALAB
 *    BO'LMAYDI.
 *
 * -----------------------------------------------------------------------
 * ⛔ BU BLOK KVITANSIYA EMAS — §9.3 NING 1–4 KANALI SHU YERDA
 * -----------------------------------------------------------------------
 *   1. `bg-warning/20` lenta + `border-l-4`  (rang — LEKIN yagona signal emas)
 *   2. `Clock` ikonkasi                      (shakl)
 *   3. `billing.pendingTitle`                (sarlavha)
 *   4. `billing.pendingNotice` — ⛔ TO'LIQ JUMLA («Bu kutilayotgan summa —
 *      hisob hali yozilmagan.»), qisqartma emas
 *
 * ⛔ 6-KANAL — `[Dalilni ko'rish]` BU YERDA YO'Q, chunki dalil YOZILGAN
 *    HISOBGA tegishli va proyeksiyada hisob mavjud emas.
 *
 * ⛔ IDENTIFIKATOR KO'RSATILMAYDI VA U YASHIRILMAGAN — `pendingMarketSummarySchema`
 *    da hisob identifikatori UMUMAN E'LON QILINMAGAN, ya'ni unga murojaat
 *    KOMPILYATSIYA XATOSI. Yashirish kod-ko'rik da'vosi bo'lardi;
 *    yo'qlik esa tip tizimi bilan o'lchanadigan xossa (§9.2).
 *
 * -----------------------------------------------------------------------
 * ⛔ AVTOMATIK TAYMER YO'Q (§9.5) — DAVRIY QAYTA SO'ROV OPSIYASI BERILMAYDI
 * -----------------------------------------------------------------------
 * ⚠ TanStack'ning davriy so'rov opsiyasi bu faylda LITERAL yozilmaydi —
 * uning yo'qligi `grep` darvozasi bilan o'lchanadi va izohdagi nom
 * darvozani o'ziga qarshi qo'yardi (`badge.tsx:24-26` konvensiyasi).
 *
 * Direktor raqamni O'QIB TURGAN paytda uni jimgina o'zgartirib qo'yadigan
 * taymer — «men boshqa raqam ko'rgandim» degan NIZONING MANBAI. Uning
 * o'rniga: `[Yangilash]` tugmasi (qaror FOYDALANUVCHIDA) va
 * `fetched_at` — ⛔ SERVER bergan «olingan vaqt». Vaqt klientda
 * hisoblanmaydi: klient soati siljigan brauzerda u ikkinchi haqiqat
 * bo'lardi.
 *
 * ⛔ NOL — NATIJA: uchala ko'rsatkich ham nol bo'lganda ⛔ HAMON
 *    ko'rinadi. «Bugun hech kim savdo qilmadi» bilan «hisoblagich
 *    ishlamayapti» bir xil ko'rinmasligi kerak (`day-breakdown.tsx:32-38`
 *    qoidasining aynan takrori).
 * =============================================================================
 */

export function PendingSummary() {
  const t = useTranslations();
  const format = useFormatter();
  const pending = useMarketPending();

  return (
    /*
     * ⛔ G-25 (b): ATRIBUT ENG TASHQI ELEMENTDA va u HAR HOLATDA
     *    chiqadi — yuklanish, xato va ma'lumot shoxlarida ham. Aks holda
     *    darvoza «hali yuklanmadi» holatida jimgina qizarardi va keyingi
     *    ijrochi uni «flaky» deb yumshatardi.
     */
    <div
      className="flex flex-col gap-3 border-l-4 border-warning bg-warning/20 p-4 text-text"
      data-billing-content="pending"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 text-sm font-semibold">
          <Clock aria-hidden="true" className="size-4" />
          {t("billing.pendingTitle")}
        </h2>

        <div className="flex flex-wrap items-center gap-3">
          {/*
           * ⛔ VAQT SERVERDAN (`fetched_at`) — klient `Date.now()` bilan
           *    hisoblamaydi. Ikkinchi manba ikkinchi haqiqat bo'lardi.
           */}
          {pending.data !== undefined ? (
            <p className="text-xs text-text-muted">
              {t("billing.fetchedAt")}:{" "}
              <span className="font-mono tabular-nums">
                {format.dateTime(new Date(pending.data.fetched_at), {
                  timeStyle: "short",
                })}
              </span>
            </p>
          ) : null}

          <Button
            onClick={() => void pending.refetch()}
            size="sm"
            variant="secondary"
          >
            {t("billing.refresh")}
          </Button>
        </div>
      </div>

      {/* ⛔ 4-KANAL: TO'LIQ JUMLA, SHARTSIZ — nol natijada ham ko'rinadi. */}
      <p className="text-sm">{t("billing.pendingNotice")}</p>

      {pending.isPending ? (
        <div aria-busy="true" role="status">
          <span className="sr-only">{t("common.loading")}</span>
          <Skeleton className="h-12" />
        </div>
      ) : null}

      {pending.isError ? (
        <p
          className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
          role="alert"
        >
          {t("errors.loadFailedBody")}
        </p>
      ) : null}

      {pending.data !== undefined ? (
        <>
          {/*
           * ⛔ YOPIQ KUN JIM QOLMAYDI (D-24): bugungi patta hisoblanmaydi,
           *    LEKIN eski qarz undiriladi — shuning uchun qarz ko'rsatkichi
           *    bu holatda ham chiziladi.
           */}
          {pending.data.market_open ? null : (
            <p className="text-sm font-semibold">{t("collect.marketClosed")}</p>
          )}

          <dl className="flex flex-wrap gap-x-8 gap-y-3">
            <Metric
              label={t("collect.todayAmount")}
              value={
                <>
                  <span className="font-mono tabular-nums">
                    {format.number(pending.data.pending_amount_soum)}
                  </span>{" "}
                  {t("billing.amountUnit")}
                </>
              }
              /* Display roli — fazaning eng katta raqami (§7.1). */
              valueClassName="text-2xl font-semibold"
            />

            <Metric
              label={t("collect.oldDebt")}
              value={
                <>
                  <span className="font-mono tabular-nums">
                    {format.number(pending.data.outstanding_soum)}
                  </span>{" "}
                  {t("billing.amountUnit")}
                </>
              }
              valueClassName="text-base font-semibold"
            />

            <Metric
              label={t("billing.pendingStalls")}
              /* ⛔ Rasta SONI — pul emas, shuning uchun `amountUnit` YO'Q. */
              value={
                <span className="tabular-nums">
                  {format.number(pending.data.pending_stall_count)}
                </span>
              }
              valueClassName="text-base font-semibold"
            />
          </dl>
        </>
      ) : null}
    </div>
  );
}

/**
 * Bitta ko'rsatkich — raqam va yorliq DASTURIY jihatdan bog'langan.
 *
 * ⚠ VIZUAL TARTIB `order-*` BILAN (`day-breakdown.tsx:209-214` naqshi):
 *   razmetkada `<dt>` `<dd>` dan oldin turadi (HTML `<dl>` talabi),
 *   ekranda esa raqam yorliqdan oldin ko'rinadi — skrinrider «Bugungi
 *   patta: 1 200 000 so'm» deb eshitadi va raqam yolg'iz kelmaydi.
 */
function Metric({
  label,
  value,
  valueClassName,
}: {
  label: string;
  value: ReactNode;
  valueClassName: string;
}) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="order-2 text-xs text-text-muted">{label}</dt>
      <dd className={`order-1 m-0 ${valueClassName}`}>{value}</dd>
    </div>
  );
}
