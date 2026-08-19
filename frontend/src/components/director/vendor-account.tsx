"use client";

import { useState } from "react";
import { useFormatter, useLocale, useNow, useTimeZone } from "next-intl";

import { businessDayIn, shiftIsoDay } from "@/components/snapshots/day-picker";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { bucketOf } from "@/lib/debt-aging";
import { daysBetweenIsoDays, formatBusinessDay } from "@/lib/format-day";
import { formatAmount, formatSoum } from "@/lib/format-number";
import { useReceivablesReport } from "@/lib/report-queries";

/*
 * =============================================================================
 * SOTUVCHI HISOBI — `Sbozor Direktor - Sotuvchi.dc.html`.
 *
 * Manba MCP orqali o'qildi (claude.ai/design `7bb95baa…`, 2026-08-19).
 * Dizayn beshta blok beradi: profil, qarz tarkibi, TO'LOV TARIXI,
 * kechikish naqshi, maxfiylik eslatmasi.
 *
 * ⛔⛔ TO'LOV TARIXI QURILMADI — VA BU YASHIRILMAYDI.
 *
 *     Sababi mexanik, uslubiy emas: SERVERDA sotuvchi bo'yicha to'lov
 *     tarixini beradigan endpoint YO'Q. Tekshirildi (2026-08-19):
 *       * `GET /billing/charges?day=` — faqat BIR kun, sotuvchi filtri yo'q;
 *       * `GET /payments/recent` — chaqiruvchining O'Z smenasi, parametrsiz;
 *       * `GET /reports/debtors` — qoldiq va eng eski sana, tarix emas.
 *
 *     ⛔ Ro'yxatni «yasash» mumkin edi — masalan kunlik hisobotlarni
 *        aylanib chiqib sotuvchi bo'yicha filtrlash. QILINMADI: bu
 *        o'ttizta so'rov va serverning javobiga ZID bo'lishi mumkin
 *        bo'lgan ikkinchi hisoblash yo'li bo'lardi.
 *
 *     Shuning uchun o'sha joyda BO'SHLIQ NOMLANADI: nima yo'qligi va
 *     nima kerakligi yozilib turadi. Bu «keyin qilamiz» emas —
 *     tekshiruvchi ham, direktor ham nimani ko'rmayotganini BILADI.
 *
 * ⛔ MAXFIYLIK: sotuvchining ismi va telefoni FAQAT `vendor_view`
 *    huquqi bilan ko'rinadi va u direktorda bor, kassirda YO'Q. Bu
 *    sahifa `report_view` ostida — ikkalasi ham direktorda.
 * =============================================================================
 */

/** Qarzdorlik oynasi — oxirgi 90 kun (yosh guruhlari uchun yetarli). */
const WINDOW_DAYS = 90;

export function VendorAccount() {
  const format = useFormatter();
  const locale = useLocale();
  const timeZone = useTimeZone() ?? "Asia/Tashkent";
  const now = useNow();

  const [query, setQuery] = useState("");

  const todayIso = businessDayIn(timeZone, now);
  const to = shiftIsoDay(todayIso, -1);
  const from = shiftIsoDay(to, -(WINDOW_DAYS - 1));

  const debtors = useReceivablesReport({ from, to });

  const rows = debtors.data?.rows ?? [];
  const needle = query.trim().toLowerCase();
  /*
   * ⛔ Qidiruv KLIENTDA: server bu endpointda qidiruv parametri bermaydi
   *    va qatorlar soni bir bozor uchun kichik. Serverga qidiruv
   *    qo'shilganda bu blok o'sha parametrga o'tadi.
   */
  const filtered =
    needle === ""
      ? rows
      : rows.filter((row) =>
          (row.vendor_name ?? "").toLowerCase().includes(needle),
        );

  return (
    <div className="flex flex-col gap-4">
      <header>
        <div className="dir-eyebrow">Sotuvchi hisobi</div>
        <h1 className="dir-title">Qarzdorlik bo&apos;yicha sotuvchilar</h1>
        <p className="dir-tile-sub">
          {debtors.data === undefined
            ? ""
            : `${formatBusinessDay(format, debtors.data.from_date, locale)} — ${formatBusinessDay(format, debtors.data.to_date, locale)}`}
        </p>
      </header>

      <Input
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Sotuvchi ismi bo'yicha qidirish"
        value={query}
      />

      {debtors.isPending ? (
        <Skeleton className="dir-trend-skeleton" />
      ) : filtered.length === 0 ? (
        <EmptyState
          description={
            needle === ""
              ? "Bu davrda qarzdor sotuvchi yo'q. Nol ham javob — bu xato emas."
              : "Bu nom bo'yicha qarzdor topilmadi."
          }
          title="Qarzdor yo'q"
        />
      ) : (
        <div className="flex flex-col gap-3">
          {filtered.map((row) => {
            const bucket = bucketOf(row, todayIso);
            const days =
              row.oldest_debt_date === null
                ? null
                : daysBetweenIsoDays(row.oldest_debt_date, todayIso);

            return (
              <Card key={row.vendor_id ?? row.stall_codes.join("-")}>
                <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-3">
                  <div>
                    <h2 className="dir-trend-title">
                      {row.vendor_name ?? "Ism ko'rsatilmagan"}
                    </h2>
                    <p className="dir-tile-note">
                      Rastalar: {row.stall_codes.join(", ")}
                    </p>
                  </div>
                  {bucket === null ? null : (
                    <Badge
                      tone={
                        bucket === "b90"
                          ? "danger"
                          : bucket === "b61"
                            ? "warning"
                            : "muted"
                      }
                    >
                      {days === null ? "" : `${days} kun`}
                    </Badge>
                  )}
                </CardHeader>

                <CardContent className="flex flex-col gap-3">
                  <div className="flex flex-wrap items-baseline gap-3">
                    <p
                      className={
                        row.outstanding_soum > 0
                          ? "dir-tile-value dir-tile-value-danger"
                          : "dir-tile-value"
                      }
                    >
{formatSoum(format, row.outstanding_soum, locale)}
                    </p>
                    {row.outstanding_soum < 0 ? (
                      <span className="dir-tile-note">
                        Ortiqcha to&apos;lov — avans
                      </span>
                    ) : null}
                  </div>

                  <p className="dir-tile-note">
                    {row.oldest_debt_date === null
                      ? "Eng eski qarz sanasi o'lchanmagan"
                      : `Eng eski qarz: ${formatBusinessDay(format, row.oldest_debt_date, locale)}`}
                  </p>

                  {/*
                   * ⛔⛔ BO'SHLIQ NOMLANADI — modul izohining asosiy bandi.
                   *     Dizaynda bu joyda TO'LOV TARIXI turadi; serverda
                   *     uni beradigan endpoint yo'q va soxta ro'yxat
                   *     chizilmaydi.
                   */}
                  <div className="audit-source">
                    <Badge tone="muted">Yo&apos;q</Badge>
                    <p className="dir-tile-note">
                      To&apos;lov tarixi bu yerda ko&apos;rsatilmaydi: serverda
                      sotuvchi bo&apos;yicha to&apos;lov ro&apos;yxatini
                      beradigan yo&apos;l hali yo&apos;q. Mavjud yo&apos;llar
                      bir kunlik yoki kassirning o&apos;z smenasiga
                      tegishli — ulardan tarix yasash serverning javobiga
                      zid bo&apos;lishi mumkin edi.
                    </p>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
