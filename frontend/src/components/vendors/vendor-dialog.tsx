"use client";

import { useEffect, useMemo, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslations } from "next-intl";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { looksLikeUzbekPhone } from "@/components/users/create-user-dialog";
import type { VendorListItem } from "@/lib/api-types";
import { marketErrorMessageKey } from "@/lib/market-errors";
import { useCreateVendor, useUpdateVendor } from "@/lib/market-queries";

/*
 * =============================================================================
 * Sotuvchi formasi — YARATISH va TAHRIRLASH bitta komponentda.
 *
 * NEGA BITTA: ikkala forma ham aynan ikkita maydondan iborat va bir xil
 * telefon qoidasiga bo'ysunadi (D-12). Ikki fayl bo'lsa, telefon
 * tekshiruvini bir joyda o'zgartirib ikkinchisini unutish mumkin bo'lardi.
 *
 * INLINE TAHRIR EMAS, MODAL (UI-SPEC §8.4): telefon o'zgarishi serverda
 * 409 (`vendor_phone_taken`) bilan RAD ETILISHI mumkin, inline maydonda esa
 * o'sha tushuntirishni qo'yadigan joy yo'q. Ustiga har o'zgarish auditga
 * tushadi va `onBlur` saqlash ikkilanish paytida tasodifiy yozuvlar
 * hosil qilardi — aniq "Saqlash" tugmasi niyat chegarasini beradi.
 *
 * TELEFON NORMALIZATSIYASI SERVERDA (`normalize_phone` -> E.164). Bu
 * yerdagi tekshiruv faqat "yozishda adashildi" holatini ushlaydi va
 * `create-user-dialog.tsx` bilan BITTA funksiyani baham ko'radi.
 * =============================================================================
 */

type VendorFormValues = {
  fullName: string;
  phone: string;
};

const EMPTY_VALUES: VendorFormValues = { fullName: "", phone: "" };

export function VendorDialog({
  onOpenChange,
  open,
  vendor,
}: {
  onOpenChange: (open: boolean) => void;
  open: boolean;
  /** `null` — yaratish rejimi; aks holda tahrirlash. */
  vendor: VendorListItem | null;
}) {
  const t = useTranslations();
  const createVendor = useCreateVendor();
  const updateVendor = useUpdateVendor();
  const [formError, setFormError] = useState<string | null>(null);

  const isEdit = vendor !== null;

  const schema = useMemo(
    () =>
      z.object({
        fullName: z.string().trim().min(1, { error: t("errors.required") }),
        phone: z
          .string()
          .min(1, { error: t("errors.required") })
          .refine(looksLikeUzbekPhone, { error: t("auth.invalidPhone") }),
      }),
    [t],
  );

  const {
    formState: { errors, isSubmitting },
    handleSubmit,
    register,
    reset,
  } = useForm<VendorFormValues>({
    resolver: zodResolver(schema),
    defaultValues: EMPTY_VALUES,
  });

  /*
   * Tahrirlashda maydonlar TANLANGAN sotuvchidan to'ldiriladi. `useEffect`
   * ATAYIN: dialog bitta nusxada yashaydi va `vendor` prop'i almashganda
   * forma yangi qiymatlarni olishi kerak — `defaultValues` esa faqat
   * birinchi montajda o'qiladi.
   *
   * Effekt ichida `setState` CHAQIRILMAYDI (kaskad renderlar): `reset` —
   * react-hook-form ning tashqi omboriga yozuv, React holatiga emas.
   * `formError` esa dialog yopilganda tozalanadi (`handleOpenChange`),
   * ya'ni u hech qachon boshqa sotuvchiga o'tib qolmaydi.
   */
  useEffect(() => {
    reset(
      vendor === null
        ? EMPTY_VALUES
        : { fullName: vendor.full_name, phone: vendor.phone },
    );
  }, [reset, vendor]);

  function handleOpenChange(next: boolean) {
    if (!next) {
      reset(EMPTY_VALUES);
      setFormError(null);
    }
    onOpenChange(next);
  }

  async function onSubmit(values: VendorFormValues) {
    setFormError(null);
    try {
      if (vendor === null) {
        await createVendor.mutateAsync({
          full_name: values.fullName.trim(),
          phone: values.phone,
        });
      } else {
        await updateVendor.mutateAsync({
          id: vendor.id,
          full_name: values.fullName.trim(),
          phone: values.phone,
        });
      }
      handleOpenChange(false);
    } catch (error) {
      // 409 `vendor_phone_taken` shu yerda ko'rinadi: xato KONKRET va u
      // umumiy 4xx matniga tushirilmaydi (`market-errors.ts`).
      setFormError(t(marketErrorMessageKey(error)));
    }
  }

  return (
    <Dialog.Root onOpenChange={handleOpenChange} open={open}>
      <Dialog.Content
        description={isEdit ? t("vendors.editHint") : t("vendors.createHint")}
        size="lg"
        title={isEdit ? t("vendors.editTitle") : t("vendors.createTitle")}
      >
        <form
          className="flex flex-col gap-4"
          noValidate
          onSubmit={handleSubmit(onSubmit)}
        >
          <Field
            error={errors.fullName?.message}
            id="vendor-full-name"
            label={t("vendors.fullNameLabel")}
          >
            <Input
              aria-describedby={
                errors.fullName ? "vendor-full-name-error" : undefined
              }
              aria-invalid={errors.fullName ? true : undefined}
              autoComplete="off"
              id="vendor-full-name"
              {...register("fullName")}
            />
          </Field>

          <Field
            error={errors.phone?.message}
            id="vendor-phone"
            label={t("vendors.phoneLabel")}
          >
            <Input
              aria-describedby={errors.phone ? "vendor-phone-error" : undefined}
              aria-invalid={errors.phone ? true : undefined}
              autoComplete="off"
              id="vendor-phone"
              inputMode="tel"
              placeholder={t("auth.phoneHint")}
              type="tel"
              {...register("phone")}
            />
          </Field>

          {formError ? (
            <p
              className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
              role="alert"
            >
              {formError}
            </p>
          ) : null}

          <Dialog.Footer>
            <Button
              className="sm:flex-1"
              disabled={isSubmitting}
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
