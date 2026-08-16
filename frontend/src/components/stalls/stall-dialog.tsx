"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslations } from "next-intl";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { STALL_STATUSES } from "@/lib/api-types";
import type { StallStatusValue } from "@/lib/api-types";
import { marketErrorMessageKey } from "@/lib/market-errors";
import {
  useCategoriesQuery,
  useCreateStall,
  useStallQuery,
  useUpdateStall,
  useZonesQuery,
} from "@/lib/market-queries";

/*
 * =============================================================================
 * Rasta yaratish va tahrirlash — BITTA komponent, ikki rejim.
 *
 * NEGA MODAL, inline tahrir EMAS (UI-SPEC §8.4), uchta sabab:
 *   1. AUDIT CHEGARASI — har o'zgarish `fn_audit_row()` bilan yoziladi
 *      (D-10). Inline `onBlur` saqlash ikkilanish paytida tasodifiy audit
 *      yozuvlari hosil qilardi; aniq "Saqlash" tugmasi niyat chegarasini
 *      beradi.
 *   2. RAD ETILADIGAN O'ZGARISH — rasta raqamini tahrirlashni DB rad
 *      etishi mumkin (D-02, `stall_code_retired`). Inline maydonda 409
 *      tushuntirishiga joy yo'q; modalda `role="alert"` bloki bor.
 *   3. BIR NECHA MAYDON BIRGA — raqam + zona + holat bitta tranzaksiya.
 *
 * ⚠ IKKI REJIMNING FARQI — `category_id` (D-04):
 *   `create` -> maydon BOR va MAJBURIY, lekin u `POST /stalls` TANASINING
 *               bir qismi sifatida BITTA chaqiruvda ketadi;
 *   `edit`   -> maydon YO'Q. Mavjud rastaning toifasi SANADAN kuchga kiradi
 *               va uni oddiy tahrir bilan almashtirish o'tmishdagi patta
 *               hisobini qayta yozardi. Uning yagona yo'li —
 *               `stall-category-dialog.tsx`.
 *
 * ⚠ YARATISH FORMASIDA `valid_from` MAYDONI YO'Q. Boshlang'ich toifa
 * davrining sanasini SERVER `market_profile.operating_since` dan qo'yadi va
 * klient uni tanlay olmaydi. Maydon qo'yilganda u so'rov tanasida joy
 * topmasdi — ya'ni foydalanuvchiga hech qanday ta'sir ko'rsatmaydigan
 * "o'lik" boshqaruv bo'lardi.
 * =============================================================================
 */

export type StallDialogMode = "create" | "edit";

type StallFormValues = {
  code: string;
  zone_id: string;
  category_id: string;
  status: StallStatusValue;
  note: string;
};

const EMPTY_VALUES: StallFormValues = {
  code: "",
  zone_id: "",
  category_id: "",
  status: "active",
  note: "",
};

