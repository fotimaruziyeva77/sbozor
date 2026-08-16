"use client";

import { useEffect, useMemo, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslations } from "next-intl";
import { useForm, useWatch } from "react-hook-form";
import { z } from "zod";

import { RoleCheckbox } from "@/components/users/create-user-dialog";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import type { UserListItem } from "@/lib/api-types";
import { assignableRoles } from "@/lib/api-types";
import { useAuthStore } from "@/lib/auth-store";
import { adminErrorMessageKey, useUpdateUserRoles } from "@/lib/queries";
import type { Role } from "@/lib/rbac";
import { roleLabelKey } from "@/lib/rbac";

/*
 * =============================================================================
 * MAVJUD FOYDALANUVCHINING ROLLARINI TAHRIRLASH (Topilma №G).
 *
 * Bu yo'l UMUMAN YO'Q edi: backend'da rol yangilash endpointi ham,
 * UI'da menyu bandi ham. Natijada bozor ma'muriyati «rolni o'zgartirish
 * uchun hisobni o'chirib qayta yaratish» yo'liga majbur bo'lardi — u esa
 * foydalanuvchining parolini, sessiyalarini va audit izini uzib yuborardi.
 *
 * ⛔ 1. DIALOG JORIY ROLLAR BILAN OCHILADI VA HAR OCHILISHDA QAYTA
 *       TO'LDIRILADI.
 *
 *    Server to'plamni ALMASHTIRADI, qo'shmaydi. Bo'sh holatda ochilgan
 *    dialogda «saqlash» bosilsa, admin bilmagan holda mavjud rolni
 *    o'chirib yuborardi. `reset()` esa ikkinchi nuqsonni yopadi: usiz
 *    ikkinchi foydalanuvchining dialogi BIRINCHISINING tanlovi bilan
 *    ochilardi (komponent mount bo'lib qolgan holatda).
 *
 * ⛔ 2. VARIANTLAR `assignableRoles()` DAN — D-04 DARAJASINING KO'ZGUSI.
 *
 *    Haqiqiy darvoza serverda va u IKKI to'plamni ham tekshiradi:
 *    nishonning JORIY rollarini ham, so'ralayotgan YANGISINI ham
 *    (`users.py::update_user_roles`). Bu yerdagi ro'yxat faqat formada
 *    berib bo'lmaydigan katakcha KO'RINMASLIGI uchun.
 *
 * ⛔ 3. YANGI PAROL YO'Q — bu amal SIR TUG'DIRMAYDI.
 *
 *    `CreateUserDialog` va `reset-password` vaqtinchalik parol
 *    qaytaradi va shuning uchun ota-komponentga uzatadi. Rol tahriri
 *    hech qanday sir ishlab chiqarmaydi, ya'ni muvaffaqiyatda dialog
 *    shunchaki yopiladi.
 *
 * ⚠ 4. KUCHGA KIRISH LAHZASI EKRANDA HALOL AYTILADI (`editRolesHint`).
 *
 *    Rollar JWT da'volarida yashaydi; `/auth/refresh` ularni DB'dan
 *    qayta o'qiydi, ya'ni yangi to'plam keyingi token yangilanishida
 *    (≤15 daq) kuchga kiradi. Huquqni DARHOL tortib olish yo'li — rol
 *    tahriri emas, BLOKLASH (D-08). Buni yashirish admin «pasaytirdim,
 *    demak endi kira olmaydi» deb o'ylashiga olib borardi.
 * =============================================================================
 */

/** Rol guruhining xato izohi — BARQAROR `id` (`Field` konvensiyasi). */
const ROLES_ERROR_ID = "edit-roles-error";

type EditRolesValues = { roles: string[] };

