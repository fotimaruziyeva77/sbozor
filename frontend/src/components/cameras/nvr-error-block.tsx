"use client";

import { useEffect, useRef, useState } from "react";
import { AlertCircle, AlertTriangle } from "lucide-react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";
import type { NvrErrorTone } from "@/lib/nvr-errors";
import {
  nvrErrorView,
  pickErrorDetail,
  rawDetailText,
} from "@/lib/nvr-errors";

/*
 * =============================================================================
 * XATO BLOKI — 3-fazaning eng qimmatli komponenti (D-02, SC#3, UI-SPEC §7).
 *
 * D-02: *«Xato hech qachon "ulanmadi" degan quruq xabar bo'lmaydi — sababi
 * va tuzatish yo'li ko'rsatiladi.»*
 *
 * MEXANIZM (UI-SPEC §7.1): ikkalasi ham YORLIQLANGAN blok. Yorliq
 * `text-xs font-semibold tracking-wide` (Meta), mazmun Body 14/400.
 * Ikkalasi BIR XIL tipografik og'irlikda — birortasi ikkinchisining
 * «izohi» bo'lib ko'rinmaydi.
 *
 * RAD ETILGAN MUQOBILLAR (uchalasi ham UI-SPEC §7.1 da):
 *   * tuzatishni QALIN qilish — ikkita qalin matn bir-biri bilan
 *     raqobatlashadi va ierarxiya butunlay yo'qoladi;
 *   * tuzatishni sabab jumlasining DUMIGA ulash («… — NTP xizmatini
 *     yoqing») — bu AYNAN D-02 taqiqlagan shakl: tuzatish ikkinchi
 *     darajali bo'lib qoladi va uzun matnda umuman o'qilmaydi;
 *   * FAQAT tuzatishni ko'rsatish — admin nimani tuzatayotganini
 *     bilmasa, u tasodifan boshqa narsani o'zgartiradi.
 *
 * ⚠ RETRY AFFORDANSI `retrySafe === false` BO'LGANDA RENDER QILINMAYDI —
 *   u YO'Q, yashirilgan emas. Qoida bitta jumlada: *tugma faqat qayta
 *   urinish HOLATNI O'ZGARTIRMAYDIGAN hollarda ko'rinadi; autentifikatsiya
 *   urinishi esa qurilmadagi qulflash hisoblagichini OSHIRADI.*
 *
 *   Raqam bilan (03-05 o'lchovi): retry predikatiga bitta HTTP xato sinfi
 *   qo'shilgan sabotaj urinishlar sonini 0 dan 5 ga — Hikvision ning
 *   qulflash chegarasiga — chiqargan edi. Ya'ni bitta ortiqcha affordans
 *   NVR hisobini 30 daqiqaga qulflaydi va undan keyin TO'G'RI parol ham
 *   ishlamaydi. Backend qayta urinishni rad etadi; UI uni TAKLIF ham
 *   qilmasligi kerak.
 *
 * ⚠ MASKALASH CHEGARASI (UI-SPEC §7.4 [TALAB]): `error_detail` ning
 *   `mask_sensitive` dan o'tgani BACKENDNING kafolati (`NvrError`
 *   konstruktori + `nvr_repo.finish_run()`). UI MASKALAMAYDI va
 *   TEKSHIRMAYDI — ikkinchi maskalash qatlami «backend nima yozsa ham
 *   xavfsiz» degan YOLG'ON xotirjamlik berardi. Bu yerdagi allowlist
 *   (`pickErrorDetail`) boshqa vazifani bajaradi: noma'lum kalit
 *   ekranga tarjimasiz texnik satr bo'lib CHIQMAYDI.
 *
 * ⚠ XOM MATN HTML SIFATIDA HECH QACHON chizilmaydi (T-03-64): mazmun
 *   JSX bolasi bo'lib, `whitespace-pre-wrap break-all` bilan chiqadi.
 *   `frontend/src/components/cameras/` daraxtida xavfli render API'si
 *   UMUMAN yo'q va bu grep bilan tekshiriladi — shu sababdan uning nomi
 *   bu izohda literal sifatida ham yozilmaydi (kodbaza konvensiyasi).
 * =============================================================================
 */

/** Ma'lumot yetishmaganda ICU platsholderiga tushadigan qiymat. */
const EM_DASH = "—";

/**
 * `tone` -> konteyner uslubi (UI-SPEC §7.2).
 *
 * ⚠ SARIQ MATN RANGI EMAS: `--color-warning` oq fonda 2.03:1 beradi.
 *   Sariq tintdagi matn `text-text` bo'ladi (o'lchangan 15.63:1) va bu
 *   taqiq 2-fazadan meros (02-UI-SPEC §4.2).
 */
const TONE_CLASS: Record<NvrErrorTone, string> = {
  danger: "bg-danger/10 text-danger-text",
  warning: "bg-warning/20 text-text",
};

const TONE_ICON: Record<NvrErrorTone, typeof AlertCircle> = {
  danger: AlertCircle,
  warning: AlertTriangle,
};

