"use client";

import { useEffect } from "react";
import { Loader2, Lock } from "lucide-react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { HUMAN_ANSWERS } from "@/lib/api-types";
import type { HumanAnswer } from "@/lib/api-types";

/*
 * =============================================================================
 * UCHTA JAVOB TUGMASI — VA UCHINCHISI HAM QONUNIY (UI-SPEC §7.3).
 *
 * «Aniq ayta olmayman» — TO'LIQ HUQUQLI javob. Uni olib tashlash
 * nazoratchini TAXMIN QILISHGA majburlardi va xolis o'lchovga ataylab
 * shovqin qo'shardi (`HUMAN_VERDICT_CHECK` docstringi). U aniqlik
 * matritsasidan TASHQARIDA sanaladi (O-06), ya'ni «xato» ham, «to'g'ri»
 * ham emas — u KADR SIFATI haqidagi ma'lumot.
 *
 * -----------------------------------------------------------------------
 * ⛔ `event.repeat` E'TIBORSIZ QOLDIRILADI — VA BU O'LCHANADIGAN QOIDA
 * -----------------------------------------------------------------------
 * Klaviatura yorliqlari (`1`/`2`/`3`) halol ishni tezlashtiradi. Lekin
 * tugmani BOSIB TURISH brauzerda `keydown` ni sekundiga o'nlab marta
 * qo'zg'atadi va usiz bitta bosish O'NLAB javob yuborardi — ya'ni
 * nazoratchi ko'rmagan bandlarga javob yozilardi va ular hisobotga
 * «nazoratchi tasdiqladi» bo'lib kirardi. Bu ommaviy tasdiqlashning
 * KLAVIATURA SHAKLI (D-18) va shuning uchun u test bilan qulflangan.
 *
 * -----------------------------------------------------------------------
 * ⛔ CHECKBOX, KO'P TANLASH, «TANLANGANLARNI TASDIQLASH» — YO'Q (D-18)
 * -----------------------------------------------------------------------
 * G-18(b) `components/review/**` va `components/blind-audit/**` da
 * `type="checkbox"` ni va massiv bilan yuboriladigan mutatsiyani
 * skanerlaydi. Shart shu faylda AMALDA bajariladi: har javob AYNAN
 * bitta qiymat yuboradi.
 *
 * -----------------------------------------------------------------------
 * ⚠ `aria-disabled`, `disabled` EMAS (§13.3)
 * -----------------------------------------------------------------------
 * `disabled` tugma fokus olmaydi va skrinrider uni umuman o'qimaydi,
 * ya'ni «nega bosilmayapti?» savoliga javob beradigan joy qolmaydi.
 * `aria-disabled` esa fokuslanadi, e'lon qilinadi va bosilganda SABAB
 * ko'rsatiladi.
 * =============================================================================
 */

/**
 * Javob -> tarjima kaliti.
 *
 * ⚠ `Record<HumanAnswer, …>` ATAYIN: yangi javob qiymati qo'shilsa
 *   (yoki olib tashlansa) BU YER kompilyatsiya vaqtida qizaradi. Kalit
 *   matnining mavjudligini esa `src/global.ts` ning augmentatsiyasi
 *   tekshiradi — ya'ni ikkala yo'nalish ham kompilyatorda.
 */
const LABEL_KEY: Record<
  HumanAnswer,
  "review.answerOccupied" | "review.answerEmpty" | "review.answerUnclear"
> = {
  occupied: "review.answerOccupied",
  empty: "review.answerEmpty",
  uncertain: "review.answerUnclear",
};

export type DecisionBarProps = {
  /** Darvoza YOPIQ bo'lsa uchala tugma ham `aria-disabled`. */
  blocked: boolean;
  /** Javob yozilgan bo'lsa tugmalarda qulf ikonkasi ko'rinadi. */
  locked?: boolean;
  /** Yuborilayotgan javob — o'sha tugmada `Loader2`. */
  pendingAnswer?: HumanAnswer | null;
  /** Bloklangan holatda bosilsa ko'rsatiladigan sabab. */
  onBlockedPress: () => void;
  onAnswer: (answer: HumanAnswer) => void;
};

export function DecisionBar({
  blocked,
  locked = false,
  pendingAnswer = null,
  onBlockedPress,
  onAnswer,
}: DecisionBarProps) {
  const t = useTranslations();

  /*
   * Klaviatura yorliqlari — `1` / `2` / `3` (§13.5).
   *
   * ⛔ `event.repeat === true` DARHOL QAYTARADI. Yuqoridagi blokka
   *    qarang: usiz tugmani bosib turish ketma-ket javob yuborardi.
   *
   * ⚠ FORMA MAYDONIDA YORLIQ ISHLAMAYDI: bu ekranda matn maydoni yo'q,
   *   lekin dialog ochilganda (yaqinlashtirish, chiqish tasdig'i) u
   *   YOPILISHI kerak — aks holda `1` bosish dialog ustidan javob
   *   yuborardi. Shuning uchun ishlovchi `blocked` bo'lganda ham hech
   *   nima yubormaydi va dialoglar `blocked` ni ko'taradi.
   */
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.repeat) return;
      if (event.altKey || event.ctrlKey || event.metaKey) return;

      const index = ["1", "2", "3"].indexOf(event.key);
      if (index === -1) return;

      const target = event.target;
      if (
        target instanceof HTMLElement &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.isContentEditable)
      ) {
        return;
      }

      event.preventDefault();
      if (blocked) {
        onBlockedPress();
        return;
      }
      onAnswer(HUMAN_ANSWERS[index]);
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [blocked, onAnswer, onBlockedPress]);

  return (
    <div className="flex flex-col gap-2">
      <p className="text-lg font-semibold">{t("review.question")}</p>

      <div className="flex flex-col gap-2 sm:flex-row">
        {HUMAN_ANSWERS.map((answer, index) => (
          <Button
            aria-disabled={blocked ? true : undefined}
            className="sm:flex-1"
            key={answer}
            onClick={() => {
              if (blocked) {
                onBlockedPress();
                return;
              }
              onAnswer(answer);
            }}
            size="lg"
            variant="secondary"
          >
            {pendingAnswer === answer ? (
              <Loader2
                aria-hidden="true"
                className="animate-spin motion-reduce:animate-none"
              />
            ) : locked ? (
              <Lock aria-hidden="true" />
            ) : (
              <span aria-hidden="true" className="font-mono text-xs">
                {index + 1}
              </span>
            )}
            {t(LABEL_KEY[answer])}
          </Button>
        ))}
      </div>

      <p className="text-xs text-text-muted">{t("review.shortcutHint")}</p>
    </div>
  );
}
