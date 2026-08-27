"use client";

import { useTranslations } from "next-intl";

import { ConfusionMatrix } from "@/components/occupancy/confusion-matrix";
import { ExportButton } from "@/components/reports/export-button";
import { useReportPeriod } from "@/components/reports/period-picker";
import { Skeleton } from "@/components/ui/skeleton";
import { useAccuracyReport } from "@/lib/occupancy-queries";

/*
 * =============================================================================
 * ANIQLIK BLOKI — ⛔ O'RAM, IKKINCHI KOMPONENT EMAS (§9.2, M-11).
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 1. NEGA BU FAYL SHUNCHA KICHIK — VA SHUNDAY QOLISHI SHART.
 * -----------------------------------------------------------------------
 * Aniqlik yuzasining butun mazmuni ALLAQACHON `occupancy/` katalogida:
 * to'rt xom son, uch oraliq, bazaviy ulush, ikki xatoning ikki AYRIM
 * jumlasi va «hali o'lchanmadi» shoxi. Uni bu yerda QAYTA yozish ikkita
 * ekranda ⛔ IKKI XIL ANIQLIK ko'rsatishga olib borardi va ular
 * bir kun jimgina ajralib ketardi — 5-fazaning eng qimmat qarori
 * (foiz SERVERDAN) shu bilan bekor bo'lardi.
 *
 * ⛔ Shuning uchun bu fayl AYNAN uch ish qiladi: davrni uzatadi, mavjud
 *    komponentni chizadi va AI-02 jumlasini qo'yadi. ⛔ Nisbat, oraliq,
 *    chegara — birortasining ta'rifi bu yerda YO'Q (G-42(f)).
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 2. DAVR YORLIG'I PROP BO'LIB UZATILMAYDI (§8.7, G-39(c)).
 * -----------------------------------------------------------------------
 * Mavjud komponent davrni JAVOBNING `from_date`/`to_date` idan O'ZI
 * chizadi. Unga so'ralgan oraliqni prop qilib berish «men oktyabrni
 * so'radim, oktyabr ko'rsatildi» degan ⛔ YOLG'ON TASDIQ berardi —
 * holbuki server davrni QISQARTIRGAN bo'lishi mumkin. Shuning uchun bu
 * yerdan unga ⛔ FAQAT javob uzatiladi, davr esa so'rovga ketadi.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 3. O'LCHANMAGAN SON CHIZILMAYDI — VA U IKKI QATLAMDA AYTILADI.
 * -----------------------------------------------------------------------
 * `measured === false` da mavjud komponent foizlarni ⛔ UMUMAN
 * chizmaydi (qaror SERVERNIKI) va o'z jumlasini beradi. Bu yerga esa
 * ⛔ HISOBOT YUZASINING nomlangan sababi qo'shiladi va u ATAYIN boshqa
 * so'z bilan boshlanadi: «BU DAVRDA…».
 *
 * ⚠ Farq bezak emas, MA'NO: `/occupancy` da davr tanlanmaydi (server
 *   standarti), ya'ni u yerdagi «hali o'lchanmadi» ⛔ UMUMAN o'lchanmadi
 *   degani. Bu yerda esa davrni FOYDALANUVCHI tanlagan va aynan o'sha
 *   oynada javob yetmagan — «hali o'lchanmadi» ni o'qigan direktor
 *   «demak tizim hech qachon tekshirilmagan» degan ⛔ NOTO'G'RI xulosaga
 *   kelardi va davrni kengaytirib ko'rish xayoliga ham kelmasdi.
 *   Bu IN-05 (har yuza — o'z matn kataloqi) ning bevosita natijasi.
 *
 * ⛔ NOLGA TUSHIRUVCHI ZAXIRA OPERATORLARI (`??` / `||` ning nol bilan
 *    juftligi) bu faylda ⛔ TAQIQ — ular o'lchanmagan miqdorni
 *    o'lchangan nolga aylantirishning arifmetik shakli. O'lchandi
 *    (sabotaj 1): shunday zaxira qo'yilishi bilan ekranda foiz paydo
 *    bo'ladi va G-40(a) qizaradi.
 *
 * ⛔ SO'ROV YIQILGANDA ham foiz chizilmaydi va bo'sh matritsa ham
 *    ko'rsatilmaydi — bu ⛔ WR-05 ning aynan bandi (07 ko'rigi:
 *    «yiqilgan so'rov 0 % bo'lib chiziladi») va u SHU YERDA yopiladi.
 *    Xato NOMLANADI va keyingi qadam bilan birga keladi (D-02).
 *
 * ⛔ KLIENTDA IKKINCHI CHEGARA QURILMAYDI: «foiz chizilsinmi?» qarorini
 *    serverning `measured` i beradi va chegara soni ham javobdan keladi.
 *    Uni `wilson.ts` dagi konstantadan olish yoki taqqoslashni klientda
 *    takrorlash ikkinchi chegara tug'dirardi va ular bir kun ajralib
 *    ketardi (05-12, 2-ochiq band). ⚠ Maydonni O'QISH esa QONUNIY va
 *    MAJBURIY: nomlangan sabab serverning chegarasini AYTADI.
 *
 * -----------------------------------------------------------------------
 * ⛔ 4. AI-02 HOLATI — SHARTSIZ VA BEZAKSIZ (§9.4, D-11).
 * -----------------------------------------------------------------------
 * Jumla `measured` dan ⛔ MUSTAQIL: aniqlik o'lchangan kunlarda uni
 * yashirish «endi model tekshirilgan» degan ⛔ NOTO'G'RI xulosa berardi.
 * ⛔ Ogohlantirish bezagi ham, jonli hudud roli ham YO'Q: bu HOLAT,
 *    xato emas (07 D-22 sinfi) — bezak uni har ochilishda SHOVQIN
 *    qilardi va uch kundan keyin o'qilmay qolardi.
 *
 * -----------------------------------------------------------------------
 * ⛔ 5. EKSPORT TUGMASI SHU BLOKDA (§9.2 diagrammasi).
 * -----------------------------------------------------------------------
 * ⚠ Qo'shni ikki blokda (tushum, qarzdorlik) tugmani SAHIFA qo'yadi
 *   (08-13 qarori). Bu yerda esa u o'ramning ICHIDA va sabab
 *   spetsifikatsiyada literal: blok mavjud komponentni o'raydi, ya'ni
 *   «aniqlik hisoboti» degan yuza AYNAN shu fayl bilan tugaydi.
 *   ⛔ SAHIFA UNGA IKKINCHI TUGMA QO'YMAYDI.
 * =============================================================================
 */

