"use client";

import { Suspense } from "react";
import { ArrowRight } from "lucide-react";
import { useTranslations } from "next-intl";

import { ForbiddenNotice } from "@/components/auth/forbidden-notice";
import { AccuracyBlock } from "@/components/reports/accuracy-block";
import { AnomalyArchive } from "@/components/reports/anomaly-archive";
import { CompareMode } from "@/components/reports/compare-mode";
import { DebtorsReport } from "@/components/reports/debtors-report";
import { ExportButton } from "@/components/reports/export-button";
import {
  PeriodPicker,
  useReportPeriod,
} from "@/components/reports/period-picker";
import { RevenueReport } from "@/components/reports/revenue-report";
import { Link } from "@/i18n/navigation";
import { useAuthStore } from "@/lib/auth-store";
import { hasPermission } from "@/lib/rbac";

/*
 * =============================================================================
 * Y-1 + Y-2 — DAVR HISOBOTLARI VA AI ANIQLIGI (RECON-04, RECON-05).
 *
 * ⛔⛔ FAZANING ENG YUQORI USTUVORLIKDAGI YUZASI: direktor «oktyabrda
 *     nima bo'ldi?» degan BITTA savolini shu ekranda beradi va UCHTA
 *     javob oladi — tushum, qarz, nomuvofiqlik — hammasi BIR davrda
 *     (§4.2). To'rtinchi blok esa o'sha javoblarning ISHONCHLILIGI.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 1. BLOK TO'PLAMI ⛔ DAVRGA QARAB O'ZGARMAYDI — BESHALASI HAR DOIM
 * -----------------------------------------------------------------------
 * Bu qoida `/reconciliation` ning ⛔ TESKARISI va farq ATAYIN:
 *
 *   (a) ⛔ MAKSIMUM ALLAQACHON KECHA (§4.4). `daily_charges` D+1 04:10 da
 *       tug'iladi, davr tanlagichi esa bugungi kunni UMUMAN qabul
 *       qilmaydi — ya'ni «ma'lumot HALI TUG'ILMAGAN» holati bu ekranda
 *       ⛔ YUZAGA KELMAYDI. `/reconciliation` da esa u har kuni yuzaga
 *       keladi (kun tanlagichi BUGUNNI beradi) va o'sha yerda blokni
 *       chizmaslik YAGONA to'g'ri javob edi;
 *
 *   (b) ⛔ BLOKNI YASHIRISH BO'SH DAVRNI MUVAFFAQIYAT KABI KO'RSATARDI.
 *       Chizilmagan «Qarzdorlik ro'yxati» direktorga ⛔ «qarzdor yo'q»
 *       bo'lib o'qilardi — holbuki u «bu davr uchun so'rov yuborilmadi»
 *       degani bo'lardi. ⛔ Bo'sh davr — BO'SH HOLAT (§14.7), yo'q blok
 *       EMAS.
 *
 * ⛔ Shuning uchun bu faylda blok chizilishini shartga bog'laydigan
 *    BIRORTA tarmoqlanish YO'Q. Beshala `<section>` ham shartsiz.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 2. BU FAYL MAZMUN ATRIBUTINI ⛔ HECH QACHON YOZMAYDI
 * -----------------------------------------------------------------------
 * ⚠ Atributning NOMI ham bu faylda uchramaydi — uning yo'qligi mexanik
 *   `grep` darvozasi (`0`) bilan o'lchanadi, ya'ni izohdagi nusxa
 *   darvozani o'ziga qarshi qo'yardi.
 *
 * Atribut ⛔ RO'YXAT KOMPONENTINING O'ZIDA (07 G-29(b) mexanikasi).
 * Sabab O'LCHANGAN (06-faza G-25): faqat blok atributlarini ko'radigan
 * darvozani ⛔ BO'SH O'RAM MUKAMMAL qondirardi va butun yuza
 * ⛔ CHIZILMAGAN holda faza YASHIL qaytardi. Agar atribut shu faylda
 * bo'lsa, sahifa o'zining false-green iga o'zi yo'l ochardi.
 *
 * -----------------------------------------------------------------------
 * ⛔ 3. DAVR ⛔ BIR MARTA TANLANADI VA PROP BO'LIB UZATILMAYDI
 * -----------------------------------------------------------------------
 * `<PeriodPicker/>` sahifada ⛔ AYNAN BIR MARTA; to'rtala blok esa
 * oraliqni `useReportPeriod()` HOOKIDAN oladi (08-13 naqshi). Propga
 * o'tkazish sahifa bilan blok orasida ⛔ UCHINCHI HAQIQAT MANBAINI
 * tug'dirardi va bir kun ular jimgina ajralib ketardi.
 *
 * ⚠ Bu fayl hookni FAQAT eksport tugmalari uchun chaqiradi — ularning
 *   nishoni (`period`) va o'chirilganligi (`isEmpty`) sahifaning
 *   zimmasida, chunki tugmalarni ham SAHIFA joylashtiradi (quyida).
 *
 * -----------------------------------------------------------------------
 * ⛔ 4. EKSPORT TUGMASI — UCH BLOKDA SAHIFADAN, TO'RTINCHISIDA ICHKARIDAN
 * -----------------------------------------------------------------------
 * `revenue`, `debtors`, `anomalies` — tugmani ⛔ SAHIFA qo'yadi: blokni
 * ham u quradi va ro'yxat komponentlari o'z ichida tugma SAQLAMAYDI
 * (08-13 qarori).
 *
 * ⛔ `accuracy` — ISTISNO va u MUZOKARASIZ: tugma `accuracy-block.tsx`
 *    ning ICHIDA (§9.2 diagrammasi, 08-15). Bu yerga IKKINCHISINI qo'yish
 *    bir blokda ⛔ IKKI BIR XIL tugma berardi va §12.1 ning «to'rtta
 *    eksport» kontrakti beshtaga aylanardi.
 *
 * -----------------------------------------------------------------------
 * ⛔ 5. HUQUQ KO'ZGUSI — SO'ROVDAN OLDIN
 * -----------------------------------------------------------------------
 * `report_view` yo'q sessiyada birorta so'rov UMUMAN ketmaydi. ⚠ Haqiqiy
 * nazorat SERVERDA — hisobot marshrutlari `require_permission` ostida
 * (08-07/08-12/08-16). ⛔ Yangi huquq QO'SHILMAYDI: `report_view` ikkala
 * matritsada ham ALLAQACHON bor va bu faza `rbac.ts` ↔ `rbac.py`
 * juftligiga UMUMAN TEGMAYDI (M-6).
 *
 * ⚠ `Suspense` ⛔ MAJBURIY: ish maydoni `?from=`/`?to=` ni `nuqs` orqali
 *   KLIENTDA o'qiydi va chegara bo'lmasa Next 16 butun marshrutni statik
 *   prerender ro'yxatidan chiqarib `build` ni YIQITADI (`/reconciliation`
 *   va `/billing` da o'lchangan).
 *
 * -----------------------------------------------------------------------
 * ⚠ 6. SARLAVHANING `text-2xl` I §7.2 DAGI «AYNAN BITTA Display» EMAS
 * -----------------------------------------------------------------------
 * Sahifa sarlavhasi — ⛔ QOBIQ elementi va u kodbazadagi o'n oltita
 * marshrutda AYNAN shu shaklda (`text-2xl font-semibold tracking-tight`).
 * §7.2 esa MA'LUMOT raqamlari haqida: davr tushumi Display oladi,
 * qarzdorlik yig'indisi esa OLMAYDI. Sarlavhani kichraytirish uni blok
 * sarlavhalari (`text-lg`) bilan TENGLASHTIRARDI va ierarxiyani
 * yo'qotardi.
 *
 * ⛔ 7. SOLISHTIRUV NAVIGATSIYADA EMAS (§4.7) — havola SHU SAHIFADA.
 *    U parallel rejimning 2–4 haftasi uchun va doimiy navigatsiya sloti
 *    uni cutover'dan keyin ham abadiy qoldirardi.
 * =============================================================================
 */

