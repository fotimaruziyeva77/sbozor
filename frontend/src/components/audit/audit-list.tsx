"use client";

import { useMemo } from "react";
import { useFormatter, useTranslations } from "next-intl";

import { AuditDiff } from "@/components/audit/audit-diff";
import { useAuditFilters } from "@/components/audit/audit-filters";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import type { AuditEntry } from "@/lib/api-types";
import { isAuditAction, isAuditTable } from "@/lib/api-types";
import { cn } from "@/lib/cn";
import { adminErrorMessageKey, useAuditQuery, useUsersQuery } from "@/lib/queries";

/*
 * =============================================================================
 * AUDIT RO'YXATI — FAQAT O'QISH (D-12, T-01-72).
 *
 * Bu komponentda birorta yozuv yoki o'chirish amali YO'Q va bo'lishi ham
 * mumkin emas: `audit_log` append-only (01-05 da to'rt qatlamli DB himoyasi
 * bilan), ya'ni "tahrirlash" tugmasi baribir xato bilan tugardi va
 * jurnalning o'zgarmasligiga shubha uyg'otardi.
 *
 * Har yozuv KARTA ko'rinishida (topshiriq §7) va D-12 ning to'rt ustuni
 * aniq ko'rinadi:
 *   KIM       -> `actor_label` / foydalanuvchi ismi / tizim
 *   QACHON    -> `at` (Asia/Tashkent) + `business_date`
 *   NIMA      -> `action` + `table_name` (tarjima qilingan)
 *   ESKI->YANGI -> `AuditDiff`
 * =============================================================================
 */

export function AuditList() {
  const t = useTranslations();
  const { filters } = useAuditFilters();
  const auditQuery = useAuditQuery(filters);

  /*
   * "Kim" ustunining manbai IKKI QISMDAN iborat. `GET /audit` javobi
   * `actor_label` ni beradi, lekin ism/telefonni ATAYIN bermaydi — audit
   * javobiga profil maydonlarini qo'shish shaxsiy ma'lumot yuzasini
   * kengaytirardi (01-07 qarori). Shuning uchun ism `GET /users` dan,
   * ID bo'yicha ulanadi; foydalanuvchi topilmasa `actor_label` qoladi.
   */
  const usersQuery = useUsersQuery();
  const actorNames = useMemo(() => {
    const map = new Map<string, string>();
    for (const user of usersQuery.data?.items ?? []) {
      map.set(user.id, user.full_name ?? user.phone);
    }
    return map;
  }, [usersQuery.data]);

  if (auditQuery.isPending) {
    return (
      <p className="text-sm text-text-muted" role="status">
        {t("common.loading")}
      </p>
    );
  }

  if (auditQuery.isError) {
    return (
      <p
        className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger"
        role="alert"
      >
        {t(adminErrorMessageKey(auditQuery.error))}
      </p>
    );
  }

  const entries = auditQuery.data.pages.flatMap((page) => page.items);

  if (entries.length === 0) {
    return <p className="text-sm text-text-muted">{t("audit.emptyState")}</p>;
  }

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-text-muted" role="status">
        {t("audit.resultCount", { count: entries.length })}
      </p>

      <ul aria-label={t("audit.title")} className="flex flex-col gap-3">
        {entries.map((entry) => (
          <li key={entry.id}>
            <AuditCard
              actorName={
                entry.actor_user_id === null
                  ? null
                  : (actorNames.get(entry.actor_user_id) ?? null)
              }
              entry={entry}
            />
          </li>
        ))}
      </ul>

      {auditQuery.hasNextPage ? (
        <div>
          <Button
            disabled={auditQuery.isFetchingNextPage}
            onClick={() => void auditQuery.fetchNextPage()}
            variant="secondary"
          >
            {auditQuery.isFetchingNextPage
              ? t("common.loading")
              : t("audit.loadMore")}
          </Button>
        </div>
      ) : null}
    </div>
  );
}

function AuditCard({
  actorName,
  entry,
}: {
  actorName: string | null;
  entry: AuditEntry;
}) {
  const t = useTranslations();
  const tActions = useTranslations("audit.actions");
  const tTables = useTranslations("audit.tables");
  const format = useFormatter();

  /*
   * Vaqt `next-intl` ning formatlagichi bilan chiqadi — mintaqa
   * `src/i18n/request.ts` da BITTA joyda (`Asia/Tashkent`) belgilangan va
   * provayder orqali klientga o'tadi. Sanani qo'lda formatlash har
   * komponentda mintaqani qayta e'lon qilishga majbur qilardi va bir kun
   * kimdir UTC'ni ko'rsatib qo'yardi — bu esa yozuvni noto'g'ri
   * biznes-kunga bog'lardi (FOUND-05).
   */
  const at = format.dateTime(new Date(entry.at), {
    dateStyle: "medium",
    timeStyle: "medium",
  });

  // Noma'lum qiymat XOM holda ko'rinadi: u DB dagi texnik identifikator
  // (keyingi fazalarning yangi hodisasi yoki jadvali) va uni yashirish
  // jurnalda tushunarsiz bo'shliq qoldirardi.
  const actionLabel = isAuditAction(entry.action)
    ? tActions(entry.action)
    : entry.action;
  const tableLabel = isAuditTable(entry.table_name)
    ? tTables(entry.table_name)
    : entry.table_name;

  const isDbTrigger = entry.source === "db_trigger";

  return (
    <Card>
      <CardHeader className="gap-2 pb-3">
        <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
          {/* NIMA */}
          <span className="text-base font-medium">
            <span className="sr-only">{t("audit.what")}: </span>
            {actionLabel} · {tableLabel}
          </span>

          {/* QACHON */}
          <span className="text-sm text-text-muted">
            <span className="sr-only">{t("audit.when")}: </span>
            {at}
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-text-muted">
          {/* KIM — D-16: ism/telefon tarjima qilinmaydi. */}
          <span>
            {t("audit.who")}:{" "}
            <span className="font-medium text-text">
              {actorName ?? entry.actor_label ?? t("audit.systemActor")}
            </span>
          </span>

          <span>
            {t("audit.businessDate")}: {entry.business_date}
          </span>

          <span
            className={cn(
              "inline-flex items-center rounded-full px-2 py-0.5 text-xs",
              isDbTrigger ? "bg-surface-muted text-text" : "bg-accent/10 text-accent",
            )}
          >
            <span className="sr-only">{t("audit.sourceLabel")}: </span>
            {isDbTrigger ? t("audit.sourceDbTrigger") : t("audit.sourceApp")}
          </span>
        </div>
      </CardHeader>

      {/* ESKI -> YANGI */}
      <CardContent>
        <AuditDiff entry={entry} />
      </CardContent>
    </Card>
  );
}
