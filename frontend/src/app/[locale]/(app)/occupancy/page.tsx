"use client";

import { Suspense, useState } from "react";
import { useLocale, useTranslations } from "next-intl";

import { localeHref } from "@/lib/locale-href";
import { BrandLoader } from "@/components/ui/brand-loader";
import { ForbiddenNotice } from "@/components/auth/forbidden-notice";
import { ConfusionMatrix } from "@/components/occupancy/confusion-matrix";
import { DayBreakdown } from "@/components/occupancy/day-breakdown";
import { RoundSummary } from "@/components/occupancy/round-summary";
import {
  StallDayList,
  useNoCoverageOnly,
} from "@/components/occupancy/stall-day-list";
import { StallDetailDialog } from "@/components/occupancy/stall-detail-dialog";
import { DayPicker, useDaySelection } from "@/components/snapshots/day-picker";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import type { OccupancyStallItem } from "@/lib/api-types";
import { useAuthStore } from "@/lib/auth-store";
import {
  useAccuracyReport,
  useAuditRound,
  useOccupancyDay,
} from "@/lib/occupancy-queries";
import { hasPermission } from "@/lib/rbac";

/*
 * =============================================================================
 * BANDLIK VA ANIQLIK HISOBOTI — Y-4 (UI-SPEC §11).
 *
 * ⛔⛔ BU DIREKTORNING YUZASI (`report_view`), NAZORATCHINING EMAS.
 *
 *     `ROLE_PERMISSIONS[inspector]` — aynan `{occupancy_review}`, ya'ni
 *     nazoratchi bu sahifani UMUMAN ocha olmaydi (T-05-69). Sabab
 *     maxfiylikda emas: nazoratchi O'Z aniqligini ko'rsa u RAQAMNI
 *     YAXSHILASHGA urinardi va o'lchov o'zi o'lchayotgan narsani
 *     o'zgartirardi. «Tez qaror» sanog'i esa aynan o'sha urinishning izi
 *     bo'lib qolardi.
 *
 * TO'RT VERTIKAL ZONA (§11.1) va ular HECH QACHON ALMASHMAYDI:
 *   (A) kun tanlagichi + kunlik xulosa   — besh hisoblagich;
 *   (B) aniqlik                          — chalkashlik matritsasi;
 *   (C) namuna holati                    — o'lchovning O'ZI;
 *   (D) rastalar ro'yxati                — DL-5 ni ochadi.
 *
 * ⛔ KUN ALMASHTIRILGANDA MAZMUN O'CHMAYDI (§8.4 O-2): zona
 *    `aria-busy="true"` oladi va joyida qoladi. Zona (B) esa kun bilan
 *    UMUMAN o'zgarmaydi — u kunlik emas, oyning TO'PLANGAN namunasi.
 *
 * ⛔ E-6 «0 BAND» EMAS (§8.4 O-3). `stalls === 0` — «kun hali
 *    yopilmagan», «hamma rasta bo'sh» EMAS: `day_summary` ning tashqi
 *    `SELECT` i agregat va materializatsiya qilinmagan kunda oltala son
 *    ham `0` bo'ladi. Ikkisini bir xil ko'rsatish direktorni «bugun hech
 *    kim savdo qilmabdi» degan xulosaga olib borardi.
 *
 * ⚠ HUQUQ TEKSHIRUVI SO'ROVDAN OLDIN (`review/page.tsx:87-91` naqshi):
 *   huquqsiz sessiyada uchala so'rov ham UMUMAN ketmaydi. Haqiqiy
 *   nazorat serverda — uchala marshrut ham `require_permission(REPORT_VIEW)`.
 *
 * ⛔ DAVR TANLAGICHI, EKSPORT TUGMASI VA DIAGRAMMA YO'Q (§16.1): ular
 *    8-fazaning hisobot yuzasi.
 * =============================================================================
 */

