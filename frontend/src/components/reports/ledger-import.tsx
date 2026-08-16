"use client";

import { useId, useRef, useState } from "react";
import { FileUp, Upload } from "lucide-react";
import { useFormatter, useNow, useTimeZone, useTranslations } from "next-intl";
import { parseAsString, useQueryState } from "nuqs";
import { toast } from "sonner";

import { ImportErrors } from "@/components/import/import-errors";
import {
  businessDayIn,
  isValidIsoDay,
  shiftIsoDay,
} from "@/components/snapshots/day-picker";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { formatBusinessDay } from "@/lib/format-day";
import { importErrorsOf } from "@/lib/market-queries";
import { reportErrorView } from "@/lib/report-errors";
import {
  downloadLedgerTemplate,
  useLedgerUpload,
  useThreeWayReport,
} from "@/lib/report-queries";

/*
 * =============================================================================
 * Y-3 — KUN TANLAGICHI VA DAFTAR IMPORTI (§10.2, §10.3, §14.8, DL-6).
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 1. MAKSIMUM KUN — ⛔ KECHA, VA BU `/billing` NIKIDAN FARQ QILADI
 * -----------------------------------------------------------------------
 * `useBillingDay()` ⛔ TO'G'RIDAN-TO'G'RI QAYTA ISHLATILMAYDI: uning
 * maksimumi ⛔ BUGUN. Bu yerda esa maksimum ⛔ KECHA va sabab mahsulot
 * qarori, xulq emas:
 *
 *   • bugungi tizim summasi ⛔ HALI YOPILMAGAN (`daily_charges` D+1
 *     04:10 da tug'iladi);
 *   • daftar ham kun ⛔ OXIRIDA yig'iladi (qog'oz jarayon).
 *
 * ⛔ Ya'ni «bugun» ni solishtirish ⛔ HAR DOIM farq ko'rsatardi va
 *    uchala sinf ham ⛔ SOXTA bo'lardi: ekran har kuni «bozorda 300 ta
 *    nomuvofiqlik» deb yolg'on gapirardi va parallel rejim birinchi
 *    kunidayoq ishonchdan chiqardi.
 *
 * ⚠ SANA ARIFMETIKASI QAYTADAN YOZILMAYDI [M-16]: `businessDayIn`,
 *   `isValidIsoDay`, `shiftIsoDay` 4-fazadan IMPORT qilinadi. Ikkinchi
 *   nusxa bir kun `en-CA` formatlagichi yoki UTC arifmetikasi bo'yicha
 *   ajralib ketardi va ikki ekran BOSHQA-BOSHQA biznes-kunni
 *   ko'rsatardi — buni hech qanday test ko'rmasdi, chunki har nusxa
 *   O'Z testi bilan kelardi.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 2. DL-6 — BIRINCHI DARAJA; ⛔ IKKINCHISI ONGLI RAVISHDA RAD ETILGAN
 * -----------------------------------------------------------------------
 * Shu kun uchun daftar BOR bo'lsa, yangi fayl eskisining ⛔ O'RNINI
 * OLADI (D-17: import ALMASHTIRUVCHI amal, tahrirlovchi emas) — ya'ni
 * tasdiqsiz bu tugmani tasodifan bosish bilan sodir bo'lardi.
 *
 * ⛔ LEKIN MATN YOZIB TASDIQLASH (⛔ IKKINCHI DARAJA, §4.6)
 *    ISHLATILMAYDI: daftar importi ⛔ KUNLIK operatsion amal (parallel
 *    rejimda har kuni) va matn yozdirish uni ⛔ HAR KUNI jazolardi.
 *    Yo'qotish ham cheklangan — o'sha kunning qatorlari va ular
 *    ⛔ QAYTA YUKLANADI. Ikkinchi daraja UI'dan QAYTARIB BO'LMAYDIGAN
 *    amallar uchun (kaskad o'chirish, rastani yopish).
 *
 * ⚠ Rad etilgan darajaning KODDAGI nomi bu izohda LITERAL yozilmaydi —
 *   darvoza xom `grep` bilan o'lchaydi (kodbaza konvensiyasi) va
 *   izohdagi nusxa uni o'ziga qarshi qo'yardi.
 *
 * ⛔ Daftar YO'Q bo'lgan kunda dialog ⛔ UMUMAN OCHILMAYDI: yo'qotiladigan
 *    narsa yo'q va ortiqcha bosish kunlik ishni sekinlashtirardi.
 *
 * -----------------------------------------------------------------------
 * ⛔ 3. IKKINCHI IMPORT OQIMI QURILMAYDI (§10.3)
 * -----------------------------------------------------------------------
 * 2-fazaning quvuri qayta ishlatiladi: shablon -> fayl tanlash ->
 * ⛔ ALL-OR-NOTHING yuborish -> 422 da `import-errors.tsx`. Xato
 * ro'yxatining o'zi ⛔ SHU KOMPONENTDA qayta yozilmaydi — ikkinchi nusxa
 * «hech narsa saqlanmadi» jumlasini yoki guruhlashni bir kun
 * yo'qotardi (D-14).
 *
 * -----------------------------------------------------------------------
 * ⛔ 4. MUVAFFAQIYAT — TOAST, XATO — INLINE (§14.7, §12.2)
 * -----------------------------------------------------------------------
 * Fazada ⛔ AYNAN BITTA toast turi bor va u shu yerda: «Daftar yuklandi:
 * {rows} qator». Xato esa ⛔ HECH QACHON toastda: u g'oyib bo'lardi va
 * foydalanuvchi tugmani qayta-qayta bosardi — har bosish esa yangi
 * import urinishi bo'lardi.
 * =============================================================================
 */

