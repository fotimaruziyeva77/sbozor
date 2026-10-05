"use client";

import { useEffect, useRef } from "react";
import type { ComponentPropsWithRef, ComponentType, ReactNode } from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";

import { cn } from "@/lib/cn";

/*
 * Radix Dialog qobig'i — modal, fokus tuzog'i, Esc va fokus qaytishi
 * Radix'dan tekin keladi.
 *
 * NEGA AJRATILDI: bu overlay + content class satri 1-fazada UCH joyda
 * bir xil nusxada yashagan (`create-user-dialog`, `user-list`,
 * `temp-password-dialog`). 2-faza yana beshta dialog qo'shadi — nusxa
 * sakkiztaga chiqardi va fokus tuzog'i bir joyda buzilsa sakkizta ekranda
 * buzilardi.
 *
 * DIQQAT: bu faylda foydalanuvchiga ko'rinadigan matn YO'Q. `title` va
 * `description` `next-intl` orqali chaqiruvchidan prop bo'lib keladi.
 *
 * `Description` MAJBURIY: Radix uni `aria-describedby` ga bog'laydi va
 * usiz skrinrider foydalanuvchisi dialog nima so'rayotganini eshitmaydi.
 * Ko'rinishi shart bo'lmagan joyda `srOnlyDescription` ishlatiladi —
 * yo'q qilish emas.
 */

export type DialogSize = "sm" | "md" | "lg" | "xl";

/*
 * Kenglik sinflari LITERAL bo'lishi shart: Tailwind manba faylini skanerlaydi,
 * ish vaqtida yig'ilgan sinf nomi CSS'ga tushmaydi.
 */
const SIZE_CENTERED: Record<DialogSize, string> = {
  sm: "w-[min(26rem,calc(100vw-2rem))]",
  md: "w-[min(28rem,calc(100vw-2rem))]",
  lg: "w-[min(30rem,calc(100vw-2rem))]",
  /*
   * ⛔⛔ `xl` — KADR KO'RSATADIGAN OYNA UCHUN (261005, foydalanuvchi
   *     talabi: «juda kichkina, katta ko'rinishi kerak»).
   *
   *     `lg` 30rem = 480px. 16:9 kadr unda 480x270 bo'lib chiqadi —
   *     ya'ni bozor rastasini ko'rish uchun mo'ljallangan oyna
   *     telefonning yarmi hajmida edi. Rasta ustidagi raqamni ham,
   *     sotuvchini ham ajratib bo'lmasdi.
   *
   * ⚠ 72rem (1152px) — `app-shell` dagi kontent kengligi bilan BIR
   *   OILADAN. Undan kattasi 24" monitorda oynaning chekkalarini ko'z
   *   bir sakrashda qamrab olmaydigan masofaga chiqarardi (o'sha
   *   yerdagi 1600px chegarasi bilan ayni sabab).
   */
  xl: "w-[min(72rem,calc(100vw-2rem))]",
};

const SIZE_SHEET: Record<DialogSize, string> = {
  sm: "sm:w-[min(26rem,calc(100vw-2rem))]",
  md: "sm:w-[min(28rem,calc(100vw-2rem))]",
  lg: "sm:w-[min(30rem,calc(100vw-2rem))]",
  xl: "sm:w-[min(72rem,calc(100vw-2rem))]",
};

/**
 * Har ikkala variantda bir xil qoladigan qism.
 *
 * Holat animatsiyasi (09-UI-SPEC §12.4): Radix `data-state="open"|"closed"`
 * atributini O'ZI qo'yadi — yangi prop yo'q. Kirish `--motion-base`,
 * chiqish `--motion-fast` (§4.4 qoida 2: chiqish 2× tez). `starting:`
 * (`@starting-style`) kirish tranzitsiyasining boshlang'ich holatini beradi —
 * usiz element to'g'ridan-to'g'ri `open` holatda mount bo'lib, tranzitsiya
 * umuman o'ynamasdi [O'LCHANDI, 09-02 T1: Tailwind 4.3.3 `starting:` ni
 * `@starting-style` blokiga kompilyatsiya qiladi]. Reduced-motion'da global
 * blok `transition-duration` ni 0.01ms ga tushiradi — natija ayni, harakatsiz.
 */
