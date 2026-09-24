"use client";

import type { ReactNode, RefObject } from "react";
import { useEffect, useRef, useState, useSyncExternalStore } from "react";

import { Check, TriangleAlert } from "lucide-react";
import { useTranslations } from "next-intl";

import { Reveal } from "@/components/marketing/reveal";
import { cn } from "@/lib/cn";
import { prefersReducedMotion } from "@/lib/motion";

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

/*
 * =============================================================================
 * RAQAMNING «DUMALASHI» — foydalanuvchi: «animatsiyalarini juda ham
 * chiroyli qil» (260819).
 *
 * ⛔⛔ NEGA ODDIY `setState` YETMAYDI. Javob o'zgarganda yillik summa
 *     BIR KADRDA sakrab qolardi: 62 400 000 -> 212 160 000. Ko'z buni
 *     «hisob o'zgardi» deb emas, «ekran miltilladi» deb o'qiydi va eng
 *     qimmat raqam — butun seksiyaning MA'NOSI — e'tibordan chetda
 *     qolardi. Yumshoq o'tishda esa ko'z harakatga ergashadi va oxirgi
 *     qiymatda TO'XTAYDI. Bu «vau» uchun emas, E'TIBOR uchun.
 *
 * ⛔⛔ VA NEGA QIYMAT HOLATDA (`useState`) SAQLANMAYDI — BU ENG MUHIM
 *     QISMI, VA U XROMDA O'LCHANDI.
 *
 *     Birinchi tahrirda ko'rsatiladigan qiymat `useState` da edi va uni
 *     faqat `requestAnimationFrame` yangilardi. Natija: brauzer kadr
 *     chizmaydigan holatda (yorliq fonda, oyna yashiringan, tizim
 *     tejamkor rejimda) rAF UMUMAN yugurmaydi — va raqam mount
 *     paytidagi qiymatda MUZLAB qoladi. Slayder surilardi, javob
 *     o'zgarardi, ekrandagi son esa eski. Animatsiya mahsulotni
 *     BUZARDI.
 *
 *     Shuning uchun endi: HAQIQAT — React renderida (`formatSum(value)`
 *     to'g'ridan-to'g'ri chiziladi), animatsiya esa DOM ustidan
 *     vaqtincha yozadi. rAF yugurmasa — foydalanuvchi darhol TO'G'RI
 *     sonni ko'radi. Ya'ni nosozlik yo'nalishi xavfsiz tomonga qaragan.
 *
 * ⛔ HAR O'ZGARISHDA JORIY QIYMATDAN qayta boshlanadi (`currentRef`),
 *    noldan emas. Slayder sudralayotganda bu «quyruq» effektini beradi —
 *    raqam barmoqdan ozgina orqada, tinch suzib boradi.
 *
 * ⛔ `prefers-reduced-motion` — animatsiya UMUMAN yo'q: React nima
 *    chizgan bo'lsa, o'sha qoladi. Global CSS bloki bu yerda yordam
 *    bermaydi (harakat JS'da), shuning uchun shox QO'LDA yozilgan.
 *
 * ⛔ 520ms — o'lchangan kelishuv: 300ms da o'tish sezilmaydi, 800ms da
 *    esa foydalanuvchi javobni kutib qoladi. Egri chiziq oxiri yumshoq
 *    (`easeOutCubic`) — to'xtash «urilib» emas, «qo'nib» o'tadi.
 *
 * ⚠ `lib/use-count-up.ts` QAYTA ISHLATILMADI va bu ONGLI: u hero
 *   sahnasining shartnomasiga (null qiymat, «birinchi ko'rinish 0 dan»,
 *   faza bo'yicha davomiylik) qurilgan va o'z darvozalari bilan
 *   qulflangan (G-land-2). Ustiga u ham qiymatni HOLATDA saqlaydi —
 *   ya'ni yuqorida tasvirlangan muzlash sinfiga ochiq. Uni bu yerda
 *   ishlatish hero kontraktini o'zgartirishni talab qilardi.
 *
 * ⚠ Nishon tugun FAQAT sonni tutishi shart (`textContent` butunlay
 *   almashtiriladi) — shuning uchun valyuta so'zi tugundan TASHQARIDA.
 * =============================================================================
 */
const COUNT_DURATION_MS = 520;

/** Oxiri yumshoq — boshi tez: qiymat darhol javob berayotgandek tuyuladi. */
function easeOutCubic(progress: number): number {
  return 1 - (1 - progress) ** 3;
}

/** No-op obuna — afzallik bir marta o'qiladi (lib/motion.ts falsafasi). */
const subscribeNoop = (): (() => void) => () => {};
const getServerReducedMotion = (): boolean => false;

