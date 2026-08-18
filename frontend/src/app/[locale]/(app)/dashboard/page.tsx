"use client";

import { ScrollText, Users } from "lucide-react";
import { useTranslations } from "next-intl";

import { MarketStatusCard } from "@/components/dashboard/market-status-card";
import { DebtorsCard } from "@/components/dashboard/debtors-card";
import { LeakCard } from "@/components/dashboard/leak-card";
import { OccupancyDonut } from "@/components/dashboard/occupancy-donut";
import { RevenueCard } from "@/components/dashboard/revenue-card";
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

      {/*
       * Y-2 IKKI KARTASI — `HeadlineCard` dan KEYIN, `MarketStatusCard`
       * shartidan OLDIN (09-05; bosh ekranning mavjud tartibi o'zgarmaydi).
       *
       * ⛔⛔ HUQUQ AYNAN `report_view`, `market_manage` EMAS (O-03):
       *    birinchisi `director` + `market_admin` da bor va kassirda YO'Q;
       *    `market_manage` esa FAQAT `platform_admin` da. Ikkalasini
       *    adashtirish yo kassirga tushumni sizdirardi, yo direktorni
       *    yopardi — G-motion-6 ning butun maqsadi shuni oldini olish.
       *    Yangi huquq QO'SHILMAYDI: ikkala endpoint ham serverda
       *    `REPORT_VIEW` ostida [VERIFIED: occupancy.py:83,114,
       *    reports.py:156].
       *
       * ⛔ SHART KOMPONENTDAN TASHQARIDA (G-motion-6(b,c)): huquqsiz
       *    sessiyada SO'ROV HAM ketmaydi. Anti-naqsh — `hidden` sinfi
       *    bilan yashirish: karta so'rovni BARIBIR yuborardi va bozorning
       *    kunlik tushumi kassirning tarmoq panelida ko'rinardi — 6-faza
       *    ko'r deklaratsiyasi bitta commitda qulardi (§0.2).
       */}
      {hasPermission(roles, "report_view") && principal?.marketId ? (
        <>
          <RevenueCard />
          <OccupancyDonut />
          {/*
           * ⛔ TARTIB TASODIFIY EMAS (260818 auditi, Topilma №5).
           *
           * `LeakCard` — mahsulotning ASOSIY qiymati («band, lekin
           * to'lovsiz»), `DebtorsCard` — «kim, qancha, qachondan beri».
           * Ikkalasi ham `report_view` ostida va SHU SHART ICHIDA turadi:
           * huquqsiz sessiyada so'rov HAM ketmaydi (yuqoridagi izoh).
           *
           * ⚠ Ular tushum va bandlikdan KEYIN: birinchi ikkitasi «bozor
           *   qanday ishlayapti», keyingi ikkitasi «qayerda yo'qotish
           *   bor» degan savolga javob beradi va bu o'qish tartibi.
           */}
          <LeakCard />
          <DebtorsCard />
        </>
      ) : null}

      {/*
       * BOZOR HOLATI KARTASI — `HeadlineCard` dan KEYIN, `SECTIONS` dan
       * OLDIN (Topilma №H). `HeadlineCard` ham, `SECTIONS` ham
       * TEGILMAYDI: bosh ekranning mavjud tartibi (UI-SPEC §10.4)
       * o'zgarmaydi, karta ular ORASIGA qo'yiladi.
       *
       * ⛔ DARVOZA AYNAN `market_manage` VA TANLOV ASOSLANGAN:
       *    (a) `rbac.ts` matritsasida u FAQAT `platform_admin` da bor —
       *        direktorda ham, bozor adminida ham YO'Q, ya'ni topshiriqning
       *        «direktor bosh ekraniga tegmang» sharti mexanik bajariladi
       *        (uni 8-faza boyitadi);
       *    (b) kartaning birlamchi amali bozorni faollashtirishga olib
       *        boradi va u aynan `MARKET_MANAGE` ostidagi endpoint;
       *    (c) `market_data_view` bilan darvozalash DIREKTORNI ham
       *        qamrab, o'sha taqiqni buzardi.
       *
       * ⛔ SHART KOMPONENTDAN TASHQARIDA: huquqsiz sessiyada
       *    `GET /markets/{id}/setup-status` ga so'rov HAM ketmaydi
       *    (`cameras/page.tsx` da o'rnatilgan naqsh). Haqiqiy nazorat
       *    serverda.
       */}
      {hasPermission(roles, "market_manage") && principal?.marketId ? (
        <MarketStatusCard
          isActive={principal.marketIsActive}
          marketId={principal.marketId}
        />
      ) : null}

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
