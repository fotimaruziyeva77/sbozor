"use client";

/*
 * =============================================================================
 * HERO SAHNASI — 12 SONIYALIK «JONLI BOZOR» SIKLI (10-UI-SPEC §5, K-1,
 * sketch 003-B foydalanuvchi tasdiqlagan; ROADMAP SC#2 ning mazmuni).
 *
 * ⛔⛔ BOSHLANG'ICH HOLAT = YAKUNIY KADR (§5.2 [QAROR]). Birinchi render —
 * ya'ni SSG HTML ham — 5-faza holatini chizadi: 30 katak yoniq, bittasi
 * to'lovsiz (amber), hisobot OCHIQ, tushum 2 306 000. Bitta mexanizm uchta
 * muammoni yechadi: (1) LCP sahnani kutmaydi — JS kelmasa ham hech nima
 * yetishmaydi; (2) reduced-motion shoxi IKKINCHI KOD bo'lmaydi — server
 * kadri o'zi javob, sikl shunchaki boshlanmaydi; (3) gidratatsiyadan keyin
 * «rewind» miltillashi yo'q — sikl 5-fazadan (server kadridan) DAVOM etadi.
 * Sikl tartibi: 5 → (pauza) → 1 → 2 → 3 → 4 → 5 → …
 *
 * ⛔ REDUCED-MOTION — effektning BIRINCHI qatorida erta return (Tuzoq 4,
 * naqsh: collect/success-choreography.tsx): birorta taymer UMUMAN
 * YARATILMAYDI. Sikl ichida har fazada tekshirish NOTO'G'RI bo'lardi —
 * taymerlar baribir yaratilib G-land-2(a) qizarar va arzon telefonda
 * batareya baribir yeyilardi.
 *
 * ⛔ TAYMER REYESTRI (G-land-2(d)): har faza o'z taymer id'sini massivga
 * yozadi; to'xtash/unmount'da HAMMASI tozalanadi va massiv bo'shatiladi.
 * Sizib qolgan 12s halqa sahifa yopilgandan keyin ham ishlab batareyani
 * yeydi. Naqsh: review-session.tsx dagi bitta ref — bu yerda MASSIV.
 *
 * ⛔ IKKI MUSTAQIL TO'XTATGICH, BITTA SAMARA (Tuzoq 5, §5.6 mexanizm 2/3):
 * IntersectionObserver (ko'rinuvchanlik) va document.visibilitychange (tab
 * fokusi) bitta bayroqqa YIG'ILMAYDI — hosila shart `running = visible &&
 * !pageHidden`. To'xtaganda taymerlar tozalanadi, DOM holati SAQLANADI;
 * davom etganda JORIY fazadan davom etadi (rewind YO'Q). Bitta bayroqqa
 * yig'ilsa foydalanuvchi tabga qaytganda sahna qayta boshlanardi.
 * ⛔ Sun'iy sikl chegarasi («3 martadan keyin to'xtasin») RAD ETILGAN
 * (§5.6): ko'rinuvchanlik — taxmin emas, o'lchov.
 *
 * ⛔ HALOLLIK (K-7, G-land-4(a)): `scene.sampleBadge` HAR fazada ko'rinadi
 * va shartli render ichida EMAS. Sahna raqamlari namunaviy — real bozor
 * nomi va «jonli» da'vosi yozilmaydi.
 *
 * ⛔ A11Y (§15.2): sahna — bezak emas, KONTENT: konteynerda role="img" +
 * aria-label (a11yDescription); ichki o'zgaruvchan qismlar aria-hidden.
 * Faza yorlig'i aria-live'ga QO'YILMAYDI — 12 soniyada 5 marta gapirish
 * shovqin. Amber rasta yorliq MATNI bilan juft (§15.12).
 *
 * ⛔ MOBIL (§5.8): media-shox CSS'da (sinf variantlari), JS'da EMAS —
 * <840px da 5 ustun va har uchinchi katak yashirin (30 → 20 katak, amber
 * katakning ko'rinадиган o'rni o'rtaga yaqin). JS BIR XIL DOM chizadi:
 * viewport o'qish SSG kadrini klientda boshqacha qilib gidratatsiya
 * nomuvofiqligi berardi. Sikl timinglari o'zgarmaydi.
 *
 * ⛔ GPU-TOZA (G-land-3, T-10-21): holat o'tishlari faqat transform/opacity/
 * rang; sweep — `.landing-sweep` (@keyframes faqat transform, globals.css);
 * inline uslubda geometriya YO'Q — faqat stagger kechikishi (transitionDelay)
 * va u ham fazaga qarab hisoblanadi (§5.4: katak stagger'i qaytariladigan
 * holat bo'lgani uchun @keyframes bilan emas).
 * =============================================================================
 */

