import type { Metadata } from "next";

import "./globals.css";

/*
 * VAQTINCHALIK ildiz layout — 2-taskda `app/[locale]/layout.tsx` bilan
 * almashtiriladi (next-intl locale segmenti ildiz layout rolini oladi).
 */
export const metadata: Metadata = {
  title: "SBOZOR",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="uz-Latn" className="h-full">
      <body className="flex min-h-full flex-col">{children}</body>
    </html>
  );
}
