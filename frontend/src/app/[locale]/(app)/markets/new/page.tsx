"use client";

import { useTranslations } from "next-intl";

import { MarketRequisitesForm } from "@/components/wizard/market-requisites-form";
import { WizardShell } from "@/components/wizard/wizard-shell";
import { useAuthStore } from "@/lib/auth-store";
import { hasPermission } from "@/lib/rbac";

/*
 * =============================================================================
 * Ustaning BIRINCHI marshruti — faqat 1-qadam (UI-SPEC §6.1).
 *
 * NEGA ALOHIDA MARSHRUT: 1-qadamgacha yangi bozorning tenant konteksti
 * MAVJUD EMAS — u aynan shu qadam natijasida tug'iladi. Bitta marshrutga
 * sig'dirish "market_id bormi?" shartini har render'da takrorlashni talab
 * qilardi. Shuning uchun `?step` bu yerda YO'Q va bo'lishi ham kerak emas.
 *
 * IKKI DARVOZA, IKKALASI HAM MAJBURIY (T-02-126): `market_manage` huquqi
 * VA platforma admini bayrog'i. D-07 bo'yicha `market_manage` faqat
 * platforma adminida bo'ladi, ya'ni ikkinchi tekshiruv bugun ortiqcha
 * ko'rinadi — lekin u matritsa kengayib ketgan kunda YAGONA to'siq bo'lib
 * qoladi. Klientdagi tekshiruv serverdagining O'RNINI BOSMAYDI: 02-11
 * `require_platform_admin` + `require_permission` ni ikkalasini ham
 * qo'yadi va `test_market_admin_cannot_create_market` buni qulflaydi.
 *
 * ⚠ `marketId={null}` — ATAYIN. Sessiyada BOSHQA bozor tanlangan bo'lishi
 * mumkin (platforma admini tizimga aynan shunday kiradi) va uning
 * to'liqlik holatini yangi bozor ustasida ko'rsatish sof yolg'on bo'lardi:
 * rels "4 qadam bajarilgan" deb turgan bo'lardi, holbuki hali bozorning
 * o'zi ham yo'q.
 * =============================================================================
 */
export default function NewMarketPage() {
  const t = useTranslations();
  const { principal } = useAuthStore();

  const roles = principal?.roles ?? [];
  const canCreate =
    hasPermission(roles, "market_manage") &&
    (principal?.isPlatformAdmin ?? false);

  if (!canCreate) {
    return (
      <p
        className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
        role="alert"
      >
        {t("errors.forbidden")}
      </p>
    );
  }

  return (
    <WizardShell currentStep={1} marketId={null} title={t("wizard.title")}>
      <MarketRequisitesForm />
    </WizardShell>
  );
}
