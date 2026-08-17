"use client";

import { useFormatter, useTranslations } from "next-intl";

import { VarianceCell } from "@/components/billing/variance-cell";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useUsersQuery } from "@/lib/queries";
import { useShiftReport } from "@/lib/shift-queries";

/*
 * =============================================================================
 * E BLOKI — SMENA VA FARQ (§11.5, CASH-04, D-26).
 *
 * ⛔ BU BLOK IKKALA KUNDA HAM CHIZILADI (§11.2, E qatori): smena kun
 *    ICHIDA yopiladi, ya'ni «bugun» uchun ham yopilgan smena bo'lishi
 *    mumkin. Shuning uchun u G-25 ning ikkala to'plamida ham bor va
 *    kesishmaning bir a'zosi.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ YOZUV YUZASI AYNAN NOL — VA U TO'PLAM TENGLIGI BILAN O'LCHANADI
 * -----------------------------------------------------------------------
 * D-26: farq ⛔ HECH QACHON avtomatik to'g'rilanmaydi va qo'lda
 * to'g'rilash yo'li ham 6-fazada OCHILMAYDI — uning marshruti serverda
 * umuman yozilmagan. Shuning uchun bu blokda tasdiqlash, izohlash,
 * kechirish yoki tuzatish tugmalarining ⛔ BIRORTASI HAM yo'q, va
 * `variance-list.test.tsx` buni ⛔ INTERAKTIV ELEMENTLAR TO'PLAMINING
 * TENGLIGI bilan tekshiradi: yangi tugma qo'shilsa darvoza O'ZI qizaradi
 * (D-32). Bitta nomni inkor qiladigan da'vo faqat O'SHA nomni ushlardi.
 *
 * ⛔ FARQ SERVERDA HISOBLANGAN — klientda AYIRISH QILINMAYDI. 05-14 ning
 *    darsi: klientdagi qayta hisob xato bo'lib emas, ⛔ IKKINCHI JAVOB
 *    bo'lib chiqadi va nizoda qaysi biri to'g'ri ekani noaniq bo'lardi.
 *
 * -----------------------------------------------------------------------
 * ⚠ SMENASIZ TO'LOVLAR — NOMLANGAN QATOR, JIM YO'QOLISH EMAS
 * -----------------------------------------------------------------------
 * `shift_id IS NULL` bo'lgan to'lovlar birorta kassir qutisiga
 * tushmagan, ya'ni ular farq hisobiga ⛔ KIRMAYDI — va bu TO'G'RI.
 * Ammo ular ⛔ PUL, va jadvaldan tushirib qoldirish «o'lchanmagan
 * miqdorni nol deb yozish» bo'lardi (D-14 ruhi). Shuning uchun ular
 * jadval ostida ALOHIDA qator bo'lib, sanog'i VA summasi bilan
 * ko'rinadi — ⛔ nol bo'lganda ham.
 *
 * ⛔ KASSIR ISMI KLIENTDA JOIN QILINADI (§5.5, C-10): `GET /users`
 *    mavjud va audit qilingan marshrut; moliyaviy javobga ism maydoni
 *    qo'shilmaydi.
 *
 * ⛔ FARQ CHEGARASI VA OGOHLANTIRISHI YO'Q (§11.5): chegara
 *    kelishilmagan va u bozor bo'yicha sozlanadigan bo'lishi kerak —
 *    8-faza egasi.
 * =============================================================================
 */

