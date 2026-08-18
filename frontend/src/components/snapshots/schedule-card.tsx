"use client";

import { Fragment } from "react";
import { CalendarDays, TriangleAlert } from "lucide-react";
import { useFormatter, useLocale, useTranslations } from "next-intl";

import { CoverageWarning } from "@/components/snapshots/coverage-warning";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type {
  ScheduleModeValue,
  SnapshotScheduleDay,
  SnapshotScheduleProfile,
} from "@/lib/api-types";
import { formatBusinessDay } from "@/lib/format-day";
import { useScheduleToday } from "@/lib/snapshot-queries";

/*
 * =============================================================================
 * ZONA A — JADVAL KARTASI (Y-1, §4.3).
 *
 * ⛔⛔ «ERTAGA» QATORI DOIM RENDER QILINADI — BUGUNGI BILAN BIR XIL
 *     BO'LSA HAM. D-05 ning butun mazmuni shu IKKI qatorning
 *     MAVJUDLIGIDA, ularning farqida emas.
 *
 *     Vasvasa har ko'rikda qaytadi: «bir xil bo'lsa nega ikki marta
 *     yozamiz?». Ikki qator bir xil bo'lganda ham axborot tashiydi — u
 *     «bugun qanday bo'lsa, ertaga ham shunday» deydi. Bitta qatorga
 *     yig'ilsa, admin jadvalni tahrirlagan lahzada ekranda hech narsa
 *     o'zgarmasdi va u «saqlandimi?» degan savol bilan qolardi. Qoida
 *     `schedule-card.test.tsx` da qulflangan va u FARQ IZOHI testidan
 *     MUSTAQIL — biri ikkinchisining o'rnini bosmaydi.
 *
 * ⚠ SARIQ MATN ISHLATILMAYDI (§9.2): farq izohi `bg-warning/20` fonida
 *   oddiy `text-text` bilan chiziladi (o'lchangan 15,64:1). Ogohlantirish
 *   rangi matn sifatida oq fonda 2,03:1 beradi — falokat. Taqiqlangan
 *   utilita nomi bu izohda LITERAL yozilmaydi, chunki qabul mezoni uni
 *   grep bilan qidiradi va izohdagi nusxa darvozani o'z hujjati ustida
 *   qizartirardi (kodbazada besh marta takrorlangan sinf).
 *
 * ⚠ AKSENT BUDJETI (§9.3): bu KUZATUV sahifasi va uning to'g'ri javobi —
 *   «hamma narsa joyida». Shuning uchun sahifada birlamchi (aksent
 *   fonli) tugma UMUMAN YO'Q: ikkala amal ham ikkilamchi. Aksent faqat
 *   dialog ICHIDAGI saqlash tugmasida qoladi. Bu 3-fazadan ATAYIN farq —
 *   `/cameras` bir va'dani bajaradigan HARAKAT sahifasi edi.
 *
 * ⚠ RBAC KO'ZGUSI: `camera_manage` yo'q bo'lsa tugmalar RENDER
 *   QILINMAYDI — `aria-disabled` ham emas. Ishlamaydigan tugma
 *   foydalanuvchiga 403 beradi va tizim buzuq ko'rinadi (T-04-77).
 *   Haqiqiy darvoza serverda (`require_permission(CAMERA_MANAGE)`).
 * =============================================================================
 */

/**
 * Profil rejimi -> yorliq kaliti.
 *
 * ⚠ `as const` MAJBURIY (`weekday-picker.tsx:44-54` naqshi): `t()`
 *   next-intl ning tip xavfsizligi ostida ishlaydi va `` t(`snapshots.
 *   scheduleMode${mode}`) `` shaklidagi dinamik kalit kompilyatorga
 *   noma'lum bo'lardi — kalit xatosi runtime'ga qolardi. `satisfies`
 *   esa uchala rejimning qamralganini tekshiradi.
 */
const MODE_KEYS = {
  past: "snapshots.scheduleModePast",
  active: "snapshots.scheduleModeActive",
  future: "snapshots.scheduleModeFuture",
} as const satisfies Record<ScheduleModeValue, string>;