export default function OccupancyPage() {
  const t = useTranslations();
  const { principal } = useAuthStore();

  /*
   * ⛔⛔ IKKI HUQUQDAN BIRI YETARLI (260820).
   *
   *     Ilgari bu yerda faqat `report_view` turardi va NAZORATCHI
   *     403 olardi — holbuki bandlikni AYNAN U o'lchaydi va
   *     sahifaning O'ZIDA unga atalgan shox bor (`canReview`).
   *     Ya'ni ekran nazoratchini kutardi, eshik esa yopiq edi.
   *
   *     Natijasi buzuq halqa: nazoratchi kun bo'yi kadr ko'rib
   *     qaror yozadi, lekin o'z ishining NATIJASINI ko'ra olmaydi.
   *
   * ⚠ SIZIB CHIQISH YO'Q: bu yuzada PUL maydoni umuman yo'q —
   *   javob `stalls/occupied/empty/no_coverage/human_confirmed`
   *   sanoqlaridan iborat (`occupancy.py`).
   */
  const roles = principal?.roles ?? [];
  if (
    !hasPermission(roles, "report_view") &&
    !hasPermission(roles, "occupancy_review")
  ) {
    return <ForbiddenNotice />;
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold tracking-tight">
        {t("occupancy.title")}
      </h1>

      {/*
       * `Suspense` MAJBURIY (`snapshots/page.tsx:100-111` naqshi): ish
       * maydoni `?day=` ni `nuqs` orqali o'qiydi, ya'ni daraxtning shu
       * qismi klient tomonda render qilinadi. Chegara bo'lmasa Next 16
       * butun marshrutni statik prerender ro'yxatidan chiqarib, BUILD ni
       * yiqitadi.
       */}
      <Suspense
        fallback={
          <BrandLoader />
        }
      >
        <OccupancyWorkspace />
      </Suspense>
    </div>
  );
}

/* --- Ish maydoni ---------------------------------------------------------- */

