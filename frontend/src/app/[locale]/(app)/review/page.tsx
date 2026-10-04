"use client";

import { LockKeyhole } from "lucide-react";
import { useFormatter, useLocale, useTranslations } from "next-intl";
import { useQuery } from "@tanstack/react-query";

import { formatBusinessDay, formatBusinessWeekday } from "@/lib/format-day";
import { localeHref } from "@/lib/locale-href";
import { ForbiddenNotice } from "@/components/auth/forbidden-notice";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { businessDayIn, shiftIsoDay } from "@/components/snapshots/day-picker";
import { apiFetch } from "@/lib/api-client";
import { reviewYesterdaySummarySchema } from "@/lib/api-types";
import type { QueueBudget } from "@/lib/api-types";
import { useAuthStore } from "@/lib/auth-store";
import { domainKey } from "@/lib/market-queries";
import { hasPermission } from "@/lib/rbac";
import { useReviewBudget } from "@/lib/review-queries";

/*
 * =============================================================================
 * NAZORATCHINING UYI (Y-2 uyi, UI-SPEC §7.2).
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ KO'RMASDAN TEKSHIRISH KARTASI DOM TARTIBIDA BIRINCHI [QAROR]
 * -----------------------------------------------------------------------
 * 05-RESEARCH §C.8: «kunlik byudjetli navbat aynan vaqt bosimi
 * yaratadi». Noaniq navbatni birinchi qo'yish ko'rmasdan tekshirishni
 * kunning OXIRIGA surardi — ya'ni xolis o'lchov charchagan holda,
 * shosha-pisha bajarilardi. Tartib O'LCHOV USTUVORLIGINI ko'rsatadi va
 * u `review-queries.test.tsx` da DOM tartibi bo'yicha qulflanadi.
 *
 * -----------------------------------------------------------------------
 * ⛔ IKKALA KARTA HAM DOIM KO'RINADI — BYUDJET TUGAGAN BO'LSA HAM
 * -----------------------------------------------------------------------
 * Tugagan kartani yashirish «bugun bunday ish yo'q edi» degan yolg'on
 * xabarni berardi. Tugagan karta hisoblagichni `30 / 30` qilib
 * ko'rsatadi, `Bajarildi` nishoni oladi va tugmasi `aria-disabled`
 * bo'ladi — ya'ni FAKT o'zgaradi, ekranning tuzilishi emas.
 *
 * -----------------------------------------------------------------------
 * ⚠ OXIRGI QATOR (D-19 ILGAGI) VA UNING O'LCHANGAN CHEKLOVI
 * -----------------------------------------------------------------------
 * §7.2 uni «doim ko'rinadi, nol bo'lsa ham» deb belgilaydi. Manba —
 * `GET /occupancy?day=…` ning `default_empty` maydoni, u esa
 * `REPORT_VIEW` ostida; `inspector` da bu huquq YO'Q va aynan
 * `inspector` bu sahifaning yagona egasi (§4.6).
 *
 * Shuning uchun qator FAQAT huquq bo'lganda so'raladi va chiziladi.
 * ⛔ NOL YOZIB QO'YISH TAQIQ: «Kecha: 0 ta rasta ko'rilmagani uchun
 *    bo'sh deb hisoblandi» — o'lchanmagan holatda bu eng yomon shakldagi
 *    YOLG'ON, chunki u nazoratchining kechagi qoldig'ini NOL deb
 *    e'lon qilardi.
 * ⚠ Eng tor tuzatish SUMMARY da yozilgan: `ReviewBudgetResponse` ga
 *   bitta maydon (`default_empty_yesterday`) — u allaqachon
 *   `OCCUPANCY_REVIEW` ostida.
 * =============================================================================
 */

export default function ReviewHomePage() {
  const t = useTranslations();
  const { principal } = useAuthStore();

  /*
   * ⚠ HUQUQ TEKSHIRUVI SO'ROVDAN OLDIN (`cameras/page.tsx:86-95` naqshi):
   *   huquqsiz sessiyada `GET /review/budget` ga so'rov HAM ketmaydi.
   *   Haqiqiy nazorat serverda (`require_permission(OCCUPANCY_REVIEW)`).
   */
  if (!hasPermission(principal?.roles ?? [], "occupancy_review")) {
    return <ForbiddenNotice />;
  }

  return <ReviewHome />;
}

