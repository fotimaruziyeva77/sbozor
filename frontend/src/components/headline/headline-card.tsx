"use client";

import { useFormatter, useTranslations } from "next-intl";
import { useState } from "react";

import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/cn";
import {
  headlineLabelKey,
  headlineUnitOf,
  useHeadline,
} from "@/lib/headline-queries";
import { useCountUp } from "@/lib/use-count-up";

/*
 * =============================================================================
 * ⛔⛔ BOSH EKRAN KO'RSATKICHI — IKKINCHI SONNI KO'RSATA OLMAYDIGAN KARTA.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 1. BU KOMPONENT ROLNI UMUMAN O'QIMAYDI [QAROR — UI-SPEC §10.2]
 * -----------------------------------------------------------------------
 * Sessiya do'koni, huquq tekshiruvi va besh rol nomining birortasi ham bu
 * KATALOGDA uchramaydi. Ya'ni «bu kassirmi?» degan shoxni bu yerda
 * YOZIB BO'LMAYDI — u yozilishi uchun avval taqiqlangan nom import
 * qilinishi kerak, va o'sha import darvozani QIZARTIRADI.
 *
 * Sabab intizom emas, ARXITEKTURA: qaysi son qaysi huquqqa tegishli
 * ekanini SERVER hal qiladi (D-28, `me.py::HEADLINE_ORDER`). Klient buni
 * takrorlasa IKKINCHI HAQIQAT MANBAI tug'ilardi va u serverdan jimgina
 * ajralib ketardi — foydalanuvchi ekranda bir sonni, hisobotda boshqasini
 * ko'rardi.
 *
 * ⛔ Shuning uchun komponentga FAQAT `marketId` beriladi. Ko'proq
 *    ma'lumot berish uchun ochiq yo'l YO'Q: propslar ro'yxati shu.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 2. AYNAN BITTA RAQAM [D-29]
 * -----------------------------------------------------------------------
 * Trend, o'q, «kechagiga nisbatan», foiz, ikkinchi qator — ⛔ YO'Q.
 * Ikkinchi son qo'shilishi bilan karta «qaysi biri asosiy?» degan
 * savolga javob berishga majbur bo'lardi va o'sha javob ROLGA bog'liq
 * bo'lardi — ya'ni yuqoridagi 1-band bir bosqichda buzilardi.
 *
 * ⛔ Ikonka ham YO'Q (§10.2): ikonka «bu qanday son» ni aytishga
 *    urinardi, ya'ni u ham rolga bog'liq shart tug'dirardi.
 * ⛔ `[Batafsil]` havolasi ham YO'Q (§10.5): har rol uchun BOSHQA nishon
 *    kerak bo'lardi.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 3. BIRLIK MATNI REYESTRDAN KELADI, SHARTDAN EMAS [Pitfall 1]
 * -----------------------------------------------------------------------
 * `HEADLINE_UNIT[metric] === "soum"` bo'lgandagina `headline.amountUnit`
 * chiziladi. Kassirning ko'rsatkichi — KVITANSIYALAR SONI, ya'ni uning
 * birligi `"count"` va unga «so'm» ⛔ QO'SHILMAYDI.
 *
 * Bu kosmetika emas: 6-faza kassir ko'rligini uch qatlamda qurgan
 * (T-06-53, T-06-59, `shifts.py:126`) va bosh ekranda pul birligi bilan
 * ko'rsatilgan son kassirni smena yopishda AYNAN SHU SONNI deklaratsiya
 * qilishga undardi — variance HAR DOIM NOL bo'lardi.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 4. KO'RSATKICH YO'Q BO'LSA — KARTA UMUMAN CHIZILMAYDI
 * -----------------------------------------------------------------------
 * `403` (huquq mos kelmadi) ham, javob kelmagan holat ham `null`
 * qaytaradi: na nol, na tire, na «yuklab bo'lmadi» qizil bloki.
 *
 * ⛔ NOL YOZILMAYDI, chunki nol — O'LCHANGAN QIYMAT (T-05-04, 05-14).
 * ⛔ XATO BLOKI HAM CHIZILMAYDI [QAROR — §10.2 so'zma-so'z]: bosh
 *    ekranda foydalanuvchi HECH NARSA QILA OLMAYDIGAN qizil blok —
 *    shovqin. Sahifaning qolgani ishlayveradi, ko'rsatkich esa yo'q
 *    bo'lsa — yo'q.
 *
 * ⚠ REJADAN OG'ISH (ochiq qayd): reja «xatoda `role="alert"` bilan qisqa
 *   matn» degan edi. UI-SPEC §10.2 esa buni [QAROR] bilan RAD ETADI
 *   («Xato — karta umuman chizilmaydi (`null`)»), va §14.9 xato
 *   kontrakti har xato matnidan SABAB + NIMA QILISH KERAK talab qiladi —
 *   bu yerda ikkalasi ham yo'q. Bog'lovchi hujjat — UI-SPEC.
 *
 * -----------------------------------------------------------------------
 * ⚠ 5. YANGI `ui/` PRIMITIVI QURILMAYDI [§3.2]
 * -----------------------------------------------------------------------
 * `ui/` dagi «katta raqam kartasi» ertaga `secondaryValue` propini
 * olardi va D-29 BITTA PROPS UZATILISHI bilan buzilardi. Mavjud `Card`
 * ishlatiladi, urg'u esa TIPOGRAFIYADAN keladi (§7.2), yangi
 * o'lchamdan emas (§6.2 — ichki bo'shliq `lg`, ya'ni 16px).
 * =============================================================================
 */

export type HeadlineCardProps = {
  /** ⛔ Komponentning YAGONA kirishi (§10.2). */
  marketId: string | null;
};

