"use client";

import { useFormatter, useLocale, useTranslations } from "next-intl";

import { ACTIVATION_STEP } from "@/components/wizard/wizard-steps";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Link } from "@/i18n/navigation";
import { formatAmount } from "@/lib/format-number";
import { useSetupStatusQuery } from "@/lib/market-queries";
import { useUsersQuery } from "@/lib/queries";

/*
 * =============================================================================
 * BOZOR HOLATI + TO'RT HISOBLAGICH — PLATFORMA ADMINI BOSH EKRANI
 * (Topilma №H).
 *
 * Bosh ekran platforma adminiga bozor TIRIKMI yoki QORALAMAMI — aytmasdi.
 * Bu kartaning butun vazifasi shu savolga javob berish va qoralama
 * holatida keyingi qadamni KO'RSATISH.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 1. YANGI ENDPOINT YOZILMAYDI [QAROR]
 * -----------------------------------------------------------------------
 * To'rttala son MAVJUD ikki so'rovdan keladi:
 *   * `GET /markets/{id}/setup-status` -> `stalls`, `vendors`, `cameras`
 *     (u `MARKET_DATA_VIEW` talab qiladi va FAOL bozorda ham ishlaydi —
 *     `markets.py` da `is_active` sharti YO'Q);
 *   * `GET /users` -> `items.length`.
 *
 * Yangi «dashboard summary» endpointi uchinchi haqiqat manbai bo'lardi
 * va u bir kun ustaning sanoqlaridan jimgina ajralib ketardi.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 2. O'LCHANMAGAN QIYMAT O'RNIGA NOL YOZILMAYDI [T-05-04]
 * -----------------------------------------------------------------------
 * So'rov yiqilsa yoki hali kelmagan bo'lsa — `—`. «Bozorda 0 ta rasta
 * bor» va «rastalar sonini bilmayman» butunlay boshqa ikki gap, va
 * birinchisini ikkinchisining o'rniga yozish ma'muriyatga tizim
 * ishlayotgandek tuyulishiga sabab bo'lardi (05-13, 05-14, 03-08).
 *
 * ⛔ HOLAT NOMA'LUM bo'lsa ham (`undefined`/`null`) — `—`, «Qoralama»
 *    EMAS, va faollashtirish havolasi CHIZILMAYDI. Faol bozorga
 *    «faollashtiring» havolasini ko'rsatish adminni 409 ga olib borardi.
 *
 * -----------------------------------------------------------------------
 * ⚠ 3. IKKI SO'ROV MUSTAQIL
 * -----------------------------------------------------------------------
 * Biri yiqilganda ikkinchisining soni ekranda QOLADI. Umumiy «xato
 * bloki» `GET /users` ning bir martalik nosozligida rastalar sonini ham
 * o'chirib yuborardi.
 *
 * -----------------------------------------------------------------------
 * ⚠ 4. HAVOLA MANZILI KONSTANTADAN
 * -----------------------------------------------------------------------
 * `ACTIVATION_STEP` (`wizard-steps.ts`) — sonli literal yozilmaydi.
 * Qadam raqami o'zgargan kuni literal JIMGINA yolg'onga aylanardi
 * (`market-picker.tsx` da o'rnatilgan qoida).
 *
 * -----------------------------------------------------------------------
 * ⚠ 5. DARVOZA BU YERDA EMAS, SAHIFADA
 * -----------------------------------------------------------------------
 * Komponent rolni O'QIMAYDI. «Kim ko'radi?» savoliga `dashboard/page.tsx`
 * javob beradi (`market_manage`) va u yerda so'rov HAM yuborilmaydi —
 * `HeadlineCard` bilan aynan bir xil taqsimot.
 * =============================================================================
 */

/** O'lchanmagan qiymatning YAGONA ko'rinishi. */
const UNKNOWN = "—";

export type MarketStatusCardProps = {
  marketId: string | null;
  /** `undefined`/`null` — NOMA'LUM (`auth-store.ts::Principal` izohi). */
  isActive: boolean | null | undefined;
};

export function MarketStatusCard({ isActive, marketId }: MarketStatusCardProps) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();

  const setupStatus = useSetupStatusQuery(marketId);
  const users = useUsersQuery();

  /* Bozor tanlanmagan — so'rov ham yuborilmaydi, karta ham chizilmaydi. */
  if (marketId === null) return null;

  const busy = setupStatus.isPending || users.isPending;

  /** Son yoki `—` — ⛔ nol HECH QACHON o'rnini bosmaydi. */
  const count = (value: number | undefined): string =>
    value === undefined ? UNKNOWN : formatAmount(format, value, locale);

  const status = setupStatus.data;

  return (
    <Card aria-busy={busy ? true : undefined}>
      <CardHeader className="pb-2">
        <h2 className="text-lg font-semibold">{t("dashboard.marketStatus")}</h2>
      </CardHeader>

      <CardContent className="flex flex-col gap-4">
        {busy ? (
          <span className="sr-only" role="status">
            {t("common.loading")}
          </span>
        ) : null}

        {/*
         * HOLAT QATORI — uch shox va uchinchisi (`—`) BELGISIZ: badge
         * o'zi «o'lchangan holat» signali va uni noma'lum qiymat ustiga
         * qo'yish rangni yolg'on kanalga aylantirardi.
         */}
        <div className="flex items-center gap-3">
          {isActive === true ? (
            <Badge tone="success">{t("dashboard.statusActive")}</Badge>
          ) : isActive === false ? (
            <Badge tone="warning">{t("dashboard.statusDraft")}</Badge>
          ) : (
            <span className="text-sm text-text-muted">{UNKNOWN}</span>
          )}
        </div>

        {/*
         * ⛔ HAVOLA AYNAN `isActive === false` DA. `!isActive` YOZILMAYDI:
         *    u `undefined` ni ham qamrab, noma'lum holatda faollashtirish
         *    yo'lini ochib qo'yardi (H3).
         */}
        {isActive === false ? (
          <Link
            className="text-sm font-semibold text-accent-text underline underline-offset-4"
            href={`/markets/setup?step=${ACTIVATION_STEP}`}
          >
            {t("dashboard.activateHint")}
          </Link>
        ) : null}

        <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Counter label={t("dashboard.countStalls")} value={count(status?.stalls)} />
          <Counter
            label={t("dashboard.countVendors")}
            value={count(status?.vendors)}
          />
          <Counter
            label={t("dashboard.countCameras")}
            value={count(status?.cameras)}
          />
          <Counter
            label={t("dashboard.countUsers")}
            value={count(users.data?.items.length)}
          />
        </dl>
      </CardContent>
    </Card>
  );
}

/**
 * Bitta hisoblagich — `<dt>` darhol `<dd>` bilan qo'shni.
 *
 * ⚠ Qo'shnilik TEST KONTRAKTI ham: o'lchov yorliqni topib, YONIDAGI
 *   qiymatni o'qiydi. Oraliqqa o'rovchi element qo'yish `—` da'vosini
 *   jimgina o'lchanmas qilardi.
 */
function Counter({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-xs text-text-muted">{label}</dt>
      <dd className="font-mono text-xl font-semibold tabular-nums">{value}</dd>
    </div>
  );
}
