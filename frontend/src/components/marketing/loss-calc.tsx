"use client";

import { useState } from "react";

import { useTranslations } from "next-intl";

import { Reveal } from "@/components/marketing/reveal";
import { cn } from "@/lib/cn";

/*
 * «60 soniyalik audit» — Landing v2 (claude.ai/design, foydalanuvchi
 * buyurtmasi) HISOB-KITOB seksiyasi, dizayndagi TO'RT SAVOLLI oqim bilan.
 * Klient orollari reyestrining a'zosi (G-land-1(a)).
 *
 * ⛔ HALOLLIK (K-7 bilan kelishuv): bu narx kalkulyatori EMAS va bizning
 * va'damiz EMAS — foydalanuvchining O'Z javoblari asosidagi arifmetika.
 * Ikkala disclaimer (kirish matni + karta ostidagi «hisob usuli») dizayndan
 * olingan; to'lovsiz ulush FOIZ belgisisiz, so'z bilan yoziladi (G-land-4(e)).
 *
 * Server hech nimaga tegmaydi: sof klient arifmetikasi, fetch 0.
 */
const ASSUMED_WORKDAYS_PER_MONTH = 26;
const ASSUMED_UNPAID_SHARE = 0.05;
const MONTHS_PER_YEAR = 12;
/** «Katta bozor» chegarasi — bundan yuqorida nazoratchi ko'zi yetmaydi. */
const LARGE_MARKET_STALLS = 700;

const FEE_OPTIONS = [5000, 8000, 12_000, 20_000] as const;
const CAMERA_OPTIONS = ["nvr", "old", "none"] as const;
const LEDGER_OPTIONS = ["paper", "excel", "system"] as const;

type CameraAnswer = (typeof CAMERA_OPTIONS)[number];
type LedgerAnswer = (typeof LEDGER_OPTIONS)[number];

/** Xulosa yo'nalishi: `risk` — amber nuqta, `ok` — yashil nuqta. */
type Finding = { key: string; tone: "risk" | "ok"; text: string };

const TOTAL_QUESTIONS = 4;

/** 2306000 → «2 306 000» (hero-scene formatining ayni qoidasi). */
function formatSum(value: number): string {
  return String(value).replace(/\B(?=(?:\d{3})+(?!\d))/gu, " ");
}

/** Variant tugmasi — tanlangani aksent hoshiya oladi (dizayn `mkOpts`). */
function OptionButton({
  label,
  onClick,
  selected,
}: {
  label: string;
  onClick: () => void;
  selected: boolean;
}) {
  return (
    <button
      className={cn(
        "min-h-14 rounded-lg border px-4 py-3.5 text-left text-sm font-semibold",
        "cursor-pointer bg-surface transition duration-(--motion-base) ease-(--ease-out)",
        selected
          ? "border-accent text-accent-text"
          : "border-border text-text hover:border-border-ui",
      )}
      onClick={onClick}
      type="button"
    >
      {label}
    </button>
  );
}

