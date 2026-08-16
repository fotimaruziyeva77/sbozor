"use client";

import { Suspense, useRef } from "react";
import { useTranslations } from "next-intl";

import { ForbiddenNotice } from "@/components/auth/forbidden-notice";
import { AnomalyList } from "@/components/billing/anomaly-list";
import { ChargeList } from "@/components/billing/charge-list";
import { BillingDayPicker, useBillingDay } from "@/components/billing/day-picker";
import { PendingSummary } from "@/components/billing/pending-summary";
import { VarianceList } from "@/components/billing/variance-list";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { useAuthStore } from "@/lib/auth-store";
import { hasPermission } from "@/lib/rbac";

/*
 * =============================================================================
 * Y-4 — HISOBLAR, QARZ, ANOMALIYA VA SMENA FARQI (§11, BILL-02/03/04, CASH-04).
 *
 * ⛔⛔ BU EKRANNING ENG KUCHLI QARORI «KO'RSATISH» EMAS, ⛔ «AJRATISH».
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ G-25 — PROYEKSIYA VA YOZILGAN HISOB BIR EKRANDA UCHRASHMAYDI
 * -----------------------------------------------------------------------
 * Bu D-17 ning eng kuchli kanali (§9.3, 7-kanal) va u ⛔ STRUKTURAVIY,
 * vizual emas. C-3 ga ko'ra hisob ⛔ ERTASI KUNI 04:10 da tug'iladi
 * (`stall_slot_occupancy` D kuni uchun D+1 03:40 da to'ladi), ya'ni
 * bugungi kun uchun yozilgan hisob ⛔ MAVJUD EMAS. Bu TABIIY FAKT UI'da
 * KAFOLATGA aylantiriladi:
 *
 *   `day = bugun`  -> {day, pending, shifts}
 *   `day < bugun`  -> {day, charges, anomalies, shifts}
 *   kesishma       -> {day, shifts}
 *
 * Ya'ni `pending` va `charges` ⛔ HECH QACHON birga chiqmaydi va
 * direktor ikkisini yonma-yon ⛔ KO'RA OLMAYDI — «proyeksiyani
 * kvitansiya deb o'qish» uchun fizik joy qolmaydi.
 *
 * ⛔ «CHIZILMAYDI» DEGANI ⛔ DOM'DA UMUMAN YO'Q. Blokni ko'rinmas qilib
 *    qoldirish (CSS bilan yashirish yoki mos atribut qo'yish) YARAMAYDI:
 *    G-25 blok to'plamining ⛔ TENGLIGI bilan o'lchaydi va yashirilgan
 *    blok to'plamda ⛔ QOLARDI — ya'ni darvoza yashil bo'lib, ekranda
 *    esa ikkalasi ham mavjud bo'lardi.
 *    ⚠ Yashirish usullarining nomlari bu izohda LITERAL yozilmaydi:
 *      ularning yo'qligi `grep` darvozasi bilan o'lchanadi (kodbaza
 *      konvensiyasi, `badge.tsx:24-26`).
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ BU FAYL MAZMUN ATRIBUTINI HECH QACHON YOZMAYDI
 * -----------------------------------------------------------------------
 * ⚠ Atributning NOMI ham bu faylda uchramaydi — uning yo'qligi
 *   mexanik `grep` darvozasi (`0`) bilan o'lchanadi, ya'ni izohdagi
 *   nusxa darvozani o'ziga qarshi qo'yardi.
 *
 * Atribut ⛔ RO'YXAT KOMPONENTINING O'ZIDA. Sabab O'LCHANGAN: G-25 ning
 * eski shakli faqat `data-billing-block` ning ATRIBUT QIYMATLARINI
 * ko'rardi, ya'ni bo'sh `<div data-billing-block="charges" />` uni
 * ⛔ MUKAMMAL qondirardi va BILL-02/03/04 direktor ekranida
 * ⛔ UMUMAN CHIZILMAGAN holda darvoza, task VA faza ⛔ YASHIL qaytardi
 * (05-15 ning S-D sinfi). Agar atribut shu faylda bo'lsa, sahifa
 * darvozani ⛔ PLATSHOLDER BILAN QONDIRA OLARDI — ya'ni o'zining
 * false-green iga o'zi yo'l ochardi.
 *
 * -----------------------------------------------------------------------
 * ⛔ HUQUQ KO'ZGUSI — SO'ROVDAN OLDIN (`occupancy/page.tsx:90-99` naqshi)
 * -----------------------------------------------------------------------
 * `report_view` yo'q sessiyada birorta so'rov UMUMAN ketmaydi. ⚠ Haqiqiy
 * nazorat SERVERDA — hamma marshrut `require_permission(REPORT_VIEW)`
 * ostida; bu yerdagi ko'zgu faqat foydalanuvchini kutilgan raddan
 * oldindan qaytaradi.
 *
 * ⚠ `Suspense` ⛔ MAJBURIY (`occupancy/page.tsx:107-113` da o'lchangan):
 *   ish maydoni `?day=` ni `nuqs` orqali KLIENTDA o'qiydi. Chegara
 *   bo'lmasa Next 16 butun marshrutni statik prerender ro'yxatidan
 *   chiqarib `build` ni yiqitadi.
 *
 * ⛔ DAVR TANLAGICHI, EKSPORT VA DIAGRAMMA YO'Q — 8-fazaning hisobot
 *    yuzasi (§16.1).
 * =============================================================================
 */