/** `?day=YYYY-MM-DD` — Y-3 ning URL holati (§4.5). */
export const COMPARE_DAY_PARAM = "day";

/**
 * Fayl maydonining ⛔ BARQAROR id'si.
 *
 * ⚠ `useId()` EMAS va bu ATAYIN: bo'sh holat 6 (§14.7) ning amali —
 *   `comparison` blokidan shu maydonga ⛔ FOKUSNI KO'CHIRISH, ya'ni
 *   qo'shni komponent uni nom bilan topa olishi SHART. Havola
 *   yozilmaydi: `components/reports/**` da havola tokenlari ⛔ 0
 *   (G-38(a)) va fokus ko'chirish skrinrider uchun ham to'g'ri javob
 *   (sakrash e'lon qilinadi, sahifa jimgina siljimaydi).
 */
export const LEDGER_FILE_INPUT_ID = "compare-ledger-file";

export type CompareDaySelection = {
  /** Tanlangan biznes-kun — HAR DOIM yaroqli va HAR DOIM <= KECHA. */
  day: string;
  todayIso: string;
  /** ⛔ MAKSIMUM ham, STANDART ham — yuqoridagi 1-band. */
  yesterdayIso: string;
  setDay: (next: string) => void;
};

/**
 * Y-3 ning kun tanlovi — ⛔ YAGONA manba (tanlagich ham, daftar bloki
 * ham, jadval ham shundan o'qiydi).
 *
 * ⚠ QAYTARILADIGAN `day` NORMALLASHTIRILGAN: yaroqsiz qiymat ham,
 *   ⛔ BUGUN ham, kelajakdagi kun ham STANDARTGA (kecha) tushadi.
 *   Iste'molchi hech qachon «bu qiymat ishonchlimi?» degan savolga
 *   tushmaydi va tekshiruv bir joyda qoladi.
 *
 * ⚠ YAROQSIZ `?day=` JIMGINA STANDARTGA TUSHADI, xato ko'rsatilmaydi
 *   [MEROS: 03-UI-SPEC §5.4]: eskirgan xatcho'pdan kelgan adminga «URL
 *   noto'g'ri» deyish hech qanday foydali qadam bermaydi.
 */
export function useCompareDay(): CompareDaySelection {
  const [raw, setRaw] = useQueryState(
    COMPARE_DAY_PARAM,
    parseAsString.withDefault("").withOptions({ history: "push" }),
  );
  const timeZone = useTimeZone() ?? "Asia/Tashkent";
  const now = useNow();

  const todayIso = businessDayIn(timeZone, now);
  const yesterdayIso = shiftIsoDay(todayIso, -1);

  /* ⛔ Chegara `yesterdayIso`, ⛔ `todayIso` EMAS — 1-band. */
  const day = isValidIsoDay(raw) && raw <= yesterdayIso ? raw : yesterdayIso;

  return {
    day,
    todayIso,
    yesterdayIso,
    setDay: (next: string) => {
      /*
       * Standart kun uchun parametr UMUMAN yozilmaydi — toza havola
       * ertasiga O'SHA KUNGI standartni (yangi «kecha» ni) ko'rsatadi
       * va sana havolada qotib qolmaydi.
       */
      void setRaw(next === yesterdayIso ? null : next);
    },
  };
}

/**
 * Kun tanlagichi — ⛔ BOSHQARUV, ro'yxat EMAS.
 *
 * ⛔ Shuning uchun u `data-compare-content` CHIQARMAYDI va sahifaning
 *    mazmun juftligida `CONTENT_EXEMPT` ichida (§10.1).
 */
