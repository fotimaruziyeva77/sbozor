"use client";

import { BellOff, TriangleAlert } from "lucide-react";
import { useFormatter, useNow, useTranslations } from "next-intl";

import { Badge } from "@/components/ui/badge";
import type { BadgeTone } from "@/components/ui/badge";
import { ALERT_SEVERITIES } from "@/lib/api-types";
import type { AlertEvent, AlertSeverityValue } from "@/lib/api-types";
import { cn } from "@/lib/cn";

/*
 * =============================================================================
 * BITTA OGOHLANTIRISH QATORI (§6.7, D-19, D-22).
 *
 * ⛔⛔ DALIL-KADR BU YERGA HECH QACHON KIRMAYDI — NA TASVIR, NA THUMBNAIL,
 *     NA «dalilni ko'rish» HAVOLASI.
 *
 *     Kadrlar bozor tashrifchilarining SHAXSIY MA'LUMOTI, Telegram
 *     serverlari esa loyiha zimmasiga olgan O'zR data-rezidentlik
 *     chegarasidan TASHQARIDA (D-19). Ogohlantirish zonasida faqat MATN
 *     va SONLAR bo'ladi.
 *
 *     Taqiq uch mustaqil qatlamda yashaydi: (1) backend `alert_events`
 *     ga kadr havolasini YOZA olmaydi (04-08 ning yozish paytidagi
 *     allowlisti); (2) javob modelida bunday maydon UMUMAN yo'q (04-09);
 *     (3) shu fayl va `alert-list.tsx` ustidagi matn darvozasi (G-3).
 *     Uchinchisisiz birinchi ikkitasi kelajakdagi tahrirni to'sa
 *     olmasdi — tasvir elementi typecheck'ni ham, lint'ni ham, birorta
 *     komponent testini ham qizartirmaydi.
 *
 * ⛔ YOPISH/BOSTIRISH TUGMASI QURILMAYDI. Ogohlantirishni faqat
 *    TIKLANISH yopadi (backend `resolved_at`). Qo'lda yopish tugmasi
 *    adminga muammoni KO'RMASDAN yashirish imkonini berardi — va bu
 *    D-20 ning («alert yo'qlikka qo'yiladi») aynan teskarisi. Backendda
 *    ham bunday marshrut umuman mavjud emas (04-09).
 *
 * ⛔ `notified_at === null` QATORI YASHIRILMAYDI. «Telegram xabari
 *    yuborilmadi» — aynan shu yerda tug'iladigan «alert bor deb
 *    o'ylash» yolg'onining yagona qarshi dalili: admin ekranda
 *    ogohlantirishni ko'rib, xabar ham ketgan deb hisoblardi, holbuki
 *    tunda telefoniga hech nima kelmagan. Shuning uchun shart faqat
 *    MATNNI tanlaydi, qatorning MAVJUDLIGINI emas.
 *
 * ⚠ `occurrences > 1` QATORI MAJBURIY (D-22): guruhlash MA'LUMOT
 *   YASHIRISH bo'lib ko'rinmasligi kerak. «So'nggi soatda yana 47
 *   marta» — bo'g'ilgan takrorlarning ochiq hisoboti.
 *
 * ⚠ `detail` DAN FAQAT NOMLANGAN KALITLAR O'QILADI. Bu yerda umumiy
 *   sikl YO'Q va bu ATAYIN: `jsonb` ustuniga kelajakdagi har qanday
 *   yozuvchi istalgan kalitni yozishi mumkin va sikl uni JIMGINA
 *   ekranga chiqarardi. ⛔ Bu backend allowlistining IKKINCHI NUSXASI
 *   emas (`api-types.ts:1418-1422` uni ochiq taqiqlaydi) — biz filtr
 *   qurmaymiz, biz shunchaki BILGANIMIZNI chizamiz.
 * =============================================================================
 */

type SeverityView = {
  labelKey:
    | "snapshots.severity.info"
    | "snapshots.severity.warning"
    | "snapshots.severity.critical"
    | "snapshots.severityUnknown";
  tone: BadgeTone;
};

/**
 * `alert_events.severity` -> tone + yorliq (§6.7, §9.4).
 *
 * ⛔ `Record<AlertSeverityValue, …>` ATAYIN (`case-status-badge.tsx`
 *    naqshi): reyestrga to'rtinchi daraja qo'shilsa bu jadval `tsc` da
 *    qizaradi, ya'ni yangi daraja yorliqsiz ekranga chiqib keta olmaydi.
 */
