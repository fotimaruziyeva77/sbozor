"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Tag } from "lucide-react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTimeZone, useTranslations } from "next-intl";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import type { StallListItem } from "@/lib/api-types";
import { marketErrorMessageKey } from "@/lib/market-errors";
import { useCategoriesQuery, useSetStallCategory } from "@/lib/market-queries";

/*
 * =============================================================================
 * Rasta TOIFASINI o'zgartirish (D-04 — voris modeli).
 *
 * Bu dialog FAQAT MAVJUD rasta uchun. Yaratish oqimida chaqirilmaydi: yangi
 * rastaning boshlang'ich toifasi `POST /stalls` tanasida ketadi va uning
 * davri sanasini server `market_profile.operating_since` dan qo'yadi.
 *
 * NEGA ALOHIDA DIALOG: toifa — SANADAN kuchga kiradigan atribut. Uni oddiy
 * tahrir formasida almashtirish "kechadan boshlab boshqa toifa edi" degan
 * ma'noni berardi va o'tmishdagi kunlik patta hisobini qayta yozardi.
 * =============================================================================
 */

type CategoryFormValues = {
  category_id: string;
  valid_from: string;
};

const EMPTY_VALUES: CategoryFormValues = { category_id: "", valid_from: "" };

/**
 * Bozor mintaqasidagi ERTANGI kun, `YYYY-MM-DD`.
 *
 * Mintaqa `next-intl` konfiguratsiyasidan olinadi (`Asia/Tashkent`) —
 * `toISOString()` UTC beradi va +5 mintaqada u kechqurun BUGUNGI kunni
 * ko'rsatardi, ya'ni maydon serverning rad etadigan sanasini taklif
 * qilardi. `en-CA` formatlagichi ISO tartibini beradi.
 */
