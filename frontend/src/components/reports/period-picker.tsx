"use client";

import { useId } from "react";
import { useNow, useTimeZone, useTranslations } from "next-intl";
import { parseAsString, useQueryStates } from "nuqs";

import {
  businessDayIn,
  isValidIsoDay,
  shiftIsoDay,
} from "@/components/snapshots/day-picker";
import { EmptyState } from "@/components/ui/empty-state";
import { Select } from "@/components/ui/select";
import { PERIOD_PRESETS, type PeriodPreset } from "@/lib/api-types";

/*
 * =============================================================================
 * HISOBOT DAVRI — ⛔ MAKSIMUM KECHA, STANDART OXIRGI 30 KUN (§4.4, §4.5).
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ MAKSIMUM KECHA — BU XULQ EMAS, DOMEN QOIDASI (§1.2 qoida 1).
 * -----------------------------------------------------------------------
 * `daily_charges` ⛔ D+1 04:10 da tug'iladi. Ya'ni BUGUNGI kunni
 * qamragan hisobot ⛔ KAM KO'RSATILGAN bo'ladi — va u ekranda qolib
 * ketmaydi: direktor uni `.xlsx` bo'lib yuklab oladi, chop etadi va
 * ⛔ TARQATADI. Ekranda tuzatiladigan xato faylda AYLANIB YURADI
 * (T-08-37).
 *
 * ⛔ Shu sababdan chegara IKKI QATLAMDA (4 va 5-fazadagi `day-picker`
 *    naqshi): `max` atributi **va** URL/`onChange` filtri. `max` yolg'iz
 *    YETARLI EMAS — u brauzer maslahati va DevTools bilan olib
 *    tashlanadi. ⚠ HAQIQIY chegara esa SERVERDA (`_report_period`,
 *    08-07): bu qatlam foydalanuvchini bajarilmas so'rovdan QAYTARADI,
 *    darvoza emas (02-15 qoidasi).
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ STANDART — OXIRGI 30 KUN, VA SABAB MEXANIK, DID EMAS.
 * -----------------------------------------------------------------------
 * Server aniqlik hisoboti uchun `ACCURACY_WINDOW_DAYS = 30` ni STANDART
 * qilgan [KOD: `occupancy.py:174`]. Standartlar MOS KELGANDA `/reports`
 * va `/occupancy` dagi aniqlik raqami ⛔ AYNAN TENG bo'ladi va «ikki xil
 * haqiqat» TUG'ILMAYDI. Boshqa standart (masalan «joriy oy») ikki
 * ekranda ikki xil son berardi va uni ⛔ HECH QANDAY TEST KO'RMASDI —
 * ikkalasi ham arifmetik jihatdan to'g'ri bo'lardi.
 *
 * -----------------------------------------------------------------------
 * ⚠ SOF SANA YORDAMCHILARI 4-FAZADAN IMPORT QILINADI, NUSXA OLINMAYDI.
 * -----------------------------------------------------------------------
 * `businessDayIn` / `isValidIsoDay` / `shiftIsoDay` —
 * `components/snapshots/day-picker.tsx` da. Ikkinchi `en-CA` formatlagichi
 * yoki ikkinchi UTC arifmetikasi bir kun ajralib ketardi va ikki ekran
 * BOSHQA-BOSHQA biznes-kunni ko'rsatardi (M-16). Buni hech qanday test
 * ko'rmasdi, chunki har nusxa O'Z testi bilan kelardi.
 *
 * -----------------------------------------------------------------------
 * ⛔ NEGA BU KOMPONENT `ui/` GA KO'TARILMAYDI.
 * -----------------------------------------------------------------------
 * `ui/` dagi «umumiy oraliq tanlagichi» ertaga `maxDate` PROPINI olardi —
 * va o'sha lahzada «maksimum kecha» chaqiruvchining tanloviga aylanardi.
 * Bu yerdagi butun mazmun esa aynan shu chegaraning ⛔ MUZOKARASIZLIGI.
 *
 * ⚠ PRESET URL'DA SAQLANMAYDI (§4.5): u `from`/`to` dan TESKARI
 *   hisoblanadi. Ikkalasini yozish ikkinchi haqiqat manbai bo'lardi va
 *   ular bir kun ajralib ketardi («`thisMonth` yozilgan, oraliq esa
 *   avgust» holati).
 * =============================================================================
 */

/** `?from=YYYY-MM-DD` — hisobot davrining quyi chegarasi (§4.5). */
export const PERIOD_FROM_PARAM = "from";
/** `?to=YYYY-MM-DD` — hisobot davrining yuqori chegarasi (§4.5). */
export const PERIOD_TO_PARAM = "to";