export type NvrErrorBlockProps = {
  /**
   * Blok montaj bo'lganda (yoki kod o'zgarganda) fokusni O'ZIGA oladi.
   *
   * ⚠ STANDART HOLDA `false` va bu ataylab (UI-SPEC §7.6): forma
   *   yuborilib xato kelganda fokus blokka ko'chadi, LEKIN kashfiyot
   *   jobi 60 soniyadan keyin `failed` bilan qaytganda fokus
   *   KO'CHMAYDI — foydalanuvchi allaqachon boshqa ish qilayotgan
   *   bo'lishi mumkin. Bitta komponent, ikki xil chaqiruvchi.
   */
  autoFocus?: boolean;
  className?: string;
  /** Javobdagi `error_code`; noma'lum qiymat `errors.generic` ga tushadi. */
  code: string | null | undefined;
  /** Javobdagi `error_detail` — faqat allowlist'dagi kalitlar o'qiladi. */
  detail?: Record<string, unknown> | null;
  /**
   * Qayta urinish amali.
   *
   * Berilgan bo'lsa ham, kod `retrySafe === false` bo'lsa tugma
   * RENDER QILINMAYDI.
   */
  onRetry?: () => void;
};

export function NvrErrorBlock({
  autoFocus = false,
  className,
  code,
  detail,
  onRetry,
}: NvrErrorBlockProps) {
  const t = useTranslations();
  const view = nvrErrorView(code);
  const containerRef = useRef<HTMLDivElement | null>(null);

  /*
   * Fokus EFFEKTDA, render paytida emas: `code` o'zgarganda blok qayta
   * fokuslanadi (ketma-ket ikki xato), bir xil kod takrorlanganda esa
   * mazmun ham o'zgarmagani uchun fokus joyida qoladi.
   */
  useEffect(() => {
    if (autoFocus) containerRef.current?.focus();
  }, [autoFocus, code]);

  const countdown = useUnlockCountdown(detail);

  /*
   * NOMA'LUM KOD (UI-SPEC §7.3 oxirgi qatori).
   *
   * ⚠ YORLIQLANGAN IKKI BLOK BU YERDA CHIZILMAYDI. Sabab: yorliq
   *   TUZILISHNI va'da qiladi, bizda esa uning yarmi yo'q — «SABAB»
   *   yorlig'i ostida umumiy jumla turib, «NIMA QILISH KERAK» yorlig'i
   *   bo'sh qolsa, u halol «bilmayman» emas, KAMCHILIK bo'lib ko'rinardi.
   *
   * ⚠ `error_detail` KO'RSATILMAYDI (T-02-99 / T-03-66): xom `detail`,
   *   stack izi yoki SQL matni foydalanuvchiga HECH QACHON chiqmaydi.
   *   Noma'lum kodda o'sha tanani ekranga chiqarish ichki tafsilotni
   *   sizdirishning eng oson yo'li bo'lardi.
   */
  if (view === null) {
    return (
      <div
        className={cn(
          "flex gap-3 rounded-md p-4 outline-none",
          TONE_CLASS.danger,
          className,
        )}
        ref={containerRef}
        role="alert"
        tabIndex={-1}
      >
        <AlertCircle aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
        <div className="flex min-w-0 flex-1 flex-col gap-3">
          <p className="text-sm leading-normal">{t("errors.generic")}</p>
          {onRetry ? (
            <div>
              <Button onClick={onRetry} size="sm" variant="secondary">
                {t("cameras.retryCheck")}
              </Button>
            </div>
          ) : null}
        </div>
      </div>
    );
  }

  const Icon = TONE_ICON[view.tone];
  const values = icuValues(detail, countdown);
  const raw = rawDetailText(detail);

  return (
    <div
      className={cn(
        "flex gap-3 rounded-md p-4 outline-none",
        TONE_CLASS[view.tone],
        className,
      )}
      data-error-code={view.code}
      ref={containerRef}
      role="alert"
      tabIndex={-1}
    >
      <Icon aria-hidden="true" className="mt-0.5 size-4 shrink-0" />

      <div className="flex min-w-0 flex-1 flex-col gap-3">
        {/*
         * `<dl>` — yorliq va mazmun AYNAN juftlik, ya'ni skrinrider ham
         * ularni juftlik bo'lib o'qiydi. Ikkala `<dt>` bir xil sinfda,
         * ikkala `<dd>` ham — teng og'irlik razmetkadan ham ko'rinadi.
         */}
        <dl className="flex flex-col gap-3">
          <div>
            <dt className="text-xs font-semibold tracking-wide">
              {t("cameras.errorCauseLabel")}
            </dt>
            <dd className="text-sm leading-normal">
              {t(view.causeKey, values)}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-semibold tracking-wide">
              {t("cameras.errorFixLabel")}
            </dt>
            <dd className="text-sm leading-normal">{t(view.fixKey, values)}</dd>
          </div>
        </dl>

        {view.retrySafe && onRetry ? (
          <div>
            <Button onClick={onRetry} size="sm" variant="secondary">
              {t("cameras.retryCheck")}
            </Button>
          </div>
        ) : null}

        {/*
         * `<details>` FAQAT `raw` bo'lganda (UI-SPEC §7.4): bo'sh
         * ochiladigan blok — shovqin, va u har xato ostida turib
         * «yana nimadir bor» degan yolg'on va'da berardi.
         */}
        {raw !== null ? (
          <details className="text-xs">
            <summary className="cursor-pointer font-semibold select-none">
              {t("cameras.errorDetails")}
            </summary>
            <p className="mt-2 font-mono text-xs break-all whitespace-pre-wrap">
              {raw}
            </p>
          </details>
        ) : null}
      </div>
    </div>
  );
}

