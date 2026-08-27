"use client";

import { Suspense, useId, useState } from "react";
import { useTranslations } from "next-intl";

import { BrandLoader } from "@/components/ui/brand-loader";
import { ForbiddenNotice } from "@/components/auth/forbidden-notice";
import { AlertList } from "@/components/snapshots/alert-list";
import { captureCellState } from "@/components/snapshots/capture-cell";
import { CaptureGrid } from "@/components/snapshots/capture-grid";
import { CaptureLegend } from "@/components/snapshots/capture-legend";
import {
  DayPicker,
  useDaySelection,
  useIssuesOnly,
  useShowClosedAlerts,
} from "@/components/snapshots/day-picker";
import { DaySummary } from "@/components/snapshots/day-summary";
import { ScheduleCard } from "@/components/snapshots/schedule-card";
import { ScheduleDialog } from "@/components/snapshots/schedule-dialog";
import type { ScheduleDialogRequest } from "@/components/snapshots/schedule-dialog";
import { SnapshotDialog } from "@/components/snapshots/snapshot-dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import type { CaptureRun } from "@/lib/api-types";
import { EMPTY_CAMERA_FILTERS, useCamerasQuery } from "@/lib/camera-queries";
import { useAuthStore } from "@/lib/auth-store";
import { Link } from "@/i18n/navigation";
import { hasPermission } from "@/lib/rbac";
import { useCaptureDay } from "@/lib/snapshot-queries";

/*
 * =============================================================================
 * KADR OLISH — 4-FAZANING YAGONA SAHIFASI (UI-SPEC §4.1 [QAROR]).
 *
 * `/schedule`, `/snapshots/[id]`, `/alerts` QURILMAYDI. ⚠ Bu
 * `04-PATTERNS.md` §1.7 dan ATAYIN chekinish va sabab UI-SPEC §4.1 da:
 * jadval — bu fazaning ENG KICHIK yuzasi (uch qator), ijro jurnali esa
 * asosiysi; marshrutni «schedule» deb nomlash sahifaning nomini uning
 * eng kichik qismidan olardi.
 *
 * TO'RT VERTIKAL ZONA (§4.2) va ular HECH QACHON ALMASHMAYDI:
 *   (A) jadval kartasi          — 04-10;
 *   (B) ogohlantirishlar        — Z-3 da UMUMAN render qilinmaydi;
 *   (C) kun tanlagichi + xulosa;
 *   (D) ijro jurnali.
 *
 * ⛔ ZONALAR KUN ALMASHTIRILGANDA YIQILMAYDI (§4.2). (C) va (D)
 *    `aria-busy="true"` oladi va MAZMUNI JOYIDA QOLADI. Jadval yiqilib
 *    qayta qurilsa admin «ma'lumotim yo'qoldimi?» deb qo'rqardi — va
 *    kun almashtirish bu sahifadagi ENG TEZ-TEZ takrorlanadigan amal.
 *
 * ⛔ Z-7 va Z-8 NING FARQI HAYOTIY. Z-7 — jadval bu kunni qoplamaydi
 *    (bo'shliq yoki bozor hali faollashmagan): xulosa E-2 ni chizadi va
 *    JURNAL UMUMAN render qilinmaydi. Z-8 — jadval bor, kun hali
 *    boshlanmagan: xulosa `0 / 7` beradi va jurnal to'liq «kutilmoqda»
 *    hujayralaridan iborat bo'ladi. Ikkalasini bir xil ko'rsatish
 *    adminni «tizim ishlamayapti» degan xulosaga olib borardi.
 *
 * ⚠ HUQUQ TEKSHIRUVI SO'ROVDAN OLDIN (`cameras/page.tsx:85-94` naqshi):
 *   huquqsiz foydalanuvchi uchun ish maydoni UMUMAN render qilinmaydi,
 *   ya'ni `GET /snapshot-schedules/today` ga so'rov ham ketmaydi. Bu 403
 *   ni yashirish uchun emas (u baribir bo'lardi), balki jurnalga
 *   ma'nosiz rad etilgan urinishlar yozilmasligi uchun. Haqiqiy nazorat
 *   serverda: `require_permission(CAMERA_VIEW)`.
 *
 * ⚠ AKSENT BUDJETI (§9.3): bu sahifada birlamchi (aksent fonli) tugma
 *   UMUMAN YO'Q va bu 3-fazadan ATAYIN farq — `/cameras` bir va'dani
 *   bajaradigan HARAKAT sahifasi edi («tugmani bos — kameralar paydo
 *   bo'lsin»), `/snapshots` esa KUZATUV sahifasi va uning to'g'ri
 *   javobi «hamma narsa joyida». E-1 dagi havola ham ikkilamchi.
 *
 * ⚠ USTAGA QADAM QO'SHILMAYDI (§4.9, D-01): admin jadval uchun HECH
 *   NIMA kiritmaydi va usta qadami bo'lsa, hech nima kiritmagan bozor
 *   «chala» ko'rinardi — D-01 ning aynan teskarisi.
 * =============================================================================
 */