function tomorrowIn(timeZone: string): string {
  const tomorrow = new Date(Date.now() + 24 * 60 * 60 * 1000);
  return new Intl.DateTimeFormat("en-CA", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(tomorrow);
}

export function StallCategoryDialog({
  onOpenChange,
  open,
  stall,
}: {
  onOpenChange: (open: boolean) => void;
  open: boolean;
  stall: StallListItem | null;
}) {
  const t = useTranslations();
  const timeZone = useTimeZone() ?? "Asia/Tashkent";
  const [formError, setFormError] = useState<string | null>(null);
  const errorRef = useRef<HTMLParagraphElement>(null);

  const categoriesQuery = useCategoriesQuery({ enabled: open });
  const setCategory = useSetStallCategory();

  /*
   * ⚠ QULAYLIK, DARVOZA EMAS.
   *
   * `min` atributi ham, quyidagi zod sharti ham foydalanuvchiga to'g'ri
   * sanani TAKLIF qiladi, xolos. Ularni DevTools bilan olib tashlash
   * mumkin va bu hech narsani ochmaydi: haqiqiy tekshiruv serverda,
   * `set_category()` ning ilova darajasidagi `valid_from > business_today()`
   * darvozasida (02-08, T-02-61a) va u uchta test bilan qulflangan.
   *
   * Chegara QAT'IY (`>`): server BUGUNGI sanani ham rad etadi va javob
   * `stalls.categoryPastLocked` matniga aylanadi. Shuning uchun eng erta
   * ruxsat etilgan qiymat — ERTAGA.
   */
  const minValidFrom = useMemo(() => tomorrowIn(timeZone), [timeZone]);

  const schema = useMemo(
    () =>
      z.object({
        category_id: z.string().min(1, { error: t("errors.required") }),
        valid_from: z
          .string()
          .min(1, { error: t("errors.required") })
          // `minValidFrom` ning O'ZI ertangi kun, ya'ni `>=` "qat'iy
          // kelajak" degani. ISO sanalarni leksikografik solishtirish
          // to'g'ri ishlaydi (`YYYY-MM-DD` — qat'iy kenglikda).
          .refine((value) => value >= minValidFrom, {
            error: t("stalls.categoryPastLocked"),
          }),
      }),
    [minValidFrom, t],
  );

  const {
    formState: { errors, isSubmitting },
    handleSubmit,
    register,
    reset,
  } = useForm<CategoryFormValues>({
    resolver: zodResolver(schema),
    defaultValues: EMPTY_VALUES,
  });

  useEffect(() => {
    if (!open) return;
    reset({ category_id: "", valid_from: minValidFrom });
  }, [minValidFrom, open, reset]);

  /*
   * Server xatosi dialog YOPILGANDA tozalanadi, effektda EMAS: effekt
   * ichidagi sinxron `setState` kaskadli renderga olib keladi
   * (`react-hooks/set-state-in-effect`). Yopilishda tozalash bir xil
   * natijani beradi — qayta ochilgan dialog doim toza boshlanadi.
   */
  function handleOpenChange(next: boolean) {
    if (!next) setFormError(null);
    onOpenChange(next);
  }

  // Server xatosi kelganda fokus xato blokiga ko'chadi (§6.8).
  useEffect(() => {
    if (formError !== null) errorRef.current?.focus();
  }, [formError]);

  async function onSubmit(values: CategoryFormValues) {
    if (!stall) return;
    setFormError(null);
    try {
      await setCategory.mutateAsync({
        stallId: stall.id,
        category_id: values.category_id,
        valid_from: values.valid_from,
      });
      handleOpenChange(false);
    } catch (error) {
      // Server rad etsa xato YUTILMAYDI — u forma tepasida ko'rsatiladi.
      setFormError(t(marketErrorMessageKey(error)));
    }
  }

  return (
    <Dialog.Root onOpenChange={handleOpenChange} open={open}>
      <Dialog.Content icon={Tag}
        description={t("stalls.changeCategoryHint")}
        size="lg"
        title={t("stalls.changeCategory")}
      >
        <form
          className="flex flex-col gap-4"
          noValidate
          onSubmit={handleSubmit(onSubmit)}
        >
          {formError ? (
            <p
              className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
              ref={errorRef}
              role="alert"
              tabIndex={-1}
            >
              {formError}
            </p>
          ) : null}

          {stall ? (
            // D-16: rasta raqami DB kontenti — tarjima qilinmaydi.
            <p className="rounded-sm bg-surface-muted px-3 py-2 font-mono text-sm font-semibold tabular-nums">
              {stall.code}
            </p>
          ) : null}

          <Field
            error={errors.category_id?.message}
            id="stall-category-value"
            label={t("stalls.categoryLabel")}
          >
            <Select
              aria-describedby={
                errors.category_id ? "stall-category-value-error" : undefined
              }
              aria-invalid={errors.category_id ? true : undefined}
              id="stall-category-value"
              {...register("category_id")}
            >
              <option value="" />
              {/* D-16: toifa nomi DB kontenti — tarjima qilinmaydi. */}
              {(categoriesQuery.data?.items ?? []).map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </Select>
          </Field>

          <Field
            error={errors.valid_from?.message}
            id="stall-category-date"
            label={t("stalls.categoryValidFrom")}
          >
            <Input
              aria-describedby={
                errors.valid_from ? "stall-category-date-error" : undefined
              }
              aria-invalid={errors.valid_from ? true : undefined}
              id="stall-category-date"
              min={minValidFrom}
              type="date"
              {...register("valid_from")}
            />
          </Field>

          <Dialog.Footer>
            {/*
             * ⛔ KODBAZA QOIDASI: submit tugmasi FAQAT yuborish jarayoni
             *   davomida yopiladi. Tanlanmagan toifa — tugmaning holati
             *   emas, VALIDATSIYA XABARI: yopiq tugma nima yetishmayotganini
             *   aytmaydi va foydalanuvchi uchun «saqlandi» dan
             *   farqlanmaydi. Mexanik darvoza: `scripts/submit-gate.test.mjs`.
             */}
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