export function EditRolesDialog({
  onOpenChange,
  open,
  user,
}: {
  onOpenChange: (open: boolean) => void;
  open: boolean;
  /** `null` — dialog yopiq va nishon hali tanlanmagan. */
  user: UserListItem | null;
}) {
  const t = useTranslations();
  const tRoles = useTranslations("roles");
  const { principal } = useAuthStore();
  const updateRoles = useUpdateUserRoles();
  const [formError, setFormError] = useState<string | null>(null);

  const roleOptions = assignableRoles(principal?.isPlatformAdmin ?? false);

  const schema = useMemo(
    () =>
      z.object({
        roles: z.array(z.string()).min(1, { error: t("users.rolesRequired") }),
      }),
    [t],
  );

  const {
    control,
    formState: { errors, isSubmitted, isSubmitting },
    handleSubmit,
    reset,
    setValue,
  } = useForm<EditRolesValues>({
    resolver: zodResolver(schema),
    defaultValues: { roles: user === null ? [] : [...user.roles] },
  });

  /*
   * ⚠ HAR OCHILISHDA QAYTA TO'LDIRISH (yuqoridagi 1-band). Bog'liqlik
   *   `user.id` VA `open` — ikkinchisisiz bir xil foydalanuvchini ikki
   *   marta ochgan admin birinchi seansdagi bekor qilinmagan tanlovni
   *   ko'rardi.
   *
   * ⚠ `setFormError(null)` BU YERDA CHAQIRILMAYDI (`react-hooks/
   *   set-state-in-effect`) va u KERAK HAM EMAS: xato holati YOPILISHDA
   *   tozalanadi (`handleOpenChange`), ya'ni dialog har doim toza
   *   ochiladi. Effektga qo'yish ikkinchi tozalash nuqtasi bo'lardi va
   *   ular bir kun ajralib ketardi.
   */
  const userId = user?.id ?? null;
  const userRoles = user === null ? "" : [...user.roles].join(",");
  useEffect(() => {
    if (!open) return;
    reset({ roles: userRoles === "" ? [] : userRoles.split(",") });
  }, [open, reset, userId, userRoles]);

  /*
   * `useWatch`, `watch()` EMAS: `watch` — `useForm()` qaytaradigan oddiy
   * funksiya va React Compiler uni memoizatsiya qila olmaydi (eskirgan
   * UI xavfi). `useWatch` esa hook bo'lib, obunani to'g'ri e'lon qiladi.
   */
  const selectedRoles = useWatch({ control, name: "roles" });

  /*
   * ⛔ QAYTA VALIDATSIYA SHARTI — FORMA YUBORILGANMI, ROL BORMI EMAS.
   *   `create-user-dialog.tsx` da o'lchangan T2 qarorining aynan nusxasi:
   *   `selectedRoles.length > 0` sharti 0 -> 1 o'tishini QAMRAMASDI va
   *   foydalanuvchi xatoni tuzatgan lahzada xabar ekranda QOLARDI.
   */
  function toggleRole(role: Role) {
    const next = selectedRoles.includes(role)
      ? selectedRoles.filter((item) => item !== role)
      : [...selectedRoles, role];
    setValue("roles", next, { shouldValidate: isSubmitted });
  }

  function handleOpenChange(next: boolean) {
    if (!next) setFormError(null);
    onOpenChange(next);
  }

  async function onSubmit(values: EditRolesValues) {
    if (user === null) return;
    setFormError(null);
    try {
      await updateRoles.mutateAsync({ userId: user.id, roles: values.roles });
      handleOpenChange(false);
    } catch (error) {
      setFormError(t(adminErrorMessageKey(error)));
    }
  }

  return (
    <Dialog.Root onOpenChange={handleOpenChange} open={open}>
      <Dialog.Content
        description={t("users.editRolesHint")}
        size="lg"
        title={t("users.editRolesTitle")}
      >
        <form
          className="flex flex-col gap-4"
          noValidate
          onSubmit={handleSubmit(onSubmit)}
        >
          {/* D-16: ism/telefon DB kontenti — tarjima qilinmaydi. */}
          {user ? (
            <p className="rounded-sm bg-surface-muted px-3 py-2 text-sm font-semibold">
              {user.full_name ?? user.phone}
            </p>
          ) : null}

          {/*
           * `fieldset`/`legend` — `Field` EMAS: rollar bitta boshqaruv
           * elementi emas, checkbox GURUHI (`create-user-dialog` dagi
           * bilan aynan bir xil sabab).
           */}
          <fieldset
            aria-describedby={errors.roles ? ROLES_ERROR_ID : undefined}
            className="flex flex-col gap-2"
          >
            <legend className="mb-1 text-sm font-semibold">
              {t("users.rolesLabel")}
            </legend>
            {roleOptions.map((role) => {
              const labelKey = roleLabelKey(role);
              if (labelKey === null) return null;
              return (
                <RoleCheckbox
                  checked={selectedRoles.includes(role)}
                  idPrefix="edit-roles"
                  key={role}
                  label={tRoles(labelKey)}
                  onToggle={() => toggleRole(role)}
                  role={role}
                />
              );
            })}
            {errors.roles ? (
              <p
                className="text-sm text-danger-text"
                id={ROLES_ERROR_ID}
                role="alert"
              >
                {errors.roles.message}
              </p>
            ) : null}
          </fieldset>

          {formError ? (
            <p
              className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
              role="alert"
            >
              {formError}
            </p>
          ) : null}

          <Dialog.Footer>
            <Button
              className="sm:flex-1"
              disabled={isSubmitting}
              size="lg"
              type="submit"
            >
              {isSubmitting ? t("common.loading") : t("common.save")}
            </Button>
            <Dialog.Close asChild>
              <Button className="sm:flex-1" size="lg" variant="secondary">
                {t("common.cancel")}
              </Button>
            </Dialog.Close>
          </Dialog.Footer>
        </form>
      </Dialog.Content>
    </Dialog.Root>
  );
}
