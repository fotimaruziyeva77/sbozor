"use client";

import { useMemo, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslations } from "next-intl";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useRouter } from "@/i18n/navigation";
import { ApiError, NetworkError, apiFetch } from "@/lib/api-client";
import { loginResponseSchema } from "@/lib/api-types";
import { useAuthStore } from "@/lib/auth-store";

/*
 * D-01: identifikator — TELEFON. Elektron pochta / login nomi maydoni yo'q.
 * D-04: o'z-o'zidan hisob ochish yo'q — hisobni admin yaratadi, shuning
 *       uchun bu formada yangi hisob ochish havolasi ham yo'q.
 * D-02: parolni admin tiklaydi — parol tiklash havolasi ham yo'q.
 * (Uchala taqiq grep darvozasi bilan qulflangan, shuning uchun taqiqlangan
 * iboralar bu yerda literal sifatida yozilmaydi.)
 *
 * Login endpointi: `POST /api/v1/auth/login`.
 */
const LOGIN_PATH = "/auth/login";

type LoginFormValues = {
  phone: string;
  password: string;
};

/**
 * Login xatosining tor xaritasi (T-01-63).
 *
 * `invalid_credentials` — telefon topilmadimi yoki parol xatomi, FARQLANMAYDI.
 * Backend ham uchala rad etish yo'lida (mavjud emas / parol xato / bloklangan)
 * bayt-bayt bir xil javob qaytaradi; UI o'sha kafolatni buzmasligi kerak.
 * Shuning uchun bu yerda `errorMessageKey()` umumiy xaritasi ATAYIN
 * ishlatilmaydi — u `account_blocked` ni alohida xabarga aylantirardi.
 */
function loginErrorKey(
  error: unknown,
): "auth.invalidCredentials" | "auth.tooManyAttempts" | "auth.invalidPhone" | "errors.network" | "errors.generic" {
  if (error instanceof NetworkError) return "errors.network";
  if (error instanceof ApiError) {
    // 422 — telefon formati o'qilmadi (bu enumeration signali EMAS: server
    // "bunday foydalanuvchi yo'q" demaydi, "raqam noto'g'ri" deydi).
    if (error.status === 422) return "auth.invalidPhone";
    if (error.detail === "invalid_credentials") return "auth.invalidCredentials";
    if (error.detail === "too_many_attempts") return "auth.tooManyAttempts";
  }
  return "errors.generic";
}

export function LoginForm() {
  const t = useTranslations();
  const router = useRouter();
  const { setSession } = useAuthStore();
  const [formError, setFormError] = useState<string | null>(null);

  const schema = useMemo(
    () =>
      z.object({
        // Normalizatsiya SERVERDA (`phonenumbers`) — bu yerda faqat
        // "bo'sh emas" tekshiriladi, aks holda mahalliy formatdagi
        // ("901234567") yaroqli raqam klientda rad etilardi.
        phone: z.string().trim().min(1, { error: t("errors.required") }),
        password: z.string().min(1, { error: t("errors.required") }),
      }),
    [t],
  );

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(schema),
    defaultValues: { phone: "", password: "" },
  });

  async function onSubmit(values: LoginFormValues) {
    setFormError(null);
    try {
      const response = await apiFetch(LOGIN_PATH, {
        method: "POST",
        body: { phone: values.phone, password: values.password },
        schema: loginResponseSchema,
        // Login'da eski (yaroqsiz) token yuborilmaydi va 401 da refresh
        // qilinmaydi — aks holda noto'g'ri parol "sessiya tiklash" tsikliga
        // aylanardi.
        skipAuth: true,
      });

      setSession({
        accessToken: response.access_token,
        principal: {
          userId: null,
          phone: null,
          fullName: null,
          roles: response.roles,
          marketId: response.market?.id ?? null,
          marketName: response.market?.name ?? null,
          isPlatformAdmin: response.is_platform_admin,
          locale: response.locale,
          mustChangePassword: response.must_change_password,
        },
        markets: response.markets,
      });

      /*
       * Yo'naltirish tartibi QAT'IY:
       *   1) majburiy parol almashtirish (D-02) — hech narsa uni chetlab o'tmaydi
       *   2) bozor tanlanmagan (D-06) — sessiya hali hech qanday ma'lumotga kira olmaydi
       *   3) bosh ekran
       *
       * `{locale: response.locale}` — foydalanuvchi profilidagi til (D-13).
       * Shu tufayli `localeDetection: false` (D-15) bilan ziddiyat yo'q:
       * tilni brauzer emas, server aytadi va URL prefiksi shunga ko'chadi.
       */
      const target = response.must_change_password
        ? "/change-password"
        : response.market === null
          ? "/select-market"
          : "/dashboard";

      router.replace(target, { locale: response.locale });
    } catch (error) {
      setFormError(t(loginErrorKey(error)));
    }
  }

  return (
    <form
      className="flex flex-col gap-4"
      noValidate
      onSubmit={handleSubmit(onSubmit)}
    >
      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-medium" htmlFor="phone">
          {t("auth.phoneLabel")}
        </label>
        <Input
          id="phone"
          type="tel"
          inputMode="tel"
          autoComplete="tel"
          autoFocus
          placeholder={t("auth.phoneHint")}
          aria-invalid={errors.phone ? true : undefined}
          aria-describedby={errors.phone ? "phone-error" : undefined}
          {...register("phone")}
        />
        {errors.phone ? (
          <p className="text-sm text-danger-text" id="phone-error">
            {errors.phone.message}
          </p>
        ) : null}
      </div>

      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-medium" htmlFor="password">
          {t("auth.passwordLabel")}
        </label>
        <Input
          id="password"
          type="password"
          autoComplete="current-password"
          aria-invalid={errors.password ? true : undefined}
          aria-describedby={errors.password ? "password-error" : undefined}
          {...register("password")}
        />
        {errors.password ? (
          <p className="text-sm text-danger-text" id="password-error">
            {errors.password.message}
          </p>
        ) : null}
      </div>

      {formError ? (
        <p
          className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
          role="alert"
        >
          {formError}
        </p>
      ) : null}

      <Button type="submit" size="lg" disabled={isSubmitting}>
        {isSubmitting ? t("auth.signingIn") : t("auth.signIn")}
      </Button>
    </form>
  );
}
