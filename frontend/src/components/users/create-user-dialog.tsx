"use client";

import { useMemo, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslations } from "next-intl";
import { useForm, useWatch } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import type { ApiLocale } from "@/lib/api-types";
import { assignableRoles, LOCALE_LABELS, LOCALES, localeSchema } from "@/lib/api-types";
import { useAuthStore } from "@/lib/auth-store";
import { adminErrorMessageKey, useCreateUser } from "@/lib/queries";
import type { Role } from "@/lib/rbac";
import { roleLabelKey } from "@/lib/rbac";

/*
 * Yangi foydalanuvchi (D-04 ikki bosqichli yaratish, D-05 rollar to'plami).
 *
 * ROL TANLOVI KO'P TANLOVLI (D-05). Kichik bozorda bir odam ham bozor
 * admini, ham kassir bo'ladi — bitta tanlovli boshqaruv (radio) bu holatni
 * umuman ifodalay olmasdi va sxemaga (`user_market_roles.roles` massivi)
 * ham zid bo'lardi.
 *
 * KO'RSATILADIGAN ROLLAR `assignableRoles()` dan keladi (D-04 darajasi):
 * bozor admini o'ziga teng yoki undan yuqori rolni umuman KO'RMAYDI. Bu
 * faqat UX ko'zgusi — haqiqiy darvoza serverda va u 403 `role_not_allowed`
 * qaytaradi, shuning uchun o'sha xato baribir tarjima bilan ko'rsatiladi.
 */

/**
 * Telefon raqamining SHAKLI (D-01: telefon — yagona identifikator).
 *
 * Qat'iy E.164 ga keltirish SERVERDA (`normalize_phone`) bajariladi; bu
 * yerdagi tekshiruv faqat "yozishda adashildi" holatini forma ichida
 * ushlaydi va `+998 90 123 45 67`, `998901234567`, `901234567`
 * shakllarining hammasini qabul qiladi.
 *
 * EKSPORT QILINGAN (02-15): sotuvchi formasi ham AYNAN shu shaklni
 * tekshiradi (D-12 — telefon bozor ichida yagona identifikator). Ikkinchi
 * nusxa yozish ikki regexni yaratardi va ular bir kun ajralib ketardi —
 * o'shanda bir yo'l qabul qilgan raqamni ikkinchisi rad etardi.
 */
export function looksLikeUzbekPhone(value: string): boolean {
  const digits = value.replace(/\D/gu, "");
  return /^998\d{9}$/u.test(digits) || /^\d{9}$/u.test(digits);
}

type CreateUserValues = {
  phone: string;
  fullName: string;
  roles: string[];
  locale: ApiLocale;
};

/**
 * Rol guruhining xato izohi — BARQAROR `id` (`Field` konvensiyasi).
 *
 * `useId()` EMAS va bu ataylab: bu dialog sahifada AYNAN BITTA marta
 * render qilinadi (`open` bilan boshqariladi) va qo'shni maydonlar ham
 * qat'iy `create-*` identifikatorlarini ishlatadi. Ikki xil sxemani
 * aralashtirish `aria-describedby` ni kod ko'rigida tekshirib bo'lmas
 * qilardi.
 */
const ROLES_ERROR_ID = "create-roles-error";

const EMPTY_VALUES: CreateUserValues = {
  phone: "",
  fullName: "",
  roles: [],
  locale: "uz-Latn",
};