const SEVERITY_VIEW: Record<AlertSeverityValue, SeverityView> = {
  info: { labelKey: "snapshots.severity.info", tone: "neutral" },
  warning: { labelKey: "snapshots.severity.warning", tone: "warning" },
  critical: { labelKey: "snapshots.severity.critical", tone: "danger" },
};

/**
 * ⛔⛔ NOMA'LUM DARAJA — ZAXIRA YORLIQ, ⛔ ENG PAST DARAJA EMAS (WR-11).
 *
 * =============================================================================
 * Eski shakl xaritadan topilmagan qiymatni `??` refleksi bilan
 * ⛔ ENG ZARARSIZ darajaga tushirardi: backend `emergency`
 * qo'shsa, admin uni ekranda ⛔ «Ma'lumot» ko'k nishoni bilan ko'rardi va
 * eng shoshilinch signalni ⛔ E'TIBORSIZ qoldirardi. Bu ⛔ shu faylning
 * O'Z qoidasiga zid (pastda: «XOM KALIT EKRANGA HECH QACHON CHIQMAYDI …
 * noma'lum kalit NOMLANGAN zaxira oladi») — u yerda zaxira NOMLANADI, bu
 * yerda esa qiymat JIMGINA pasaytirilardi.
 *
 * ⛔ `tone="neutral"` — ⛔ `danger` EMAS: qizil rang o'lchanmagan
 *    qiymatni «jiddiy» deb E'LON QILARDI, ya'ni teskari tomondan AYNI
 *    yolg'onni takrorlardi. Neytral nishon faqat bitta rost faktni
 *    aytadi: darajaning yorlig'i hali tarjima qilinmagan.
 *
 * ⛔ MATN XOM KALITNI KO'RSATMAYDI: `emergency` degan satrni ko'rgan
 *    admin uni nosozlik kodi deb o'qib, uni izlashga tushardi
 *    (`ALERT_TITLE_KEYS` bilan aynan bir sabab).
 * =============================================================================
 */
const SEVERITY_UNKNOWN: SeverityView = {
  labelKey: "snapshots.severityUnknown",
  tone: "neutral",
};

/** Qiymat reyestrdami — KO'RINISH qatlamining yagona shoxi. */
function isAlertSeverity(value: string): value is AlertSeverityValue {
  return (ALERT_SEVERITIES as readonly string[]).includes(value);
}

