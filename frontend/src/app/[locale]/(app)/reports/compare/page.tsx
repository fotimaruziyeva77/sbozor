"use client";

import { Suspense } from "react";
import { useTranslations } from "next-intl";

import { BrandLoader } from "@/components/ui/brand-loader";
import { ForbiddenNotice } from "@/components/auth/forbidden-notice";
import { CompareTable } from "@/components/reports/compare-table";
import { ExportButton } from "@/components/reports/export-button";
import {
  CompareDayPicker,
  LedgerImport,
  useCompareDay,
} from "@/components/reports/ledger-import";
import { useAuthStore } from "@/lib/auth-store";
import { hasPermission } from "@/lib/rbac";
import { useThreeWayReport } from "@/lib/report-queries";

/*
 * =============================================================================
 * Y-3 — UCH TOMONLAMA SOLISHTIRUV (RECON-04, §10.1).
 *
 * ⛔⛔ BU EKRAN PARALLEL REJIMNING (hafta 13–16) KUNLIK ASBOBI: qog'oz
 *     daftar bilan tizim yonma-yon turadi va cutover qarori aynan shu
 *     varaqdan chiqadi.
 *
 * -----------------------------------------------------------------------
 * ⛔ 1. NEGA ALOHIDA MARSHRUT, `/reports` ICHIDA EMAS (§4.3)
 * -----------------------------------------------------------------------
 * Uning davri ⛔ KUN, `/reports` niki esa ORALIQ. Ikkalasini bitta
 * sahifaga qo'yish bitta tanlagichni ikki xil ma'noda ishlatishni talab
 * qilardi va foydalanuvchi qaysi davr qaysi jadvalga tegishli ekanini
 * BILMASDI.
 *
 * ⛔ Navigatsiyaga esa KIRMAYDI (§4.7): u parallel rejimning 2–4 haftasi
 *    uchun va doimiy nav sloti uni cutover'dan keyin ham ABADIY
 *    qoldirardi. Kirish yo'li — `/reports` ichidagi havola.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 2. BU FAYL MAZMUN ATRIBUTINI ⛔ HECH QACHON YOZMAYDI
 * -----------------------------------------------------------------------
 * ⚠ Atributning NOMI ham bu faylda uchramaydi — uning yo'qligi mexanik
 *   `grep` darvozasi (`0`) bilan o'lchanadi, ya'ni izohdagi nusxa
 *   darvozani o'ziga qarshi qo'yardi.
 *
 * Atribut ⛔ BLOK KOMPONENTINING O'ZIDA. Sabab O'LCHANGAN (06-faza
 * G-25): faqat blok atributlarini ko'radigan darvozani ⛔ BO'SH O'RAM
 * MUKAMMAL qondirardi va butun yuza ⛔ CHIZILMAGAN holda faza YASHIL
 * qaytardi. Agar atribut shu faylda bo'lsa, sahifa o'zining false-green
 * iga o'zi yo'l ochardi.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 3. UCHALA BLOK ⛔ SHARTSIZ — DAFTAR BOR-YO'QLIGIDAN QAT'I NAZAR
 * -----------------------------------------------------------------------
 * Daftar yuklanmagan kunda `comparison` bloki ⛔ JADVAL CHIZMAYDI, lekin
 * ⛔ YO'QOLMAYDI ham: u ⛔ NOMLANGAN HOLAT ko'rsatadi («Bu kun uchun
 * daftar yuklanmagan») va keyingi qadamni beradi (§14.7 bo'sh holat 6 —
 * fazadagi YAGONA `action` li bo'sh holat).
 *
 * ⛔ Blokni yashirish adminga «solishtirish kerak emas» bo'lib
 *    o'qilardi; «hamma farq 0» jadvali esa undan ham yomon —
 *    ⛔ MUVAFFAQIYATLI solishtiruv bo'lib ko'rinardi, qog'ozga chiqardi
 *    va TASDIQLANARDI (⚠ o'sha amalning nomi bu faylda LITERAL
 *    yozilmaydi — darvoza xom `grep` bilan o'lchaydi va izohdagi nusxa
 *    uni o'ziga qarshi qo'yardi),
 *    ya'ni parallel rejimning butun maqsadi (SC#5) jimgina yo'qolardi
 *    (§10.6, D-10). Qaror `compare-table.tsx` ning ICHIDA yashaydi —
 *    sahifa u yerga ⛔ ikkinchi shart yozmaydi.
 *
 * -----------------------------------------------------------------------
 * ⛔ 4. KUN ⛔ BIR MARTA TANLANADI VA PROP BO'LIB UZATILMAYDI
 * -----------------------------------------------------------------------
 * `<CompareDayPicker/>` sahifada ⛔ AYNAN BIR MARTA; daftar bloki ham,
 * jadval ham kunni `useCompareDay()` HOOKIDAN oladi (`/reports` dagi
 * `useReportPeriod()` naqshi). Propga o'tkazish sahifa bilan blok
 * orasida ⛔ UCHINCHI HAQIQAT MANBAINI tug'dirardi va bir kun ular
 * jimgina ajralib ketardi.
 *
 * ⚠ Bu fayl hookni FAQAT eksport nishoni uchun chaqiradi — u ham AYNI
 *   kalitdan o'qiydi, ya'ni ikkinchi so'rov YUBORILMAYDI.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 5. EKSPORT DAFTARSIZ KUNDA ⛔ O'CHIRILGAN (§12.6)
 * -----------------------------------------------------------------------
 * `.xlsx` ning pastida ⛔ IKKI BO'SH TASDIQ QATORI bor (D-19), ya'ni u
 * qog'ozga chiqadigan hujjat. Daftarsiz kunning fayli «hamma farq 0»
 * varaqasi bo'lib chop etilardi va ekrandagi taqiq ⛔ FAYLDA AYLANIB
 * O'TILARDI. Shuning uchun nishon `has_ledger` ga bog'langan.
 *
 * ⛔ `aria-disabled`, `disabled` EMAS [MEROS: 05-UI-SPEC §13.3]: tugma
 *    fokusni yo'qotmaydi va sabab ekranda qoladi.
 *
 * -----------------------------------------------------------------------
 * ⛔ 6. QOG'OZDAGI TASDIQ AMALI TIZIMDA TAKRORLANMAYDI (D-19, §10.7)
 * -----------------------------------------------------------------------
 * Raqamli tasdiq mexanizmi YO'Q va tugma uni ⛔ BORDEK ko'rsatardi;
 * «tasdiqlangan» holati esa bazada ⛔ DALILSIZ yozuv bo'lardi. Tizim
 * qog'ozda nima bo'lganini BILMAYDI va bilmagan narsasini ko'rsatmaydi.
 * Bo'sh qatorlar faqat `.xlsx` ning pastida (§12.6).
 *
 * -----------------------------------------------------------------------
 * ⛔ 7. HUQUQ KO'ZGUSI — SO'ROVDAN OLDIN
 * -----------------------------------------------------------------------
 * `report_view` yo'q sessiyada birorta so'rov UMUMAN ketmaydi. ⚠ Haqiqiy
 * nazorat SERVERDA (`require_permission`, 08-16). ⛔ Yangi huquq
 * QO'SHILMAYDI: `report_view` ikkala matritsada ham ALLAQACHON bor va bu
 * faza `rbac.ts` ↔ `rbac.py` juftligiga UMUMAN TEGMAYDI (M-6).
 *
 * ⚠ `Suspense` ⛔ MAJBURIY: ish maydoni `?day=` ni `nuqs` orqali KLIENTDA
 *   o'qiydi va chegara bo'lmasa Next 16 butun marshrutni statik
 *   prerender ro'yxatidan chiqarib `build` ni YIQITADI (`/reports`,
 *   `/reconciliation` va `/billing` da o'lchangan).
 * =============================================================================
 */

