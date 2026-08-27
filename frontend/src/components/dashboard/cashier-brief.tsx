"use client";

import { useEffect, useState } from "react";
import type { ComponentType } from "react";
import {
  ArrowRight,
  CircleAlert,
  CircleCheck,
  CircleDot,
  FileText,
  HandCoins,
  Info,
  LayoutGrid,
  LogOut,
  RefreshCw,
  TriangleAlert,
} from "lucide-react";
import { useFormatter, useLocale, useTranslations } from "next-intl";

import { Card, CardContent } from "@/components/ui/card";
import { BrandLoader } from "@/components/ui/brand-loader";
import { Link } from "@/i18n/navigation";
import { useCollectRoster } from "@/lib/collect-roster-queries";
import { formatBusinessDay } from "@/lib/format-day";
import { formatAmount } from "@/lib/format-number";
import { useHeadline } from "@/lib/headline-queries";
import type { PaymentRecord } from "@/lib/payment-queries";
import { useRecentPayments } from "@/lib/payment-queries";
import { useOpenShift } from "@/lib/shift-queries";
import { cn } from "@/lib/cn";

const LONG_SHIFT_HOURS = 14;
/**
 * Smena shuncha soatdan oshsa ogohlantirish chiqadi (J-01).
 *
 * 14 — bozor ish kunidan (06:00–18:00) UZUN, lekin bir kecha
 * o'tishidan QISQA. Ya'ni u odatiy uzun kunni bezovta qilmaydi,
 * «yopishni unutdim» holatini esa o'sha kuni ushlaydi.
 */

/*
 * =============================================================================
 * KASSIR PANELI — bosh ekranning kassir uchun mazmuni (260819; 2026-08-25
 * foydalanuvchi maketi bo'yicha ikkinchi marta qayta qurildi).
 *
 * Maket tuzilishi (chap 2/3 + o'ng 1/3):
 *   chap  — «Smena holati» (belgi, boshlangan vaqt, JONLI davomiylik,
 *           smena raqami, yopish tugmasi) -> «Patta yig'ish» gero
 *           (sanoq-progress + katta CTA) -> tezkor amallar qatori;
 *   o'ng  — «Bugungi natija» (uch SANOQ) -> «Oxirgi to'lovlar» (server
 *           bergan ≤5 qator) -> «Barcha to'lovlar».
 *
 * ⛔⛔ FAQAT BACKENDDA BOR MA'LUMOT (foydalanuvchi buyrug'i 2026-08-25):
 *     smena {id, opened_at} · roster SANOQLARI · headline SONI · oxirgi
 *     to'lovlar ro'yxati. Maketdagi «Yig'ilgan summa», «O'rtacha patta»,
 *     «Boshlang'ich naqd», «Ochgan: …» BACKENDDA YO'Q va QO'SHILMAYDI.
 *
 * ⛔⛔ YIG'INDI KO'RSATILMAYDI — VA BU ATAYIN, «hali yo'q» emas: kassir
 *     smenani KO'R sanaydi (D-25/D-26). Server oxirgi 5 to'lovni beradi
 *     (qo'shib chiqara olmasin), roster javobida summa maydoni UMUMAN
 *     yo'q (`strictObject` rad etadi). ALOHIDA to'lov summasi esa
 *     ko'rinadi — kassir uni o'zi yozgan (§8.8 bilan bir xil yuza).
 *
 * ⛔ MAXRAJ: `paid + unpaid` — «Sotuvchisiz» KIRMAYDI (O'-01).
 *
 * ⛔ So'rovlar FAQAT kassirda ketadi: chaqiruvchi (`dashboard/page.tsx`)
 *    komponentni `payment_create` sharti bilan chizadi (mavjud naqsh).
 *
 * ⛔ `marketId` PROP, huquq EMAS: metrika faqat `receipts_written`
 *    bo'lgandagina yoziladi (D-28; rollar to'plami kesishganda begona
 *    metrika yorliq ostiga tushmasin).
 * =============================================================================
 */

