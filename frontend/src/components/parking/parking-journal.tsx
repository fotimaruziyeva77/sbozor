"use client";

import { useId, useState } from "react";
import { Camera, Search } from "lucide-react";
import { useTranslations } from "next-intl";

import {
  JOURNAL_FILTERS,
  PLATE_EXAMPLE,
  filterJournal,
  journalCounts,
} from "@/components/parking/parking-data";
import type { JournalFilter } from "@/components/parking/parking-data";
import { JournalPhotoDialog, StatusBadge } from "@/components/parking/parking-photos";
import { PlateBadge } from "@/components/parking/plate-badge";
import { useParkingFormat } from "@/components/parking/use-parking-format";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import type { EdgeParkingReport, EdgeParkingReportSession } from "@/lib/api-types";

/*
 * =============================================================================
 * MASHINALAR JURNALI — davrdagi har seans, raqam bo'yicha qidiruv (261102).
 *
 * Avvalgi qaror («ro'yxat faqat Excelda») telefonda minglab qatorni
 * o'qib bo'lmasligidan edi. Endi ro'yxat SAHIFALANADI (25 tadan) va
 * raqam bo'yicha QIDIRILADI — «bu mashina qachon kirgan edi?» savoliga
 * Excel ochmasdan javob. To'liq fayl baribir Excelda.
 *
 * ⛔ Kadr qatorda chizilmaydi — faqat tugma: har ochilish auditga
 *    yoziladi va 25 ta kadr telefonda megabaytlab trafik bo'lardi.
 * =============================================================================
 */

const PAGE_SIZE = 25;

export function JournalCard({
  data,
  siteId,
}: {
  data: EdgeParkingReport;
  siteId: string;
}) {
  const t = useTranslations("parkingReport");
  const searchId = useId();
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<JournalFilter>("all");
  const [limit, setLimit] = useState(PAGE_SIZE);
  const [photo, setPhoto] = useState<EdgeParkingReportSession | null>(null);

  const counts = journalCounts(data.sessions);
  const rows = filterJournal(data.sessions, query, filter);
  const visible = rows.slice(0, limit);

  function changeFilter(next: JournalFilter): void {
    setFilter(next);
    setLimit(PAGE_SIZE);
  }

  return (
    <Card className="dir-chart-card hover:translate-y-0">
      <CardHeader className="flex flex-row flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="dir-trend-title">{t("journal.title")}</h2>
          <p className="dir-tile-sub">
            {t("journal.shown", { shown: visible.length, total: rows.length })}
          </p>
        </div>
        <div className="park-search">
          <label className="sr-only" htmlFor={searchId}>
            {t("journal.searchLabel")}
          </label>
          <Search aria-hidden="true" className="park-search-icon size-4" />
          <input
            autoComplete="off"
            className="park-search-input"
            id={searchId}
            onChange={(event) => {
              setQuery(event.target.value);
              setLimit(PAGE_SIZE);
            }}
            placeholder={t("journal.searchPlaceholder", { example: PLATE_EXAMPLE.slice(0, 6) })}
            spellCheck={false}
            type="search"
            value={query}
          />
        </div>
      </CardHeader>

      <CardContent className="flex flex-col gap-4">
        <div aria-label={t("journal.filterLabel")} className="flex flex-wrap gap-1.5" role="group">
          {JOURNAL_FILTERS.map((item) => (
            <Button
              aria-pressed={filter === item}
              key={item}
              onClick={() => changeFilter(item)}
              size="sm"
              variant={filter === item ? "secondary" : "ghost"}
            >
              {t(`journal.filter.${item}`)}{" "}
              <span className="park-filter-count">{counts[item]}</span>
            </Button>
          ))}
        </div>

        {rows.length === 0 ? (
          <EmptyState description={t("journal.noMatchHint")} title={t("journal.noMatch")} />
        ) : (
          <div className="park-journal-scroll">
            {/* Native `<table>` + `<caption class="sr-only">` + `<th scope>` (§15). */}
            <table className="park-journal">
              <caption className="sr-only">{t("journal.title")}</caption>
              <thead>
                <tr>
                  <th scope="col">{t("journal.colPlate")}</th>
                  <th scope="col">{t("journal.colEntered")}</th>
                  <th scope="col">{t("journal.colExited")}</th>
                  <th className="park-num" scope="col">
                    {t("journal.colDuration")}
                  </th>
                  <th className="park-num" scope="col">
                    {t("journal.colAmount")}
                  </th>
                  <th scope="col">{t("journal.colStatus")}</th>
                  <th scope="col">
                    <span className="sr-only">{t("journal.colPhoto")}</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {visible.map((session) => (
                  <JournalRow
                    key={session.session_id}
                    onPhoto={() => setPhoto(session)}
                    session={session}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}

        {rows.length > visible.length ? (
          <div>
            <Button onClick={() => setLimit((n) => n + PAGE_SIZE)} size="sm" variant="secondary">
              {t("journal.more", { count: Math.min(PAGE_SIZE, rows.length - visible.length) })}
            </Button>
          </div>
        ) : null}
      </CardContent>

      {photo === null ? null : (
        <JournalPhotoDialog onClose={() => setPhoto(null)} session={photo} siteId={siteId} />
      )}
    </Card>
  );
}

function JournalRow({
  session,
  onPhoto,
}: {
  session: EdgeParkingReportSession;
  onPhoto: () => void;
}) {
  const t = useTranslations("parkingReport");
  const fmt = useParkingFormat();
  const plate = session.plate ?? t("noPlate");
  const photoLabel = t(session.opened_at_exit ? "journal.photoExit" : "journal.photo", { plate });

  return (
    <tr>
      <th scope="row">
        <PlateBadge plate={session.plate} size="sm" />
      </th>
      <td>
        {/* Chiqishda ro'yxatga olingan: kirgan vaqti NOMA'LUM — chiqish vaqti takrorlanmaydi. */}
        {session.opened_at_exit ? (
          <span className="park-stamp">
            <span className="text-text-muted">—</span>
            <span className="park-stamp-day">{t("journal.atExit")}</span>
          </span>
        ) : (
          <Stamp iso={session.entered_at} />
        )}
      </td>
      <td>
        {session.exited_at === null ? (
          <span className="text-text-muted">—</span>
        ) : (
          <Stamp iso={session.exited_at} />
        )}
      </td>
      <td className="park-num">
        {session.duration_minutes === null || session.opened_at_exit
          ? "—"
          : fmt.duration(session.duration_minutes)}
      </td>
      <td className="park-num">
        {session.amount_soum > 0 ? fmt.soum(session.amount_soum) : "—"}
      </td>
      <td>
        <StatusBadge session={session} />
      </td>
      <td>
        {session.entry_file_id === null ? null : (
          <Button
            aria-label={photoLabel}
            onClick={onPhoto}
            size="sm"
            title={photoLabel}
            variant="ghost"
          >
            <Camera aria-hidden="true" />
          </Button>
        )}
      </td>
    </tr>
  );
}

/** Vaqt (kuchli) va kun (sust) — ikki qator; ma'lum bo'lmasa chiziqcha. */
function Stamp({ iso }: { iso: string | null }) {
  const fmt = useParkingFormat();
  if (iso === null) return <span className="text-text-muted">—</span>;
  return (
    <span className="park-stamp">
      <span className="park-stamp-time">{fmt.time(iso)}</span>
      <span className="park-stamp-day">{fmt.day(iso)}</span>
    </span>
  );
}