function ReviewHome() {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();
  const { principal } = useAuthStore();

  const todayIso = businessDayIn("Asia/Tashkent", new Date());
  const yesterdayIso = shiftIsoDay(todayIso, -1);
  const budget = useReviewBudget(todayIso);

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">
          {t("review.title")}
        </h1>
        <p className="text-sm text-text-muted">
          {/*
           * ⛔ XOM ISO EMAS VA XOM `weekday` EMAS (260818 jonli o'lchov):
           *    bu qator ekranda «2026-08-18 · Tue» bo'lib chiqardi —
           *    sana mahalliylashtirilmagan, hafta kuni esa INGLIZCHA.
           *    Ikkalasi ham `format-day.ts` ning yagona yo'lidan o'tadi.
           */}
          {formatBusinessDay(format, todayIso, locale)} ·{" "}
          {formatBusinessWeekday(format, todayIso, locale)}
        </p>
      </header>

      {budget.isPending ? (
        <div aria-busy="true" className="flex flex-col gap-6" role="status">
          <span className="sr-only">{t("common.loading")}</span>
          <Skeleton className="h-44" />
          <Skeleton className="h-44" />
        </div>
      ) : budget.isError ? (
        <p
          className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
          role="alert"
        >
          {t("errors.loadFailedBody")}
        </p>
      ) : (
        <>
          {/*
           * ⛔ BIRINCHI KARTA — KO'RMASDAN TEKSHIRISH. Tartib qaror,
           *    estetika emas (yuqoridagi blok).
           */}
          <QueueCard
            actionHref={localeHref(locale, "/review/blind")}
            actionLabel={t("review.startBlind")}
            counters={budget.data.blind_audit}
            emptyNote={t("review.blindEmptyNote")}
            immutableNote={t("review.blindImmutable")}
            lead={t("review.blindLead")}
            title={t("review.blindTitle")}
          />

          <QueueCard
            actionHref={localeHref(locale, "/review/uncertain")}
            actionLabel={t("review.continueUncertain")}
            counters={budget.data.uncertain}
            emptyNote={t("review.uncertainEmptyNote")}
            immutableNote={null}
            lead={t("review.uncertainLead")}
            title={t("review.uncertainTitle")}
          />
        </>
      )}

      <YesterdayHook
        canSeeReport={hasPermission(principal?.roles ?? [], "report_view")}
        day={yesterdayIso}
        href={localeHref(locale, "/occupancy")}
      />
    </div>
  );
}

/* --- Navbat kartasi -------------------------------------------------------- */

/**
 * Bitta navbatning kartasi — IKKALASI ham AYNAN shu komponentdan.
 *
 * ⚠ IKKI NUSXA YOZILMAYDI: kartalarning farqi FAQAT matn va manzilda,
 *   ya'ni ikkinchi komponent «tugagan byudjet qanday ko'rinadi?»
 *   savolini ikki joyda javoblardi va ular bir kun ajralib ketardi.
 *
 * ⛔ HISOBLAGICH — PROGRESS BAR EMAS (§7.3 [QAROR]). Bar navbatni
 *    TUGATILADIGAN O'YINGA aylantiradi va bu aynan shosha-pisha
 *    bosishning rag'bati. `12 / 50` FAKT aytadi, maqsad qo'ymaydi. Shart
 *    `review-queries.test.tsx` da DOM asosida qulflangan
 *    (`<progress>` ham, `role="progressbar"` ham topilmasligi kerak).
 */
