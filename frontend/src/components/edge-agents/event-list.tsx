"use client";

import { useState } from "react";
import { TriangleAlert } from "lucide-react";
import { useFormatter, useLocale, useTimeZone, useTranslations } from "next-intl";

import { EdgeFrameThumb } from "@/components/edge-agents/edge-frame";
import {
  EVENT_TYPE_LABELS,
  KNOWN_EVENT_TYPES,
  eventTypeLabel,
  summarizeEventData,
} from "@/components/edge-agents/edge-labels";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import type { EdgeEvent } from "@/lib/api-types";
import { formatInstant } from "@/lib/format-day";
import { formatSoum } from "@/lib/format-number";
import { useEdgeEventsQuery } from "@/lib/edge-site-queries";

/** So'nggi hodisalar: tur filtri + «Ko'proq» (offset). */
export function EventList({ siteId }: { siteId: string }) {
  const t = useTranslations();
  const tType = useTranslations("edgeAgents.events.type");
  const [type, setType] = useState("");
  const events = useEdgeEventsQuery(siteId, type);

  const rows = events.data?.pages.flatMap((page) => page.items) ?? [];

  return (
    <Card>
      <CardHeader>
        <h2 className="text-lg font-semibold">{t("edgeAgents.events.title")}</h2>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <Field
          className="max-w-xs"
          id="edge-event-type"
          label={t("edgeAgents.events.filterType")}
        >
          <Select
            id="edge-event-type"
            onChange={(event) => setType(event.target.value)}
            value={type}
          >
            <option value="">{t("edgeAgents.events.filterAll")}</option>
            {KNOWN_EVENT_TYPES.map((value) => (
              <option key={value} value={value}>
                {tType(EVENT_TYPE_LABELS[value])}
              </option>
            ))}
          </Select>
        </Field>

        {events.isPending ? (
          <div aria-busy="true" className="flex flex-col gap-2" role="status">
            <span className="sr-only">{t("common.loading")}</span>
            <Skeleton className="h-12" />
            <Skeleton className="h-12" />
            <Skeleton className="h-12" />
          </div>
        ) : events.isError && rows.length === 0 ? (
          <div
            className="flex flex-col items-start gap-3 rounded-md bg-danger/10 p-4 text-danger-text"
            role="alert"
          >
            <p className="text-sm">{t("errors.loadFailedBody")}</p>
            <Button onClick={() => void events.refetch()} size="sm" variant="secondary">
              {t("common.retry")}
            </Button>
          </div>
        ) : rows.length === 0 ? (
          <p className="text-sm text-text-muted">{t("edgeAgents.events.empty")}</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-sm">
              <caption className="sr-only">{t("edgeAgents.events.title")}</caption>
              <thead>
                <tr className="border-b border-border text-left text-xs text-text-muted">
                  <th className="p-2 font-normal" scope="col">{t("edgeAgents.events.colTime")}</th>
                  <th className="p-2 font-normal" scope="col">{t("edgeAgents.events.colType")}</th>
                  <th className="p-2 font-normal" scope="col">{t("edgeAgents.events.colData")}</th>
                  <th className="p-2 font-normal" scope="col">{t("edgeAgents.events.colFrames")}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((event) => (
                  <EventRow event={event} key={event.id} siteId={siteId} />
                ))}
              </tbody>
            </table>
          </div>
        )}

        {events.isFetchNextPageError ? (
          <p className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text" role="alert">
            {t("errors.loadFailedBody")}
          </p>
        ) : null}

        {events.hasNextPage ? (
          <div>
            <Button
              disabled={events.isFetchingNextPage}
              onClick={() => void events.fetchNextPage()}
              variant="secondary"
            >
              {events.isFetchingNextPage
                ? t("common.loading")
                : t("edgeAgents.events.more")}
            </Button>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

function EventRow({ event, siteId }: { event: EdgeEvent; siteId: string }) {
  const t = useTranslations("edgeAgents.events");
  const format = useFormatter();
  const locale = useLocale();
  const timeZone = useTimeZone();
  const label = eventTypeLabel(event.type);
  const at = new Date(event.occurred_at);
  const summary = summarizeEventData(event.data, (value) =>
    formatSoum(format, value, locale),
  );

  return (
    <tr className="border-b border-border align-top">
      <td className="p-2 whitespace-nowrap">
        {Number.isNaN(at.getTime())
          ? event.occurred_at
          : formatInstant(format, at, locale, timeZone, "short", "medium")}
        {event.clock_ok ? null : (
          <span
            className="ml-1 inline-flex align-middle text-warning-text"
            title={t("clockWarn")}
          >
            <TriangleAlert aria-hidden="true" className="size-4" />
            <span className="sr-only">{t("clockWarn")}</span>
          </span>
        )}
      </td>
      <td className="p-2">
        {label === null ? (
          <span className="font-mono text-xs">{event.type}</span>
        ) : (
          t(`type.${label}`)
        )}
      </td>
      <td className="p-2 break-words text-text-muted">{summary || "—"}</td>
      <td className="p-2">
        {event.file_ids.length === 0 ? (
          <span className="text-text-muted">—</span>
        ) : (
          <div className="flex flex-wrap gap-1">
            {event.file_ids.map((fileId) => (
              <EdgeFrameThumb fileId={fileId} key={fileId} siteId={siteId} />
            ))}
          </div>
        )}
      </td>
    </tr>
  );
}