export function CashierBrief({ marketId }: { marketId: string | null }) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();
  const { data, isLoading, refetch: refetchShift } = useOpenShift();
  const roster = useCollectRoster("unpaid", 1);
  const headline = useHeadline(marketId);
  const recent = useRecentPayments();

  if (isLoading) {
    /* Bozor «rasta ustunlari» loaderi — spinner EMAS (masterplan §3.2). */
    return <BrandLoader />;
  }

  const shift = data ?? null;
  const openedAt = shift === null ? null : new Date(shift.opened_at);
  const openHours =
    openedAt === null
      ? null
      : Math.floor((Date.now() - openedAt.getTime()) / 3_600_000);

  const paid = roster.data?.paid_count ?? null;
  const unpaid = roster.data?.unpaid_count ?? null;

  /*
   * Kvitansiya soni faqat metrika AYNAN `headline.receipts_written`
   * (server i18n KALIT yuboradi — `headline-queries.ts:34`) bo'lganda
   * yoziladi — server boshqa ko'rsatkich bergan sessiyada (rollar
   * to'plami, D-05) yorliq ostida BEGONA son turmasin.
   */
  const receipts =
    headline.available && headline.metric === "headline.receipts_written"
      ? (headline.value ?? null)
      : null;

  const refreshAll = () => {
    void refetchShift();
    void roster.refetch();
    void recent.refetch();
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="grid items-start gap-4 xl:grid-cols-[1.66fr_1fr]">
        {/* ---- chap ustun ---------------------------------------------- */}
        <div className="flex min-w-0 flex-col gap-4">
          <ShiftStatusCard locale={locale} shiftId={shift?.id ?? null} openedAt={openedAt} />
          <CollectHero loading={roster.isPending} paid={paid} unpaid={unpaid} />

          <div className="grid gap-3 sm:grid-cols-3">
            <QuickLink
              href="/collect#roster"
              icon={LayoutGrid}
              title={t("dashboard.quickRoster")}
            />
            <QuickLink
              href={shift === null ? "/collect" : "/collect/shift"}
              icon={LogOut}
              title={
                shift === null ? t("collect.shiftOpen") : t("collect.shiftClose")
              }
            />
            {/*
             * «Yangilash» — faqat MAVJUD so'rovlarni qayta yugurtiradi;
             * yangi endpoint YO'Q (foydalanuvchi cheklovi).
             */}
            <button
              className={cn(
                "group flex min-h-12 items-center gap-3 rounded-xl border border-border-ui",
                "px-4 py-2.5 text-sm font-semibold transition-colors hover:bg-surface-muted",
              )}
              onClick={refreshAll}
              type="button"
            >
              <RefreshCw aria-hidden="true" className="size-5 shrink-0" />
              {t("dashboard.refresh")}
            </button>
          </div>
        </div>

        {/* ---- o'ng ustun ---------------------------------------------- */}
        <div className="flex min-w-0 flex-col gap-4">
          <Card>
            <CardContent className="flex flex-col gap-3 pt-5">
              <p className="text-sm font-semibold uppercase tracking-wide text-text-muted">
                {t("dashboard.todayResult")}
              </p>
              <ResultRow
                icon={FileText}
                label={t("dashboard.statReceipts")}
                tone="accent"
                value={
                  receipts === null ? "—" : formatAmount(format, receipts, locale)
                }
              />
              <ResultRow
                icon={CircleCheck}
                label={t("dashboard.statPaid")}
                tone="success"
                value={paid === null ? "—" : formatAmount(format, paid, locale)}
              />
              <ResultRow
                icon={CircleAlert}
                label={t("dashboard.statUnpaid")}
                tone="danger"
                value={
                  unpaid === null ? "—" : formatAmount(format, unpaid, locale)
                }
              />
            </CardContent>
          </Card>

          <RecentPaymentsCard items={recent.data?.items ?? null} />
        </div>
      </div>

      {/*
       * UZUN SMENA — OGOHLANTIRISH (J-01 ning ikkinchi yarmi).
       *
       * AVTOMATIK YOPISH QILINMAYDI: smenani yopish KO'R DEKLARATSIYA
       * talab qiladi (kassir naqdni sanab kiritadi). Uni tizim o'zi
       * yopsa deklaratsiya BO'SH qolardi va o'sha kunning farqi umuman
       * hisoblanmasdi. Shuning uchun bu YOZUV, amal emas.
       */}
      {shift !== null && openHours !== null && openHours >= LONG_SHIFT_HOURS ? (
        <p
          className="flex items-start gap-2 rounded-md bg-warning/25 px-3 py-2 text-sm text-text"
          role="status"
        >
          <TriangleAlert aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
          {t("dashboard.shiftLongWarning", { hours: openHours })}
        </p>
      ) : null}

      {/*
       * ⛔ Ko'r sanash izohi ATAYIN ko'rinadi: «summani qayerdan
       *    ko'raman?» degan savol kassirda baribir tug'iladi va javobsiz
       *    qolsa u buni NUQSON deb o'ylaydi. Bir qator izoh savolni
       *    yopadi. Smena yo'qligida esa «qayerdan ochaman» javobi.
       */}
      <p className="flex items-start gap-2 text-sm leading-relaxed text-text-muted">
        <Info aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
        {shift === null ? t("dashboard.shiftNoneHint") : t("dashboard.blindHint")}
      </p>
    </div>
  );
}