export function CompareDayPicker() {
  const t = useTranslations();
  const selection = useCompareDay();
  const inputId = useId();

  /*
   * ⚠ E'LON FOYDALANUVCHI URINGANDA TUG'ILADI, sahifa ochilganda emas
   *   [MEROS: `billing/day-picker.tsx`]: doimiy matn har kun
   *   almashtirilganda qayta o'qilardi.
   */
  const [rejected, setRejected] = useState(false);

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2">
        {/* Har boshqaruvda `<label htmlFor>` (§15) — platsholder yorliq emas. */}
        <label className="text-sm text-text-muted" htmlFor={inputId}>
          {t("compare.dayLabel")}
        </label>

        <input
          aria-invalid={rejected}
          className="min-h-11 rounded-md border border-border bg-surface px-3 text-sm text-text focus-visible:border-accent focus-visible:ring-2 focus-visible:ring-accent/25 focus-visible:outline-none"
          id={inputId}
          /* ⛔ KECHA — hook bilan BIRGA, ikki qatlam (§10.2). */
          max={selection.yesterdayIso}
          onChange={(event) => {
            const next = event.target.value;
            if (isValidIsoDay(next) && next <= selection.yesterdayIso) {
              setRejected(false);
              selection.setDay(next);
              return;
            }
            /*
             * ⛔ BUGUN VA KELAJAK QABUL QILINMAYDI: `?day=` yozilmaydi
             *    va maydon `aria-invalid` oladi. Jimgina kechaga
             *    tushirish foydalanuvchiga «qabul qilindi» deb yolg'on
             *    gapirardi.
             */
            setRejected(true);
          }}
          type="date"
          value={selection.day}
        />
      </div>

      {/*
       * ⛔ NOMLANGAN SABAB — rang kanali YO'Q (§13.4). «Bugun tanlanmaydi»
       *   qoidasi foydalanuvchiga urinishdan OLDIN aytiladi.
       */}
      <p className="text-xs text-text-muted">{t("compare.maxDayHint")}</p>

      <p className="sr-only" role="status">
        {rejected ? t("compare.maxDayHint") : ""}
      </p>
    </div>
  );
}

/** ⛔ Noma'lum nosozlikda ham SABAB + QADAM (D-02) — xom istisno HECH QACHON. */
function useUploadFeedback(error: unknown) {
  const rowErrors = importErrorsOf(error);
  const detail =
    error !== null && typeof error === "object" && "detail" in error
      ? String((error as { detail: unknown }).detail)
      : null;

  return { rowErrors, view: rowErrors === null ? reportErrorView(detail) : null };
}

