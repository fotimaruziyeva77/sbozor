"use client";

import { ArrowRight, CircleDot, HandCoins, Info, LogOut } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Link } from "@/i18n/navigation";
import { useOpenShift } from "@/lib/shift-queries";
import { cn } from "@/lib/cn";

/*
 * =============================================================================
 * KASSIR BRIFI — bosh ekranning kassir uchun mazmuni (260819).
 *
 * ⛔⛔ NEGA QO'SHILDI: kassirning bosh ekranida BITTA son turardi
 *     («bugun yozilgan kvitansiyalar») va boshqa hech nima. Kassir u
 *     yerdan ish boshlay olmasdi va boshliq so'raganda javob topa
 *     olmasdi — foydalanuvchi aynan shu ikkisini so'radi: «kassirga
 *     qulay va axborot berishga boshliq so'rab qolganda oson».
 *
 *     Kassirga kuniga kerak bo'ladigan javob UCHTA:
 *       1. Smenam ochiqmi va qachondan beri?   -> shu karta
 *       2. Bugun nechta patta yozdim?          -> `HeadlineCard` (tepada)
 *       3. Ishga qayerdan kiraman?             -> «Patta yig'ish» tugmasi
 *
 * ⛔⛔ SUMMA BU YERDA HECH QACHON KO'RSATILMAYDI — VA BU ENG MUHIM
 *     CHEKLOV. Kassir smenani KO'R sanaydi: naqdni o'zi sanab kiritadi,
 *     tizim esa o'z summasini bermaydi va farqni faqat direktor ko'radi
 *     (`shift-queries.ts` sarlavhasi, D-25/D-26).
 *
 *     Yig'indini bu ekranga chiqarish uchta himoyani BIR QATORDA bekor
 *     qilardi: server oxirgi 5 ta to'lovni beradi (qo'shib chiqara
 *     olmasin), yopish javobida tizim summasi YO'Q, farq esa
 *     `REPORT_VIEW` ostida. Kassir sonni o'qib, deklaratsiyada AYNAN
 *     shuni yozardi va farq HAR DOIM nol bo'lardi — ko'r sanashning
 *     butun qiymati yo'qolardi.
 *
 *     Shuning uchun bu kartada: HOLAT, VAQT va AMAL bor; SON yo'q.
 *     Yagona son — tepadagi `HeadlineCard` ning KVITANSIYA SONI
 *     (`count`, summa emas).
 *
 * ⛔ Ko'r sanash izohi ATAYIN ko'rinadi: «summani qayerdan ko'raman?»
 *    degan savol kassirda baribir tug'iladi va javobsiz qolsa u buni
 *    NUQSON deb o'ylaydi. Bir qator izoh savolni yopadi.
 *
 * ⛔ So'rov FAQAT kassirda ketadi: chaqiruvchi (`dashboard/page.tsx`)
 *    komponentni `payment_create` sharti bilan chizadi. Shart
 *    komponentdan TASHQARIDA — huquqsiz sessiyada `GET /shifts/open`
 *    ga so'rov HAM ketmasin (kodbazadagi mavjud naqsh).
 * =============================================================================
 */

export function CashierBrief() {
  const t = useTranslations();
  const format = useFormatter();
  const { data, isLoading } = useOpenShift();

  if (isLoading) {
    return (
      <div aria-busy="true" role="status">
        <span className="sr-only">{t("common.loading")}</span>
        {/* Balandlik yakuniy karta bilan bir xil — ochilganda sakramaydi. */}
        <Skeleton className="h-40" />
      </div>
    );
  }

  const shift = data ?? null;
  const openedAt = shift === null ? null : new Date(shift.opened_at);

  return (
    <Card>
      <CardContent className="flex flex-col gap-5 pt-5">
        {/* ---- 1-qator: smena holati ------------------------------------ */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-col gap-1">
            <p className="text-sm font-semibold text-text-muted">
              {t("collect.shiftTitle")}
            </p>
            <p className="flex items-center gap-2 text-lg font-semibold">
              {/*
               * ⛔ Rang YOLG'IZ signal EMAS (WCAG 1.4.1): nuqta yonida
               *    holat MATNI turadi va u rangsiz ham o'qiladi.
               */}
              <CircleDot
                aria-hidden="true"
                className={cn(
                  "size-4 shrink-0",
                  shift === null ? "text-text-muted" : "text-success-text",
                )}
                strokeWidth={2.5}
              />
              {shift === null
                ? t("dashboard.shiftNone")
                : t("dashboard.shiftOpenSince", {
                    time: format.dateTime(openedAt as Date, {
                      timeStyle: "short",
                    }),
                  })}
            </p>
          </div>

          {shift === null ? null : (
            <Link
              className={cn(
                "inline-flex min-h-11 shrink-0 items-center gap-2 rounded-md",
                "border border-border-ui px-4 text-sm font-semibold",
                "transition-colors hover:bg-surface-muted",
              )}
              href="/collect/shift"
            >
              <LogOut aria-hidden="true" className="size-4" />
              {t("collect.shiftClose")}
            </Link>
          )}
        </div>

        {/* ---- 2-qator: kunlik ishga kirish ------------------------------ */}
        {/*
         * ⛔ Bu tugma sahifadagi BIRLAMCHI amal va u smena yopiq bo'lsa
         *    ham ko'rinadi: smenani ochish AYNAN `/collect` da bo'ladi
         *    (`shift-open-card.tsx`), ya'ni ikkala holatda ham to'g'ri
         *    joyga olib boradi va ikkinchi tugma kerak emas.
         */}
        <Link
          className={cn(
            "inline-flex min-h-14 items-center justify-between gap-3 rounded-xl",
            "bg-accent px-5 text-accent-fg transition-colors hover:bg-accent-hover",
          )}
          href="/collect"
        >
          <span className="flex items-center gap-3">
            <HandCoins aria-hidden="true" className="size-5 shrink-0" />
            {/*
             * ⛔ `collect.title` («Patta yig'ish»), `nav.collect`
             *    («Yig'ish») EMAS: menyu yorlig'i qisqa bo'lishi kerak
             *    va u yerda kontekst yon paneldan keladi. Bu yerda esa
             *    tugma YOLG'IZ turadi va «Yig'ish» nimani yig'ishini
             *    aytmaydi. Sahifaning O'Z sarlavhasi bilan bir xil
             *    matn bosishdan keyin nima ochilishini ham va'da qiladi.
             */}
            <span className="text-lg font-semibold">
              {t("collect.title")}
            </span>
          </span>
          <ArrowRight aria-hidden="true" className="size-5 shrink-0" />
        </Link>

        {/* ---- 3-qator: kutilgan savolning javobi ------------------------ */}
        <p className="flex items-start gap-2 text-sm leading-relaxed text-text-muted">
          <Info aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
          {shift === null
            ? t("dashboard.shiftNoneHint")
            : t("dashboard.blindHint")}
        </p>
      </CardContent>
    </Card>
  );
}
