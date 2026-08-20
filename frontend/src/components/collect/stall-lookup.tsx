"use client";

import type { RefObject } from "react";
import { Search } from "lucide-react";
import { useTranslations } from "next-intl";

import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { billingErrorView } from "@/lib/billing-errors";
import { cn } from "@/lib/cn";

/*
 * =============================================================================
 * 1-QADAM — RASTA RAQAMINI TOPISH (UI-SPEC §8.3).
 *
 * ⛔⛔ BU NAVIGATOR, FILTR EMAS — VA FARQ MEXANIK.
 *
 *   `stalls/stall-filters.tsx` RO'YXATNI TORAYTIRADI: natija — kamroq
 *   qator, foydalanuvchi ularni ko'zdan kechiradi. Bu yerda esa natija —
 *   BITTA RASTA va oqim darhol keyingi qadamga o'tadi. Shuning uchun
 *   `enterKeyHint="go"` («ket»), `"search"` EMAS: klaviaturaning o'zi
 *   foydalanuvchiga «bu qidiruv emas, bu o'tish» deb aytadi.
 *
 * -----------------------------------------------------------------------
 * ⛔ QADAM IDENTIFIKATORI — HAR LAHZADA AYNAN BITTA ELEMENT (§8.2)
 * -----------------------------------------------------------------------
 * `data-collect-step="stall"` MAVJUD BO'LGAN elementga qo'yiladi:
 *   - ro'yxat yo'q  -> `<input>` ning O'ZIGA;
 *   - ro'yxat bor   -> RO'YXAT KONTEYNERIGA (input atributni YO'QOTADI).
 *
 * ⛔ Qiymat IKKALA holatda ham `"stall"` — bu 06-UI-SPEC §8.2 ning ochiq
 *    FLAG'ini yopgan qaror: ko'p moslikdagi tanlash 1-QADAM ICHIDAGI
 *    ikkinchi o'zaro ta'sir bo'lib qoladi. Natijada sanoq baxtli yo'lda
 *    3, ko'p moslikda 4 bo'ladi va qo'shimcha o'zaro ta'sir SON BILAN
 *    ko'rinadi — 02-UI-SPEC §6.9 ning «≤2 o'zaro ta'sir» byudjeti
 *    o'lchanadigan bo'ladi.
 *
 * ⛔ `ownsStep` PROP: qadamning egasi SESSIYA komponentida hal qilinadi.
 *    Rasta topilgach qadam `payment-bar.tsx` ga o'tadi va bu element
 *    atributni YO'QOTADI — aks holda DOM'da ikkita `[data-collect-step]`
 *    bo'lib, §8.2 invarianti (va u bilan birga G-20 sanog'i) buzilardi.
 *
 * -----------------------------------------------------------------------
 * ⛔ O'Z RAQAMLI KLAVIATURAMIZ QURILMAYDI (06-RESEARCH OQ-2)
 * -----------------------------------------------------------------------
 * `inputMode="numeric"` OS ning o'z panelini ochadi. Raqam-only panel
 * `A-3` yoki `12a` kabi kodlarni KIRITIB BO'LMAYDIGAN qilardi va bu
 * «ba'zi rastalardan pul yig'ib bo'lmaydi» degan nosozlikka aylanardi.
 * ⛔ Ayni sabab bilan maydonning turi MATN bo'lib qoladi — raqamli tur
 * brauzer darajasida harf va chiziqchani rad etardi.
 *
 * -----------------------------------------------------------------------
 * ⚠ MATN «TOPILMADI» HOLATIDA TANLANADI
 * -----------------------------------------------------------------------
 * Kassir qayta terish uchun `Ctrl+A` bosmasligi kerak — bu bozor
 * sharoitida bir qo'lda bajarib bo'lmaydigan harakat.
 * =============================================================================
 */