/* ---- smena holati kartasi ------------------------------------------------ */

function ShiftStatusCard({
  locale,
  openedAt,
  shiftId,
}: {
  locale: string;
  openedAt: Date | null;
  shiftId: string | null;
}) {
  const t = useTranslations();
  const format = useFormatter();

  return (
    <Card>
      <CardContent className="flex flex-col gap-4 pt-5">
        <div className="flex flex-wrap items-center gap-3">
          <p className="text-sm font-semibold uppercase tracking-wide text-text-muted">
            {t("dashboard.shiftCardTitle")}
          </p>
          {/*
           * ⛔ Rang YOLG'IZ signal EMAS (WCAG 1.4.1): belgida holat
           *    MATNI ham bor.
           */}
          <span
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-semibold",
              openedAt === null
                ? "bg-surface-muted text-text-muted"
                : "bg-success/10 text-success-text",
            )}
          >
            <CircleDot aria-hidden="true" className="size-4" strokeWidth={2.5} />
            {openedAt === null
              ? t("dashboard.shiftNone")
              : t("collect.shiftStatusOpen")}
          </span>
        </div>

        {openedAt === null || shiftId === null ? (
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm leading-relaxed text-text-muted">
              {t("dashboard.shiftNoneHint")}
            </p>
            <Link
              className={cn(
                "inline-flex min-h-11 shrink-0 items-center gap-2 rounded-md bg-accent",
                "px-5 text-sm font-semibold text-accent-fg transition-colors hover:bg-accent-hover",
              )}
              href="/collect"
            >
              {t("collect.shiftOpen")}
              <ArrowRight aria-hidden="true" className="size-5" />
            </Link>
          </div>
        ) : (
          <>
            <div className="grid gap-4 sm:grid-cols-3">
              <div className="flex flex-col gap-0.5">
                <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">
                  {t("collect.shiftOpenedAt")}
                </p>
                <p className="font-mono text-lg font-semibold tabular-nums">
                  {format.dateTime(openedAt, { timeStyle: "short" })}
                </p>
                <p className="text-xs text-text-muted">
                  {formatBusinessDay(
                    format,
                    openedAt.toISOString().slice(0, 10),
                    locale,
                  )}
                </p>
              </div>
              <div className="flex flex-col gap-0.5">
                <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">
                  {t("dashboard.shiftDurationLabel")}
                </p>
                <ShiftTicker openedAt={openedAt} />
              </div>
              <div className="flex flex-col gap-0.5">
                <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">
                  {t("dashboard.shiftNumber")}
                </p>
                {/* Identifikator serverning O'ZINIKI — yangi maydon emas. */}
                <p className="font-mono text-lg font-semibold uppercase tabular-nums">
                  №{shiftId.slice(-8)}
                </p>
              </div>
            </div>

            <Link
              className={cn(
                "inline-flex min-h-11 items-center justify-center gap-2 self-start rounded-md",
                "border border-danger/40 px-4 text-sm font-semibold text-danger-text",
                "transition-colors hover:bg-danger/10",
              )}
              href="/collect/shift"
            >
              <LogOut aria-hidden="true" className="size-5" />
              {t("collect.shiftClose")}
            </Link>
          </>
        )}
      </CardContent>
    </Card>
  );
}

