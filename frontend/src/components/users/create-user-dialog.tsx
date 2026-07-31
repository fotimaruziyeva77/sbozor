"use client";

import { useMemo, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslations } from "next-intl";
import { useForm, useWatch } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { ApiLocale } from "@/lib/api-types";
import { assignableRoles, LOCALE_LABELS, LOCALES, localeSchema } from "@/lib/api-types";
import { useAuthStore } from "@/lib/auth-store";
import { adminErrorMessageKey, useCreateUser } from "@/lib/queries";
import type { Role } from "@/lib/rbac";
import { roleLabelKey } from "@/lib/rbac";

/*
 * Yangi foydalanuvchi (D-04 ikki bosqichli yaratish, D-05 rollar to'plami).
 *
 * ROL TANLOVI KO'P TANLOVLI (D-05). Kichik bozorda bir odam ham bozor
 * admini, ham kassir bo'ladi — bitta tanlovli boshqaruv (radio) bu holatni
 * umuman ifodalay olmasdi va sxemaga (`user_market_roles.roles` massivi)
 * ham zid bo'lardi.
 *
 * KO'RSATILADIGAN ROLLAR `assignableRoles()` dan keladi (D-04 darajasi):
 * bozor admini o'ziga teng yoki undan yuqori rolni umuman KO'RMAYDI. Bu
 * faqat UX ko'zgusi — haqiqiy darvoza serverda va u 403 `role_not_allowed`
 * qaytaradi, shuning uchun o'sha xato baribir tarjima bilan ko'rsatiladi.
 */

/**
 * Telefon raqamining SHAKLI (D-01: telefon — yagona identifikator).
 *
 * Qat'iy E.164 ga keltirish SERVERDA (`normalize_phone`) bajariladi; bu
 * yerdagi tekshiruv faqat "yozishda adashildi" holatini forma ichida
 * ushlaydi va `+998 90 123 45 67`, `998901234567`, `901234567`
 * shakllarining hammasini qabul qiladi.
 */
function looksLikeUzbekPhone(value: string): boolean {
  const digits = value.replace(/\D/gu, "");
  return /^998\d{9}$/u.test(digits) || /^\d{9}$/u.test(digits);
}

type CreateUserValues = {
  phone: string;
  fullName: string;
  roles: string[];
  locale: ApiLocale;
};

const EMPTY_VALUES: CreateUserValues = {
  phone: "",
  fullName: "",
  roles: [],
  locale: "uz-Latn",
};

