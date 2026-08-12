"use client";

import { ScrollText, Users } from "lucide-react";
import { useTranslations } from "next-intl";

import { HeadlineCard } from "@/components/headline/headline-card";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Link } from "@/i18n/navigation";
import { useAuthStore } from "@/lib/auth-store";
import type { Permission, RoleLabelKey } from "@/lib/rbac";
import { hasPermission, roleLabelKey } from "@/lib/rbac";

/*
 * Bosh ekran.
 *
 * DIQQAT: bu yerda birorta SOXTA raqam yo'q — va endi bitta HAQIQIY raqam
 * bor. `<HeadlineCard />` ko'rsatadigan son `GET /me/headline` dan keladi
 * (07-03) va uni qaysi ko'rsatkich ekanini SERVER huquq bo'yicha tanlaydi
 * (D-28); ko'rsatkich yo'q bo'lsa karta UMUMAN chizilmaydi — nol yozilmaydi.
 *
 * Qolgan metrikalar (band rastalar, yig'ilgan patta, nomuvofiqlik yig'indisi)
 * hamon YO'Q va ularning o'rniga "0" yoki namunaviy grafik ko'rsatish
 * ma'muriyatga tizim ishlayotgandek tuyulishiga sabab bo'lardi.
 *
 * ⛔ Joylashuv qat'iy (UI-SPEC §10.4): sarlavha + rol yorliqlaridan KEYIN,
 *    `SECTIONS` dan OLDIN — bosh ekranning birinchi mazmunli elementi shu
 *    ekranning JAVOBI. Boshlang'ich sahifa redirekti QO'SHILMAYDI (O-05).
 */
const SECTIONS: readonly {
  href: "/users" | "/audit";
  labelKey: "users" | "audit";
  icon: typeof Users;
  permission: Permission;
}[] = [
  { href: "/users", labelKey: "users", icon: Users, permission: "user_view" },
  {
    href: "/audit",
    labelKey: "audit",
    icon: ScrollText,
    permission: "audit_view",
  },
];

export default function DashboardPage() {
  const t = useTranslations();
  const tRoles = useTranslations("roles");
  const { principal } = useAuthStore();

  const roles = principal?.roles ?? [];
  const roleLabels = roles
    .map((role) => roleLabelKey(role))
    .filter((key): key is RoleLabelKey => key !== null)
    .map((key) => tRoles(key));

  const sections = SECTIONS.filter((section) =>
    hasPermission(roles, section.permission),
  );

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">
          {t("nav.dashboard")}
        </h1>
        {/* D-16: bozor nomi tarjima qilinmaydi — qanday kiritilgan bo'lsa shunday. */}
        <p className="text-sm text-text-muted">
          {t("shell.marketLabel")}: {principal?.marketName ?? "—"}
        </p>
        {roleLabels.length > 0 ? (
          <p className="text-sm text-text-muted">
            {t("users.rolesLabel")}: {roleLabels.join(" · ")}
          </p>
        ) : null}
      </div>

      {/*
       * ⛔ Komponentga FAQAT `marketId` uzatiladi (§10.2). Rol ham, huquq
       *    ham BERILMAYDI: qaysi son ko'rinishini server hal qiladi va
       *    klient buni takrorlay olmasligi kerak.
       */}
      <HeadlineCard marketId={principal?.marketId ?? null} />

      {sections.length > 0 ? (
        <ul className="grid gap-3 sm:grid-cols-2">
          {sections.map((section) => {
            const Icon = section.icon;
            return (
              <li key={section.href}>
                <Link className="block" href={section.href}>
                  <Card className="transition-colors hover:bg-surface-muted">
                    <CardHeader>
                      <span className="flex items-center gap-2 text-lg font-semibold">
                        <Icon aria-hidden="true" className="size-4" />
                        {t(`nav.${section.labelKey}`)}
                      </span>
                    </CardHeader>
                    <CardContent />
                  </Card>
                </Link>
              </li>
            );
          })}
        </ul>
      ) : null}
    </div>
  );
}
