"use client";

import { LockKeyhole } from "lucide-react";
import { useTranslations } from "next-intl";

/*
 * =============================================================================
 * DOIMIY LENTA — UCH KANALNING BIRINCHISI (UI-SPEC §7.6).
 *
 * -----------------------------------------------------------------------
 * ⚠ NIMA UCHUN UMUMAN LENTA KERAK
 * -----------------------------------------------------------------------
 * Ikkala navbat ham tizim javobini javobdan KEYIN ko'rsatadi (§7.1), ya'ni
 * ular KO'RINISHDA BIR XIL bo'lib qoladi va nazoratchi qaysi birida
 * ekanini bilmasligi mumkin. Farqni UCH KANAL yopadi: doimiy lenta +
 * marshrut (`/review/blind`) + `<h1>`. Bittasi yetmaydi — foydalanuvchi
 * manzil qatoriga ham, sarlavhaga ham har band almashganda qaramaydi.
 *
 * -----------------------------------------------------------------------
 * ⛔ RANGI `warning` YOKI `danger` EMAS [QAROR]
 * -----------------------------------------------------------------------
 * Ko'rmasdan tekshirish — NOSOZLIK EMAS, u normal va muhim ish.
 * Ogohlantirish rangi nazoratchida «xato qildimmi?» tuyg'usini
 * tug'dirib, uni SHOSHILTIRARDI — ya'ni rang tanlovi bevosita javob
 * sifatiga ta'sir qilardi. Neytral, lekin OG'IR ko'rinish (qalin chap
 * chegara + qulf ikonkasi) to'g'ri ohangni beradi.
 *
 * ⚠ RANG YAGONA SIGNAL EMAS (WCAG 1.4.1): ikonka (SHAKL) + matn (SO'Z) +
 *   chap chegara (TUZILMA) — uch mustaqil kanal.
 *
 * -----------------------------------------------------------------------
 * ⛔ YOPILMAYDI, YASHIRILMAYDI, SKROLL BILAN KETMAYDI
 * -----------------------------------------------------------------------
 * `sticky top-0`. Yopiladigan lenta birinchi bandda yopilardi va qolgan
 * 29 tasida umuman ko'rinmasdi — ya'ni himoya birinchi bosishdayoq
 * yo'qolardi.
 *
 * ⛔ `role="alert"` OLMAYDI (§13.6). U sahifa yuklanganda MAVJUD
 *    BO'LGAN holat, yangi hodisa emas. `alert` uni har band almashganda
 *    qayta o'qitardi va nazoratchi uni ESHITMAY QO'YARDI — ya'ni
 *    ogohlantirishning kuchi kamayardi. `<h2>` sifatida BIR MARTA
 *    o'qiladi va sarlavha navigatsiyasida topiladi.
 *
 * ⚠ IKKI JUMLA, IKKALASI HAM MAJBURIY (§12.5): birinchisi «nega
 *   boshqacha», ikkinchisi «nima uchun ehtiyot bo'lish kerak». Ikkinchi
 *   jumla G-14(d) ning matn yarmini ham bajaradi — «o'zgartirib
 *   bo'lmaydi» EKRANDA doimiy turadi, javobdan keyin paydo bo'ladigan
 *   xabar emas.
 * =============================================================================
 */

export function BlindBanner({
  answered,
  total,
}: {
  answered: number | null;
  total: number | null;
}) {
  const t = useTranslations();

  return (
    <div className="sticky top-0 z-10 flex items-start justify-between gap-4 border-l-4 border-text bg-surface-muted px-4 py-3">
      <div className="flex items-start gap-3">
        <LockKeyhole aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
        <div className="flex flex-col gap-1">
          <h2 className="text-sm font-semibold">{t("review.blindTitle")}</h2>
          <p className="max-w-prose text-sm">{t("review.blindBanner")}</p>
        </div>
      </div>

      {/*
       * Hisoblagich — FAKT, maqsad emas (`budget-counter.tsx` bilan bir
       * qaror). ⛔ Progress bar bu yerda ham QURILMAYDI.
       *
       * ⚠ SON HALI KELMAGAN BO'LSA QATOR CHIZILMAYDI: `0 / 0` yozib
       *   qo'yish «bugun hech nima yo'q» degan yolg'onni aytardi.
       */}
      {answered === null || total === null ? null : (
        <p className="font-mono text-xs whitespace-nowrap tabular-nums">
          {t("review.blindProgress", { done: answered, total })}
        </p>
      )}
    </div>
  );
}