export function LossCalc() {
  const t = useTranslations("landing");
  const [step, setStep] = useState(1);
  const [stalls, setStalls] = useState(500);
  const [fee, setFee] = useState<number>(8000);
  const [cameras, setCameras] = useState<CameraAnswer | null>(null);
  const [ledger, setLedger] = useState<LedgerAnswer | null>(null);

  const dailyUnpaid = Math.round(stalls * ASSUMED_UNPAID_SHARE);
  const monthlyLoss = dailyUnpaid * fee * ASSUMED_WORKDAYS_PER_MONTH;
  const yearlyLoss = monthlyLoss * MONTHS_PER_YEAR;
  const done = step > TOTAL_QUESTIONS;

  /* Xulosalar — javoblardan KELIB CHIQADI (dizayn `findings`): javob
     berilmagan savol xulosa bermaydi, ya'ni o'ylab topilgan da'vo yo'q. */
  const findings: Finding[] = [];
  if (ledger !== null) {
    findings.push({
      key: `ledger-${ledger}`,
      tone: ledger === "system" ? "ok" : "risk",
      text: t(`calc.findings.${ledger}`),
    });
  }
  if (cameras !== null) {
    findings.push({
      key: `cameras-${cameras}`,
      tone: cameras === "none" ? "risk" : "ok",
      text: t(`calc.findings.cam${cameras === "nvr" ? "Nvr" : cameras === "old" ? "Old" : "None"}`),
    });
  }
  findings.push(
    stalls >= LARGE_MARKET_STALLS
      ? {
          key: "size-large",
          tone: "risk",
          text: t("calc.findings.large", { stalls: formatSum(stalls) }),
        }
      : { key: "size-small", tone: "ok", text: t("calc.findings.small") },
  );

  return (
    <div className="grid items-start gap-12 min-[841px]:grid-cols-2">
      <Reveal>
        <h2 className="landing-h2 tracking-tight">
          {t("calc.title")}
        </h2>
        <p className="mt-3.5 max-w-[52ch] text-sm leading-relaxed text-text-muted">
          {t("calc.intro")}
        </p>

        {/* Jarayon chizig'i — 4 ta band; o'tilgani to'q, joriysi ochroq. */}
        <div className="mt-7 flex max-w-[280px] gap-1.5" aria-hidden="true">
          {[1, 2, 3, 4].map((index) => (
            <span
              className={cn(
                "h-1 flex-1 rounded-full transition-colors duration-(--motion-slow)",
                done || step > index
                  ? "bg-accent"
                  : step === index
                    ? "bg-accent/60"
                    : "bg-border",
              )}
              key={index}
            />
          ))}
        </div>
        <p className="mt-2.5 text-xs text-text-muted" data-testid="calc-counter">
          {done ? t("calc.counterDone") : t("calc.counter", { step })}
        </p>

        <div className="mt-4">
          {step === 1 ? (
            <div>
              <h3 className="landing-h3">{t("calc.q1.title")}</h3>
              <p
                className="mt-4 text-xl font-bold text-accent-text"
                data-numeric
              >
                {formatSum(stalls)} {t("calc.q1.unit")}
              </p>
              <label className="sr-only" htmlFor="calc-stalls">
                {t("calc.q1.title")}
              </label>
              <input
                className="mt-2.5 w-full accent-(--color-accent)"
                id="calc-stalls"
                max={2000}
                min={100}
                onChange={(event) => {
                  setStalls(Number(event.target.value));
                }}
                step={50}
                type="range"
                value={stalls}
              />
              <div className="mt-1.5 flex justify-between text-xs text-text-muted">
                <span data-numeric>100</span>
                <span data-numeric>2 000</span>
              </div>
              <button
                className={cn(
                  "mt-5.5 min-h-12 cursor-pointer rounded-xl bg-accent px-6.5",
                  "text-sm font-semibold text-accent-fg",
                )}
                onClick={() => {
                  setStep(2);
                }}
                type="button"
              >
                {t("calc.next")}
              </button>
            </div>
          ) : null}

          {step === 2 ? (
            <div>
              <h3 className="landing-h3">{t("calc.q2.title")}</h3>
              <div className="mt-4 flex flex-col gap-2.5">
                {FEE_OPTIONS.map((value) => (
                  <OptionButton
                    key={value}
                    label={t(`calc.q2.fee${value}`)}
                    onClick={() => {
                      setFee(value);
                      setStep(3);
                    }}
                    selected={fee === value}
                  />
                ))}
              </div>
              <BackButton label={t("calc.back")} onClick={() => setStep(1)} />
            </div>
          ) : null}

          {step === 3 ? (
            <div>
              <h3 className="landing-h3">{t("calc.q3.title")}</h3>
              <div className="mt-4 flex flex-col gap-2.5">
                {CAMERA_OPTIONS.map((value) => (
                  <OptionButton
                    key={value}
                    label={t(`calc.q3.${value}`)}
                    onClick={() => {
                      setCameras(value);
                      setStep(4);
                    }}
                    selected={cameras === value}
                  />
                ))}
              </div>
              <BackButton label={t("calc.back")} onClick={() => setStep(2)} />
            </div>
          ) : null}

          {step === 4 ? (
            <div>
              <h3 className="landing-h3">{t("calc.q4.title")}</h3>
              <div className="mt-4 flex flex-col gap-2.5">
                {LEDGER_OPTIONS.map((value) => (
                  <OptionButton
                    key={value}
                    label={t(`calc.q4.${value}`)}
                    onClick={() => {
                      setLedger(value);
                      setStep(5);
                    }}
                    selected={ledger === value}
                  />
                ))}
              </div>
              <BackButton label={t("calc.back")} onClick={() => setStep(3)} />
            </div>
          ) : null}

          {done ? (
            <div>
              <h3 className="landing-h3">{t("calc.done.title")}</h3>
              <p className="mt-2.5 max-w-[50ch] text-sm leading-relaxed text-text-muted">
                {t("calc.done.body")}
              </p>
              <BackButton
                label={t("calc.done.restart")}
                onClick={() => {
                  setStep(1);
                }}
              />
            </div>
          ) : null}
        </div>
      </Reveal>

      <Reveal delayIndex={1}>
        {/* Natija kartasi — indigo panel; data-theme tokenlarni tungiga
            buradi (sinf faqat fonni beradi — tokensiz matn xira qolardi). */}
        <div
          className="landing-night rounded-2xl px-8 py-9 shadow-raised"
          data-theme="dark"
        >
          <p className="text-xs text-text-muted">{t("calc.dailyLabel")}</p>
          <p className="mt-2 text-2xl font-bold" data-numeric>
            ~{formatSum(dailyUnpaid)} {t("calc.dailyUnit")}
          </p>

          <p className="mt-5.5 text-xs text-text-muted">{t("calc.yearLabel")}</p>
          {/* ⛔ hero-o'lcham utilitasi EMAS — u 1 fayl/1 uchrashuvga
              qulflangan (G-land-5(a)); bu kartaning o'z o'lchami. */}
          <p
            className="landing-loss-total mt-2 font-bold text-warning-text"
            data-numeric
            data-testid="loss-calc-yearly"
          >
            {formatSum(yearlyLoss)} {t("calc.currency")}
          </p>
          <p className="mt-1.5 text-xs text-text-muted" data-numeric>
            {t("calc.monthlyInline", { amount: formatSum(monthlyLoss) })}
          </p>

          <ul className="mt-5.5 flex flex-col gap-3 border-t border-border pt-5">
            {findings.map((finding) => (
              <li className="flex items-start gap-2.5" key={finding.key}>
                <span
                  aria-hidden="true"
                  className={cn(
                    "mt-1.5 size-1.5 shrink-0 rounded-full",
                    finding.tone === "risk" ? "bg-warning" : "bg-success",
                  )}
                />
                <span className="text-xs leading-relaxed text-text-muted">
                  {finding.text}
                </span>
              </li>
            ))}
          </ul>

          <p className="mt-5 text-xs leading-relaxed text-text-muted">
            {t("calc.method")}
          </p>

          {done ? (
            <a
              className={cn(
                "mt-5 inline-flex min-h-12 items-center justify-center rounded-xl",
                "bg-accent px-6 text-sm font-semibold text-accent-fg",
              )}
              href="#demo"
            >
              {t("calc.done.cta")}
            </a>
          ) : null}
        </div>
      </Reveal>
    </div>
  );
}

/** Ikkilamchi («orqaga»/«qayta») tugma — dizayndagi `auditGhost`. */
function BackButton({
  label,
  onClick,
}: {
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      className={cn(
        "mt-5 min-h-10 cursor-pointer rounded-lg border border-border px-4.5",
        "text-xs font-semibold text-text-muted hover:text-text",
      )}
      onClick={onClick}
      type="button"
    >
      {label}
    </button>
  );
}
