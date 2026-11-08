"use client";

import type { ReactNode } from "react";
import {
  useFormatter,
  useLocale,
  useNow,
  useTimeZone,
  useTranslations,
} from "next-intl";
import { Banknote, Camera, ReceiptText, Store } from "lucide-react";

import {
  captureBuckets,
  countStallDays,
  expectedStalls,
} from "@/components/director/chart-data";
import {
  CollectedPartTiles,
  usePeriodSub,
} from "@/components/director/collected-parts";
import type { Period } from "@/components/director/period";
import {
  comparePeriod,
  debtWindow,
  includesToday,
  periodDays,
} from "@/components/director/period";
import {
  parkingTotalOf,
  usePanelParkingReport,
} from "@/components/director/use-panel-parking";
import { PanelTile } from "@/components/panel/tile";
import { businessDayIn, shiftIsoDay } from "@/components/snapshots/day-picker";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuthStore } from "@/lib/auth-store";
import { cn } from "@/lib/cn";
import { formatBusinessDay } from "@/lib/format-day";
import { deltaView, formatAmount, formatSoum } from "@/lib/format-number";
import { useMapDayStatusQuery } from "@/lib/map-day-queries";
import { useSetupStatusQuery } from "@/lib/market-queries";
import { hasPermission } from "@/lib/rbac";
import { useLiveRevenue, useReceivablesReport } from "@/lib/report-queries";
import { useCaptureDays } from "@/lib/snapshot-queries";

/*
 * =============================================================================
 * PANELNING BOSH QATORI — TO'RTTA ODDIY SAVOL (261016).
 *
 * ⛔⛔ NEGA ALMASHTIRILDI. Foydalanuvchi bosh katak va olti katakli to'rni
 *     ko'rsatib aytdi: «buni hech kim tushunmayapti». Ekranda bo'sh halqa
 *     «—», «Patta yig'ilish darajasi», «Kun yopilmagan», «Ishonch
 *     oralig'i», «Band, lekin to'lovsiz» kabi atamalar va kun boshida
 *     «−100%» turardi — direktor ulardan hech birini «hozir nima
 *     bo'lyapti» savoliga javob sifatida o'qiy olmasdi.
 *
 * Endi to'rt katak — har biri ODDIY SAVOLGA bitta son bilan javob beradi
 * va sonning ostida u nimani anglatishi ODDIY GAP bilan yoziladi:
 *
 *   1. Tushum       — «qancha pul yig'ildi?»       (tanlangan davr;
 *                     261103 dan rastalar + avtoturargoh)
 *   2. To'lagan     — «nechta rasta to'ladi?»      (bugun, xaritadan)
 *   3. Qarz         — «kimda qancha qarz bor?»     (reestr holati)
 *   4. Kameralar    — «kameralar ishlayaptimi?»    (bugungi kadrlar)
 *
 * ⛔ SO'ROVLAR YANGI EMAS: har katak pastdagi grafik bilan AYNI kalitdan
 *    o'qiydi (`useLiveRevenue`, `/billing/map`, `debtWindow`,
 *    `useCaptureDays`) — katak va grafik bir javobdan chiziladi va ikki
 *    joyda ikki xil son ko'rinmaydi.
 *
 * ⛔ TUGAMAGAN KUN FOIZ BILAN SOLISHTIRILMAYDI: kun boshida «−100%»
 *    yolg'on xavotir edi. Davr bugunni qamrasa oldingi davrning SUMMASI
 *    oddiy gap bilan yoziladi, foiz esa faqat ikkala davr yopilganda.
 * =============================================================================
 */

/** Kamera katagi qarab chiqadigan kunlar (grafik bilan bir xil oyna). */
const CAPTURE_DAYS = 7;

export function DirectorKpis({ period }: { period: Period }) {
  const t = useTranslations();
  const roles = useAuthStore().principal?.roles ?? [];

  /*
   * ⛔ 261108 (buyurtmachi): buxgalterga pul UCH alohida son bilan — umumiy,
   *    patta, tarozi. Bu pulni ko'rish huquqi emas (u direktorda ham bor),
   *    balki buxgalter ekranining tartibi, shuning uchun shart ROLDA.
   *    Direktor paneli o'zgarmaydi.
   */
  if (roles.includes("accountant")) {
    return (
      <div className="dir-kpis">
        <div className="col-span-full grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-3">
          <RevenueKpi
            className="col-span-2 lg:col-span-1"
            label={t("director.kpiTotalMoney")}
            period={period}
          />
          <CollectedPartTiles period={period} />
        </div>
        <div className="col-span-full grid grid-cols-2 gap-3 sm:gap-4">
          <StallsKpi />
          <DebtKpi period={period} />
          <CameraKpi />
        </div>
      </div>
    );
  }

  return (
    <div className="dir-kpis">
      <RevenueKpi period={period} />
      <StallsKpi />
      <DebtKpi period={period} />
      <CameraKpi />
    </div>
  );
}

