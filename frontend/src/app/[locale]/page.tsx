import { notFound } from "next/navigation";
import { hasLocale } from "next-intl";
import { setRequestLocale } from "next-intl/server";

import { redirect } from "@/i18n/navigation";
import { routing } from "@/i18n/routing";

/*
 * Ildiz sahifa — kirish nuqtasi.
 *
 * `/uz` (yoki `/uz-cyrl`, `/ru`) ochilganda foydalanuvchi bosh ekranga
 * yuboriladi; sessiya bo'lmasa `(app)` qatlami uni `/login` ga qaytaradi.
 * Ya'ni "kirganmi yoki yo'qmi" savoliga javob BITTA joyda beriladi va
 * bu yerda takrorlanmaydi.
 *
 * 01-02 dagi vaqtinchalik namoyish sahifasi shu bilan almashtirildi.
 */
export default async function RootPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!hasLocale(routing.locales, locale)) {
    notFound();
  }
  setRequestLocale(locale);

  redirect({ href: "/dashboard", locale });
}