export function StallDialog({
  mode,
  onOpenChange,
  open,
  stallId,
}: {
  mode: StallDialogMode;
  onOpenChange: (open: boolean) => void;
  open: boolean;
  /**
   * `mode="edit"` da majburiy; `create` da `null`.
   *
   * ATAYIN faqat ID: forma qiymatlari `GET /stalls/{id}` dan urug'lanadi,
   * ya'ni dialogni ro'yxat qatoridan ham, rasta kartasidan ham bir xil
   * chaqirish mumkin.
   */
  stallId: string | null;
}) {
  const t = useTranslations();
  const tStatus = useTranslations("stalls.status");
  const [formError, setFormError] = useState<string | null>(null);
  const errorRef = useRef<HTMLParagraphElement>(null);

  const zonesQuery = useZonesQuery({ enabled: open });
  const categoriesQuery = useCategoriesQuery({
    enabled: open && mode === "create",
  });

  /*
   * ⚠ `note` RO'YXAT qatorida YO'Q — u faqat `GET /stalls/{id}` javobida
   * keladi (02-08 kontrakti). Formani ro'yxatdagi qator bilan urug'lantirish
   * izohni bo'sh ko'rsatardi va SAQLASH uni JIMGINA o'chirib yuborardi.
   * Shuning uchun tahrir rejimi batafsil javobni kutadi.
   */
  const isEdit = mode === "edit";
  const detailQuery = useStallQuery(isEdit && open ? stallId : null);
  const detail = detailQuery.data;

  const createStall = useCreateStall();
  const updateStall = useUpdateStall();

  const schema = useMemo(
    () =>
      z.object({
        code: z.string().trim().min(1, { error: t("errors.required") }),
        zone_id: z.string().min(1, { error: t("errors.required") }),
        // Yaratishda majburiy, tahrirlashda maydon umuman render
        // qilinmaydi — shuning uchun cheklov ham rejimga bog'liq.
        category_id:
          mode === "create"
            ? z.string().min(1, { error: t("errors.required") })
            : z.string(),
        status: z.enum(STALL_STATUSES),
        note: z.string(),
      }),
    [mode, t],
  );

  const {
    formState: { errors, isSubmitting },
    handleSubmit,
    register,
    reset,
  } = useForm<StallFormValues>({
    resolver: zodResolver(schema),
    defaultValues: EMPTY_VALUES,
  });

  /*
   * Forma HAR OCHILISHDA bir marta urug'lanadi.
   *
   * `seededFor` ref MAJBURIY: fon refetch'i (masalan oynaga qaytish)
   * `detail` ni yangilaydi va shartsiz `reset` foydalanuvchi terib turgan
   * matnni jimgina o'chirib yuborardi.
   */
  const seededFor = useRef<string | null>(null);

  useEffect(() => {
    if (!open) {
      seededFor.current = null;
      return;
    }

    if (mode === "create") {
      if (seededFor.current === "create") return;
      seededFor.current = "create";
      reset(EMPTY_VALUES);
      return;
    }

    if (!detail || seededFor.current === detail.id) return;
    seededFor.current = detail.id;
    reset({
      code: detail.code,
      zone_id: detail.zone_id,
      category_id: "",
      status: detail.status,
      note: detail.note ?? "",
    });
  }, [detail, mode, open, reset]);

  /*
   * Server xatosi dialog YOPILGANDA tozalanadi, urug'lantirish effektida
   * EMAS: effekt ichidagi sinxron `setState` kaskadli render hosil qiladi
   * (`react-hooks/set-state-in-effect`).
   */
  function handleOpenChange(next: boolean) {
    if (!next) setFormError(null);
    onOpenChange(next);
  }

  // Server xatosi kelganda fokus AYNAN xato blokiga ko'chadi (§6.8) — aks
  // holda klaviatura foydalanuvchisi xabarni umuman topa olmaydi.
  useEffect(() => {
    if (formError !== null) errorRef.current?.focus();
  }, [formError]);

  async function onSubmit(values: StallFormValues) {
    setFormError(null);
    const note = values.note.trim() === "" ? null : values.note.trim();

    try {
      if (mode === "create") {
        // BITTA chaqiruv: `category_id` shu tananing bir qismi (02-08
        // shartnomasi). Ikkinchi so'rov yaratish oqimida QILINMAYDI.
        await createStall.mutateAsync({
          code: values.code.trim(),
          zone_id: values.zone_id,
          category_id: values.category_id,
          status: values.status,
          note,
        });
      } else if (stallId) {
        await updateStall.mutateAsync({
          id: stallId,
          code: values.code.trim(),
          zone_id: values.zone_id,
          status: values.status,
          note,
        });
      }
      handleOpenChange(false);
    } catch (error) {
      setFormError(t(marketErrorMessageKey(error)));
    }
  }

  /*
   * ⛔⛔ TAHRIR REJIMINING UCH HOLATI — UCH MUSTAQIL SHOX, VA TARTIB MUHIM.
   *
   *     Ilgari holat UMUMAN yo'q edi: `detailQuery` faqat `.data` sifatida
   *     o'qilardi va sekin yoki yiqilgan so'rovda admin BO'SH FORMA +
   *     jimgina o'chirilgan «Saqlash» ni ko'rardi — signal yo'q, sabab
   *     yo'q, qayta urinish yo'li yo'q. Nosozlik uchun javobgarlik
   *     NOTO'G'RI ODAMGA yozilardi (TEST-REPORT 2026-08-14, Topilma №6
   *     ning aynan sinfi; `schedule-dialog.tsx` va
   *     `charge-detail-dialog.tsx` bu naqshni allaqachon o'rnatgan).
   *
   *     `renderBody()` KOMPONENT EMAS — ichida hook yo'q. Shuning uchun
   *     barcha hooklar (`useForm`, `useEffect`, `useRef`) komponent
   *     tepasida, SHARTSIZ chaqirilgan holda qoladi va bu
   *     `schedule-card.tsx:116-158` dagi erta-qaytish uslubining dialog
   *     ICHIDAGI to'g'ridan-to'g'ri tarjimasi.
   *
   * ⛔ `isEdit &&` PREFIKSI IKKALA GUARDDA HAM MAJBURIY. `useStallQuery(null)`
   *    `enabled: false` bilan ishlaydi va TanStack bunday so'rovni ABADIY
   *    `isPending: true` deb ushlab turadi — prefikssiz guard `create`
   *    rejimini mangu skeletonga qamab, rasta qo'shish yo'lini butunlay
   *    yopardi. Regressiya `stall-dialog.test.tsx` ning `create`
   *    nazoratida qulflangan.
   */
  function renderBody(): ReactNode {
    if (isEdit && detailQuery.isPending) {
      return (
        <div aria-busy="true" role="status">
          <span className="sr-only">{t("common.loading")}</span>
          <Skeleton className="h-64" />
        </div>
      );
    }

    if (isEdit && detailQuery.isError) {
      return (
        <div
          className="flex flex-col items-start gap-3 rounded-md bg-danger/10 p-4 text-danger-text"
          role="alert"
        >
          <p className="text-sm font-semibold">{t("errors.loadFailedTitle")}</p>
          {/*
           * ⛔ XOM XATO MATNI KO'RSATILMAYDI (T-02-99): `error.message` ham,
           *    server `detail` i ham o'qilmaydi. Tarjima qilingan jumla
           *    NIMA QILISH kerakligini aytadi; xom matn esa faqat
           *    qo'rqitardi va hech qanday yo'l ko'rsatmasdi.
           */}
          <p className="text-sm">{t("errors.loadFailedBody")}</p>
          <Button
            onClick={() => void detailQuery.refetch()}
            size="sm"
            variant="secondary"
          >
            {t("common.retry")}
          </Button>
        </div>
      );
    }

    return (
      <form
        className="flex flex-col gap-4"
        noValidate
        onSubmit={handleSubmit(onSubmit)}
      >
        {/*
         * Server xatosi forma TEPASIDA (§6.8). `tabIndex={-1}` — blok
         * fokus ola oladigan bo'lsin, lekin Tab tartibiga kirmasin.
         */}
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

        <Field
          error={errors.code?.message}
          id="stall-form-code"
          label={t("stalls.codeLabel")}
        >
          <Input
            aria-describedby={errors.code ? "stall-form-code-error" : undefined}
            aria-invalid={errors.code ? true : undefined}
            autoComplete="off"
            id="stall-form-code"
            inputMode="numeric"
            {...register("code")}
          />
        </Field>

        <Field
          error={errors.zone_id?.message}
          id="stall-form-zone"
          label={t("stalls.zoneLabel")}
        >
          <Select
            aria-describedby={
              errors.zone_id ? "stall-form-zone-error" : undefined
            }
            aria-invalid={errors.zone_id ? true : undefined}
            id="stall-form-zone"
            {...register("zone_id")}
          >
            <option value="" />
            {/* D-16: zona nomi DB kontenti — tarjima qilinmaydi. */}
            {(zonesQuery.data?.items ?? []).map((zone) => (
              <option key={zone.id} value={zone.id}>
                {zone.name}
              </option>
            ))}
          </Select>
        </Field>

        {/*
         * TOIFA — FAQAT yaratish rejimida (D-04). Tahrir rejimida bu
         * maydon ATAYIN yo'q: mavjud rastaning toifasi sanadan kuchga
         * kiradi va uni almashtirishning yagona yo'li — alohida dialog.
         */}
        {mode === "create" ? (
          <Field
            error={errors.category_id?.message}
            id="stall-form-category"
            label={t("stalls.categoryLabel")}
          >
            <Select
              aria-describedby={
                errors.category_id ? "stall-form-category-error" : undefined
              }
              aria-invalid={errors.category_id ? true : undefined}
              id="stall-form-category"
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
        ) : null}

        <Field id="stall-form-status" label={t("stalls.statusLabel")}>
          <Select id="stall-form-status" {...register("status")}>
            {STALL_STATUSES.map((status) => (
              <option key={status} value={status}>
                {tStatus(status)}
              </option>
            ))}
          </Select>
        </Field>

        <Field id="stall-form-note" label={t("stalls.noteLabel")}>
          <Input autoComplete="off" id="stall-form-note" {...register("note")} />
        </Field>

        <Dialog.Footer>
          {/*
           * ⛔ KODBAZA QOIDASI: submit tugmasi FAQAT yuborish jarayoni
           *   davomida yopiladi. Domen sharti (maydon bo'sh, ro'yxat
           *   bo'sh, tanlov yo'q) tugmaga EMAS, validatsiya xabariga
           *   aylanadi — o'chirilgan tugma NIMA yetishmayotganini
           *   AYTMAYDI. Qoidaning mexanik darvozasi:
           *   `scripts/submit-gate.test.mjs`.
           *
           * ⚠ ILGARIGI IKKINCHI SHART («batafsil javob kelmaguncha yopiq»)
           *   OLIB TASHLANDI va u endi MANTIQAN ERISHIB BO'LMAS: forma
           *   javob kelmaguncha UMUMAN chizilmaydi (yuqoridagi guard
           *   zanjiri), ya'ni urug'lanmagan forma bilan saqlash holatining
           *   o'zi yo'q. Jim-disabled tugma o'rniga KO'RINADIGAN holat —
           *   skeleton yoki sabab + qayta urinish [quick 260816-5yz].
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
    );
  }

  return (
    <Dialog.Root onOpenChange={handleOpenChange} open={open}>
      <Dialog.Content
        description={
          mode === "create" ? t("stalls.createHint") : t("stalls.editHint")
        }
        size="lg"
        title={mode === "create" ? t("stalls.create") : t("stalls.edit")}
      >
        {renderBody()}
      </Dialog.Content>
    </Dialog.Root>
  );
}
