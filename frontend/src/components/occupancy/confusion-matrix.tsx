"use client";

import { TriangleAlert } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import type {
  AccuracyReport,
  ProportionIntervalPayload,
} from "@/lib/api-types";

/*
 * =============================================================================
 * ZONA (B) — CHALKASHLIK MATRITSASI (§11.5). AI-04 NING XOLIS CHIQISHI.
 *
 * ⛔⛔ «ANIQLIK» YOLG'IZ KO'RSATKICH SIFATIDA E'LON QILINMAYDI.
 *
 *     05-RESEARCH §C.8.4 ochiq ogohlantiradi: rastalarning 90 % i band
 *     bo'lsa, «har doim band» deydigan SOXTA model 90 % aniqlik oladi.
 *     Shuning uchun uch narsa MAJBURIY va ularsiz raqam chizilmaydi:
 *     matritsaning to'rt xom soni, BAZAVIY BANDLIK ULUSHI va `n`.
 *
 * ⛔⛔ FOIZ BU FAYLDA HISOBLANMAYDI — U SERVERDAN KELADI.
 *
 *     Maxrajlar 05-12 da SPETSIFIKATSIYANING O'Z ISHLANGAN MISOLIDAN
 *     chiqarilgan (tp=401, fp=23, fn=38, tn=150 -> 5,4 % va 8,7 %) va
 *     faqat `fp/(tp+fp)` hamda `fn/(tp+fn)` juftligi o'sha sonlarni
 *     beradi. Ikkalasini `n` ga bo'lish 3,8 % va 6,2 % berardi —
 *     XATOSIZ arifmetika, lekin BOSHQA savolga javob.
 *
 *     Ya'ni klientda qayta hisoblash «xato» sifatida ko'rinmasdi: u
 *     ikkinchi, jimgina boshqacha javob tug'dirardi. Shu sababdan bu
 *     faylda bo'lish amali ham, `lib/wilson.ts` importi ham YO'Q.
 *
 * ⛔ WALD ORALIG'I ISHLATILMAYDI va u umuman hisoblanmaydi: serverdagi
 *    oraliqlar Wilson score bo'yicha (kichik `n` va chetdagi `p` da
 *    to'g'ri qoplama beradi).
 *
 * ⛔ NUQTA BAHO ORALIQSIZ CHIZILMAYDI (`percentView`). Yolg'iz foiz
 *    namuna ko'tara olmaydigan aniqlikni va'da qilardi.
 *
 * ⛔ IKKI XATO TENG EMAS VA MATN SHUNI AYTADI:
 *      «Band deb xato»  -> sotuvchi bilan NIZO xavfi (ishonch);
 *      «Bo'sh deb xato» -> YIG'ILMAGAN patta (pul).
 *    Har biri O'Z jumlasi bilan; ikkalasini bitta jumlaga qo'shish
 *    ularni «xato» degan bir xil narsaga aylantirardi.
 *
 * ⛔ DIAGRAMMA YO'Q va `recharts` BOG'LIQLIK EMAS (§3.5, §16.1).
 *
 * ⛔ DAVR TANLAGICHI HAM, `eval`/`train` FILTRI HAM YO'Q. Hisobot FAQAT
 *    ko'r namunaning `eval` qismidan chiqadi (D-14) va aralashtiruvchi
 *    boshqaruv qurilsa, 70/30 bo'linishining butun ma'nosi yo'qolardi.
 *    Sarlavha buni matn bilan ham aytadi.
 *
 * ⛔⛔ NAZORATCHINING ICHKI MOSLIGI (D-16) BU YERDA YO'Q — na qator, na
 *     «—», na nol. UI-SPEC §11.6 uni so'raydi va o'sha qator ESKIRGAN:
 *     05-11 mexanizm bugungi sxemada IFODALAB BO'LMASLIGINI o'lchagan,
 *     05-12 esa maydonni javobdan butunlay chiqarib tashlagan. Bo'sh
 *     joy ko'rsatish keyingi ijrochini unga son yozishga undardi.
 * =============================================================================
 */

/** Foizga aylantirilgan nisbat — UCHALA chegara ham mavjud bo'lganda. */
export type PercentView = {
  point: number;
  lower: number;
  upper: number;
};