/**
 * Standart davrning uzunligi — ⛔ 30 KUN.
 *
 * ⛔ Qiymat serverning `ACCURACY_WINDOW_DAYS` i bilan AYNAN teng bo'lishi
 *    SHART (yuqoridagi blok). O'zgartirilsa, `/reports` va `/occupancy`
 *    standart holatda IKKI XIL aniqlik foizini ko'rsatardi.
 */
export const DEFAULT_PERIOD_DAYS = 30;

/** Oyning birinchi kuni — `YYYY-MM-01`. */
function monthStartIso(iso: string): string {
  return `${iso.slice(0, 7)}-01`;
}

/**
 * Presetning oralig'i — reyestrdagi HAR a'zo uchun bir joyda.
 *
 * ⛔ `custom` uchun `null`: u PRESET EMAS, presetning YO'QLIGINING nomi
 *    (§4.4). Uni tanlab bo'lmaydi — u faqat teskari hisobdan CHIQADI.
 *
 * ⚠ `thisMonth` OYNING 1-KUNIDA `from > to` beradi va bu ⛔ TO'G'RI:
 *   joriy oyda hali yopilgan kun YO'Q. Bu holat `lastMonth` ga
 *   TUSHIRILMAYDI (§4.4) — jimgina boshqa oyni ko'rsatish direktorga
 *   NOTO'G'RI OYNING raqamini berardi.
 */
function presetRange(
  preset: PeriodPreset,
  todayIso: string,
): { from: string; to: string } | null {
  const maxDayIso = shiftIsoDay(todayIso, -1);

  switch (preset) {
    case "last30":
      return { from: shiftIsoDay(maxDayIso, -(DEFAULT_PERIOD_DAYS - 1)), to: maxDayIso };
    case "yesterday":
      return { from: maxDayIso, to: maxDayIso };
    case "thisMonth":
      return { from: monthStartIso(todayIso), to: maxDayIso };
    case "lastMonth": {
      const lastMonthEnd = shiftIsoDay(monthStartIso(todayIso), -1);
      return { from: monthStartIso(lastMonthEnd), to: lastMonthEnd };
    }
    default:
      return null;
  }
}

/**
 * Oraliq -> preset (TESKARI hisob, §4.5).
 *
 * ⛔ Reyestrdan ITERATSIYA qilinadi — qo'lda yozilgan `if` zanjiri
 *    `PERIOD_PRESETS` ga oltinchi a'zo qo'shilganda JIMGINA ortda
 *    qolardi.
 */
export function presetOf(
  from: string,
  to: string,
  todayIso: string,
): PeriodPreset {
  for (const preset of PERIOD_PRESETS) {
    const range = presetRange(preset, todayIso);
    if (range !== null && range.from === from && range.to === to) return preset;
  }
  return "custom";
}

export type ReportPeriodSelection = {
  /** ⛔ HAR DOIM normallashtirilgan — iste'molchi qayta tekshirmaydi. */
  from: string;
  to: string;
  /** `from`/`to` dan TESKARI hisoblangan (§4.5). */
  preset: PeriodPreset;
  /**
   * ⛔ `from > to` — joriy oyda hali yopilgan kun YO'Q (§4.4).
   *
   * ⚠ ISTE'MOLCHI BUNI HURMAT QILISHI SHART: so'rov `enabled: !isEmpty`
   *   bilan to'siladi, aks holda server bo'sh oraliq uchun `400
   *   range_invalid` qaytarardi va ekranda MAHSULOT QARORI o'rniga
   *   XATO ko'rinardi.
   */
  isEmpty: boolean;
  todayIso: string;
  /** ⛔ Yuqori chegara — KECHA. `max` atributi ham, filtr ham shundan. */
  maxDayIso: string;
  setPreset: (next: PeriodPreset) => void;
  setFrom: (next: string) => void;
  setTo: (next: string) => void;
};

/**
 * URL'dan kelgan davrni NORMALLASHTIRADI.
 *
 * ⛔ QOIDALAR TARTIBI MA'NOLI:
 *   1. Yaroqsiz shakl -> standart (jimgina, xato KO'RSATILMAYDI:
 *      eskirgan xatcho'pdan kelgan direktorga «URL noto'g'ri» deyish
 *      hech qanday foydali qadam bermaydi [MEROS: 03-UI-SPEC §5.4]).
 *   2. ⛔ PRESET ORALIG'I AYNAN MOS KELSA — QABUL, hatto `from > to`
 *      bo'lsa ham. Bu YAGONA yo'l, unda teskari oraliq qonuniy:
 *      `thisMonth` oyning 1-kunida. Bu bandsiz o'sha nomlangan holat
 *      sahifa yangilanishida JIMGINA yo'qolardi va URL ulashib
 *      bo'lmasdi.
 *   3. Teskari oraliq -> standart. ⛔ ALMASHTIRILMAYDI: avtomatik
 *      almashtirish foydalanuvchi SO'RAMAGAN davrni ko'rsatardi va u
 *      buni sezmasdi.
 *   4. `to > kecha` -> standart. Bu `max` atributining IKKINCHI qatlami.
 */
