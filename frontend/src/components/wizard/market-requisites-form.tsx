"use client";

import { useCallback, useMemo, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslations } from "next-intl";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { WIZARD_SETUP_PATH } from "@/components/wizard/wizard-steps";
import { useRouter } from "@/i18n/navigation";
import { useSelectMarket } from "@/lib/auth-queries";
import { applySession } from "@/lib/auth-store";
import { marketErrorMessageKey } from "@/lib/market-errors";
import { useCreateMarket } from "@/lib/market-queries";

/*
 * =============================================================================
 * Ustaning 1-qadami — rekvizitlar (UI-SPEC §6.5, §6.8, O-02).
 *
 * IKKI BO'LIM (O-02): «Asosiy» ochiq turadi, «Rasmiy rekvizitlar» esa
 * `<details>` ichida. Bu ATAYIN: A1/A2 taxminlari LOW confidence, ya'ni
 * buyurtmachi bilan tasdiqlanganda maydon QO'SHILISHI kutilmoqda va u
 * layoutni buzmasligi kerak. Ochiq ro'yxatga sakkizinchi maydon qo'shilsa
 * birinchi ekran butunlay rekvizitga aylanardi.
 *
 * AVTOMATIK SAQLASH YO'Q [QAROR, §6.5]: bu forma `market_create()` ni
 * chaqiradi va QORALAMA BOZOR tug'diradi. Har terilgan harfda saqlash
 * tashlab ketilgan qoralamalar to'plamini yaratardi — ularning har biri
 * bozor tanlash ekranida ko'rinadi va admin qaysi biri "haqiqiy" ekanini
 * bilmasdi.
 *
 * SANA CHEGARASI YO'Q [A3]: `operating_since` O'TMISHDAGI sana bo'lishi
 * MUMKIN va odatda shunday bo'ladi (mavjud bozor raqamlashtirilyapti).
 * Barcha boshlang'ich tarif va toifa davrlari aynan shu sanadan yoziladi,
 * ya'ni uni "kelajakda bo'lsin" deb cheklash butun tarixni tarifsiz
 * qoldirardi va 6-fazaning kunlik hisobi har kunni anomaliya deb topardi.
 *
 * T-02-125: rekvizit maydonlarida `autoComplete="off"` — bank ma'lumotlari
 * brauzerning avtomatik to'ldirish xotirasida qolmasligi kerak.
 * =============================================================================
 */

/** MVP: bitta mintaqa. Ro'yxat kengaysa `Select` shu massivdan to'ladi. */
const TIMEZONES = ["Asia/Tashkent"] as const;

type RequisitesValues = {
  name: string;
  timezone: string;
  operatingSince: string;
  address: string;
  tin: string;
  bankAccount: string;
  bankMfo: string;
  contactPhone: string;
};

const EMPTY_VALUES: RequisitesValues = {
  name: "",
  timezone: TIMEZONES[0],
  operatingSince: "",
  address: "",
  tin: "",
  bankAccount: "",
  bankMfo: "",
  contactPhone: "",
};

/** `<details>` ichidagi maydonlar — xato bo'lsa bo'lim MAJBURAN ochiladi. */
const OFFICIAL_FIELDS = [
  "address",
  "tin",
  "bankAccount",
  "bankMfo",
  "contactPhone",
] as const;

/** Bo'sh matn serverga `null` bo'lib ketadi — `""` "kiritilgan" degani emas. */
function orNull(value: string): string | null {
  const trimmed = value.trim();
  return trimmed === "" ? null : trimmed;
}

