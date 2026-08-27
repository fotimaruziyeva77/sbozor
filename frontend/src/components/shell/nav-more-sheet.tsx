"use client";

import type { LucideIcon } from "lucide-react";

import { Dialog } from "@/components/ui/dialog";
import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/cn";

/*
 * Mobil "Ko'proq" varag'i (UI-SPEC §12.3).
 *
 * NEGA UMUMAN BOR: 2-faza navigatsiyani 8 bo'limga kengaytiradi, mobil
 * pastki panel esa 360px kenglikda 8 elementni ko'tara olmaydi (har biriga
 * ~45px tushardi va nishon o'lchami 44px dan pastga tushib, WCAG 2.5.8 ni
 * buzardi). Shuning uchun panelda eng ko'pi 5 element qoladi va qolganlari
 * shu varaqda ochiladi.
 *
 * YANGI BOG'LIQLIK YO'Q: mavjud `ui/dialog.tsx` ning `sheetOnMobile`
 * varianti ishlatiladi (UI-SPEC §1.4 — yangi npm paketi qo'shilmaydi).
 * Fokus tuzog'i, `Esc` va fokusning triggerga qaytishi Radix'dan keladi.
 *
 * DIQQAT: bu faylda foydalanuvchi matni YO'Q — sarlavha ham, yorliqlar ham
 * `next-intl` orqali chaqiruvchidan prop bo'lib keladi (02-02 qoidasi).
 */

export type NavSheetItem = {
  href: string;
  label: string;
  icon: LucideIcon;
  active: boolean;
};

export function NavMoreSheet({
  description,
  items,
  onOpenChange,
  open,
  title,
}: {
  description: string;
  items: readonly NavSheetItem[];
  onOpenChange: (open: boolean) => void;
  open: boolean;
  title: string;
}) {
  return (
    <Dialog.Root onOpenChange={onOpenChange} open={open}>
      <Dialog.Content
        description={description}
        sheetOnMobile
        srOnlyDescription
        title={title}
      >
        <ul className="flex flex-col gap-1">
          {items.map((item) => (
            <li key={item.href}>
              <Link
                aria-current={item.active ? "page" : undefined}
                className={cn(
                  // `min-h-11` — 44px barmoq nishoni (UI-SPEC §11).
                  "flex min-h-11 items-center gap-2 rounded-md px-3 text-sm font-semibold transition-colors",
                  item.active
                    ? "bg-surface-muted text-text"
                    : "text-text-muted hover:bg-surface-muted hover:text-text",
                )}
                href={item.href}
                /*
                 * Varaq havola bosilganda yopiladi. `Dialog.Close asChild`
                 * ATAYIN ishlatilmadi: u bolasidan ref uzatishni talab
                 * qiladi va navigatsiya `Link` i o'ralgan komponent —
                 * yopilish mas'uliyatini shu yerda ochiq ushlab turish
                 * bitta yashirin taxminni kamaytiradi.
                 */
                onClick={() => onOpenChange(false)}
              >
                <item.icon aria-hidden="true" className="size-4" />
                {item.label}
              </Link>
            </li>
          ))}
        </ul>
      </Dialog.Content>
    </Dialog.Root>
  );
}
