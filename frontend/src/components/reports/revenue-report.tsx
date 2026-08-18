"use client";

import { useId } from "react";
import { useFormatter, useLocale, useTranslations } from "next-intl";

import { useReportPeriod } from "@/components/reports/period-picker";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import type { RevenueReportRow } from "@/lib/api-types";
import { formatBusinessDay } from "@/lib/format-day";
import { useRevenueReport } from "@/lib/report-queries";

/*
 * =============================================================================
 * TUSHUM HISOBOTI — ⛔ DAVR SERVERNIKI, YIG'INDI SERVERNIKI (§8.2, §8.6, §8.7).
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 1. EKRANDAGI DAVR — JAVOBDAN, `nuqs` HOLATIDAN EMAS (§8.7, G-39(a)).
 * -----------------------------------------------------------------------
 * Server so'ralgan davrni ⛔ QISQARTIRISHI mumkin: maksimum kecha,
 * ma'lumotning boshlanish sanasi, qator chegarasi. So'ralgan davrni
 * chizish «men oktyabrni so'radim, oktyabr ko'rsatildi» degan
 * ⛔ YOLG'ON TASDIQ berardi, holbuki javob sentyabr 15 dan boshlangan
 * bo'lishi mumkin.
 *
 * ⛔ Bu ekranda tuzatiladigan, FAYLDA esa TARQALADIGAN xato: direktor
 *    raqamni `.xlsx` qilib yuklab oladi, chop etadi, yig'ilishga olib
 *    boradi va varaqdagi davr bilan raqam BOSHQA-BOSHQA savolga javob
 *    beradi. Ekrandagi noto'g'ri son tuzatiladi; chop etilgani esa
 *    imzolanadi.
 *
 * ⚠ Bu `confusion-matrix.tsx` ning BUGUNGI xulqi (u ham davrni
 *   `report.from_date`/`report.to_date` dan chizadi) va u shu bilan
 *   uchala hisobotga TARQATILADI — ikkinchi konvensiya tug'ilmaydi.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 2. YIG'INDI KLIENTDA HISOBLANMAYDI (D-03, G-42(b)).
 * -----------------------------------------------------------------------
 * Qatorlar ustidan yurib jamlash ⛔ YOZILMAYDI — server
 * `total_collected_soum` va `total_charged_soum` ni O'ZI beradi.
 *
 * ⛔ Sabab 05-14 darsi: klientdagi qayta hisob ⛔ XATO BO'LIB EMAS,
 *    IKKINCHI JAVOB bo'lib chiqadi. Uchta mustaqil mexanizm ikki sonni
 *    ajratadi va uchalasi ham «arifmetik jihatdan to'g'ri» qoladi:
 *      • yaxlitlash — server butun so'mda, klient boshqa yo'lda;
 *      • SAHIFALASH — ekranda 50 qator, davrda 45 000 (§8.6);
 *      • filtr — serverdagi tuzatish/kredit taqsimoti qoidalari.
 *    Ya'ni ekranda ikki xil «davr tushumi» paydo bo'lardi va qaysi biri
 *    hujjat ekani ⛔ NOANIQ bo'lib qolardi.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 3. IKKI SANA USTUNI — IKKI XIL SAVOL (Pitfall 14).
 * -----------------------------------------------------------------------
 * «To'langan» — pul QACHON yig'ildi (`payments.business_date`);
 * «Hisoblangan» — QAYSI kunning pattasi (`daily_charges.service_date`).
 * Kassir bugun kechagi qarzni to'laydi, ya'ni ular ⛔ BIR XIL EMAS.
 * Bittasini tanlab «tushum» deb atash direktorga ⛔ NOTO'G'RI SAVOLGA
 * javob berardi — shuning uchun ikkalasi ham chiziladi va ⛔ USTUN
 * SARLAVHASINING O'ZI farqni AYTADI (`*Hint` kalitlari, uchala tilda).
 *
 * -----------------------------------------------------------------------
 * ⛔ 4. SAHIFADA AYNAN BITTA Display — DAVR TUSHUMI (§7.1, §7.2).
 * -----------------------------------------------------------------------
 * Sahifada o'nlab raqam bo'ladi. Har blokning yig'indisi eng katta
 * o'lchamni olsa, ⛔ TO'RTTA TENG KATTA raqam bir-biri bilan
 * raqobatlashardi va direktor «eng muhimi qaysi?» savoliga javob
 * TOPMASDI. RECON-04 ning birinchi jumlasi — davr tushumi, ya'ni Display
 * AYNAN unga tegishli. Qolgan hamma raqam Body.
 *
 * -----------------------------------------------------------------------
 * ⛔ 5. MAXRAJ JUMLASI MAJBURIY (§8.6).
 * -----------------------------------------------------------------------
 * «{shown} qatordan {total} tasi» bo'lmasa, direktor ekrandagi 50 qatorni
 * ⛔ BUTUN DAVR deb o'qirdi. Yig'indi esa butun davrniki — ya'ni son
 * bilan ro'yxat JIMGINA ajralardi. Shuning uchun yig'indi `aria-describedby`
 * orqali ⛔ IKKALA jumlaga (davr VA maxraj) bog'lanadi: skrinrider
 * foydalanuvchisi ham sonni yolg'iz eshitmaydi.
 * =============================================================================
 */