export function LedgerImport() {
  const t = useTranslations();
  const format = useFormatter();

  const { day } = useCompareDay();
  const report = useThreeWayReport(day);
  const upload = useLedgerUpload();

  const [file, setFile] = useState<File | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [templateError, setTemplateError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  /*
   * ⛔ «DAFTAR BORMI?» — SERVERNING JAVOBIDAN (`has_ledger`), qatorlar
   *   sonidan EMAS: bo'sh daftar ham YUKLANGAN daftar (D-17) va uni
   *   almashtirmoqchi bo'lgan admin baribir tasdiq ko'rishi kerak.
   */
  const hasLedger = report.data?.has_ledger === true;

  const { rowErrors, view } = useUploadFeedback(upload.error);

  function send(chosen: File): void {
    upload.mutate(
      { day, file: chosen },
      {
        onSuccess: (result) => {
          /* ⛔ Fazadagi YAGONA toast turi (§14.7). */
          toast.success(t("compare.ledgerLoaded", { rows: result.rows }));
          setFile(null);
          if (inputRef.current !== null) inputRef.current.value = "";
        },
      },
    );
  }

  function onSubmit(): void {
    /* ⛔ `aria-disabled` ning ko'zgusi: bosiladi, lekin so'rov ketmaydi. */
    if (file === null || upload.isPending) return;

    if (hasLedger) {
      setConfirmOpen(true);
      return;
    }
    send(file);
  }

  async function onTemplate(): Promise<void> {
    setTemplateError(null);
    try {
      await downloadLedgerTemplate();
    } catch {
      setTemplateError(t("errors.generic"));
    }
  }

  return (
    /* ⛔ Mazmun atributini blokning O'ZI chiqaradi (§10.1, G-37(b)). */
    <div className="flex flex-col gap-3" data-compare-content="ledger">
      <h2 className="text-lg font-semibold">{t("compare.ledger")}</h2>

      {/*
       * ⛔ HOLAT AVVAL, AMAL KEYIN: admin tugmani bosishdan OLDIN
       *   almashtirish bo'lishini bilishi kerak — dialog kutilmagan
       *   bo'lmasligi shart.
       */}
      <p className="text-sm text-text-muted">
        {hasLedger ? t("compare.ledgerPresent") : t("compare.ledgerMissing")}
      </p>

      <div className="flex flex-col gap-2">
        {/*
         * ⛔ `secondary` — AKSENT EMAS (§13.3): yuklab olish amali
         *   yakunlovchi emas, tayyorgarlik.
         */}
        <Button
          className="self-start"
          onClick={() => void onTemplate()}
          variant="secondary"
        >
          <FileUp aria-hidden="true" />
          {t("compare.ledgerTemplate")}
        </Button>

        {templateError !== null ? (
          <p className="text-sm text-text-muted" role="status">
            {templateError}
          </p>
        ) : null}
      </div>

      <div className="flex flex-col gap-2">
        <label className="text-sm text-text-muted" htmlFor={LEDGER_FILE_INPUT_ID}>
          {t("compare.ledgerFile")}
        </label>

        {/*
         * ⛔ FAYL SERVERDA TEKSHIRILADI (T-02-121): bu yerda parse YO'Q,
         *   klient faqat baytlarni yuboradi. Brauzerdagi tekshiruv
         *   chetlab o'tiladi va xavfsizlik chegarasi bo'la olmaydi.
         */}
        <input
          accept=".xlsx"
          className="min-h-11 rounded-md border border-border bg-surface px-3 py-2 text-sm text-text focus-visible:border-accent focus-visible:ring-2 focus-visible:ring-accent/25 focus-visible:outline-none"
          id={LEDGER_FILE_INPUT_ID}
          onChange={(event) => {
            upload.reset();
            setFile(event.target.files?.[0] ?? null);
          }}
          ref={inputRef}
          type="file"
        />

        <p className="text-xs text-text-muted">{t("compare.ledgerHint")}</p>
      </div>

      {/*
       * ⛔⛔ FAZADAGI YAGONA AKSENT (§13.3): `[Daftarni yuklash]` — Y-3
       *     ning yagona YAKUNLOVCHI amali va uning raqobatchisi yo'q;
       *     qolgan hamma narsa o'qish yoki tayyorgarlik.
       *
       * ⛔ `size="lg"` (44 px, §6.1 istisnosi): bozor admini uni
       *    TELEFONDA ham bosadi — parallel rejim DALA ishi.
       *
       * ⛔ `aria-disabled`, `disabled` EMAS [MEROS: 05-UI-SPEC §13.3]:
       *    o'chirilgan tugma fokusni yo'qotadi va skrinrider
       *    foydalanuvchisi «tugma qayerga ketdi?» holatida qolardi.
       */}
      <Button
        aria-busy={upload.isPending}
        aria-disabled={file === null || upload.isPending}
        className="self-start"
        onClick={onSubmit}
        size="lg"
        variant="default"
      >
        <Upload aria-hidden="true" />
        {t("compare.ledgerUpload")}
      </Button>

      {/* --- 422: qator xatolari — ⛔ 2-fazaning MAVJUD ro'yxati (D-14). --- */}
      {rowErrors !== null ? (
        <ImportErrors
          errorCounts={rowErrors.error_counts}
          errors={rowErrors.errors}
        />
      ) : null}

      {/* --- Qatorlarga aloqasi yo'q xato — ⛔ SABAB + QADAM (§14.9). --- */}
      {upload.isError && rowErrors === null ? (
        <p className="flex flex-col gap-1 text-sm text-text-muted" role="alert">
          <span>{view === null ? t("errors.generic") : t(view.causeKey)}</span>
          {view === null ? null : <span>{t(view.fixKey)}</span>}
        </p>
      ) : null}

      {/*
       * ⛔ DL-6 — FAZADAGI YAGONA DIALOG VA YAGONA DESTRUKTIV TUGMA
       *   (§4.6, §14.8). `confirmVariant` ATAYIN LITERAL yozilgan
       *   (standarti ham shu): darvoza destruktiv variantning EGASI
       *   `ConfirmDialog` ekanini manba matnidan o'lchaydi va standartga
       *   suyanish uni ko'rinmas qilardi.
       */}
      <ConfirmDialog
        cancelLabel={t("common.cancel")}
        confirmLabel={t("compare.ledgerReplaceConfirm")}
        confirmVariant="destructive"
        description={t("compare.ledgerReplaceBody", {
          day: formatBusinessDay(format, day),
        })}
        isBusy={upload.isPending}
        level={1}
        onConfirm={() => {
          setConfirmOpen(false);
          if (file !== null) send(file);
        }}
        onOpenChange={setConfirmOpen}
        open={confirmOpen}
        title={t("compare.ledgerReplaceTitle")}
      />
    </div>
  );
}
