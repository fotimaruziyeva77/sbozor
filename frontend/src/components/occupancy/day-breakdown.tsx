"use client";

import type { ReactNode } from "react";
import {
  CircleCheckBig,
  CircleDashed,
  CircleSlash,
  EyeOff,
  Hand,
} from "lucide-react";
import { useTranslations } from "next-intl";

import { Badge } from "@/components/ui/badge";
import type { BadgeTone } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import type { OccupancyDay } from "@/lib/api-types";

/*
 * =============================================================================
 * ZONA (A) — KUNLIK XULOSA (§11.3, §11.4). AI-05 va AI-06 NING CHIQISHI.
 *
 * ⛔⛔ BESH HISOBLAGICH VA BIRORTASI IKKINCHISIGA QO'SHILMAYDI.
 *
 *     `Band` · `Bo'sh` · `Ko'rilmagani uchun bo'sh` (D-19) ·
 *     `Qamrov yo'q` (D-22) · `Nazoratchi tasdig'i bilan` (KESISHUVCHI).
 *
 *     `Ko'rilmagani uchun bo'sh` `Bo'sh` ga qo'shilsa, «nazoratchi
 *     ulgurmadi» degan YAGONA signal yo'qolardi va bozor jimgina pul
 *     yo'qotardi. `Qamrov yo'q` qo'shilsa, aniqlik hisoboti ham jimgina
 *     noto'g'ri bo'lardi — u rasta haqida MA'LUMOT YO'Q, u bo'sh EMAS.
 *
 * ⛔ BESHALASI HAM DOIM RENDER BO'LADI — NOL BO'LGANDA HAM.
 *
 *    Nol qiymatlilarni tashlab yuboradigan shart bu yerda YO'Q va
 *    qo'shilmaydi (3 va 4-fazadagi qoidaning aynan takrori,
 *    `snapshots/day-summary.tsx:27-40`). Nol — NATIJA, uning yo'qligi
 *    emas: «bugun hech kim ko'rilmadi» bilan «hisoblagich ishlamayapti»
 *    bir xil ko'rinmasligi kerak.
 *
 * ⛔ FOIZ QO'YILMAYDI. `186 / 300` aniqroq va YAXLITLANMAYDI; ulushga
 *    aylantirilgan son to'rtta ko'rilmagan rastani ko'zdan yashirardi.
 *    Shu sababdan bu faylda foiz belgisi UMUMAN uchramaydi va uni
 *    qo'shish `day-breakdown.test.tsx` ni qizartiradi.
 *
 * ⛔ YIG'INDI SERVERDAN KELADI (`summary.stalls`) va KLIENTDA QAYTA
 *    JAMLANMAYDI (05-12, 3-ochiq band). Ikki mustaqil yig'indi bir kun
 *    ajralib ketardi va nosozlik ENG YOMON shaklda ko'rinardi: ikkala son
 *    ham xatosiz. Sarlavhadagi «Rasta N ta» aynan shuning uchun bor —
 *    nomuvofiqlik darhol KO'RINADI va test uni DOM'dan o'lchaydi.
 *
 * ⚠ `role="status"`, `alert` EMAS (§11.4): bu HISOBOT, ogohlantirish
 *   emas. `alert` uni har sahifa yuklanishida shoshilinch xabar
 *   sifatida o'qitardi.
 *
 * ⚠ SLOTLARARO AGREGATSIYA BU YERDA YO'Q VA BO'LMAYDI HAM (§16.1).
 *   Bu blok «kun davomida kamida bir marta band ko'rindi» deydi,
 *   «pattaga tushadi» DEMAYDI — `occupancy.notBillingYet` shuni ochiq
 *   aytadi. Aks holda direktor bu raqamni kunlik daromad deb o'qib,
 *   6-faza kelganda IKKI XIL son ko'rardi.
 * =============================================================================
 */

type CounterView = {
  Icon: typeof CircleCheckBig;
  /** ⚠ Kalitlar ITTIFOQ sifatida: `useTranslations()` ularni sxemadan chiqaradi. */
  labelKey:
    | "occupancy.occupied"
    | "occupancy.empty"
    | "occupancy.defaultEmpty"
    | "occupancy.noCoverage"
    | "occupancy.humanConfirmed";
  tone: BadgeTone;
  /** ⚠ `false` — KESISHUVCHI o'lcham, ya'ni yig'indiga KIRMAYDI. */
  exclusive: boolean;
  value: (summary: OccupancyDay) => number;
};

/**
 * Besh hisoblagich — TARTIB VA TARKIB QAT'IY (§11.4 eskizi).
 *
 * ⚠ Ro'yxat SHARTSIZ o'qiladi: bu yerda tanlash bosqichi YO'Q va
 *   bo'lmaydi ham. Ikonka va tone `§10.4` reyestridan olinadi — rang
 *   YAGONA signal emas (WCAG 1.4.1), har badge MATN ham tashiydi.
 *
 * ⛔ `default_empty` va `empty` TURLI `tone` oladi va bu MUZOKARASIZ:
 *    ikkalasi ham hisob-kitobda «bo'sh» ga olib keladi, lekin ma'nosi
 *    qarama-qarshi — biri O'LCHOV, ikkinchisi O'LCHOVNING YO'QLIGI.
 */
