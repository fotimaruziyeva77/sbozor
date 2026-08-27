import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

import { routing } from "@/i18n/routing";
import { hasLocale } from "next-intl";

/*
 * ⛔ SARLAVHA UCHUN ALOHIDA `layout.tsx` — sabab MEXANIK (K-03):
 *   sahifaning o'zi `"use client"` va `metadata` eksport qila olmaydi.
 *   2026-08-25 auditida K-03 qamrovi 4 sahifada to'xtab qolgani topildi —
 *   endi (app) guruhining HAMMA marshruti o'z tab nomini beradi.
 *
 * ⚠ Layout FAQAT `children` ni qaytaradi — DOM ham, uslub ham qo'shmaydi.
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
  const t = await getTranslations({ locale: resolved, namespace: "snapshots" });
  return { title: t("title") };
}

export default function TitleLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