export function VarianceList({ day }: { day: string }) {
  const t = useTranslations();
  const format = useFormatter();
  const report = useShiftReport(day);
  const users = useUsersQuery();

  const rows = report.data?.rows ?? [];

  const cashierNames = new Map(
    (users.data?.items ?? []).map(
      (user) => [user.id, user.full_name ?? user.phone] as const,
    ),
  );

  return (
    /*
     * ⛔ G-25 (b): atribut eng tashqi elementda va HAR holatda — bo'sh
     *    natija ham NATIJA.
     */
    <div className="flex flex-col gap-3" data-billing-content="shifts">
      <h2 className="text-sm font-semibold">{t("billing.shiftsTitle")}</h2>

      {report.isPending ? (
        <div aria-busy="true" role="status">
          <span className="sr-only">{t("common.loading")}</span>
          <Skeleton className="h-24" />
        </div>
      ) : null}

      {report.isError ? (
        <p
          className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
          role="alert"
        >
          {t("errors.loadFailedBody")}
        </p>
      ) : null}

      {report.data !== undefined && rows.length === 0 ? (
        /* ⛔ BO'SH HOLAT №7 (§13.8) — amali YO'Q, bo'sh `<div>` ham emas. */
        <EmptyState
          description={t("billing.emptyShiftsHint")}
          title={t("billing.emptyShifts")}
        />
      ) : null}

      {rows.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs text-text-muted">
                <th className="py-2 pr-3 font-medium" scope="col">
                  {t("collect.shiftTitle")}
                </th>
                <th className="py-2 pr-3 font-medium" scope="col">
                  {t("roles.cashier")}
                </th>
                <th className="py-2 pr-3 font-medium" scope="col">
                  {t("billing.declared")}
                </th>
                <th className="py-2 pr-3 font-medium" scope="col">
                  {t("billing.systemTotal")}
                </th>
                <th className="py-2 font-medium" scope="col">
                  {t("billing.variance")}
                </th>
              </tr>
            </thead>
            <tbody>
              {/*
                * Qator hover foni (§12.8). `VarianceCell` pilli o'z fonini
                * USTIDA saqlaydi — hover bg uni bosib qolmaydi (u qator
                * emas, inline element).
                */}
              {rows.map((row) => (
                <tr
                  className="border-b border-border transition-colors hover:bg-surface-muted"
                  key={row.id}
                >
                  <td className="py-2 pr-3 font-mono text-xs tabular-nums">
                    {format.dateTime(new Date(row.opened_at), {
                      timeStyle: "short",
                    })}
                    {" — "}
                    {/*
                     * ⚠ `closed_at === null` — smena HALI OCHIQ. Bu
                     *   normal holat va u nol bilan to'ldirilmaydi.
                     */}
                    {row.closed_at === null
                      ? "…"
                      : format.dateTime(new Date(row.closed_at), {
                          timeStyle: "short",
                        })}
                  </td>
                  <td className="py-2 pr-3 text-text-muted">
                    {cashierNames.get(row.cashier_id) ?? ""}
                  </td>
                  <td className="py-2 pr-3 font-mono tabular-nums">
                    {/* Ochiq smenada deklaratsiya hali YO'Q — to'qilmaydi. */}
                    {row.declared_soum === null
                      ? "—"
                      : format.number(row.declared_soum)}
                  </td>
                  <td className="py-2 pr-3 font-mono tabular-nums">
                    {format.number(row.system_soum)}
                  </td>
                  <td className="py-2">
                    {/* ⛔ Uch kanal — `variance-cell.tsx` da. */}
                    <VarianceCell soum={row.variance_soum} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {/*
       * ⛔ SMENASIZ TO'LOVLAR — SHARTSIZ QATOR. Nol bo'lganda ham
       *    ko'rinadi: «smenasiz to'lov yo'q» bilan «bu son umuman
       *    hisoblanmayapti» bir xil ko'rinmasligi kerak.
       */}
      {report.data !== undefined ? (
        <p className="text-xs text-text-muted">
          {t("billing.shiftlessPayments")}:{" "}
          <span className="font-mono tabular-nums">
            {format.number(report.data.shiftless_payment_count)}
          </span>{" "}
          ·{" "}
          <span className="font-mono tabular-nums">
            {format.number(report.data.shiftless_payment_soum)}
          </span>{" "}
          {t("billing.amountUnit")}
        </p>
      ) : null}
    </div>
  );
}
