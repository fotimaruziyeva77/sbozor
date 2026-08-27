"use client";

import { useState } from "react";
import { UserPlus } from "lucide-react";
import { useTranslations } from "next-intl";

import { ForbiddenNotice } from "@/components/auth/forbidden-notice";
import { ReadOnlyNote } from "@/components/auth/read-only-note";
import { ImportPanel } from "@/components/import/import-panel";
import { CreateUserDialog } from "@/components/users/create-user-dialog";
import { TempPasswordDialog } from "@/components/users/temp-password-dialog";
import { UserList } from "@/components/users/user-list";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/lib/auth-store";
import { hasPermission } from "@/lib/rbac";

/*
 * Foydalanuvchi boshqaruvi (D-04, D-02, D-05, D-08).
 *
 * IKKI HUQUQ, IKKI XIL NATIJA:
 *   `USER_VIEW`   — ro'yxatni ko'rish (platforma admini, direktor, bozor admini)
 *   `USER_MANAGE` — yaratish / bloklash / parol tiklash (direktorda YO'Q — D-07)
 *
 * Huquqsiz kirgan foydalanuvchi (kassir, nazoratchi) `errors.forbidden`
 * ko'radi. Navigatsiyada havola allaqachon yashirilgan, ya'ni bu ekran
 * faqat manzilni QO'LDA kiritganda ochiladi — va shunda ham hech qanday
 * so'rov yuborilmaydi. Haqiqiy nazorat serverda: `require_permission`
 * dependency'si 403 qaytaradi (T-01-70).
 *
 * VAQTINCHALIK PAROL bitta joyda yashaydi — shu sahifaning holatida. Uni
 * yaratish dialogi ham, ro'yxatdagi "parolni tiklash" ham shu yerga uzatadi,
 * dialog yopilganda esa qiymat `null` ga qaytadi (D-02, T-01-68).
 *
 * ⚠ IKKITA YO'L, IKKI XIL MIQYOS (MARKET-07, ROADMAP self-service qoidasi).
 * Dialog — BITTA odam uchun (yangi kassir ishga keldi); import paneli —
 * ma'muriyat bergan BUTUN ro'yxat uchun. Ikkinchisi birinchisining o'rnini
 * bosmaydi va aksincha ham: 30 kishilik bozor uchun dialogni 30 marta
 * to'ldirish "muhandis aralashuvi bilan ishlaydigan onboarding" ning
 * yumshoq ko'rinishi bo'lardi va u qabul qilinmaydi.
 *
 * Panel ro'yxatdan KEYIN turadi: kundalik ish — mavjud a'zolarni ko'rish,
 * ommaviy yuklash esa bozor ochilishida bir-ikki marta bo'ladigan amal.
 */
export default function UsersPage() {
  const t = useTranslations();
  const { principal } = useAuthStore();
  const [createOpen, setCreateOpen] = useState(false);
  const [temporaryPassword, setTemporaryPassword] = useState<string | null>(
    null,
  );

  const roles = principal?.roles ?? [];
  const canView = hasPermission(roles, "user_view");
  const canManage = hasPermission(roles, "user_manage");

  if (!canView) {
    return <ForbiddenNotice />;
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">
          {t("users.title")}
        </h1>

        {canManage ? (
          <Button onClick={() => setCreateOpen(true)}>
            <UserPlus aria-hidden="true" />
            {t("users.create")}
          </Button>
        ) : null}
      </div>

      {canManage ? null : <ReadOnlyNote />}

      <UserList onTemporaryPassword={setTemporaryPassword} />

      {/*
       * Panel `canManage` bo'lmasa UMUMAN chizilmaydi — bu UI ko'zgusi
       * (T-01-62). Haqiqiy darvoza serverda:
       * `require_permission(USER_MANAGE)`, ya'ni direktor so'rovni qo'lda
       * yuborsa ham 403 oladi.
       */}
      {canManage ? <ImportPanel kind="staff" /> : null}

      {canManage ? (
        <CreateUserDialog
          onCreated={setTemporaryPassword}
          onOpenChange={setCreateOpen}
          open={createOpen}
        />
      ) : null}

      <TempPasswordDialog
        onClose={() => setTemporaryPassword(null)}
        password={temporaryPassword}
      />
    </div>
  );
}