export default function ReportsPage() {
  const t = useTranslations();
  const { principal } = useAuthStore();

  if (!hasPermission(principal?.roles ?? [], "report_view")) {
    return <ForbiddenNotice />;
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">
          {t("reports.title")}
        </h1>

        {/*
         * ⛔ AKSENT OLMAYDI (§13.3): fazadagi yagona aksent fonli tugma —
         *   Y-3 dagi `[Daftarni yuklash]`. Bu havola esa NAVIGATSIYA,
         *   yakunlovchi amal emas.
         */}
        <Link
          className="inline-flex min-h-11 items-center gap-2 rounded-md border border-border bg-surface px-4 text-sm font-semibold text-text hover:bg-surface-muted"
          href="/reports/compare"
        >
          {t("reports.compareLink")}
          <ArrowRight aria-hidden="true" className="size-4" />
        </Link>
      </div>

      <Suspense
        fallback={
          <p className="text-sm text-text-muted" role="status">
            {t("common.loading")}
          </p>
        }
      >
        <ReportsWorkspace />
      </Suspense>
    </div>
  );
}

/* --- Ish maydoni ---------------------------------------------------------- */

function ReportsWorkspace() {
  /*
   * ⛔ HOOK FAQAT EKSPORT NISHONI UCHUN (yuqoridagi 3-band). Bloklar
   *   oraliqni O'ZLARI shu hookdan oladi — bu yerdan propga uzatilmaydi.
   *
   * ⛔ `isEmpty` NI HURMAT QILISH SHART: bo'sh oraliqda eksport so'rovi
   *    server `400 range_invalid` bilan qaytarardi va ekranda MAHSULOT
   *    QARORI o'rniga XATO ko'rinardi (08-09 kontrakti).
   */
  const period = useReportPeriod();
  const target = { from: period.from, to: period.to };

  return (
    /* ⛔ `gap-8` = 32px — beshala blok orasidagi YAGONA masofa (§6.1). */
    <div className="flex flex-col gap-8">
      {/*
       * --- A: DAVR TANLAGICHI — ⛔ BOSHQARUV, ro'yxat emas -----------------
       *
       * ⛔ Shu sababdan u mazmun juftligining YAGONA istisnosi
       *   (`CONTENT_EXEMPT`) va istisnolar to'plamining O'LCHAMI darvozada
       *   alohida assert bilan qulflangan.
       */}
      <section data-report-block="period">
        <PeriodPicker />
      </section>

      {/*
       * --- B…E: BESHALA BLOK ⛔ SHARTSIZ (yuqoridagi 1-band) ---------------
       *
       * ⛔ Eksport tugmasi blok ICHIDA, ro'yxatdan KEYIN: u o'sha blokning
       *   amali va sahifa darajasidagi yagona tugma «qaysi hisobot
       *   yuklanadi?» degan javobsiz savolni tug'dirardi (§12.1).
       */}
      {/*
       * ⛔⛔ SOLISHTIRISH REJIMI — dizayn talabi (Hisobot ekrani, 260819).
       *
       * Tushum blokidan OLDIN turadi: direktor avval «qanday o'zgardi»
       * ni ko'radi, keyin kunlar kesimiga tushadi. Dizaynda ham shu
       * tartib.
       *
       * ⚠ `data-report-block` BERILMAYDI: o'sha atribut hisobot
       *   bloklarining YOPIQ to'plamini o'lchaydi (G-37 naqshi) va yangi
       *   a'zo qo'shilishi o'sha darvozani qizartirardi. Solishtirish —
       *   hisobot EMAS, hisobotlar USTIDAGI qatlam.
       */}
      <section className="flex flex-col gap-3">
        <CompareMode />
      </section>

      <section className="flex flex-col gap-3" data-report-block="revenue">
        <RevenueReport />
        <div>
          <ExportButton
            kind="revenue"
            period={target}
            unavailable={period.isEmpty}
          />
        </div>
      </section>

      <section className="flex flex-col gap-3" data-report-block="debtors">
        <DebtorsReport />
        <div>
          <ExportButton
            kind="debtors"
            period={target}
            unavailable={period.isEmpty}
          />
        </div>
      </section>

      <section className="flex flex-col gap-3" data-report-block="anomalies">
        <AnomalyArchive />
        <div>
          <ExportButton
            kind="anomalies"
            period={target}
            unavailable={period.isEmpty}
          />
        </div>
      </section>

      {/*
       * ⛔ ANIQLIK BLOKIDA IKKINCHI EKSPORT TUGMASI YO'Q (4-band): u
       *   `accuracy-block.tsx` ning ICHIDA va u yerda qolishi §9.2
       *   diagrammasining talabi.
       */}
      <section data-report-block="accuracy">
        <AccuracyBlock />
      </section>
    </div>
  );
}
