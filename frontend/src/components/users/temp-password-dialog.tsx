"use client";

import { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { Check, Copy } from "lucide-react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";

/*
 * =============================================================================
 * VAQTINCHALIK PAROL — BIR MARTA KO'RSATILADI (D-02, T-01-68).
 *
 * Parol butun umri davomida faqat ikki joyda bo'ladi: HTTP javobining
 * tanasida va shu komponentning `props` ida. Dialog yopilganda ota-komponent
 * uni `null` ga o'rnatadi va qiymat React holatidan butunlay chiqib ketadi.
 *
 * ATAYIN QILINMAYDI:
 *   - diagnostika chiqishiga yozish (grep darvozasi bilan qulflangan);
 *   - URL yoki so'rov parametriga qo'yish — u brauzer tarixida va server
 *     kirish jurnalida qolib ketardi;
 *   - brauzer omboriga saqlash (T-01-60 bilan bir xil sabab);
 *   - React Query keshiga tushirish (shuning uchun `useMutation`).
 *
 * Nusxa olish tugmasi bundan istisno emas: buferga yozish foydalanuvchining
 * ANIQ harakati va u brauzerdan tashqariga chiqmaydi.
 * =============================================================================
 */

export function TempPasswordDialog({
  password,
  onClose,
}: {
  password: string | null;
  onClose: () => void;
}) {
  const t = useTranslations();
  const [copied, setCopied] = useState(false);

  function handleOpenChange(open: boolean) {
    if (open) return;
    // Parol ota-komponent holatidan tozalanadi — bu dialogning yagona
    // yopilish yo'li (Escape, tashqariga bosish va tugma ham shu yerga keladi).
    setCopied(false);
    onClose();
  }

  async function copyToClipboard() {
    if (!password) return;
    try {
      await navigator.clipboard.writeText(password);
      setCopied(true);
    } catch {
      // Buferga ruxsat berilmagan (HTTPS bo'lmagan kontekst yoki rad javobi).
      // Parol baribir ekranda ko'rinib turibdi — oqim to'xtamaydi.
    }
  }

  return (
    <Dialog.Root onOpenChange={handleOpenChange} open={password !== null}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40" />
        <Dialog.Content className="fixed top-1/2 left-1/2 z-50 flex w-[min(28rem,calc(100vw-2rem))] -translate-x-1/2 -translate-y-1/2 flex-col gap-4 rounded-lg border border-border bg-surface p-6 shadow-raised">
          <Dialog.Title className="text-lg font-semibold">
            {t("users.tempPasswordTitle")}
          </Dialog.Title>

          <Dialog.Description className="text-sm text-text-muted">
            {t("users.tempPasswordWarning")}
          </Dialog.Description>

          <p
            className="rounded-md border border-border bg-surface-muted px-4 py-3 text-center font-mono text-xl tracking-wider break-all select-all"
            data-testid="temporary-password"
          >
            {password}
          </p>

          <div className="flex flex-col gap-2 sm:flex-row-reverse">
            <Button className="sm:flex-1" onClick={() => void copyToClipboard()}>
              {copied ? (
                <Check aria-hidden="true" />
              ) : (
                <Copy aria-hidden="true" />
              )}
              {copied ? t("users.copied") : t("users.copy")}
            </Button>

            <Dialog.Close asChild>
              <Button className="sm:flex-1" variant="secondary">
                {t("common.close")}
              </Button>
            </Dialog.Close>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