/** Katakning bosh soni — raqam katta, birlik kichik (telefonda sig'sin). */
function KpiAmount({ value, tone }: { value: number; tone?: "danger" }) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();
  return (
    <p className={cn("dir-kpi-value", tone === "danger" && "text-danger-text")}>
      {formatAmount(format, value, locale)}{" "}
      <span className="dir-kpi-unit">{t("reports.amountUnit")}</span>
    </p>
  );
}

function KpiLoading() {
  return <Skeleton className="dir-kpi-skeleton" />;
}

/** Katak ostidagi oddiy gap — ohangi ma'nosiga qarab. */
function KpiNote({
  tone,
  children,
}: {
  tone?: "success" | "warning" | "danger";
  children: ReactNode;
}) {
  return (
    <span
      className={cn(
        tone === "danger" && "text-danger-text",
        tone === "warning" && "text-warning-text",
        tone === "success" && "text-success-text",
      )}
    >
      {children}
    </span>
  );
}

/* -------------------------------------------------------------------------- */
/* 1. Tushum                                                                  */
/* -------------------------------------------------------------------------- */

/**
 * Katakning soni: rastalar + avtoturargoh (261103, buyurtmachi: «faqat
 * rasta pulini emas, avtoturargoh pulini ham qo'sh»).
 *
 *   `parking === null` — avtoturargoh yo'q, huquq yo'q yoki so'rov
 *   yiqildi: son BUGUNGI holicha (faqat rastalar), bo'linish chizilmaydi.
 *
 * ⛔ Taqqoslash ham JAMI bilan: joriy jami oldingi davrning faqat rasta
 *    puli bilan solishtirilsa foiz soxta o'sishni ko'rsatardi. Oldingi
 *    davrning avtoturargoh soni noma'lum bo'lsa taqqoslash CHIZILMAYDI.
 */
export function revenueTotals(
  stalls: number | null,
  parking: number | null,
  previousStalls: number | null,
  previousParking: number | null,
): { current: number | null; previous: number | null } {
  if (parking === null) return { current: stalls, previous: previousStalls };
  return {
    current: stalls === null ? null : stalls + parking,
    previous:
      previousStalls === null || previousParking === null
        ? null
        : previousStalls + previousParking,
  };
}

function RevenueKpi({
  period,
  label,
  className,
}: {
  period: Period;
  /** Buxgalterda «Umumiy pul»; berilmasa — «Tushum». */
  label?: string;
  className?: string;
}) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();
  const timeZone = useTimeZone() ?? "Asia/Tashkent";
  const now = useNow();
  const todayIso = businessDayIn(timeZone, now);
  const sub = usePeriodSub(period);

  const prev = comparePeriod(period);
  const live = useLiveRevenue({ from: period.from, to: period.to });
  const livePrev = useLiveRevenue({ from: prev.from, to: prev.to });
  const parking = usePanelParkingReport(period);
  const parkingPrev = usePanelParkingReport(prev);

  const stalls = live.data?.total_collected_soum ?? null;
  const parkingSum = parking.pending ? null : parkingTotalOf(parking);
  const { current, previous } = revenueTotals(
    stalls,
    parkingSum,
    livePrev.data?.total_collected_soum ?? null,
    parkingPrev.pending ? null : parkingTotalOf(parkingPrev),
  );
  const open = includesToday(period, todayIso);

  /* ⛔ Foiz FAQAT ikkala davr yopilganda (modul izohi). */
  const delta =
    open || current === null || previous === null
      ? null
      : deltaView(current, previous, {
          goodIsUp: true,
          bothClosed: true,
          notCompleteText: t("common.deltaNotComplete"),
          noChangeText: t("common.deltaNoChange"),
        });

  return (
    <PanelTile
      className={className}
      href="/reports"
      icon={Banknote}
      label={label ?? t("director.kpiRevenue")}
      note={
        previous === null ? undefined : (
          <KpiNote>
            {t(periodDays(period) === 1 ? "director.kpiPrevDay" : "director.kpiPrevSpan", {
              sum: formatSoum(format, previous, locale),
            })}
          </KpiNote>
        )
      }
      step={0}
      sub={sub}
    >
      {/*
       * ⛔ Avtoturargoh soni kelguncha skeleton: rastalar summasini «jami»
       *    deb ko'rsatib, bir lahzadan keyin kattaroq songa sakrash —
       *    direktorga ikki xil javob berish bo'lardi.
       */}
      {live.isLoading || parking.pending ? (
        <KpiLoading />
      ) : current === null ? (
        <p className="dir-kpi-value text-text-muted">—</p>
      ) : (
        <div className="flex flex-col gap-1.5">
          <div className="flex flex-wrap items-baseline gap-2">
            <KpiAmount value={current} />
            {delta === null ? null : <Badge tone={delta.tone}>{delta.text}</Badge>}
          </div>
          {/* Bo'linish — FAQAT avtoturargoh soni ma'lum bo'lganda. */}
          {stalls === null || parkingSum === null ? null : (
            <p className="dir-kpi-split">
              <span>
                {t("director.kpiRevenueStalls", {
                  sum: formatAmount(format, stalls, locale),
                })}
              </span>
              <span>
                {t("director.kpiRevenueParking", {
                  sum: formatAmount(format, parkingSum, locale),
                })}
              </span>
            </p>
          )}
        </div>
      )}
    </PanelTile>
  );
}

