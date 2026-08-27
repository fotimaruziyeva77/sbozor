"use client";

import { useState } from "react";
import { CircleCheck, CircleDashed, RefreshCw, UserX } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/cn";
import {
  ROSTER_STATES,
  useCollectRoster,
  type RosterState,
} from "@/lib/collect-roster-queries";

/*
 * =============================================================================
 * BUGUNGI RASTALAR — TO'LANGAN / TO'LANMAGAN (0027, foydalanuvchi talabi).
 *
 * «kassirga to'lanmagan rastalarni ro'yhatini chiqarib berasan alohida
 *  qilib responsiveda ham aniq ko'rinishi kerak … har bir to'langan
 *  rastani ro'yhatini chiqarasan va tagiga son qo'yasan filtrdagiday
 *  qilib ko'zga ko'rinmay qolgani page bo'lib boshqasiga 2 3 bo'lib
 *  o'tadi, to'lanmagani ham aynan shunday bo'lsin»
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ SUMMA KO'RSATILMAYDI — KO'R SMENA SANOG'I (D-25/D-26).
 *
 *   Bu ro'yxat TO'LIQ (barcha rasta), `GET /payments/recent` esa
 *   ATAYIN beshta qator bilan chegaralangan — kassir yig'indini qo'shib
 *   chiqara olmasin. Bu yerga summa qo'shilsa o'sha chegaralashning
 *   butun ma'nosi yo'qolardi: kassir jamini o'zi hisoblab, smena
 *   yopishda AYNAN o'sha sonni yozardi va direktor ko'radigan FARQ har
 *   doim nol bo'lardi.
 *
 *   Sxema buni MEXANIK qiladi: `rosterRowSchema` — `strictObject`, ya'ni
 *   server bir kun summa yuborsa javob RAD ETILADI.
 *
 * -----------------------------------------------------------------------
 * ⛔ SANOQ ESA KO'RSATILADI VA U SUMMA EMAS.
 *
 *   «12 / 38» — nechta rasta, qancha so'm EMAS. Undan yig'indi chiqarib
 *   bo'lmaydi (har rastaning tarifi har xil) va u kassirning kunlik
 *   ishini ko'rsatadigan YAGONA halol o'lchov.
 *
 * -----------------------------------------------------------------------
 * ⛔ IKKI RO'YXAT BITTA KOMPONENTDA, IKKI NUSXADA EMAS.
 *
 *   Farq FAQAT `state` da: sarlavha, bo'sh holat matni va ikonka shundan
 *   hosila. Ikki alohida komponent yozilsa sahifalash mantig'i ikki
 *   nusxada yashardi va ular bir kun ajralib ketardi (bu loyihada
 *   takroran topilgan sinf).
 * =============================================================================
 */

const STATE_LABEL: Record<
  RosterState,
  "collect.rosterUnpaid" | "collect.rosterPaid" | "collect.rosterUnassigned"
> = {
  unpaid: "collect.rosterUnpaid",
  paid: "collect.rosterPaid",
  unassigned: "collect.rosterUnassigned",
};

const STATE_EMPTY: Record<
  RosterState,
  | "collect.rosterEmptyUnpaid"
  | "collect.rosterEmptyPaid"
  | "collect.rosterEmptyUnassigned"
> = {
  unpaid: "collect.rosterEmptyUnpaid",
  paid: "collect.rosterEmptyPaid",
  unassigned: "collect.rosterEmptyUnassigned",
};
/**
 * ⛔ IKKI REYESTR — TERNARY ZANJIRI EMAS.
 *
 * Uchinchi holat qo'shilganda ternary zanjiri to'rt joyda o'sardi va
 * to'rtinchisi qo'shilganda ulardan biri UNUTILARDI. `Record<RosterState,
 * ...>` esa yangi a'zoni `tsc` bilan MAJBURLAYDI.
 */

export type StallRosterProps = {
  /** Boshlang'ich filtr — ⛔ standart `unpaid` (kassirning asosiy savoli). */
  initialState?: RosterState;
};

