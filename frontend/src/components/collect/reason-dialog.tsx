"use client";

import { useId, useState } from "react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Dialog } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import {
  ADJUSTMENT_REASONS,
  REVERSAL_REASONS,
  soumSchema,
} from "@/lib/api-types";
import type {
  AdjustmentReasonValue,
  ReversalReasonValue,
} from "@/lib/api-types";

/*
 * =============================================================================
 * DL-1 / DL-2 — SABAB-KOD DIALOGI (UI-SPEC §4.4, §8.6, §8.8, §13.5).
 *
 * ⛔⛔ BU DIALOG ATAYIN QIMMAT — VA QIMMATLIK DIZAYN TALABI.
 *
 *   Summani o'zgartirish — ISTISNO, va uning narxi baxtli yo'lning
 *   narxidan YUQORI bo'lishi SHART. Aks holda kassir uni har rastada
 *   bosib, tarifni EFFEKTIV RAVISHDA bekor qilardi va BILL-01 ning butun
 *   ma'nosi (o'zgarmas, tarifga asoslangan patta) yo'qolardi.
 *
 *   Shuning uchun bu yerda uch qo'shimcha o'zaro ta'sir bor: dialogni
 *   ochish, sababni tanlash, tasdiqlash — va sabab tanlanmaguncha tasdiq
 *   `aria-disabled`. Bu ANTI-AFFORDANS va u ataylab.
 *
 * ⛔ `data-collect-step` YO'Q: override baxtli yo'lning qadami EMAS, ya'ni
 *    u G-20 sanog'iga KIRMASLIGI kerak. Kirsa, «uch qadam» da'vosi
 *    override yo'lida ham rost bo'lib qolardi va D-18 o'z ma'nosini
 *    yo'qotardi.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ ERKIN MATN MAYDONI YO'Q (D-19) — VA BU DOM DARAJASIDA O'LCHANADI
 * -----------------------------------------------------------------------
 * Na `<textarea>`, na matn turidagi sabab maydoni. Sabab ochiq: erkin
 * matn hisobotda GURUHLANMAYDI va amalda BO'SH qoladi — yoki, yomoni,
 * «boshqa» eng katta guruh bo'lib qolardi.
 *
 * ⛔ `other` / `custom` sabab-kodi ham YO'Q (06-RESEARCH OQ-3): u erkin
 *    matnni ORQA ESHIKDAN qaytarib keltirardi.
 *
 * ⛔ RO'YXAT REYESTRDAN ITERATSIYA QILINADI (D-32), qo'lda yozilmaydi.
 *    Qo'lda yozilgan ro'yxat backendga yangi a'zo qo'shilganda JIMGINA
 *    eskirardi va G-24 ni ham, ekranni ham ajratib yuborardi.
 *
 * -----------------------------------------------------------------------
 * ⚠ `size="sm"` — ATAYLAB KICHIK (§4.4)
 * -----------------------------------------------------------------------
 * Dialog BITTA EKRANGA sig'ishi kerak: telefonda skroll qilinadigan
 * dialogda «tasdiqlash» ko'rinmay qolsa, kassir uni TOPMAYDI va oqim
 * to'xtaydi — bozor sharoitida bu «tizim ishlamayapti» degan xulosa.
 *
 * ⚠ `mode="reversal"` da mavjud `ConfirmDialog` (1-daraja) ishlatiladi:
 *   bekor qilish — DESTRUKTIV amal va uning tasdiq shakli kodbazada
 *   allaqachon bir marta hal qilingan (fokus destruktiv tugmada EMAS).
 *   ⚠ `ConfirmDialog` ning yagona bloklash kirishi — `isBusy`, shuning
 *   uchun «sabab tanlanmagan» sharti shu prop orqali uzatiladi va
 *   sababning O'ZI `children` da `role="status"` bilan aytiladi.
 * =============================================================================
 */

export type ReasonDialogResult =
  | {
      mode: "override";
      reasonCode: AdjustmentReasonValue;
      amountSoum: number;
    }
  | { mode: "reversal"; reasonCode: ReversalReasonValue };

export type ReasonDialogProps = {
  mode: "override" | "reversal";
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: (result: ReasonDialogResult) => void;
};

/** ⛔ Manfiy VA NOL rad etiladi — `money.py` chegarasi bilan bir xil. */
function parseAmount(raw: string): number | null {
  const value = Number(raw);
  if (!Number.isInteger(value) || value <= 0) return null;
  return soumSchema.safeParse(value).success ? value : null;
}