/**
 * `06:00:00` -> `06:00` (§13.4).
 *
 * ⚠ XOM JAVOB O'ZGARTIRILMAYDI, format CHIZISH joyida qisqartiriladi:
 *   Pydantic `time` ni `HH:MM:SS` bo'lib seriyalaydi (04-09 da
 *   o'lchangan), sxemada esa u satr bo'lib qoladi. Kesish sxemada
 *   bajarilsa keyingi iste'molchi «nega serverdagi qiymat boshqa?»
 *   savoliga tushardi.
 *
 * ⚠ `next-intl` ISHLATILMAYDI va bu ataylab: bu JADVAL QIYMATI, ya'ni
 *   24 soatlik va uchala tilda BIR XIL. Mahalliylashtirilgan vaqt
 *   `06:00 AM` bo'lib chiqib, NVR interfeysidagi qiymat bilan
 *   solishtirib bo'lmas holga kelardi.
 */
export function formatSlotTime(raw: string): string {
  return raw.slice(0, 5);
}

export function ScheduleCard({
  canManage,
  onAddSeasonal,
  onEdit,
}: {
  /** `camera_manage` — huquq yo'q bo'lsa tugmalar RENDER QILINMAYDI. */
  canManage: boolean;
  /**
   * DL-2 ni ochadi.
   *
   * ⚠ IXTIYORIY: dialogning o'zi 04-10 ning uchinchi taskida quriladi va
   *   sahifa uni o'shanda ulaydi. Tugmaning O'ZI esa shu yerda tug'iladi,
   *   chunki RBAC ko'zgusining testi aynan uning MAVJUDLIGINI o'lchaydi.
   */
  onAddSeasonal?: () => void;
  /**
   * DL-1 ni ochadi (yuqoridagi bilan bir xil sabab).
   *
   * ⚠ TIP `null` NI QABUL QILMAYDI va bu tuzatishning ikkinchi yarmi:
   *   chaqiruvchi profilsiz holatni umuman ko'ra olmaydi, ya'ni «dialog
   *   nima bilan ochiladi?» savoli KOMPILYATSIYA paytida hal bo'ladi.
   */
  onEdit?: (profile: SnapshotScheduleProfile) => void;
}) {
  const t = useTranslations();
  const schedule = useScheduleToday();

  /* Z-1 — bitta `Skeleton` blok (§6.2). */
  if (schedule.isPending) {
    return (
      <Card>
        <CardContent className="pt-5">
          <div aria-busy="true" role="status">
            <span className="sr-only">{t("common.loading")}</span>
            <Skeleton className="h-32" />
          </div>
        </CardContent>
      </Card>
    );
  }

  /*
   * Z-2 — meros xato bloki (§6.2).
   *
   * ⚠ Bu BIZNING API'mizning xatosi, jadvalning emas: qayta urinish shu
   *   yerda XAVFSIZ va u NVR ga umuman bormaydi.
   */
  if (schedule.isError) {
    return (
      <Card>
        <CardContent className="pt-5">
          <div
            className="flex flex-col items-start gap-3 rounded-md bg-danger/10 p-4 text-danger-text"
            role="alert"
          >
            <p className="text-sm font-semibold">
              {t("errors.loadFailedTitle")}
            </p>
            <p className="text-sm">{t("errors.loadFailedBody")}</p>
            <Button
              onClick={() => void schedule.refetch()}
              size="sm"
              variant="secondary"
            >
              {t("common.retry")}
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  const data = schedule.data;
  const profile = data.profile;

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center gap-2">
          <CalendarDays aria-hidden="true" className="size-4 shrink-0" />
          {/*
           * Profil nomi — DB KONTENTI va TARJIMA QILINMAYDI (1-faza
           * D-16). `truncate` + `title`: uzunligi noma'lum.
           */}
          <span className="truncate text-sm font-semibold" title={profile?.name}>
            {profile === null ? t("snapshots.scheduleTitle") : profile.name}
          </span>
          {profile === null ? null : (
            <Badge tone="muted">{t(MODE_KEYS[profile.mode])}</Badge>
          )}
        </div>
        {profile === null ? null : <ProfilePeriod profile={profile} />}
      </CardHeader>

      <CardContent className="flex flex-col gap-4">
        {/*
         * ⛔ IKKALA QATOR HAM SHARTSIZ. `<dl>` — yorliq va mazmun
         *    dasturiy juftlik, ya'ni skrinriderda «Ertaga» va uning
         *    vaqtlari birga eshitiladi.
         */}
        <dl className="flex flex-col gap-2">
          <DayRow
            day={data.today}
            label={t("snapshots.today")}
            timesCount={t("snapshots.timesCount", {
              count: data.today.times.length,
            })}
          />
          <DayRow
            day={data.tomorrow}
            label={t("snapshots.tomorrow")}
            timesCount={t("snapshots.timesCount", {
              count: data.tomorrow.times.length,
            })}
          />
        </dl>

        {/*
         * D-05 farq izohi — MUSTAQIL shart. `role="status"`: u sahifa
         * yuklanganda ham, jadval saqlangandan keyin ham o'sha joyda
         * turadi va yangilanishi e'lon qilinadi. `role="alert"` EMAS —
         * bu nosozlik emas, qoida.
         */}
        {data.differs ? (
          <p
            className="flex items-start gap-2 rounded-md bg-warning/20 px-3 py-2 text-sm text-text"
            role="status"
          >
            <TriangleAlert aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
            {t("snapshots.takesEffectTomorrow")}
          </p>
        ) : null}

        {/*
         * Yopiq kun qatori — O'QISH UCHUN, tugma EMAS (D-10, §16.2).
         * `capture_on_closed_days` `market_profile` ning maydoni va u
         * 2-fazaning egaligida; bitta checkbox uchun boshqa fazaning
         * sozlamalar yuzasini ochish noto'g'ri egalik bo'lardi.
         */}
        {data.capture_on_closed_days ? (
          <p
            className="text-xs text-text-muted"
            title={t("snapshots.closedDaysWhy")}
          >
            {t("snapshots.closedDaysIncluded")}
          </p>
        ) : null}

        {canManage ? (
          <div className="flex flex-col gap-2 sm:flex-row">
            {/*
             * ⛔ TAHRIR TUGMASI IKKI SHARTNI TALAB QILADI: huquq VA
             *    OBYEKT. Ilgari faqat birinchisi tekshirilardi va
             *    `profile === null` da tugma `onEdit?.(null)` ni
             *    chaqirib, dialogni obyektsiz ochardi — ya'ni u
             *    va'dasini HECH QACHON bajarmasdi (Topilma №6).
             *
             *    Bu yuqoridagi RBAC ko'zgusi bilan AYNI qoida, boshqa
             *    sabab bilan: ishlamaydigan tugma yo'q tugmadan yomonroq
             *    — u tizimni buzuq ko'rsatadi va foydalanuvchini o'z
             *    xatosini izlashga majbur qiladi.
             *
             * ⚠ MAVSUMIY TUGMA FAQAT `canManage` ostida QOLADI va bu
             *   FARQ mazmunli: u YANGI profil yaratadi, ya'ni profilsiz
             *   bozorda ham to'liq ma'noli amal.
             */}
            {profile !== null ? (
              <Button onClick={() => onEdit?.(profile)} variant="secondary">
                {t("snapshots.editSchedule")}
              </Button>
            ) : null}
            <Button onClick={() => onAddSeasonal?.()} variant="secondary">
              {t("snapshots.addSeasonal")}
            </Button>
          </div>
        ) : null}

        <CoverageWarning
          count={data.uncovered_days}
          horizonDays={data.uncovered_horizon_days}
        />
      </CardContent>
    </Card>
  );
}

/* --- Bitta kun qatori ------------------------------------------------------ */

function DayRow({
  day,
  label,
  timesCount,
}: {
  day: SnapshotScheduleDay;
  label: string;
  timesCount: string;
}) {
  return (
    <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
      <dt className="w-16 shrink-0 text-sm font-semibold">{label}</dt>
      <dd className="flex min-w-0 flex-1 flex-wrap items-baseline gap-x-2 gap-y-1">
        <span className="text-sm">{timesCount}</span>
        {/*
         * Vaqtlar `font-mono`: proporsional shriftda `06:00` va `18:00`
         * turli kenglikda bo'lib, ro'yxat qiyshayardi (§8.3). Ajratgich
         * `aria-hidden` — skrinrider har vaqtdan keyin «nuqta» demasin.
         */}
        {day.times.map((time, index) => (
          <Fragment key={time}>
            {index > 0 ? (
              <span aria-hidden="true" className="text-xs text-text-muted">
                ·
              </span>
            ) : null}
            <span className="font-mono text-xs">{formatSlotTime(time)}</span>
          </Fragment>
        ))}
      </dd>
    </div>
  );
}

/* --- Profil davri ---------------------------------------------------------- */

function ProfilePeriod({ profile }: { profile: SnapshotScheduleProfile }) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();

  const from = t("snapshots.scheduleFrom", {
    date: formatBusinessDay(format, profile.starts_on, locale),
  });
  const until =
    profile.ends_on === null
      ? null
      : t("snapshots.scheduleUntil", {
          date: formatBusinessDay(format, profile.ends_on, locale),
        });

  return (
    <p className="text-xs text-text-muted">
      {until === null ? from : `${from} ${until}`}
    </p>
  );
}
