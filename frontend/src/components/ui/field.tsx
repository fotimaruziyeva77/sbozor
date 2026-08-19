import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

/*
 * Forma maydoni: yorliq + boshqaruv elementi + xato + izoh.
 *
 * DIQQAT: bu faylda matn YO'Q — `label`, `error` va `hint` tarjima
 * qilingan holda chaqiruvchidan keladi.
 *
 * ID KONVENSIYASI (chaqiruvchi shu ikki nomga tayanadi):
 *   xato izohi  -> `${id}-error`
 *   yordam izohi -> `${id}-hint`
 *
 * Boshqaruv elementining o'zi `aria-describedby` va `aria-invalid` ni
 * OLADI — `Field` ularni majburlamaydi. Sabab: `cloneElement` bilan
 * bolaga atribut tiqish `children` ning haqiqiy shaklini yashiradi va
 * `<div>` o'ralgan yoki ikkita boshqaruv elementi bo'lgan holatlarda
 * jimgina noto'g'ri elementga yopishadi. Ochiq shartnoma halolroq:
 *
 *   <Field error={errors.phone?.message} id="phone" label={t("...")}>
 *     <Input
 *       aria-describedby={errors.phone ? "phone-error" : undefined}
 *       aria-invalid={errors.phone ? true : undefined}
 *       id="phone"
 *     />
 *   </Field>
 */
export type FieldProps = {
  children: ReactNode;
  className?: string;
  /** Tarjima qilingan xato matni. Bo'lsa `${id}-error` idsi bilan chiqadi. */
  error?: string;
  /** Yordamchi izoh. Bo'lsa `${id}-hint` idsi bilan chiqadi. */
  hint?: string;
  /** Boshqaruv elementining `id` si — yorliq va izoh shunga bog'lanadi. */
  id: string;
  label: ReactNode;
  /*
   * ⛔ `lg` — LANDING formasi uchun (260819). Ilova formalarida 12px
   *    izoh to'g'ri: u zich ekranda qo'shimcha satr, o'qilishi shart
   *    emas. Landingda esa izoh BEGONA odamga yozilgan («shu raqamga
   *    qo'ng'iroq qilamiz») va 12px da u shunchaki ko'rinmaydi.
   *
   * ⛔ Yorliq `lg` da ham `text-sm` bo'lib qoladi va bu ONGLI: yorliq
   *    maydon MATNIDAN (18px) kichik bo'lishi kerak, aks holda ikkalasi
   *    bir og'irlikda bo'lib ierarxiya yo'qoladi.
   */
  size?: "md" | "lg";
};

export function Field({
  children,
  className,
  error,
  hint,
  id,
  label,
  size = "md",
}: FieldProps) {
  return (
    <div className={cn("flex flex-col gap-2", className)}>
      <label className="text-sm font-semibold" htmlFor={id}>
        {label}
      </label>
      {children}
      {hint ? (
        <p
          className={cn(
            size === "lg" ? "text-sm" : "text-xs",
            "text-text-muted",
          )}
          id={`${id}-hint`}
        >
          {hint}
        </p>
      ) : null}
      {/*
       * `text-danger-text` — `--color-danger` matn sifatida tint fonda
       * o'lchangan 3.97:1 beradi (WCAG 1.4.3 buzilishi). Rang YAGONA
       * signal emas: yonida `aria-invalid` va matnning o'zi turadi.
       *
       * `.motion-shake` (09-UI-SPEC §12.7) — xato PARAGRAFI 2px shake
       * (200ms, bir marta, `globals.css` reyestridan). Karta emas, paragraf:
       * login kartasi shake QILMAYDI (§17.2 — «ayblov» hissi). Xato paydo
       * bo'lganda `<p>` yangidan mount bo'ladi — animatsiya shu lahzada bir
       * marta o'ynaydi. Reduced-motion'da global blok 0.01ms ga tushiradi —
       * faqat matn qoladi. `FieldProps` kontrakti O'ZGARMAGAN.
       */}
      {error ? (
        <p
          className={cn("text-sm text-danger-text", "motion-shake")}
          id={`${id}-error`}
        >
          {error}
        </p>
      ) : null}
    </div>
  );
}
