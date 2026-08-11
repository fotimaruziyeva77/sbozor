"use client";

import { useId, useState } from "react";
import { useNow, useTimeZone, useTranslations } from "next-intl";
import { parseAsString, useQueryState } from "nuqs";

import {
  businessDayIn,
  isValidIsoDay,
  shiftIsoDay,
} from "@/components/snapshots/day-picker";

/*
 * =============================================================================
 * Y-4 NING KUN TANLAGICHI — STANDARTI ⛔ KECHA (§11.1, C-3).
 *
 * -----------------------------------------------------------------------
 * ⛔ NEGA STANDART «BUGUN» EMAS — BU XULQ EMAS, MAHSULOT QARORI
 * -----------------------------------------------------------------------
 * Hisob ⛔ ERTASI KUNI 04:10 da tug'iladi (C-3: `BILLING_CLOSE_CRON`
 * `"10 4 * * *"`, chunki `stall_slot_occupancy` D kuni uchun faqat
 * D+1 03:40 da to'ladi). Ya'ni ⛔ BUGUNGI KUN UCHUN YOZILGAN HISOB
 * UMUMAN MAVJUD EMAS.
 *
 * Standart «bugun» bo'lsa, direktor sahifani ochganda ⛔ HAR DOIM bo'sh
 * ro'yxat ko'rardi va «tizim ishlamayapti» degan xulosaga kelardi —
 * holbuki tizim to'g'ri ishlayapti va shunchaki hali vaqt kelmagan.
 * Standarti KECHA bo'lgan sahifa esa birinchi ochilishdayoq HAQIQIY
 * ma'lumot ko'rsatadi.
 *
 * -----------------------------------------------------------------------
 * ⛔ MAKSIMUM — BUGUN, VA U IKKI QATLAMDA
 * -----------------------------------------------------------------------
 * Kelajakdagi kun uchun hisob ⛔ IMKONSIZ:
 * `CHECK (service_date <= business_date)`. UI qatlami `max` atributi va
 * `onChange` filtri bilan to'sadi, server esa 422 beradi. ⚠ UI qatlami
 * DARVOZA EMAS — u DevTools bilan olib tashlanadi; u shunchaki
 * foydalanuvchini bajarilmas so'rovdan qaytaradi (02-15 ning qoidasi).
 *
 * -----------------------------------------------------------------------
 * ⚠ SOF YORDAMCHILAR 4-FAZADAN QAYTA ISHLATILADI, NUSXA OLINMAYDI
 * -----------------------------------------------------------------------
 * `businessDayIn` / `isValidIsoDay` / `shiftIsoDay` —
 * `components/snapshots/day-picker.tsx` da va ular SHU YERGA
 * KO'CHIRILMAYDI. Ikkinchi nusxa bir kun `en-CA` formatlagichi yoki UTC
 * arifmetikasi bo'yicha ajralib ketardi va ikki ekran BOSHQA-BOSHQA
 * biznes-kunni ko'rsatardi — buni hech qanday test ko'rmasdi, chunki
 * har nusxa o'z testi bilan kelardi.
 *
 * ⛔ LEKIN HOOK QAYTA ISHLATILMAYDI: `useDaySelection()` ning standarti
 *    BUGUN va u 4-fazaning xulqi (`/snapshots`, `/occupancy`). Uni
 *    parametrlash ikkala iste'molchining standartini BITTA shartga
 *    bog'lardi va bu yerdagi C-3 qarori o'sha shartning ichida
 *    ko'rinmay qolardi.
 *
 * ⚠ Y-4 — `?day=` GA RUXSAT ETILGAN YAGONA YUZA (§4.5). Y-1 va Y-3 da
 *   URL holati TAQIQ; bu yerda esa kun ulashiladigan havolaning bir
 *   qismi va «qaysi kunni ko'rdingiz?» savoli nizoda ma'no tashiydi.
 * =============================================================================
 */

/** `?day=YYYY-MM-DD` — Y-4 ning YAGONA URL holati (§4.5). */
export const BILLING_DAY_PARAM = "day";

export type BillingDaySelection = {
  /** Tanlangan biznes-kun — HAR DOIM yaroqli va HAR DOIM <= bugun. */
  day: string;
  todayIso: string;
  /** ⛔ STANDART — sabab yuqoridagi blokda (C-3). */
  yesterdayIso: string;
  /** `day = bugun` — sahifa bloklar to'plamini shunga qarab tanlaydi (G-25). */
  isToday: boolean;
  setDay: (next: string) => void;
};

