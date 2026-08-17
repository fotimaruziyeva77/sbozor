"use client";

import { useState } from "react";

import { useTranslations } from "next-intl";

import { Reveal } from "@/components/marketing/reveal";

/*
 * Yo'qotish kalkulyatori — Landing v2 (claude.ai/design, foydalanuvchi
 * buyurtmasi) HISOB-KITOB seksiyasi. Klient orollari reyestrining a'zosi
 * (G-land-1(a) — reyestr 5 → 6, ONGLI kengayish).
 *
 * ⛔ HALOLLIK (K-7 bilan kelishuv): bu narx kalkulyatori EMAS va bizning
 * va'damiz EMAS — foydalanuvchining O'Z taxmini asosidagi arifmetika.
 * Ikkala disclaimer (kirish matni + karta osti) dizayndan aynan olingan;
 * taxmin parametrlari (patta 8 000 so'm · 26 ish kuni · 5% to'lovsiz)
 * karta ostida LITERAL ochiq yoziladi.
 *
 * Server hech nimaga tegmaydi: sof klient arifmetikasi, fetch 0.
 */
const ASSUMED_DAILY_FEE_SOUM = 8000;
const ASSUMED_WORKDAYS_PER_MONTH = 26;
const ASSUMED_UNPAID_SHARE = 0.05;

/** 2306000 → «2 306 000» (hero-scene formatining ayni qoidasi). */
function formatSum(value: number): string {
  return String(value).replace(/\B(?=(?:\d{3})+(?!\d))/gu, " ");
}

export function LossCalc() {
  const t = useTranslations("landing");
  const [stalls, setStalls] = useState(500);

  const dailyUnpaid = Math.round(stalls * ASSUMED_UNPAID_SHARE);
  const monthlyLoss =
    dailyUnpaid * ASSUMED_DAILY_FEE_SOUM * ASSUMED_WORKDAYS_PER_MONTH;

  return (
    <div className="grid items-center gap-12 min-[841px]:grid-cols-2">
      <Reveal>
        <h2 className="text-2xl font-semibold tracking-tight">
          {t("calc.title")}
        </h2>
        <p className="mt-3 max-w-[56ch] text-sm leading-relaxed text-text-muted">
          {t("calc.intro")}
        </p>
        <label className="mt-7 block text-sm font-semibold">
          {t("calc.sliderLabel")}{" "}
          <span className="text-accent-text" data-numeric>
            {formatSum(stalls)}
          </span>
          <input
            className="mt-3 w-full accent-(--color-accent)"
            max={2000}
            min={100}
            onChange={(event) => {
              setStalls(Number(event.target.value));
            }}
            step={50}
            type="range"
            value={stalls}
          />
        </label>
        <div className="mt-1 flex justify-between text-xs text-text-muted">
          <span data-numeric>100</span>
          <span data-numeric>2 000</span>
        </div>
      </Reveal>
      <Reveal delayIndex={1}>
        {/* Natija kartasi — indigo panel; data-theme tokenlarni tungiga
            buradi (sinf faqat fonni beradi — tokensiz matn xira qolardi). */}
        <div
          className="landing-night rounded-2xl p-8 shadow-raised"
          data-theme="dark"
        >
          <p className="text-xs text-text-muted">{t("calc.dailyLabel")}</p>
          <p className="mt-1 text-2xl font-bold" data-numeric>
            ~{formatSum(dailyUnpaid)} {t("calc.dailyUnit")}
          </p>
          <p className="mt-5 text-xs text-text-muted">
            {t("calc.monthlyLabel")}
          </p>
          {/* ⛔ hero-o'lcham utilitasi EMAS — u 1 fayl/1 uchrashuvga
              qulflangan (G-land-5(a)); eng katta ruxsatli matn roli. */}
          <p
            className="mt-1 text-2xl font-bold text-warning-text"
            data-numeric
            data-testid="loss-calc-monthly"
          >
            {formatSum(monthlyLoss)} {t("calc.currency")}
          </p>
          <p className="mt-4 text-xs leading-relaxed text-text-muted">
            {t("calc.assumptions")}
          </p>
        </div>
      </Reveal>
    </div>
  );
}
