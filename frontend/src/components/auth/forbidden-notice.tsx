"use client";

import { useLocale, useTranslations } from "next-intl";

import { localeHref } from "@/lib/locale-href";

/*
 * =============================================================================
 * RAD ETISH EKRANI — YAGONA KOMPONENT VA CHIQISH YO'LI (Topilma №K).
 *
 * Ilgari bu blok YIGIRMATA `page.tsx` da nusxa ko'chirilgan bitta
 * yalang'och qator edi: «Bu amal uchun ruxsat yo'q» — na sabab, na
 * chiqish yo'li. Nazoratchi uni yettita URL'da ko'rgan va har safar
 * boshi berk ko'chaga tushgan.
 *
 * Endi uchta narsa bor: NIMA bo'ldi, NEGA, va QAYERGA borish mumkin.
 *
 * ⛔ JOYI ATAYIN `ui/` EMAS. `src/components/ui/` dagi birorta primitiv
 *    `useTranslations` ni import qilmaydi (o'lchandi: 0 hodisa) va
 *    `empty-state.tsx` bu konvensiyani ochiq aytadi («bu faylda matn
 *    YO'Q»). Bu komponentning esa O'Z copy'si bor, ya'ni u domen
 *    komponenti.
 *
 * ⛔⛔ `Link` (`@/i18n/navigation`) ATAYIN ISHLATILMAYDI VA SABAB
 *    O'LCHANGAN: `next-intl/navigation` -> `next/navigation` zanjiri
 *    vitest ostida yechilmaydi va uni import qilgan HAR fayl «0 test»
 *    bilan yiqiladi (`camera-row.tsx` izohida qayd etilgan o'lchov:
 *    to'rtta fayl, 27 test). Bu komponent YIGIRMATA sahifada render
 *    qilinadi — jumladan `billing/page.test.tsx` ning mavjud
 *    `errors.forbidden` assertida — ya'ni o'sha zanjir bu yerda eng
 *    qimmat.
 *
 *    NARXI HALOL: oddiy `<a>` to'liq sahifa yuklashini beradi. Rad
 *    etish ekranidan chiqish kunlik amal EMAS (foydalanuvchi bu yerga
 *    adashib tushadi), ya'ni farq sezilmaydi — `camera-row.tsx` dagi
 *    ayni argument.
 *
 * ⛔ NISHON `/dashboard` VA U HAR ROL UCHUN XAVFSIZ: `app-shell.tsx`
 *    da o'sha navigatsiya elementi `permission: null`, ya'ni u hech bir
 *    huquq talab qilmaydi. Foydalanuvchini yana bir rad etish ekraniga
 *    yuborish nosozlikni ikki barobar qilardi.
 *
 *    RAD ETILGAN MUQOBIL: «roldan hosila qilingan uy sahifasi». U
 *    ikkinchi marshrutlash qoidasini tug'dirardi va u `app-shell`
 *    dagi navigatsiya matritsasi bilan bir kun ajralib ketardi.
 *
 * ⚠ MANZIL KODDA QAT'IY (T-6r1-03): u URL'dan ham, javob
 *   ma'lumotidan ham OLINMAYDI — ochiq redirekt yuzasi yaratilmaydi.
 *
 * ⚠ RAD ETISHNING SABABI (qaysi huquq yetishmayotgani) YOZILMAYDI:
 *   komponent qaysi huquq tekshirilganini BILMAYDI va uni propga
 *   aylantirish 20 ta chaqiruv joyini yana bir-biridan ajratardi.
 * =============================================================================
 */

export function ForbiddenNotice() {
  const t = useTranslations();
  const locale = useLocale();

  return (
    <div
      className="flex flex-col items-start gap-2 rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
      role="alert"
    >
      {/*
       * ⛔ MATN O'Z ELEMENTIDA QOLADI. Uni tushuntirish bilan bitta
       *    `<p>` ga qo'shish `billing/page.test.tsx` ning mavjud
       *    `getByText(messages.errors.forbidden)` assertini
       *    qizartirardi — «mavjud testlarni sindirmang» sharti aynan
       *    shu tanlovda hal bo'ladi.
       */}
      <p className="font-semibold">{t("errors.forbidden")}</p>
      <p>{t("errors.forbiddenHint")}</p>

      <a
        className="underline underline-offset-2"
        href={localeHref(locale, "/dashboard")}
      >
        {t("errors.backToDashboard")}
      </a>
    </div>
  );
}