/* --- ICU qiymatlari -------------------------------------------------------- */

/**
 * Matn kalitlaridagi TO'RTTA platsholder — HAR DOIM to'liq uzatiladi.
 *
 * ⚠ HAMMASI BIR VAQTDA BERILADI va bu ataylab: `nvr_clock_drift` da
 *   `{minutes}`, `nvr_account_locked` da `{time}`, `device_not_supported`
 *   da `{model}`, `channel_offline` da `{channel}` bor. Kodga qarab
 *   tanlab uzatish «bitta kod uchun platsholder unutildi -> ICU
 *   xatosi -> ekranda bo'sh blok» yo'lini ochiq qoldirardi; ortiqcha
 *   qiymatni ICU jimgina e'tiborsiz qoldiradi.
 *
 * Qiymat yetishmasa `—` tushadi: raqamning O'RNI ko'rinib turadi va
 * matn buzilmaydi.
 */
function icuValues(
  detail: Record<string, unknown> | null | undefined,
  countdown: string | null,
): Record<string, string | number> {
  const picked = pickErrorDetail(detail);

  return {
    minutes: driftMinutes(picked.drift_seconds) ?? EM_DASH,
    time: countdown ?? EM_DASH,
    model: asText(picked.model) ?? EM_DASH,
    channel: asText(picked.channel_no) ?? asText(picked.channel_name) ?? EM_DASH,
  };
}

function asText(value: unknown): string | null {
  if (typeof value === "string" && value.length > 0) return value;
  if (typeof value === "number" && Number.isFinite(value)) return String(value);
  return null;
}

/**
 * `drift_seconds` -> daqiqa (matn «{minutes} daqiqa farq qilyapti» deydi).
 *
 * Modul bo'yicha: farq ikkala yo'nalishda ham bir xil muammo, ishora
 * esa adminga hech narsa bermaydi. `Math.round` — 90 soniya «2 daqiqa»,
 * 30 soniya «1 daqiqa» bo'ladi va nol chiqmaydi (nol farq umuman xato
 * tug'dirmaydi).
 */
function driftMinutes(value: unknown): number | null {
  if (typeof value !== "number" || !Number.isFinite(value)) return null;
  return Math.max(1, Math.round(Math.abs(value) / 60));
}

/* --- `nvr_account_locked` taymeri ------------------------------------------ */

/**
 * `error_detail.unlock_at` gacha qolgan vaqt, `mm:ss` (UI-SPEC §7.4).
 *
 * ⚠ `aria-live` YO'Q va bu ataylab: har soniyada yangilanadigan qiymat
 *   jonli hudud bo'lsa skrinrider foydalanuvchisi boshqa hech narsani
 *   eshitmasdi. Taymer VIZUAL ko'rsatkich; qulfning o'zi va uni ochish
 *   yo'li matnda yozilgan.
 *
 * ⚠ `Date.now()` FAQAT effektda chaqiriladi (`react-hooks/purity`):
 *   render paytidagi chaqiruv React Compiler qoidasini buzardi va
 *   03-08 da aynan shu qoida poll shaklini qayta loyihalashga majbur
 *   qilgan edi.
 */
function useUnlockCountdown(
  detail: Record<string, unknown> | null | undefined,
): string | null {
  const unlockAt = pickErrorDetail(detail).unlock_at;
  const target = typeof unlockAt === "string" ? Date.parse(unlockAt) : Number.NaN;
  const hasTarget = Number.isFinite(target);

  /*
   * Soat — TASHQI TIZIM, ya'ni holat effekt TANASIDA emas, intervalning
   * CALLBACK ida yangilanadi (`react-hooks/set-state-in-effect`).
   * Boshlang'ich qiymat esa `useState` ning dangasa initsializatorida
   * bir marta o'qiladi — shu bilan birinchi kadrda ham to'g'ri raqam
   * turadi va «—» dan sakrash bo'lmaydi.
   */
  const [nowMs, setNowMs] = useState(() => Date.now());

  useEffect(() => {
    if (!hasTarget) return;
    const id = setInterval(() => setNowMs(Date.now()), 1000);
    return () => clearInterval(id);
  }, [hasTarget]);

  if (!hasTarget) return null;
  return formatMmSs(Math.max(0, target - nowMs));
}

/** Sof funksiya — testda soatni ushlab turmasdan tekshiriladi. */
export function formatMmSs(milliseconds: number): string {
  const total = Math.max(0, Math.floor(milliseconds / 1000));
  const minutes = Math.floor(total / 60);
  const seconds = total % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}