/**
 * Jonli davomiylik — `opened_at` dan HISOBLANADI (yangi maydon emas).
 *
 * ⚠ Interval 1 s: bu MATN yangilanishi, CSS harakat emas — G-motion
 *   ruxsat to'plamiga tegmaydi va reduced-motion uni cheklamaydi
 *   (soat ko'rsatkichi kontent hisoblanadi).
 */
function ShiftTicker({ openedAt }: { openedAt: Date }) {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1_000);
    return () => clearInterval(timer);
  }, []);

  const total = Math.max(0, Math.floor((now - openedAt.getTime()) / 1_000));
  const pad = (value: number) => String(value).padStart(2, "0");

  return (
    <p className="font-mono text-lg font-semibold tabular-nums">
      {pad(Math.floor(total / 3_600))}:{pad(Math.floor(total / 60) % 60)}:
      {pad(total % 60)}
    </p>
  );
}

/* ---- patta yig'ish gero kartasi ------------------------------------------ */

function CollectHero({
  loading,
  paid,
  unpaid,
}: {
  loading: boolean;
  paid: number | null;
  unpaid: number | null;
}) {
  const t = useTranslations();

  const total = paid === null || unpaid === null ? null : paid + unpaid;
  const ratio = total === null || total === 0 ? 0 : (paid as number) / total;
  const percent = Math.round(ratio * 100);

  return (
    <Card>
      <CardContent className="flex flex-col gap-4 pt-5">
        <div className="flex flex-col gap-0.5">
          <p className="text-lg font-semibold">{t("collect.title")}</p>
          <p className="text-sm text-text-muted">
            {t("dashboard.quickCollectHint")}
          </p>
        </div>

        {loading && total === null ? (
          <BrandLoader compact />
        ) : (
          <div className="flex flex-col gap-2">
            {/*
             * ⛔ SANOQ, summa emas (fayl sarlavhasi): maketdagi «Bugungi
             *    yig'ilgan summa» o'rnida patta SANOG'I turadi.
             */}
            <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <span className="font-mono text-2xl font-semibold tabular-nums">
                {total === null
                  ? "—"
                  : t("dashboard.collectOf", {
                      done: paid as number,
                      total,
                    })}
              </span>
              <span className="font-mono text-sm font-semibold tabular-nums text-accent-text">
                {total === null ? "" : `${percent}%`}
              </span>
            </div>
            <div
              aria-hidden="true"
              className="h-2.5 w-full overflow-hidden rounded-full bg-border"
            >
              <div
                className="cashier-bar-fill h-full rounded-full bg-accent"
                style={{ width: `${percent}%` }}
              />
            </div>
            <p className="text-sm tabular-nums text-text-muted">
              {paid ?? 0} {t("dashboard.progressDone")} · {unpaid ?? 0}{" "}
              {t("dashboard.progressLeft")}
            </p>
          </div>
        )}

        <div className="flex flex-wrap items-center gap-3">
          <Link
            className={cn(
              "inline-flex min-h-12 items-center gap-2 rounded-xl bg-accent px-6",
              "text-sm font-semibold text-accent-fg transition-colors hover:bg-accent-hover",
            )}
            href="/collect"
          >
            <HandCoins aria-hidden="true" className="size-5" />
            {t("dashboard.collectCta")}
            <ArrowRight aria-hidden="true" className="size-5" />
          </Link>
          <Link
            className={cn(
              "inline-flex min-h-11 items-center gap-2 rounded-md px-3 text-sm",
              "font-semibold text-accent-text transition-colors hover:bg-accent/8",
            )}
            href="/collect#roster"
          >
            {t("dashboard.quickRoster")}
            <ArrowRight aria-hidden="true" className="size-4" />
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}

/* ---- yordamchi bloklar --------------------------------------------------- */

const RESULT_TONE = {
  accent: "bg-accent/12 text-accent-text",
  danger: "bg-danger/10 text-danger-text",
  success: "bg-success/10 text-success-text",
} as const;

const RESULT_VALUE_TONE = {
  accent: "text-text",
  danger: "text-danger-text",
  success: "text-success-text",
} as const;

function ResultRow({
  icon: Icon,
  label,
  tone,
  value,
}: {
  icon: ComponentType<{ className?: string; "aria-hidden"?: boolean }>;
  label: string;
  tone: keyof typeof RESULT_TONE;
  value: string;
}) {
  return (
    <div className="flex items-center gap-3">
      <span
        aria-hidden="true"
        className={cn(
          "grid size-10 shrink-0 place-items-center rounded-lg",
          RESULT_TONE[tone],
        )}
      >
        <Icon aria-hidden className="size-5" />
      </span>
      <span className="min-w-0 flex-1 truncate text-sm text-text-muted">
        {label}
      </span>
      <span
        className={cn(
          "font-mono text-lg font-semibold tabular-nums",
          RESULT_VALUE_TONE[tone],
        )}
      >
        {value}
      </span>
    </div>
  );
}

function QuickLink({
  href,
  icon: Icon,
  title,
}: {
  href: "/collect" | "/collect/shift" | "/collect#roster";
  icon: ComponentType<{ className?: string; "aria-hidden"?: boolean }>;
  title: string;
}) {
  return (
    <Link
      className={cn(
        "group flex min-h-12 items-center gap-3 rounded-xl border border-border-ui",
        "px-4 py-2.5 text-sm font-semibold transition-colors hover:bg-surface-muted",
      )}
      href={href}
    >
      <Icon aria-hidden className="size-5 shrink-0" />
      <span className="min-w-0 flex-1 truncate">{title}</span>
      <ArrowRight
        aria-hidden
        className="size-4 shrink-0 transition-transform group-hover:translate-x-0.5"
      />
    </Link>
  );
}

/* ---- oxirgi to'lovlar ---------------------------------------------------- */

/** Yopiq to'plam — next-intl tiplangan kalitlar literal bo'lishi shart. */
const METHOD_KEY = {
  cash: "collect.methodCash",
  terminal: "collect.methodTerminal",
} as const;

function RecentPaymentsCard({ items }: { items: PaymentRecord[] | null }) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();

  return (
    <Card>
      <CardContent className="flex flex-col gap-3 pt-5">
        <p className="text-sm font-semibold uppercase tracking-wide text-text-muted">
          {t("collect.recentTitle")}
        </p>

        {items === null ? (
          <BrandLoader compact />
        ) : items.length === 0 ? (
          <p className="text-sm text-text-muted">{t("collect.recentEmpty")}</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {items.map((record) => {
              /*
               * §8.8 bilan bir xil semantika: storno qatori MANFIY
               * ko'rinadi (`payment-row.tsx` dagi `signedAmount`).
               */
              const signed =
                record.kind === "reversal"
                  ? -record.amount_soum
                  : record.amount_soum;
              return (
                <li
                  className="flex items-center gap-3 rounded-lg border border-border px-3 py-2"
                  key={record.payment_id}
                >
                  <span
                    aria-hidden="true"
                    className="grid size-9 shrink-0 place-items-center rounded-lg bg-accent/12 font-mono text-xs font-semibold text-accent-text"
                  >
                    {record.stall_code.slice(0, 4)}
                  </span>
                  <span className="flex min-w-0 flex-1 flex-col">
                    <span className="truncate text-sm font-semibold">
                      {record.stall_code}
                    </span>
                    <span className="truncate text-xs tabular-nums text-text-muted">
                      {t(METHOD_KEY[record.method])} ·{" "}
                      {format.dateTime(new Date(record.created_at), {
                        timeStyle: "short",
                      })}
                    </span>
                  </span>
                  <span
                    className={cn(
                      "font-mono text-sm font-semibold tabular-nums",
                      record.kind === "reversal"
                        ? "text-danger-text"
                        : record.reversed
                          ? "text-text-muted line-through"
                          : "text-text",
                    )}
                  >
                    {formatAmount(format, signed, locale)}{" "}
                    {t("collect.amountUnit")}
                  </span>
                </li>
              );
            })}
          </ul>
        )}

        <Link
          className={cn(
            "inline-flex min-h-11 items-center justify-center gap-2 rounded-md border",
            "border-border-ui text-sm font-semibold transition-colors hover:bg-surface-muted",
          )}
          href="/collect"
        >
          {t("dashboard.recentAll")}
        </Link>
      </CardContent>
    </Card>
  );
}
