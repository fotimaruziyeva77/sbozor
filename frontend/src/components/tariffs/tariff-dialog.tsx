"use client";

import { useEffect, useMemo, useState } from "react";
import { Banknote } from "lucide-react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useFormatter, useLocale, useNow, useTimeZone, useTranslations } from "next-intl";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import type { CategoryItem, TariffItem } from "@/lib/api-types";
import { formatBusinessDay } from "@/lib/format-day";
import { marketErrorMessageKey } from "@/lib/market-errors";
import { useCreateTariff, useUpdateTariff } from "@/lib/market-queries";

/*
 * =============================================================================
 * Tarif formasi (D-06/D-07).
 *
 * ⚠⚠ SANA CHEGARASI SERVERDAN KELADI — QAT'IY QOIDA (T-02-119a) ⚠⚠
 *
 * `valid_from` maydonining `min` atributi FAQAT `GET /tariffs` javobidagi
 * `min_valid_from` dan olinadi va u bu yerda HECH QANDAY hisob-kitobga
 * uchramaydi: `??` yoki `||` bilan zaxira qiymat berilmaydi, ertangi kun
 * lokal hisoblanmaydi.
 *
 * NEGA BU SHUNCHALIK MUHIM: server ikki tarmoqni biladi —
 *   faol bozorda    `min_valid_from` = ertangi kun;
 *   QORALAMA bozorda `min_valid_from` = `market_profile.operating_since`
 *                     va u O'TMISHDAGI sana bo'lishi mumkin.
 * Klient keyingi kunni O'ZI hisoblasa, ustaning 4-qadami (boshlang'ich narx)
 * UI orqali UMUMAN bajarilmas bo'lardi: server 201 qaytaradigan sanani
 * maydon kiritishga qo'ymasdi, bozor esa hech qachon faollashmasdi.
 *
 * ⚠ Bu taqiq MEXANIK grep darvozasi bilan qulflangan va darvoza sana
 * hisobining atamalarini (jumladan o'zbekcha "keyingi kun" ning bir
 * so'zli shakli) qidiradi — shuning uchun ular bu izohda ham literal
 * yozilmaydi (02-08 da o'rnatilgan konvensiya: darvoza o'z hujjatiga
 * qarshi turmasin).
 *
 * YO'NALISH MUHIM: `min` — QULAYLIK, darvoza SERVERDA. Klient serverdan
 * QATTIQROQ bo'lmasligi kerak. Teskarisi (klient ruxsat berdi, server rad
 * etdi) esa MAQBUL va u xato xabari bilan hal qilinadi — qoralama bozorda
 * `operating_since` bilan bugun orasidagi sanalar aynan shunday: `min` dan
 * katta, lekin server 422 beradi.
 *
 * Shu sababli `valid_from` uchun zod `refine` i ATAYIN YOZILMAGAN. "Sana
 * kelajakda bo'lsin" tekshiruvini bu yerga qo'yish yuqoridagi taqiqning
 * boshqa shakldagi takrori bo'lardi.
 *
 * BUGUNGI SANA NIMA UCHUN KERAK: FAQAT ikki PERMISSIV qaror uchun —
 * maydonni oldindan to'ldirish va tushuntiruvchi izohni ko'rsatish. Ular
 * hech qachon hech qanday sanani TAQIQLAY olmaydi. Qiymat `useNow()` va
 * `useTimeZone()` dan olinadi, qo'lda emas: vaqt mintaqasi `i18n/request.ts`
 * da BITTA joyda (`Asia/Tashkent`) e'lon qilingan va uni ikkinchi marta
 * e'lon qilish bir kun hisobni noto'g'ri biznes-kunga bog'lardi (FOUND-05).
 * =============================================================================
 */

type TariffFormValues = {
  amountSoum: string;
  categoryId: string;
  validFrom: string;
};

/**
 * `Date` -> `YYYY-MM-DD` (ko'rsatish mintaqasida).
 *
 * `en-CA` ATAYIN: uning qisqa sana formati ISO-8601 bilan bir xil, ya'ni
 * natijani `min_valid_from` (server bergan ISO satr) bilan LEKSIK
 * solishtirish mumkin. Foydalanuvchiga ko'rinadigan matn bu emas — u
 * `useFormatter()` orqali chiqadi.
 *
 * Mintaqa noma'lum bo'lsa `null` qaytadi va CHAQIRUVCHI qulaylikdan voz
 * kechadi. Brauzerning O'Z mintaqasiga tushib qolish TAQIQ: foydalanuvchi
 * boshqa mintaqada bo'lsa "bugun" bir kunga siljib, izoh noto'g'ri
 * holatda chiqardi (FOUND-05 sinfi).
 */
