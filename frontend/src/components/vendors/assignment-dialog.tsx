"use client";

import { useEffect, useState } from "react";
import { Check, Link2, TriangleAlert } from "lucide-react";
import { useFormatter, useLocale, useTranslations } from "next-intl";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import type { VendorListItem } from "@/lib/api-types";
import { formatBusinessDay } from "@/lib/format-day";
import { marketErrorMessageKey } from "@/lib/market-errors";
import {
  EMPTY_STALL_FILTERS,
  useCloseAssignment,
  useCreateAssignment,
  useStallAssignmentsQuery,
  useStallsQuery,
} from "@/lib/market-queries";

/*
 * =============================================================================
 * Rasta <-> sotuvchi biriktirish dialogi — IKKI REJIM (D-09/D-10/D-11).
 *
 *   `open`  — yangi davr ochiladi (`stall_id`, `vendor_id`, `from_date`)
 *   `close` — ochiq davr yopiladi (`to_date`)
 *
 * ALMASHINUV — IKKI ALOHIDA AMAL va bu dialog ularni BITTA tugmaga
 * birlashtirmaydi. Backend ham qulaylik endpointini bermaydi va sabab bir
 * xil: "eski sotuvchi qachon ketdi" va "yangisi qachon keldi" — ikki
 * alohida audit yozuvi, ya'ni nizo chiqqanda javob ikkalasida ham bor.
 *
 * DAVR CHEGARASI `[from_date, to_date)` — YOPILISH SANASI KIRMAYDI. Ya'ni
 * ko'rsatilgan kun ALLAQACHON yangi sotuvchiniki va o'sha kunning pattasi
 * unga yoziladi (D-10). Bu jumla ekranda MAJBURIY: usiz admin kunni bir
 * kunga xato qo'yadi va qarz noto'g'ri odamga yoziladi (T-02-117).
 *
 * QOPLANISH DARVOZASI DB'DA (`EXCLUDE` konstrayti -> 409
 * `assignment_period_overlaps`). Bu yerdagi ogohlantirish faqat OLDINDAN
 * aytadi va yuborishni TO'SMAYDI — klient serverdan qattiqroq bo'lmasligi
 * kerak.
 *
 * XATO XARITASI `market-errors.ts` da: 409 `assignment_period_overlaps` ->
 * `vendors.periodOverlaps`, 409 `assignment_not_open` ->
 * `vendors.periodClosed`, 422 `invalid_period` -> `vendors.invalidPeriod`,
 * 404 -> `errors.notFound`. Bu yerda takrorlanmaydi.
 * =============================================================================
 */

export type AssignmentMode = "open" | "close";

/** Qidiruv natijalarida ko'rsatiladigan rastalar soni. */
const STALL_SUGGESTION_LIMIT = 8;

/** Qidiruv so'rovining kechikishi — `nuqs` ning `throttleMs` bilan bir xil. */
const SEARCH_DELAY_MS = 300;

/**
 * Dialog ICHIDAGI qidiruv uchun kechikish.
 *
 * `nuqs` ning `throttleMs` i BU YERDA ishlamaydi: u URL holati uchun, dialog
 * maydoni esa URL'ga chiqmaydi (va chiqmasligi ham kerak — biriktirish
 * oqimining oraliq holati havolada ma'no bermaydi). Usiz har bosilgan
 * tugma alohida `GET /stalls` so'rovini yuborardi.
 */
function useDelayedValue(value: string): string {
  const [delayed, setDelayed] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDelayed(value), SEARCH_DELAY_MS);
    return () => clearTimeout(timer);
  }, [value]);

  return delayed;
}

type SelectedStall = { code: string; id: string };