export default function BillingPage() {
  const t = useTranslations();
  const { principal } = useAuthStore();

  if (!hasPermission(principal?.roles ?? [], "report_view")) {
    return <ForbiddenNotice />;
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold tracking-tight">
        {t("billing.title")}
      </h1>

      <Suspense
        fallback={
          <p className="text-sm text-text-muted" role="status">
            {t("common.loading")}
          </p>
        }
      >
        <BillingWorkspace />
      </Suspense>
    </div>
  );
}

/* --- Ish maydoni ---------------------------------------------------------- */

function BillingWorkspace() {
  const t = useTranslations();
  const selection = useBillingDay();
  const anomaliesRef = useRef<HTMLDivElement | null>(null);

  return (
    <div className="flex flex-col gap-6">
      {/* --- A: KUN TANLAGICHI — ikkala kunda ham -------------------------- */}
      <section data-billing-block="day">
        <BillingDayPicker />
      </section>

      {/*
       * --- B: KUTILAYOTGAN PATTA — ⛔ FAQAT `day = bugun` ----------------
       *
       * ⛔ `day < bugun` da bu blok DOM'da UMUMAN YO'Q: o'tgan kun uchun
       *    «kutilayotgan» summa ma'nosiz va u yozilgan hisob yonida
       *    tursa ikkinchi, raqobatchi son bo'lardi.
       */}
      {selection.isToday ? (
        <section data-billing-block="pending">
          <PendingSummary />
        </section>
      ) : null}

      {/*
       * --- C va D: YOZILGAN HISOB VA ANOMALIYA — ⛔ FAQAT `day < bugun` --
       */}
      {selection.isToday ? null : (
        <>
          <section data-billing-block="charges">
            <ChargeList
              day={selection.day}
              onGoToAnomalies={() =>
                anomaliesRef.current?.scrollIntoView({ block: "start" })
              }
            />
          </section>

          <section data-billing-block="anomalies" ref={anomaliesRef}>
            <AnomalyList day={selection.day} />
          </section>
        </>
      )}

      {/*
       * --- BO'SH HOLAT №4 (§13.8) — ⛔ BLOK EMAS, BLOKNING YO'QLIGI ------
       *
       * ⛔ BU JUMLA `data-billing-block` ATRIBUTINI OLMAYDI. Olsa,
       *    `day = bugun` to'plami `{day, pending, shifts}` bo'lmay
       *    qolardi va G-25 (a) ⛔ NOTO'G'RI SABABDAN qizarardi.
       *
       * ⛔ TAVSIF C-3 NI OCHIQ TUSHUNTIRADI: tushuntirilmasa direktor
       *    bo'sh sahifani ⛔ NOSOZLIK deb o'qirdi — 4-fazadagi «bo'sh
       *    katak» sinfidagi jim xato.
       */}
      {selection.isToday ? (
        <EmptyState
          action={
            <Button
              onClick={() => selection.setDay(selection.yesterdayIso)}
              size="sm"
              variant="secondary"
            >
              {t("billing.goYesterday")}
            </Button>
          }
          description={t("billing.chargesLaterNotice")}
          title={t("billing.emptyToday")}
        />
      ) : null}

      {/*
       * --- E: SMENA FARQI — ⛔ IKKALA KUNDA HAM ---------------------------
       *
       * Smena kun ICHIDA yopiladi, ya'ni «bugun» uchun ham yopilgan
       * smena bo'lishi mumkin (§11.2, E qatori). Shuning uchun u
       * `day` bilan birga G-25 kesishmasining a'zosi.
       */}
      <section data-billing-block="shifts">
        <VarianceList day={selection.day} />
      </section>
    </div>
  );
}