import { useEffect, useRef, useState } from "react";

import { useTranslations } from "next-intl";

import { cn } from "@/lib/cn";
import { prefersReducedMotion } from "@/lib/motion";
import { useCountUp } from "@/lib/use-count-up";

/** 6×5 xarita (≥840px); mobil CSS-shox 5 ustun + har 3-katak yashirin. */
const STALL_COUNT = 30;
const GRID_COLUMNS = 6;
/**
 * To'lovsiz qoladigan rasta — DOM'da 0-asosli 16 (nth-child 17, ya'ni har
 * uchinchisi yashirilganda 3n ga tushmaydi va mobilda ham ko'rinadi; undan
 * oldin 5 katak yashirinib ko'rinadigan o'rni 11 bo'ladi — §5.8 jadvali).
 */
const UNPAID_STALL_INDEX = 16;

/** Yakuniy kadr tushumi — sketch 003-B raqami, namunaviy belgi ostida. */
const FINAL_REVENUE_SOUM = 2_306_000;
/** 3-fazada «to'lovsiz» aniqlanganda ko'rinadigan oraliq tushum. */
const DISCREPANCY_REVENUE_SOUM = 2_298_000;

/*
 * §5.5 ijro shartnomasi: 0–2,6 · 2,6–5,3 · 5,3–8,3 · 8,3–10,0 · 10,0–13,5.
 * ⛔ Sikl haqiqiy davri 13 500 ms — «12s» faqat nom. Besh faza yig'indisi
 * AYNAN 13 500 bo'lishi test kontraktining (G-land-2(b)) asosi.
 */
const PHASE1_MS = 2600;
const PHASE2_MS = 2700;
const PHASE3_MS = 3000;
const PHASE4_MS = 1700;
const PHASE5_MS = 3500;

/** Reset (holat off) va kataklarning yonishi orasidagi bitta qisqa kadr. */
const STALL_REVEAL_DELAY_MS = 120;
/** Katak chizilish qadami (faza 1) — sketch 003-B ning 70 ms i. */
const STALL_STAGGER_MS = 70;
/** Ustunma-ustun to'lov to'lqini qadami (faza 2). */
const COLUMN_STAGGER_MS = 280;
/** Tushum sanash davomiyliklari (§5.5): nomuvofiqlik / to'lov. */
const COUNT_DISCREPANCY_MS = 900;
const COUNT_SETTLE_MS = 600;
/**
 * Reset'dagi sanash — deyarli oniy (bitta rAF kadri). ⛔ 0 bo'lmaydi:
 * useCountUp progressi 0/0 = NaN bo'lib halqa hech qachon tugamasdi.
 */
const RESET_COUNT_MS = 1;

type Phase = 1 | 2 | 3 | 4 | 5;

type SceneState = {
  phase: Phase;
  /** Kataklar yoniqmi (faza 1 reset'ida false, so'ng stagger bilan true). */
  stallsOn: boolean;
  /** Kataklar to'lov to'lqinini olganmi (faza 2+). */
  paidWave: boolean;
  /** №16 «to'lovsiz» sifatida ochilganmi (faza 3+ va server kadri). */
  unpaidRevealed: boolean;
  /** №16 to'langanmi (faza 4–5, siklda; server kadrida EMAS). */
  unpaidResolved: boolean;
  reportVisible: boolean;
  /** null — server kadri: hisoblagich halqasi UMUMAN boshlanmaydi. */
  revenueTarget: number | null;
  revenueDurationMs: number;
};

/**
 * Server chizadigan yakuniy kadr (§5.2): xarita to'liq, bitta amber,
 * hisobot ochiq. `revenueTarget: null` — useCountUp halqasiz (T-05-04
 * naqshi), ekranda literal yakuniy son turadi.
 */
