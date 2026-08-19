"use client";

import type { ReactNode } from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  ArrowRight,
  Check,
  Hash,
  Loader2,
  Phone,
  ShieldCheck,
  Store,
  User,
} from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Link } from "@/i18n/navigation";
import { demoErrorMessageKey } from "@/lib/demo-errors";

/*
 * Demo-forma — landing sahifasining YAGONA anonim yozuv yuzasi (10-04, Y-2).
 *
 * ⛔⛔ B-2 QOIDASI (10-RESEARCH, o'lchangan): bu fayl kirish formasining
 * skeletini KO'CHIRADI, lekin uning HTTP-mijoz o'rami va sxema katalogi
 * modullarini IMPORT QILMAYDI — o'sha graf 69 KB gzip va u anonim sahifada
 * hech nima chizmaydi. O'rniga:
 *   - yo'l — quyidagi LITERAL konstanta (modul importi emas);
 *   - sxema — shu faylning O'Z ichidagi mahalliy `z.object` (arzon chunk:
 *     forma kutubxonasi + resolver 11 KB gzip va u KERAK);
 *   - so'rov — XOM `fetch`, javob `res.ok`/`res.status` bilan hal qilinadi.
 * Qulf: `demo-form.test.tsx` dagi manba skani (locale-switcher naqshi).
 *
 * ⛔ G-SUBMIT (L-19): submitning yagona `disabled` sharti — `isSubmitting`.
 * Bo'sh maydon ham, belgilanmagan rozilik ham KO'RINADIGAN validatsiya
 * xabari beradi, jim tugma emas.
 *
 * ⛔ Telefon: klientda QATTIQ REGEKS YO'Q (T-10-11) — yagona haqiqat manbai
 * serverdagi normalizatsiya. Klient faqat raqam SONINI (≥9) tekshiradi;
 * qattiq klient regeksi server qabul qiladigan raqamlarni rad etib
 * IKKINCHI haqiqat manbai tug'dirardi.
 */
const DEMO_REQUEST_PATH = "/api/v1/public/demo-requests";

/** Anti-spam 2-qatlam: mount'dan yuborishgacha minimal turish vaqti. */
const MIN_DWELL_MS = 3000;

/** O'zbek raqami kamida 9 raqam tashiydi (prefikssiz mahalliy shakl). */
const MIN_PHONE_DIGITS = 9;

type DemoFormValues = {
  name: string;
  phone: string;
  marketName: string;
  stallCount: string;
  consent: boolean;
  website: string;
};