/**
 * `alert_events.alert_key` -> tarjima kaliti.
 *
 * ⛔ XOM KALIT EKRANGA HECH QACHON CHIQMAYDI (§6.7). Noma'lum kalit
 *    `errors.generic` ga tushadi: `capture_stopped` degan satrni ko'rgan
 *    admin uni nosozlik kodi deb o'qib, uni izlashga tushardi.
 *
 * Manba: reyestr — `app/jobs/alerting.py::ALERT_META`; a'zolar SONI esa
 * `frontend/scripts/snapshot-copy.test.mjs` ning `ALERT_TITLE_KEY_COUNT`
 * qulfida (IN-03).
 * ⚠ SON BU IZOHDA ATAYIN YOZILMAYDI: oldingi shakl («o'n bitta») reyestr
 *   o'sganda JIMGINA eskirdi va izoh koddan ajralib ketdi. Qulf esa
 *   eskirmaydi — u a'zo qo'shilganda darvozani QIZARTIRADI.
 *
 * ⛔ REYESTR EKSPORT QILINADI va bu ⛔ QULAYLIK EMAS: `alert-list.test.tsx`
 *    a'zolarni AYNAN shu yerdan ITERATSIYA qilib RENDER holida o'lchaydi
 *    (07 `deferred-items.md` №1-qo'shimchasi). Testda qo'lda ro'yxat
 *    yozilsa, o'n yettinchi a'zo qo'shilganda u JIMGINA eskirardi va
 *    darvoza «hammasi chizildi» deb yolg'on gapirardi (05-13 darsi).
 * ⚠ `nvr_account_locked` UI-SPEC §11.9 jadvalida YO'Q edi va u shu
 *   rejada qo'shildi: u `critical` va HECH QACHON bo'g'ilmaydi, ya'ni
 *   matnsiz qolgan taqdirda admin eng shoshilinch xabarni «Kutilmagan
 *   xato» ko'rinishida olardi.
 * ⚠ `billing_close_stale` 6-fazada qo'shildi va u AYNAN o'sha sinfda:
 *   u `critical`, bo'g'ilmaydi va uning manbai «kunlik patta hisobi
 *   umuman ishlamadi» — matnsiz qolganda admin platformaning eng
 *   qimmat nosozligini «Kutilmagan xato» bo'lib ko'rardi.
 * ⚠ `vendor_binding_conflict` 7-fazada (07-08, D-26b) qo'shildi va u
 *   yagona SO'ROV YO'LIDAN tug'iladigan kalit: uni supurgi emas,
 *   `binding_repo.resolve()` ochadi. Matnsiz qolganda admin «reyestrda
 *   ikki sotuvchida bir xil raqam bor» xabarini «Kutilmagan xato» bo'lib
 *   ko'rardi va nuqsonni tuzatish yo'lini topa olmasdi.
 *   ⛔ MATNDA TELEFON RAQAMI HAM, SOTUVCHI ISMI HAM YO'Q: alert Telegram
 *   orqali ham ketadi va Telegram serverlari loyiha zimmasiga olgan O'zR
 *   data-rezidentlik chegarasidan TASHQARIDA (D-19 bilan bir xil sabab).
 *   Tuzatish veb yuzasida bajariladi.
 * ⚠ OXIRGI TO'RTTASI 07-14 DA (D-17) QO'SHILDI va ular BITTA sinfda:
 *   fon oqimining YURAK URISHI YO'Q. Ularsiz `billing_close_stale` bilan
 *   aynan bir xil nosozlik takrorlanardi — kalit `ALERT_META` da bo'lib,
 *   ekranda «Kutilmagan xato» bo'lib chizilardi, ya'ni «uchala locale'da
 *   matn bor» da'vosi BO'SH-ROST bo'lardi (07-08 ning o'lchangan darsi).
 *   ⛔ `outboxStale` MATNI «o'qildi» yoki «yetkazildi» DA'VOSINI QILMAYDI
 *   (Pitfall 2): u navbatning TO'XTAGANINI aytadi. Telegram Bot API
 *   yetkazilganlik kvitansiyasini umuman bermaydi va bu semantika butun
 *   fazada BIR XIL (`outbox.py` ning `delivered` bandi).
 * ⚠ `notification_stale` (Topilma №I) `outboxStale` DAN AJRALIB TURISHI
 *   SHART va bu matn tanlovining o'zi: `outboxStale` — jobning O'LIMI,
 *   `notificationStale` — job TIRIK bo'lgani holda BO'SHAMAYOTGAN navbat.
 *   Ikkalasiga bir xil jumla yozish adminni «navbat to'xtadi» degan
 *   xulosaga olib borardi, holbuki tik har daqiqada yugurib turibdi va
 *   tuzatish yo'li BOSHQA (manzil/bog'lanish, jarayon emas).
 */
export const ALERT_TITLE_KEYS = {
  capture_stopped: "snapshots.alertKey.captureStopped",
  capture_missed: "snapshots.alertKey.captureMissed",
  camera_offline: "snapshots.alertKey.cameraOffline",
  capture_credential_unreadable: "snapshots.alertKey.credentialUnreadable",
  nvr_account_locked: "snapshots.alertKey.nvrAccountLocked",
  backup_stale: "snapshots.alertKey.backupStale",
  retention_stale: "snapshots.alertKey.retentionStale",
  billing_close_stale: "snapshots.alertKey.billingCloseStale",
  disk_pressure: "snapshots.alertKey.diskPressure",
  capture_recovered: "snapshots.alertKey.captureRecovered",
  vendor_binding_conflict: "snapshots.alertKey.vendorBindingConflict",
  outbox_stale: "snapshots.alertKey.outboxStale",
  reconciliation_stale: "snapshots.alertKey.reconciliationStale",
  digest_stale: "snapshots.alertKey.digestStale",
  overdue_stale: "snapshots.alertKey.overdueStale",
  notification_stale: "snapshots.alertKey.notificationStale",
} as const;

type AlertTitleKey = (typeof ALERT_TITLE_KEYS)[keyof typeof ALERT_TITLE_KEYS];

/**
 * Yaroqli lahza yoki ⛔ `null` — «tizim buni O'LCHAY OLMADI».
 *
 * ⛔ ZAXIRA QIYMAT YO'Q (`Date.now()` ham, epoxa ham): to'qilgan lahza
 *    ekranga O'LCHANGAN vaqt bo'lib chizilardi (05-14 darsi).
 */
function parseInstant(value: string): number | null {
  const ms = Date.parse(value);
  return Number.isFinite(ms) ? ms : null;
}

