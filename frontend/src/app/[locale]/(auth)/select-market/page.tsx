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
 *
 * =============================================================================
 * ⛔⛔ KOMPOZITSIYA — YALANG'OCH KARTA EMAS (260820, jonli o'lchandi).
 *
 *     Bu yerda faqat `<Card>` turardi va u kontentiga qarab kichrayardi:
 *     1878px ekranda 210px kenglikdagi karta, ekranning CHAP chekkasiga
 *     yopishgan holda. Bu — platforma adminining BIRINCHI ekrani va u
 *     tugallanmagandek ko'rinardi.
 *
 *     Sabab tuzilmada edi: `(auth)/layout.tsx` `main` ga `items-center`
 *     beradi, ya'ni bola VERTIKAL markazlashadi, lekin kenglikni O'ZI
 *     belgilaydi. Kirish sahifasi shuning uchun to'g'ri ko'rinadi —
 *     unda ikki ustunli setka bor va u kenglikni to'ldiradi.
 *
 *     Endi bu ekran ham kirish sahifasi bilan BIR XIL naqshda: chapda
 *     mazmun (nima uchun tanlash kerak), o'ngda tanlov kartasi.
 * =============================================================================
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
    <div className="grid w-full items-center gap-16 min-[901px]:grid-cols-[1fr_27.5rem]">
      {/*
       * ⛔ CHAP USTUN `min-[901px]` DAN PASTDA CHIZILMAYDI: telefonda
       *    tanlov kartasi butun ekranni oladi va uning ustidagi izoh
       *    faqat aylantirish qo'shardi. Kirish sahifasidagi qaror bilan
       *    bir xil.
       */}
      <div className="hidden min-[901px]:block">
        <h1 className="login-title text-balance">
          {t("selectMarketTitle")}
        </h1>
        <p className="login-lead mt-4.5 max-w-[44ch] text-text-muted">
          {t("selectMarketLead")}
        </p>
      </div>

      <Card>
        <CardHeader>
          {/*
           * ⛔ Sarlavha `min-[901px]` dan yuqorida CHAP ustunda turadi,
           *    shuning uchun kartada u faqat kichik ekranda chiziladi —
           *    aks holda bitta ekranda ikkita bir xil sarlavha bo'lardi.
           */}
          <h2 className="text-2xl font-semibold tracking-tight min-[901px]:sr-only">
            {t("selectMarketTitle")}
          </h2>
        </CardHeader>
        <CardContent>
          <MarketPicker />
        </CardContent>
      </Card>
    </div>
  );
}
