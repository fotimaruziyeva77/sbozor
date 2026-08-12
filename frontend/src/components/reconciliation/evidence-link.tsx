"use client";

import { ExternalLink } from "lucide-react";
import { useTranslations } from "next-intl";

import { Link } from "@/i18n/navigation";
import { useAuthStore } from "@/lib/auth-store";
import { hasPermission } from "@/lib/rbac";

/*
 * =============================================================================
 * ⛔⛔ DALIL — HAVOLA, KADR EMAS. BU FAYL O'SHA QARORNING BUTUN SHAKLI.
 *
 * -----------------------------------------------------------------------
 * ⛔ 1. NEGA KADR BU YERDA CHIZILMAYDI — INTIZOM EMAS, MEXANIKA (M-7)
 * -----------------------------------------------------------------------
 * Sessiya tokeni `Authorization` sarlavhasida yashaydi, cookie'da ⛔ EMAS
 * (cookie faqat refresh uchun). Demak brauzer o'zi ochadigan
 * `<a href="…/…/{id}/image">` ⛔ TOKENSIZ ketadi va ⛔ 401 oladi.
 *
 * Ya'ni «dalil havolasi» ni rasm BAYTLARIGA havola deb tushunish UI'ni
 * ⛔ BIRINCHI BOSISHDAYOQ buzardi — va uni tuzatish uchun ijrochi tabiiy
 * ravishda rasmni SAHIFAGA qo'yishga o'tardi, ya'ni «dalil-kadr bu
 * yuzada chizilmaydi» taqig'ini ⛔ AYLANIB O'TARDI.
 *
 * -----------------------------------------------------------------------
 * ⛔ 2. TANLANGAN YO'L: MAVJUD YUZAGA ILOVA ICHIDAGI NAVIGATSIYA
 * -----------------------------------------------------------------------
 * Nishon — ⛔ `/billing?day={service_date}`, ya'ni ALLAQACHON mavjud
 * yuza. Kadr o'sha yerda, ⛔ SESSIYA TOKENI OSTIDA chiziladi va u
 * o'zining yagona marshrutida qoladi. Bu yerda ⛔ ikkinchi kadr yuzasi
 * ochilmaydi: ikkinchi yuza kadr marshrutlarining yopiq to'plamini
 * kengaytirish bosimini tug'dirardi.
 *
 * ⛔ Shuning uchun bu KATALOGDA rasm chizishning BIRORTA usuli ham
 *    yozilmaydi va u mexanik skan bilan o'lchanadi
 *    (`scripts/reconciliation-copy.test.mjs`). ⚠ Taqiqlangan token
 *    nomlari bu izohda LITERAL yozilmaydi — skan izohni koddan
 *    ajratsa ham, nusxa darvozani o'ziga qarshi qo'yish odati
 *    kodbazada ATAYIN rad etilgan (`badge.tsx:24-26` konvensiyasi).
 *
 * ⛔ MATN «Dalilni ochish» — «Kadrni ko'rish» ⛔ EMAS: bu sahifada kadr
 *    KO'RINMAYDI va yolg'on affordans foydalanuvchini aldardi.
 *
 * ⛔ YANGI OYNADA OCHILMAYDI: ilovaning yangi nusxasi auth holatini
 *    qayta tiklaydi va foydalanuvchini login ekraniga tashlashi mumkin.
 *    ⚠ Mos atribut ham, uning qiymati ham bu faylda YOZILMAYDI.
 *
 * -----------------------------------------------------------------------
 * ⛔ 3. HUQUQSIZ KO'RUVCHIDA ELEMENT ⛔ UMUMAN CHIZILMAYDI
 * -----------------------------------------------------------------------
 * O'chirilgan tugma ⛔ EMAS, tooltip ⛔ EMAS: o'chirilgan tugma MAVJUD
 * imkoniyatni e'lon qilardi. Bu RBAC UI ko'zgusining mavjud qoidasi.
 *
 * ⚠⚠ VA BU SHOX BUGUN ERISHIB BO'LMAYDI — SABAB SHU YERDA QOLADI.
 *    Bugungi matritsada `report_view` egalarining IKKALASIDA ham
 *    `camera_view` bor, ya'ni «huquqsiz ko'ruvchi» real sessiyada
 *    UCHRAMAYDI. Shuning uchun:
 *      (a) bu KELAJAKKA mo'ljallangan qo'riqchi;
 *      (b) uning testi SUN'IY rollar bilan yoziladi va shu sabab test
 *          faylida ham izoh sifatida qoladi — aks holda keyingi ijrochi
 *          uni «foydasiz test» deb o'chirardi.
 *
 * ⛔ 4. DALILSIZ QATORDA HAM CHIZILMAYDI: marshrut bermagan qator uchun
 *    affordans ham, platsholder ham qo'yilmaydi (05-14 darsi).
 * =============================================================================
 */

export type EvidenceLinkProps = {
  /** Nishon kuni — qator O'ZINING xizmat sanasi, «bugun» EMAS. */
  serviceDate: string;
  /** Dalil identifikatorlari; bo'sh bo'lsa element chizilmaydi. */
  snapshotIds: readonly string[];
};

export function EvidenceLink({ serviceDate, snapshotIds }: EvidenceLinkProps) {
  const t = useTranslations();
  const { principal } = useAuthStore();

  const roles = principal?.roles ?? [];
  const maySeeEvidence =
    hasPermission(roles, "camera_view") ||
    hasPermission(roles, "occupancy_review");

  /* ⛔ Ikkala shox ham `null` — o'chirilgan element EMAS (yuqoriga qarang). */
  if (!maySeeEvidence) return null;
  if (snapshotIds.length === 0) return null;

  return (
    <Link
      className="inline-flex min-h-11 items-center gap-1 rounded-md px-2 text-sm text-text-muted underline-offset-4 hover:underline focus-visible:ring-2 focus-visible:ring-accent/25 focus-visible:outline-none"
      href={`/billing?day=${encodeURIComponent(serviceDate)}`}
    >
      <ExternalLink aria-hidden="true" className="size-4" />
      {t("recon.evidenceOpen")}
    </Link>
  );
}
