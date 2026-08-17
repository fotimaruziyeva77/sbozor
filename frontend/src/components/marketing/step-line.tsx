"use client";

import { useTranslations } from "next-intl";
import { useState, useSyncExternalStore } from "react";

import { Reveal } from "@/components/marketing/reveal";
import { cn } from "@/lib/cn";
import { prefersReducedMotion } from "@/lib/motion";

/*
 * =============================================================================
 * 3-QADAM SEKSIYASI — CHIZIQ TO'LISHI `data-step` ORQALI (10-UI-SPEC §10, K-3).
 * Bu sahifaning 3-SEKSIYASI, hero EMAS. Klient orollari reyestrining a'zosi
 * (G-land-1(a)).
 *
 * ⛔⛔ TO'LISH GEOMETRIYASI BU FAYLDA UMUMAN YO'Q (§10.2 [QAROR], T-10-21):
 *    komponent faqat `data-step="0|1|2|3"` atributini yozadi; `scaleY`
 *    darajalari, `transform-origin` va 900ms kompozit qiymat `globals.css`
 *    dagi `.landing-step-fill` + uchta `[data-step]` selektorida yashaydi.
 *    Sketch manbasining `.prog` balandlik-tranzitsiyasi shakli
 *    (003-landing-hero.html:89) ATAYIN takrorlanmadi — u
 *    BANNED_KEYFRAME_PROPS sinfidagi layout-thrash beradi va bugungi
 *    darvozadan jimgina o'tardi (L-8 o'lchangan bo'shliq; G-land-3(a)
 *    10-07 da shu teshikni yopadi). Taqiqlangan xossa nomlari izohda ham
 *    literal yozilmaydi (badge.tsx konvensiyasi).
 *
 * Tetik — `Reveal` primitivining QAYTA ISHLATILISHI (qo'shimcha observer
 * ochilmaydi): har qadam `threshold: 0.4` bilan ko'ringanda `onReveal`
 * `data-step` ni oshiradi (`Math.max` — qadamlar tartibsiz otilsa ham daraja
 * orqaga qaytmaydi) va qadam matni `.motion-enter` bilan ochiladi.
 * `disconnect()` tozalashi `Reveal` ning o'z shartnomasida (reveal.test.tsx).
 *
 * ⛔ Reduced-motion — QO'SHIMCHA SHOX YO'Q: globals.css'ning global bloki
 *    transition'larni 0.01ms ga tushiradi, ya'ni chiziq darhol to'lgan
 *    holatda chiziladi. Lekin `data-step` oxirgi qiymatga YETISHI shart
 *    (observer qurilmaydi — `Reveal` ochilish signalini bermaydi). Mexanizm:
 *    `useSyncExternalStore` (motion.ts sarlavhasi aynan shu qatlamni nazarda
 *    tutgan) — server snapshoti `false` (SSR kadri `data-step="0"` bilan mos),
 *    klientda esa afzallik o'qilishi bilan daraja 3 ga HISOBLANADI (holat
 *    emas, hosila — effektda setState chaqirig'i YO'Q, react-hooks qoidasiga
 *    mos). Obuna — no-op: afzallik bir martalik o'qiladi (lib/motion.ts
 *    falsafasi), hodisaga qayta bo'yalish shart emas.
 *
 * ⛔ Taymer chaqiruvlari bu faylda 0 marta (G-land-3(c); taqiqlangan
 *    chaqiruv nomlari izohda ham literal yozilmaydi — badge.tsx
 *    konvensiyasi). Avtomatik harakat faqat hero sahnasida.
 * =============================================================================
 */
const STEPS = ["s1", "s2", "s3"] as const;

/** No-op obuna — bir martalik o'qish (lib/motion.ts falsafasi). */
const subscribeNoop = (): (() => void) => () => {};
const getServerReducedMotion = (): boolean => false;

export function StepLine() {
  const t = useTranslations("landing");
  const [revealedStep, setRevealedStep] = useState(0);
  const reducedMotion = useSyncExternalStore(
    subscribeNoop,
    prefersReducedMotion,
    getServerReducedMotion,
  );
  /* Reduced-motion'da daraja darhol oxirgi qiymat — hosila, holat emas. */
  const step = reducedMotion ? 3 : revealedStep;

  return (
    <div className="flex flex-col gap-6" data-step={step}>
      <Reveal>
        <h2 className="text-2xl font-semibold tracking-tight">
          {t("steps.title")}
        </h2>
      </Reveal>
      <div className="relative">
        {/* Fon chizig'i — `border` rangida 2px (§10.1), dekorativ. */}
        <div
          aria-hidden="true"
          className="absolute top-2 bottom-2 left-[5px] w-0.5 rounded-full bg-border"
        />
        {/* To'lgan qism — daraja globals.css'dagi [data-step] selektorlaridan. */}
        <div
          aria-hidden="true"
          className="landing-step-fill absolute top-2 bottom-2 left-[5px] w-0.5 rounded-full bg-accent"
        />
        <ol className="flex flex-col gap-10">
          {STEPS.map((key, index) => (
            <li className="relative pl-8" key={key}>
              {/* Qadam nuqtasi: border-ui -> accent (bare `transition` —
                  yumshoqlik @theme default juftligidan, §10.1). */}
              <span
                aria-hidden="true"
                className={cn(
                  "absolute top-1 left-0 size-3 rounded-full border-2 transition",
                  step > index
                    ? "border-accent bg-accent"
                    : "border-border-ui bg-surface",
                )}
              />
              <Reveal
                onReveal={() =>
                  setRevealedStep((current) => Math.max(current, index + 1))
                }
                threshold={0.4}
              >
                <h3 className="text-lg font-semibold">
                  {t(`steps.${key}.title`)}
                </h3>
                <p className="mt-1 max-w-[66ch] text-sm leading-relaxed text-text-muted">
                  {t(`steps.${key}.body`)}
                </p>
              </Reveal>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}