export function CreateUserDialog({
  onCreated,
  onOpenChange,
  open,
}: {
  onCreated: (temporaryPassword: string) => void;
  onOpenChange: (open: boolean) => void;
  open: boolean;
}) {
  const t = useTranslations();
  const tRoles = useTranslations("roles");
  const { principal } = useAuthStore();
  const createUser = useCreateUser();
  const [formError, setFormError] = useState<string | null>(null);

  const roleOptions = assignableRoles(principal?.isPlatformAdmin ?? false);

  const schema = useMemo(
    () =>
      z.object({
        phone: z
          .string()
          .min(1, { error: t("errors.required") })
          .refine(looksLikeUzbekPhone, { error: t("auth.invalidPhone") }),
        fullName: z.string(),
        roles: z.array(z.string()).min(1, { error: t("users.rolesRequired") }),
        locale: localeSchema,
      }),
    [t],
  );

  const {
    control,
    formState: { errors, isSubmitting },
    handleSubmit,
    register,
    reset,
    setValue,
  } = useForm<CreateUserValues>({
    resolver: zodResolver(schema),
    defaultValues: EMPTY_VALUES,
  });

  /*
   * `useWatch`, `watch()` EMAS: `watch` — `useForm()` qaytaradigan oddiy
   * funksiya va React Compiler uni memoizatsiya qila olmaydi (eskirgan UI
   * xavfi). `useWatch` esa hook bo'lib, obunani to'g'ri e'lon qiladi.
   */
  const selectedRoles = useWatch({ control, name: "roles" });

  function toggleRole(role: Role) {
    const next = selectedRoles.includes(role)
      ? selectedRoles.filter((item) => item !== role)
      : [...selectedRoles, role];
    setValue("roles", next, { shouldValidate: selectedRoles.length > 0 });
  }

  function handleOpenChange(next: boolean) {
    if (!next) {
      reset(EMPTY_VALUES);
      setFormError(null);
    }
    onOpenChange(next);
  }

  async function onSubmit(values: CreateUserValues) {
    setFormError(null);
    try {
      const created = await createUser.mutateAsync({
        phone: values.phone,
        fullName: values.fullName.trim() === "" ? null : values.fullName.trim(),
        roles: values.roles,
        locale: values.locale,
      });

      // Parol dialogdan CHIQIB ketmaydi — u ota-komponentga uzatiladi va
      // o'sha yerda bir martalik oynada ko'rsatiladi (D-02).
      handleOpenChange(false);
      onCreated(created.temporary_password);
    } catch (error) {
      setFormError(t(adminErrorMessageKey(error)));
    }
  }

  return (
    <Dialog.Root onOpenChange={handleOpenChange} open={open}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40" />
        <Dialog.Content className="fixed top-1/2 left-1/2 z-50 flex max-h-[calc(100vh-2rem)] w-[min(30rem,calc(100vw-2rem))] -translate-x-1/2 -translate-y-1/2 flex-col gap-4 overflow-y-auto rounded-lg border border-border bg-surface p-6 shadow-raised">
          <Dialog.Title className="text-lg font-semibold">
            {t("users.createTitle")}
          </Dialog.Title>
          <Dialog.Description className="sr-only">
            {t("users.createHint")}
          </Dialog.Description>

          <form
            className="flex flex-col gap-4"
            noValidate
            onSubmit={handleSubmit(onSubmit)}
          >
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium" htmlFor="create-phone">
                {t("users.phoneLabel")}
              </label>
              <Input
                aria-invalid={errors.phone ? true : undefined}
                autoComplete="off"
                id="create-phone"
                inputMode="tel"
                placeholder={t("auth.phoneHint")}
                type="tel"
                {...register("phone")}
              />
              {errors.phone ? (
                <p className="text-sm text-danger-text">{errors.phone.message}</p>
              ) : null}
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium" htmlFor="create-full-name">
                {t("users.fullNameLabel")}
              </label>
              <Input
                autoComplete="off"
                id="create-full-name"
                {...register("fullName")}
              />
            </div>

            <fieldset className="flex flex-col gap-2">
              <legend className="mb-1 text-sm font-medium">
                {t("users.rolesLabel")}
              </legend>
              {roleOptions.map((role) => {
                const labelKey = roleLabelKey(role);
                if (labelKey === null) return null;
                return (
                  <RoleCheckbox
                    checked={selectedRoles.includes(role)}
                    key={role}
                    label={tRoles(labelKey)}
                    onToggle={() => toggleRole(role)}
                    role={role}
                  />
                );
              })}
              {errors.roles ? (
                <p className="text-sm text-danger-text">{errors.roles.message}</p>
              ) : null}
            </fieldset>

            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium" htmlFor="create-locale">
                {t("users.localeLabel")}
              </label>
              {/* Yorliqlar ENDONIM — tarjima qilinmaydi (`LOCALE_LABELS`). */}
              {/* `border-ui` — boshqaruv elementi chegarasi (WCAG 2.2
                  SC 1.4.11, o'lchangan 1.28:1 -> 3.64:1). */}
              <select
                className="h-10 w-full rounded-sm border border-border-ui bg-surface px-3 text-sm text-text outline-none focus-visible:border-accent focus-visible:ring-2 focus-visible:ring-accent/25"
                id="create-locale"
                {...register("locale")}
              >
                {LOCALES.map((code) => (
                  <option key={code} lang={code} value={code}>
                    {LOCALE_LABELS[code]}
                  </option>
                ))}
              </select>
            </div>

            {formError ? (
              <p
                className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
                role="alert"
              >
                {formError}
              </p>
            ) : null}

            <div className="flex flex-col gap-2 sm:flex-row-reverse">
              <Button
                className="sm:flex-1"
                disabled={selectedRoles.length === 0 || isSubmitting}
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
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

/** Bitta rol katakchasi — `type="checkbox"` (D-05: ko'p tanlovli). */
function RoleCheckbox({
  checked,
  label,
  onToggle,
  role,
}: {
  checked: boolean;
  label: string;
  onToggle: () => void;
  role: string;
}) {
  return (
    <label
      // `border-ui` — bu yorliq checkbox'ning barmoq nishoni, ya'ni
      // boshqaruv elementi (WCAG 2.2 SC 1.4.11, 1.28:1 -> 3.64:1).
      className="flex min-h-11 cursor-pointer items-center gap-3 rounded-md border border-border-ui px-3 py-2 text-sm transition-colors hover:bg-surface-muted"
      htmlFor={`create-role-${role}`}
    >
      <input
        checked={checked}
        className="size-4 accent-accent"
        id={`create-role-${role}`}
        onChange={onToggle}
        type="checkbox"
        value={role}
      />
      {label}
    </label>
  );
}
