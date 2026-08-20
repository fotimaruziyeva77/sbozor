"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { ArrowLeft } from "lucide-react";

import { ForbiddenNotice } from "@/components/auth/forbidden-notice";
import { PlanEditor } from "@/components/stalls/plan-editor";
import { useAuthStore } from "@/lib/auth-store";
import { hasPermission } from "@/lib/rbac";

/*
 * =============================================================================
 * PLAN MUHARRIRI — ALOHIDA SAHIFA, XARITANING «REJIMI» EMAS (260820).
 *
 * ⛔⛔ NEGA ALOHIDA MARSHRUT.
 *
 *   `/map` — HAMMA ko'radigan kundalik ekran: direktor, nazoratchi,
 *   kassir shu yerdan rasta qidiradi. Chizish esa NODIR va XAVFLI ish:
 *   bitta noto'g'ri surish butun qatorni ko'chirib yuboradi.
 *
 *   Ularni bitta ekranga qo'yish degani — kundalik foydalanuvchi har
 *   kirganda tahrir asboblarini ko'rishi va tasodifan chizmani
 *   buzishi. Alohida marshrut esa tahrirni ATAYIN qilingan ish qiladi:
 *   odam «Planni chizish» ni BOSIB kiradi.
 *
 * ⛔ HUQUQ SO'ROVDAN OLDIN: `stall_manage` bo'lmasa muharrir umuman
 *   render qilinmaydi, ya'ni `GET /stalls/map` ga so'rov ham ketmaydi.
 *   Direktorda bu huquq YO'Q (D-07) — u xaritani ko'radi, lekin
 *   ko'chira olmaydi, va buni SERVER ham qaytaradi (403).
 * =============================================================================
 */
export default function PlanEditorPage() {
  const t = useTranslations();
  const { principal } = useAuthStore();

  if (!hasPermission(principal?.roles ?? [], "stall_manage")) {
    return <ForbiddenNotice />;
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <Link
          className="inline-flex w-fit items-center gap-1 text-sm font-semibold text-text-muted hover:text-text"
          href="/map"
        >
          <ArrowLeft aria-hidden="true" className="size-4" />
          {t("plan.backToMap")}
        </Link>
        <h1 className="text-2xl font-semibold tracking-tight">
          {t("plan.title")}
        </h1>
        <p className="max-w-2xl text-sm text-text-muted">{t("plan.intro")}</p>
      </div>

      <PlanEditor />
    </div>
  );
}
