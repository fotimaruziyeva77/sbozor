"use client";

import { useFormatter, useTranslations } from "next-intl";

import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  headlineLabelKey,
  headlineUnitOf,
  useHeadline,
} from "@/lib/headline-queries";

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
        {/* ⛔ `0` EMAS: soxta javob bo'lardi (§10.2). */}
        <Skeleton className="h-8 w-28" />
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

  return (
    <Card className="flex flex-col gap-1 p-4" data-headline>
      {/*
       * Display roli (§7.1) + ⛔ `font-mono` (§7.3): summa HAM, sanoq HAM
       * bir xil uslubda. Ikki uslub «bu boshqa turdagi son» degan YOLG'ON
       * KANAL bo'lardi — ekran qaysi son ekanini BILMAYDI.
       */}
      <p className="text-2xl leading-tight font-semibold tracking-tight">
        <span className="font-mono tabular-nums">{format.number(value)}</span>
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