function OccupancyWorkspace() {
  const t = useTranslations();
  const locale = useLocale();
  const { principal } = useAuthStore();
  const { day, todayIso } = useDaySelection();

  const canReview = hasPermission(principal?.roles ?? [], "occupancy_review");
  /*
   * ⛔ ANIQLIK — FAQAT HISOBOT HUQUQIDA (260827, T-05-58 ning davomi).
   *
   * Sahifaning o'zi ikki huquqdan biri bilan ochiladi (yuqoridagi izoh),
   * LEKIN `/occupancy/accuracy` serverda `REPORT_VIEW` ostida QOLADI:
   * nazoratchi o'z ANIQLIGINI ko'rsa raqamni yaxshilashga urinardi.
   *
   * ⚠ `enabled` — QULAYLIK EMAS, ZARURAT: usiz nazoratchi sessiyasida
   *   so'rov baribir ketardi, 403 olardi va UI uni «Ma'lumot yuklanmadi»
   *   deb ko'rsatardi — ya'ni huquq qarori nosozlikka o'xshab qolardi.
   *   Haqiqiy nazorat serverda; bu — o'sha qarorning ko'zgusi.
   */
  const canSeeAccuracy = hasPermission(principal?.roles ?? [], "report_view");
  const occupancy = useOccupancyDay(day, todayIso);
  const accuracy = useAccuracyReport({ enabled: canSeeAccuracy });
  const round = useAuditRound(day, todayIso);
  const [noCoverageOnly, setNoCoverageOnly] = useNoCoverageOnly();

  /*
   * ⚠ DL-5 HOLATI URL'DA EMAS (`snapshots/page.tsx:244-249` naqshi):
   *   URL'da faqat `?day=` va `?nocov=` yashaydi. Rasta tafsilotini
   *   ulashiladigan havolaga aylantirish uni sahifa holatidan marshrutga
   *   ko'chirardi va «orqaga» tugmasi dialogni qayta ochardi.
   */
  const [openStall, setOpenStall] = useState<OccupancyStallItem | null>(null);

  return (
    <div className="flex flex-col gap-6">
      {/* --- ZONA (A): kun tanlagichi + kunlik xulosa -------------------- */}
      <section
        aria-busy={occupancy.isFetching}
        aria-label={t("occupancy.summaryTitle")}
        className="flex flex-col gap-3"
      >
        {/*
         * ⛔ TANLAGICH 4-FAZANIKI VA U QAYTA TA'RIFLANMAYDI (§11.2).
         *    Yagona farq — «kelajak tanlanmaydi» ning SABABI.
         */}
        <DayPicker noFutureDaysKey="occupancy.noFutureDays" />

        {occupancy.isPending ? (
          /* O-1 — birinchi yuklash: BITTA `Skeleton` qator (§8.4). */
          <Card>
            <CardContent className="pt-5">
              <div aria-busy="true" role="status">
                <span className="sr-only">{t("common.loading")}</span>
                <Skeleton className="h-16" />
              </div>
            </CardContent>
          </Card>
        ) : null}

        {occupancy.isError ? (
          /* O-5 — meros xato bloki (`day-summary.tsx:151-169`). */
          <Card>
            <CardContent className="pt-5">
              <div
                className="flex flex-col items-start gap-3 rounded-md bg-danger/10 p-4 text-danger-text"
                role="alert"
              >
                <p className="text-sm font-semibold">{t("errors.loadFailedTitle")}</p>
                <p className="text-sm">{t("errors.loadFailedBody")}</p>
                <Button
                  onClick={() => void occupancy.refetch()}
                  size="sm"
                  variant="secondary"
                >
                  {t("common.retry")}
                </Button>
              </div>
            </CardContent>
          </Card>
        ) : null}

        {occupancy.data !== undefined ? (
          occupancy.data.stalls === 0 ? (
            /*
             * ⛔ O-3 — E-6. «Bu kunda bandlik hisoblanmagan», «0 band»
             *    EMAS. Amal `/cameras` ga olib boradi, chunki sababning
             *    ikkala shakli ham (yaroqli kadr yo'q / zona chizilmagan)
             *    o'sha yerda ko'rinadi.
             */
            <Card>
              <CardContent className="pt-5">
                <EmptyState
                  action={
                    <a
                      className="inline-flex min-h-11 items-center rounded-md border border-border bg-surface px-6 text-sm font-semibold text-text hover:bg-surface-muted"
                      href={localeHref(locale, "/cameras")}
                    >
                      {t("occupancy.goToCameras")}
                    </a>
                  }
                  description={t("occupancy.emptyDayHint")}
                  title={t("occupancy.emptyDay")}
                />
              </CardContent>
            </Card>
          ) : (
            <DayBreakdown
              canReview={canReview}
              onGoToReview={
                <a
                  className="inline-flex min-h-11 items-center rounded-md border border-border bg-surface px-4 text-sm font-semibold text-text hover:bg-surface-muted"
                  href={localeHref(locale, "/review")}
                >
                  {t("occupancy.goToReview")}
                </a>
              }
              summary={occupancy.data}
            />
          )
        ) : null}
      </section>

      {/* --- ZONA (B): aniqlik ------------------------------------------- */}
      {/*
       * ⛔ ZONA (B) KUN BILAN O'ZGARMAYDI (§11.1) va shuning uchun u
       *    `aria-busy` ni kunlik so'rovdan OLMAYDI: u oyning to'plangan
       *    namunasi. Kun almashtirilganda bu blok umuman qayta
       *    so'ralmaydi.
       */}
      {/*
       * ⛔ NAZORATCHIDA ZONA (B) UMUMAN CHIZILMAYDI: bo'sh skelet yoki
       *    xato bloki «bu yerda men ko'ra olmaydigan narsa bor» degan
       *    savolni tug'dirardi. Yo'qlik — eng toza javob.
       */}
      {canSeeAccuracy ? (
      <section
        aria-busy={accuracy.isFetching}
        aria-label={t("occupancy.accuracyTitle")}
      >
        {accuracy.isPending ? (
          <Card>
            <CardContent className="pt-5">
              <div aria-busy="true" role="status">
                <span className="sr-only">{t("common.loading")}</span>
                <Skeleton className="h-40" />
              </div>
            </CardContent>
          </Card>
        ) : accuracy.isError ? (
          <Card>
            <CardContent className="pt-5">
              <p
                className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
                role="alert"
              >
                {t("errors.loadFailedBody")}
              </p>
            </CardContent>
          </Card>
        ) : (
          <ConfusionMatrix report={accuracy.data} />
        )}
      </section>
      ) : null}

      {/* --- ZONA (C): namuna holati ------------------------------------- */}
      <section aria-busy={round.isFetching} aria-label={t("occupancy.roundTitle")}>
        {round.isPending ? (
          <Card>
            <CardContent className="pt-5">
              <div aria-busy="true" role="status">
                <span className="sr-only">{t("common.loading")}</span>
                <Skeleton className="h-24" />
              </div>
            </CardContent>
          </Card>
        ) : round.isError ? (
          <Card>
            <CardContent className="pt-5">
              <p
                className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
                role="alert"
              >
                {t("errors.loadFailedBody")}
              </p>
            </CardContent>
          </Card>
        ) : (
          <RoundSummary round={round.data} />
        )}
      </section>

      {/* --- ZONA (D): rastalar ro'yxati ---------------------------------- */}
      {/*
       * ⚠ RO'YXAT XULOSA BILAN AYNI SO'ROVDAN keladi va u kun
       *   almashtirilganda `aria-busy` oladi, MAZMUNI esa joyida qoladi
       *   (§8.4 O-2). `stalls === 0` bo'lgan kunda ro'yxat umuman
       *   chizilmaydi — E-6 allaqachon sababni aytgan.
       */}
      {occupancy.data !== undefined && occupancy.data.stalls > 0 ? (
        <section
          aria-busy={occupancy.isFetching}
          aria-label={t("occupancy.stallsTitle")}
        >
          <StallDayList
            items={occupancy.data.items}
            noCoverageOnly={noCoverageOnly}
            onNoCoverageOnlyChange={setNoCoverageOnly}
            onOpen={setOpenStall}
          />
        </section>
      ) : null}

      <StallDetailDialog
        item={openStall}
        onOpenChange={(open) => {
          if (!open) setOpenStall(null);
        }}
      />
    </div>
  );
}