export default function SnapshotsPage() {
  const t = useTranslations();
  const { principal } = useAuthStore();

  if (!hasPermission(principal?.roles ?? [], "camera_view")) {
    return <ForbiddenNotice />;
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold tracking-tight">
        {t("snapshots.title")}
      </h1>

      {/*
       * `Suspense` MAJBURIY (`audit/page.tsx` va `cameras/page.tsx`
       * naqshi): ish maydoni kun tanlagichi bilan birga `?day=` ni
       * `nuqs` orqali o'qiydigan bo'ladi, ya'ni daraxtning shu qismi
       * klient tomonda render qilinadi. Chegara bo'lmasa Next 16 butun
       * marshrutni statik prerender ro'yxatidan chiqarib, BUILD ni
       * yiqitadi.
       *
       * ⚠ CHEGARA HOZIRDAN QO'YILADI, 04-11 da emas: u yerda qo'shilsa
       *   o'zgarish hook qo'shish emas, sahifaning TUZILISHINI qayta
       *   qurish bo'lardi — va oradagi commit build'da yiqilardi.
       */}
      <Suspense
        fallback={
          <BrandLoader />
        }
      >
        <SnapshotsWorkspace />
      </Suspense>
    </div>
  );
}

/* --- Ish maydoni ---------------------------------------------------------- */

