"use client";

import { useId, useRef, useState } from "react";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import type { ButtonProps } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";

/*
 * Destruktiv amal tasdig'i — IKKI DARAJA (UI-SPEC §10.6).
 *
 *   1-daraja — sarlavha + tavsif + [Bekor qilish] [Fe'l].
 *              Amalni UI'dan qaytarish mumkin (tarifni tiklash,
 *              biriktirishni qayta ochish).
 *   2-daraja — qo'shimcha: foydalanuvchi AYNAN `typeToConfirm` matnini
 *              yozmaguncha tasdiq bloklanadi. Faqat UI'dan QAYTARIB
 *              BO'LMAYDIGAN amallar uchun: qoralama bozorni kaskad
 *              o'chirish va rastani yopish (raqam abadiy iste'moldan
 *              chiqadi).
 *
 * `aria-disabled`, `disabled` EMAS: `disabled` tugma fokus olmaydi va
 * skrinrider uni umuman o'qimaydi, ya'ni "nega bosilmayapti?" savoliga
 * javob beradigan joy qolmaydi. `aria-disabled` esa fokuslanadi va e'lon
 * qilinadi; bosilganda fokus yetishmayotgan maydonga ko'chadi.
 *
 * FOKUS OCHILGANDA hech qachon destruktiv tugmada bo'lmaydi — 1-darajada
 * bekor qilishda, 2-darajada matn maydonida.
 *
 * DIQQAT: bu faylda matn YO'Q — barcha yorliqlar `next-intl` orqali
 * chaqiruvchidan prop bo'lib keladi. Tasdiq tugmasining yorlig'i GENERIC
 * "Tasdiqlash" BO'LMASLIGI kerak: foydalanuvchi ko'pincha dialog matnini
 * o'qimasdan tugmaga qarab qaror qiladi (§10.6).
 */

type ConfirmDialogBase = {
  /** Bekor qilish tugmasining yorlig'i (`common.cancel`). */
  cancelLabel: string;
  /** Xato bloki yoki qo'shimcha kontekst — chaqiruvchi beradi. */
  children?: ReactNode;
  /** Tasdiq tugmasining yorlig'i — O'Z FE'LI, "Tasdiqlash" emas. */
  confirmLabel: string;
  /**
   * Standart `destructive` — bu dialogning asosiy vazifasi shu.
   *
   * ISTISNO uchun ochiq qoldirildi: TIKLOVCHI amal (bloklangan
   * foydalanuvchini ochish) ham tasdiq so'raydi, lekin uni qizil qilish
   * foydalanuvchiga yolg'on xavf signali beradi va qizil rangning
   * ma'nosini yemiradi.
   */
  confirmVariant?: ButtonProps["variant"];
  description: ReactNode;
  /** So'rov ketayotganda tasdiqni bloklaydi. */
  isBusy?: boolean;
  onConfirm: () => void;
  onOpenChange: (open: boolean) => void;
  open: boolean;
  title: string;
};

export type ConfirmDialogProps =
  | (ConfirmDialogBase & {
      level?: 1;
      typeToConfirm?: never;
      typeToConfirmLabel?: never;
    })
  | (ConfirmDialogBase & {
      level: 2;
      /** Foydalanuvchi AYNAN shu matnni yozishi shart (rasta raqami, bozor nomi). */
      typeToConfirm: string;
      /** Matn maydonining yorlig'i — tarjima qilingan. */
      typeToConfirmLabel: string;
    });

export function ConfirmDialog(props: ConfirmDialogProps) {
  const {
    cancelLabel,
    children,
    confirmLabel,
    confirmVariant = "destructive",
    description,
    isBusy = false,
    onConfirm,
    onOpenChange,
    open,
    title,
  } = props;

  const inputId = useId();
  const [typed, setTyped] = useState("");
  const cancelRef = useRef<HTMLButtonElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const needsTyping = props.level === 2;
  // Bo'shliq kesiladi: nusxa-joylashtirishdagi tasodifiy probel amalni
  // to'sib qo'ymasligi kerak, lekin katta-kichik harf FARQ QILADI.
  const typedMatches = needsTyping
    ? typed.trim() === props.typeToConfirm.trim()
    : true;
  const blocked = isBusy || !typedMatches;

  function handleOpenChange(next: boolean) {
    // Yozilgan matn dialog bilan birga o'ladi — qayta ochilganda tasdiq
    // yana noldan so'raladi.
    if (!next) setTyped("");
    onOpenChange(next);
  }

  function handleConfirm() {
    if (blocked) {
      // So'rov YUBORILMAYDI; fokus yetishmayotgan maydonga ko'chadi.
      if (!typedMatches) inputRef.current?.focus();
      return;
    }
    onConfirm();
  }

  return (
    <Dialog.Root onOpenChange={handleOpenChange} open={open}>
      <Dialog.Content
        description={description}
        onOpenAutoFocus={(event) => {
          event.preventDefault();
          if (needsTyping) inputRef.current?.focus();
          else cancelRef.current?.focus();
        }}
        size="sm"
        title={title}
      >
        {children}

        {needsTyping ? (
          <Field id={inputId} label={props.typeToConfirmLabel}>
            <Input
              autoComplete="off"
              id={inputId}
              onChange={(event) => setTyped(event.target.value)}
              ref={inputRef}
              value={typed}
            />
          </Field>
        ) : null}

        <Dialog.Footer>
          <Button
            aria-disabled={blocked ? true : undefined}
            className="sm:flex-1"
            onClick={handleConfirm}
            variant={confirmVariant}
          >
            {confirmLabel}
          </Button>
          <Dialog.Close asChild>
            <Button className="sm:flex-1" ref={cancelRef} variant="secondary">
              {cancelLabel}
            </Button>
          </Dialog.Close>
        </Dialog.Footer>
      </Dialog.Content>
    </Dialog.Root>
  );
}