const CONTENT_BASE = [
  "z-50 flex flex-col gap-4 overflow-y-auto border border-border bg-surface p-6 shadow-raised",
  "transition data-[state=closed]:duration-(--motion-fast) data-[state=open]:duration-(--motion-base)",
  "data-[state=open]:scale-100 data-[state=open]:opacity-100",
  "data-[state=closed]:scale-[0.96] data-[state=closed]:opacity-0",
  "starting:data-[state=open]:scale-[0.96] starting:data-[state=open]:opacity-0",
].join(" ");

/** Markazlashtirilgan modal — standart. */
const CONTENT_CENTERED =
  "fixed top-1/2 left-1/2 max-h-[calc(100vh-2rem)] -translate-x-1/2 -translate-y-1/2 rounded-lg";

/*
 * Mobil PASTKI VARAQ (UI-SPEC §7.6): `<640px` da ekranning pastiga
 * yopishadi, `sm:` dan boshlab markazlashgan modalga qaytadi. Faqat CSS —
 * ikkinchi komponent ham, ikkinchi bog'liqlik ham qo'shilmaydi.
 */
const CONTENT_SHEET = [
  "fixed inset-x-0 bottom-0 max-h-[85vh] w-full rounded-t-lg rounded-b-none",
  "sm:top-1/2 sm:right-auto sm:bottom-auto sm:left-1/2",
  "sm:max-h-[calc(100vh-2rem)] sm:-translate-x-1/2 sm:-translate-y-1/2",
  "sm:rounded-lg",
].join(" ");

export type DialogContentProps = Omit<
  ComponentPropsWithRef<typeof DialogPrimitive.Content>,
  "title"
> & {
  /** Dialog sarlavhasi — tarjima qilingan matn (`next-intl`). */
  title: ReactNode;
  /** `aria-describedby` mazmuni — tarjima qilingan matn. Majburiy. */
  description: ReactNode;
  /** Tavsif ko'rinmasin, lekin skrinrider uni o'qisin. */
  srOnlyDescription?: boolean;
  /** `<640px` da pastki varaq ko'rinishi (UI-SPEC §7.6 — rasta kartasi). */
  sheetOnMobile?: boolean;
  size?: DialogSize;
  /**
   * Sarlavha yonidagi ikonka (2026-08-25, foydalanuvchi: «iconlardan
   * foydalan») — dialog MAVZUSINI bir qarashda aytadi. Ixtiyoriy:
   * bermagan chaqiruvchi avvalgidek yalang'och sarlavha oladi.
   */
  icon?: ComponentType<{ className?: string; "aria-hidden"?: boolean }>;
  /** Ikonka diski ohangi — destruktiv dialoglar qizil disk oladi. */
  iconTone?: "accent" | "danger";
  /**
   * Portal manzili — berilmasa `document.body` (Radix standarti).
   *
   * ⚠ NEGA KERAK (2026-08-25, to'lov modali): kassir oqimining testlari
   *   kontraktni `container` DOIRASIDA o'lchaydi; body-portal ularni
   *   ko'r qilib qo'ydi (8 test yiqildi — o'lchandi). Chaqiruvchi o'z
   *   daraxtidagi elementni bersa, modal o'sha yerga chiziladi —
   *   `position: fixed` tufayli VIZUAL farq yo'q.
   */
  portalContainer?: HTMLElement | null;
  /**
   * `Root modal={false}` bilan JUFT ishlatiladigan overlay (2026-08-25,
   * to'lov modali): Radix o'z Overlay'ini faqat modal rejimda chizadi.
   *
   * ⚠ NEGA modal EMAS: modal rejimning fokus qafasi `focus()` ni o'sha
   *   zahoti ichkariga qaytaradi — kassir oqimining «to'lovdan keyin
   *   fokus qidiruvda» shartnomasi (§8.3/§8.5) sinxron buziladi
   *   (o'lchandi). Qafassiz dialog + shu yassi overlay ko'rinishni
   *   saqlaydi, klaviaturani esa bo'shatadi.
   */
  plainOverlay?: boolean;
};

const ICON_TONE = {
  accent: "bg-accent/12 text-accent-text",
  danger: "bg-danger/10 text-danger-text",
} as const;

