"use client";

import { useState } from "react";
import { Check, Copy, KeyRound } from "lucide-react";
import { useFormatter, useLocale, useTimeZone, useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import type { EdgeActivationCode } from "@/lib/api-types";
import { formatInstant } from "@/lib/format-day";

/**
 * Aktivatsiya kodini KATTA va nusxalanadigan qilib ko'rsatadi.
 *
 * `users/temp-password-dialog.tsx` naqshi: kod bir martalik, dialog
 * yopilgach u qayta ko'rsatilmaydi — kerak bo'lsa yangisi olinadi.
 */
export function ActivationCodeDialog({
  code,
  onClose,
}: {
  code: EdgeActivationCode | null;
  onClose: () => void;
}) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();
  const timeZone = useTimeZone();
  const [copied, setCopied] = useState(false);

  function handleOpenChange(open: boolean) {
    if (open) return;
    setCopied(false);
    onClose();
  }

  async function copyToClipboard() {
    if (!code) return;
    try {
      await navigator.clipboard.writeText(code.code);
      setCopied(true);
    } catch {
      // Clipboard rad etilsa kod ekranda turibdi va `select-all` bilan
      // qo'lda belgilanadi — xato ko'rsatishga arzimaydi.
    }
  }

  const expires = code === null ? null : new Date(code.expires_at);

  return (
    <Dialog.Root onOpenChange={handleOpenChange} open={code !== null}>
      <Dialog.Content
        description={t("edgeAgents.codeInstruction")}
        icon={KeyRound}
        title={t("edgeAgents.codeTitle")}
      >
        <p
          className="rounded-md border border-border bg-surface-muted px-4 py-4 text-center font-mono text-2xl font-semibold tracking-widest break-all select-all"
          data-testid="activation-code"
        >
          {code?.code}
        </p>

        {expires !== null && !Number.isNaN(expires.getTime()) ? (
          <p className="text-sm text-text-muted">
            {t("edgeAgents.codeExpires", {
              date: formatInstant(format, expires, locale, timeZone),
            })}
          </p>
        ) : null}

        <Dialog.Footer>
          <Button className="sm:flex-1" onClick={() => void copyToClipboard()}>
            {copied ? <Check aria-hidden="true" /> : <Copy aria-hidden="true" />}
            {copied ? t("edgeAgents.copied") : t("edgeAgents.copy")}
          </Button>
          <Dialog.Close asChild>
            <Button className="sm:flex-1" variant="secondary">
              {t("common.close")}
            </Button>
          </Dialog.Close>
        </Dialog.Footer>
      </Dialog.Content>
    </Dialog.Root>
  );
}
