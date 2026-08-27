"use client";

import { ScrollText, Users } from "lucide-react";
import { useTranslations } from "next-intl";

import { CashierBrief } from "@/components/dashboard/cashier-brief";
import { InspectorBrief } from "@/components/dashboard/inspector-brief";
import { MarketStatusCard } from "@/components/dashboard/market-status-card";
import { AdminPanel } from "@/components/admin/panel";
import { DirectorPanel } from "@/components/director/panel";
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

  /*
   * ⛔⛔ ADMIN PANELI CHIZILGANDA `SECTIONS` CHIZILMAYDI (260819).
   *
   *     `SECTIONS` — «Foydalanuvchilar» va «Audit jurnali» ga ikkita
   *     katta karta. Admin panelining O'ZIDA esa «Xodimlar → Barchasi»
   *     va «Oxirgi o'zgarishlar → To'liq jurnal» bloklari bor —
   *     ya'ni ayni ikki manzilga ayni ekranda IKKI marta eshik
   *     ochilardi va pastdagi ikkitasi bo'm-bo'sh turardi
   *     [jonli ko'rildi].
   *
   *     Panelsiz rollarda (kassir, nazoratchi, platforma admini)
   *     `SECTIONS` O'Z O'RNIDA QOLADI — ular uchun bu yagona eshik.
   */
  const adminPanelShown =
    principal?.marketId !== undefined &&
    principal?.marketId !== null &&
    hasPermission(roles, "tariff_manage");

  /*
   * ⛔⛔ «PANEL BORMI?» — BITTA HISOB, UCH JOYDA ISHLATILADI (260820).
   *
   *     Avval umumiy sarlavha va `HeadlineCard` `report_view` bilan
   *     yashirilardi — ya'ni faqat DIREKTOR nazarda tutilgan edi.
   *     `AdminPanel` `tariff_manage` bilan qo'shilgach, PLATFORMA
   *     ADMINI ikkalasini ham oldi: ekranda «Boshqaruv paneli / Bozor:
   *     … / Rollar: …» va darhol ostida «KARMANA TEST BOZORI ·
   *     PLATFORMA ADMINI / Admin paneli» turardi — bozor nomi ham,
   *     rol ham IKKI MARTA [jonli ko'rildi].
   *
   *     Shart endi ROLGA emas, EKRANDAGI HOLATGA bog'landi: panel
   *     chizilsa, umumiy sarlavha chizilmaydi. Yangi panel qo'shilsa
   *     ham qoida o'z-o'zidan to'g'ri ishlaydi.
   */
  const panelShown = adminPanelShown || hasPermission(roles, "report_view");

  /*
   * ⛔⛔ KASSIR PANELI KVITANSIYA SONINI O'ZI KO'RSATADI (2026-08-25,
   *     maket): birinchi hisoblagich AYNAN `headline` soni. `HeadlineCard`
   *     ham chizilsa, bitta son ekranda IKKI marta turardi — direktor
   *     panelidagi (260818) bilan bir xil xato. Nazoratchida (panelsiz,
   *     kassir ham emas) `HeadlineCard` O'Z O'RNIDA QOLADI.
   */
  const cashierShown = hasPermission(roles, "payment_create");

  /*
   * ⛔⛔ NAZORATCHI PANELI (2026-08-25 auditi N1) — kassir bilan AYNAN bir
   *     naqsh: huquq `occupancy_review`, shart KOMPONENTDAN TASHQARIDA
   *     (huquqsiz sessiyada `GET /review/budget` ga so'rov HAM ketmasin).
   *     Panel ko'rsatkichni o'zi beradi — `HeadlineCard` yashirinadi
   *     (son ikki marta chiqmasin, kassirdagi qaror bilan bir xil).
   */
  const inspectorShown =
    !cashierShown && !panelShown && hasPermission(roles, "occupancy_review");

  const sections = adminPanelShown
    ? []
    : SECTIONS.filter((section) => hasPermission(roles, section.permission));

  return (
    /*
     * ⛔ `gap-8` — 6-fazadagi `gap-6` DAN KATTA (foydalanuvchi talabi:
     *    «boshqaruv paneli va yig'ish bo'limi ya'ni sectionni katta
     *    qilasan»). Bosh ekranda mustaqil bloklar ko'p (holat, brifing,
     *    hisoblagichlar, navigatsiya) va ular zich turganda ko'z
     *    qaysi biri qayerda tugashini QIDIRADI.
     */
    <div className="flex flex-col gap-8">
      {/*
       * ⛔⛔ DIREKTORDA UMUMIY SARLAVHA CHIZILMAYDI (260818, dizayn importi).
       *
       * `DirectorPanel` ning O'ZI sarlavha beradi: bozor nomi + rol
       * («KARMANA TEST BOZORI · DIREKTOR»), «Bugun paneli» va sana
       * qatori. Ikkalasi birga chizilganda ekranda IKKITA sarlavha
       * ustma-ust turardi va bozor nomi ham ikki marta yozilardi —
       * jonli o'lchandi.
       *
       * ⚠ Kassir va nazoratchida QOLADI: ularda dizayn paneli yo'q va
       *   bu blok yagona kontekst (qaysi bozor, qaysi rol).
       */}
      {panelShown ? null : cashierShown ? (
        /*
         * KASSIRDA — maketdagi salomlashuv (2026-08-25): ism `GET /me`
         * dan (backendda BOR maydon), yo'q bo'lsa umumiy sarlavha.
         * Bozor nomi qoladi — kontekst (D-16: tarjima qilinmaydi).
         */
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold tracking-tight">
            {principal?.fullName
              ? t("dashboard.welcome", { name: principal.fullName })
              : t("nav.dashboard")}
          </h1>
          <p className="text-sm text-text-muted">
            {t("dashboard.welcomeHint")} · {principal?.marketName ?? "—"}
          </p>
        </div>
      ) : (
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
      )}

      {/*
       * ⛔ Komponentga FAQAT `marketId` uzatiladi (§10.2). Rol ham, huquq
       *    ham BERILMAYDI: qaysi son ko'rinishini server hal qiladi va
       *    klient buni takrorlay olmasligi kerak.
       *
       * ⛔⛔ DIREKTORDA CHIZILMAYDI (260818, dizayn importi).
       *
       * `Sbozor Direktor.dc.html` da sarlavha kartasi YO'Q — olti
       * katakning O'ZI panel. Ikkalasi birga chizilganda ekranda ikkita
       * «tushum» soni turardi va ular BOSHQA kunga tegishli edi
       * (sarlavha — bugun, 1-katak — kecha). Jonli o'lchandi: sarlavha
       * `16,000`, katak `0 so'm` — direktor uchun bu ziddiyat.
       *
       * ⚠ Kassir va nazoratchida QOLADI: ularda olti katak yo'q va
       *   sarlavha kartasi yagona ko'rsatkich.
       */}
      {panelShown || cashierShown || inspectorShown ? null : (
        <HeadlineCard marketId={principal?.marketId ?? null} />
      )}

      {/*
       * =====================================================================
       * ⛔⛔ KASSIR BRIFI — `HeadlineCard` DAN BEVOSITA KEYIN (260819).
       * =====================================================================
       * Kassirning bosh ekranida bitta son turardi va boshqa hech nima:
       * u yerdan ish boshlab ham, boshliqqa javob berib ham bo'lmasdi.
       * Endi tepada KVITANSIYA SONI (`HeadlineCard`), ostida esa SMENA
       * HOLATI + kunlik ishga kirish tugmasi turadi — ikkalasi birga
       * «nechta yozdim» va «qachondan beri ishdaman» savollariga javob
       * beradi.
       *
       * ⛔ SHART KOMPONENTDAN TASHQARIDA: huquqsiz sessiyada
       *    `GET /shifts/open` ga so'rov HAM ketmasin (kodbazadagi
       *    `MarketStatusCard` / `DirectorPanel` naqshi).
       *
       * ⛔ DARVOZA AYNAN `payment_create`: u kassirda bor, direktorda
       *    esa YO'Q — ya'ni direktorning dizayn paneli tegilmaydi va
       *    ikkita boshqa-boshqa «bosh ekran» paydo bo'lmaydi.
       *
       * ⛔ SUMMA CHIQARILMAYDI (komponent sarlavhasidagi izoh): kassir
       *    smenani KO'R sanaydi va yig'indini ko'rsatish o'sha
       *    mexanizmni bir qatorda bekor qilardi.
       * =====================================================================
       */}
      {cashierShown ? (
        <CashierBrief marketId={principal?.marketId ?? null} />
      ) : null}

      {inspectorShown ? <InspectorBrief /> : null}

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
      {/*
       * =====================================================================
       * ⛔⛔ DIREKTOR PANELI — FOYDALANUVCHI DIZAYNI (260818).
       * =====================================================================
       * Ilgari bu yerda beshta alohida karta turardi (`RevenueCard`,
       * `OccupancyDonut`, `LeakCard`, `DebtorsCard`). Ular MENING
       * tanlovim edi, dizaynning EMAS — va bu farq foydalanuvchi
       * tomonidan aniqlandi.
       *
       * Endi `Sbozor Direktor.dc.html` (claude.ai/design, MCP orqali
       * o'qilgan) ning olti katagi chiziladi: tartib, o'lchamlar, raqam
       * formati, kirish animatsiyasi va havolalar — dizayndan.
       *
       * ⛔ SHART KOMPONENTDAN TASHQARIDA (G-motion-6(b,c)): huquqsiz
       *    sessiyada SO'ROV HAM ketmaydi — kassirning tarmoq panelida
       *    bozorning kunlik tushumi ko'rinmasligi kerak.
       * =====================================================================
       */}
      {/*
       * =====================================================================
       * ⛔⛔ BOSH EKRAN ROLGA QARAB IKKI XIL PANEL BERADI (260819).
       * =====================================================================
       * Bugungacha bozor admini ham DIREKTOR panelini ko'rardi — ikkalasida
       * ham `report_view` bor. Lekin ular boshqa ikki savolga javob beradi:
       *
       *   direktor     -> «pul to'liq yig'ilyaptimi?»   (hisobdorlik)
       *   bozor admini -> «bozorim ishlashga tayyormi?» (sozlash)
       *
       * ⛔ DARVOZA AYNAN `tariff_manage` VA TANLOV ASOSLANGAN: bozorni
       *    KIM boshqarsa, admin panelini o'sha ko'radi. Bu huquq
       *    `market_admin` va `platform_admin` da bor, direktorda YO'Q
       *    (D-07) — ya'ni ajratish rol nomiga emas, HUQUQQA tayanadi va
       *    yangi rol qo'shilganda o'z-o'zidan to'g'ri ishlaydi.
       *
       * ⚠ Bozor admini pulni YO'QOTMAYDI: `report_view` unda qoladi va
       *   «Hisobotlar» menyuda turadi. Yo'qolgani — bosh ekrandagi
       *   takroriy panel, ma'lumot emas.
       * =====================================================================
       */}
      {principal?.marketId && hasPermission(roles, "tariff_manage") ? (
        <AdminPanel
          /* `undefined` — holat NOMA'LUM (sessiya tiklanmagan);
             o'shanda belgi chizilmaydi. */
          isDraft={
            principal.marketIsActive === undefined ||
            principal.marketIsActive === null
              ? undefined
              : !principal.marketIsActive
          }
          marketId={principal.marketId}
          marketName={principal.marketName ?? "Bozor"}
          roleLabel={roleLabels.join(" · ")}
        />
      ) : hasPermission(roles, "report_view") && principal?.marketId ? (
        <DirectorPanel
          marketName={principal.marketName ?? "Bozor"}
          /* Rollar TO'PLAM (D-05): bir odam ham direktor, ham admin
             bo'lishi mumkin — ikkalasi ham yoziladi. */
          roleLabel={roleLabels.join(" · ")}
        />
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
      {/*
       * ⛔⛔ ADMIN PANELI CHIZILGANDA BU KARTA CHIZILMAYDI (260820).
       *
       *     `MarketStatusCard` to'rt hisoblagich beradi: rasta ·
       *     sotuvchi · kamera · foydalanuvchi. `AdminPanel` ning
       *     REESTR bo'limi AYNAN shu sonlarni, sozlash halqasi esa
       *     ularning to'liqligini ko'rsatadi — ya'ni bir ekranda bir
       *     xil to'rt son IKKI MARTA turardi [jonli ko'rildi].
       *
       * ⚠ HOLAT VA FAOLLASHTIRISH YO'QOLMAYDI: panelning sozlash
       *   katagi «Ustani ochish →» bilan aynan o'sha ustaga, ya'ni
       *   faollashtirish qadamiga olib boradi.
       */}
      {hasPermission(roles, "market_manage") &&
      principal?.marketId &&
      !adminPanelShown ? (
        <MarketStatusCard
          isActive={principal.marketIsActive}
          marketId={principal.marketId}
        />
      ) : null}

      {sections.length > 0 ? (
        <ul className="grid gap-4 sm:grid-cols-2">
          {sections.map((section) => {
            const Icon = section.icon;
            return (
              <li key={section.href}>
                <Link className="block" href={section.href}>
                  <Card className="transition-colors hover:bg-surface-muted">
                    <CardHeader>
                      <span className="flex items-center gap-3 text-lg font-semibold">
                        {/*
                         * ⛔ 20px — 16px EMAS (foydalanuvchi topilmasi:
                         *    «iconlar juda kichin»). Bu kartaning
                         *    YAGONA vizual belgisi: matndan kichik
                         *    ikonka uni bezakka aylantiradi.
                         */}
                        <Icon aria-hidden="true" className="size-5" />
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