export function AssignmentDialog({
  mode,
  onOpenChange,
  open,
  vendor,
}: {
  mode: AssignmentMode;
  onOpenChange: (open: boolean) => void;
  open: boolean;
  vendor: VendorListItem;
}) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();

  const [search, setSearch] = useState("");
  const [stall, setStall] = useState<SelectedStall | null>(null);
  const [date, setDate] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [stallError, setStallError] = useState<string | null>(null);
  const [dateError, setDateError] = useState<string | null>(null);

  const delayedSearch = useDelayedValue(search);
  const stallsQuery = useStallsQuery({
    ...EMPTY_STALL_FILTERS,
    q: delayedSearch,
  });
  const assignmentsQuery = useStallAssignmentsQuery(stall?.id ?? null);

  const createAssignment = useCreateAssignment();
  const closeAssignment = useCloseAssignment();

  const isClosing = mode === "close";
  const isBusy = createAssignment.isPending || closeAssignment.isPending;

  const suggestions = (stallsQuery.data?.pages[0]?.items ?? []).slice(
    0,
    STALL_SUGGESTION_LIMIT,
  );

  /*
   * Rastada BIR VAQTDA bitta ochiq davr bo'ladi (D-09). Ochiq davr —
   * `to_date === null`.
   */
  const openPeriod =
    assignmentsQuery.data?.items.find((item) => item.to_date === null) ?? null;
  const openPeriodIsOurs = openPeriod?.vendor_id === vendor.id;

  function handleOpenChange(next: boolean) {
    if (!next) {
      setSearch("");
      setStall(null);
      setDate("");
      setFormError(null);
      setStallError(null);
      setDateError(null);
    }
    onOpenChange(next);
  }

  async function handleSubmit() {
    setFormError(null);
    setStallError(stall === null ? t("vendors.stallRequired") : null);
    setDateError(date === "" ? t("errors.required") : null);
    if (stall === null || date === "") return;

    try {
      if (isClosing) {
        if (openPeriod === null || !openPeriodIsOurs) {
          setFormError(t("vendors.noOpenAssignment"));
          return;
        }
        await closeAssignment.mutateAsync({ id: openPeriod.id, to_date: date });
      } else {
        await createAssignment.mutateAsync({
          stall_id: stall.id,
          vendor_id: vendor.id,
          from_date: date,
          to_date: null,
        });
      }
      handleOpenChange(false);
    } catch (error) {
      setFormError(t(marketErrorMessageKey(error)));
    }
  }

  return (
    <Dialog.Root onOpenChange={handleOpenChange} open={open}>
      <Dialog.Content icon={Link2}
        description={
          isClosing ? t("vendors.closeAssignmentHint") : t("vendors.assignHint")
        }
        size="lg"
        title={
          isClosing ? t("vendors.closeAssignment") : t("vendors.assignStall")
        }
      >
        {/* D-16: sotuvchi ismi DB kontenti — tarjima qilinmaydi. */}
        <p className="rounded-sm bg-surface-muted px-3 py-2 text-sm font-semibold">
          {vendor.full_name}
        </p>

        <Field
          error={stallError ?? undefined}
          id="assignment-stall"
          label={t("vendors.stallLabel")}
        >
          {stall === null ? (
            <Input
              aria-describedby={
                stallError ? "assignment-stall-error" : undefined
              }
              aria-invalid={stallError ? true : undefined}
              autoComplete="off"
              id="assignment-stall"
              onChange={(event) => setSearch(event.target.value)}
              placeholder={t("vendors.stallSearchPlaceholder")}
              type="search"
              value={search}
            />
          ) : (
            <div className="flex items-center justify-between gap-3 rounded-sm border border-border-ui px-3 py-2">
              <span className="flex items-center gap-2 font-mono text-sm tabular-nums">
                <Check aria-hidden="true" className="size-4 text-success-text" />
                {/* D-16: rasta raqami DB kontenti. */}
                {stall.code}
              </span>
              <Button
                onClick={() => {
                  setStall(null);
                  setFormError(null);
                }}
                size="sm"
                variant="secondary"
              >
                {t("common.search")}
              </Button>
            </div>
          )}
        </Field>

        {/*
         * Sotuvchining MAVJUD rastalari — tez tanlov. Yopish rejimida bu
         * deyarli har doim kerakli ro'yxat, ochish rejimida esa "yana bitta
         * rasta" holatida foydali.
         */}
        {stall === null && vendor.stall_codes.length > 0 ? (
          <div className="flex flex-wrap items-center gap-1">
            <span className="text-xs text-text-muted">
              {t("vendors.stallCodesLabel")}:
            </span>
            {vendor.stall_codes.map((code) => (
              <button
                className="rounded-full bg-surface-muted px-2 py-1 font-mono text-xs tabular-nums transition-colors hover:bg-border"
                key={code}
                onClick={() => setSearch(code)}
                type="button"
              >
                {code}
              </button>
            ))}
          </div>
        ) : null}

        {stall === null ? (
          <StallSuggestions
            isPending={stallsQuery.isPending}
            onSelect={(next) => {
              setStall(next);
              setStallError(null);
            }}
            stalls={suggestions}
          />
        ) : null}

        {/*
         * QOPLANISH OGOHLANTIRISHI — TO'SIQ EMAS (`role="status"`, alert
         * emas). Ochiq davr `[from, ∞)` bo'lgani uchun ustiga yangi davr
         * ochish har qanday sanada qoplanadi va server 409 beradi; bu qator
         * shuni OLDINDAN aytadi, lekin yuborishni bloklamaydi — haqiqiy
         * darvoza DB'dagi `EXCLUDE` konstraytida.
         */}
        {!isClosing && openPeriod !== null ? (
          <div
            className="flex flex-col gap-1 rounded-sm bg-warning/20 px-3 py-2 text-sm"
            role="status"
          >
            <span className="flex items-center gap-2 font-semibold">
              <TriangleAlert aria-hidden="true" className="size-4 shrink-0" />
              {t("vendors.periodOverlaps")}
            </span>
            {/* D-16: sotuvchi ismi DB kontenti. */}
            <span className="text-text-muted">
              {t("vendors.currentAssignment", { vendor: openPeriod.vendor_name })}
            </span>
          </div>
        ) : null}

        {isClosing && stall !== null && !openPeriodIsOurs ? (
          <p
            className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
            role="alert"
          >
            {t("vendors.noOpenAssignment")}
          </p>
        ) : null}

        <Field
          error={dateError ?? undefined}
          hint={isClosing ? t("vendors.handoverHint") : undefined}
          id="assignment-date"
          label={
            isClosing ? t("vendors.toDateLabel") : t("vendors.fromDateLabel")
          }
        >
          <Input
            aria-describedby={
              [
                dateError ? "assignment-date-error" : null,
                isClosing ? "assignment-date-hint" : null,
              ]
                .filter((id) => id !== null)
                .join(" ") || undefined
            }
            aria-invalid={dateError ? true : undefined}
            id="assignment-date"
            onChange={(event) => {
              setDate(event.target.value);
              setDateError(null);
            }}
            type="date"
            value={date}
          />
        </Field>

        {/*
         * §10.6 D-4: yopish — destruktiv amal va oqibati AYNAN shu daqiqada
         * aytiladi. Matn TANLANGAN sana bilan chiqadi, ya'ni tasdiq
         * mavhum emas. Ustiga ikkinchi modal QO'YILMAYDI: bu dialogning
         * o'zi forma bo'lib, "Biriktirishni yopish" tugmasi allaqachon
         * ANIQ niyat chegarasi va uning yorlig'i generic "Tasdiqlash" emas.
         */}
        {isClosing && date !== "" ? (
          <p className="rounded-sm bg-surface-muted px-3 py-2 text-sm">
            {t("vendors.closeAssignmentConfirm", {
              date: formatBusinessDay(format, date, locale),
              vendor: vendor.full_name,
            })}
          </p>
        ) : null}

        {formError ? (
          <p
            className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
            role="alert"
          >
            {formError}
          </p>
        ) : null}

        <Dialog.Footer>
          <Button
            className="sm:flex-1"
            disabled={isBusy}
            onClick={() => void handleSubmit()}
            size="lg"
            variant={isClosing ? "destructive" : "default"}
          >
            {isBusy
              ? t("common.loading")
              : isClosing
                ? t("vendors.closeAssignment")
                : t("vendors.assignAction")}
          </Button>
          <Dialog.Close asChild>
            <Button className="sm:flex-1" size="lg" variant="secondary">
              {t("common.cancel")}
            </Button>
          </Dialog.Close>
        </Dialog.Footer>
      </Dialog.Content>
    </Dialog.Root>
  );
}

function StallSuggestions({
  isPending,
  onSelect,
  stalls,
}: {
  isPending: boolean;
  onSelect: (stall: SelectedStall) => void;
  stalls: readonly { code: string; id: string; zone_name: string }[];
}) {
  const t = useTranslations();

  if (isPending) {
    return (
      <p className="text-sm text-text-muted" role="status">
        {t("common.loading")}
      </p>
    );
  }

  if (stalls.length === 0) {
    return <p className="text-sm text-text-muted">{t("vendors.stallNotFound")}</p>;
  }

  return (
    <ul className="flex max-h-56 flex-col gap-1 overflow-y-auto">
      {stalls.map((item) => (
        <li key={item.id}>
          <button
            className="flex min-h-11 w-full items-center justify-between gap-3 rounded-sm border border-border px-3 py-2 text-left text-sm transition-colors hover:bg-surface-muted"
            onClick={() => onSelect({ code: item.code, id: item.id })}
            type="button"
          >
            {/* D-16: rasta raqami va zona nomi DB kontenti. */}
            <span className="font-mono tabular-nums">{item.code}</span>
            <Badge tone="muted">{item.zone_name}</Badge>
          </button>
        </li>
      ))}
    </ul>
  );
}
