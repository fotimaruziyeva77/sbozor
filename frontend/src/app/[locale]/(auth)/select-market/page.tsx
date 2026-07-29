import { notFound } from "next/navigation";
import { hasLocale } from "next-intl";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { MarketPicker } from "@/components/auth/market-picker";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { routing } from "@/i18n/routing";

/**
 * Bozor tanlash (D-06).
 *
 * Bu qadam platforma admini va bir nechta bozorga a'zo foydalanuvchi uchun
 * MAJBURIY: bozor tanlanmaguncha sessiyada tenant konteksti yo'q va u hech
 * qanday ma'lumotni ko'ra olmaydi.
 */
export default async function SelectMarketPage({
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
          {t("selectMarketTitle")}
        </h1>
      </CardHeader>
      <CardContent>
        <MarketPicker />
      </CardContent>
    </Card>
  );
}