function isoDateIn(timeZone: string | undefined, value: Date): string | null {
  if (timeZone === undefined) return null;
  return new Intl.DateTimeFormat("en-CA", {
    day: "2-digit",
    month: "2-digit",
    timeZone,
    year: "numeric",
  }).format(value);
}

export function TariffDialog({
  categories,
  minValidFrom,
  onOpenChange,
  open,
  tariff,
  presetCategoryId,
}: {
  categories: readonly CategoryItem[];
  /**
   * `GET /tariffs` javobining `min_valid_from` maydoni — O'ZGARTIRILMAGAN
   * holda. Chaqiruvchi uni hisoblab bermaydi va u ixtiyoriy emas.
   */
  minValidFrom: string;
  onOpenChange: (open: boolean) => void;
  open: boolean;
  /** `null` — yangi qator; aks holda KELAJAKDAGI qatorni tahrirlash. */
  tariff: TariffItem | null;
  /** 2026-08-26 №2: toifa kartasidagi «Narx» tugmasi shu toifani oldindan tanlaydi. */
  presetCategoryId?: string | null;
}) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();
  const now = useNow();
  const timeZone = useTimeZone();

  const createTariff = useCreateTariff();
  const updateTariff = useUpdateTariff();
  const [formError, setFormError] = useState<string | null>(null);

  const isEdit = tariff !== null;
  const today = isoDateIn(timeZone, now);

  /*
   * Server ruxsat bergan eng erta sana BUGUNDAN OLDIN bo'lsa, bozor
   * qoralama va undan boshlang'ich narx kutilmoqda (D-13 ning 4-qadami).
   * Shunda maydon o'sha sana bilan to'ldiriladi va yoniga sabab yoziladi —
   * aks holda admin "nega o'tmishdagi sana?" deb o'ylab, uni kelajakka
   * surib yuborardi va bozor ishlay boshlagan kunlar tarifsiz qolardi.
   *
   * `today === null` (mintaqa noma'lum) — QULAYLIKDAN voz kechiladi:
   * maydon to'ldirilmaydi va izoh chiqmaydi. `min` esa O'ZGARMAYDI, ya'ni
   * o'tmishdagi sanani QO'LDA kiritish yo'li baribir ochiq qoladi. Yo'nalish
   * muhim: noaniqlikda hech narsa TAQIQLANMAYDI.
   */
  const isInitialTariff = today !== null && minValidFrom < today;

  const defaults = useMemo<TariffFormValues>(
    () => ({
      amountSoum: "",
      categoryId: presetCategoryId ?? categories[0]?.id ?? "",
      // Oldindan to'ldirish PERMISSIV: server ALLAQACHON ruxsat bergan
      // qiymat qo'yiladi, hech narsa taqiqlanmaydi.
      validFrom: isInitialTariff ? minValidFrom : "",
    }),
    [categories, isInitialTariff, minValidFrom, presetCategoryId],
  );

  const schema = useMemo(
    () =>
      z.object({
        // Pul BUTUN so'm (spec §6): `float` kiritilsa forma ichida
        // to'xtaydi, 422 kutilmaydi.
        amountSoum: z
          .string()
          .min(1, { error: t("errors.required") })
          .refine((value) => /^\d+$/u.test(value) && Number(value) > 0, {
            error: t("tariffs.amountInvalid"),
          }),
        categoryId: z.string().min(1, { error: t("tariffs.categoryRequired") }),
        // `min(1)` — maydon TO'LDIRILGAN bo'lsin, xolos. Sananing O'ZI
        // haqidagi qoida serverda (yuqoridagi izohga qarang).
        validFrom: z.string().min(1, { error: t("errors.required") }),
      }),
    [t],
  );

  const {
    formState: { errors, isSubmitting },
    handleSubmit,
    register,
    reset,
  } = useForm<TariffFormValues>({
    resolver: zodResolver(schema),
    defaultValues: defaults,
  });

  useEffect(() => {
    reset(
      tariff === null
        ? defaults
        : {
            amountSoum: String(tariff.amount_soum),
            categoryId: tariff.category_id,
            validFrom: tariff.valid_from,
          },
    );
  }, [defaults, reset, tariff]);

  function handleOpenChange(next: boolean) {
    if (!next) {
      reset(defaults);
      setFormError(null);
    }
    onOpenChange(next);
  }

  async function onSubmit(values: TariffFormValues) {
    setFormError(null);
    try {
      if (tariff === null) {
        await createTariff.mutateAsync({
          amount_soum: Number(values.amountSoum),
          category_id: values.categoryId,
          valid_from: values.validFrom,
        });
      } else {
        /*
         * `category_id` PATCH tanasida YO'Q (D-05): tarif kaliti aynan
         * `(category_id, valid_from)` va toifani almashtirish qatorni
         * BOSHQA narx tarixiga ko'chirardi.
         */
        await updateTariff.mutateAsync({
          amount_soum: Number(values.amountSoum),
          id: tariff.id,
          valid_from: values.validFrom,
        });
      }
      handleOpenChange(false);
    } catch (error) {
      /*
       * Serverning uchta domen javobi shu yerda ko'rinadi va ularning
       * matni `market-errors.ts` da:
       *   409 `tariff_already_set_for_date`  -> `tariffs.dateTaken`
       *   422 `valid_from_must_be_future`    -> `tariffs.mustBeFuture`
       *   403 `tariff_past_locked`           -> `tariffs.pastLocked`
       * Oxirgisi — o'tmish qulfi: u DB triggeridan keladi va UI tugmani
       * yashirgani bilan YO'QOLMAYDI.
       */
      setFormError(t(marketErrorMessageKey(error)));
    }
  }

  return (
    <Dialog.Root onOpenChange={handleOpenChange} open={open}>
      <Dialog.Content icon={Banknote}
        description={isEdit ? t("tariffs.editHint") : t("tariffs.createHint")}
        size="lg"
        title={isEdit ? t("tariffs.editTitle") : t("tariffs.createTitle")}
      >
        <form
          className="flex flex-col gap-4"
          noValidate
          onSubmit={handleSubmit(onSubmit)}
        >
          <Field
            error={errors.categoryId?.message}
            id="tariff-category"
            label={t("tariffs.categoryLabel")}
          >
            <Select
              aria-describedby={
                errors.categoryId ? "tariff-category-error" : undefined
              }
              aria-invalid={errors.categoryId ? true : undefined}
              /*
               * Tahrirlashda toifa QULFLANGAN — `PATCH /tariffs/{id}` uni
               * qabul qilmaydi (D-05). Ochiq qoldirish foydalanuvchiga
               * bajarilmaydigan tanlov ko'rsatardi.
               */
              disabled={isEdit}
              id="tariff-category"
              {...register("categoryId")}
            >
              {categories.length === 0 ? (
                <option value="">{t("tariffs.noCategories")}</option>
              ) : null}
              {/* D-16: toifa nomi DB kontenti — tarjima qilinmaydi. */}
              {categories.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </Select>
          </Field>

          <Field
            error={errors.amountSoum?.message}
            hint={t("tariffs.amountUnit")}
            id="tariff-amount"
            label={t("tariffs.amountLabel")}
          >
            <Input
              aria-describedby={
                errors.amountSoum
                  ? "tariff-amount-error tariff-amount-hint"
                  : "tariff-amount-hint"
              }
              aria-invalid={errors.amountSoum ? true : undefined}
              autoComplete="off"
              className="tabular-nums"
              id="tariff-amount"
              inputMode="numeric"
              {...register("amountSoum")}
            />
          </Field>

          <Field
            error={errors.validFrom?.message}
            hint={
              isInitialTariff
                ? t("tariffs.initialHint", {
                    date: formatBusinessDay(format, minValidFrom, locale),
                  })
                : undefined
            }
            id="tariff-valid-from"
            label={t("tariffs.validFromLabel")}
          >
            <Input
              aria-describedby={
                [
                  errors.validFrom ? "tariff-valid-from-error" : null,
                  isInitialTariff ? "tariff-valid-from-hint" : null,
                ]
                  .filter((id) => id !== null)
                  .join(" ") || undefined
              }
              aria-invalid={errors.validFrom ? true : undefined}
              id="tariff-valid-from"
              /*
               * ⚠ SERVERDAN. Bu qator o'zgartirilmaydi: hech qanday
               * hisob, hech qanday zaxira qiymat.
               */
              min={minValidFrom}
              type="date"
              {...register("validFrom")}
            />
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
            {/*
             * ⛔ KODBAZA QOIDASI: submit tugmasi FAQAT yuborish jarayoni
             *   davomida yopiladi. Bo'sh toifa ro'yxati tugmani YOPMAYDI —
             *   u zodning `tariffs.categoryRequired` xabariga aylanadi.
             *   Ilgari yopiq tugma yonidagi `tariffs.noCategories`
             *   placeholder'iga ZID turardi: matn nima qilish kerakligini
             *   aytardi, tugma esa sababsiz bosilmasdi. Mexanik darvoza:
             *   `scripts/submit-gate.test.mjs`.
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
