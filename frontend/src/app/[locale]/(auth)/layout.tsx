/*
 * Kirish oqimining qobig'i: markazlashtirilgan tor ustun, bitta karta.
 * Apple-uslub (topshiriq §7) — bitta aniq harakat, ortiqcha bezaksiz.
 *
 * DIQQAT: bu yerda hech qanday matn yo'q — barchasi sahifalarda
 * `next-intl` orqali keladi.
 */
export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <main className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center gap-6 p-6">
      {children}
    </main>
  );
}
