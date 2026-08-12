"use client";

import { Suspense } from "react";
import { useTranslations } from "next-intl";

import { CaseList } from "@/components/reconciliation/case-list";
import {
  ReconciliationDayPicker,
  useReconciliationDay,
} from "@/components/reconciliation/day-picker";
import { DeliveryPlaceholder } from "@/components/reconciliation/delivery-placeholder";
import { HitRateCard } from "@/components/reconciliation/hit-rate-card";
import { UnpaidList } from "@/components/reconciliation/unpaid-list";
import { UnregisteredList } from "@/components/reconciliation/unregistered-list";
import { useAuthStore } from "@/lib/auth-store";
import { hasPermission } from "@/lib/rbac";

/*
 * =============================================================================
 * Y-1 + Y-2 + Y-4 — KUNLIK NOMUVOFIQLIK HISOBOTI (RECON-01/02, BOT-04).
 *
 * ⛔⛔ FAZANING ENG YUQORI USTUVORLIKDAGI YUZASI: direktor aynan shu
 *     ekranda «band, lekin to'lovsiz» ni KO'RADI.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 1. BLOK TO'PLAMI KUNGA QARAB — VA U TO'PLAM TENGLIGI BILAN
 *     QULFLANGAN
 * -----------------------------------------------------------------------
 *   `day = bugun`  -> {kun tanlagichi, yetkazilganlik}
 *   `day < bugun`  -> oltala blok
 *   kesishma       -> {kun tanlagichi, yetkazilganlik}
 *
 * ⛔ `day = bugun` DA TO'RT BLOK ⛔ CHIZILMAYDI — bo'sh EMAS, ⛔ YO'Q:
 *
 *   (a) ular bugun ⛔ MAVJUD EMAS: hisob D+1 04:10 da, navbat D+1
 *       04:25 da tug'iladi. Bo'sh ro'yxat «bugun nomuvofiqlik yo'q»
 *       degan ⛔ SOXTA IJOBIY javob bo'lardi va u eng yomon xato —
 *       direktorni XOTIRJAM qilardi;
 *   (b) yetkazilganlik esa BUGUN ⛔ KERAK: kvitansiya HOZIR ketadi va
 *       «xabar kelmadi» nizosi O'SHA KUNI chiqadi.
 *
 * ⛔ «CHIZILMAYDI» DEGANI ⛔ DOM'DA UMUMAN YO'Q. Blokni ko'rinmas qilib
 *    qoldirish YARAMAYDI: darvoza blok to'plamining ⛔ TENGLIGI bilan
 *    o'lchaydi va yashirilgan blok to'plamda ⛔ QOLARDI.
 *    ⚠ Yashirish usullarining nomlari bu izohda LITERAL yozilmaydi.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 2. BU FAYL MAZMUN ATRIBUTINI ⛔ HECH QACHON YOZMAYDI
 * -----------------------------------------------------------------------
 * ⚠ Atributning NOMI ham bu faylda uchramaydi — uning yo'qligi mexanik
 *   `grep` darvozasi (`0`) bilan o'lchanadi, ya'ni izohdagi nusxa
 *   darvozani o'ziga qarshi qo'yardi.
 *
 * Atribut ⛔ RO'YXAT KOMPONENTINING O'ZIDA. Sabab O'LCHANGAN: faqat blok
 * atributlarini ko'radigan darvozani bo'sh o'ram ⛔ MUKAMMAL qondirardi
 * va butun yuza ⛔ CHIZILMAGAN holda faza YASHIL qaytardi. Agar atribut
 * shu faylda bo'lsa, sahifa o'zining false-green iga o'zi yo'l ochardi.
 *
 * -----------------------------------------------------------------------
 * ⛔ 3. BIRLASHTIRILGAN JAMI YO'Q
 * -----------------------------------------------------------------------
 * Ikki sinf ikki blokda va ular orasida ularning sonini birlashtirgan
 * ⛔ BIRORTA element yo'q. Bloklar `2xl` (32px) bilan ajratilgan va
 * ⛔ HECH QACHON bir qatorda emas.
 *
 * -----------------------------------------------------------------------
 * ⛔ 4. HUQUQ KO'ZGUSI — SO'ROVDAN OLDIN
 * -----------------------------------------------------------------------
 * `report_view` yo'q sessiyada birorta so'rov UMUMAN ketmaydi. ⚠ Haqiqiy
 * nazorat SERVERDA — beshala marshrut ham `require_permission` ostida.
 *
 * ⚠ `Suspense` ⛔ MAJBURIY: ish maydoni `?day=` ni `nuqs` orqali
 *   KLIENTDA o'qiydi va chegara bo'lmasa Next 16 butun marshrutni
 *   statik prerender ro'yxatidan chiqarib `build` ni yiqitadi.
 *
 * ⛔ 5. DAVR TANLAGICHI, EKSPORT, DIAGRAMMA VA HOLAT FILTRI YO'Q —
 *    8-fazaning hisobot yuzasi.
 * =============================================================================
 */

export default function ReconciliationPage() {
  const t = useTranslations();
  const { principal } = useAuthStore();

  if (!hasPermission(principal?.roles ?? [], "report_view")) {
    return (
      <p
        className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
        role="alert"
      >
        {t("errors.forbidden")}
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold tracking-tight">
        {t("recon.title")}
      </h1>

      <Suspense
        fallback={
          <p className="text-sm text-text-muted" role="status">
            {t("common.loading")}
          </p>
        }
      >
        <ReconciliationWorkspace />
      </Suspense>
    </div>
  );
}

/* --- Ish maydoni ---------------------------------------------------------- */

function ReconciliationWorkspace() {
  const selection = useReconciliationDay();

  return (
    /* ⛔ `gap-8` = 32px — oltala blok orasidagi YAGONA masofa. */
    <div className="flex flex-col gap-8">
      {/* --- A: KUN TANLAGICHI — ikkala kunda ham ------------------------- */}
      <section data-recon-block="day">
        <ReconciliationDayPicker />
      </section>

      {/*
       * --- B…E: HISOBOT BLOKLARI — ⛔ FAQAT `day < bugun` ----------------
       *
       * ⛔ Ikki sinf IKKI ALOHIDA blokda va ular orasida yig'indi YO'Q.
       */}
      {selection.isToday ? null : (
        <>
          <section data-recon-block="unpaid">
            <UnpaidList day={selection.day} />
          </section>

          <section data-recon-block="unregistered">
            <UnregisteredList day={selection.day} />
          </section>

          <section data-recon-block="cases">
            <CaseList day={selection.day} />
          </section>

          <section data-recon-block="hitrate">
            <HitRateCard day={selection.day} />
          </section>
        </>
      )}

      {/*
       * --- F: XABAR YETKAZILISHI — ⛔ IKKALA KUNDA HAM -------------------
       *
       * Kesishmaning ikkinchi a'zosi: kvitansiya HOZIR ketadi, ya'ni
       * bugungi holat direktorga BUGUN kerak (yuqoridagi 1(b) bandi).
       */}
      <section data-recon-block="delivery">
        <DeliveryPlaceholder day={selection.day} />
      </section>
    </div>
  );
}