export function AccuracyBlock() {
  const t = useTranslations();

  /* ⚠ Davr HOOKDAN, propdan emas (08-13 naqshi): `isEmpty` ham shu
   *   yagona manbadan keladi va bo'sh oraliqda so'rov YUBORILMAYDI. */
  const period = useReportPeriod();
  const report = useAccuracyReport({
    from: period.from,
    to: period.to,
    enabled: !period.isEmpty,
  });

  const data = report.data;

  return (
    /* ⛔ Mazmun atributini blokning O'ZI chiqaradi (§8.1, G-29(b)). */
    <div className="flex flex-col gap-3" data-report-content="accuracy">
      <h2 className="text-lg font-semibold">{t("reports.accuracyTitle")}</h2>

      {report.isPending && !period.isEmpty ? (
        <div aria-busy="true" role="status">
          <span className="sr-only">{t("common.loading")}</span>
          <Skeleton className="h-24" />
        </div>
      ) : null}

      {report.isError ? (
        <p
          className="flex flex-col gap-1 rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
          role="alert"
        >
          <span>{t("errors.loadFailedTitle")}</span>
          <span>{t("errors.loadFailedBody")}</span>
        </p>
      ) : null}

      {data !== undefined ? (
        <>
          <ConfusionMatrix report={data} />

          {data.measured ? null : (
            /*
             * ⛔ NOMLANGAN SABAB — bo'sh joy ham, tire ham, nol ham
             *   EMAS. Sonlar SERVERDAN: `n` — javoblar soni,
             *   chegara — serverning O'Z qarori.
             */
            <p className="rounded-sm bg-surface-muted px-3 py-2 text-sm text-text">
              {t("reports.accuracyNotMeasured", {
                min: data.min_sample,
                n: data.n,
              })}
            </p>
          )}
        </>
      ) : null}

      {/*
       * ⛔ AI-02 — SHARTSIZ (yuqoridagi 4-band). U so'rov holatidan ham
       *   mustaqil: xatoda ham, yuklanishda ham ekranda qoladi.
       */}
      <p className="text-xs text-text-muted">
        {t("reports.accuracyDisclaimer")}
      </p>

      <ExportButton
        kind="accuracy"
        period={{ from: period.from, to: period.to }}
        unavailable={period.isEmpty}
      />
    </div>
  );
}
