"use client";

import { useId } from "react";
import { Target } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useReconciliationCases,
  useReconciliationMarketId,
} from "@/lib/reconciliation-queries";

/*
 * =============================================================================
 * E BLOKI — ANIQLIK ULUSHI. ⛔ MAXRAJSIZ FOIZ — YOLG'ON.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 1. FOIZ KO'RINSA, TO'RT SANOQ HAM SHU BLOKDA KO'RINADI
 * -----------------------------------------------------------------------
 * Nisbat — `asosli / (asosli + asossiz)`. Maxrajga `yangi` va
 * `ko'rilmoqda` ⛔ KIRMAYDI: hali ko'rilmagan qator metrikani
 * pasaytirardi, ya'ni ko'rsatkich o'z JARAYONINI emas, uning
 * KECHIKISHINI o'lchardi.
 *
 * ⛔ Maxrajsiz «68 %» ni direktor «100 tadan 68 tasi» deb o'qiydi. Bu
 *    ⛔ KO'RINMAYDIGAN YOLG'ON: raqam rost, xulosa noto'g'ri. Shuning
 *    uchun maxraj jumlasi ham, istisno jumlasi ham ⛔ MAJBURIY va
 *    ikkalasi foizga `aria-describedby` bilan BOG'LANADI — skrinrider
 *    foydalanuvchisi ham foizni maxrajsiz eshitmaydi.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 2. MAXRAJ NOL BO'LGANDA FOIZ ⛔ UMUMAN CHIZILMAYDI
 * -----------------------------------------------------------------------
 * `0/0` — ⛔ ANIQLANMAGAN, «nol foiz» ⛔ EMAS. `0 %` «biz tekshirdik va
 * hech biri asosli chiqmadi» degan ⛔ TESKARI XULOSANI berardi —
 * holbuki hech nima hali tekshirilmagan.
 *
 * ⛔ Shuning uchun bu holatda foiz BELGISI ham DOM'da bo'lmaydi va
 *    `0`, `NaN`, `∞`, `—%` kabi qiymatlar HECH QACHON chizilmaydi.
 *    O'rniga ⛔ NOMLANGAN SABAB: «Hali hal qilingan nomuvofiqlik yo'q»
 *    + navbatda nechtasi turgani.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 3. NISBAT SAQLANMAYDI — NA MAYDON, NA O'ZGARUVCHI NOMIDA
 * -----------------------------------------------------------------------
 * U ⛔ RENDER PAYTIDA to'rt sanoqdan hisoblanadi va ⛔ IKKINCHI SO'ROV
 * QILINMAYDI: sanoqlar navbat envelope'ida allaqachon keladi. Serverdagi
 * davr kesimidagi marshrut bu ekranda ⛔ ISHLATILMAYDI — u BOSHQA kesim
 * (davr, kun emas) va ikki manba ekranda ikki xil raqam bo'lardi.
 *
 * ⚠ Saqlangan hosila nomining O'ZI ham bu katalogda taqiqlangan va
 *   uning yo'qligi mexanik skan bilan o'lchanadi. Shuning uchun mahalliy
 *   nom — `ratio`.
 *
 * -----------------------------------------------------------------------
 * ⛔ 4. QO'LDA FOIZ HISOBLANMAYDI
 * -----------------------------------------------------------------------
 * Foiz `useFormatter().number(v, {style: "percent"})` bilan chiziladi:
 * `%` belgisining JOYI va ajratkich ⛔ LOCALE'GA BOG'LIQ va uni qo'lda
 * yopishtirish uchala tilning birida noto'g'ri chiqardi.
 *
 * ⚠ «AI aniqligi» BILAN ADASHTIRMASLIK uchun matnda «nomuvofiqlik»
 *   so'zi turadi: bu ko'rsatkich NAVBATNING aniqligi, model aniqligi
 *   EMAS.
 * =============================================================================
 */