export function CreateUserDialog({
  onCreated,
  onOpenChange,
  open,
}: {
  onCreated: (temporaryPassword: string) => void;
  onOpenChange: (open: boolean) => void;
  open: boolean;
}) {
  const t = useTranslations();
  const tRoles = useTranslations("roles");
  const { principal } = useAuthStore();
  const createUser = useCreateUser();
  const [formError, setFormError] = useState<string | null>(null);

  const roleOptions = assignableRoles(principal?.isPlatformAdmin ?? false);

  const schema = useMemo(
    () =>
      z.object({
        phone: z
          .string()
          .min(1, { error: t("errors.required") })
          .refine(looksLikeUzbekPhone, { error: t("auth.invalidPhone") }),
        fullName: z.string(),
        roles: z.array(z.string()).min(1, { error: t("users.rolesRequired") }),
        locale: localeSchema,
      }),
    [t],
  );

  const {
    control,
    formState: { errors, isSubmitted, isSubmitting },
    handleSubmit,
    register,
    reset,
    setValue,
  } = useForm<CreateUserValues>({
    resolver: zodResolver(schema),
    defaultValues: EMPTY_VALUES,
  });

  /*
   * `useWatch`, `watch()` EMAS: `watch` — `useForm()` qaytaradigan oddiy
   * funksiya va React Compiler uni memoizatsiya qila olmaydi (eskirgan UI
   * xavfi). `useWatch` esa hook bo'lib, obunani to'g'ri e'lon qiladi.
   */
  const selectedRoles = useWatch({ control, name: "roles" });

  /*
   * ⛔ QAYTA VALIDATSIYA SHARTI — FORMA YUBORILGANMI, ROL BORMI EMAS.
   *
   *   Ilgari shart `selectedRoles.length > 0` edi va u AYNAN 0 -> 1
   *   o'tishini qamramasdi — ya'ni foydalanuvchi xatoni tuzatgan
   *   lahzada qayta validatsiya BO'LMASDI va `users.rolesRequired`
   *   ekranda QOLARDI. Bu «tuzatdim, lekin hech nima o'zgarmadi»
   *   holati va u boshlang'ich nuqsondan ham chalg'ituvchiroq.
   *
   *   `isSubmitted` — RHF ning O'Z bayrog'i: forma bir marta
   *   yuborilgunicha jim turamiz (terish paytida qichqirmaslik
   *   qoidasi), yuborilgandan keyin esa HAR toggle darhol qayta
   *   baholanadi. Shartsiz `true` ham ishlardi, lekin u dialog
   *   ochilishi bilanoq xato ko'rsatishga yo'l ochib qo'yardi.
   */
  function toggleRole(role: Role) {
    const next = selectedRoles.includes(role)
      ? selectedRoles.filter((item) => item !== role)
      : [...selectedRoles, role];
    setValue("roles", next, { shouldValidate: isSubmitted });
  }

  function handleOpenChange(next: boolean) {
    if (!next) {
      reset(EMPTY_VALUES);
      setFormError(null);
    }
    onOpenChange(next);
  }

  async function onSubmit(values: CreateUserValues) {
    setFormError(null);
    try {
      const created = await createUser.mutateAsync({
        phone: values.phone,
        fullName: values.fullName.trim() === "" ? null : values.fullName.trim(),
        roles: values.roles,
        locale: values.locale,
      });

      // Parol dialogdan CHIQIB ketmaydi — u ota-komponentga uzatiladi va
      // o'sha yerda bir martalik oynada ko'rsatiladi (D-02).
      handleOpenChange(false);
      onCreated(created.temporary_password);
    } catch (error) {
      setFormError(t(adminErrorMessageKey(error)));
    }
  }

  return (
    <Dialog.Root onOpenChange={handleOpenChange} open={open}>
      <Dialog.Content
        description={t("users.createHint")}
        size="lg"
        srOnlyDescription
        title={t("users.createTitle")}
      >
        <form
          className="flex flex-col gap-4"
          noValidate
          onSubmit={handleSubmit(onSubmit)}
        >
          <Field
            error={errors.phone?.message}
            id="create-phone"
            label={t("users.phoneLabel")}
          >
            <Input
              aria-describedby={errors.phone ? "create-phone-error" : undefined}
              aria-invalid={errors.phone ? true : undefined}
              autoComplete="off"
              id="create-phone"
              inputMode="tel"
              placeholder={t("auth.phoneHint")}
              type="tel"
              {...register("phone")}
            />
          </Field>

          <Field id="create-full-name" label={t("users.fullNameLabel")}>
            <Input
              autoComplete="off"
              id="create-full-name"
              {...register("fullName")}
            />
          </Field>

          {/*
           * `fieldset`/`legend` — `Field` EMAS: rollar bitta boshqaruv
           * elementi emas, checkbox GURUHI. `Field` ning `htmlFor` i
           * guruhga bog'lana olmaydi, `legend` esa aynan shu uchun bor.
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
                  key={role}
                  label={tRoles(labelKey)}
                  onToggle={() => toggleRole(role)}
                  role={role}
                />
              );
            })}
            {/*
             * `role="alert"` — xabar formaning O'RTASIDA tug'iladi va
             * fokus saqlash tugmasida qoladi; e'lonsiz u skrinriderda
             * umuman eshitilmasdi. `id` esa `Field` ning `${id}-error`
             * konvensiyasi bilan BIR CHIZIQDA: checkbox guruhi `Field`
             * ga o'ralmaydi (yuqoridagi izohdagi sabab kuchda), lekin
             * xatoni boshqaruvga bog'lash qoidasi baribir amal qiladi.
             */}
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

          <Field id="create-locale" label={t("users.localeLabel")}>
            {/* Yorliqlar ENDONIM — tarjima qilinmaydi (`LOCALE_LABELS`). */}
            <Select id="create-locale" {...register("locale")}>
              {LOCALES.map((code) => (
                <option key={code} lang={code} value={code}>
                  {LOCALE_LABELS[code]}
                </option>
              ))}
            </Select>
          </Field>

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

/** Bitta rol katakchasi — `type="checkbox"` (D-05: ko'p tanlovli). */
function RoleCheckbox({
  checked,
  label,
  onToggle,
  role,
}: {
  checked: boolean;
  label: string;
  onToggle: () => void;
  role: string;
}) {
  return (
    <label
      // `border-ui` — bu yorliq checkbox'ning barmoq nishoni, ya'ni
      // boshqaruv elementi (WCAG 2.2 SC 1.4.11, 1.28:1 -> 3.64:1).
      className="flex min-h-11 cursor-pointer items-center gap-3 rounded-md border border-border-ui px-3 py-2 text-sm transition-colors hover:bg-surface-muted"
      htmlFor={`create-role-${role}`}
    >
      <input
        checked={checked}
        className="size-4 accent-accent"
        id={`create-role-${role}`}
        onChange={onToggle}
        type="checkbox"
        value={role}
      />
      {label}
    </label>
  );
}
