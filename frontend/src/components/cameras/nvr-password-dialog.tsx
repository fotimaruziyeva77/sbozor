"use client";

import { useMemo, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslations } from "next-intl";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { PasswordInput } from "@/components/cameras/nvr-form";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { useUpdateNvrPassword } from "@/lib/camera-queries";
import { marketErrorMessageKey } from "@/lib/market-errors";

/*
 * =============================================================================
 * NVR PAROLINI YANGILASH (UI-SPEC §4.6).
 *
 * ⚠ ESKI PAROL SO'RALMAYDI — u bizda OCHIQ MATNDA YO'Q. Uni so'rash
 *   ikki yomon yo'ldan biriga olib borardi: yo shifrni ochib
 *   solishtirish (parolni yana bir marta xotiraga chiqarish), yo NVR'ga
 *   tekshiruv so'rovi yuborish — ya'ni AYNAN D-03 taqiqlagan qo'shimcha
 *   autentifikatsiya urinishi. Darvoza boshqa joyda: `CAMERA_MANAGE`
 *   huquqi (`POST /nvr-devices/{id}/password`).
 *
 * ⚠ MAYDON BITTA va u BO'SH ochiladi. Mavjud parol dialogga PROP bo'lib
 *   ham kelmaydi: javob sxemasida bunday maydon umuman yo'q (D-12).
 *
 * ⚠ MUVAFFAQIYATDA `onUpdated()` CHAQIRILADI va bu shunchaki xabar
 *   emas — REKVIZIT O'ZGARISHINING signali. NVR kartasidagi auth qulfi
 *   FAQAT shu signaldan ochiladi (§4.4): kartada login/parol maydoni
 *   yo'q, ya'ni qulfning ochilish yo'li ham AYNAN shu bitta.
 * =============================================================================
 */

type PasswordValues = { password: string };

export function NvrPasswordDialog({
  nvrId,
  onOpenChange,
  onUpdated,
  open,
}: {
  nvrId: string;
  onOpenChange: (open: boolean) => void;
  /** Rekvizit o'zgardi — chaqiruvchi auth qulfini shu bilan ochadi. */
  onUpdated: () => void;
  open: boolean;
}) {
  const t = useTranslations();
  const updatePassword = useUpdateNvrPassword();
  const [formError, setFormError] = useState<string | null>(null);

  const schema = useMemo(
    () => z.object({ password: z.string().min(1, { error: t("errors.required") }) }),
    [t],
  );

  const {
    formState: { errors, isSubmitting },
    handleSubmit,
    register,
    reset,
  } = useForm<PasswordValues>({
    resolver: zodResolver(schema),
    defaultValues: { password: "" },
  });

  function handleOpenChange(next: boolean): void {
    if (!next) {
      // Parol dialog yopilishi bilan forma holatidan chiqadi (D-12).
      reset({ password: "" });
      setFormError(null);
    }
    onOpenChange(next);
  }

  async function onSubmit(values: PasswordValues): Promise<void> {
    setFormError(null);
    try {
      await updatePassword.mutateAsync({ nvrId, password: values.password });
      toast.success(t("cameras.toastPasswordUpdated"));
      handleOpenChange(false);
      onUpdated();
    } catch (error) {
      setFormError(t(marketErrorMessageKey(error)));
    }
  }

  return (
    <Dialog.Root onOpenChange={handleOpenChange} open={open}>
      <Dialog.Content
        description={t("cameras.passwordHint")}
        size="sm"
        title={t("cameras.updatePassword")}
      >
        <form
          className="flex flex-col gap-4"
          noValidate
          onSubmit={handleSubmit(onSubmit)}
        >
          <Field
            error={errors.password?.message}
            id="nvr-new-password"
            label={t("cameras.nvrPassword")}
          >
            <PasswordInput
              describedBy={
                errors.password ? "nvr-new-password-error" : undefined
              }
              id="nvr-new-password"
              invalid={errors.password !== undefined}
              registration={register("password")}
            />
          </Field>

          {formError !== null ? (
            <p
              className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
              role="alert"
            >
              {formError}
            </p>
          ) : null}

          <Dialog.Footer>
            <Button
              aria-disabled={isSubmitting ? true : undefined}
              className="sm:flex-1"
              size="lg"
              type="submit"
            >
              {isSubmitting ? t("common.loading") : t("common.save")}
            </Button>
            <Dialog.Close asChild>
              <Button className="sm:flex-1" size="lg" variant="secondary">
                {t("common.cancel")}
              </Button>
            </Dialog.Close>
          </Dialog.Footer>
        </form>
      </Dialog.Content>
    </Dialog.Root>
  );
}