export function ReasonDialog({
  mode,
  open,
  onOpenChange,
  onConfirm,
}: ReasonDialogProps) {
  const t = useTranslations();
  const adjustmentLabel = useTranslations("collect.adjustmentReason");
  const reversalLabel = useTranslations("collect.reversalReason");

  const reasonId = useId();
  const amountId = useId();

  /* ⛔ Bo'sh satr — «tanlanmagan». `placeholder` TANLOV sifatida qabul
   *    qilinmaydi va u aynan shu qiymat orqali ajratiladi. */
  const [reasonCode, setReasonCode] = useState("");
  const [rawAmount, setRawAmount] = useState("");

  const amount = parseAmount(rawAmount);
  const blocked =
    reasonCode === "" || (mode === "override" && amount === null);

  function reset(): void {
    setReasonCode("");
    setRawAmount("");
  }

  function handleOpenChange(next: boolean): void {
    if (!next) reset();
    onOpenChange(next);
  }

  function handleConfirm(): void {
    if (blocked) return;
    if (mode === "override") {
      if (amount === null) return;
      onConfirm({
        mode: "override",
        reasonCode: reasonCode as AdjustmentReasonValue,
        amountSoum: amount,
      });
    } else {
      onConfirm({
        mode: "reversal",
        reasonCode: reasonCode as ReversalReasonValue,
      });
    }
    reset();
  }

  /*
   * ⛔ RO'YXAT REYESTRDAN — qo'lda yozilgan `<option>` lar YO'Q.
   *    `mode` reyestrni tanlaydi, elementlarni EMAS.
   */
  const reasonSelect = (
    <Field
      id={reasonId}
      label={
        mode === "override"
          ? t("collect.reasonLabel")
          : t("collect.reverseReasonLabel")
      }
    >
      <Select
        id={reasonId}
        onChange={(event) => setReasonCode(event.target.value)}
        value={reasonCode}
      >
        <option value="">{t("collect.reasonPlaceholder")}</option>
        {mode === "override"
          ? ADJUSTMENT_REASONS.map((code) => (
              <option key={code} value={code}>
                {adjustmentLabel(code)}
              </option>
            ))
          : REVERSAL_REASONS.map((code) => (
              <option key={code} value={code}>
                {reversalLabel(code)}
              </option>
            ))}
      </Select>
    </Field>
  );

  /* §14.3: `aria-disabled` bosilganda SABAB aytiladi — jim turmaydi. */
  const blockedHint =
    blocked && reasonCode === "" ? (
      <p className="text-sm text-text-muted" role="status">
        {t("collect.errorFix.reason_required")}
      </p>
    ) : null;

  if (mode === "reversal") {
    return (
      <ConfirmDialog
        cancelLabel={t("common.close")}
        confirmLabel={t("collect.reverse")}
        description={t("collect.errorFix.reason_required")}
        isBusy={blocked}
        onConfirm={handleConfirm}
        onOpenChange={handleOpenChange}
        open={open}
        title={t("collect.reverseTitle")}
      >
        {reasonSelect}
        {blockedHint}
      </ConfirmDialog>
    );
  }

  return (
    <Dialog.Root onOpenChange={handleOpenChange} open={open}>
      <Dialog.Content
        description={t("collect.errorFix.reason_required")}
        sheetOnMobile
        size="sm"
        title={t("collect.override")}
      >
        {reasonSelect}

        {/*
         * ⛔ Maydon turi RAQAMLI KLAVIATURA bilan, LEKIN matn turi EMAS:
         *    G-24(c) DOM darajasida `textarea` va matn maydonining
         *    yo'qligini TO'PLAM TENGLIGI bilan o'lchaydi.
         */}
        <Field
          error={
            rawAmount !== "" && amount === null
              ? t("collect.errorCause.amount_unavailable")
              : undefined
          }
          id={amountId}
          label={t("collect.newAmountLabel")}
        >
          <Input
            aria-invalid={rawAmount !== "" && amount === null ? true : undefined}
            autoComplete="off"
            className="min-h-14 font-mono tabular-nums"
            id={amountId}
            inputMode="numeric"
            onChange={(event) => setRawAmount(event.target.value)}
            value={rawAmount}
          />
        </Field>

        {blockedHint}

        <Dialog.Footer>
          <Button
            aria-disabled={blocked ? true : undefined}
            className="sm:flex-1"
            onClick={handleConfirm}
            variant="secondary"
          >
            {t("common.save")}
          </Button>
          <Dialog.Close asChild>
            <Button className="sm:flex-1" variant="ghost">
              {t("common.cancel")}
            </Button>
          </Dialog.Close>
        </Dialog.Footer>
      </Dialog.Content>
    </Dialog.Root>
  );
}