function SnapshotsWorkspace() {
  const t = useTranslations();
  const { principal } = useAuthStore();
  const canManage = hasPermission(principal?.roles ?? [], "camera_manage");

  /*
   * E-1 ning sharti (§10.4). ⚠ `isSuccess` MAJBURIY: `items.length === 0`
   * ni yuklanish paytida ham to'g'ri deb o'qish har ochilishda bir
   * lahzalik «kamera yo'q» chaqnashini berardi — va u aynan eng yomon
   * yolg'on, chunki admin buni nosozlik deb qabul qilardi.
   */
  const cameras = useCamerasQuery(EMPTY_CAMERA_FILTERS);
  const hasNoCameras = cameras.isSuccess && cameras.data.items.length === 0;

  /*
   * ⚠ DIALOG HOLATI URL'DA EMAS (§4.4, 02-UI-SPEC §7.1 dan meros):
   *   URL'da faqat `?day=`, `?issues=`, `?closed=` yashaydi. Jadval
   *   tahririni ulashiladigan havolaga aylantirish uni sahifa holatidan
   *   marshrutga ko'chirardi va «orqaga» tugmasi yarim to'ldirilgan
   *   formani qaytarardi.
   */
  const [dialog, setDialog] = useState<ScheduleDialogRequest | null>(null);

  /*
   * ⛔ E-1 ZONALARNING O'RNINI EGALLAYDI, ular yonida turmaydi.
   *
   * Kamerasiz bozorda jadval kartasi «Bugun 7 marta» deb turardi,
   * holbuki 0 kamera × 7 vaqt = 0 kadr. Ya'ni ekran REJANI ko'rsatib,
   * NATIJA nolligini yashirардi — bu fazaning butun maqsadi esa
   * yo'qlikni ko'rinadigan qilish (§1.2).
   *
   * ⚠ «Jadval qo'shing» bo'sh holati HECH QACHON chiqmaydi (§10.4):
   *   D-01 bo'yicha jadval usta tomonidan avtomatik yoziladi.
   */
  if (hasNoCameras) {
    return (
      <EmptyState
        action={
          <Link
            className="inline-flex min-h-11 items-center rounded-md border border-border bg-surface px-6 text-sm font-semibold text-text hover:bg-surface-muted"
            href="/cameras"
          >
            {t("snapshots.goToCameras")}
          </Link>
        }
        description={t("snapshots.emptyNoCamerasHint")}
        title={t("snapshots.emptyNoCameras")}
      />
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {/* --- ZONA (A): jadval kartasi ------------------------------------ */}
      <section aria-label={t("snapshots.scheduleTitle")}>
        <ScheduleCard
          canManage={canManage}
          onAddSeasonal={() => setDialog({ kind: "create" })}
          onEdit={(profile) =>
            setDialog({ kind: "edit", scheduleId: profile.id })
          }
        />
      </section>

      {/* --- ZONA (B): ogohlantirishlar --------------------------------- */}
      <AlertZone />

      {/* --- ZONA (C) va (D): kun jurnali -------------------------------- */}
      <CaptureLog />

      {/*
       * DL-1 va DL-2 — bitta qobiq. Dialog ZONA EMAS: u sahifa holati
       * bo'lib, zonalarning tartibiga umuman ta'sir qilmaydi (§4.2 —
       * zonalar hech qachon almashmaydi).
       */}
      <ScheduleDialog
        onOpenChange={(open) => {
          if (!open) setDialog(null);
        }}
        request={dialog}
      />
    </div>
  );
}

/* --- Zona B --------------------------------------------------------------- */

/**
 * Ogohlantirishlar zonasi.
 *
 * ⚠ POLL FAQAT BUGUNGI KUN KO'RILAYOTGANDA (§6.8) va u JURNAL BILAN
 *   AYNI oraliqda: aks holda ekranda «2 kadr olinmadi» ko'rinib turib,
 *   ogohlantirish paydo bo'lmasdi — va admin ikkisini solishtira
 *   olmasdi (D-20 ning butun mazmuni).
 */
function AlertZone() {
  const { isToday } = useDaySelection();
  const [showClosed, setShowClosed] = useShowClosedAlerts();

  return (
    <AlertList closed={showClosed} onClosedChange={setShowClosed} poll={isToday} />
  );
}

/* --- Zonalar C va D ------------------------------------------------------- */

/** Muammoli hujayra holatlari — `?issues=1` filtri aynan shularni qidiradi. */
const ISSUE_STATES = new Set(["dark", "blank", "corrupt", "failed", "missed"]);

function CaptureLog() {
  const t = useTranslations();
  const { day, todayIso } = useDaySelection();
  const [issuesOnly, setIssuesOnly] = useIssuesOnly();
  const issuesId = useId();

  const captureDay = useCaptureDay(day, todayIso);

  /*
   * ⚠ DL-3 HOLATI URL'DA EMAS (§4.4): kadr — bozor tashrifchilarining
   *   shaxsiy ma'lumoti va ulashiladigan havola uni sessiyadan
   *   tashqariga olib chiqish taassurotini berardi. Bu D-19 ning ruhi
   *   bilan bir xil chiziq.
   */
  const [openRun, setOpenRun] = useState<CaptureRun | null>(null);

  const rows = captureDay.data?.rows ?? [];

  /*
   * ⚠ FILTR QATOR (KAMERA) DARAJASIDA ishlaydi, hujayra darajasida emas.
   *   Faqat muammoli HUJAYRALARNI qoldirish qatorni teshik-teshik
   *   qilardi va «06:30 da nima bo'ldi?» savoliga javob berish uchun
   *   kerak bo'lgan qo'shni kadrlarni olib tashlardi.
   */
  const problemCameras = new Set(
    rows
      .filter((row) => ISSUE_STATES.has(captureCellState(row)))
      .map((row) => row.camera_id),
  );
  const visibleRows = issuesOnly
    ? rows.filter((row) => problemCameras.has(row.camera_id))
    : rows;

  const totalCameras = new Set(rows.map((row) => row.camera_id)).size;
  const hiddenCameras = issuesOnly ? totalCameras - problemCameras.size : 0;

  /* Dialog navigatsiyasi — O'SHA QATORDAGI oldingi/keyingi VAQT (§6.6). */
  const rowRuns =
    openRun === null
      ? []
      : rows
          .filter((row) => row.camera_id === openRun.camera_id)
          .sort((left, right) => left.slot_time.localeCompare(right.slot_time));
  const openIndex = rowRuns.findIndex((row) => row.run_id === openRun?.run_id);

  /* Z-7 — reja yo'q: xulosa E-2 ni chizadi, JURNAL umuman chizilmaydi. */
  const hasPlan = captureDay.data !== undefined && captureDay.data.summary.planned > 0;

  return (
    <>
      <section
        aria-busy={captureDay.isFetching}
        aria-label={t("snapshots.day")}
        className="flex flex-col gap-3"
      >
        <DayPicker />
        <DaySummary day={day} onShowIssues={() => setIssuesOnly(true)} todayIso={todayIso} />
      </section>

      {captureDay.isPending ? (
        /* Z-5 — uchta `Skeleton` qator REAL qator balandligida (§6.2). */
        <section aria-busy="true" aria-label={t("snapshots.logTitle")} role="status">
          <span className="sr-only">{t("common.loading")}</span>
          <Card>
            <CardContent className="flex flex-col gap-2 pt-5">
              <Skeleton className="h-11" />
              <Skeleton className="h-11" />
              <Skeleton className="h-11" />
            </CardContent>
          </Card>
        </section>
      ) : null}

      {captureDay.isError ? (
        <section aria-label={t("snapshots.logTitle")}>
          <Card>
            <CardContent className="pt-5">
              <div
                className="flex flex-col items-start gap-3 rounded-md bg-danger/10 p-4 text-danger-text"
                role="alert"
              >
                <p className="text-sm font-semibold">{t("errors.loadFailedTitle")}</p>
                <p className="text-sm">{t("errors.loadFailedBody")}</p>
                <Button
                  onClick={() => void captureDay.refetch()}
                  size="sm"
                  variant="secondary"
                >
                  {t("common.retry")}
                </Button>
              </div>
            </CardContent>
          </Card>
        </section>
      ) : null}

      {hasPlan ? (
        <section
          aria-busy={captureDay.isFetching}
          aria-label={t("snapshots.logTitle")}
          className="flex flex-col gap-3"
        >
          <Card>
            <CardContent className="flex flex-col gap-4 pt-5">
              {/*
               * ⛔ LEGENDA MATRITSANING USTIDA va u YIG'ILMAYDI (§6.5):
               *    hujayrada matn yo'q, ya'ni ikonka lug'ati birdan-bir
               *    o'rgatuvchi yuza.
               */}
              <div className="flex flex-wrap items-end justify-between gap-3">
                <CaptureLegend />
                <div className="flex flex-col items-start gap-1">
                  <label className="flex items-center gap-2 text-sm" htmlFor={issuesId}>
                    <input
                      checked={issuesOnly}
                      className="size-4 accent-accent"
                      id={issuesId}
                      onChange={(event) => setIssuesOnly(event.target.checked)}
                      type="checkbox"
                    />
                    {t("snapshots.showIssues")}
                  </label>
                  {hiddenCameras > 0 ? (
                    <p className="text-xs text-text-muted">
                      {t("snapshots.issuesHidden", { count: hiddenCameras })}
                    </p>
                  ) : null}
                </div>
              </div>

              {visibleRows.length === 0 ? (
                /*
                 * Z-10 — filtr hech narsa topmadi. ⚠ Bu «hammasi yaxshi»
                 * degani EMAS, u FILTR natijasi; matn fakt aytadi,
                 * tabriklamaydi (§10.4 E-3).
                 */
                <EmptyState
                  action={
                    <Button onClick={() => setIssuesOnly(false)} size="sm" variant="secondary">
                      {t("snapshots.clearFilter")}
                    </Button>
                  }
                  description={t("snapshots.emptyFilteredHint")}
                  title={t("snapshots.emptyFiltered")}
                />
              ) : (
                <CaptureGrid onOpen={setOpenRun} rows={visibleRows} />
              )}
            </CardContent>
          </Card>
        </section>
      ) : null}

      <SnapshotDialog
        cameraName={openRun?.camera_name ?? ""}
        canNext={openIndex >= 0 && openIndex < rowRuns.length - 1}
        canPrev={openIndex > 0}
        channelNo={openRun?.channel_no ?? 0}
        onNavigate={(direction) => {
          const next = rowRuns[openIndex + direction];
          if (next !== undefined) setOpenRun(next);
        }}
        onOpenChange={(open) => {
          if (!open) setOpenRun(null);
        }}
        open={openRun !== null}
        run={openRun}
      />
    </>
  );
}