function QueueCard({
  actionHref,
  actionLabel,
  counters,
  emptyNote,
  immutableNote,
  lead,
  title,
}: {
  actionHref: string;
  actionLabel: string;
  counters: QueueBudget;
  emptyNote: string;
  immutableNote: string | null;
  lead: string;
  title: string;
}) {
  const t = useTranslations();
  /*
   * ⛔⛔ IKKI XIL «BOSIB BO'LMAYDI» VA ULAR ARALASHTIRILMAYDI (261003).
   *
   *   `done`  — BUGUNGI CHEGARA tugadi; ish bor, lekin ertaga.
   *   `empty` — NAVBAT bo'sh; bugun ham, ertaga ham bosishdan foyda yo'q.
   *
   * Ilgari faqat `done` bor edi va `0 / 30` ikkala holatni ham bir xil
   * chizardi: tugma FAOL turardi, nazoratchi bosardi va bo'sh ekranga
   * tushardi. Jonli bazada o'lchandi — `blind_audit` navbatida 0 ta band
   * bor va hech qachon bo'lmagan, `uncertain` da esa 2614 tasi kutyapti.
   */
  const done = counters.remaining === 0;
  const empty = counters.available === 0;
  const blocked = done || empty;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-3">
        <h2 className="text-sm font-semibold">{title}</h2>
        {/*
          ⚠ TARTIB: bo'sh navbat BYUDJETDAN USTUN. Ikkalasi ham rost
            bo'lsa («bugun 30 ta javob berdim va navbat ham tugadi»)
            foydalanuvchiga kerakligi — ish qolmagani.
        */}
        {empty ? (
          <Badge tone="muted">{t("review.queueEmpty")}</Badge>
        ) : done ? (
          <Badge tone="success">{t("review.budgetDone")}</Badge>
        ) : null}
      </CardHeader>

      <CardContent className="flex flex-col gap-3">
        <p className="text-sm text-text-muted">{lead}</p>

        {/* `font-mono` — HUJJATLASHTIRILGAN ISTISNO (§9.4): ustunlashgan sonlar. */}
        <p className="font-mono text-xs tabular-nums">
          {t("review.today", { done: counters.answered, max: counters.budget })}
        </p>

        {/*
          ⛔ NAVBAT HAJMI — BYUDJETDAN ALOHIDA QATOR. Uni «12 / 50» ga
             qo'shib yuborish ikki xil sonni bitta kasrga aylantirardi va
             «50» nimani anglatishi (chegarami? navbatmi?) noaniq bo'lardi.
        */}
        {empty ? (
          <p className="text-xs text-text-muted">{emptyNote}</p>
        ) : (
          <p className="font-mono text-xs tabular-nums text-text-muted">
            {t("review.waiting", { count: counters.available })}
          </p>
        )}

        {immutableNote === null ? null : (
          <p className="flex items-center gap-2 text-xs text-text-muted">
            <LockKeyhole aria-hidden="true" className="size-4 shrink-0" />
            {immutableNote}
          </p>
        )}

        {/*
         * ⚠ `aria-disabled`, `disabled` EMAS (§13.3): `disabled` havola
         *   fokus olmaydi va skrinrider uni umuman o'qimaydi, ya'ni «nega
         *   ochilmayapti?» savoliga javob beradigan joy qolmaydi.
         *   Byudjet tugaganda `href` OLIB TASHLANADI — bosish yo'lining
         *   O'ZI yopiladi, ko'rinishi esa qoladi.
         */}
        <a
          aria-disabled={blocked ? true : undefined}
          className={
            blocked
              ? "inline-flex w-fit items-center rounded-md bg-surface-muted px-4 py-2 text-sm font-medium text-text-muted"
              : "inline-flex w-fit items-center rounded-md bg-accent px-4 py-2 text-sm font-medium text-accent-fg"
          }
          href={blocked ? undefined : actionHref}
        >
          {actionLabel}
        </a>
      </CardContent>
    </Card>
  );
}

/* --- D-19 ilgagi ----------------------------------------------------------- */

/**
 * «Kecha: N ta rasta ko'rilmagani uchun bo'sh deb hisoblandi.»
 *
 * ⛔ SON YO'Q BO'LSA QATOR HAM YO'Q. Yuqoridagi modul izohiga qarang:
 *    nol o'rniga yozilgan taxmin nazoratchining kechagi qoldig'ini
 *    NOL deb e'lon qilardi.
 *
 * ⚠ NOL BO'LSA QATOR BOR: `default_empty === 0` — NATIJA («kecha hamma
 *   rasta ko'rildi»), ma'lumotning yo'qligi emas. Farq
 *   `review-queries.test.tsx` da ikkala yo'nalishda ham o'lchanadi.
 */
function YesterdayHook({
  canSeeReport,
  day,
  href,
}: {
  canSeeReport: boolean;
  day: string;
  href: string;
}) {
  const t = useTranslations();
  const { principal } = useAuthStore();
  const marketId = principal?.marketId ?? null;

  const summary = useQuery({
    queryKey: domainKey(marketId ?? "", "review-yesterday", day),
    queryFn: () =>
      apiFetch(`/occupancy?day=${encodeURIComponent(day)}`, {
        schema: reviewYesterdaySummarySchema,
      }),
    enabled: canSeeReport && marketId !== null,
    retry: false,
    refetchOnWindowFocus: false,
  });

  if (!canSeeReport || summary.data === undefined) return null;

  return (
    <p className="text-sm text-text-muted">
      {t("review.yesterdayDefaultEmpty", { count: summary.data.default_empty })}{" "}
      <a className="underline underline-offset-2" href={href}>
        {t("review.goToOccupancy")}
      </a>
    </p>
  );
}