/* -------------------------------------------------------------------------- */
/* 2. Bugun to'lagan rastalar                                                 */
/* -------------------------------------------------------------------------- */

function StallsKpi() {
  const t = useTranslations();
  const dayLayer = useMapDayStatusQuery();

  /* ⛔ Huquqsiz sessiyada katak yo'q — so'rov ham ketmagan. */
  if (!dayLayer.isEnabled) return null;

  const status = dayLayer.status;
  const counts = countStallDays(status?.market_active === true ? status.rows : []);
  const expected = expectedStalls(counts);
  const unpaid = counts.due + counts.mismatch;
  const percent = expected === 0 ? 0 : (counts.paid / expected) * 100;

  let note: ReactNode;
  if (status !== null && !status.market_active) {
    note = <KpiNote>{t("director.kpiStallsDraft")}</KpiNote>;
  } else if (status !== null && status.market_open === false) {
    note = <KpiNote>{t("director.kpiStallsClosed")}</KpiNote>;
  } else if (expected === 0) {
    note = <KpiNote>{t("director.kpiStallsNone")}</KpiNote>;
  } else if (unpaid > 0) {
    note = (
      <KpiNote tone="danger">
        {t("director.kpiStallsUnpaid", { count: unpaid })}
      </KpiNote>
    );
  } else {
    note = <KpiNote tone="success">{t("director.kpiStallsAllPaid")}</KpiNote>;
  }

  return (
    <PanelTile
      href="/map"
      icon={Store}
      label={t("director.kpiStalls")}
      note={dayLayer.isPending || dayLayer.isError ? undefined : note}
      step={1}
      sub={t("director.periodToday")}
    >
      {dayLayer.isPending ? (
        <KpiLoading />
      ) : dayLayer.isError || status === null ? (
        <p className="dir-kpi-value text-text-muted">—</p>
      ) : (
        <div className="flex flex-col gap-2.5">
          <p className="dir-kpi-value">
            {expected === 0 ? "—" : `${counts.paid} / ${expected}`}
            <span className="dir-kpi-unit"> {t("director.kpiStallsUnit")}</span>
          </p>
          {/*
           * ⛔ Chiziq — to'langan ulushi, yashil: «qancha qismi yopildi».
           *    Son yonida turibdi — chiziq faqat shakl.
           */}
          {expected === 0 ? null : (
            <div aria-hidden="true" className="dir-kpi-meter">
              <span style={{ width: `${percent}%` }} />
            </div>
          )}
        </div>
      )}
    </PanelTile>
  );
}

/* -------------------------------------------------------------------------- */
/* 3. Qarz                                                                    */
/* -------------------------------------------------------------------------- */

function DebtKpi({ period }: { period: Period }) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();
  const timeZone = useTimeZone() ?? "Asia/Tashkent";
  const now = useNow();
  const todayIso = businessDayIn(timeZone, now);

  const debtors = useReceivablesReport(debtWindow(period, todayIso));
  const total = debtors.data?.total_outstanding_soum ?? null;
  const debtorCount =
    debtors.data?.rows.filter((row) => row.outstanding_soum > 0).length ?? 0;
  /*
   * ⛔ Eng eski qarz sanasi — qatorlardagi MINIMUM; `null` lar tashlanadi
   *    (to'qilgan sana chizilmaydi, D-10).
   */
  const oldest =
    debtors.data?.rows
      .filter((row) => row.outstanding_soum > 0)
      .map((row) => row.oldest_debt_date)
      .filter((value): value is string => value !== null)
      .sort()[0] ?? null;

  let note: ReactNode = undefined;
  if (total !== null && total < 0) {
    /* ⛔ MANFIY QOLDIQ — AVANS, qarz emas: qizil rang yolg'on bo'lardi. */
    note = <KpiNote>{t("director.advanceNote")}</KpiNote>;
  } else if (total !== null && debtorCount > 0) {
    note = (
      <KpiNote>
        {t("director.debtVendors", { count: debtorCount })}
        {oldest === null
          ? ""
          : ` · ${t("director.debtOldest", { date: formatBusinessDay(format, oldest, locale) })}`}
      </KpiNote>
    );
  } else if (total !== null) {
    note = <KpiNote tone="success">{t("director.kpiDebtNone")}</KpiNote>;
  }

  return (
    <PanelTile
      href="/reports/vendor"
      icon={ReceiptText}
      label={t("director.kpiDebt")}
      note={note}
      step={2}
      sub={t("director.registrySub", {
        date: formatBusinessDay(format, todayIso, locale),
      })}
    >
      {debtors.isLoading ? (
        <KpiLoading />
      ) : total === null ? (
        <p className="dir-kpi-value text-text-muted">—</p>
      ) : (
        <KpiAmount tone={total > 0 ? "danger" : undefined} value={total} />
      )}
    </PanelTile>
  );
}