/**
 * Ikki lahza orasidagi davomiylik — daqiqa, uzoq bo'lsa soat.
 *
 * ⚠ MATN EMAS, SON + BIRLIK: `Intl` birlikni uchala tilda o'zi
 *   chizadi, ya'ni «2 s 15 daq» kabi tarjima qilinmaydigan qisqartma
 *   tug'ilmaydi (§11.11 ning atama qoidasi bilan bir xil sabab).
 *
 * =============================================================================
 * ⛔⛔ YARAMAS SATRDA `null` — `0` HAM, «—» HAM EMAS (WR-12).
 *
 * `Date.parse` yaroqsiz satrda `NaN` beradi va JS semantikasi uni
 * ⛔ JIMGINA olib o'tadi: `Math.max(0, NaN) === NaN`,
 * `Math.max(1, NaN) === NaN`, `NaN < 120` esa `false` — ya'ni eski shakl
 * `{ unit: "hour", value: NaN }` qaytarardi.
 *
 * ⛔ VA U EKRANDA `NaN` BO'LIB KO'RINMASDI: `Intl` `NaN` ni ⛔ LOCALE'GA
 *    TARJIMA qiladi va uz-Latn da qator «son emas soat davom etdi» bo'lib
 *    chizilardi (o'lchandi, 08-10 QIZIL bosqichi). Ya'ni faqat ASCII
 *    `NaN` ni qidiradigan darvoza bu nosozlikni ⛔ UMUMAN ko'rmasdi.
 *
 * ⛔ `null` — CHAQIRUVCHI UCHUN BUYRUQ: davomiylik elementi ⛔ UMUMAN
 *    chizilmaydi (D-10). `0` yozish «bir zumda hal bo'ldi» degan YOLG'ON
 *    da'vo, «—» esa TO'QILGAN qiymat bo'lardi.
 * =============================================================================
 */
export function alertDurationParts(
  fromIso: string,
  toIso: string,
): { unit: "hour" | "minute"; value: number } | null {
  const from = parseInstant(fromIso);
  const to = parseInstant(toIso);
  if (from === null || to === null) return null;

  const ms = Math.max(0, to - from);
  const minutes = Math.max(1, Math.round(ms / 60_000));
  if (minutes < 120) return { unit: "minute", value: minutes };
  return { unit: "hour", value: Math.round(minutes / 60) };
}

function asNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function asText(value: unknown): string | null {
  return typeof value === "string" && value.length > 0 ? value : null;
}