export default function ComparePage() {
  const t = useTranslations();
  const { principal } = useAuthStore();

  if (!hasPermission(principal?.roles ?? [], "report_view")) {
    return <ForbiddenNotice />;
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold tracking-tight">
        {t("compare.title")}
      </h1>

      <Suspense
        fallback={
          <BrandLoader />
        }
      >
        <CompareWorkspace />
      </Suspense>
    </div>
  );
}

/* --- Ish maydoni ---------------------------------------------------------- */

function CompareWorkspace() {
  /*
   * ⛔ HOOK FAQAT EKSPORT NISHONI UCHUN (yuqoridagi 4-band). Bloklar
   *   kunni O'ZLARI shu hookdan oladi — bu yerdan propga uzatilmaydi.
   */
  const { day } = useCompareDay();
  const report = useThreeWayReport(day);

  return (
    /* ⛔ `gap-8` = 32px — uchala blok orasidagi YAGONA masofa (§6.1). */
    <div className="flex flex-col gap-8">
      {/*
       * --- A: KUN TANLAGICHI — ⛔ BOSHQARUV, ro'yxat emas ------------------
       *
       * ⛔ Shu sababdan u mazmun juftligining YAGONA istisnosi
       *   (`CONTENT_EXEMPT`) va istisnolar to'plamining O'LCHAMI darvozada
       *   alohida assert bilan qulflangan.
       */}
      <section data-compare-block="day">
        <CompareDayPicker />
      </section>

      {/* --- B: DAFTAR — ⛔ fazadagi YAGONA yozuv amali (D-17) -------------- */}
      <section data-compare-block="ledger">
        <LedgerImport />
      </section>

      {/*
       * --- C: SOLISHTIRUV — ⛔ SHARTSIZ (yuqoridagi 3-band) ----------------
       *
       * ⛔ Eksport tugmasi blok ICHIDA, jadvaldan KEYIN: u o'sha blokning
       *   amali. Sahifa darajasidagi yolg'iz tugma «qaysi hisobot
       *   yuklanadi?» degan javobsiz savolni tug'dirardi (§12.1).
       */}
      <section className="flex flex-col gap-3" data-compare-block="comparison">
        <CompareTable />
        <div>
          <ExportButton
            day={day}
            kind="three-way"
            unavailable={report.data?.has_ledger !== true}
          />
        </div>
      </section>
    </div>
  );
}