export function RevenueReport() {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();

  /*
   * ⚠ DAVR TANLOVI HOOKDAN, PROPDAN EMAS (08-09 kontrakti): tanlagichning
   *   O'ZI sahifada AYNAN BIR MARTA chiziladi, bloklar esa oraliqni shu
   *   yagona manbadan o'qiydi. Ikkinchi prop zanjiri sahifa bilan blok
   *   orasida uchinchi haqiqat manbai bo'lardi.
   *
   * ⛔ `isEmpty` HURMAT QILINADI: bo'sh oraliqda so'rov yuborilsa server
   *    `400` qaytarardi va ekranda MAHSULOT QARORI (§14.7 bo'sh holat 5)
   *    o'rniga XATO ko'rinardi.
   */
  const period = useReportPeriod();
  const report = useRevenueReport(
    { from: period.from, to: period.to },
    { enabled: !period.isEmpty },
  );

  const periodId = useId();
  const rowsShownId = useId();

  const data = report.data;

  return (
    /*
     * ⛔ MAZMUN ATRIBUTINI RO'YXATNING O'ZI CHIQARADI, SAHIFA EMAS
     *   (§8.1, 07 G-29(b) mexanikasi). Sabab O'LCHANGAN: faqat blok
     *   atributlarining to'plamini tekshiradigan darvoza ⛔ BO'SH
     *   O'RAMNI MUKAMMAL o'tkazardi — butun yuza chizilmagan holda ham
     *   darvoza yashil qaytardi. Atribut ENG TASHQI elementda va HAR
     *   holatda: yuklanishda ham, xatoda ham.
     */
    <div className="flex flex-col gap-3" data-report-content="revenue">
      <h2 className="text-lg font-semibold">{t("reports.revenueTitle")}</h2>

      {report.isPending && !period.isEmpty ? (
        <div aria-busy="true" role="status">
          <span className="sr-only">{t("common.loading")}</span>
          <Skeleton className="h-24" />
        </div>
      ) : null}

      {report.isError ? (
        /*
         * ⛔ YIQILGAN SO'ROV NOL BO'LIB CHIZILMAYDI (D-10, WR-05 sinfi):
         *   bo'sh jadval yoki «0 so'm» direktorga «bu davrda tushum
         *   yo'q» degan YOLG'ON faktni berardi. Xato NOMLANADI va
         *   keyingi qadam bilan birga keladi (D-02).
         */
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
          <dl className="flex flex-col gap-1">
            <div className="flex flex-wrap items-baseline gap-x-6 gap-y-2">
              <div className="flex flex-col gap-1">
                <dt className="text-xs text-text-muted">
                  {t("reports.revenueTotal")}
                </dt>
                {/*
                 * ⛔ SAHIFADAGI YAGONA Display (§7.2) va u ⛔ YOLG'IZ
                 *   KELMAYDI: `aria-describedby` uni davr jumlasiga VA
                 *   maxraj jumlasiga bog'laydi (§15). Ko'z bilan ular
                 *   yonma-yon turadi, skrinriderda esa bu bog'lanishsiz
                 *   son kontekstsiz o'qilardi.
                 */}
                <dd
                  aria-describedby={`${periodId} ${rowsShownId}`}
                  className="m-0 font-mono text-2xl font-semibold tabular-nums"
                >
                  {format.number(data.total_collected_soum)}{" "}
                  <span className="font-sans text-sm font-normal text-text-muted">
                    {t("reports.amountUnit")}
                  </span>
                </dd>
              </div>

              <div className="flex flex-col gap-1">
                {/*
                 * ⛔ HISOBLANGAN YIG'INDI HAM CHIZILADI, LEKIN Body
                 *   o'lchamida: Pitfall 14 ikkala ta'rifni ham talab
                 *   qiladi, §7.2 esa ikkinchi Display ni TAQIQLAYDI.
                 */}
                <dt className="text-xs text-text-muted">
                  {t("reports.revenueCharged")}
                </dt>
                <dd className="m-0 font-mono text-sm font-semibold tabular-nums">
                  {format.number(data.total_charged_soum)}{" "}
                  <span className="font-sans font-normal text-text-muted">
                    {t("reports.amountUnit")}
                  </span>
                </dd>
              </div>
            </div>

            {/*
             * ⛔ DAVR JUMLASI ⛔ JAVOBDAN (§8.7). `period.from`/`period.to`
             *   BU YERDA ISHLATILMAYDI va bu qoidaning butun mazmuni.
             */}
            <p className="text-xs text-text-muted" id={periodId}>
              {t("reports.periodShown", {
                /* ⛔ XOM ISO EMAS — bu qator ekranda «2026-07-19 — 2026-08-17»
                 *    bo'lib chiqardi, holbuki yonidagi jadval sanalari
                 *    «19-iyul, 2026» edi. Bir sahifada ikki xil sana yo'li. */
                from: formatBusinessDay(format, data.from_date, locale),
                to: formatBusinessDay(format, data.to_date, locale),
              })}
            </p>

            <p className="text-xs text-text-muted" id={rowsShownId}>
              {t("reports.rowsShown", {
                shown: data.shown_count,
                total: data.row_count,
              })}
            </p>
          </dl>

          {data.rows.length === 0 ? (
            /*
             * ⛔ BO'SH DAVR — NOMLANGAN HOLAT, sarlavhalari bor bo'sh
             *   jadval EMAS: bo'sh jadval «ma'lumot bor, hammasi nol»
             *   degan taassurot berardi. ⛔ `action` YO'Q (§14.7): davrni
             *   o'zgartirish keyingi QADAM emas, u allaqachon ekranda.
             */
            <EmptyState
              description={t("reports.emptyRevenueHint", {
                from: data.from_date,
                to: data.to_date,
              })}
              title={t("reports.emptyRevenue")}
            />
          ) : (
            <div className="overflow-x-auto">
              {/*
               * ⛔ NATIVE `<table>` + `<caption class="sr-only">` +
               *   `<th scope>` (§15). ⛔ ARIA panjara roli YOZILMAYDI
               *   [MEROS: 04-11 darsi]: u native semantikani ALMASHTIRIB,
               *   sarlavha–katak bog'lanishini qo'lda tiklashni talab
               *   qilardi va skrinrider klaviatura modelini o'zgartirardi.
               */}
              <table className="w-full border-collapse text-sm">
                <caption className="sr-only">
                  {t("reports.revenueTitle")}
                </caption>
                <thead>
                  <tr className="border-b border-border text-left text-xs text-text-muted">
                    <th className="p-3 font-normal" scope="col">
                      {t("reports.dateColumn")}
                    </th>
                    {/*
                     * ⛔ SARLAVHANING O'ZI FARQNI AYTADI (Pitfall 14):
                     *   «hisoblangan» patta kuni bo'yicha, «to'langan»
                     *   to'lov kuni bo'yicha. Izohsiz ikki ustun bir
                     *   savolning ikki javobi bo'lib o'qilardi.
                     */}
                    <th className="p-3 font-normal" scope="col">
                      {t("reports.revenueCharged")}
                      <span className="block">
                        {t("reports.revenueChargedHint")}
                      </span>
                    </th>
                    <th className="p-3 font-normal" scope="col">
                      {t("reports.revenuePaid")}
                      <span className="block">
                        {t("reports.revenuePaidHint")}
                      </span>
                    </th>
                    <th className="p-3 font-normal" scope="col">
                      {t("reports.revenueDiff")}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {data.rows.map((row) => (
                    <RevenueRow key={row.business_date} row={row} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      ) : null}
    </div>
  );
}

/**
 * Bitta biznes-kun — ⛔ UCHALA SON HAM SERVERDAN KELGANICHA.
 *
 * ⛔ `diff_soum` BU YERDA HAM AYIRILMAYDI: u javobning O'Z maydoni.
 *    Klient faqat ⛔ ISHORASINI o'qiydi (rang kanali uchun) va
 *    formatlaydi.
 */
function RevenueRow({ row }: { row: RevenueReportRow }) {
  const format = useFormatter();
  const locale = useLocale();

  /*
   * ⛔ MANFIY — QIZIL, MUSBAT — ODDIY MATN RANGI, ⛔ YASHIL EMAS (§8.2).
   *
   * Ortiqcha to'lov ⛔ YAXSHILIK EMAS: u ham tekshiriladigan holat
   * (kassirning xatosi, ikki marta yozilgan to'lov, noto'g'ri rasta).
   * Yashil bezak uni «hammasi joyida» deb ko'rsatardi va u ⛔ HECH
   * QACHON tekshirilmasdi.
   *
   * ⚠ RANG YOLG'IZ SIGNAL EMAS (WCAG 1.4.1, §13.4): ikkinchi kanal —
   *   formatlagichning MINUS belgisi, uchinchisi — «Farq» ustun
   *   sarlavhasi.
   */
  const diffClass = row.diff_soum < 0 ? "text-danger-text" : "text-text";

  return (
    /*
     * Qator hover foni (§12.8). `text-danger-text` MATN rangi — fon emas,
     * hover bg u bilan to'qnashmaydi (kontrast juftligi G-motion-5
     * reyestrida `*-text`/tint sifatida o'lchangan).
     */
    <tr className="border-b border-border transition-colors last:border-b-0 hover:bg-surface-muted">
      <td className="p-3">{formatBusinessDay(format, row.business_date, locale)}</td>
      <td className="p-3 font-mono tabular-nums">
        {format.number(row.charged_soum)}
      </td>
      <td className="p-3 font-mono tabular-nums">
        {format.number(row.collected_soum)}
      </td>
      <td className={`p-3 font-mono tabular-nums ${diffClass}`}>
        {format.number(row.diff_soum)}
      </td>
    </tr>
  );
}
