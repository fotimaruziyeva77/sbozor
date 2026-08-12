"use client";

import { useFormatter, useTranslations } from "next-intl";

import { CaseStatusBadge } from "@/components/reconciliation/case-status-badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { CASE_STATUSES } from "@/lib/api-types";
import type { CaseStatusValue } from "@/lib/api-types";
import type {
  CaseList as CaseListResponse,
  CaseRow,
} from "@/lib/reconciliation-queries";
import { useReconciliationCases } from "@/lib/reconciliation-queries";

/*
 * =============================================================================
 * D BLOKI — NOMUVOFIQLIK NAVBATI (RECON-02, §9.2).
 *
 * -----------------------------------------------------------------------
 * ⛔ 1. «NOMUVOFIQLIK OCHISH» TUGMASI ⛔ QURILMAYDI
 * -----------------------------------------------------------------------
 * Navbat `recon.open` cron'ida ⛔ AVTOMATIK va sinf A uchun kechikish
 * chegarasi bilan tug'iladi. Qo'lda ochish:
 *   (1) ⛔ CHEGARANI AYLANIB O'TARDI — direktor bugungi hisobga navbat
 *       ochib, ertaga to'lov kelganda uni YOPISHGA majbur bo'lardi
 *       (aynan o'sha shovqin uchun chegara qo'yilgan);
 *   (2) ⛔ IDEMPOTENTLIKNI BUZARDI — qisman UNIQUE indeks qo'lda va cron
 *       urinishlari orasida POYGA yaratardi;
 *   (3) direktorning haqiqiy ehtiyoji «buni tezroq ko'ring», ya'ni
 *       MAS'UL biriktirish — yangi qator emas.
 *
 * -----------------------------------------------------------------------
 * ⛔ 2. HOLAT O'ZGARTIRISH BOSHQARUVI BU YERDA YO'Q
 * -----------------------------------------------------------------------
 * Hukm — tafsilot dialogining ishi va u ALOHIDA huquq ostida. Bu blok
 * ⛔ SOF O'QISH: yozuv yuzasi AYNAN NOL.
 *
 * -----------------------------------------------------------------------
 * ⛔ 3. OMMAVIY AMAL ⛔ QURILMAYDI
 * -----------------------------------------------------------------------
 * Ko'p tanlovli ro'yxat direktorga ⛔ BIR BOSISHDA 50 NOMUVOFIQLIKNI
 * yopish imkonini berardi — bu «hammasini tasdiqlash» dan QIMMATROQ
 * xato, chunki natijasi HUKM va u aniqlik ulushini BUZADI. Hech qanday
 * yechim matni ham qolmasdi.
 *
 * ⚠ Bu katalog o'sha taqiqning mexanik skanidan o'tadi va qamrov
 *   dizayn kontraktining E'LONIDAN hosila qilinadi.
 *
 * -----------------------------------------------------------------------
 * ⛔ 4. TO'RT SANOQ NOL BO'LGANDA HAM KO'RINADI
 * -----------------------------------------------------------------------
 * Sikl ⛔ REYESTR ustidan yuradi (D-32), ya'ni «nolmaslarini ko'rsatish»
 * sharti umuman yo'q: yo'qolgan sanoq «bugun hech nima yopilmadi» bilan
 * «hisoblagich ishlamayapti» ni mexanik ravishda bir xil ko'rsatardi.
 *
 * ⛔ AYNAN SHU TO'RT SANOQDAN aniqlik ulushi ham chiqadi — ⛔ IKKINCHI
 *    SO'ROVSIZ. Ikki so'rov ikki lahzani ko'rsatib, ekranda «ikki xil
 *    raqam» tug'dirardi.
 *
 * -----------------------------------------------------------------------
 * ⚠⚠ 5. SOTUVCHI USTUNI ⛔ YO'Q — DIZAYN KONTRAKTIDAN ASOSLI CHETLANISH
 * -----------------------------------------------------------------------
 * Kontrakt bu jadvalga «Sotuvchi (klientda join)» ustunini yozgan, lekin
 * 07-10 ning SHIPLANGAN `CaseRowResponse` ida sotuvchi identifikatori
 * ⛔ UMUMAN YO'Q — qator faqat case, nishon (anomaliya YOKI hisob), sana,
 * holat, mas'ul va ochilish vaqti bilan keladi. Server docstringi buni
 * ochiq aytadi: rasta kodi, sotuvchi va summa navbat qatorida EMAS,
 * chunki ularni ko'chirish navbatni ⛔ IKKINCHI HAQIQAT MANBAIGA
 * aylantirardi.
 *
 * ⛔ SHUNING UCHUN USTUN QO'SHILMAYDI, «—» BILAN HAM: to'qilgan yoki
 *    doim bo'sh ustun 4-fazadagi «bo'sh katak» sinfidagi jim xato
 *    bo'lardi (05-14 darsi). Sotuvchi hisobot bloklarida KO'RINADI va
 *    o'sha yerda u HAQIQIY ma'lumot bilan keladi.
 * =============================================================================
 */

