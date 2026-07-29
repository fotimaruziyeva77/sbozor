import { use } from "react";
import { notFound } from "next/navigation";
import { hasLocale, useTranslations } from "next-intl";
import { setRequestLocale } from "next-intl/server";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { routing } from "@/i18n/routing";

/*
 * VAQTINCHALIK ildiz sahifa — uchala locale marshrutining ishlashini
 * isbotlaydi. Login sahifasi 01-08 rejasida keladi.
 *
 * DIQQAT: hech qanday matn hardcode qilinmagan — hammasi `next-intl` orqali.
 */
export default function HomePage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = use(params);
  if (!hasLocale(routing.locales, locale)) {
    notFound();
  }
  setRequestLocale(locale);

  const t = useTranslations("common");

  return (
    <main className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center p-6">
      <Card>
        <CardHeader>
          <h1 className="text-2xl font-semibold tracking-tight">
            {t("appName")}
          </h1>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-text-muted">{t("appTagline")}</p>
        </CardContent>
      </Card>
    </main>
  );
}
