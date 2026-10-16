"use client";

import type { ReactNode } from "react";
import {
  CheckCircle2,
  CircleSlash,
  FileWarning,
  ImageOff,
  MoonStar,
  XCircle,
} from "lucide-react";
import { useFormatter, useLocale, useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import type { CaptureDaySummary } from "@/lib/api-types";
import { cn } from "@/lib/cn";
import { formatBusinessDay } from "@/lib/format-day";
import { useCaptureDay } from "@/lib/snapshot-queries";

/*
 * =============================================================================
 * ZONA C — KUNLIK XULOSA (§6.3).
 *
 * ⛔⛔ OLTALA HISOBLAGICH HAM DOIM KO'RINADI — NOL BO'LGANDA HAM.
 *
 *     Nol qiymatlilarni tashlab yuboradigan shart bu yerda YO'Q va
 *     qo'shilmaydi. U keyingi tahrirlovchi uchun eng tabiiy «tozalash»
 *     bo'lib ko'rinadi, lekin aynan shu «tozalash» SC#2 ning UI
 *     isbotini o'ldiradi: nol — NATIJA, uning yo'qligi emas.
 *
 *     «0 ta kadr olinmadi» va «olinmadi hisoblagichi umuman yo'q» — ikki
 *     butunlay boshqa da'vo. Birinchisi «tizim tekshirdi va muammo
 *     topmadi» deydi; ikkinchisi «tizim buni umuman o'lchadimi?» degan
 *     savolni ochiq qoldiradi. Bu 3-fazadagi «uch hisoblagich»
 *     qoidasining aynan takrori [MEROS: 03-UI-SPEC §6.3] va u yerda ham
 *     yechim nol qatorni MAJBURIY ko'rsatish edi.
 *
 *     Qoida `day-summary.test.tsx` da (G-8) va qabul mezonining matn
 *     darvozasida qulflangan.
 *
 * ⛔ NISBIY KO'RSATKICH QO'YILMAYDI (§6.3 oxirgi qatori). `173 / 175`
 *    aniqroq va u YAXLITLANMAYDI; ulushga aylantirilgan son esa ikkita
 *    o'tkazib yuborilgan kadrni ko'zdan yashirardi. Shu sababdan bu
 *    faylda ulush belgisi umuman uchramaydi va uni qo'shish darvozani
 *    qizartiradi.
 *
 * ⛔ `planned === 0` — «hammasi nol» EMAS (Z-7 va Z-8 ning farqi
 *    hayotiy): u «jadval bu kunni qoplamaydi» degani. Hisoblagichlar
 *    UMUMAN chizilmaydi va `0 / 0` ham chiqmaydi — aks holda admin
 *    «tizim ishlamayapti» degan xulosaga kelardi.
 *
 * ⚠ `role="status"`, `alert` EMAS: kunlik xulosa — HISOBOT. `alert`
 *   uni har sahifa yuklanishida shoshilinch xabar sifatida o'qitardi.
 *   Jonli hudud KALLOUTNI ham qamraydi va bu ATAYIN (§12.6): poll bilan
 *   yangilanishda hujayralar jimgina o'zgaradi, `missed` soni oshsa esa
 *   xulosa qayta e'lon qilinadi — bu YAGONA istisno.
 * =============================================================================
 */

type CounterView = {
  Icon: typeof CheckCircle2;
  /** 261016: yorliq ostidagi bir-ikki so'zli izoh — «xato» va «olinmadi» farqi. */
  hintKey:
    | "snapshots.countOkHint"
    | "snapshots.countDarkHint"
    | "snapshots.countBlankHint"
    | "snapshots.countCorruptHint"
    | "snapshots.countFailedHint"
    | "snapshots.countMissedHint";
  labelKey:
    | "snapshots.countOk"
    | "snapshots.countDark"
    | "snapshots.countBlank"
    | "snapshots.countCorrupt"
    | "snapshots.countFailed"
    | "snapshots.countMissed";
  /** Nol bo'lmaganda ikonka doirasining rangi; nolda — neytral. */
  tone: "success" | "warning" | "danger";
  value: (summary: CaptureDaySummary) => number;
};

/**
 * Oltita hisoblagich — TARTIB VA TARKIB QAT'IY (§6.3 eskizi).
 *
 * ⚠ Ro'yxat SHARTSIZ o'qiladi: u yerda hech qanday tanlash bosqichi
 *   yo'q va bo'lmaydi ham. Ikonkalar legenda (§6.5) va matritsa
 *   hujayralari bilan AYNI — xulosadagi `⊘` va jurnaldagi `⊘` bir xil
 *   narsani anglatishi kerak, aks holda legenda ikki marta o'rganilardi.
 */
const COUNTERS: readonly CounterView[] = [
  {
    Icon: CheckCircle2,
    hintKey: "snapshots.countOkHint",
    labelKey: "snapshots.countOk",
    tone: "success",
    value: (summary) => summary.ok,
  },
  {
    Icon: MoonStar,
    hintKey: "snapshots.countDarkHint",
    labelKey: "snapshots.countDark",
    tone: "warning",
    value: (summary) => summary.dark,
  },
  {
    Icon: ImageOff,
    hintKey: "snapshots.countBlankHint",
    labelKey: "snapshots.countBlank",
    tone: "warning",
    value: (summary) => summary.blank,
  },
  {
    Icon: FileWarning,
    hintKey: "snapshots.countCorruptHint",
    labelKey: "snapshots.countCorrupt",
    tone: "warning",
    value: (summary) => summary.corrupt,
  },
  {
    Icon: XCircle,
    hintKey: "snapshots.countFailedHint",
    labelKey: "snapshots.countFailed",
    tone: "danger",
    value: (summary) => summary.failed,
  },
  {
    Icon: CircleSlash,
    hintKey: "snapshots.countMissedHint",
    labelKey: "snapshots.countMissed",
    tone: "danger",
    value: (summary) => summary.missed,
  },
];

export function DaySummary({
  day,
  onShowIssues,
  todayIso,
}: {
  day: string;
  /** [Muammolilarni ko'rsatish] — `?issues=1` ni yoqadi (§6.3). */
  onShowIssues: () => void;
  todayIso: string;
}) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();
  const query = useCaptureDay(day, todayIso);

  /* Z-5 — birinchi yuklash: bitta `Skeleton` qator (§6.2). */
  if (query.isPending) {
    return (
      <Card>
        <CardContent className="pt-5">
          <div aria-busy="true" role="status">
            <span className="sr-only">{t("common.loading")}</span>
            <Skeleton className="h-16" />
          </div>
        </CardContent>
      </Card>
    );
  }

  /* Z-9 — zona xatosi. Hujayra xatosidan BUTUNLAY boshqa narsa (§6.1). */
  if (query.isError) {
    return (
      <Card>
        <CardContent className="pt-5">
          <div
            className="flex flex-col items-start gap-3 rounded-md bg-danger/10 p-4 text-danger-text"
            role="alert"
          >
            <p className="text-sm font-semibold">{t("errors.loadFailedTitle")}</p>
            <p className="text-sm">{t("errors.loadFailedBody")}</p>
            <Button onClick={() => void query.refetch()} size="sm" variant="secondary">
              {t("common.retry")}
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  const { archived_present: archivedPresent, summary } = query.data;

  /*
   * ⛔ Z-7 — kunda reja UMUMAN yo'q. Hisoblagichlar chizilmaydi va
   *    «olindi» qatori ham chiqmaydi: `0 / 0` «tizim bugun ishlamadi»
   *    degan yolg'on signal berardi, holbuki jadval bu kunni umuman
   *    qoplamaydi.
   *
   * ⚠ AMAL BERILMAYDI (§10.4 E-2): «Jadvalni ko'rish» havolasi faqat
   *   `uncovered_days > 0` bo'lganda ma'noli va o'sha son ZONA A ning
   *   javobida yashaydi (`/snapshot-schedules/today`). Uni bu yerda
   *   ikkinchi so'rov bilan olib kelish ikkinchi haqiqat manbai
   *   bo'lardi; qoplanmagan kunlar ogohlantirishi zona A da allaqachon
   *   ko'rinadi.
   */
  if (summary.planned === 0) {
    return (
      <Card>
        <CardContent className="pt-5">
          <EmptyState
            description={t("snapshots.emptyNoPlanHint")}
            title={t("snapshots.emptyNoPlan")}
          />
        </CardContent>
      </Card>
    );
  }

  const dayLabel = formatBusinessDay(format, day, locale);

  /*
   * 261016: chiziq — natijaning SHAKLI (yashil/sariq/qizil/kutilmoqda).
   * ⛔ U `aria-hidden` va SON BERMAYDI: aniq qiymat ostidagi oltita
   *    hisoblagichda. Har bo'lak kamida 4px — 175 tadan 2 ta yo'qolgan
   *    kadr ham ko'zga tashlanadi (ulush soni esa uni yashirardi).
   */
  const poor = summary.dark + summary.blank + summary.corrupt;
  const lost = summary.failed + summary.missed;
  const waiting = Math.max(0, summary.planned - summary.ok - poor - lost);
  const segments = [
    { className: "bg-success", key: "ok", value: summary.ok },
    { className: "bg-warning", key: "poor", value: poor },
    { className: "bg-danger", key: "lost", value: lost },
    { className: "bg-border-ui", key: "waiting", value: waiting },
  ];

  /*
   * «48 qayerdan?» — reja kamera × vaqt ko'paytmasiga teng bo'lsa, shu
   * ko'rinishda aytiladi. Teng bo'lmasa (kun o'rtasida kamera qo'shilgan)
   * jumla chiqmaydi: noto'g'ri ko'paytma yolg'on bo'lardi.
   */
  const cameraCount = new Set(query.data.rows.map((row) => row.camera_id)).size;
  const timeCount = new Set(query.data.rows.map((row) => row.slot_time)).size;
  const showBreakdown = cameraCount > 0 && cameraCount * timeCount === summary.planned;

  return (
    <Card>
      <CardContent className="flex flex-col gap-4 pt-5">
        {/*
         * ⚠ SANA `font-mono` EMAS (§8.3): u o'qiladigan matn. Format
         *   `next-intl` locale'idan keladi va hafta kuni bilan birga —
         *   «payshanba» adminning kunni tanigan yagona belgisi bo'lishi
         *   mumkin.
         */}
        <p className="text-sm text-text-muted">{dayLabel}</p>

        <div className="flex flex-col gap-4" role="status">
          <div className="flex flex-col gap-2">
            <p className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <span className="text-sm text-text-muted">{t("snapshots.captured")}</span>
              <span className="text-2xl font-semibold tabular-nums">
                {t("snapshots.capturedOf", {
                  done: summary.done,
                  planned: summary.planned,
                })}
              </span>
            </p>
            <span aria-hidden="true" className="dir-split">
              {segments.map((segment) =>
                segment.value === 0 ? null : (
                  <span
                    className={`dir-split-part ${segment.className}`}
                    key={segment.key}
                    style={{ flexGrow: segment.value }}
                  />
                ),
              )}
            </span>
            {showBreakdown ? (
              <p className="text-xs text-text-muted">
                {t("snapshots.planBreakdown", { cameras: cameraCount, times: timeCount })}
              </p>
            ) : null}
          </div>

          {/*
           * ⛔ BU RO'YXATDA TANLASH BOSQICHI YO'Q. Har qanday shart —
           *    «nolmaslarini ko'rsatish», «faqat muammolilarini
           *    ko'rsatish» — G-8 ni buzadi va yuqoridagi izohdagi
           *    sababni yo'q qiladi.
           */}
          <dl className="capture-counters">
            {COUNTERS.map((counter) => (
              <Counter
                Icon={counter.Icon}
                hint={t(counter.hintKey)}
                key={counter.labelKey}
                label={t(counter.labelKey)}
                tone={counter.tone}
                value={counter.value(summary)}
              />
            ))}
          </dl>

          {/*
           * `missed > 0` — G-8 DAN MUSTAQIL da'vo: hisoblagichning
           * o'zi allaqachon ko'rinadi, bu jumla esa uni SO'Z bilan
           * takrorlaydi va keyingi qadamni beradi. Ikkalasi bir
           * shartga bog'lansa, biri ikkinchisining testini
           * qizartirmasdi.
           */}
          {summary.missed > 0 ? (
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm">
                {t("snapshots.missedCallout", { count: summary.missed })}
              </p>
              <Button onClick={onShowIssues} size="sm" variant="ghost">
                {t("snapshots.showIssuesLink")}
              </Button>
            </div>
          ) : null}
        </div>

        {/*
         * Arxivlangan kamera jurnalda KO'RINMAYDI (§6.4 oxirgi qatori) va
         * uning qatorlari xulosaga ham kirmaydi. Bayroqsiz admin «kecha
         * 25 kamera bor edi, bugun 24» farqini nosozlik deb o'ylardi.
         */}
        {archivedPresent ? (
          <p className="text-xs text-text-muted">{t("snapshots.archivedNote")}</p>
        ) : null}
      </CardContent>
    </Card>
  );
}

/**
 * Bitta hisoblagich — raqam va yorliq DASTURIY jihatdan bog'langan
 * (`cameras/discovery-result.tsx:217` naqshi).
 *
 * ⚠ VIZUAL TARTIB `order-*` BILAN: razmetkada `<dt>` `<dd>` dan OLDIN
 *   turadi (HTML `<dl>` ning talabi), ekranda esa raqam yorliqdan oldin
 *   ko'rinadi (§6.3 eskizi). Skrinrider «olinmadi: 2» deb eshitadi,
 *   ya'ni «2» hech qachon yolg'iz kelmaydi.
 */
function Counter({
  Icon,
  hint,
  label,
  tone,
  value,
}: {
  Icon: typeof CheckCircle2;
  hint: string;
  label: string;
  tone: CounterView["tone"];
  value: number;
}) {
  return (
    <div className={cn("capture-counter", value === 0 && "capture-counter-zero")}>
      <dt className="order-2 flex flex-col">
        <span className="capture-counter-label">{label}</span>
        <span className="capture-counter-hint">{hint}</span>
      </dt>
      <dd className="capture-counter-value order-1 m-0">
        {/* Ikonka matnsiz: `dd` ning matni faqat son (G-8 testi shuni o'qiydi). */}
        <span
          aria-hidden="true"
          className={cn(
            "capture-counter-icon",
            value === 0 ? "stat-tone-neutral" : `stat-tone-${tone}`,
          )}
        >
          <Icon className="size-3.5" />
        </span>
        {value}
      </dd>
    </div>
  );
}