function normalizePeriod(
  rawFrom: string,
  rawTo: string,
  todayIso: string,
): { from: string; to: string } {
  const fallback = presetRange("last30", todayIso) as {
    from: string;
    to: string;
  };

  if (!isValidIsoDay(rawFrom) || !isValidIsoDay(rawTo)) return fallback;
  if (presetOf(rawFrom, rawTo, todayIso) !== "custom") {
    return { from: rawFrom, to: rawTo };
  }
  if (rawFrom > rawTo) return fallback;
  if (rawTo > shiftIsoDay(todayIso, -1)) return fallback;

  return { from: rawFrom, to: rawTo };
}

/**
 * Davr tanlovi — YAGONA manba (tanlagich ham, bloklar ham shundan).
 *
 * ⚠ HOOK ALOHIDA EKSPORT QILINADI: sahifa oralig'ni so'rov hooklariga
 *   uzatishi kerak, lekin tanlagichning O'ZI sahifa tepasida bir marta
 *   chiziladi. Ikkinchi nusxa chizilsa, ikkalasi bir xil URL'dan
 *   o'qigani uchun ajralib keta olmaydi — lekin bo'shliq ikki marta
 *   ishlatilardi.
 */
export function useReportPeriod(): ReportPeriodSelection {
  const [raw, setRaw] = useQueryStates(
    {
      [PERIOD_FROM_PARAM]: parseAsString.withDefault(""),
      [PERIOD_TO_PARAM]: parseAsString.withDefault(""),
    },
    { history: "push" },
  );

  const timeZone = useTimeZone() ?? "Asia/Tashkent";
  const now = useNow();

  const todayIso = businessDayIn(timeZone, now);
  const maxDayIso = shiftIsoDay(todayIso, -1);
  const fallback = presetRange("last30", todayIso) as {
    from: string;
    to: string;
  };

  const period = normalizePeriod(raw.from, raw.to, todayIso);

  function write(next: { from: string; to: string }): void {
    /*
     * ⛔ STANDART DAVR UCHUN PARAMETR UMUMAN YOZILMAYDI [MEROS:
     *   `billing/day-picker.tsx:105-112`]. Toza havola ERTASIGA ham
     *   o'sha kungi standartni (yangi «oxirgi 30 kun» ni) ko'rsatadi va
     *   sana havolada QOTIB QOLMAYDI — ulashilgan «oxirgi oy» havolasi
     *   bir haftadan keyin ham oxirgi oyni beradi.
     */
    const isDefault = next.from === fallback.from && next.to === fallback.to;
    void setRaw(
      isDefault
        ? { [PERIOD_FROM_PARAM]: null, [PERIOD_TO_PARAM]: null }
        : { [PERIOD_FROM_PARAM]: next.from, [PERIOD_TO_PARAM]: next.to },
    );
  }

  return {
    from: period.from,
    to: period.to,
    preset: presetOf(period.from, period.to, todayIso),
    isEmpty: period.from > period.to,
    todayIso,
    maxDayIso,
    setPreset: (next: PeriodPreset) => {
      const range = presetRange(next, todayIso);
      /* ⛔ `custom` TANLANMAYDI — u hosila (§4.5). */
      if (range !== null) write(range);
    },
    setFrom: (next: string) => {
      /* ⛔ Ikkinchi qatlam: `max` atributi DevTools bilan olinadi. */
      if (isValidIsoDay(next) && next <= maxDayIso) {
        write({ from: next, to: period.to });
      }
    },
    setTo: (next: string) => {
      if (isValidIsoDay(next) && next <= maxDayIso) {
        write({ from: period.from, to: next });
      }
    },
  };
}

/**
 * Davr tanlagichi — preset `<select>` + ikki `<input type="date">`.
 *
 * ⛔ BOSHQARUV, ro'yxat EMAS: shuning uchun u `data-report-content`
 *    CHIQARMAYDI va G-37(c) da `CONTENT_EXEMPT` ichida
 *    (`billing/day-picker.tsx:118-121` naqshi).
 *
 * ⚠ SANA TANLAGICHI UCHUN KUTUBXONA QO'SHILMAYDI: native
 *   `<input type="date">` OS ning O'Z tanlagichini ochadi (§15) — o'z
 *   locale'i, o'z klaviatura qo'llab-quvvatlashi bilan. Yangi npm paketi
 *   esa ta'minot zanjiri yuzasini kengaytirardi (T-08-SC).
 */
