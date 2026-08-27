"use client";

import { useId, useState } from "react";
import { Plus, Scale, Trash2 } from "lucide-react";
import { useFormatter, useLocale, useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { formatBusinessDay } from "@/lib/format-day";
import { formatAmount } from "@/lib/format-number";
import { marketErrorMessageKey } from "@/lib/market-errors";
import {
  useCreateServiceFee,
  useDeleteServiceFee,
  useServiceFees,
  type ServiceFeeItem,
} from "@/lib/service-fee-queries";

/*
 * =============================================================================
 * MAJBURIY XIZMAT HAQI (tarozi) — TARIFLAR SAHIFASIDAGI KARTA (0027).
 *
 * Foydalanuvchi talabi: «Ta'riflarda qushiladi u uzgarsa u yerda
 * ko'rinsin».
 *
 * -----------------------------------------------------------------------
 * ⛔ TARIF RO'YXATIDAN YUQORIDA TURADI VA BU ATAYIN.
 *
 *   Xizmat haqi HAR toifaga tegadi, ya'ni u tarif jadvalining ustidagi
 *   qatlam. Uni pastga qo'yish «bu ham bitta tarif turi» degan yolg'on
 *   model berardi — holbuki u bozor darajasidagi ALOHIDA narx.
 *
 * -----------------------------------------------------------------------
 * ⛔ «HOZIRGI QIYMAT» SERVERDAN (`current_amount_soum`), RO'YXATNING
 *    BIRINCHI QATORIDAN EMAS.
 *
 *   Tartib `valid_from DESC`, ya'ni birinchi qator KELAJAKDAGI narx
 *   bo'lishi mumkin. Uni «hozirgi» deb ko'rsatish adminni bugun amalda
 *   BOSHQA summa turganidan bexabar qoldirardi.
 *
 * -----------------------------------------------------------------------
 * ⚠ `UPDATE` YO'Q (D-06): mavjud qator TAHRIRLANMAYDI, yangi sanadan
 *   YANGI qator qo'shiladi. Kelajakdagi qatorni o'chirish mumkin,
 *   o'tgani esa DB triggeri bilan qulflangan (403 `service_fee_past_
 *   locked`) — shuning uchun bu kartada «Tahrirlash» tugmasi UMUMAN
 *   yo'q, u mavjud bo'lmagan yo'lni va'da qilardi.
 * =============================================================================
 */

export type ServiceFeeCardProps = {
  /** `TARIFF_MANAGE` — yo'q bo'lsa forma UMUMAN chizilmaydi (huquq ko'zgusi). */
  canManage: boolean;
};

export function ServiceFeeCard({ canManage }: ServiceFeeCardProps) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();

  const fees = useServiceFees();
  const create = useCreateServiceFee();
  const remove = useDeleteServiceFee();

  const [open, setOpen] = useState(false);
  const [label, setLabel] = useState("");
  const [amount, setAmount] = useState("");
  const [validFrom, setValidFrom] = useState("");
  /*
   * ⛔⛔ KO'RINADIGAN VALIDATSIYA — O'CHIRILGAN TUGMA EMAS.
   *
   *   `submit-gate.test.mjs` domen shartini `disabled` ga qo'yishni
   *   TAQIQLAYDI va sabab yozilgan: «o'chirilgan tugma NIMA
   *   yetishmayotganini AYTMAYDI». Admin bo'sh nom bilan tugmani
   *   bosolmay, nega bosolmayotganini bilmay qolardi.
   *
   *   Shuning uchun tugma HAR DOIM bosiladi (faqat `isPending` da
   *   yopiladi) va yetishmayotgan maydon MATN bilan aytiladi.
   */
  const [errors, setErrors] = useState<{
    label?: string;
    amount?: string;
    validFrom?: string;
  }>({});

  const labelId = useId();
  const amountId = useId();
  const dateId = useId();

  const data = fees.data ?? null;
  const money = (value: number) =>
    `${formatAmount(format, value, locale)} ${t("tariffs.amountUnit")}`;

  const submit = () => {
    const trimmed = label.trim();
    const parsed = Number(amount);
    const next: typeof errors = {};

    if (trimmed === "") next.label = t("tariffs.feeLabelRequired");
    /*
     * ⛔ `>= 0` (`> 0` EMAS): nol QONUNIY qiymat — «bu bozorda xizmat
     *    haqi olinmaydi». Shart serverdagi `Field(ge=0)` bilan AYNAN
     *    bir xil, ya'ni klient serverdan qat'iyroq bo'lib qolmaydi.
     */
    if (amount === "" || !Number.isInteger(parsed) || parsed < 0) {
      next.amount = t("tariffs.feeAmountInvalid");
    }
    if (validFrom === "") next.validFrom = t("tariffs.feeDateRequired");

    setErrors(next);
    if (Object.keys(next).length > 0) return;

    create.mutate(
      { amount_soum: parsed, label: trimmed, valid_from: validFrom },
      {
        onSuccess: () => {
          setOpen(false);
          setLabel("");
          setAmount("");
          setValidFrom("");
          setErrors({});
        },
      },
    );
  };

  return (
    <Card>
      <CardContent className="flex flex-col gap-4 pt-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            {/*
             * ⛔ IKONKA 24px (`size-6`) — 16px EMAS. Foydalanuvchi
             *    topilmasi: «iconlar juda kichin». Bo'lim boshidagi
             *    ikonka mavzuni bir qarashda aytadi va u matn bilan
             *    bir o'lchamda bo'lsa umuman ko'rinmaydi.
             */}
            <Scale
              aria-hidden="true"
              className="mt-0.5 size-6 shrink-0 text-text-muted"
            />
            <div className="flex flex-col gap-1">
              <h2 className="text-lg leading-snug font-semibold tracking-tight">
                {t("tariffs.feeSectionTitle")}
              </h2>
              <p className="text-sm text-text-muted">
                {t("tariffs.feeSectionHint")}
              </p>
            </div>
          </div>

          {canManage ? (
            <Button
              onClick={() => setOpen((value) => !value)}
              size="sm"
              variant="secondary"
            >
              <Plus aria-hidden="true" className="size-4" />
              {t("tariffs.feeAdd")}
            </Button>
          ) : null}
        </div>

        {/* --- Hozirgi qiymat -------------------------------------------- */}
        {fees.isPending ? (
          <Skeleton className="h-11 w-48" />
        ) : (
          <div className="flex flex-col gap-1">
            <p className="text-xs text-text-muted">{t("tariffs.feeCurrent")}</p>
            {data === null || data.current_amount_soum === null ? (
              /*
               * ⛔ «BELGILANMAGAN» — NOL EMAS. Ikkalasi boshqa holat:
               *    nol «qaror qabul qilindi, olinmaydi» degani, yo'qlik
               *    esa «hali hech kim qo'ymagan». Ularni aralashtirish
               *    adminni «men qo'ygandim-ku» degan savolga qoldirardi.
               */
              <>
                <p className="text-lg font-semibold text-text-muted">
                  {t("tariffs.feeNone")}
                </p>
                <p className="text-sm text-text-muted">
                  {t("tariffs.feeNoneHint")}
                </p>
              </>
            ) : (
              <p className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                <span className="font-mono text-2xl font-semibold tabular-nums text-text">
                  {money(data.current_amount_soum)}
                </span>
                <span className="text-sm text-text-muted">
                  {data.current_label}
                </span>
              </p>
            )}
          </div>
        )}

        {/* --- Yangi qiymat formasi -------------------------------------- */}
        {canManage && open ? (
          <form
            className="flex flex-col gap-3 rounded-md border border-border bg-surface-muted p-4"
            onSubmit={(event) => {
              event.preventDefault();
              submit();
            }}
          >
            <p className="text-sm font-semibold text-text">
              {t("tariffs.feeAddTitle")}
            </p>

            <Field
              error={errors.label}
              hint={t("tariffs.feeLabelHint")}
              id={labelId}
              label={t("tariffs.feeLabelField")}
            >
              <Input
                autoComplete="off"
                id={labelId}
                onChange={(event) => setLabel(event.target.value)}
                placeholder={t("tariffs.feeLabelPlaceholder")}
                value={label}
              />
            </Field>

            <Field
              error={errors.amount}
              hint={t("tariffs.feeZeroHint")}
              id={amountId}
              label={t("tariffs.feeAmountField")}
            >
              <Input
                autoComplete="off"
                className="tabular-nums"
                id={amountId}
                inputMode="numeric"
                onChange={(event) => setAmount(event.target.value)}
                value={amount}
              />
            </Field>

            <Field
              error={errors.validFrom}
              hint={
                data === null
                  ? undefined
                  : formatBusinessDay(format, data.min_valid_from, locale)
              }
              id={dateId}
              label={t("tariffs.validFromLabel")}
            >
              <Input
                id={dateId}
                min={data?.min_valid_from}
                onChange={(event) => setValidFrom(event.target.value)}
                type="date"
                value={validFrom}
              />
            </Field>

            {/*
             * ⛔ XATO REYESTRDAN (`marketErrorMessageKey`), xom `detail`
             *    EMAS: noma'lum kod `errors.generic` ga tushadi va SQL
             *    matni foydalanuvchiga HECH QACHON ko'rsatilmaydi
             *    (T-02-99).
             */}
            {create.isError ? (
              <p className="text-sm text-danger-text" role="alert">
                {t(marketErrorMessageKey(create.error))}
              </p>
            ) : null}

            <div className="flex gap-2">
              {/*
               * ⛔ `disabled` DA FAQAT `isPending` — domen sharti YO'Q
               *    (`submit-gate.test.mjs` ning ruxsat etilgan lug'ati).
               */}
              <Button disabled={create.isPending} type="submit">
                {t("common.save")}
              </Button>
              <Button
                onClick={() => setOpen(false)}
                type="button"
                variant="ghost"
              >
                {t("common.cancel")}
              </Button>
            </div>
          </form>
        ) : null}

        {/* --- Tarix ------------------------------------------------------ */}
        {data !== null && data.items.length > 0 ? (
          <div className="flex flex-col gap-2">
            <h3 className="text-sm font-semibold text-text-muted">
              {t("tariffs.feeHistoryTitle")}
            </h3>
            <ul className="flex flex-col gap-2">
              {data.items.map((item) => (
                <ServiceFeeRow
                  canManage={canManage}
                  isRemoving={remove.isPending}
                  item={item}
                  key={item.id}
                  money={money}
                  onRemove={() => remove.mutate(item.id)}
                />
              ))}
            </ul>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

/* --- Tarix qatori ---------------------------------------------------------- */

function ServiceFeeRow({
  item,
  money,
  canManage,
  isRemoving,
  onRemove,
}: {
  item: ServiceFeeItem;
  money: (value: number) => string;
  canManage: boolean;
  isRemoving: boolean;
  onRemove: () => void;
}) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();

  return (
    <li className="flex min-h-14 flex-wrap items-center justify-between gap-x-4 gap-y-1 rounded-md border border-border bg-surface px-4 py-3">
      <span className="flex flex-col gap-0.5">
        <span className="font-mono text-lg font-semibold tabular-nums text-text">
          {money(item.amount_soum)}
        </span>
        <span className="text-sm text-text-muted">{item.label}</span>
      </span>

      <span className="text-sm tabular-nums text-text-muted">
        {formatBusinessDay(format, item.valid_from, locale)}
        {item.valid_to === null
          ? ""
          : ` — ${formatBusinessDay(format, item.valid_to, locale)}`}
      </span>

      {/*
       * ⛔ O'CHIRISH FAQAT KELAJAKDAGI QATORDA (`is_past === false`).
       *    O'tgani DB triggeri bilan qulflangan va tugmani ko'rsatib
       *    keyin 403 berish — o'lik affordans (KAMCHILIKLAR №F ning
       *    aynan o'sha sinfi).
       */}
      {canManage && !item.is_past ? (
        <Button
          aria-label={t("tariffs.feeDeleteAction")}
          disabled={isRemoving}
          onClick={onRemove}
          size="sm"
          variant="ghost"
        >
          <Trash2 aria-hidden="true" className="size-4" />
        </Button>
      ) : null}
    </li>
  );
}