export function HeadlineCard({ marketId }: HeadlineCardProps) {
  const t = useTranslations();
  const format = useFormatter();
  const headline = useHeadline(marketId);

  /*
   * Count-up (09-UI-SPEC §10.3, L-5): 600ms, kubik ease. ⛔ `undefined`
   * `null` ga tushadi va halqa UMUMAN boshlanmaydi — nol sanalmaydi
   * (T-05-04). Oxirgi kadr — qiymatning O'ZI, ya'ni pastdagi
   * `format.number()` AYNAN server songa qo'llanadi.
   */
  const shown = useCountUp(headline.value ?? null);

  /*
   * Tick — count tugagach BIR marta `scale(1.03)` (L-5). `settledFor`
   * `transitionEnd` da QAYSI qiymat uchun tick tugaganini eslab qoladi:
   * yuqoriga 150ms + pastga 150ms, ⛔ cheksiz pulsatsiya YO'Q. Yangi
   * qiymatda `settledFor !== value` bo'lib tick o'zi qayta qurollanadi —
   * effektda sinxron setState YO'Q (hodisa-asosli).
   */
  const [settledFor, setSettledFor] = useState<number | null>(null);

  /* Bozor tanlanmagan — so'rov ham yuborilmaydi, karta ham chizilmaydi. */
  if (marketId === null) return null;

  if (headline.isPending) {
    return (
      <Card
        aria-busy="true"
        className="flex flex-col gap-1 p-4"
        data-headline
        role="status"
      >
        <span className="sr-only">{t("common.loading")}</span>
        {/*
         * ⛔ `0` EMAS: soxta javob bo'lardi (§10.2).
         * ⛔ G-motion-7(c): balandlik `h-11` — `isPending` da `unit` HALI
         *    MA'LUM EMAS, shuning uchun ENG KATTA shox (Display-XL, 44px
         *    qator qutisi) olinadi. `h-8` -> `h-11` sakrashi CLS berardi;
         *    `count` shoxida `h-11` -> `h-8` qisqarishi esa layout
         *    siljishi emas, shunchaki bo'shliq (09-RESEARCH ochiq savol 5).
         */}
        <Skeleton className="h-11 w-28" />
        <Skeleton className="h-5 w-48" />
      </Card>
    );
  }

  /*
   * ⛔ YAGONA CHIQISH NUQTASI: `available === false` — huquq yo'q (`403`)
   *    yoki javob kelmadi. Ikkala holatda ham karta YO'Q.
   */
  if (
    !headline.available ||
    headline.metric === undefined ||
    headline.value === undefined
  ) {
    return null;
  }

  const value = headline.value;
  const unit = headlineUnitOf(headline.metric);

  /* Count tugadi — tick kadri (`scale(1.03)`), `transitionEnd` qaytaradi. */
  const arrived = shown === value;

  return (
    <Card className="flex flex-col gap-1 p-4" data-headline>
      {/*
       * Display roli (§7.1) + ⛔ `font-mono` (§7.3): summa HAM, sanoq HAM
       * bir xil uslubda. Ikki uslub «bu boshqa turdagi son» degan YOLG'ON
       * KANAL bo'lardi — ekran qaysi son ekanini BILMAYDI.
       *
       * ⛔ G-motion-7(b): `text-display` SHARTLI — FAQAT `unit === "soum"`.
       *    Metrikani SERVER tanlaydi va u rasta/kvitansiya SONI ham
       *    bo'lishi mumkin; 40px li «34» direktorga «34 million» bo'lib
       *    o'qilardi (§7.1). Sanoq `text-2xl` da QOLADI.
       */}
      <p
        className={cn(
          "font-semibold tracking-tight",
          unit === "soum" ? "text-display" : "text-2xl leading-tight",
        )}
      >
        {/*
         * ⛔ A11Y (§10.3): yakuniy qiymat `sr-only` MATN TUGUNI bo'lib
         *    DARHOL to'liq turadi — skrinrider count'ni kutmaydi va
         *    `aria-live` UMUMAN yo'q (600ms da 20 marta gapirardi).
         *    Sanayotgan span esa `aria-hidden` — u bezak, ma'lumot emas.
         *    G-33(a) skaneri ham aynan shu `sr-only` tugunni o'qiydi.
         */}
        <span className="sr-only">{format.number(value)}</span>
        <span
          aria-hidden="true"
          className={cn(
            "inline-block font-mono tabular-nums",
            /* Tick — 150ms (`--motion-fast` token, sehrli son YO'Q). */
            "transition-transform duration-(--motion-fast)",
            arrived && settledFor !== value ? "scale-[1.03]" : "scale-100",
          )}
          onTransitionEnd={() => setSettledFor(value)}
        >
          {format.number(shown ?? value)}
        </span>
        {/*
         * ⛔ Birlik FAQAT `"soum"` da. `pending-summary.tsx:177` naqshi:
         *    «Rasta SONI — pul emas, shuning uchun `amountUnit` YO'Q».
         */}
        {unit === "soum" ? (
          <>
            {" "}
            {t("headline.amountUnit")}
          </>
        ) : null}
      </p>
      {/*
       * Yorliq — Body + `text-text-muted` (§7.2). ⛔ Heading EMAS: u
       * sahifa sarlavhasi bilan raqobatlashardi va ko'z uni «bo'lim nomi»
       * deb o'qirdi.
       *
       * ⚠ `count` — ICU ko'plik SHAKLINI tanlash uchun; matn ichida son
       *   CHIZILMAYDI (branch'larda `#` yo'q), aks holda ekranda IKKINCHI
       *   raqam paydo bo'lardi.
       */}
      <p className="text-sm leading-normal text-text-muted">
        {t(headlineLabelKey(headline.metric), { count: value })}
      </p>
    </Card>
  );
}