/**
 * Nisbatning ko'rsatiladigan shakli — SOF FUNKSIYA (§S-13).
 *
 * ⛔ QAT'IY QOIDA: uchala maydondan BIRORTASI `null` bo'lsa natija ham
 *    `null`. «Nuqta bor, oraliq yo'q» holati ekranda YOLG'IZ FOIZ bo'lib
 *    ko'rinardi va o'quvchi uni o'lchov aniqligi deb o'qirdi —
 *    `wilson.ts` ning butun mavjud bo'lish sababi aynan shu
 *    («aniqlik 100 %, oraliq 100–100 %» degan yolg'on qat'iylik).
 *
 * ⚠ FUNKSIYA HISOBLAMAYDI, FAQAT MIQYOSNI O'ZGARTIRADI: server 0..1
 *   oralig'ida beradi, ekran esa foizda o'qiydi. Bo'lish amali yo'q,
 *   ya'ni ikkinchi javob tug'ila olmaydi.
 */
export function percentView(
  interval: ProportionIntervalPayload,
): PercentView | null {
  const { point, lower, upper } = interval;
  if (point === null || lower === null || upper === null) return null;
  return { point: point * 100, lower: lower * 100, upper: upper * 100 };
}

export function ConfusionMatrix({ report }: { report: AccuracyReport }) {
  const t = useTranslations();
  const format = useFormatter();

  /** Foiz — BIR XIL aniqlikda, uchala qatorda ham (§9.4). */
  const percent = (value: number): string =>
    format.number(value, {
      maximumFractionDigits: 1,
      minimumFractionDigits: 1,
    });

  const correct = percentView(report.correct);
  const falseOccupied = percentView(report.false_occupied);
  const falseEmpty = percentView(report.false_empty);
  const baseRate = report.base_rate;

  return (
    <Card>
      <CardHeader className="flex flex-col gap-1">
        <h2 className="text-sm font-semibold">{t("occupancy.accuracyTitle")}</h2>
        {/*
         * ⛔ SARLAVHA `queue_kind` NI ANIQ AYTADI: «Ko'rmasdan tekshirish
         *    namunasidan» — ya'ni noaniq navbat javoblari bu raqamga
         *    KIRMAYDI (D-14, SC#4).
         *
         * ⚠ `n` PROZA JUMLASINING ICHIDA va shu sababdan `font-mono`
         *   OLMAYDI (§9.4 ning ro'yxati «ustunlashadigan qiymat» uchun):
         *   bu yerda u hech nima bilan ustunlashmaydi, ya'ni monospace
         *   bezak bo'lardi. Ustunlashadigan sonlar — matritsa kataklari
         *   va uch oraliq — `font-mono` OLADI.
         */}
        <p className="text-xs text-text-muted">
          {t("occupancy.accuracyFrom", {
            from: report.from_date,
            to: report.to_date,
            n: report.n,
          })}
        </p>
      </CardHeader>

      <CardContent className="flex flex-col gap-4">
        {/*
         * ⛔ NAMUNANING HOLATI HAR DOIM KO'RINADI — `measured` DAN
         *    MUSTAQIL va ayniqsa u `false` bo'lganda.
         *
         *    Javobsiz band namunadan CHIQMAYDI (§C.8, 4-dushman): uni
         *    tashlab yuborish qisman bajarilgan auditni TOZA ko'rinishga
         *    keltirardi. «Aniq ayta olmadi» esa matritsadan TASHQARIDA
         *    (O-06) va u xato emas — u kadr sifati haqidagi ma'lumot.
         */}
        <p className="text-xs text-text-muted">
          {t("occupancy.sampleLine", {
            answered: report.answered,
            drawn: report.drawn,
            unanswered: report.unanswered,
            unclear: report.dont_know,
          })}
        </p>

        {report.unanswered > 0 ? (
          <p className="rounded-md bg-warning/20 px-3 py-2 text-xs text-text">
            {t("occupancy.sampleIncomplete", { count: report.unanswered })}
          </p>
        ) : null}

        {report.measured ? (
          <>
            <table className="w-fit border-collapse text-sm">
              <caption className="pb-2 text-left text-xs text-text-muted">
                {t("occupancy.accuracyCaption")}
              </caption>
              <thead>
                <tr>
                  {/* Bo'sh burchak — `<th>` EMAS: u hech nimani nomlamaydi. */}
                  <td />
                  <th
                    className="border border-border px-3 py-2 text-left text-xs font-medium"
                    scope="col"
                  >
                    {t("occupancy.humanSaysOccupied")}
                  </th>
                  <th
                    className="border border-border px-3 py-2 text-left text-xs font-medium"
                    scope="col"
                  >
                    {t("occupancy.humanSaysEmpty")}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <th
                    className="border border-border px-3 py-2 text-left text-xs font-medium"
                    scope="row"
                  >
                    {t("occupancy.systemSaysOccupied")}
                  </th>
                  <Cell value={report.matrix.true_occupied} />
                  {/*
                   * ⚠ RANG YAGONA SIGNAL EMAS (WCAG 1.4.1, §10.4): katak
                   *   `⚠` ikonkasini HAM oladi va uning oqibati pastda
                   *   O'Z JUMLASI bilan yozilgan.
                   */}
                  <Cell
                    tone="bg-danger/12 text-danger-text"
                    value={report.matrix.false_occupied}
                    warn
                  />
                </tr>
                <tr>
                  <th
                    className="border border-border px-3 py-2 text-left text-xs font-medium"
                    scope="row"
                  >
                    {t("occupancy.systemSaysEmpty")}
                  </th>
                  <Cell
                    tone="bg-warning/20 text-text"
                    value={report.matrix.false_empty}
                    warn
                  />
                  <Cell value={report.matrix.true_empty} />
                </tr>
              </tbody>
            </table>

            <div className="flex flex-col gap-2">
              {correct === null ? null : (
                <p className="font-mono text-sm tabular-nums">
                  {t("occupancy.correctShare", {
                    high: percent(correct.upper),
                    low: percent(correct.lower),
                    value: percent(correct.point),
                  })}
                </p>
              )}

              {falseOccupied === null ? null : (
                <div className="flex flex-col">
                  <p className="font-mono text-sm tabular-nums">
                    {t("occupancy.falseOccupied", {
                      high: percent(falseOccupied.upper),
                      low: percent(falseOccupied.lower),
                      value: percent(falseOccupied.point),
                    })}
                  </p>
                  <p className="text-xs text-text-muted">
                    {t("occupancy.falseOccupiedWhy")}
                  </p>
                </div>
              )}

              {falseEmpty === null ? null : (
                <div className="flex flex-col">
                  <p className="font-mono text-sm tabular-nums">
                    {t("occupancy.falseEmpty", {
                      high: percent(falseEmpty.upper),
                      low: percent(falseEmpty.lower),
                      value: percent(falseEmpty.point),
                    })}
                  </p>
                  <p className="text-xs text-text-muted">
                    {t("occupancy.falseEmptyWhy")}
                  </p>
                </div>
              )}

              {/*
               * ⛔ BAZAVIY ULUSH MAJBURIY: usiz «90 %» raqami
               *    O'QILMAYDI — o'quvchi uni «har doim band» deydigan
               *    soxta modeldan ajrata olmasdi.
               */}
              {baseRate === null ? null : (
                <p className="font-mono text-sm tabular-nums">
                  {t("occupancy.baseRate", { value: percent(baseRate * 100) })}
                </p>
              )}
            </div>
          </>
        ) : (
          /*
           * ⛔ O-4 — MATRITSA O'RNIGA MATN VA BIRORTA FOIZ CHIZILMAYDI.
           *
           *    Qaror SERVERNIKI (`measured`) va chegara ham serverdan
           *    (`min_sample`): klientda `n >= 20` deb qayta yozish
           *    ikkinchi chegara tug'dirardi va ular bir kun ajralib
           *    ketardi (05-12, 2-ochiq band).
           */
          <p className="rounded-md bg-surface-muted px-3 py-2 text-sm text-text">
            {t("occupancy.notMeasuredYet", {
              min: report.min_sample,
              n: report.n,
            })}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

/**
 * Matritsaning bitta katagi — XOM SON, `font-mono` (§9.4).
 *
 * ⚠ Ustunlar TIK solishtiriladi va bu jadvalning butun ma'nosi; shuning
 *   uchun bu yerda monospace bezak emas, FUNKSIYA.
 */
function Cell({
  tone,
  value,
  warn = false,
}: {
  tone?: string;
  value: number;
  warn?: boolean;
}) {
  return (
    <td
      className={`border border-border px-3 py-2 text-right font-mono tabular-nums ${tone ?? ""}`}
    >
      <span className="inline-flex items-center gap-1">
        {warn ? <TriangleAlert aria-hidden="true" className="size-3" /> : null}
        {value}
      </span>
    </td>
  );
}
