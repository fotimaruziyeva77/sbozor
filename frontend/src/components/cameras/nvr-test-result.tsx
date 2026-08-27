"use client";

import { AlertTriangle } from "lucide-react";
import { useTranslations } from "next-intl";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/cn";
import type { NvrTestConnectionResponse } from "@/lib/api-types";

/*
 * =============================================================================
 * MUVAFFAQIYATLI TEKSHIRUV BLOKI (UI-SPEC §4.5).
 *
 * ⚠ `role="status"`, `role="alert"` EMAS: muvaffaqiyat shoshilinch xabar
 *   emas va u foydalanuvchining ishini uzmasligi kerak. Shu sababdan
 *   FOKUS HAM KO'CHMAYDI — admin tugmada qoladi, e'lon esa
 *   `aria-live="polite"` bilan yetkaziladi.
 *
 * TO'RT QATOR VA UCHTASINING SABABI ALOHIDA:
 *
 *   * MODEL / TURI — «qurilma javob berdi» ning ko'rinadigan dalili;
 *   * KANALLAR SONI **MAJBURIY** — adminning «to'g'ri qurilmaga
 *     ulandimmi?» savoliga YAGONA javobi. 16 kanalli NVR'da 6 ta kamera
 *     ko'rinishi normal holat va bu raqamsiz admin buni bilolmasdi;
 *   * SOAT FARQI **DOIM** ko'rsatiladi — 300 soniyalik chegaradan
 *     kichik bo'lganda ham. 250 soniyalik farq BUGUN ishlaydi, ertaga
 *     esa digest autentifikatsiyasini sindiradi; ko'rsatish uni
 *     OLDINDAN tuzatish imkonini beradi.
 *
 * ⚠ SERIYA RAQAMI BU BOSQICHDA KO'RSATILMAYDI (UI-SPEC §4.5): javobda u
 *   BOR, lekin tekshiruv ekranida u shovqin — hali hech narsa
 *   saqlanmagan va solishtiradigan yozuv yo'q. U yozuv saqlangandan
 *   keyin NVR kartasida chiqadi (`nvr-card.tsx`).
 * =============================================================================
 */

/**
 * Ogohlantirish chegarasi — soniya (UI-SPEC §4.5).
 *
 * ⚠ QURILMANING RAD ETISH CHEGARASI EMAS: Hikvision digest'ni ~300
 *   soniyadan katta farqda rad etadi. 120 — bundan sezilarli PASTDA va
 *   bu ataylab: ogohlantirish nosozlik BO'LGUNCHA chiqishi kerak, aks
 *   holda u xatoning takroridan boshqa narsa emas.
 */
export const CLOCK_DRIFT_WARNING_SECONDS = 120;

export function NvrTestResult({
  className,
  result,
}: {
  className?: string;
  result: NvrTestConnectionResponse;
}) {
  const t = useTranslations();

  // Xato holatini `NvrErrorBlock` chizadi — bu komponent faqat `ok: true`.
  if (!result.ok) return null;

  const drift = result.clock_drift_seconds;
  const driftIsHigh =
    typeof drift === "number" &&
    Number.isFinite(drift) &&
    Math.abs(drift) >= CLOCK_DRIFT_WARNING_SECONDS;

  return (
    <div
      aria-live="polite"
      className={cn(
        "flex flex-col gap-3 rounded-md border border-border bg-surface-muted p-4",
        className,
      )}
      role="status"
    >
      <div className="flex items-center gap-2">
        <Badge tone="success">{t("cameras.deviceFound")}</Badge>
      </div>

      <dl className="flex flex-col gap-2 text-sm">
        <Row label={t("cameras.model")} value={result.model ?? null} mono />
        <Row label={t("cameras.deviceType")} value={result.device_type ?? null} />
        <Row
          label={t("cameras.channelCount")}
          value={
            typeof result.channels_preview === "number"
              ? t("cameras.channelCountValue", { count: result.channels_preview })
              : null
          }
        />
        <Row
          label={t("cameras.clockDrift")}
          value={
            typeof drift === "number" && Number.isFinite(drift)
              ? t("cameras.clockDriftValue", { seconds: Math.round(drift) })
              : null
          }
          suffix={
            driftIsHigh ? (
              <Badge className="gap-1" tone="warning">
                <AlertTriangle aria-hidden="true" className="size-3" />
                {t("cameras.clockDriftWarning")}
              </Badge>
            ) : null
          }
        />
      </dl>
    </div>
  );
}

/**
 * Bitta qator — yorliq va qiymat.
 *
 * `null` qiymat `—` bo'lib chiqadi, QATOR ESA QOLADI: yo'qolgan qator
 * «bu qurilmada bunday ma'lumot yo'q» degan yolg'on xulosa berardi,
 * holbuki haqiqiy holat «qurilma bu maydonni qaytarmadi».
 */
function Row({
  label,
  mono = false,
  suffix,
  value,
}: {
  label: string;
  mono?: boolean;
  suffix?: React.ReactNode;
  value: string | null;
}) {
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
      <dt className="min-w-32 text-text-muted">{label}</dt>
      {/*
       * `font-mono text-xs` — HUJJATLASHTIRILGAN ISTISNO (UI-SPEC §2.2):
       * model qurilmaning web-interfeysi bilan BELGIMA-BELGI
       * solishtiriladi.
       */}
      <dd className={cn(mono && "font-mono text-xs")}>{value ?? "—"}</dd>
      {suffix}
    </div>
  );
}
