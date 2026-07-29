"use client";

import { useMemo, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslations } from "next-intl";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useRouter } from "@/i18n/navigation";
import { apiFetch, errorMessageKey } from "@/lib/api-client";
import { emptyResponseSchema } from "@/lib/api-types";
import { useAuthStore } from "@/lib/auth-store";

/**
 * D-02: vaqtinchalik parol bilan kirgan foydalanuvchi shu ekrandan
 * chetlab o'ta olmaydi. Chetlab o'tishga qarshi ikki qatlam bor:
 * (1) `(app)` qatlami `mustChangePassword` ni har render'da tekshiradi,
 * (2) server yozuv endpointlarini parol almashtirilmaguncha rad etadi.
 * Bu forma — o'sha qatlamlarning yagona chiqish yo'li.
 *
 * Endpoint: `POST /api/v1/auth/change-password` -> 204.
 */
const CHANGE_PASSWORD_PATH = "/auth/change-password";

/** `services/core-api/app/schemas.py::MIN_PASSWORD_LENGTH` bilan bir xil. */
const MIN_PASSWORD_LENGTH = 10;

type ChangePasswordValues = {
  currentPassword: string;
  newPassword: string;
  confirmPassword: string;
};

export function ChangePasswordForm() {
  const t = useTranslations();
  const router = useRouter();
  const { principal, updatePrincipal } = useAuthStore();
  const [formError, setFormError] = useState<string | null>(null);

  const schema = useMemo(
    () =>
      z
        .object({
          currentPassword: z.string().min(1, { error: t("errors.required") }),
          newPassword: z.string().min(MIN_PASSWORD_LENGTH, {
            error: t("auth.passwordTooShort"),
          }),
          confirmPassword: z.string().min(1, { error: t("errors.required") }),
        })
        .refine((values) => values.newPassword === values.confirmPassword, {
          error: t("auth.passwordMismatch"),
          path: ["confirmPassword"],
        })
        .refine((values) => values.newPassword !== values.currentPassword, {
          error: t("auth.passwordSameAsCurrent"),
          path: ["newPassword"],
        }),
    [t],
  );

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ChangePasswordValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      currentPassword: "",
      newPassword: "",
      confirmPassword: "",
    },
  });

  async function onSubmit(values: ChangePasswordValues) {
    setFormError(null);
    try {
      await apiFetch(CHANGE_PASSWORD_PATH, {
        method: "POST",
        body: {
          current_password: values.currentPassword,
          new_password: values.newPassword,
        },
        schema: emptyResponseSchema,
      });

      // Bayroq darhol tushiriladi — aks holda `(app)` qatlami foydalanuvchini
      // shu ekranga qaytarib, cheksiz aylanma hosil qilardi.
      updatePrincipal({ mustChangePassword: false });
      toast.success(t("auth.passwordChanged"));

      router.replace(
        principal?.marketId === null ? "/select-market" : "/dashboard",
      );
    } catch (error) {
      setFormError(t(errorMessageKey(error)));
    }
  }

  return (
    <form
      className="flex flex-col gap-4"
      noValidate
      onSubmit={handleSubmit(onSubmit)}
    >
      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-medium" htmlFor="current-password">
          {t("auth.currentPassword")}
        </label>
        <Input
          id="current-password"
          type="password"
          autoComplete="current-password"
          autoFocus
          aria-invalid={errors.currentPassword ? true : undefined}
          {...register("currentPassword")}
        />
        {errors.currentPassword ? (
          <p className="text-sm text-danger">{errors.currentPassword.message}</p>
        ) : null}
      </div>

      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-medium" htmlFor="new-password">
          {t("auth.newPassword")}
        </label>
        <Input
          id="new-password"
          type="password"
          autoComplete="new-password"
          aria-invalid={errors.newPassword ? true : undefined}
          {...register("newPassword")}
        />
        {errors.newPassword ? (
          <p className="text-sm text-danger">{errors.newPassword.message}</p>
        ) : null}
      </div>

      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-medium" htmlFor="confirm-password">
          {t("auth.confirmPassword")}
        </label>
        <Input
          id="confirm-password"
          type="password"
          autoComplete="new-password"
          aria-invalid={errors.confirmPassword ? true : undefined}
          {...register("confirmPassword")}
        />
        {errors.confirmPassword ? (
          <p className="text-sm text-danger">{errors.confirmPassword.message}</p>
        ) : null}
      </div>

      {formError ? (
        <p
          className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger"
          role="alert"
        >
          {formError}
        </p>
      ) : null}

      <Button type="submit" size="lg" disabled={isSubmitting}>
        {isSubmitting ? t("common.loading") : t("common.save")}
      </Button>
    </form>
  );
}