const FINAL_FRAME: SceneState = {
  phase: 5,
  paidWave: true,
  reportVisible: true,
  revenueDurationMs: COUNT_SETTLE_MS,
  revenueTarget: null,
  stallsOn: true,
  unpaidResolved: false,
  unpaidRevealed: true,
};

/**
 * Namunaviy son formati — 2306000 → «2 306 000» (oddiy bo'shliq).
 *
 * ⛔ Intl formatter ATAYIN ishlatilmaydi: server kadri uchala locale'da
 * AYNAN bir xil bo'lishi (SSG deterministik) va test DOM matni ustida
 * o'lchashi kerak (jsdom'da hisoblangan uslub yaroqsiz — 10-RESEARCH).
 * Bu real pul emas — namunaviy demo raqam (K-7), locale-mos guruhlashning
 * ma'no yuki yo'q.
 */
function formatSampleSoum(value: number): string {
  return String(value).replace(/\B(?=(?:\d{3})+(?!\d))/gu, " ");
}

export function HeroScene() {
  const t = useTranslations("landing");
  const [scene, setScene] = useState<SceneState>(FINAL_FRAME);
  /** ⛔ Taymer REYESTRI — har id shu massivga; tozalashda hammasi. */
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);
  /** Joriy faza — pauzadan keyin SHU fazadan davom (rewind yo'q). */
  const phaseRef = useRef<Phase>(5);
  const sceneNodeRef = useRef<HTMLDivElement | null>(null);

  const counted = useCountUp(scene.revenueTarget, scene.revenueDurationMs);
  const shownRevenue =
    scene.revenueTarget === null ? FINAL_REVENUE_SOUM : (counted ?? 0);

  useEffect(() => {
    /* ⛔ BIRINCHI QATOR (Tuzoq 4): reduced-motion'da taymer YARATILMAYDI. */
    if (prefersReducedMotion()) return;
    const node = sceneNodeRef.current;
    if (node === null) return;
    /* jsdom'da IntersectionObserver YO'Q — stub'siz muhitda sikl yo'q. */
    if (typeof IntersectionObserver === "undefined") return;

    let visible = false;
    let pageHidden = document.visibilityState === "hidden";
    let running = false;

    const clearScheduled = (): void => {
      for (const id of timersRef.current) {
        clearTimeout(id);
      }
      timersRef.current = [];
    };

    const schedule = (callback: () => void, delayMs: number): void => {
      timersRef.current.push(setTimeout(callback, delayMs));
    };

    /**
     * Fazaga kirish: to'liq holat + keyingi faza taymeri. Har faza to'liq
     * obyekt yozadi — pauza/davom har qanday nuqtada deterministik.
     */
    const enterPhase = (phase: Phase): void => {
      phaseRef.current = phase;
      switch (phase) {
        case 1: {
          /* Reset: kataklar o'chadi, hisobot yopiladi, tushum 0 ga. */
          setScene({
            phase: 1,
            paidWave: false,
            reportVisible: false,
            revenueDurationMs: RESET_COUNT_MS,
            revenueTarget: 0,
            stallsOn: false,
            unpaidResolved: false,
            unpaidRevealed: false,
          });
          /* Bitta kadr keyin kataklar stagger bilan chiziladi (§5.5/1). */
          schedule(() => {
            setScene((current) => ({ ...current, stallsOn: true }));
          }, STALL_REVEAL_DELAY_MS);
          schedule(() => {
            enterPhase(2);
          }, PHASE1_MS);
          return;
        }
        case 2: {
          /* Kamera nuri + ustunma-ustun to'lov; ⛔ №16 TEGILMAYDI. */
          setScene({
            phase: 2,
            paidWave: true,
            reportVisible: false,
            revenueDurationMs: RESET_COUNT_MS,
            revenueTarget: 0,
            stallsOn: true,
            unpaidResolved: false,
            unpaidRevealed: false,
          });
          schedule(() => {
            enterPhase(3);
          }, PHASE2_MS);
          return;
        }
        case 3: {
          /* Nomuvofiqlik: №16 amber + diqqat-halqa (bir marta) + yorliq. */
          setScene({
            phase: 3,
            paidWave: true,
            reportVisible: false,
            revenueDurationMs: COUNT_DISCREPANCY_MS,
            revenueTarget: DISCREPANCY_REVENUE_SOUM,
            stallsOn: true,
            unpaidResolved: false,
            unpaidRevealed: true,
          });
          schedule(() => {
            enterPhase(4);
          }, PHASE3_MS);
          return;
        }
        case 4: {
          /* Kassir to'lovni qayd etdi: yorliq yashil, №16 yashil. */
          setScene({
            phase: 4,
            paidWave: true,
            reportVisible: false,
            revenueDurationMs: COUNT_SETTLE_MS,
            revenueTarget: FINAL_REVENUE_SOUM,
            stallsOn: true,
            unpaidResolved: true,
            unpaidRevealed: true,
          });
          schedule(() => {
            enterPhase(5);
          }, PHASE4_MS);
          return;
        }
        case 5: {
          /* Kunlik hisobot + ~1,5s pauza (PHASE5_MS ichida). */
          setScene({
            phase: 5,
            paidWave: true,
            reportVisible: true,
            revenueDurationMs: COUNT_SETTLE_MS,
            revenueTarget: FINAL_REVENUE_SOUM,
            stallsOn: true,
            unpaidResolved: true,
            unpaidRevealed: true,
          });
          schedule(() => {
            enterPhase(1);
          }, PHASE5_MS);
          return;
        }
      }
    };

    /**
     * Davom etish — JORIY fazadan (§5.2 «rewind YO'Q»). 5-fazada DOM'ga
     * TEGILMAYDI: server kadri (yoki sikl hisobot kadri) allaqachon
     * ekranda — faqat keyingi o'tish rejalashtiriladi. Shu bitta shox
     * mount'dagi «kadrdan davom»ni ham, pauzadan qaytishni ham beradi.
     */
    const resumeFromCurrentPhase = (): void => {
      if (phaseRef.current === 5) {
        schedule(() => {
          enterPhase(1);
        }, PHASE5_MS);
        return;
      }
      enterPhase(phaseRef.current);
    };

    /* ⛔ Ikki mustaqil shart, bitta samara (Tuzoq 5). */
    const sync = (): void => {
      const nextRunning = visible && !pageHidden;
      if (nextRunning === running) return;
      running = nextRunning;
      if (running) {
        resumeFromCurrentPhase();
        return;
      }
      /* To'xtash: taymerlar tozalanadi, DOM holati SAQLANADI. */
      clearScheduled();
    };

    const observer = new IntersectionObserver((entries) => {
      const lastEntry = entries[entries.length - 1];
      visible = lastEntry === undefined ? false : lastEntry.isIntersecting;
      sync();
    });
    observer.observe(node);

    const onVisibilityChange = (): void => {
      pageHidden = document.visibilityState === "hidden";
      sync();
    };
    document.addEventListener("visibilitychange", onVisibilityChange);

    return () => {
      /* ⛔ disconnect MAJBURIY (reja Task 2) + to'liq taymer tozalash. */
      observer.disconnect();
      document.removeEventListener("visibilitychange", onVisibilityChange);
      clearScheduled();
    };
  }, []);

  const tagVariant =
    scene.phase === 3 ? "unpaid" : scene.phase === 4 ? "paid" : "hidden";

  /** Stagger faqat 1–2-fazalarda; qolganida o'tishlar kechikishsiz. */
  const stallTransitionDelayMs = (index: number): number => {
    if (scene.phase === 1) return index * STALL_STAGGER_MS;
    if (scene.phase === 2 && index !== UNPAID_STALL_INDEX) {
      return (index % GRID_COLUMNS) * COLUMN_STAGGER_MS;
    }
    return 0;
  };

  const stallState = (index: number): "empty" | "paid" | "unpaid" => {
    if (index === UNPAID_STALL_INDEX) {
      if (scene.unpaidResolved) return "paid";
      if (scene.unpaidRevealed) return "unpaid";
      return "empty";
    }
    return scene.paidWave ? "paid" : "empty";
  };

  return (
    <div
      aria-label={t("scene.a11yDescription")}
      className="rounded-lg border border-border bg-surface p-5 shadow-raised"
      data-phase={scene.phase}
      ref={sceneNodeRef}
      role="img"
    >
      {/* ⛔ Namunaviy belgi — HAR fazada, shartli render YO'Q (G-land-4(a)). */}
      <p aria-hidden="true" className="text-xs text-text-muted">
        <span>ⓘ </span>
        {t("scene.sampleBadge")}
      </p>
      <div aria-hidden="true" className="mt-2 flex flex-col gap-3">
        <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1 text-xs text-text-muted">
          <span>{t("scene.marketLabel")}</span>
          <span>
            {t("scene.revenueLabel")}
            {" · "}
            <span
              className="font-semibold text-text"
              data-numeric
              data-testid="hero-scene-revenue"
            >
              {formatSampleSoum(shownRevenue)}
            </span>
          </span>
        </div>
        {/* Faza yorlig'i — sahnaning MATNLI hikoyasi, har tilda almashadi.
            ⛔ aria-live YO'Q (§15.2). min-h yorliq almashganda sakratmaydi. */}
        <p
          className="min-h-5 text-sm font-semibold text-text"
          data-testid="hero-scene-phase"
        >
          {t(`scene.phase${scene.phase}`)}
        </p>
        <div className="landing-sweep-frame relative">
          <div
            className="grid grid-cols-6 gap-2 max-[840px]:grid-cols-5"
            data-testid="hero-scene-map"
          >
            {Array.from({ length: STALL_COUNT }, (_, index) => {
              const state = stallState(index);
              return (
                <span
                  className={cn(
                    "aspect-square rounded-md border border-border bg-surface-muted",
                    "transition duration-(--motion-base) ease-(--ease-out)",
                    scene.stallsOn ? "scale-100 opacity-100" : "scale-85 opacity-0",
                    state === "paid" && "border-success bg-success/20",
                    state === "unpaid" &&
                      "motion-attention border-warning bg-warning/20",
                    /* Mobil soddalashuv (§5.8) — CSS-shox, JS emas. */
                    "max-[840px]:nth-[3n]:hidden",
                  )}
                  data-on={String(scene.stallsOn)}
                  data-state={state}
                  key={index}
                  style={{ transitionDelay: `${stallTransitionDelayMs(index)}ms` }}
                />
              );
            })}
          </div>
          {/* Kamera nuri — sweep-frame FARZANDI (cqw shu konteynerga). */}
          <span
            className={cn(
              "pointer-events-none absolute inset-0 w-[3px] rounded-full",
              "bg-linear-to-b from-transparent via-accent to-transparent",
              scene.phase === 2 ? "landing-sweep opacity-100" : "opacity-0",
            )}
          />
        </div>
        {/* Yorliq — xarita ostida markazda (§5.8: o'lchovsiz joylashuv);
            amber rasta MATN bilan juft (§15.12). DOM'da doim — layout
            sakramaydi, faqat opacity/transform almashadi. */}
        <p
          className={cn(
            "self-center rounded-full border px-3 py-1 text-xs font-semibold text-text",
            "transition duration-(--motion-base) ease-(--ease-out)",
            tagVariant === "hidden"
              ? "translate-y-1 opacity-0"
              : "translate-y-0 opacity-100",
            tagVariant === "paid"
              ? "border-success bg-success/20"
              : "border-warning bg-warning/20",
          )}
          data-tag={tagVariant}
          data-testid="hero-scene-tag"
        >
          {tagVariant === "paid" ? t("scene.tagPaid") : t("scene.tagUnpaid")}
        </p>
        {/* Kunlik hisobot — pastdan ko'tariladi (translate/opacity). */}
        <div
          className={cn(
            "rounded-md border border-border bg-surface p-4 shadow-card",
            "transition duration-(--motion-slow) ease-(--ease-out)",
            scene.reportVisible
              ? "translate-y-0 opacity-100"
              : "translate-y-3 opacity-0",
          )}
          data-testid="hero-scene-report"
          data-visible={String(scene.reportVisible)}
        >
          <p className="text-sm font-semibold text-text">
            {t("scene.reportTitle")}
          </p>
          <dl className="mt-2 flex flex-col gap-1 text-xs text-text-muted">
            <div className="flex items-baseline justify-between gap-3">
              <dt>{t("scene.reportOccupied")}</dt>
              <dd data-numeric>215</dd>
            </div>
            <div className="flex items-baseline justify-between gap-3">
              <dt>{t("scene.reportPaid")}</dt>
              <dd data-numeric>214</dd>
            </div>
            <div className="flex items-baseline justify-between gap-3 font-semibold text-text">
              <dt>{t("scene.reportUnpaid")}</dt>
              <dd data-numeric>1 → 0</dd>
            </div>
          </dl>
        </div>
      </div>
    </div>
  );
}
