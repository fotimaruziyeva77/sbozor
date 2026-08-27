"use client";

import { useMemo, useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslations } from "next-intl";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
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


/*
 * 2026-08-26 (buyurtmachi №6): har parol maydonida ko'z-ikonkasi —
 * login bilan BIR ko'rinish. Holat maydon boshiga alohida (bir maydonni
 * ochish qolganlarini ochmaydi).
 */
function EyeToggle({
  shown,
  onToggle,
  showLabel,
  hideLabel,
}: {
  shown: boolean;
  onToggle: () => void;
  showLabel: string;
  hideLabel: string;
}) {
  return (
    <button
      aria-label={shown ? hideLabel : showLabel}
      aria-pressed={shown}
      className="absolute top-1/2 right-2 grid size-9 -translate-y-1/2 cursor-pointer place-items-center rounded-md text-text-muted transition-colors hover:bg-surface-muted hover:text-text"
      onClick={onToggle}
      type="button"
    >
      {shown ? (
        <EyeOff aria-hidden="true" className="size-5" />
      ) : (
        <Eye aria-hidden="true" className="size-5" />
      )}
    </button>
  );
}

export function ChangePasswordForm() {
  const [shownFields, setShownFields] = useState<{
    current: boolean;
    next: boolean;
    confirm: boolean;
  }>({ current: false, next: false, confirm: false });
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
      <Field
        error={errors.currentPassword?.message}
        id="current-password"
        label={t("auth.currentPassword")}
      >
        <span className="relative flex">
        <Input
          id="current-password"
          className="pr-12"
          type={shownFields.current ? "text" : "password"}
          autoComplete="current-password"
          autoFocus
          aria-invalid={errors.currentPassword ? true : undefined}
          aria-describedby={
            errors.currentPassword ? "current-password-error" : undefined
          }
          {...register("currentPassword")}
        />
        <EyeToggle
          hideLabel={t("auth.hidePassword")}
          onToggle={() =>
            setShownFields((f) => ({ ...f, current: !f.current }))
          }
          showLabel={t("auth.showPassword")}
          shown={shownFields.current}
        />
        </span>
      </Field>

      <Field
        error={errors.newPassword?.message}
        id="new-password"
        label={t("auth.newPassword")}
      >
        <span className="relative flex">
        <Input
          id="new-password"
          className="pr-12"
          type={shownFields.next ? "text" : "password"}
          autoComplete="new-password"
          aria-invalid={errors.newPassword ? true : undefined}
          aria-describedby={
            errors.newPassword ? "new-password-error" : undefined
          }
          {...register("newPassword")}
        />
        <EyeToggle
          hideLabel={t("auth.hidePassword")}
          onToggle={() =>
            setShownFields((f) => ({ ...f, next: !f.next }))
          }
          showLabel={t("auth.showPassword")}
          shown={shownFields.next}
        />
        </span>
      </Field>

      <Field
        error={errors.confirmPassword?.message}
        id="confirm-password"
        label={t("auth.confirmPassword")}
      >
        <span className="relative flex">
        <Input
          id="confirm-password"
          className="pr-12"
          type={shownFields.confirm ? "text" : "password"}
          autoComplete="new-password"
          aria-invalid={errors.confirmPassword ? true : undefined}
          aria-describedby={
            errors.confirmPassword ? "confirm-password-error" : undefined
          }
          {...register("confirmPassword")}
        />
        <EyeToggle
          hideLabel={t("auth.hidePassword")}
          onToggle={() =>
            setShownFields((f) => ({ ...f, confirm: !f.confirm }))
          }
          showLabel={t("auth.showPassword")}
          shown={shownFields.confirm}
        />
        </span>
      </Field>

      {formError ? (
        <p
          className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
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
