import { notFound } from "next/navigation";
import { hasLocale } from "next-intl";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { LoginForm } from "@/components/auth/login-form";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { routing } from "@/i18n/routing";

/*
 * Kirish sahifasi (D-01, D-04).
 *
 * Bu sahifada ATAYIN YO'Q (uchalasi ham grep darvozasi bilan qulflangan,
 * shuning uchun taqiqlangan iboralar bu yerda literal sifatida yozilmaydi):
 *   - elektron pochta / login nomi maydoni — identifikator faqat telefon
 *   - yangi hisob ochish havolasi — hisobni faqat admin yaratadi (D-04)
 *   - parolni tiklash havolasi — parolni ham faqat admin tiklaydi (D-02)
 */
export default async function LoginPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!hasLocale(routing.locales, locale)) {
    notFound();
  }
  // Statik renderni yoqadi — busiz sahifa dinamik bo'lib qoladi.
  setRequestLocale(locale);

  const t = await getTranslations("common");

  return (
    <Card>
      <CardHeader>
        <h1 className="text-2xl font-semibold tracking-tight">{t("appName")}</h1>
        <p className="text-sm text-text-muted">{t("appTagline")}</p>
      </CardHeader>
      <CardContent>
        <LoginForm />
      </CardContent>
    </Card>
  );
}