export function StallRoster({ initialState = "unpaid" }: StallRosterProps) {
  const t = useTranslations();
  const format = useFormatter();

  const [state, setState] = useState<RosterState>(initialState);
  const [page, setPage] = useState(1);

  const roster = useCollectRoster(state, page);
  const data = roster.data ?? null;

  /*
   * ⛔ FILTR ALMASHGANDA SAHIFA BIRINCHIGA QAYTADI. Aks holda kassir
   *    «to'lanmagan, 3-sahifa» dan «to'langan» ga o'tganda BO'SH ekran
   *    ko'rardi (to'langanlar 1 sahifagina bo'lsa) va uni «yuklanmadi»
   *    deb o'qirdi.
   */
  const switchState = (next: RosterState) => {
    setState(next);
    setPage(1);
  };

  const counts: Record<RosterState, number | null> = {
    unpaid: data?.unpaid_count ?? null,
    paid: data?.paid_count ?? null,
    unassigned: data?.unassigned_count ?? null,
  };

  return (
    <Card>
      <CardContent className="flex flex-col gap-4 pt-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg leading-snug font-semibold tracking-tight">
            {t("collect.rosterTitle")}
          </h2>

          <button
            aria-label={t("collect.rosterRefresh")}
            className="inline-flex min-h-11 min-w-11 items-center justify-center gap-2 rounded-md border border-border px-3 text-sm font-semibold text-text hover:bg-surface-muted"
            onClick={() => void roster.refetch()}
            type="button"
          >
            <RefreshCw aria-hidden="true" className="size-6" />
          </button>
        </div>

        {/*
         * --- FILTR (segment) -------------------------------------------
         *
         * ⛔ HAR IKKALA TUGMADA HAM SANOQ TURADI — faol bo'lganida ham,
         *    bo'lmaganida ham. Server ikkala sonni HAR IKKALA javobda
         *    beradi, ya'ni bu ikkinchi so'rov TALAB QILMAYDI va kassir
         *    «boshqasida nechta qoldi?» degan savolga tugmani
         *    BOSMASDAN javob oladi.
         *
         * ⚠ Nishonlar 48px (`min-h-12`): telefonda bir qo'lda bosiladi.
         */}
        <div
          /*
           * ⛔ UCH USTUN (O'-01): «Sotuvchisiz» uchinchi HOLAT, filtr
           *    emas. Telefonda uchtasi ham sig'adi, chunki yorliqlar
           *    qisqa va sanoq yonida turadi.
           */
          className="grid grid-cols-3 gap-2 rounded-lg bg-surface-muted p-1"
          role="group"
        >
          {ROSTER_STATES.map((value) => {
            const active = value === state;
            const count = counts[value];
            return (
              <button
                aria-pressed={active}
                className={cn(
                  /*
                   * ⛔ `px-1.5 text-xs` TELEFONDA, `sm:` dan boshlab
                   *    avvalgi o'lchov (2026-08-25 auditi K1): 375px da
                   *    «To'lanmagan» qisqarib «T…» bo'lib qolardi —
                   *    yorliq YO'QOLGAN holat filtri o'qib bo'lmas edi.
                   *    Ikonka ham tor ekranda yashirinadi — matn birinchi.
                   */
                  "flex min-h-12 items-center justify-center gap-1.5 rounded-md px-1.5 text-xs font-semibold transition-colors sm:gap-2 sm:px-3 sm:text-sm",
                  active
                    ? "bg-surface text-text shadow-sm"
                    : "text-text-muted hover:text-text",
                )}
                key={value}
                onClick={() => switchState(value)}
                type="button"
              >
                {value === "paid" ? (
                  <CircleCheck aria-hidden="true" className="hidden size-6 sm:block" />
                ) : value === "unassigned" ? (
                  <UserX aria-hidden="true" className="hidden size-6 sm:block" />
                ) : (
                  <CircleDashed aria-hidden="true" className="hidden size-6 sm:block" />
                )}
                <span className="truncate">{t(STATE_LABEL[value])}</span>
                {/*
                 * ⛔ NOL HAM CHIZILADI: «hisoblagich ishlamayapti» bilan
                 *    «bu yerda hech nima yo'q» bir xil ko'rinmasligi
                 *    kerak (`occupancy` da o'rnatilgan qoida).
                 */}
                {count === null ? null : (
                  <span
                    className={cn(
                      "min-w-7 rounded-full px-2 py-0.5 text-sm tabular-nums",
                      active
                        ? "bg-accent text-accent-fg"
                        : "bg-border-strong/40 text-text",
                    )}
                  >
                    {count}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* --- Ro'yxat --------------------------------------------------- */}
        {roster.isPending ? (
          <ul className="flex flex-col gap-2">
            {[0, 1, 2, 3].map((row) => (
              <li key={row}>
                <Skeleton className="h-14 w-full" />
              </li>
            ))}
          </ul>
        ) : roster.isError ? (
          <div className="flex flex-col gap-2" role="alert">
            <p className="text-sm text-danger-text">
              {t("collect.rosterFailed")}
            </p>
            <button
              className="self-start inline-flex min-h-11 items-center rounded-md border border-border px-4 text-sm font-semibold hover:bg-surface-muted"
              onClick={() => void roster.refetch()}
              type="button"
            >
              {t("collect.retry")}
            </button>
          </div>
        ) : data === null || data.rows.length === 0 ? (
          /*
           * ⛔ BO'SHLIK NOMLANADI VA IKKI FILTRDA IKKI XIL MA'NO:
           *    to'lanmaganlar bo'sh — YAXSHI xabar («hammasi to'langan»);
           *    to'langanlar bo'sh — NEYTRAL holat («hali yozilmagan»).
           *    Bitta umumiy «ro'yxat bo'sh» matni ikkalasini ham
           *    nosozlikdek ko'rsatardi.
           */
          <p className="py-6 text-center text-sm text-text-muted">
            {t(STATE_EMPTY[state])}
          </p>
        ) : (
          <ul className="flex flex-col gap-2">
            {data.rows.map((row) => (
              <li
                className="flex min-h-14 flex-wrap items-center justify-between gap-x-4 gap-y-1 rounded-md border border-border bg-surface px-4 py-3"
                key={row.stall_code}
              >
                <span className="flex items-center gap-3">
                  {state === "paid" ? (
                    <CircleCheck
                      aria-hidden="true"
                      className="size-6 shrink-0 text-success-text"
                    />
                  ) : state === "unassigned" ? (
                    <UserX
                      aria-hidden="true"
                      className="size-6 shrink-0 text-warning-text"
                    />
                  ) : (
                    <CircleDashed
                      aria-hidden="true"
                      className="size-6 shrink-0 text-text-muted"
                    />
                  )}
                  <span className="text-lg font-semibold tabular-nums text-text">
                    {row.stall_code}
                  </span>
                </span>

                {/*
                 * ⛔ SOTUVCHISIZ RASTA RO'YXATDA BELGILANADI — kassir
                 *    behuda urinmasin: `POST /payments` unga 409
                 *    `stall_not_assigned` beradi va u buni faqat
                 *    [Tasdiqlash] dan KEYIN bilardi.
                 */}
                {row.vendor_assigned ? null : (
                  <span
                    className="inline-flex items-center gap-1.5 rounded-full bg-warning/25 px-3 py-1 text-sm font-semibold text-text"
                    title={t("collect.rosterNoVendorHint")}
                  >
                    <UserX aria-hidden="true" className="size-5" />
                    {t("collect.rosterNoVendor")}
                  </span>
                )}

                {row.paid_at === null ? null : (
                  <span className="text-sm tabular-nums text-text-muted">
                    {format.dateTime(new Date(row.paid_at), {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                )}
              </li>
            ))}
          </ul>
        )}

        {/* --- Sahifalash ------------------------------------------------ */}
        {data !== null && data.page_count > 1 ? (
          <RosterPager
            onSelect={setPage}
            page={data.page}
            pageCount={data.page_count}
          />
        ) : null}
      </CardContent>
    </Card>
  );
}

/* --- Sahifa raqamlari ------------------------------------------------------ */

/**
 * ⛔ RAQAMLI SAHIFALAR — «Keyingi» tugmasining O'ZI EMAS.
 *
 * Foydalanuvchi aynan shuni so'radi: «page bo'lib boshqasiga 2 3 bo'lib
 * o'tadi». Raqam kassirga QAYERDA ekanini va YANA QANCHA borligini bir
 * qarashda aytadi; yolg'iz «Keyingi» esa oxirigacha bosishdan boshqa
 * yo'l qoldirmasdi.
 *
 * ⚠ OYNA — 5 ta raqam: telefon ekranida undan ko'pi sig'maydi va
 *   tugmalar 44px dan kichrayib ketardi.
 */
function RosterPager({
  page,
  pageCount,
  onSelect,
}: {
  page: number;
  pageCount: number;
  onSelect: (next: number) => void;
}) {
  const t = useTranslations();

  const window = 5;
  const start = Math.max(1, Math.min(page - Math.floor(window / 2), pageCount - window + 1));
  const pages = Array.from(
    { length: Math.min(window, pageCount) },
    (_, index) => start + index,
  );

  return (
    <nav
      aria-label={t("collect.rosterPageLabel")}
      className="flex flex-wrap items-center justify-center gap-2"
    >
      <button
        className="inline-flex min-h-11 items-center rounded-md border border-border px-3 text-sm font-semibold text-text disabled:opacity-40 hover:enabled:bg-surface-muted"
        disabled={page <= 1}
        onClick={() => onSelect(page - 1)}
        type="button"
      >
        {t("collect.rosterPrev")}
      </button>

      {pages.map((value) => (
        <button
          aria-current={value === page ? "page" : undefined}
          className={cn(
            "inline-flex min-h-11 min-w-11 items-center justify-center rounded-md border text-sm font-semibold tabular-nums transition-colors",
            value === page
              ? "border-accent bg-accent text-accent-fg"
              : "border-border text-text hover:bg-surface-muted",
          )}
          key={value}
          onClick={() => onSelect(value)}
          type="button"
        >
          {value}
        </button>
      ))}

      <button
        className="inline-flex min-h-11 items-center rounded-md border border-border px-3 text-sm font-semibold text-text disabled:opacity-40 hover:enabled:bg-surface-muted"
        disabled={page >= pageCount}
        onClick={() => onSelect(page + 1)}
        type="button"
      >
        {t("collect.rosterNext")}
      </button>
    </nav>
  );
}