export const OCCUPANCY_COUNTERS: readonly CounterView[] = [
  {
    Icon: CircleCheckBig,
    labelKey: "occupancy.occupied",
    tone: "success",
    exclusive: true,
    value: (summary) => summary.occupied,
  },
  {
    Icon: CircleDashed,
    labelKey: "occupancy.empty",
    tone: "muted",
    exclusive: true,
    value: (summary) => summary.empty,
  },
  {
    Icon: EyeOff,
    labelKey: "occupancy.defaultEmpty",
    tone: "warning",
    exclusive: true,
    value: (summary) => summary.default_empty,
  },
  {
    Icon: CircleSlash,
    labelKey: "occupancy.noCoverage",
    tone: "neutral",
    exclusive: true,
    value: (summary) => summary.no_coverage,
  },
  {
    Icon: Hand,
    labelKey: "occupancy.humanConfirmed",
    tone: "accent",
    exclusive: false,
    value: (summary) => summary.human_confirmed,
  },
];

export function DayBreakdown({
  canReview,
  onGoToReview,
  summary,
}: {
  /** `occupancy_review` huquqi — D-19 jumlasining amali shunga bog'liq. */
  canReview: boolean;
  onGoToReview: ReactNode;
  summary: OccupancyDay;
}) {
  const t = useTranslations();

  return (
    <Card>
      <CardContent className="flex flex-col gap-3 pt-5">
        <div className="flex flex-col gap-3" role="status">
          <p className="text-lg font-semibold">
            <span className="tabular-nums">
              {t("occupancy.stallCount", { count: summary.stalls })}
            </span>
          </p>

          {/*
           * ⛔ BU RO'YXATDA TANLASH BOSQICHI YO'Q. Har qanday shart —
           *    «nolmaslarini ko'rsatish», «faqat muammolilarini
           *    ko'rsatish» — D-19 va D-22 ning UI isbotini o'ldiradi.
           */}
          <dl className="flex flex-wrap gap-x-4 gap-y-2">
            {OCCUPANCY_COUNTERS.map((counter) => (
              <Counter
                icon={<counter.Icon aria-hidden="true" className="size-3" />}
                key={counter.labelKey}
                label={t(counter.labelKey)}
                title={
                  counter.exclusive ? undefined : t("occupancy.humanConfirmedWhy")
                }
                tone={counter.tone}
                value={counter.value(summary)}
              />
            ))}
          </dl>

          {/*
           * ⛔ D-19 NING MAJBURIY JUMLASI — hisoblagichdan MUSTAQIL da'vo.
           *
           *    Hisoblagichning o'zi allaqachon ko'rinadi; bu jumla uni
           *    SO'Z bilan takrorlaydi va OQIBATINI aytadi («patta
           *    yozilmadi»), keyin esa keyingi qadamni beradi. Ikkalasi bir
           *    shartga bog'lansa, biri ikkinchisining testini
           *    qizartirmasdi (`day-summary.tsx:243-249` qoidasi).
           */}
          {summary.default_empty > 0 ? (
            <div className="flex flex-wrap items-center gap-2 rounded-md bg-warning/20 px-3 py-2 text-text">
              <p className="text-sm">
                {t("occupancy.defaultEmptyWhy", { count: summary.default_empty })}
              </p>
              {canReview ? onGoToReview : null}
            </div>
          ) : null}

          {/*
           * ⛔ 6-FAZA BILAN CHALKASHISHNING YAGONA TO'SIG'I (T-05-72).
           *    Jumla SHARTSIZ: u kunning natijasiga emas, RAQAMNING
           *    MA'NOSIGA tegishli.
           */}
          <p className="text-xs text-text-muted">{t("occupancy.notBillingYet")}</p>
        </div>

        {/*
         * ⛔ QAMROVSIZLIKNING IZOHI HAM SHARTSIZ va u D-22 ni MATN
         *    darajasida ushlab turadi (G-15 aynan shu kalitni
         *    skanerlaydi): qamrovsiz rasta «bo'sh» EMAS.
         */}
        <p className="text-xs text-text-muted">{t("occupancy.noCoverageWhy")}</p>
      </CardContent>
    </Card>
  );
}

/**
 * Bitta hisoblagich — raqam va yorliq DASTURIY jihatdan bog'langan.
 *
 * ⚠ VIZUAL TARTIB `order-*` BILAN (`day-summary.tsx:275-283` naqshi):
 *   razmetkada `<dt>` `<dd>` dan OLDIN turadi (HTML `<dl>` talabi),
 *   ekranda esa raqam yorliqdan oldin ko'rinadi. Skrinrider
 *   «Ko'rilmagani uchun bo'sh: 4» deb eshitadi — «4» hech qachon yolg'iz
 *   kelmaydi.
 */
function Counter({
  icon,
  label,
  title,
  tone,
  value,
}: {
  icon: ReactNode;
  label: string;
  title?: string;
  tone: BadgeTone;
  value: number;
}) {
  return (
    <div className="flex items-center gap-x-2" title={title}>
      <dt className="order-2 text-xs">{label}</dt>
      <dd className="order-1 m-0">
        <Badge className="min-w-10 justify-center gap-1 tabular-nums" tone={tone}>
          {icon}
          {value}
        </Badge>
      </dd>
    </div>
  );
}
