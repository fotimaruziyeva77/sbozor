import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

import { routing } from "@/i18n/routing";
import { hasLocale } from "next-intl";

/*
 * ⛔ SARLAVHA UCHUN ALOHIDA `layout.tsx` — VA SABAB MEXANIK (K-03).
 *
 *   Sahifaning o'zi `"use client"`, klient komponenti esa `metadata`
 *   eksport QILA OLMAYDI (Next.js cheklovi). Yagona to'g'ri joy —
 *   yonidagi server layout.
 *
 * ⚠ Layout FAQAT `children` ni qaytaradi: u hech qanday DOM qo'shmaydi,
 *   ya'ni mavjud tartib va uslublar TEGILMAYDI.
 */
export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  const resolved = hasLocale(routing.locales, locale)
    ? locale
    : routing.defaultLocale;
  const t = await getTranslations({ locale: resolved, namespace: "collect" });
  return { title: t("title") };
}

export default function TitleLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