/* -------------------------------------------------------------------------- */
/* 4. Kameralar                                                               */
/* -------------------------------------------------------------------------- */

/**
 * Kadr kelmagan KETMA-KET kunlar — bugundan orqaga.
 *
 * ⛔ Bugun hali reja bo'yicha olinmagan kadrlar «kelmadi» deb SANALMAYDI:
 *    kun boshida hammasi navbatda turadi. Bugun faqat yo'qolgan (`lost`)
 *    kadr bo'lsa va bitta ham olinmagan bo'lsa hisobga kiradi.
 */
export function daysWithoutFrames(
  days: readonly { planned: number; ok: number; poor: number; lost: number }[],
): number {
  let streak = 0;
  for (let index = days.length - 1; index >= 0; index -= 1) {
    const day = days[index];
    if (day === undefined || day.planned === 0) break;
    const captured = day.ok + day.poor;
    if (captured > 0) break;
    if (index === days.length - 1 && day.lost === 0) continue;
    streak += 1;
  }
  return streak;
}

function CameraKpi() {
  const t = useTranslations();
  const timeZone = useTimeZone() ?? "Asia/Tashkent";
  const now = useNow();
  const principal = useAuthStore().principal;
  const marketId = principal?.marketId ?? null;
  const allowed = hasPermission(principal?.roles ?? [], "camera_view");

  const todayIso = businessDayIn(timeZone, now);
  const days = Array.from({ length: CAPTURE_DAYS }, (_, index) =>
    shiftIsoDay(todayIso, index - (CAPTURE_DAYS - 1)),
  );
  const setup = useSetupStatusQuery(marketId, { enabled: allowed });
  const results = useCaptureDays(days, { enabled: allowed });

  /* ⛔ Kamerasiz bozorda va huquqsiz sessiyada katak yo'q. */
  if (!allowed || setup.data?.cameras === 0) return null;

  const loading = results.some((result) => result.isLoading);
  const summaries = results.map((result) => result.data?.summary);
  const today = summaries[summaries.length - 1];
  const buckets = summaries.flatMap((summary) =>
    summary === undefined ? [] : [captureBuckets(summary)],
  );
  const streak =
    buckets.length === summaries.length ? daysWithoutFrames(buckets) : 0;
  const todayBuckets = today === undefined ? null : captureBuckets(today);

  let note: ReactNode = undefined;
  if (todayBuckets !== null) {
    if (todayBuckets.planned === 0) {
      note = <KpiNote>{t("director.kpiCameraNoPlan")}</KpiNote>;
    } else if (streak > 0) {
      note = (
        <KpiNote tone="danger">
          {t("director.kpiCameraDown", { days: streak })}
        </KpiNote>
      );
    } else if (todayBuckets.lost > 0) {
      note = (
        <KpiNote tone="warning">
          {t("director.kpiCameraLost", { count: todayBuckets.lost })}
        </KpiNote>
      );
    } else {
      note = <KpiNote tone="success">{t("director.kpiCameraOk")}</KpiNote>;
    }
  }

  return (
    <PanelTile
      href="/snapshots"
      icon={Camera}
      label={t("director.kpiCamera")}
      note={note}
      step={3}
      sub={t("director.kpiCameraSub")}
    >
      {loading && today === undefined ? (
        <KpiLoading />
      ) : today === undefined ? (
        <p className="dir-kpi-value text-text-muted">—</p>
      ) : (
        <p className={cn("dir-kpi-value", streak > 0 && "text-danger-text")}>
          {today.planned === 0 ? "—" : `${today.done} / ${today.planned}`}
          <span className="dir-kpi-unit"> {t("director.kpiCameraUnit")}</span>
        </p>
      )}
    </PanelTile>
  );
}