export function HitRateCard({ day }: { day: string }) {
  const t = useTranslations();
  const format = useFormatter();
  const denominatorId = useId();
  const excludedId = useId();

  /*
   * ⛔ AYNAN O'SHA KALIT — navbat bloki bilan BIR XIL. TanStack ikkala
   *   iste'molchini BITTA so'rovga birlashtiradi, ya'ni foiz va navbat
   *   AYNAN BIR LAHZANI ko'rsatadi.
   *
   * ⛔⛔ SANOQ ⛔ BIRINCHI SAHIFADAN (`counts`) — VA BU ARIFMETIKANI
   *    O'ZGARTIRMAYDI. Server kontrakti bo'yicha sanoq filtrdan ham,
   *    sahifadan ham MUSTAQIL: u HAR javobda BUTUN kunning soni. Ularni
   *    sahifalar bo'ylab YIG'ISH maxrajni har «Yana yuklash» bosilganda
   *    ⛔ IKKILANTIRARDI va foiz o'zi o'lchayotgan narsani emas, nechta
   *    sahifa ochilganini ko'rsatardi.
   */
  const marketId = useReconciliationMarketId();
  const cases = useReconciliationCases(day, { enabled: marketId !== null });

  /*
   * ⛔⛔ BOZORSIZ SESSIYA — ⛔ CHEKSIZ SKELET EMAS (IN-08).
   *
   * TanStack v5 da O'CHIRILGAN so'rov `isPending` HOLATIDA QOLADI, ya'ni
   * quyidagi shox bozorsiz sessiyada ⛔ ABADIY yugurardi. `HeadlineCard`
   * aynan shu holatni ochiq qo'riqlaydi — bu karta esa yo'q edi.
   *
   * ⛔ FOIZ BU SHOXDA UMUMAN HISOBLANMAYDI: o'lchov hali BOSHLANMAGAN,
   *    ya'ni `0 %` ham, `—%` ham YOLG'ON bo'lardi (fayl izohining
   *    2-bandi bilan AYNI sinf).
   */
  if (marketId === null) {
    return (
      <Card data-recon-content="hitrate">
        <CardHeader>
          <h2 className="text-lg font-semibold">{t("recon.accuracyTitle")}</h2>
        </CardHeader>
        <CardContent className="flex flex-col gap-1">
          <p className="text-sm">{t("recon.marketMissing")}</p>
          <p className="text-xs text-text-muted">
            {t("recon.marketMissingHint")}
          </p>
        </CardContent>
      </Card>
    );
  }

  if (cases.isPending) {
    return (
      <Card data-recon-content="hitrate">
        <CardHeader>
          <h2 className="text-lg font-semibold">{t("recon.accuracyTitle")}</h2>
        </CardHeader>
        <CardContent>
          <div aria-busy="true" role="status">
            <span className="sr-only">{t("common.loading")}</span>
            <Skeleton className="h-16" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (cases.counts === undefined) {
    /*
     * =====================================================================
     * ⛔⛔ SO'ROV YIQILDI — ⛔ O'LCHANGAN FAKT DA'VO QILINMAYDI (WR-05).
     *
     * Bu shox bir muddat `recon.accuracyNone` ni chizardi, matni esa
     * «Hali hal qilingan nomuvofiqlik yo'q». Bu ⛔ O'LCHANGAN QIYMAT
     * DA'VOSI, holbuki haqiqat ⛔ «o'lchov UMUMAN kelmadi» — va
     * ikkalasining xulosasi ⛔ QARAMA-QARSHI: birinchisi direktorni
     * «navbat toza» deb XOTIRJAM qilardi.
     *
     * Bu ⛔ AYNAN fayl izohining 2-bandidagi sinf («`0 %` ... TESKARI
     * XULOSANI berardi — holbuki hech nima hali tekshirilmagan») va
     * 05-14 ning «o'lchanmagan sonning o'rniga NOL yozilmaydi» darsi.
     *
     * ⛔ NOLGA TUSHIRUVCHI ZAXIRA OPERATORLARI (`??` / `||` ning nol
     *    bilan juftligi) ⛔ TAQIQ: ular aynan shu yolg'onning arifmetik
     *    shakli bo'lardi. O'lchandi (08-10 sabotaji): xato shoxi shunday
     *    zaxiraga almashtirilganda ekranda «0 %» paydo bo'ldi va to'rt
     *    darvoza bir vaqtda qizardi.
     *    ⚠ Taqiqlangan shakl bu izohda LITERAL yozilmaydi — nusxa
     *      mexanik skanni o'ziga qarshi qo'yardi (`badge.tsx` konvensiyasi).
     *
     * ⛔ `role="alert"` — VA U BU YERDA QONUNIY: bu ⛔ XATO (§14.9 ning
     *    jonli hududlar reyestri `alert` ni AYNAN xatoga beradi), qo'shni
     *    bloklarning yuklanish platsholderi emas. `role="status"`
     *    darvozasi (G-38) esa AYNAN OLTI joyni qulflagan va bu shox
     *    ularning birortasi EMAS.
     *
     * ⚠ Bandning IKKINCHI yarmi — yangi `accuracy-block` — 08-15 da AYNI
     *   qoida bilan quriladi (G-40(b)): ikkalasi bir sinf.
     * =====================================================================
     */
    return (
      <Card data-recon-content="hitrate">
        <CardHeader>
          <h2 className="text-lg font-semibold">{t("recon.accuracyTitle")}</h2>
        </CardHeader>
        <CardContent>
          <p
            className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
            role="alert"
          >
            {t("errors.loadFailedBody")}
          </p>
        </CardContent>
      </Card>
    );
  }

  const justified = cases.counts.justified_count;
  const unjustified = cases.counts.unjustified_count;
  const resolved = justified + unjustified;
  const pending = cases.counts.new_count + cases.counts.in_review_count;

  return (
    /* ⛔ Atribut ENG TASHQI elementda va HAR holatda — yuklanishda ham. */
    <Card data-recon-content="hitrate">
      <CardHeader>
        <h2 className="flex items-center gap-2 text-lg font-semibold">
          <Target aria-hidden="true" className="size-4" />
          {t("recon.accuracyTitle")}
        </h2>
      </CardHeader>

      <CardContent className="flex flex-col gap-3">
        {resolved === 0 ? (
          /*
           * ⛔ MAXRAJ NOL — FOIZ ELEMENTI UMUMAN CHIZILMAYDI. Bu shox
           *   `0 %` ni «yashiradigan» shart EMAS: foiz shu tarmoqda
           *   HISOBLANMAYDI ham.
           */
          <>
            <p className="text-sm">{t("recon.accuracyNone")}</p>
            <p className="text-xs text-text-muted">
              {t("recon.accuracyNoneHint", { pending })}
            </p>
          </>
        ) : (
          <>
            <p
              aria-describedby={`${denominatorId} ${excludedId}`}
              className="font-mono text-2xl leading-tight font-semibold tracking-tight tabular-nums"
            >
              {format.number(justified / resolved, { style: "percent" })}
            </p>
            {/* ⛔ MAXRAJ JUMLASI — MAJBURIY (yuqoridagi 1-bandga qarang). */}
            <p className="text-sm" id={denominatorId}>
              {t("recon.accuracyBody", { resolved, justified })}
            </p>
            {/* ⛔ ISTISNO JUMLASI — HAM MAJBURIY: yashirin qoida bo'lardi. */}
            <p className="text-xs text-text-muted" id={excludedId}>
              {t("recon.accuracyExcluded", { pending })}
            </p>
          </>
        )}
      </CardContent>
    </Card>
  );
}