export function PeriodPicker() {
  const t = useTranslations();
  const selection = useReportPeriod();
  const presetId = useId();
  const fromId = useId();
  const toId = useId();

  return (
    <fieldset className="flex flex-col gap-2">
      {/* §15: davr guruhi uchun `fieldset`/`legend` — uch boshqaruv bitta savol. */}
      <legend className="text-sm font-semibold text-text">
        {t("reports.periodLabel")}
      </legend>

      {/* §6.1: `gap-2`, o'ralganda `gap-y-3`. */}
      <div className="flex flex-wrap items-end gap-2 gap-y-3">
        <div className="flex flex-col gap-1">
          {/* §14.1: har boshqaruvda `<label htmlFor>` — platsholder yorliq emas. */}
          <label className="sr-only" htmlFor={presetId}>
            {t("reports.presetLabel")}
          </label>
          <Select
            className="w-auto"
            id={presetId}
            onChange={(event) =>
              selection.setPreset(event.target.value as PeriodPreset)
            }
            value={selection.preset}
          >
            {/*
             * ⛔ REYESTRDAN ITERATSIYA, qo'lda ro'yxat YO'Q (§16.2): qo'lda
             *    yozilgan ro'yxat `PERIOD_PRESETS` kengayganda jimgina
             *    ortda qolardi va yangi preset TANLANMAS bo'lib qolardi.
             */}
            {PERIOD_PRESETS.map((preset) => (
              <option key={preset} value={preset}>
                {t(`reports.preset.${preset}`)}
              </option>
            ))}
          </Select>
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-sm text-text-muted" htmlFor={fromId}>
            {t("reports.periodFrom")}
          </label>
          <input
            className="h-10 rounded-sm border border-border-ui bg-surface px-3 text-sm text-text outline-none transition-colors focus-visible:border-accent focus-visible:ring-2 focus-visible:ring-accent/25"
            id={fromId}
            /* ⛔ Yuqori chegara IKKALA maydonda: `from` ham kelajakda bo'lolmaydi. */
            max={selection.maxDayIso}
            onChange={(event) => selection.setFrom(event.target.value)}
            type="date"
            value={selection.from}
          />
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-sm text-text-muted" htmlFor={toId}>
            {t("reports.periodTo")}
          </label>
          <input
            className="h-10 rounded-sm border border-border-ui bg-surface px-3 text-sm text-text outline-none transition-colors focus-visible:border-accent focus-visible:ring-2 focus-visible:ring-accent/25"
            id={toId}
            max={selection.maxDayIso}
            onChange={(event) => selection.setTo(event.target.value)}
            type="date"
            value={selection.to}
          />
        </div>
      </div>

      {selection.isEmpty ? (
        /*
         * ⛔⛔ BO'SH HOLAT 5 (§14.7) — NOMLANGAN HOLAT, JIM SILJISH EMAS.
         *
         * `thisMonth` oyning 1-kunida `from > to` beradi: joriy oyda hali
         * YOPILGAN KUN YO'Q. Bu holatda tanlagich ⛔ `lastMonth` ga
         * TUSHMAYDI — jimgina boshqa oyni ko'rsatish direktorga NOTO'G'RI
         * OYNING raqamini berardi va u buni SEZMASDI (§4.4).
         *
         * ⛔ DAVR JUMLASI (`reports.periodShown`) BU YERDA CHIZILMAYDI:
         *    «2026-09-01 — 2026-08-31» o'qilishi mumkin bo'lgan davr
         *    bo'lib ko'rinardi, holbuki u BO'SH to'plam. G-38(d) shu
         *    yo'qlikni o'lchaydi.
         *
         * ⚠ Tavsif AYNAN `reports.maxDayHint`: sabab bitta va u ikki
         *   marta boshqacha yozilsa, ikki jumla bir kun ajralib ketardi.
         *   Shuning uchun chegara matni bu holatda TAKRORLANMAYDI — u shu
         *   bloknining ICHIDA turadi.
         */
        <EmptyState
          className="py-6"
          description={t("reports.maxDayHint")}
          title={t("reports.emptyMonth")}
        />
      ) : (
        <>
          {/*
           * ⚠ CHEGARA MATNI TANLAGICH YONIDA: `max` atributi bloklaydi,
           *   lekin SABABINI aytmaydi — foydalanuvchi «nega bugunni
           *   tanlay olmayapman?» holatida qolardi.
           */}
          <p className="text-sm text-text-muted">{t("reports.maxDayHint")}</p>

          <p className="text-sm text-text-muted">
            {t("reports.periodShown", {
              from: selection.from,
              to: selection.to,
            })}
          </p>
        </>
      )}
    </fieldset>
  );
}
