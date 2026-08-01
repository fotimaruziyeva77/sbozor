"use client";

import { useEffect, useRef } from "react";
import { Camera, Check, Lock } from "lucide-react";
import { useTranslations } from "next-intl";

import {
  CAMERA_PLACEHOLDER,
  completedStepCount,
  WIZARD_SETUP_PATH,
  type WizardStepView,
  wizardStepViews,
} from "@/components/wizard/wizard-steps";
import { Link } from "@/i18n/navigation";
import type { SetupStatusResponse } from "@/lib/api-types";
import { cn } from "@/lib/cn";

/*
 * =============================================================================
 * Qadam relsi — TO'RT holat, UCH kanal (UI-SPEC §6.3).
 *
 * Uchta emas, TO'RTTA holat: "ochiq-lekin-bo'sh" (to'ldirilmagan) va
 * "hali ochilmaydi" (bloklangan) butunlay boshqa ma'no beradi. Ularni
 * bittaga yig'ish adminni 4-qadamda "nega bo'sh?" deb qoldirardi.
 *
 * Har holat UCH kanal bilan beriladi — vizual + ikonka + ARIA. Rang
 * hech qachon YAGONA signal emas (UI-SPEC §4.4, WCAG 1.4.1).
 *
 * BLOKLANGAN QADAMNING SABABI KO'RINADI, yashirilmaydi: sababsiz
 * bloklangan element foydalanuvchini boshi berk ko'chaga olib boradi.
 * Sabab `blockedBy` grafidan HOSIL bo'ladi (`wizard-steps.ts`), ya'ni u
 * qadamlar tartibi bilan hech qachon ajralib keta olmaydi.
 *
 * ⚠ D-16 — KAMERA KO'RSATKICHI NEYTRAL. Bu faylda ogohlantirish ikonkasi,
 * ogohlantirish/xavf fon sinflari va shoshilinch e'lon roli TAQIQ: kamera
 * hali ulanmagani NOSOZLIK emas, rejalashtirilgan keyingi qadam. Taqiq
 * mexanik grep bilan qulflangan, shuning uchun taqiqlangan atamalar bu
 * izohda ham LITERAL yozilmaydi — keyingi ishlovchi ularni "tushuntirish
 * uchun" qaytarib qo'ymasin.
 * =============================================================================
 */

/** Bloklangan qadamning sabab matni uchun barqaror `id` (`aria-describedby`). */
function reasonId(stepId: number): string {
  return `wizard-step-${stepId}-reason`;
}

export function WizardStepper({
  currentStep,
  status,
}: {
  currentStep: number;
  /** `null` — javob hali kelmagan yoki bozor umuman yaratilmagan. */
  status: SetupStatusResponse | null;
}) {
  const t = useTranslations();

  const views = wizardStepViews(status, currentStep);
  const done = completedStepCount(views);

  const currentRef = useRef<HTMLLIElement | null>(null);

  /*
   * Mobil relsda joriy qadam MARKAZGA keladi. Bu holat o'zgartirmaydi —
   * sof DOM yon ta'siri, ya'ni `set-state-in-effect` sinfiga kirmaydi.
   *
   * `typeof` tekshiruvi MAJBURIY: jsdom `scrollIntoView` ni umuman
   * ta'riflamaydi va u yerda chaqiruv `TypeError` bilan butun komponentni
   * yiqitardi (test muhiti).
   */
  useEffect(() => {
    const node = currentRef.current;
    if (node && typeof node.scrollIntoView === "function") {
      node.scrollIntoView({ block: "nearest", inline: "center" });
    }
  }, [currentStep]);

  return (
    <nav
      aria-label={t("wizard.title")}
      className="md:sticky md:top-20 md:w-56 md:shrink-0 md:self-start"
    >
      {/*
       * Progress BITTA qatorda e'lon qilinadi: skrinrider foydalanuvchisi
       * yettita elementni sanab chiqmasligi kerak (§6.3).
       */}
      <p className="mb-3 text-xs text-text-muted" role="status">
        {t("wizard.progress", { done })}
      </p>

      <ol className="flex snap-x gap-2 overflow-x-auto pb-2 md:flex-col md:gap-1 md:overflow-x-visible md:pb-0">
        {views.map((view) => (
          <li
            className="snap-center"
            key={view.step.id}
            ref={view.state === "current" ? currentRef : undefined}
          >
            <StepItem view={view} />
          </li>
        ))}

        {/*
         * Kamera — massivning SAKKIZINCHI a'zosi EMAS (`wizard-steps.ts`
         * dagi sababga qarang), shuning uchun u shu yerda alohida
         * chiziladi va hech qanday sanoqqa qo'shilmaydi.
         */}
        <li className="snap-center">
          <span
            aria-disabled="true"
            className="flex min-h-11 min-w-11 items-center gap-2 rounded-md px-3 py-2 text-sm text-text-muted"
          >
            <Camera aria-hidden="true" className="size-4 text-text-muted" />
            <span className="whitespace-nowrap md:whitespace-normal">
              {t(CAMERA_PLACEHOLDER.labelKey)}
            </span>
          </span>
        </li>
      </ol>
    </nav>
  );
}