export function AlertRow({ alert }: { alert: AlertEvent }) {
  const t = useTranslations();
  const format = useFormatter();
  const now = useNow();

  const severity: SeverityView = isAlertSeverity(alert.severity)
    ? SEVERITY_VIEW[alert.severity]
    : SEVERITY_UNKNOWN;
  const titleKey: AlertTitleKey | undefined =
    ALERT_TITLE_KEYS[alert.alert_key as keyof typeof ALERT_TITLE_KEYS];

  const resolvedAt = alert.resolved_at;
  const isClosed = resolvedAt !== null;
  /*
   * ⛔ IKKI QIYMAT, IKKI MUSTAQIL SHOX (WR-12): yopilish LAHZASI o'qilsa
   *   ham DAVOMIYLIK o'lchanmasligi mumkin (`first_seen_at` yaroqsiz
   *   bo'lsa). Ularni bitta shartga bog'lash o'qilgan faktni ham
   *   ekrandan olib tashlardi.
   */
  const resolvedAtMs = resolvedAt === null ? null : parseInstant(resolvedAt);

  /*
   * ⚠ NOMLANGAN KALITLAR — sikl EMAS (fayl boshidagi izoh). Har biri
   *   o'z tipida o'qiladi: `jsonb` da son o'rniga satr kelib qolsa
   *   qator chizilmaydi va «[object Object]» ekranga chiqmaydi.
   */
  const marketName = asText(alert.detail.market_name);
  const cameraCount = asNumber(alert.detail.camera_count);
  const errorCode = asText(alert.detail.error_code);
  const clock = asText(alert.detail.slot_time);
  const staleHours = asNumber(alert.detail.stale_hours);
  const diskPercent = asNumber(alert.detail.disk_pct);
  const staleMinutes = asNumber(alert.detail.stale_minutes);
  const pendingCount = asNumber(alert.detail.pending_count);
  const hasDetail =
    marketName !== null ||
    cameraCount !== null ||
    errorCode !== null ||
    clock !== null ||
    staleHours !== null ||
    diskPercent !== null ||
    staleMinutes !== null ||
    pendingCount !== null;

  const duration =
    resolvedAt === null
      ? null
      : alertDurationParts(alert.first_seen_at, resolvedAt);

  return (
    <li
      className={cn(
        "flex flex-col gap-2 rounded-md border border-border p-3",
        isClosed ? "bg-surface-muted" : "bg-surface",
      )}
    >
      <div className="flex flex-wrap items-center gap-2">
        {/*
         * Rang YAGONA signal emas (§9.4): badge MATN tashiydi
         * («Jiddiy»), sarlavha esa uchinchi kanal.
         */}
        <Badge className="gap-1" tone={severity.tone}>
          <TriangleAlert aria-hidden="true" className="size-3" />
          {t(severity.labelKey)}
        </Badge>
        <p className="text-sm font-semibold">
          {titleKey === undefined ? t("errors.generic") : t(titleKey)}
        </p>
      </div>

      {/*
       * IKKALA VAQT HAM MAJBURIY (§6.7): faqat oxirgisi «bu qachondan
       * beri davom etyapti?» savolini javobsiz qoldirardi.
       */}
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-text-muted">
        <span>
          {t("snapshots.alertFirstSeen", {
            time: format.dateTime(new Date(alert.first_seen_at), {
              dateStyle: "short",
              timeStyle: "short",
            }),
          })}
        </span>
        <span>
          {t("snapshots.alertLastSeen", {
            time: format.relativeTime(new Date(alert.last_seen_at), now),
          })}
        </span>
      </div>

      {alert.occurrences > 1 ? (
        <p className="text-xs text-text-muted">
          {t("snapshots.alertRepeated", { count: alert.occurrences })}
        </p>
      ) : null}

      {alert.notified_at === null ? (
        <p
          className="flex items-center gap-1 text-xs text-text"
          title={t("snapshots.alertNotNotifiedWhy")}
        >
          <BellOff aria-hidden="true" className="size-3" />
          {t("snapshots.alertNotNotified")}
        </p>
      ) : (
        <p className="text-xs text-text-muted">
          {t("snapshots.alertNotified", {
            time: format.dateTime(new Date(alert.notified_at), {
              timeStyle: "short",
            }),
          })}
        </p>
      )}

      {hasDetail ? (
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-text-muted">
          {marketName === null ? null : (
            <span>{t("snapshots.alertMarket", { name: marketName })}</span>
          )}
          {cameraCount === null ? null : (
            <span>{t("snapshots.alertCameraCount", { count: cameraCount })}</span>
          )}
          {clock === null ? null : (
            <span>{t("snapshots.alertTime", { time: clock.slice(0, 5) })}</span>
          )}
          {staleHours === null ? null : (
            <span>{t("snapshots.alertStaleHours", { count: staleHours })}</span>
          )}
          {staleMinutes === null ? null : (
            <span>
              {t("snapshots.alertStaleMinutes", { count: staleMinutes })}
            </span>
          )}
          {pendingCount === null ? null : (
            <span>
              {t("snapshots.alertPendingCount", { count: pendingCount })}
            </span>
          )}
          {diskPercent === null ? null : (
            <span>{t("snapshots.alertDiskUsed", { percent: diskPercent })}</span>
          )}
          {errorCode === null ? null : (
            <span className="font-mono">{errorCode}</span>
          )}
        </div>
      ) : null}

      {/*
       * ⛔ HAR ELEMENT O'Z SHOXI BILAN (WR-12): o'qilmagan lahza ham,
       *   o'lchanmagan davomiylik ham ⛔ UMUMAN chizilmaydi. O'ram esa
       *   ikkalasi ham yo'q bo'lganda ⛔ BO'SH QATOR qoldirmaydi.
       */}
      {resolvedAtMs === null && duration === null ? null : (
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-text-muted">
          {resolvedAtMs === null ? null : (
            <span>
              {t("snapshots.alertResolvedAt", {
                time: format.dateTime(new Date(resolvedAtMs), {
                  dateStyle: "short",
                  timeStyle: "short",
                }),
              })}
            </span>
          )}
          {duration === null ? null : (
            <span>
              {t("snapshots.alertDuration", {
                duration: format.number(duration.value, {
                  style: "unit",
                  unit: duration.unit,
                  unitDisplay: "long",
                }),
              })}
            </span>
          )}
        </div>
      )}
    </li>
  );
}