function DialogContent({
  children,
  className,
  description,
  icon: Icon,
  iconTone = "accent",
  plainOverlay = false,
  portalContainer,
  sheetOnMobile = false,
  size = "md",
  srOnlyDescription = false,
  title,
  ...props
}: DialogContentProps) {
  /*
   * ⛔⛔ FOKUS CHAQIRGAN ELEMENTGA QAYTADI (K-04 auditi, 2026-08-25).
   *
   *   Radix trigger orqali ochilganda fokusni O'ZI qaytaradi, lekin bu
   *   loyihada dialoglar BOSHQARILADIGAN `open` bilan, `DialogTrigger`siz
   *   ochiladi — o'shanda Escape fokusni `body` ga tashlaydi va
   *   klaviatura foydalanuvchisi ro'yxat BOSHIGA tushib qoladi
   *   (auditda o'lchangan).
   *
   *   Yechim: mount paytida `document.activeElement` (chaqirgan tugma)
   *   eslab qolinadi, `onCloseAutoFocus` esa Radix'ning standart
   *   xulqini bekor qilib, fokusni AYNAN o'sha elementga qaytaradi.
   *
   * ⚠ `useRef` + mount effekti — render paytida DOM o'qilmaydi.
   */
  const openerRef = useRef<HTMLElement | null>(null);
  useEffect(() => {
    openerRef.current =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
  }, []);

  return (
    <DialogPrimitive.Portal container={portalContainer ?? undefined}>
      {/*
       * Fon 8% qorayadi + blur(4px) [L-3 xoreografiya oilasi, §4.4 qoida 3]:
       * ajratishni qorong'ilik emas, xiralik beradi — Apple-uslub.
       */}
      {plainOverlay ? (
        <div
          aria-hidden="true"
          className="fixed inset-0 z-50 bg-black/8 backdrop-blur-[4px]"
        />
      ) : (
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/8 backdrop-blur-[4px]" />
      )}
      <DialogPrimitive.Content
        className={cn(
          CONTENT_BASE,
          sheetOnMobile ? CONTENT_SHEET : CONTENT_CENTERED,
          sheetOnMobile ? SIZE_SHEET[size] : SIZE_CENTERED[size],
          className,
        )}
        {...props}
        /* ⚠ SPREAD'DAN KEYIN — chaqiruvchi bergan handler yutib
         *   yubormasin; uniki baribir ichkarida chaqiriladi. */
        onCloseAutoFocus={(event) => {
          props.onCloseAutoFocus?.(event);
          if (
            !event.defaultPrevented &&
            openerRef.current !== null &&
            openerRef.current.isConnected
          ) {
            event.preventDefault();
            openerRef.current.focus();
          }
        }}
      >
        <div className="flex items-start gap-3">
          {Icon === undefined ? null : (
            <span
              aria-hidden="true"
              className={cn(
                "grid size-11 shrink-0 place-items-center rounded-xl",
                ICON_TONE[iconTone],
              )}
            >
              <Icon aria-hidden className="size-5" />
            </span>
          )}
          <div className="flex min-w-0 flex-col gap-0.5">
            <DialogPrimitive.Title className="text-lg font-semibold">
              {title}
            </DialogPrimitive.Title>
            <DialogPrimitive.Description
              className={cn(
                srOnlyDescription ? "sr-only" : "text-sm text-text-muted",
              )}
            >
              {description}
            </DialogPrimitive.Description>
          </div>
        </div>
        {children}
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}

/*
 * Tugmalar qatori. Mobil'da USTMA-UST (to'liq kenglik — barmoq nishoni),
 * `sm:` dan boshlab `row-reverse`: birlamchi/destruktiv tugma O'NGDA,
 * bekor qilish CHAPDA (UI-SPEC §10.6).
 */
function DialogFooter({ className, ...props }: ComponentPropsWithRef<"div">) {
  return (
    <div
      className={cn("flex flex-col gap-2 sm:flex-row-reverse", className)}
      {...props}
    />
  );
}

export const Dialog = {
  Root: DialogPrimitive.Root,
  Trigger: DialogPrimitive.Trigger,
  Close: DialogPrimitive.Close,
  Content: DialogContent,
  Footer: DialogFooter,
};