const ITEM_BASE =
  "flex min-h-11 min-w-11 items-center gap-2 rounded-md px-3 py-2 text-sm font-semibold transition-colors";

function StepItem({ view }: { view: WizardStepView }) {
  const t = useTranslations();

  const { step, state, blockerLabelKey } = view;
  const name = t(step.labelKey);

  const badge =
    state === "completed" ? (
      <Check aria-hidden="true" className="size-4 shrink-0" />
    ) : state === "blocked" ? (
      <Lock aria-hidden="true" className="size-4 shrink-0 text-text-muted" />
    ) : (
      <span
        aria-hidden="true"
        className={cn(
          "flex size-6 shrink-0 items-center justify-center rounded-full text-xs",
          state === "current"
            ? "bg-accent text-accent-fg"
            : "text-text-muted",
        )}
      >
        {step.id}
      </span>
    );

  const body = (
    <>
      {badge}
      <span className="whitespace-nowrap md:whitespace-normal">{name}</span>
      {/*
       * D-11: ixtiyoriy qadam AYNAN shunday belgilanadi — aks holda admin
       * o'zini bloklangan deb o'ylab, sotuvchilarsiz davom eta olmasligiga
       * ishonardi. Yorliq matn bo'lib hisoblangan nomga ham qo'shiladi.
       */}
      {step.optional ? (
        <span className="text-xs font-normal text-text-muted">
          {t("wizard.optional")}
        </span>
      ) : null}
    </>
  );

  if (state === "current") {
    return (
      <span
        aria-current="step"
        className={cn(ITEM_BASE, "bg-surface text-text")}
      >
        {body}
      </span>
    );
  }

  if (state === "blocked") {
    return (
      <span className="flex flex-col gap-1">
        <span
          aria-describedby={
            blockerLabelKey === null ? undefined : reasonId(step.id)
          }
          aria-disabled="true"
          className={cn(ITEM_BASE, "bg-surface-muted text-text-muted")}
        >
          {body}
        </span>
        {/*
         * Sabab DESKTOP'da element ostida doim ko'rinadi; mobil relsda u
         * ham gorizontal oqimda qoladi va bosishni talab qilmaydi —
         * "bosilganda ko'rsatish" varianti sababni klaviatura foydalanuvchisi
         * uchun yashirardi.
         */}
        {blockerLabelKey === null ? null : (
          <span className="text-xs text-text-muted" id={reasonId(step.id)}>
            {t("wizard.blockedBy", { name: t(blockerLabelKey) })}
          </span>
        )}
      </span>
    );
  }

  /*
   * Bajarilgan va to'ldirilmagan qadamlarning IKKALASI ham havola: orqaga
   * qaytish ERKIN va ogohlantirish dialogi YO'Q (§6.4) — holat serverda,
   * ya'ni qaytishda yo'qoladigan narsa yo'q.
   */
  return (
    <Link
      aria-label={t(
        state === "completed" ? "wizard.stepDone" : "wizard.stepPending",
        { n: step.id, name },
      )}
      className={cn(
        ITEM_BASE,
        "border border-border-ui bg-surface hover:bg-surface-muted",
        state === "completed" ? "text-text" : "text-text-muted",
      )}
      href={`${WIZARD_SETUP_PATH}?step=${step.id}`}
    >
      {body}
    </Link>
  );
}
