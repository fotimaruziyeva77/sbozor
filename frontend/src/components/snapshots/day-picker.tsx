"use client";

import { useId, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useNow, useTimeZone, useTranslations } from "next-intl";
import { parseAsBoolean, parseAsString, useQueryState } from "nuqs";

import { Button } from "@/components/ui/button";

/*
 * =============================================================================
 * ZONA C — KUN TANLAGICHI (§6.3) va sahifaning URL HOLATI.
 *
 * ⛔ KELAJAKDAGI KUN TANLANMAYDI. Ertangi reja hali materializatsiya
 *    qilinmagan (u kunning birinchi tikida tug'iladi, D-05), ya'ni
 *    kelajakdagi kunning jurnali BO'SH bo'lardi — va bo'sh jurnal
 *    adminga «bugun hech narsa olinmadi» degan YOLG'ON signal berardi.
 *    Backend ham buni 422 bilan rad etadi (04-09), ya'ni bu ikkinchi
 *    qatlam emas, birinchi qatlamning KO'ZGUSI.
 *
 * ⚠ YAROQSIZ `?day=` JIMGINA BUGUNGA TUSHADI va xato KO'RSATILMAYDI
 *   [MEROS: 03-UI-SPEC §5.4]. Havolani qo'lda tahrirlagan yoki eskirgan
 *   xatcho'pdan kelgan foydalanuvchiga «URL noto'g'ri» deyish hech
 *   qanday foydali qadam bermaydi: u baribir bugungi kunni ko'rmoqchi.
 *
 * ⚠ URL HOLATI SHU MODULDA BIR JOYDA (`stalls/stall-filters.tsx` naqshi):
 *   `?day=` va `?issues=` ikkalasi ham shu yerdan o'qiladi, ya'ni panel
 *   va jurnal hech qachon ajralib qola olmaydi. ⛔ DIALOG holati URL'da
 *   EMAS (§4.4) — u sahifa holati.
 *
 * ⚠ `history: "push"` — orqaga tugmasi KUN bo'yicha ishlaydi. Bu §6.3
 *   ning ochiq talabi: admin uch kunni ko'rib chiqib, orqaga bosganda
 *   sahifadan chiqib ketmasligi kerak.
 *
 * ⚠ SANA `font-mono` EMAS (§8.3): u o'qiladigan MATN, belgima-belgi
 *   solishtiriladigan texnik qiymat emas. Vaqt (`06:30`) esa aksincha —
 *   u `font-mono` bo'ladi va u matritsada yashaydi.
 * =============================================================================
 */

/** `?day=` — biznes-kun, ISO shaklda (§13.4: HECH QACHON mahalliylashtirilmaydi). */
export const DAY_PARAM = "day";
/** `?issues=1` — jurnalda faqat muammoli qatorlar (Z-10). */
export const ISSUES_PARAM = "issues";

const ISO_DAY = /^\d{4}-\d{2}-\d{2}$/u;

/**
 * `Date` -> `YYYY-MM-DD` KO'RSATISH mintaqasida
 * (`schedule-dialog.tsx:368` va `tariff-dialog.tsx:81` naqshi).
 *
 * `en-CA` ATAYIN: uning qisqa sana formati ISO-8601 bilan bir xil, ya'ni
 * natija `max` atributi uchun ham, LEKSIK solishtirish uchun ham yaroqli.
 * Brauzerning O'Z mintaqasiga tushib qolish TAQIQ — Toshkentdan boshqa
 * mintaqadagi foydalanuvchida biznes-kun bir kunga siljirdi.
 */
export function businessDayIn(timeZone: string, value: Date): string {
  return new Intl.DateTimeFormat("en-CA", {
    day: "2-digit",
    month: "2-digit",
    timeZone,
    year: "numeric",
  }).format(value);
}

/**
 * `YYYY-MM-DD` haqiqiy kalendar kunimi.
 *
 * Shakl tekshiruvi YETARLI EMAS: `2026-02-30` naqshga mos keladi, lekin
 * mavjud emas. Shuning uchun qiymat UTC'da qayta qurilib, teskari
 * o'girilgan satr bilan solishtiriladi.
 */
export function isValidIsoDay(value: string): boolean {
  if (!ISO_DAY.test(value)) return false;
  const parsed = new Date(`${value}T00:00:00Z`);
  if (Number.isNaN(parsed.getTime())) return false;
  return parsed.toISOString().slice(0, 10) === value;
}

/**
 * Kunni `days` ga siljitadi.
 *
 * ⚠ UTC'da hisoblanadi va bu TO'G'RI: Toshkent UTC+5 va YOZGI VAQT YO'Q
 *   [MEROS: 04-RESEARCH §A.1], ya'ni kalendar kuni bo'yicha arifmetika
 *   siljish bermaydi. Mahalliy `Date` bilan hisoblash DST'li mintaqada
 *   ishlab turgan brauzerda bir kunni ikki marta yoki umuman
 *   bermasligi mumkin edi.
 */
export function shiftIsoDay(iso: string, days: number): string {
  const base = new Date(`${iso}T00:00:00Z`);
  base.setUTCDate(base.getUTCDate() + days);
  return base.toISOString().slice(0, 10);
}

