"use client";

import { useId } from "react";
import { Target } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useReconciliationCases } from "@/lib/reconciliation-queries";

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
  const cases = useReconciliationCases(day);

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
     * ⛔ Xatoda ⛔ NOL CHIZILMAYDI: nol O'LCHANGAN qiymat ma'nosini
     *   berardi. Nomlangan sabab qo'shni bloklarda allaqachon bor.
     */
    return (
      <Card data-recon-content="hitrate">
        <CardHeader>
          <h2 className="text-lg font-semibold">{t("recon.accuracyTitle")}</h2>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-text-muted">{t("recon.accuracyNone")}</p>
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
