"use client";

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";

import { AppShell } from "@/components/shell/app-shell";
import { BrandLoader } from "@/components/ui/brand-loader";
import { usePathname, useRouter } from "@/i18n/navigation";
import { loadPrincipal, restoreSession } from "@/lib/api-client";
import { updatePrincipal, useAuthStore } from "@/lib/auth-store";

/*
 * Himoyalangan qatlam — `(app)/layout.tsx` ning sobiq tanasi (10-03 da
 * AYNAN ko'chirildi; T-10-16: darvoza mantig'ining birorta sharti
 * o'zgarmadi). Layout endi server komponent: u `AppProviders` ni o'raydi
 * va SHU guardni provayderlar ICHIDA render qiladi — hook'lar provayderdan
 * OLDIN ishlashi mumkin emas (10-RESEARCH Tuzoq 3).
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
 * 3-QOIDANING YAGONA ISTISNOSI: `/markets/new` (CR-03). Bu — butun
 * mahsulotdagi YAGONA ekran, u tenant konteksti YO'Q holatda qonuniy
 * ishlaydi, chunki u aynan o'sha kontekstni TUG'DIRADI. Istisnosiz birinchi
 * bozorni yaratish umuman mumkin emas edi: bozori yo'q platforma admini
 * `/select-market` ga haydalar, u yerda esa faqat "chiqish" tugmasi turardi.
 * Istisno PREFIKS emas, TENGLIK bilan yozilgan (T-02-140) — `startsWith`
 * bo'lsa `/markets/new-anything` ham bozorsiz ochilib, butun `(app)`
 * daraxtiga huquq oshirish yuzasi paydo bo'lardi.
 *
 * Tekshiruv davomida BO'SH ekran emas, skelet ko'rsatiladi: bo'sh ekran
 * "ilova qotib qoldi" degan taassurot beradi.
 */

/** Usta boshlanishi — `markets/new/page.tsx` o'z darvozasini o'zi qo'yadi. */
const WIZARD_NEW_PATH = "/markets/new";

export function AppGuard({ children }: { children: React.ReactNode }) {
  const t = useTranslations("shell");
  const router = useRouter();
  const pathname = usePathname();
  const { accessToken, principal } = useAuthStore();
  const [restoreAttempted, setRestoreAttempted] = useState(false);
  const restoreStarted = useRef(false);
  const enrichStarted = useRef(false);

  // Sessiya allaqachon xotirada bo'lsa (login'dan keyingi navigatsiya)
  // hech qanday tekshiruv shart emas — bu holat DERIVATSIYA qilinadi,
  // effekt ichida `setState` bilan emas (cascading render).
  const hasSession = accessToken !== null && principal !== null;
  const checked = hasSession || restoreAttempted;

  /*
   * "Bu ekran tenant kontekstini TALAB QILADIMI?" — yagona manba.
   *
   * U IKKI joyda ishlatiladi va bu TAKROR EMAS: `useEffect` yo'naltirishni,
   * `ready` esa ekranning ochilishini boshqaradi. Faqat effekt tuzatilsa
   * `ready` `false` qolib, sahifa ABADIY SKELET ko'rsatardi; faqat `ready`
   * tuzatilsa effekt sahifani ochilishi bilanoq surib yuborardi.
   */
  const needsMarket = pathname !== WIZARD_NEW_PATH;

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
    if (needsMarket && principal.marketId === null) {
      router.replace("/select-market");
    }
  }, [checked, needsMarket, principal, router]);

  useEffect(() => {
    // Login javobida foydalanuvchi `id`, telefoni va ismi YO'Q — ular
    // `GET /api/v1/me` dan keladi. Bu to'ldirish ATAYIN "eng yaxshi harakat":
    // u yiqilsa menyu rol yorlig'ini ko'rsatadi, sessiya esa yashab qoladi.
    if (!checked || !principal || principal.userId !== null) return;
    if (principal.marketId === null || enrichStarted.current) return;
    enrichStarted.current = true;

    /*
     * ⛔ Bu yerdan FAQAT `userId/phone/fullName` olinadi (pastda), ya'ni
     *    bozor holati bu yo'ldan o'tmaydi — mavjud qiymat uzatiladi va
     *    u `updatePrincipal` ga tushmaydi.
     */
    void loadPrincipal(
      principal.marketName === null
        ? null
        : {
            name: principal.marketName,
            isActive: principal.marketIsActive ?? false,
          },
    )
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
    (!needsMarket || principal.marketId !== null);

  if (!ready) {
    return (
      /*
       * Sessiya tiklanishi — BUTUN ilova darajasidagi kutish, ya'ni
       * brend-loaderning asosiy o'rni (2026-08-25, foydalanuvchi:
       * «Loader quy... hamma qismiga»). `role="status"`/`aria-busy`
       * loaderning O'ZIDA — bu yerda takrorlanmaydi.
       */
      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col justify-center p-6">
        <BrandLoader label={t("loading")} />
      </main>
    );
  }

  return <AppShell>{children}</AppShell>;
}