export function DemoForm() {
  const t = useTranslations("landing");
  const locale = useLocale();
  const [submitted, setSubmitted] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  /*
   * Dwell o'lchovi uchun mount lahzasi. `Date.now()` render ichida
   * chaqirilmaydi (react-hooks/purity) — muhr mount effektida bosiladi;
   * effekt hali yugurmagan bo'lsa yuborish «juda tez» deb qaraladi.
   */
  const mountedAtRef = useRef<number | null>(null);
  const alertRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    mountedAtRef.current ??= Date.now();
  }, []);

  /* Xato blokiga fokus (§15.6) — forma saqlangan holda e'tibor sababga. */
  useEffect(() => {
    if (formError !== null) {
      alertRef.current?.focus();
    }
  }, [formError]);

  const schema = useMemo(
    () =>
      z.object({
        name: z
          .string()
          .trim()
          .min(2, { error: t("form.validation.nameRequired") }),
        phone: z
          .string()
          .trim()
          .min(1, { error: t("form.validation.phoneRequired") })
          .refine(
            (value) => (value.match(/\d/gu) ?? []).length >= MIN_PHONE_DIGITS,
            { error: t("form.validation.phoneInvalid") },
          ),
        marketName: z
          .string()
          .trim()
          .min(2, { error: t("form.validation.marketRequired") }),
        /*
         * Ixtiyoriy maydon: bo'sh — yaroqli; kiritilsa 1..100 000 oralig'i
         * (§12.1). Maxsus kaliti yo'q YOPIQ copy reyestrida — umumiy
         * validatsiya matni sabab va keyingi qadamni beradi.
         */
        stallCount: z.string().refine(
          (value) => {
            const cleaned = value.replaceAll(" ", "");
            if (cleaned === "") return true;
            return (
              /^\d+$/u.test(cleaned) &&
              Number(cleaned) >= 1 &&
              Number(cleaned) <= 100_000
            );
          },
          { error: t("form.error.validation") },
        ),
        consent: z.boolean().refine((value) => value, {
          error: t("form.validation.consentRequired"),
        }),
        website: z.string(),
      }),
    [t],
  );

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<DemoFormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: "",
      phone: "",
      marketName: "",
      stallCount: "",
      consent: false,
      website: "",
    },
  });

  /** Xato tanasidan kodni EHTIYOTKORLIK bilan o'qiydi (xom `fetch`). */
  async function readErrorCode(res: Response): Promise<string> {
    let detail: unknown;
    try {
      const body: unknown = await res.json();
      detail =
        typeof body === "object" && body !== null && "detail" in body
          ? (body as { detail: unknown }).detail
          : undefined;
    } catch {
      detail = undefined;
    }
    if (typeof detail === "string") return detail;
    // FastAPI'ning standart 422 massivi (Pydantic chegaralari) — server
    // alohida handler qo'shmagan, xaritalash klientda (10-01 eslatmasi).
    if (Array.isArray(detail)) return "validation_error";
    if (res.status === 429) return "rate_limited";
    if (res.status === 422) return "validation_error";
    return "delivery_failed";
  }

  /** Kod -> ekran matni; `delivery_failed` shoxida aloqa telefoni sharti. */
  function errorTextFor(code: string): string {
    const key = demoErrorMessageKey(code);
    if (key === "form.error.body") {
      /*
       * O-06: `{phone}` bo'sh qavs bo'lib KO'RSATILMAYDI — env berilmagan
       * bo'lsa telefonsiz variant. Qiymat build paytida qotiriladi.
       */
      const contactPhone = process.env.NEXT_PUBLIC_CONTACT_PHONE;
      return contactPhone
        ? t("form.error.body", { phone: contactPhone })
        : t("form.error.bodyNoPhone");
    }
    return t(key);
  }

  async function onSubmit(values: DemoFormValues) {
    setFormError(null);

    /*
     * Anti-spam 1 — honeypot: ko'rinmas maydon to'ldirilgan bo'lsa bu bot.
     * `fetch` UMUMAN chaqirilmaydi va JIM muvaffaqiyat ko'rsatiladi —
     * xato qaytarilsa mexanizm javobdan o'qilardi (server ham shunday,
     * `public.py` 3-qadami).
     */
    if (values.website.trim() !== "") {
      setSubmitted(true);
      return;
    }

    /*
     * Anti-spam 2 — dwell: odam formani 3 soniyadan tez to'ldirmaydi.
     * Xato KO'RSATILMAYDI (honeypot bilan bir xil jim shox) — haqiqiy
     * chegara baribir serverda (IP kesimi, T-10-01). Muhr hali yo'q
     * bo'lsa ham (effekt yugurmagan) — o'sha jim shox.
     */
    const mountedAt = mountedAtRef.current;
    if (mountedAt === null || Date.now() - mountedAt < MIN_DWELL_MS) {
      setSubmitted(true);
      return;
    }

    const cleanedStalls = values.stallCount.replaceAll(" ", "");
    const payload: Record<string, unknown> = {
      name: values.name.trim(),
      phone: values.phone.trim(),
      market_name: values.marketName.trim(),
      locale,
    };
    if (cleanedStalls !== "") {
      payload.stall_count = Number(cleanedStalls);
    }

    try {
      const res = await fetch(DEMO_REQUEST_PATH, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        setSubmitted(true);
        return;
      }
      setFormError(errorTextFor(await readErrorCode(res)));
    } catch {
      // Tarmoq yiqildi — sabab va keyingi qadam `delivery_failed` matnida
      // (qayta urinish yoki bevosita qo'ng'iroq).
      setFormError(errorTextFor("delivery_failed"));
    }
  }

  if (submitted) {
    return (
      /*
       * ⛔ Muvaffaqiyat sahifada QOLADI (toast emas, §12.4): foydalanuvchi
       * «yubordimmi?» deb qaytib qaraydi. `.motion-enter` — mavjud sinf;
       * konfetti YO'Q (u faqat kunlik plan bajarilganda).
       */
      <div
        aria-live="polite"
        className="motion-enter flex flex-col items-center gap-3 rounded-2xl border border-border bg-surface p-10 text-center"
        role="status"
      >
        {/* Doira ichidagi belgi — «bo'ldi» hissi belgining O'ZIDAN
            emas, uning JOYLASHUVIDAN keladi: markazda, katta, tinch. */}
        <span className="flex size-14 items-center justify-center rounded-full bg-success/15">
          <Check
            aria-hidden="true"
            className="size-7 text-success-text"
            strokeWidth={2.5}
          />
        </span>
        <p className="landing-h2 tracking-tight">
          {t("form.success.title")}
        </p>
        <p className="max-w-[40ch] landing-body text-text-muted">
          {t("form.success.body")}
        </p>
      </div>
    );
  }

  return (
    <form
      className="landing-form flex flex-col gap-5"
      noValidate
      /*
       * `handleSubmit(onSubmit)` HODISA ichida chaqiriladi (renderda emas):
       * `onSubmit` ref o'qiydi va `Date.now()` chaqiradi — react-hooks
       * qoidalari ularni faqat hodisa yo'lida qabul qiladi.
       */
      onSubmit={(event) => {
        void handleSubmit(onSubmit)(event);
      }}
    >
      {/*
       * ⛔⛔ IKKI USTUN (260819) — «hozirgi globalda mashxur formalar
       *     kabi» topshirig'ining o'zagi. To'rtta maydon bir ustunda
       *     turganda forma UZUN ko'rinadi va odam boshlashdan oldin
       *     charchaydi; juftlab qo'yilganda esa u ikki qatorga siqiladi
       *     va «tez to'ldiraman» degan taassurot beradi.
       *
       *     ⛔ Telefonda (`sm` dan past) BIR USTUN: 375px da ikkita
       *       52px maydon yonma-yon sig'maydi va yorliqlar kesilardi.
       */}
      <div className="grid gap-5 sm:grid-cols-2">
        <Field
          error={errors.name?.message}
          id="demo-name"
          label={t("form.name")}
          size="lg"
        >
          <div className="relative">
            <User
              aria-hidden="true"
              className="landing-field-icon size-5"
              strokeWidth={1.75}
            />
            <Input
              aria-describedby={errors.name ? "demo-name-error" : undefined}
              aria-invalid={errors.name ? true : undefined}
              autoComplete="name"
              className="h-13 rounded-xl pl-11 text-lg"
              id="demo-name"
              placeholder={t("form.phName")}
              {...register("name")}
            />
          </div>
        </Field>

        <Field
          error={errors.phone?.message}
          hint={t("form.hintPhone")}
          id="demo-phone"
          label={t("form.phone")}
          size="lg"
        >
          <div className="relative">
            <Phone
              aria-hidden="true"
              className="landing-field-icon size-5"
              strokeWidth={1.75}
            />
            <Input
              aria-describedby={
                errors.phone ? "demo-phone-error" : "demo-phone-hint"
              }
              aria-invalid={errors.phone ? true : undefined}
              autoComplete="tel"
              className="h-13 rounded-xl pl-11 text-lg"
              id="demo-phone"
              inputMode="tel"
              placeholder={t("form.phPhone")}
              type="tel"
              {...register("phone")}
            />
          </div>
        </Field>

        <Field
          error={errors.marketName?.message}
          id="demo-market"
          label={t("form.market")}
          size="lg"
        >
          <div className="relative">
            <Store
              aria-hidden="true"
              className="landing-field-icon size-5"
              strokeWidth={1.75}
            />
            <Input
              aria-describedby={
                errors.marketName ? "demo-market-error" : undefined
              }
              aria-invalid={errors.marketName ? true : undefined}
              autoComplete="organization"
              className="h-13 rounded-xl pl-11 text-lg"
              id="demo-market"
              placeholder={t("form.phMarket")}
              {...register("marketName")}
            />
          </div>
        </Field>

        {/* ⛔ «ixtiyoriy» YORLIQDA yozilgan, yulduzcha bilan emas: yulduzcha
            qaysi maydon majburiyligini FAQAT o'rganib bilgan odamga
            aytadi. Bu forma esa birinchi marta ko'riladi. */}
        <Field
          error={errors.stallCount?.message}
          id="demo-stalls"
          label={
            <>
              {t("form.stallCount")}{" "}
              <span className="font-normal text-text-muted">
                — {t("form.optional")}
              </span>
            </>
          }
          size="lg"
        >
          <div className="relative">
            <Hash
              aria-hidden="true"
              className="landing-field-icon size-5"
              strokeWidth={1.75}
            />
            <Input
              aria-describedby={
                errors.stallCount ? "demo-stalls-error" : undefined
              }
              aria-invalid={errors.stallCount ? true : undefined}
              autoComplete="off"
              className="h-13 rounded-xl pl-11 text-lg"
              id="demo-stalls"
              inputMode="numeric"
              placeholder={t("form.phStalls")}
              {...register("stallCount")}
            />
          </div>
        </Field>
      </div>

      {/*
        Rozilik — maxfiylik havolasi yorliq ICHIDA (§15.4): bosish maydoni
        aniq, skrinriderda kontekst saqlanadi. Yorliq ichidagi <a> bosilishi
        checkbox'ni almashtirmaydi (interaktiv avlod — HTML spec xulqi).
      */}
      <div className="flex flex-col gap-2">
        <label
          className="flex cursor-pointer items-start gap-3 landing-note"
          htmlFor="demo-consent"
        >
          <input
            aria-describedby={
              errors.consent ? "demo-consent-error" : undefined
            }
            aria-invalid={errors.consent ? true : undefined}
            className="mt-0.5 size-5 shrink-0 accent-accent"
            id="demo-consent"
            type="checkbox"
            {...register("consent")}
          />
          <span>
            {t.rich("form.consent", {
              privacy: (chunks: ReactNode) => (
                <Link
                  className="font-semibold text-accent-text underline underline-offset-2"
                  href="/maxfiylik"
                >
                  {chunks}
                </Link>
              ),
            })}
          </span>
        </label>
        {errors.consent ? (
          <p
            className="text-sm text-danger-text motion-shake"
            id="demo-consent-error"
          >
            {errors.consent.message}
          </p>
        ) : null}
      </div>

      {/*
        Honeypot — odam KO'RMAYDI (sr-only + aria-hidden + tabIndex -1),
        bot esa `website` nom bo'yicha to'ldiradi. To'ldirilgan bo'lsa
        `onSubmit` jim muvaffaqiyatga o'tadi, so'rov ketmaydi.
      */}
      <div aria-hidden="true" className="sr-only">
        <input
          autoComplete="off"
          id="demo-website"
          tabIndex={-1}
          type="text"
          {...register("website")}
        />
      </div>

      {formError ? (
        /*
         * Xatoda forma SAQLANADI (§12.4): kiritilgan qiymatlar joyida,
         * blok sabab VA keyingi qadamni aytadi (D-02), fokus shu yerga.
         */
        <div
          className="rounded-xl bg-danger/10 px-4 py-3"
          ref={alertRef}
          role="alert"
          tabIndex={-1}
        >
          <p className="landing-note font-semibold text-danger-text">
            {t("form.error.title")}
          </p>
          <p className="landing-note text-danger-text">{formError}</p>
        </div>
      ) : null}

      {/* ⛔ TO'LIQ KENGLIK — forma kartasining eng oxirgi va eng katta
          elementi. Yarim kenglikdagi tugma «yana bir narsa qoldimi?»
          degan ikkilanish beradi; to'liq kenglik esa «shu — oxiri»
          deydi. Strelka harakat yo'nalishini bildiradi (statik). */}
      <Button
        className="w-full"
        disabled={isSubmitting}
        size="hero"
        type="submit"
      >
        {isSubmitting ? (
          <>
            <Loader2
              aria-hidden="true"
              className="animate-spin motion-reduce:animate-none"
            />
            {t("form.submitting")}
          </>
        ) : (
          <>
            {t("form.submit")}
            <ArrowRight aria-hidden="true" className="size-5" />
          </>
        )}
      </Button>

      {/* ⛔ Tugma OSTIDA, ustida emas: odam avval «yuborishga tayyorman»
          deb qaror qiladi, keyin «xavfsizmi?» deb so'raydi. Javob aynan
          shu tartibda joylashgan. */}
      <p className="flex items-start gap-2 landing-micro text-text-muted">
        <ShieldCheck
          aria-hidden="true"
          className="mt-px size-4 shrink-0"
          strokeWidth={1.75}
        />
        {t("form.privacyNote")}
      </p>
    </form>
  );
}