/**
 * Y-4 ning kun tanlovi — YAGONA manba (sahifa ham, bloklar ham shundan).
 *
 * ⚠ QAYTARILADIGAN `day` NORMALLASHTIRILGAN: yaroqsiz qiymat ham,
 *   kelajakdagi kun ham STANDARTGA (kecha) tushadi. Iste'molchi hech
 *   qachon «bu qiymat ishonchlimi?» degan savolga tushmaydi.
 *
 * ⚠ YAROQSIZ `?day=` JIMGINA STANDARTGA TUSHADI va xato ko'rsatilmaydi
 *   [MEROS: 03-UI-SPEC §5.4]: eskirgan xatcho'pdan kelgan direktorga
 *   «URL noto'g'ri» deyish hech qanday foydali qadam bermaydi.
 */
export function useBillingDay(): BillingDaySelection {
  const [raw, setRaw] = useQueryState(
    BILLING_DAY_PARAM,
    parseAsString.withDefault("").withOptions({ history: "push" }),
  );
  const timeZone = useTimeZone() ?? "Asia/Tashkent";
  const now = useNow();

  const todayIso = businessDayIn(timeZone, now);
  const yesterdayIso = shiftIsoDay(todayIso, -1);
  const day = isValidIsoDay(raw) && raw <= todayIso ? raw : yesterdayIso;

  return {
    day,
    todayIso,
    yesterdayIso,
    isToday: day === todayIso,
    setDay: (next: string) => {
      /*
       * Standart kun uchun parametr UMUMAN yozilmaydi — toza havola
       * ertasiga ham O'SHA KUNGI standartni (yangi «kecha» ni)
       * ko'rsatadi va sana havolada qotib qolmaydi.
       */
      void setRaw(next === yesterdayIso ? null : next);
    },
  };
}

/**
 * Kun tanlagichi — BOSHQARUV, ro'yxat EMAS.
 *
 * ⛔ Shuning uchun u `data-billing-content` CHIQARMAYDI va G-25 (b) da
 *    `CONTENT_EXEMPT` ichida: uning o'z da'volari shu papkadagi
 *    `day-picker.test.tsx` da, sahifa darvozasida emas.
 */
export function BillingDayPicker() {
  const t = useTranslations();
  const selection = useBillingDay();
  const inputId = useId();

  /*
   * ⚠ E'LON FOYDALANUVCHI URINGANDA TUG'ILADI, sahifa ochilganda emas
   *   (`snapshots/day-picker.tsx:202-209` qoidasi): doimiy matn har kun
   *   almashtirilganda qayta o'qilardi.
   */
  const [rejected, setRejected] = useState(false);

  return (
    <div className="flex flex-wrap items-center gap-2">
      {/* Har boshqaruvda `<label htmlFor>` (§14.1) — platsholder yorliq emas. */}
      <label className="text-sm text-text-muted" htmlFor={inputId}>
        {t("billing.dayLabel")}
      </label>

      <input
        aria-invalid={rejected}
        className="min-h-11 rounded-md border border-border bg-surface px-3 text-sm text-text focus-visible:border-accent focus-visible:ring-2 focus-visible:ring-accent/25 focus-visible:outline-none"
        id={inputId}
        /* ⛔ Kelajak `max` bilan HAM to'siladi — filtr bilan BIRGA, ikki qatlam. */
        max={selection.todayIso}
        onChange={(event) => {
          const next = event.target.value;
          if (isValidIsoDay(next) && next <= selection.todayIso) {
            setRejected(false);
            selection.setDay(next);
            return;
          }
          /*
           * ⛔ KELAJAK QABUL QILINMAYDI: `?day=` YOZILMAYDI va maydon
           *    `aria-invalid` oladi. Jimgina bugunga tushirish
           *    foydalanuvchiga «qabul qilindi» deb yolg'on gapirardi.
           */
          setRejected(true);
        }}
        type="date"
        value={selection.day}
      />

      <p className="sr-only" role="status">
        {rejected ? t("billing.noFutureDays") : ""}
      </p>
    </div>
  );
}