/*
 * Qator harflari — «Sbozor Kassir» dizaynining K-1 yechimi (3.4-bo'lim).
 * Bosilganda harf qidiruvga yoziladi va SERVERNING MAVJUD prefiks qidiruvi
 * o'sha qatordagi rastalar ro'yxatini qaytaradi — yangi so'rov ochilmaydi.
 * ⛔ Shusiz kassir rasta raqamini FAQAT yoddan bilishi kerak edi: ro'yxat
 *   ham, xarita ham unga yopiq (o'lchandi, 2026-08-18).
 */
/*
 * ⛔⛔ QATOR HARFLARI SERVERDAN — QOTIRILGAN EMAS (260820).
 *
 *     Bu yerda `["A","B","C","D"]` yozilgandi. Oqibati ikki tomonlama
 *     va ikkalasi ham jonli ko'rindi:
 *
 *       · Karmanada faqat A va B bor -> kassir ekranida IKKITA
 *         O'LIK tugma turardi (bosilsa «rasta topilmadi»);
 *       · qatori E dan boshlanadigan bozorda kassirga YORDAM
 *         BO'LMASDI — u kodni yoddan terishi kerak edi.
 *
 *     Kassirda `MARKET_DATA_VIEW` yo'q (C-10), ya'ni u rastalar
 *     ro'yxatini o'zi ko'ra olmaydi — shuning uchun harflar
 *     `GET /billing/pending` javobida (`row_prefixes`) keladi.
 */

export type StallLookupProps = {
  /** Qidiruv maydonining joriy qiymati (sahifa holatida, ⛔ URL'da EMAS). */
  value: string;
  onValueChange: (value: string) => void;
  /** `Enter` bosilganda — kod bo'sh bo'lmasa chaqiriladi. */
  onSubmit: (code: string) => void;
  /** Ko'p moslikdagi kodlar (server tartibida); bo'sh bo'lsa ro'yxat yo'q. */
  matches: readonly string[];
  onSelectMatch: (code: string) => void;
  /** Server `stall_not_found` qaytardimi. */
  notFound: boolean;
  /** Qadam identifikatori SHU komponentda turibdimi (§8.2 invarianti). */
  ownsStep: boolean;
  /** `autoFocus` va §8.5 fokus qaytishi uchun — egasi sessiya komponenti. */
  inputRef: RefObject<HTMLInputElement | null>;
  /**
   * Bozorda MAVJUD qator harflari (`GET /billing/pending`).
   *
   * ⛔ Bo'sh massiv — tugmalar UMUMAN chizilmaydi. Raqamli kodli
   *    bozorda («23», «107») harf tugmasi ma'nosiz bo'lardi.
   */
  rowPrefixes: readonly string[];
  /** Maydon `id` si — `Field` yorlig'i shunga bog'lanadi. */
  fieldId: string;
};