export type DaySelection = {
  /** Tanlangan biznes-kun — HAR DOIM yaroqli va HAR DOIM <= bugun. */
  day: string;
  todayIso: string;
  isToday: boolean;
  setDay: (next: string) => void;
};

/**
 * Kun tanlovi — YAGONA manba (panel ham, jurnal ham shundan o'qiydi).
 *
 * ⚠ QAYTARILADIGAN `day` NORMALLASHTIRILGAN: yaroqsiz ham, kelajakdagi
 *   kun ham bugunga tushadi. Iste'molchi hech qachon «bu qiymat
 *   ishonchlimi?» degan savolga tushmaydi va tekshiruv bir joyda qoladi.
 */
export function useDaySelection(): DaySelection {
  const [raw, setRaw] = useQueryState(
    DAY_PARAM,
    parseAsString.withDefault("").withOptions({ history: "push" }),
  );
  const timeZone = useTimeZone() ?? "Asia/Tashkent";
  const now = useNow();

  const todayIso = businessDayIn(timeZone, now);
  const day = isValidIsoDay(raw) && raw <= todayIso ? raw : todayIso;

  return {
    day,
    todayIso,
    isToday: day === todayIso,
    setDay: (next: string) => {
      /*
       * Bugungi kun uchun parametr UMUMAN yozilmaydi — standart holat
       * toza havola bo'lib qoladi va ulashilgan «bugun» havolasi
       * ertasiga ham BUGUNNI ko'rsatadi (sana qotib qolmaydi).
       */
      void setRaw(next === todayIso ? null : next);
    },
  };
}

/** `?issues=1` — jurnal filtri (Z-10). Standart: o'chiq. */
export function useIssuesOnly(): [boolean, (next: boolean) => void] {
  const [value, setValue] = useQueryState(
    ISSUES_PARAM,
    parseAsBoolean.withDefault(false).withOptions({ history: "push" }),
  );
  return [value, (next: boolean) => void setValue(next ? true : null)];
}

export function DayPicker() {
  const t = useTranslations();
  const selection = useDaySelection();
  const inputId = useId();

  /*
   * ⚠ E'LON FOYDALANUVCHI URINGANDA TUG'ILADI, sahifa ochilganda emas.
   *   `role="status"` ni doimiy matn bilan to'ldirish har kun
   *   almashtirilganda «kelajakdagi kun tanlanmaydi» ni qayta o'qitardi —
   *   holbuki foydalanuvchi buni so'ramagan (§12.6 ning jonli hududlar
   *   reyestri ikkitadan ortiq faol hududni taqiqlaydi).
   */
  const [notice, setNotice] = useState("");

  function goPrev(): void {
    setNotice("");
    selection.setDay(shiftIsoDay(selection.day, -1));
  }

  function goNext(): void {
    if (selection.isToday) {
      /*
       * ⛔ `aria-disabled`, `disabled` EMAS (§12.3): o'chirilgan tugma
       *    fokus olmaydi va skrinrider uni umuman o'qimaydi — «nega
       *    bosilmayapti?» savoliga javob qolmaydi. Shuning uchun tugma
       *    BOSILADI, lekin so'rov yuborilmaydi va SABAB e'lon qilinadi.
       */
      setNotice(t("snapshots.noFutureDays"));
      return;
    }
    setNotice("");
    selection.setDay(shiftIsoDay(selection.day, 1));
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <Button
        aria-label={t("snapshots.dayPrev")}
        onClick={goPrev}
        size="sm"
        title={t("snapshots.dayPrev")}
        variant="secondary"
      >
        <ChevronLeft aria-hidden="true" />
      </Button>

      <Button
        aria-disabled={selection.isToday}
        onClick={() => {
          setNotice("");
          if (!selection.isToday) selection.setDay(selection.todayIso);
        }}
        size="sm"
        variant="secondary"
      >
        {t("snapshots.dayToday")}
      </Button>

      {/*
       * Har boshqaruv elementida `<label htmlFor>` (§12.1) — platsholder
       * yorliq o'rnini bosmaydi. Yorliq `sr-only`, chunki tanlagichning
       * vazifasi qatorning O'ZIDAN ko'rinib turibdi.
       */}
      <label className="sr-only" htmlFor={inputId}>
        {t("snapshots.day")}
      </label>
      <input
        className="min-h-11 rounded-md border border-border bg-surface px-3 text-sm text-text focus-visible:border-accent focus-visible:ring-2 focus-visible:ring-accent/25 focus-visible:outline-none"
        id={inputId}
        /* ⛔ Kelajak `max` bilan ham to'siladi — hook bilan BIRGA, ikki qatlam. */
        max={selection.todayIso}
        onChange={(event) => {
          setNotice("");
          const next = event.target.value;
          if (isValidIsoDay(next) && next <= selection.todayIso) {
            selection.setDay(next);
          }
        }}
        type="date"
        value={selection.day}
      />

      <Button
        aria-disabled={selection.isToday}
        aria-label={t("snapshots.dayNext")}
        onClick={goNext}
        size="sm"
        title={selection.isToday ? t("snapshots.noFutureDays") : t("snapshots.dayNext")}
        variant="secondary"
      >
        <ChevronRight aria-hidden="true" />
      </Button>

      <p className="sr-only" role="status">
        {notice}
      </p>
    </div>
  );
}