export function MarketRequisitesForm() {
  const t = useTranslations();
  const router = useRouter();

  const createMarket = useCreateMarket();
  const selectMarket = useSelectMarket();

  const [formError, setFormError] = useState<string | null>(null);
  const [officialOpen, setOfficialOpen] = useState(false);

  const schema = useMemo(
    () =>
      z.object({
        name: z
          .string()
          .trim()
          .min(2, { error: t("wizard.nameLength") })
          .max(120, { error: t("wizard.nameLength") }),
        timezone: z.string().min(1, { error: t("errors.required") }),
        operatingSince: z.string().min(1, { error: t("errors.required") }),
        address: z.string().trim().max(300, { error: t("wizard.addressLong") }),
        /*
         * Ixtiyoriy maydonlar: BO'SH satr har doim yaroqli. `.optional()`
         * bu yerda ishlamaydi — `<input>` hech qachon `undefined` bermaydi,
         * u bo'sh SATR beradi.
         */
        tin: z
          .string()
          .trim()
          .refine((value) => value === "" || /^\d{9}$/u.test(value), {
            error: t("wizard.tinInvalid"),
          }),
        bankAccount: z
          .string()
          .trim()
          .max(30, { error: t("wizard.bankAccountLong") }),
        /*
         * ⚠ Server bu maydonni ATAYIN formatlamaydi (A1 buyurtmachi bilan
         * tasdiqlanmagan). Klientdagi besh raqamli qoida — QULAYLIK, darvoza
         * emas: u O'zbekiston MFO standartini aks ettiradi. Agar HAQIQIY
         * rekvizit bu qoidaga urilib rad etilsa, tuzatish shu yerdagi
         * qoidani OLIB TASHLASH bo'ladi — serverga cheklov qo'shish EMAS.
         */
        bankMfo: z
          .string()
          .trim()
          .refine((value) => value === "" || /^\d{5}$/u.test(value), {
            error: t("wizard.bankMfoInvalid"),
          }),
        contactPhone: z
          .string()
          .trim()
          .max(20, { error: t("wizard.contactPhoneLong") }),
      }),
    [t],
  );

  const {
    formState: { errors, isSubmitting },
    handleSubmit,
    register,
  } = useForm<RequisitesValues>({
    resolver: zodResolver(schema),
    defaultValues: EMPTY_VALUES,
  });

  /*
   * Server xatosi paydo bo'lganda fokus AYNAN o'sha blokka ko'chadi (§6.8):
   * aks holda klaviatura foydalanuvchisi forma tepasidagi xabarni umuman
   * topa olmaydi. Callback ref ISHLATILADI — element montaj bo'lgan lahzada
   * chaqiriladi, ya'ni effekt ichida `setState` ham, kechikish ham kerak
   * emas.
   */
  const focusOnMount = useCallback((node: HTMLParagraphElement | null) => {
    node?.focus();
  }, []);

  /*
   * Yashirin maydondagi xato — jimgina yo'qolgan xato. `<details>` yopiq
   * bo'lsa react-hook-form fokusni ko'rinmaydigan `<input>` ga ko'chirardi
   * va foydalanuvchi "nega saqlanmayapti?" deb qolardi. Shart RENDER
   * paytida hisoblanadi, effekt bilan emas.
   */
  const hasOfficialError = OFFICIAL_FIELDS.some(
    (field) => errors[field] !== undefined,
  );

  async function onSubmit(values: RequisitesValues) {
    setFormError(null);
    try {
      const created = await createMarket.mutateAsync({
        name: values.name.trim(),
        timezone: values.timezone,
        operating_since: values.operatingSince,
        address: orNull(values.address),
        tin: orNull(values.tin),
        bank_account: orNull(values.bankAccount),
        bank_mfo: orNull(values.bankMfo),
        contact_phone: orNull(values.contactPhone),
      });

      /*
       * `select-market` MAJBURIY: yangi bozorning identifikatori tokenda
       * (`mid`) bo'lmasa 2-qadamning HAR BIR so'rovi `409
       * market_not_selected` bilan qaytardi (02-11).
       */
      const session = await selectMarket.mutateAsync(created.id);
      applySession({
        accessToken: session.access_token,
        roles: session.roles,
        market: session.market,
      });

      /*
       * Toast YO'Q (§6.5): keyingi qadamga o'tishning O'ZI tasdiq. Toast
       * navigatsiya ustiga qo'shimcha shovqin bo'lardi.
       */
      router.replace(`${WIZARD_SETUP_PATH}?step=2`);
    } catch (error) {
      setFormError(t(marketErrorMessageKey(error)));
    }
  }

  const busy = isSubmitting || createMarket.isPending || selectMarket.isPending;

  return (
    <form
      className="flex max-w-2xl flex-col gap-5"
      noValidate
      onSubmit={handleSubmit(onSubmit)}
    >
      {formError ? (
        <p
          className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
          ref={focusOnMount}
          role="alert"
          tabIndex={-1}
        >
          {formError}
        </p>
      ) : null}

      <section className="flex flex-col gap-4">
        <h2 className="text-lg font-semibold">{t("wizard.sectionBasic")}</h2>

        <Field
          error={errors.name?.message}
          id="market-name"
          label={t("wizard.nameLabel")}
        >
          <Input
            aria-describedby={errors.name ? "market-name-error" : undefined}
            aria-invalid={errors.name ? true : undefined}
            autoComplete="off"
            id="market-name"
            {...register("name")}
          />
        </Field>

        <Field
          error={errors.timezone?.message}
          id="market-timezone"
          label={t("wizard.timezoneLabel")}
        >
          <Select id="market-timezone" {...register("timezone")}>
            {TIMEZONES.map((zone) => (
              <option key={zone} value={zone}>
                {zone}
              </option>
            ))}
          </Select>
        </Field>

        <Field
          error={errors.operatingSince?.message}
          hint={t("wizard.operatingSinceHint")}
          id="market-operating-since"
          label={t("wizard.operatingSinceLabel")}
        >
          {/*
           * `min` atributi ATAYIN YO'Q — sababi fayl boshidagi izohda
           * (A3). Bu qoida grep bilan qulflangan: bu yerda sana hisobi
           * umuman bo'lmasligi kerak, chegara faqat serverdan keladi.
           */}
          <Input
            aria-describedby={
              errors.operatingSince
                ? "market-operating-since-error"
                : "market-operating-since-hint"
            }
            aria-invalid={errors.operatingSince ? true : undefined}
            autoComplete="off"
            id="market-operating-since"
            type="date"
            {...register("operatingSince")}
          />
        </Field>
      </section>

      <details
        className="rounded-lg border border-border bg-surface px-4 py-3"
        onToggle={(event) => setOfficialOpen(event.currentTarget.open)}
        open={officialOpen || hasOfficialError}
      >
        <summary className="cursor-pointer text-sm font-semibold">
          {t("wizard.sectionOfficial")}
        </summary>

        <div className="mt-4 flex flex-col gap-4">
          <p className="text-xs text-text-muted">
            {t("wizard.sectionOfficialHint")}
          </p>

          <Field
            error={errors.address?.message}
            id="market-address"
            label={t("wizard.addressLabel")}
          >
            <Input
              aria-describedby={
                errors.address ? "market-address-error" : undefined
              }
              aria-invalid={errors.address ? true : undefined}
              autoComplete="off"
              id="market-address"
              {...register("address")}
            />
          </Field>

          <Field
            error={errors.tin?.message}
            id="market-tin"
            label={t("wizard.tinLabel")}
          >
            <Input
              aria-describedby={errors.tin ? "market-tin-error" : undefined}
              aria-invalid={errors.tin ? true : undefined}
              autoComplete="off"
              id="market-tin"
              inputMode="numeric"
              {...register("tin")}
            />
          </Field>

          <Field
            error={errors.bankAccount?.message}
            id="market-bank-account"
            label={t("wizard.bankAccountLabel")}
          >
            <Input
              aria-describedby={
                errors.bankAccount ? "market-bank-account-error" : undefined
              }
              aria-invalid={errors.bankAccount ? true : undefined}
              autoComplete="off"
              id="market-bank-account"
              inputMode="numeric"
              {...register("bankAccount")}
            />
          </Field>

          <Field
            error={errors.bankMfo?.message}
            id="market-bank-mfo"
            label={t("wizard.bankMfoLabel")}
          >
            <Input
              aria-describedby={
                errors.bankMfo ? "market-bank-mfo-error" : undefined
              }
              aria-invalid={errors.bankMfo ? true : undefined}
              autoComplete="off"
              id="market-bank-mfo"
              inputMode="numeric"
              {...register("bankMfo")}
            />
          </Field>

          <Field
            error={errors.contactPhone?.message}
            id="market-contact-phone"
            label={t("wizard.contactPhoneLabel")}
          >
            <Input
              aria-describedby={
                errors.contactPhone ? "market-contact-phone-error" : undefined
              }
              aria-invalid={errors.contactPhone ? true : undefined}
              autoComplete="off"
              id="market-contact-phone"
              inputMode="tel"
              type="tel"
              {...register("contactPhone")}
            />
          </Field>
        </div>
      </details>

      <div>
        {/*
         * Aniq "Saqlash va davom etish" tugmasi — §6.5 ning forma qadami
         * shakli. Yuborilayotganda `disabled` VA matn o'zgaradi: takroriy
         * bosish ikkinchi qoralama bozor tug'dirardi.
         */}
        <Button disabled={busy} size="lg" type="submit">
          {busy ? t("wizard.saving") : t("wizard.saveAndContinue")}
        </Button>
      </div>
    </form>
  );
}