export function StallLookup({
  value,
  onValueChange,
  onSubmit,
  matches,
  onSelectMatch,
  notFound,
  ownsStep,
  inputRef,
  rowPrefixes,
  fieldId,
}: StallLookupProps) {
  const t = useTranslations();

  const hasMatches = matches.length > 0;
  const notFoundView = billingErrorView("stall_not_found");

  return (
    <div className="flex flex-col gap-3">
      {/* Qator tugmalari — qidiruvga harf yozadi, ro'yxatni server ochadi.
          ⛔ `data-collect-option` YO'Q: bu rastani TANLAMAYDI, ro'yxatni
          ochadi — ya'ni ≤3 ta'sir shartnomasining sanog'iga kirmaydi. */}
      <div className="flex flex-wrap gap-2">
        {rowPrefixes.map((letter) => (
          <button
            className={cn(
              "min-h-11 min-w-11 cursor-pointer rounded-md border px-3",
              "text-sm font-semibold transition-colors",
              value.trim().toUpperCase().startsWith(letter)
                ? "border-accent bg-accent/10 text-accent-text"
                : "border-border text-text hover:bg-surface-muted",
            )}
            key={letter}
            onClick={() => {
              onValueChange(letter);
              onSubmit(letter);
              /*
               * ⛔⛔ FOKUS MAYDONGA QAYTADI (260820, jonli o'lchandi).
               *
               *     Harf bosilgach fokus TUGMADA qolardi va kassir
               *     raqamni darhol tera olmasdi — avval maydonni
               *     bosishi kerak edi. Telefonda bu qo'shimcha
               *     tegish, ya'ni «≤3 bosish» va'dasining buzilishi.
               *
               * ⚠ Fokus qaytishi ro'yxatni YOPMAYDI: harf bosilganda
               *   server mosliklarni qaytaradi va ular tanlash uchun
               *   ochiq qoladi — kassir xohlasa teradi, xohlasa
               *   ro'yxatdan tanlaydi.
               */
              inputRef.current?.focus();
            }}
            type="button"
          >
            {letter}
          </button>
        ))}
      </div>
      <Field
        hint={hasMatches ? t("collect.rowHint") : t("collect.stallHint")}
        id={fieldId}
        label={t("collect.stallLabel")}
      >
        <div className="relative">
          <Search
            aria-hidden="true"
            className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-text-muted"
          />
          <Input
            /*
             * ⛔ BESHALA XOSSA HAM §8.3 JADVALIDAN va birortasi ham
             *    bezak emas — har biri o'lchangan nosozlikni yopadi.
             */
            aria-describedby={`${fieldId}-hint`}
            autoComplete="off"
            autoFocus
            className="min-h-14 pl-9"
            data-collect-step={ownsStep && !hasMatches ? "stall" : undefined}
            enterKeyHint="go"
            id={fieldId}
            inputMode="numeric"
            onChange={(event) => onValueChange(event.target.value)}
            onKeyDown={(event) => {
              if (event.key !== "Enter") return;
              event.preventDefault();
              const code = value.trim();
              if (code === "") return;
              onSubmit(code);
            }}
            ref={inputRef}
            type="text"
            value={value}
          />
        </div>
      </Field>

      {/*
       * ⛔ KO'P MOSLIK — RO'YXAT, VA U 1-QADAM ICHIDA QOLADI.
       *
       *   Aynan bitta moslikda bu blok UMUMAN chizilmaydi (02-UI-SPEC
       *   §6.9 kontrakti: bitta natija -> darhol karta). Oraliq ro'yxat
       *   ko'rsatish har rastaga bitta qo'shimcha bosish qo'shardi va
       *   D-18 ni kuniga 300–1000 marta buzardi.
       *
       *   Tartib SERVERDA (`stalls.code_sort`) — inson-raqamli tartib
       *   klientda qayta hisoblanmaydi: ikkinchi tartiblash ikkinchi
       *   haqiqat manbai bo'lardi.
       */}
      {hasMatches ? (
        <ul
          aria-label={t("collect.stallLabel")}
          className="flex flex-col gap-2 rounded-md border border-border bg-surface p-2"
          data-collect-step={ownsStep ? "stall" : undefined}
        >
          {matches.map((code) => (
            <li key={code}>
              <button
                className="flex min-h-11 w-full items-center rounded-sm px-3 text-left text-sm font-semibold text-text hover:bg-surface-muted"
                data-collect-option="stall"
                onClick={() => onSelectMatch(code)}
                type="button"
              >
                {code}
              </button>
            </li>
          ))}
        </ul>
      ) : null}

      {/*
       * ⛔ «TOPILMADI» — SABAB + NIMA QILISH KERAK (§13.7), yalang'och
       *    «topilmadi» EMAS. `role="status"`, `role="alert"` emas: §14.5
       *    da bir vaqtda ikkitadan ko'p `alert` chizilmaydi va bu yerda
       *    ogohlantirish emas, oddiy qayta terish holati.
       */}
      {notFound && !hasMatches && notFoundView !== null ? (
        <div
          className="flex flex-col gap-1 rounded-sm bg-danger/10 px-3 py-2"
          role="status"
        >
          <p className="text-sm font-semibold text-danger-text">
            {t(notFoundView.causeKey)}
          </p>
          <p className="text-sm text-text">{t(notFoundView.fixKey)}</p>
        </div>
      ) : null}
    </div>
  );
}
