"use client";

import { FilterX } from "lucide-react";
import { useTranslations } from "next-intl";
import { parseAsString, useQueryStates } from "nuqs";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AUDIT_ACTIONS, AUDIT_TABLES } from "@/lib/api-types";
import type { AuditFilters } from "@/lib/queries";
import { useUsersQuery } from "@/lib/queries";

/*
 * Audit filtrlari (D-12 minimal to'plami: sana oralig'i, amal turi, aktor,
 * jadval nomi).
 *
 * HOLAT URL'DA, komponentda emas. Sabab amaliy: nazoratchi topgan
 * nomuvofiqlikni "shu havolaga qara" deb yuboradi, direktor esa aynan
 * o'sha filtrlangan ko'rinishni ochadi. Komponent holatida bu imkonsiz
 * bo'lardi va sahifa yangilanganda filtr ham yo'qolardi.
 *
 * Bo'sh qiymat URL'dan butunlay chiqib ketadi (`withDefault("")` +
 * nuqs'ning standart `clearOnDefault` xulqi), ya'ni havola qisqa va
 * o'qiladigan bo'lib qoladi.
 *
 * XAVFSIZLIK: filtr qiymatlari foydalanuvchi nazoratidagi kirish, lekin
 * ular so'rov PARAMETRI sifatida ketadi va serverda `AuditQuery` pydantic
 * modeli bilan tekshiriladi (noto'g'ri sana yoki UUID -> 422). Natija
 * baribir `audit_read` RLS policy'si bilan o'z bozoriga cheklangan
 * (T-01-54), ya'ni filtr orqali begona bozor yozuvini "so'rab olish"
 * mumkin emas.
 */

/** Filtrlarning URL nomlari — havolada shu ko'rinishda turadi. */
const auditFilterParsers = {
  from: parseAsString.withDefault(""),
  to: parseAsString.withDefault(""),
  actor: parseAsString.withDefault(""),
  action: parseAsString.withDefault(""),
  table: parseAsString.withDefault(""),
};

const EMPTY_URL_FILTERS = {
  from: "",
  to: "",
  actor: "",
  action: "",
  table: "",
};

/**
 * URL holatini `useAuditQuery()` kutadigan shaklga o'giradi.
 *
 * Filtr paneli ham, ro'yxat ham SHU hookdan o'qiydi — holat prop bo'lib
 * uzatilmaydi, ya'ni ikkovi hech qachon ajralib qola olmaydi.
 */
export function useAuditFilters(): {
  filters: AuditFilters;
  isEmpty: boolean;
} {
  const [urlFilters] = useQueryStates(auditFilterParsers);

  return {
    filters: {
      from: urlFilters.from,
      to: urlFilters.to,
      actorUserId: urlFilters.actor,
      action: urlFilters.action,
      tableName: urlFilters.table,
    },
    isEmpty: Object.values(urlFilters).every((value) => value === ""),
  };
}

export function AuditFiltersPanel() {
  const t = useTranslations();
  const tActions = useTranslations("audit.actions");
  const tTables = useTranslations("audit.tables");
  const [urlFilters, setUrlFilters] = useQueryStates(auditFilterParsers);

  // Aktor ro'yxati: `AUDIT_VIEW` huquqi bo'lgan uchala rolda `USER_VIEW`
  // ham bor (01-06 matritsasi), ya'ni bu so'rov hech qachon 403 bermaydi.
  const usersQuery = useUsersQuery();

  const isEmpty = Object.values(urlFilters).every((value) => value === "");

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-border bg-surface p-4">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <Field htmlFor="audit-from" label={t("audit.filterFrom")}>
          <Input
            id="audit-from"
            onChange={(event) =>
              void setUrlFilters({ from: event.target.value })
            }
            type="date"
            value={urlFilters.from}
          />
        </Field>

        <Field htmlFor="audit-to" label={t("audit.filterTo")}>
          <Input
            id="audit-to"
            onChange={(event) => void setUrlFilters({ to: event.target.value })}
            type="date"
            value={urlFilters.to}
          />
        </Field>

        <Field htmlFor="audit-action" label={t("audit.filterAction")}>
          <Select
            id="audit-action"
            onChange={(value) => void setUrlFilters({ action: value })}
            value={urlFilters.action}
          >
            <option value="">{t("audit.filterActionAll")}</option>
            {AUDIT_ACTIONS.map((action) => (
              <option key={action} value={action}>
                {tActions(action)}
              </option>
            ))}
          </Select>
        </Field>

        <Field htmlFor="audit-actor" label={t("audit.filterActor")}>
          <Select
            id="audit-actor"
            onChange={(value) => void setUrlFilters({ actor: value })}
            value={urlFilters.actor}
          >
            <option value="">{t("audit.filterActorAll")}</option>
            {/* D-16: ism va telefon DB kontenti — tarjima qilinmaydi. */}
            {(usersQuery.data?.items ?? []).map((user) => (
              <option key={user.id} value={user.id}>
                {user.full_name ?? user.phone}
              </option>
            ))}
          </Select>
        </Field>

        <Field htmlFor="audit-table" label={t("audit.filterTable")}>
          <Select
            id="audit-table"
            onChange={(value) => void setUrlFilters({ table: value })}
            value={urlFilters.table}
          >
            <option value="">{t("audit.filterTableAll")}</option>
            {/* Jadval nomi texnik identifikator — tarjima yorlig'i yonida turadi. */}
            {AUDIT_TABLES.map((table) => (
              <option key={table} value={table}>
                {tTables(table)}
              </option>
            ))}
          </Select>
        </Field>
      </div>

      <div>
        <Button
          disabled={isEmpty}
          onClick={() => void setUrlFilters(EMPTY_URL_FILTERS)}
          size="sm"
          variant="secondary"
        >
          <FilterX aria-hidden="true" />
          {t("audit.clearFilters")}
        </Button>
      </div>
    </div>
  );
}

function Field({
  children,
  htmlFor,
  label,
}: {
  children: React.ReactNode;
  htmlFor: string;
  label: string;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-sm font-medium" htmlFor={htmlFor}>
        {label}
      </label>
      {children}
    </div>
  );
}

function Select({
  children,
  id,
  onChange,
  value,
}: {
  children: React.ReactNode;
  id: string;
  onChange: (value: string) => void;
  value: string;
}) {
  return (
    <select
      // `border-ui` — boshqaruv elementi chegarasi (WCAG 2.2 SC 1.4.11,
      // o'lchangan 1.28:1 -> 3.64:1).
      className="h-10 w-full rounded-sm border border-border-ui bg-surface px-3 text-sm text-text outline-none focus-visible:border-accent focus-visible:ring-2 focus-visible:ring-accent/25"
      id={id}
      onChange={(event) => onChange(event.target.value)}
      value={value}
    >
      {children}
    </select>
  );
}