function useCountUp(
  ref: RefObject<HTMLElement | null>,
  value: number,
  reduced: boolean,
): void {
  /* Joriy (kasrli) qiymat — keyingi o'tish shu yerdan boshlanadi. */
  const currentRef = useRef(value);
  const frameRef = useRef(0);

  useEffect(() => {
    const node = ref.current;
    if (node === null || reduced) {
      currentRef.current = value;
      return;
    }
    const from = currentRef.current;
    if (from === value) return;

    const began = performance.now();
    const step = (now: number) => {
      const progress = Math.min(1, (now - began) / COUNT_DURATION_MS);
      const shown = from + (value - from) * easeOutCubic(progress);
      currentRef.current = shown;
      node.textContent = formatSum(Math.round(shown));
      if (progress < 1) {
        frameRef.current = requestAnimationFrame(step);
      } else {
        currentRef.current = value;
      }
    };
    frameRef.current = requestAnimationFrame(step);
    return () => {
      cancelAnimationFrame(frameRef.current);
    };
  }, [ref, value, reduced]);
}

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
  const reducedMotion = useSyncExternalStore(
    subscribeNoop,
    prefersReducedMotion,
    getServerReducedMotion,
  );

  const dailyUnpaid = Math.round(stalls * ASSUMED_UNPAID_SHARE);
  const monthlyLoss = dailyUnpaid * fee * ASSUMED_WORKDAYS_PER_MONTH;
  const yearlyLoss = monthlyLoss * MONTHS_PER_YEAR;
  /* Ekranga chiqadigan qiymatlar — React chizadi, rAF esa ustidan
     yumshoq o'tish yozadi (yuqoridagi izoh). */
  const dailyRef = useRef<HTMLSpanElement | null>(null);
  const monthlyRef = useRef<HTMLSpanElement | null>(null);
  const yearlyRef = useRef<HTMLSpanElement | null>(null);
  useCountUp(dailyRef, dailyUnpaid, reducedMotion);
  useCountUp(monthlyRef, monthlyLoss, reducedMotion);
  useCountUp(yearlyRef, yearlyLoss, reducedMotion);
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
        <p className="mt-4 max-w-[52ch] landing-body text-text-muted">
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
        <p
          className="mt-3 landing-micro font-semibold tracking-wide text-text-muted"
          data-testid="calc-counter"
        >
          {done ? t("calc.counterDone") : t("calc.counter", { step })}
        </p>

        <div className="mt-4">
          {step === 1 ? (
            <div>
              <h3 className="landing-h3">{t("calc.q1.title")}</h3>
              <p
                className="mt-4 landing-loss-total font-bold text-accent-text"
                data-numeric
              >
                {formatSum(stalls)}{" "}
                <span className="landing-lead font-semibold text-text-muted">
                  {t("calc.q1.unit")}
                </span>
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
              <div className="mt-2 flex justify-between landing-micro text-text-muted">
                <span data-numeric>100</span>
                <span data-numeric>2 000</span>
              </div>
              <button
                className={cn(
                  "mt-6 inline-flex min-h-13 cursor-pointer items-center rounded-xl bg-accent px-7",
                  "landing-note font-semibold text-accent-fg",
                  "transition-colors hover:bg-accent-hover",
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
              <p className="mt-3 max-w-[50ch] landing-body text-text-muted">
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
          <p className="landing-note text-text-muted">{t("calc.dailyLabel")}</p>
          <p className="mt-2 landing-h2 font-bold" data-numeric>
            ~<span ref={dailyRef}>{formatSum(dailyUnpaid)}</span>{" "}
            <span className="landing-lead font-semibold text-text-muted">
              {t("calc.dailyUnit")}
            </span>
          </p>

          <p className="mt-6 landing-note text-text-muted">
            {t("calc.yearLabel")}
          </p>
          {/* ⛔ hero-o'lcham utilitasi EMAS — u 1 fayl/1 uchrashuvga
              qulflangan (G-land-5(a)); bu kartaning o'z o'lchami. */}
          <p
            className="landing-loss-total mt-2 font-bold text-warning-text"
            data-numeric
            data-testid="loss-calc-yearly"
          >
            <span ref={yearlyRef}>{formatSum(yearlyLoss)}</span>{" "}
            {t("calc.currency")}
          </p>
          {/* ⛔ Oylik summa `t.rich` TEGI bilan: son `<amount>` ICHIDA
              (`{sum}`), teg esa ref'li TUGUN beradi — rAF faqat SONNI
              almashtiradi, matnning qolgani (so'zlar, valyuta) tegilmaydi.
              ⛔ `{amount}` ARGUMENTIGA funksiya berish ISHLAMAYDI: next-intl
              funksiyani faqat teg uchun chaqiradi va satr sonsiz chiqardi
              (2026-09-24, `loss-calc.test.tsx` oylik bloki). */}
          <p
            className="mt-2 landing-note text-text-muted"
            data-numeric
            data-testid="loss-calc-monthly"
          >
            {t.rich("calc.monthlyInline", {
              sum: formatSum(monthlyLoss),
              amount: (chunks: ReactNode) => (
                <span ref={monthlyRef}>{chunks}</span>
              ),
            })}
          </p>

          {/* ⛔ 260819: NUQTA -> IKONKA. Rangli nuqta yagona signal edi va
              rang ko'rmaydigan foydalanuvchi uchun «xavf» bilan «yaxshi»
              farqlanmasdi (§15.12). Uchburchak/belgi shakli rangdan
              MUSTAQIL o'qiladi. */}
          <ul className="mt-6 flex flex-col gap-3.5 border-t border-border pt-5">
            {findings.map((finding) => (
              <li className="flex items-start gap-3" key={finding.key}>
                {finding.tone === "risk" ? (
                  <TriangleAlert
                    aria-hidden="true"
                    className="mt-0.5 size-4 shrink-0 text-warning-text"
                    strokeWidth={2}
                  />
                ) : (
                  <Check
                    aria-hidden="true"
                    className="mt-0.5 size-4 shrink-0 text-success-text"
                    strokeWidth={2.5}
                  />
                )}
                <span className="landing-note text-text-muted">
                  {finding.text}
                </span>
              </li>
            ))}
          </ul>

          <p className="mt-6 landing-micro text-text-muted">
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
        /* Barmoqda 44px: `min-h-*` utilitasi `@layer base` dagi
           tegish qoidasini yengadi, shuning uchun chegara SHU YERDA. */
        "pointer-coarse:min-h-11",
        "text-xs font-semibold text-text-muted hover:text-text",
      )}
      onClick={onClick}
      type="button"
    >
      {label}
    </button>
  );
}
