"use client";

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";

import { AppShell } from "@/components/shell/app-shell";
import { useRouter } from "@/i18n/navigation";
import { loadPrincipal, restoreSession } from "@/lib/api-client";
import { updatePrincipal, useAuthStore } from "@/lib/auth-store";

/*
 * Himoyalangan qatlam.
 *
 * Uch qoida, shu tartibda:
 *   1. Token yo'q -> `POST /api/v1/auth/refresh` bilan sessiyani TIKLASHGA
 *      urinadi (D-03: kassir telefonida qayta login so'ralmasin). Tiklanmasa
 *      `/login`.
 *   2. `mustChangePassword` -> `/change-password`. Bu tekshiruv HAR RENDER'da
 *      bajariladi, ya'ni URL'ni qo'lda yozib kirishga urinish ham shu yerga
 *      qaytadi (T-01-64). Server tomonda ham yozuv endpointlari yopiq.
 *   3. Bozor tanlanmagan -> `/select-market` (D-06).
 *
 * Tekshiruv davomida BO'SH ekran emas, skelet ko'rsatiladi: bo'sh ekran
 * "ilova qotib qoldi" degan taassurot beradi.
 */
export default function AppLayout({ children }: { children: React.ReactNode }) {
  const t = useTranslations("shell");
  const router = useRouter();
  const { accessToken, principal } = useAuthStore();
  const [restoreAttempted, setRestoreAttempted] = useState(false);
  const restoreStarted = useRef(false);
  const enrichStarted = useRef(false);

  // Sessiya allaqachon xotirada bo'lsa (login'dan keyingi navigatsiya)
  // hech qanday tekshiruv shart emas — bu holat DERIVATSIYA qilinadi,
  // effekt ichida `setState` bilan emas (cascading render).
  const hasSession = accessToken !== null && principal !== null;
  const checked = hasSession || restoreAttempted;

  useEffect(() => {
    if (restoreStarted.current || hasSession) return;
    restoreStarted.current = true;

    void restoreSession().then((restored) => {
      setRestoreAttempted(true);
      if (!restored) router.replace("/login");
    });
  }, [hasSession, router]);

  useEffect(() => {
    if (!checked || !principal) return;

    if (principal.mustChangePassword) {
      router.replace("/change-password");
      return;
    }
    if (principal.marketId === null) {
      router.replace("/select-market");
    }
  }, [checked, principal, router]);

  useEffect(() => {
    // Login javobida foydalanuvchi `id`, telefoni va ismi YO'Q — ular
    // `GET /api/v1/me` dan keladi. Bu to'ldirish ATAYIN "eng yaxshi harakat":
    // u yiqilsa menyu rol yorlig'ini ko'rsatadi, sessiya esa yashab qoladi.
    if (!checked || !principal || principal.userId !== null) return;
    if (principal.marketId === null || enrichStarted.current) return;
    enrichStarted.current = true;

    void loadPrincipal(principal.marketName)
      .then((profile) => {
        updatePrincipal({
          userId: profile.userId,
          phone: profile.phone,
          fullName: profile.fullName,
        });
      })
      .catch(() => {
        // Profil to'ldirilmadi — bu oqimni to'xtatmaydi.
      });
  }, [checked, principal]);

  const ready =
    checked &&
    principal !== null &&
    !principal.mustChangePassword &&
    principal.marketId !== null;

  if (!ready) {
    return (
      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-4 p-6">
        <p className="text-sm text-text-muted" role="status">
          {t("loading")}
        </p>
        <div className="h-24 animate-pulse rounded-lg bg-surface-muted" />
        <div className="h-24 animate-pulse rounded-lg bg-surface-muted" />
      </main>
    );
  }

  return <AppShell>{children}</AppShell>;
}