/** Holat -> envelope'dagi ALOHIDA sanoq. ⛔ Yig'indi maydoni YO'Q. */
const STATUS_COUNT: Record<
  CaseStatusValue,
  (data: CaseListResponse) => number
> = {
  new: (data) => data.new_count,
  in_review: (data) => data.in_review_count,
  justified: (data) => data.justified_count,
  unjustified: (data) => data.unjustified_count,
};

export function CaseList({ day }: { day: string }) {
  const t = useTranslations();
  const cases = useReconciliationCases(day, "");

  const rows = cases.data?.rows ?? [];

  return (
    /* ⛔ Atribut ENG TASHQI elementda va HAR holatda — yuklanishda ham. */
    <div className="flex flex-col gap-3" data-recon-content="cases">
      <h2 className="text-lg font-semibold">{t("recon.casesTitle")}</h2>

      {cases.isPending ? (
        <div aria-busy="true" role="status">
          <span className="sr-only">{t("common.loading")}</span>
          <Skeleton className="h-24" />
        </div>
      ) : null}

      {cases.isError ? (
        <p
          className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
          role="alert"
        >
          {t("errors.loadFailedBody")}
        </p>
      ) : null}

      {cases.data !== undefined ? (
        <dl className="flex flex-wrap gap-x-6 gap-y-2 text-sm" role="status">
          {CASE_STATUSES.map((status) => (
            <div className="flex items-center gap-2" key={status}>
              <dt className="order-2 text-xs text-text-muted">
                {t(`recon.caseStatus.${status}`)}
              </dt>
              <dd className="order-1 m-0 font-mono tabular-nums">
                {STATUS_COUNT[status](cases.data as CaseListResponse)}
              </dd>
            </div>
          ))}
        </dl>
      ) : null}

      {cases.data !== undefined && rows.length === 0 ? (
        <EmptyState
          description={t("recon.emptyCasesHint", { date: day })}
          title={t("recon.emptyCases")}
        />
      ) : null}

      {rows.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <caption className="sr-only">{t("recon.casesTitle")}</caption>
            <thead>
              <tr className="border-b border-border text-left text-xs text-text-muted">
                <th className="p-3 font-normal">{t("recon.subjectColumn")}</th>
                <th className="p-3 font-normal">{t("recon.statusColumn")}</th>
                <th className="p-3 font-normal">
                  {t("recon.assigneeColumn")}
                </th>
                <th className="p-3 font-normal">{t("recon.openedColumn")}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <CaseRowView key={row.case_id} row={row} />
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}

function CaseRowView({ row }: { row: CaseRow }) {
  const t = useTranslations();
  const format = useFormatter();

  return (
    <tr className="border-b border-border last:border-b-0">
      <td className="p-3">
        {row.subject_kind === "occupied_unpaid"
          ? t("recon.unpaidTitle")
          : t("recon.unregisteredTitle")}
      </td>
      <td className="p-3">
        <CaseStatusBadge status={row.status} />
      </td>
      <td className="p-3">
        {/*
         * ⛔ MAS'UL — IDENTIFIKATOR, ISM EMAS. Ismni qo'shish uchun
         *   foydalanuvchilar reestrini ham tortish kerak bo'lardi; u
         *   tafsilot dialogi bilan birga keladi (07-16). Bugun `null`
         *   HOLAT sifatida NOMLANADI — bo'sh katak jim xato bo'lardi.
         */}
        {row.assignee_user_id === null ? (
          <span className="text-text-muted">{t("recon.assigneeNone")}</span>
        ) : (
          <span className="font-mono text-xs">
            {row.assignee_user_id.slice(0, 8)}
          </span>
        )}
      </td>
      <td className="p-3">
        {format.dateTime(new Date(row.created_at), { dateStyle: "medium" })}
      </td>
    </tr>
  );
}
