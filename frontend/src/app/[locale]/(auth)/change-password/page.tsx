import { notFound } from "next/navigation";
import { hasLocale } from "next-intl";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { ChangePasswordForm } from "@/components/auth/change-password-form";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { routing } from "@/i18n/routing";

/**
 * Majburiy parol almashtirish (D-02).
 *
 * Bu sahifada "keyinroq" tugmasi ATAYIN yo'q: vaqtinchalik parol admin
 * tomonidan berilgan va u almashtirilmaguncha sessiya ilovaga kirmaydi.
 */
export default async function ChangePasswordPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!hasLocale(routing.locales, locale)) {
    notFound();
  }
  setRequestLocale(locale);

  const t = await getTranslations("auth");

  return (
    <Card>
      <CardHeader>
        <h1 className="text-2xl font-semibold tracking-tight">
          {t("changePasswordTitle")}
        </h1>
        <p className="text-sm text-text-muted">{t("mustChangePassword")}</p>
      </CardHeader>
      <CardContent>
        <ChangePasswordForm />
      </CardContent>
    </Card>
  );
}
